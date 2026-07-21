# PayFast ITN: atomic claim-and-grant — design

**Date:** 2026-07-21
**Status:** Approved, ready for implementation plan
**Backlog item:** `docs/BACKLOG.md` — "PayFast ITN: claim-and-grant is not a single transaction"

## Problem

`backend/routes/payfast_routes.py`'s `payfast_notify` makes granting idempotent
by claiming the intent row (`_claim_intent`: a conditional `UPDATE ... WHERE
status = 'pending'`) before granting. This closes the double-grant race, but
claim and grant are two separate round-trips, not one transaction. If the
process dies between them, `_release_claim` never runs: the row is left
`status = 'complete'` with nothing granted, and PayFast's retry sees a claimed
row and declines to redo it — the user paid and received nothing, needing
manual repair. The window is small (milliseconds, crash/OOM/redeploy only) and
the failure direction is safe (missed grant, not double grant), which is why
this was deferred rather than blocking the original two-tier pricing ship.

## Decision

Move claim + grant into a single `SECURITY DEFINER` plpgsql function,
`payfast_claim_and_grant`, called via Supabase RPC. Because both happen inside
one function invocation, they're one implicit Postgres transaction: a mid-call
crash means Postgres rolls back everything, including the claim — there is no
window left where the row is `complete` with nothing granted. This was chosen
over the two cheaper alternatives (a reconciliation sweep, or claim leases)
because it closes the gap entirely rather than adding a safety net or a
timing-based workaround around it.

**Scope: ITN-only.** `activate_license` is also called from
`admin_routes.py`'s manual-approval path, which has no race (single admin
action, no concurrent ITN callback). That path keeps calling the existing
Python `grant_credits`/`activate_license`/`grant_seats` in
`entitlement_service.py` untouched. The new SQL function duplicates the grant
logic for the ITN path only — accepted as a deliberate trade-off: unifying the
two paths would force the admin path into PayFast-specific claim semantics it
doesn't need, for no correctness benefit there.

## Migration: `db/migrations/043_payfast_atomic_claim_grant.sql`

```sql
CREATE OR REPLACE FUNCTION payfast_claim_and_grant(
    p_txn_id UUID,
    p_pf_payment_id TEXT,
    p_raw_payload JSONB,
    p_charge_type TEXT,
    p_user_id UUID,
    p_quantity INTEGER,
    p_payfast_token TEXT DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    v_term TIMESTAMPTZ;
BEGIN
    UPDATE payfast_transactions
    SET pf_payment_id = p_pf_payment_id,
        status = 'complete',
        raw_payload = p_raw_payload,
        updated_at = NOW()
    WHERE id = p_txn_id AND status = 'pending';

    IF NOT FOUND THEN
        RETURN 'duplicate';  -- someone else already claimed it
    END IF;

    IF p_charge_type = 'tier_1_credits' THEN
        INSERT INTO breakdown_credits (user_id, delta, payfast_transaction_id, reason)
        VALUES (p_user_id, p_quantity, p_txn_id, 'purchase');

    ELSIF p_charge_type = 'tier_2_license' THEN
        UPDATE profiles SET
            subscription_plan = 'tier_2_annual_team',
            subscription_status = 'active',
            subscription_expires_at = NOW() + INTERVAL '365 days',
            subscription_payment_provider = 'payfast',
            subscription_amount = 1850.00,
            subscription_currency = 'ZAR',
            subscription_payfast_token = COALESCE(p_payfast_token, subscription_payfast_token)
        WHERE id = p_user_id;

    ELSIF p_charge_type = 'tier_2_seats' THEN
        SELECT subscription_expires_at INTO v_term FROM profiles WHERE id = p_user_id;
        v_term := COALESCE(v_term, NOW() + INTERVAL '365 days');
        INSERT INTO account_seats (owner_id, seats_granted, payfast_transaction_id, term_expires_at)
        VALUES (p_user_id, p_quantity, p_txn_id, v_term);

    ELSE
        -- Defense in depth: payfast_routes.py already rejects unknown
        -- charge_type before calling this function. Raising here rolls
        -- back the claim UPDATE above too, same as any other failure.
        RAISE EXCEPTION 'unknown charge_type: %', p_charge_type;
    END IF;

    RETURN 'granted';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION payfast_claim_and_grant IS
    'Atomically claims a payfast_transactions row and performs its grant in one transaction, closing the crash-between-claim-and-grant window. ITN-only -- the admin manual-approval path uses the plain Python grant functions in entitlement_service.py, which have no race to close.';

REVOKE EXECUTE ON FUNCTION payfast_claim_and_grant FROM PUBLIC;
GRANT EXECUTE ON FUNCTION payfast_claim_and_grant TO service_role;
```

