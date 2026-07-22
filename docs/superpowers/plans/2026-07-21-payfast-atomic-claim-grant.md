# PayFast Atomic Claim-and-Grant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the crash-between-claim-and-grant window in the PayFast ITN handler by moving claim + grant into one atomic Postgres transaction, so a mid-call crash can never leave a `payfast_transactions` row `complete` with nothing granted.

**Architecture:** A new plpgsql function `payfast_claim_and_grant` (migration 043) performs the conditional claim UPDATE and the charge-type-specific grant in one function invocation — one implicit transaction. `backend/routes/payfast_routes.py` calls it via `get_supabase_admin().rpc(...)` instead of orchestrating `_claim_intent` → grant → `_release_claim` across three separate round-trips. `entitlement_service.py`'s Python grant functions are untouched (still used by the admin manual-approval path, which has no race). Verified pre-deploy against a real local Postgres via Docker — not part of the committed test suite or CI.

**Tech Stack:** Postgres plpgsql (`SECURITY DEFINER` function), Supabase RPC via `supabase-py`, Flask, pytest with `monkeypatch`. Verification-only: Docker, `psycopg2-binary` (installed in the local venv only, not `requirements.txt`).

## Global Constraints

- ITN-only scope: do not modify `entitlement_service.py`'s `grant_credits`, `activate_license`, or `grant_seats` — they stay in use by `admin_routes.py`.
- The new SQL function must reproduce the exact values each Python grant function writes (see Task 1) — this is a behavior-preserving refactor, not a behavior change.
- No new dependency in `backend/requirements.txt` — `psycopg2-binary` is a local-venv-only tool for the one-time verification script (Task 3), never imported by application code.
- The real-Postgres verification (Task 3) is a one-time, throwaway check — do not add it to `backend/tests/` or `.github/workflows/backend-tests.yml`.

---

### Task 1: Write and apply the migration

**Files:**
- Create: `backend/db/migrations/043_payfast_atomic_claim_grant.sql`

**Interfaces:**
- Consumes: existing `payfast_transactions`, `breakdown_credits`, `account_seats`, `profiles` tables (schema in `db/migrations/041_two_tier_pricing.sql`, `042_payfast_tokenization.sql`).
- Produces: a Postgres function `payfast_claim_and_grant(p_txn_id UUID, p_pf_payment_id TEXT, p_raw_payload JSONB, p_charge_type TEXT, p_user_id UUID, p_quantity INTEGER, p_payfast_token TEXT DEFAULT NULL) RETURNS TEXT`, callable via RPC as `'payfast_claim_and_grant'`. Returns `'granted'` or `'duplicate'`; raises (and rolls back everything, including the claim) on any grant-branch failure. This is what Task 2 calls.

- [ ] **Step 1: Write the migration file**

Create `backend/db/migrations/043_payfast_atomic_claim_grant.sql`:

```sql
-- Migration: Atomic claim-and-grant for PayFast ITN
-- Description: Closes the crash-between-claim-and-grant window in
--              payfast_notify. The old flow claimed the intent row
--              (_claim_intent) and granted (grant_credits/
--              activate_license/grant_seats) in two separate
--              round-trips; if the process died between them, the row
--              was left 'complete' with nothing granted, and PayFast's
--              retry declined to redo an already-claimed row. This
--              function performs both in one transaction, so a mid-call
--              crash rolls back the claim too. ITN-only -- the admin
--              manual-approval path (routes/admin_routes.py) has no
--              race and keeps calling the plain Python grant functions
--              in services/entitlement_service.py unchanged.
-- Date: 2026-07-21

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
        RETURN 'duplicate';
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

- [ ] **Step 2: Validate the SQL parses correctly**

Run: `docker run --rm -e POSTGRES_PASSWORD=postgres -v "$(pwd)/backend/db/migrations/043_payfast_atomic_claim_grant.sql:/tmp/043.sql" postgres:15 sh -c "docker-entrypoint.sh postgres &>/dev/null & sleep 5 && pg_isready -h localhost -U postgres" 2>&1 || true`

This step is superseded by the full verification in Task 3, which actually creates the function against real tables — skip a standalone syntax check here and rely on Task 3's `CREATE FUNCTION` call to surface any SQL errors (it will fail loudly if the syntax is wrong).

- [ ] **Step 3: Apply the migration to the real Supabase project**

This repo's convention (per `db/migrations/*.sql` and `CLAUDE.md`) is that migrations are applied directly against the Supabase project's SQL editor or via the Supabase CLI/dashboard — there is no local migration-runner script in this repo (`db/apply_migration_017.py` and `db/apply_migration_020.py` are one-off scripts for specific past migrations, not a general runner). Apply `043_payfast_atomic_claim_grant.sql` to the project's database now via the Supabase SQL editor (dashboard) or `supabase db push` if the project is linked locally — confirm which before running, since this touches the real production/staging database referenced in `CLAUDE.md` (project `slateone`/`twzfaizeyqwevmhjyicz`, per memory `no-sqlite-supabase-only.md`).

Expected: `CREATE FUNCTION` succeeds with no error; a `SELECT proname FROM pg_proc WHERE proname = 'payfast_claim_and_grant';` run in the same SQL editor returns one row.

- [ ] **Step 4: Commit the migration file**

```bash
git add backend/db/migrations/043_payfast_atomic_claim_grant.sql
git commit -m "feat(payfast): add atomic claim-and-grant Postgres function

Closes the crash-between-claim-and-grant window: claim and grant now
happen in one transaction (migration 043), so a mid-call crash rolls
back both instead of leaving a paid, ungranted payfast_transactions
row. ITN-only -- entitlement_service.py's Python grant functions are
unchanged and still used by the admin manual-approval path."
```

---

### Task 2: Rewire `payfast_routes.py` to call the new function

**Files:**
- Modify: `backend/routes/payfast_routes.py:45-145` (replace `_claim_intent`, `_release_claim`, and the grant-dispatch block in `payfast_notify`)

**Interfaces:**
- Consumes: `payfast_claim_and_grant` RPC from Task 1.
- Produces: `_claim_and_grant(txn_id, pf_payment_id, payload, charge_type, user_id, quantity, payfast_token) -> str` (`'granted'` or `'duplicate'`), the single seam Task 4's rewritten tests mock.

- [ ] **Step 1: Remove `_claim_intent` and `_release_claim`, add `_claim_and_grant`**

In `backend/routes/payfast_routes.py`, delete the `_claim_intent` function (lines 45-67) and `_release_claim` function (lines 70-75). In their place:

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

- [ ] **Step 2: Update the import line**

Change:
```python
from services.entitlement_service import (
    grant_credits, activate_license, grant_seats, get_entitlement,
)
```
to:
```python
from services.entitlement_service import get_entitlement
```

- [ ] **Step 3: Replace the claim/grant/release block in `payfast_notify`**

Replace this block (currently lines 130-143):
```python
    # The concurrency boundary: past here we hold the row exclusively.
    if not _claim_intent(txn_id, pf_payment_id, form):
        return jsonify({'status': 'duplicate'}), 200   # someone else has it

    try:
        if charge_type == 'tier_1_credits':
            grant_credits(user_id, quantity, txn_id)
        elif charge_type == 'tier_2_license':
            activate_license(user_id, txn_id, form.get('token'))
        elif charge_type == 'tier_2_seats':
            grant_seats(user_id, quantity, txn_id)
    except Exception as exc:
        _release_claim(txn_id)
        return _reject(f'grant failed, released for retry: {exc!r}')

    return jsonify({'status': 'ok'}), 200
```

with:
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

- [ ] **Step 4: Confirm the file has no remaining references to the deleted functions**

Run: `grep -n "_claim_intent\|_release_claim\|grant_credits\|activate_license\|grant_seats" backend/routes/payfast_routes.py`
Expected: no output (all references removed from this file).

---

### Task 3: Verify against a real local Postgres (pre-deploy gate)

**Files:**
- Create (throwaway, not committed): `/tmp/pf_verify_schema.sql`, `/tmp/pf_verify.py`

**Interfaces:**
- Consumes: `payfast_claim_and_grant` from Task 1's migration file.
- Produces: a pass/fail confirmation reported back before Task 4/5 proceed. Nothing here is committed to the repo.

- [ ] **Step 1: Start a local Postgres container**

Run:
```bash
docker run --rm -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres --name pf_verify postgres:15
sleep 3
docker exec pf_verify pg_isready -U postgres
```
Expected: `accepting connections`.

- [ ] **Step 2: Load a minimal schema**

Write `/tmp/pf_verify_schema.sql`:
```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE profiles (
    id UUID PRIMARY KEY,
    subscription_plan TEXT,
    subscription_status TEXT,
    subscription_expires_at TIMESTAMPTZ,
    subscription_payment_provider TEXT,
    subscription_amount NUMERIC(10,2),
    subscription_currency TEXT,
    subscription_payfast_token TEXT
);

CREATE TABLE payfast_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pf_payment_id TEXT UNIQUE,
    user_id UUID NOT NULL REFERENCES profiles(id),
    charge_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    raw_payload JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE breakdown_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    delta INTEGER NOT NULL,
    script_id UUID,
    payfast_transaction_id UUID,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE account_seats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    seats_granted INTEGER NOT NULL,
    payfast_transaction_id UUID,
    term_expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO profiles (id, subscription_plan, subscription_status)
VALUES ('11111111-1111-1111-1111-111111111111', 'none', 'none');
```

Run:
```bash
docker cp /tmp/pf_verify_schema.sql pf_verify:/tmp/schema.sql
docker cp backend/db/migrations/043_payfast_atomic_claim_grant.sql pf_verify:/tmp/043.sql
docker exec -u postgres pf_verify psql -U postgres -f /tmp/schema.sql
docker exec -u postgres pf_verify psql -U postgres -f /tmp/043.sql
```
Expected: both commands report `CREATE TABLE` / `INSERT 0 1` and `CREATE FUNCTION` with no errors.

- [ ] **Step 3: Write and run the verification script**

Write `/tmp/pf_verify.py`:
```python
import uuid
import threading
import psycopg2

DSN = "host=localhost port=5432 dbname=postgres user=postgres password=postgres"
USER_ID = "11111111-1111-1111-1111-111111111111"


def _new_txn(conn, charge_type):
    txn_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO payfast_transactions (id, user_id, charge_type, status) "
            "VALUES (%s, %s, %s, 'pending')",
            (txn_id, USER_ID, charge_type),
        )
    conn.commit()
    return txn_id


def _call(conn, txn_id, charge_type, quantity=1, pf_payment_id=None):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT payfast_claim_and_grant(%s, %s, %s, %s, %s, %s, %s)",
            (txn_id, pf_payment_id or str(uuid.uuid4()), '{}', charge_type,
             USER_ID, quantity, None),
        )
        result = cur.fetchone()[0]
    conn.commit()
    return result


def test_each_charge_type_grants():
    conn = psycopg2.connect(DSN)
    for charge_type, table in [
        ('tier_1_credits', 'breakdown_credits'),
        ('tier_2_license', None),
        ('tier_2_seats', 'account_seats'),
    ]:
        txn_id = _new_txn(conn, charge_type)
        result = _call(conn, txn_id, charge_type)
        assert result == 'granted', f"{charge_type}: expected granted, got {result}"
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM payfast_transactions WHERE id = %s", (txn_id,))
            assert cur.fetchone()[0] == 'complete'
            if table:
                cur.execute(f"SELECT count(*) FROM {table} WHERE payfast_transaction_id = %s", (txn_id,))
                assert cur.fetchone()[0] == 1, f"{charge_type}: expected 1 {table} row"
    print("PASS: each charge type grants and marks the row complete")
    conn.close()


def test_duplicate_call_does_not_regrant():
    conn = psycopg2.connect(DSN)
    txn_id = _new_txn(conn, 'tier_1_credits')
    first = _call(conn, txn_id, 'tier_1_credits')
    second = _call(conn, txn_id, 'tier_1_credits')
    assert first == 'granted'
    assert second == 'duplicate'
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM breakdown_credits WHERE payfast_transaction_id = %s", (txn_id,))
        assert cur.fetchone()[0] == 1, "expected exactly one grant, not two"
    print("PASS: duplicate call returns 'duplicate' and does not double-grant")
    conn.close()


def test_failure_rolls_back_the_claim():
    conn = psycopg2.connect(DSN)
    txn_id = _new_txn(conn, 'free_stuff')  # not a real charge_type
    try:
        _call(conn, txn_id, 'free_stuff')
        raise AssertionError("expected an exception for unknown charge_type")
    except psycopg2.Error:
        conn.rollback()
    # Reconnect to confirm the row's committed state (not just this txn's view)
    conn2 = psycopg2.connect(DSN)
    with conn2.cursor() as cur:
        cur.execute("SELECT status FROM payfast_transactions WHERE id = %s", (txn_id,))
        status = cur.fetchone()[0]
    assert status == 'pending', f"expected claim to roll back to pending, got {status}"
    print("PASS: a grant-branch failure rolls back the claim too")
    conn.close()
    conn2.close()


def test_concurrent_calls_grant_exactly_once():
    conn = psycopg2.connect(DSN)
    txn_id = _new_txn(conn, 'tier_1_credits')
    conn.close()

    results = []

    def _worker():
        c = psycopg2.connect(DSN)
        results.append(_call(c, txn_id, 'tier_1_credits'))
        c.close()

    t1 = threading.Thread(target=_worker)
    t2 = threading.Thread(target=_worker)
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert sorted(results) == ['duplicate', 'granted'], f"expected one granted, one duplicate, got {results}"

    conn = psycopg2.connect(DSN)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM breakdown_credits WHERE payfast_transaction_id = %s", (txn_id,))
        assert cur.fetchone()[0] == 1, "expected exactly one grant under real concurrency"
    print("PASS: two concurrent calls on the same row grant exactly once")
    conn.close()


if __name__ == '__main__':
    test_each_charge_type_grants()
    test_duplicate_call_does_not_regrant()
    test_failure_rolls_back_the_claim()
    test_concurrent_calls_grant_exactly_once()
    print("ALL VERIFICATION CHECKS PASSED")
```

Run: `backend/venv/bin/python /tmp/pf_verify.py`
Expected: all four `PASS:` lines and `ALL VERIFICATION CHECKS PASSED`, no `AssertionError` or unhandled exception.

- [ ] **Step 4: Tear down**

Run: `docker rm -f pf_verify`

- [ ] **Step 5: Report the verification result**

No commit in this task (nothing here is part of the repo). Report to the user: all 4 checks passed (or, if something failed, stop and return to Task 1/2 to fix it before proceeding — do not continue to Task 4 on a failed verification).

---

### Task 4: Rewrite `test_payfast_itn_route.py` for the new single-call seam

**Files:**
- Modify: `backend/tests/test_payfast_itn_route.py` (full rewrite of the mocking helper and several tests)

**Interfaces:**
- Consumes: `pr._claim_and_grant` (Task 2) as the single mock seam, replacing the four seams (`_claim_intent`, `_release_claim`, `grant_credits`, `activate_license`, `grant_seats`) the old tests mocked.
- Produces: a green `pytest tests/test_payfast_itn_route.py` run, proving Python-side dispatch is correct (the real transactional guarantee was proven separately in Task 3).

- [ ] **Step 1: Replace the `_pass_all` helper**

Replace:
```python
def _pass_all(monkeypatch, grants):
    monkeypatch.setattr(pr, "verify_itn_signature", lambda f, p: True)
    monkeypatch.setattr(pr, "is_valid_payfast_ip", lambda ip: True)
    monkeypatch.setattr(pr, "confirm_with_payfast", lambda f: True)
    monkeypatch.setattr(pr, "_load_intent", lambda m: _intent())
    monkeypatch.setattr(pr, "_already_processed", lambda pf: False)
    monkeypatch.setattr(pr, "_claim_intent", lambda *a, **k: True)
    monkeypatch.setattr(pr, "_release_claim", lambda *a, **k: None)
    monkeypatch.setattr(pr, "grant_credits", lambda u, n, t: grants.append(('credits', u, n)))
    monkeypatch.setattr(pr, "activate_license", lambda u, t, tok=None: grants.append(('license', u)))
    monkeypatch.setattr(pr, "grant_seats", lambda u, n, t: grants.append(('seats', u, n)))
```
with:
```python
def _pass_all(monkeypatch, calls):
    """
    calls collects (charge_type, user_id, quantity) tuples appended by the
    mocked _claim_and_grant, standing in for what the real RPC call would
    have granted. Default: 'granted'.
    """
    monkeypatch.setattr(pr, "verify_itn_signature", lambda f, p: True)
    monkeypatch.setattr(pr, "is_valid_payfast_ip", lambda ip: True)
    monkeypatch.setattr(pr, "confirm_with_payfast", lambda f: True)
    monkeypatch.setattr(pr, "_load_intent", lambda m: _intent())
    monkeypatch.setattr(pr, "_already_processed", lambda pf: False)

    def _fake_claim_and_grant(txn_id, pf_payment_id, payload, charge_type,
                               user_id, quantity, payfast_token):
        calls.append((charge_type, user_id, quantity))
        return 'granted'

    monkeypatch.setattr(pr, "_claim_and_grant", _fake_claim_and_grant)
```

- [ ] **Step 2: Update each grant-assertion test to check `calls` instead of `grants`**

Replace the body of each of these tests (the assertion shape changes from
`('credits', 'u1', 1)` / `('license', 'u1')` / `('seats', 'u1', 4)` tuples to
`('tier_1_credits', 'u1', 1)` / `('tier_2_license', 'u1', 1)` /
`('tier_2_seats', 'u1', 4)` — same information, now keyed by the real
`charge_type` string instead of a hand-picked label):

```python
def test_valid_itn_grants_credits(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    resp = _post()
    assert resp.status_code == 200
    assert calls == [('tier_1_credits', 'u1', 1)]


def test_query_param_cannot_override_the_intent(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    _client().post("/api/payfast/notify?type=tier_2_license",
                   data={'m_payment_id': 'm1', 'pf_payment_id': 'pf1',
                         'amount_gross': '450.00', 'payment_status': 'COMPLETE'})
    assert calls == [('tier_1_credits', 'u1', 1)]     # intent wins


def test_custom_str2_cannot_override_the_intent(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    _post({'custom_str2': 'tier_2_license'})
    assert calls == [('tier_1_credits', 'u1', 1)]


def test_seats_grant_uses_intent_quantity(monkeypatch):
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "_load_intent",
                        lambda m: _intent(charge_type='tier_2_seats',
                                          expected_amount='600.00', quantity=4))
    _post({'amount_gross': '600.00', 'custom_int1': '99'})   # lying client
    assert calls == [('tier_2_seats', 'u1', 4)]       # intent quantity, not custom_int1
```

All other tests that used `grants` purely as a "was anything granted" flag
(`test_bad_signature_grants_nothing`, `test_bad_ip_grants_nothing`,
`test_failed_confirmation_grants_nothing`, `test_unknown_intent_grants_nothing`,
`test_amount_mismatch_grants_nothing`, `test_replay_is_idempotent`,
`test_non_complete_status_grants_nothing`,
`test_unknown_charge_type_is_rejected_without_claiming`) need only their
local variable renamed from `grants` to `calls` — the assertions
(`assert grants == []` → `assert calls == []`) are otherwise unchanged.

- [ ] **Step 3: Replace `test_losing_a_concurrent_claim_grants_nothing`**

Replace:
```python
def test_losing_a_concurrent_claim_grants_nothing(monkeypatch):
    # Two ITNs for the same payment can both pass _already_processed before
    # either writes. The atomic claim is what actually prevents a double
    # grant: the loser gets no row back and must not grant.
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "_claim_intent", lambda *a, **k: False)
    resp = _post()
    assert resp.status_code == 200
    assert grants == []
```
with:
```python
def test_losing_a_concurrent_claim_grants_nothing(monkeypatch):
    # Two ITNs for the same payment can both pass _already_processed before
    # either writes. payfast_claim_and_grant (migration 043) is what
    # actually prevents a double grant: it returns 'duplicate' for the
    # loser, at the database layer -- verified directly against a real
    # Postgres in the payfast-atomic-claim-grant design's pre-deploy
    # check, not here. Here we only confirm Python's response to a
    # 'duplicate' result.
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "_claim_and_grant", lambda *a, **k: 'duplicate')
    resp = _post()
    assert resp.status_code == 200
    assert calls == []
```

- [ ] **Step 4: Delete `test_claim_happens_before_granting`**

Remove this test entirely:
```python
def test_claim_happens_before_granting(monkeypatch):
    # Ordering is the whole point: claiming after granting would leave the
    # double-grant window open.
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "_claim_intent",
                        lambda *a, **k: calls.append(('claim',)) or True)
    monkeypatch.setattr(pr, "grant_credits",
                        lambda u, n, t: calls.append(('credits', u, n)))
    _post()
    assert calls == [('claim',), ('credits', 'u1', 1)]
```
There is only one call now (`_claim_and_grant`); claim-before-grant ordering
is a property of the SQL function's internal statement order (migration
043's `UPDATE` before the `IF`/`ELSIF` block), not something Python-level
mocking can observe or usefully assert.

- [ ] **Step 5: Replace `test_failed_grant_releases_the_claim`**

Replace:
```python
def test_failed_grant_releases_the_claim(monkeypatch):
    # If granting blows up we must hand the row back, or PayFast's retry
    # finds it already 'complete' and the user has paid for nothing.
    released = []
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "_release_claim", lambda t: released.append(t))

    def _boom(u, n, t):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(pr, "grant_credits", _boom)
    resp = _post()
    assert resp.status_code == 200      # still 200 — PayFast will retry
    assert released == ['txn-1']
```
with:
```python
def test_grant_failure_still_returns_200(monkeypatch):
    # If the RPC call raises (DB-side failure), the function's own
    # exception has already rolled back any partial writes, including
    # the claim (migration 043) -- there is nothing to release here.
    # We only need to confirm the failure doesn't propagate as a 500,
    # so PayFast retries instead of giving up.
    calls = []
    _pass_all(monkeypatch, calls)

    def _boom(*a, **k):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(pr, "_claim_and_grant", _boom)
    resp = _post()
    assert resp.status_code == 200      # still 200 — PayFast will retry
    assert calls == []
```

- [ ] **Step 6: Update `test_unknown_charge_type_is_rejected_without_claiming`**

This test's `claimed` list tracked calls to `_claim_intent`; since that
function no longer exists, update it to track `_claim_and_grant` instead
(the assertion's intent — validated before any claim/grant call happens —
is unchanged):

```python
def test_unknown_charge_type_is_rejected_without_claiming(monkeypatch):
    claimed = []
    calls = []
    _pass_all(monkeypatch, calls)
    monkeypatch.setattr(pr, "_load_intent",
                        lambda m: _intent(charge_type='free_stuff'))
    monkeypatch.setattr(pr, "_claim_and_grant",
                        lambda *a, **k: claimed.append(1) or 'granted')
    _post()
    assert calls == []
    assert claimed == []                # validated before the row is touched
```

- [ ] **Step 7: Run the full test file**

Run: `cd backend && venv/bin/python -m pytest tests/test_payfast_itn_route.py -v`
Expected: all tests pass (same count as before minus the one deleted test,
`test_claim_happens_before_granting`).

- [ ] **Step 8: Run the full backend suite to confirm no regressions elsewhere**

Run: `cd backend && venv/bin/python -m pytest tests/ -q`
Expected: `426 passed` (427 minus the one deleted test), 0 failed.

- [ ] **Step 9: Commit**

```bash
git add backend/routes/payfast_routes.py backend/tests/test_payfast_itn_route.py
git commit -m "fix(payfast): call the atomic claim-and-grant function from payfast_notify

Replaces the three-step _claim_intent / grant dispatch / _release_claim
orchestration with a single call to payfast_claim_and_grant (migration
043), closing the crash-between-claim-and-grant window. Test suite
rewired to mock the single _claim_and_grant seam instead of the four
separate ones the old two-round-trip flow needed; the transactional
guarantee itself was verified directly against a real local Postgres
(see the design spec) rather than re-asserted here via mocks."
```

---

### Task 5: Update `docs/BACKLOG.md`

**Files:**
- Modify: `docs/BACKLOG.md` — "PayFast ITN: claim-and-grant is not a single transaction" section

**Interfaces:** none (documentation only).

- [ ] **Step 1: Mark the backlog entry resolved**

Update the section header from `## PayFast ITN: claim-and-grant is not a
single transaction` to `## PayFast ITN: claim-and-grant is not a single
transaction — RESOLVED, fixed`, and add a `**Fixed:** 2026-07-21` line plus a
short summary paragraph (matching the style of the other `RESOLVED, fixed`
entries in this file — see "list_members IDOR-shaped gap" for the pattern)
describing: migration 043 added the atomic function, `payfast_routes.py`
rewired to call it, verified against a real local Postgres (each charge
type, duplicate-call, rollback-on-failure, and real concurrent-call
scenarios all passed), and `test_payfast_itn_route.py` updated for the new
single-call seam.

- [ ] **Step 2: Commit**

```bash
git add docs/BACKLOG.md
git commit -m "docs(backlog): mark PayFast atomic claim-and-grant gap resolved"
```

---

## Self-Review Notes

- **Spec coverage:** migration + function ✓ Task 1. Python rewire ✓ Task 2. Real-Postgres verification (all 4 scenarios: per-charge-type grant, duplicate, rollback-on-failure, real concurrency) ✓ Task 3. Test suite rewrite (all seven affected tests plus the two structural changes — deleted test, renamed test) ✓ Task 4. Backlog update ✓ Task 5.
- **Placeholder scan:** none found — every step has literal SQL/Python/commands.
- **Type/name consistency:** `_claim_and_grant` signature
  `(txn_id, pf_payment_id, payload, charge_type, user_id, quantity, payfast_token)`
  used identically in Task 2 (definition), Task 4 (test mocks). RPC param
  names (`p_txn_id`, `p_pf_payment_id`, etc.) match between Task 1 (SQL
  definition) and Task 2 (Python call site). Return values `'granted'` /
  `'duplicate'` used consistently across Tasks 1, 2, 3, and 4.
- **Order dependency:** Task 3 (real-Postgres verification) is placed before
  Task 4 (test rewrite) deliberately — per the user's explicit ask ("test to
  ensure it works before we deploy"), the real transactional guarantee
  should be proven before spending effort updating the mocked test suite
  around it. If Task 3 fails, stop and fix Task 1/2 before touching Task 4.