The values written by each branch mirror the existing Python functions
exactly: `grant_credits` (`breakdown_credits` insert), `activate_license`
(`profiles` update, including the 365-day term and the
`COALESCE(p_payfast_token, ...)` "only overwrite if a new token was given"
behavior), and `grant_seats` (`account_seats` insert, term inherited from the
owner's current `subscription_expires_at` or defaulted to +365 days).

Any exception in the `IF`/`ELSIF` branches — a constraint violation, or the
defensive `RAISE EXCEPTION` — aborts the whole function, rolling back the
claim `UPDATE` at the top too. This is what makes the existing
`_release_claim()` unnecessary for DB-side failures: the row is already back
to `pending` by the time the exception surfaces to Python.

## Python: `backend/routes/payfast_routes.py`

Replace `_claim_intent` + individual grant dispatch + `_release_claim` with
one call:

```python
def _claim_and_grant(txn_id: str, pf_payment_id: str, payload: dict,
                      charge_type: str, user_id: str, quantity: int,
                      payfast_token: str | None) -> str:
    """
    Calls the payfast_claim_and_grant Postgres function (migration 043),
    which claims the intent row and performs its grant atomically in one
    transaction. Returns 'granted' or 'duplicate'.
    """
    resp = get_supabase_admin().rpc('payfast_claim_and_grant', {
        'p_txn_id': txn_id,
        'p_pf_payment_id': pf_payment_id,
        'p_raw_payload': payload,
        'p_charge_type': charge_type,
        'p_user_id': user_id,
        'p_quantity': quantity,
        'p_payfast_token': payfast_token,
    }).execute()
    return resp.data
```

`payfast_notify` replaces its claim/grant/release block with:

```python
    # The concurrency boundary: claim + grant now happen in one DB
    # transaction (migration 043) -- no window for a crash to leave the
    # row 'complete' with nothing granted.
    try:
        result = _claim_and_grant(txn_id, pf_payment_id, form, charge_type,
                                   user_id, quantity, form.get('token'))
    except Exception as exc:
        # DB-side failure (RPC error, constraint violation, etc). The
        # function's exception already rolled back any partial writes,
        # including the claim -- nothing to release here.
        return _reject(f'grant failed: {exc!r}')

    if result == 'duplicate':
        return jsonify({'status': 'duplicate'}), 200   # someone else has it

    return jsonify({'status': 'ok'}), 200
```

Removed from this file: `_claim_intent`, `_release_claim`, and the
`grant_credits, activate_license, grant_seats` import (those stay in
`entitlement_service.py`, still used by `admin_routes.py`).

## Test suite: `backend/tests/test_payfast_itn_route.py`

The current suite mocks four separate seams (`_claim_intent`,
`_release_claim`, and each grant function individually) because that mirrored
the two-round-trip implementation. With one RPC call, tests instead mock
`_claim_and_grant` and assert on what it was called with:

- Grant tests (`test_valid_itn_grants_credits`,
  `test_seats_grant_uses_intent_quantity`, etc.) mock `_claim_and_grant` to
  return `'granted'` and assert the call arguments
  `(txn_id, pf_payment_id, form, charge_type, user_id, quantity, token)`.
- `test_replay_is_idempotent` / `test_losing_a_concurrent_claim_grants_nothing`
  mock `_claim_and_grant` to return `'duplicate'`; assert 200 and no further
  action.
- `test_failed_grant_releases_the_claim` is renamed/reframed (there is no
  more explicit release call) to `test_grant_failure_still_returns_200`: mock
  `_claim_and_grant` to raise, assert 200 (PayFast retries) and no exception
  propagates.
- `test_claim_happens_before_granting` is dropped. There is only one call now
  — call-ordering is no longer a meaningful thing to assert in Python.
  Atomicity is now a database-transaction guarantee, verified separately (see
  below), not a Python-level ordering guarantee.

## Pre-deploy verification against a real Postgres

Mocking the RPC boundary in `pytest` proves the Python side dispatches
correctly, but proves nothing about the SQL function's actual transactional
behavior. Before this migration ships, verify it directly against a real,
local Postgres — a one-time check, not a permanent CI-integrated test (the
existing `backend-tests.yml` CI gate stays DB-free and mocked, as designed).

Steps:

1. `docker run --rm -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres --name pf_verify postgres:15`
2. Load a minimal schema: just `profiles`, `payfast_transactions`,
   `breakdown_credits`, `account_seats`, trimmed to the columns migration 043
   reads/writes (not the full app schema).
3. Apply migration 043 (creates the function).
4. Run a throwaway Python script (`psycopg2-binary`, installed in the local
   venv for this only — not added to `requirements.txt`, production code
   never touches Postgres directly) that exercises:
   - Each of the 3 charge types grants correctly and marks the row
     `complete`.
   - Calling again on an already-`complete` row returns `'duplicate'` and
     does not double-grant.
   - A forced failure (unknown charge type, hitting `RAISE EXCEPTION`) leaves
     the row back at `status = 'pending'` — proving the claim rolls back too.
   - **Real concurrency**: two threads, two separate `psycopg2` connections,
     both call the function on the same pending row at nearly the same
     instant. Assert exactly one returns `'granted'`, the other `'duplicate'`,
     and exactly one grant row exists.
5. Tear down the container (`docker rm -f pf_verify`).

This verification is not committed as a test file; it's a manual gate run
once during implementation, documented in the implementation plan with exact
commands so it's reproducible if ever needed again (e.g. if the function is
modified later).

## References

- `backend/routes/payfast_routes.py` — `_claim_intent`, `_release_claim`,
  `payfast_notify`
- `backend/services/entitlement_service.py` — `grant_credits`,
  `activate_license`, `grant_seats` (untouched, still used by
  `admin_routes.py`)
- `backend/db/migrations/041_two_tier_pricing.sql` — existing
  `payfast_transactions`, `breakdown_credits`, `account_seats` schema
- `backend/db/migrations/032_pricing_simplification.sql` — existing
  `SECURITY DEFINER` function precedent (`activate_monthly_subscription`)
- `backend/tests/test_payfast_itn_route.py`
