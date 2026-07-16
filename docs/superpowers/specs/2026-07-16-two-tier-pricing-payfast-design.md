# Two-Tier Pricing + PayFast — Design Spec

> **Date:** 2026-07-16
> **Status:** Approved design. Implementation plan pending.
> **Scope:** App repo (`ScripDown_AI`) — Flask backend, React frontend, Supabase schema.
> **Upstream:** `slateone/docs/app-repo-handoff-pricing.md`, `slateone/docs/pricing-model-change-spec.md`
> **Business source of truth:** `docs/SPEC_Tiered_Business_Model.md`

## 1. Objective

Replace the deprecated flat $49/month Wise subscription with the confirmed two-tier ZAR model,
wired end-to-end: landing redirect → signup → in-app PayFast checkout → ITN → entitlement → gating.

| Tier param | `signup_plan` id | Name | Price (ZAR, VAT-inclusive) | Billing | Teams |
|---|---|---|---|---|---|
| `tier_1` | `tier_1_pay_per_breakdown` | Pay-Per-Breakdown | R450 / breakdown | One-off, prepaid credits | ✕ |
| `tier_2` | `tier_2_annual_team` | Annual Team License | R1,850 / yr + R150 / seat | Annual subscription + one-off seats | ✓ |

Constraints: ZAR only. No free tier, no trial. No "AI" wording in user-facing copy — use
"breakdown" / "script analysis". Uploads and manual scene work are always free; only a
**breakdown** is billable.

## 2. Decisions

Resolving the open questions in the handoff (§6) and business spec (§9):

| Question | Decision |
|---|---|
| Tier 1 model | **Prepaid credit balance.** User buys N breakdowns; balance spent when a breakdown runs. Decouples payment from the analysis request so a PayFast round-trip never blocks a job. |
| Breakdown unit | **One charge per script, ever.** Preserves existing `track_breakdown_usage` semantics. Re-analysis after edits is free. Explicitly overrides business spec §3.1. |
| Seat billing | **Separate one-off purchases.** R1,850 recurring; seats are one-off R150 × qty, expiring with the license term. Proration deferred to Phase 2. |
| VAT | **Inclusive.** R450 is what the customer pays; PayFast `amount=450.00`. VAT backed out for invoicing. |
| Failed renewal | **Downgrade to Tier 1, team features read-only.** Per business spec §8.2. |
| Legacy users | **None exist.** `trial` / `monthly` dropped from the constraint. |
| Existing paywall holes | **Fixed as part of this work.** See §7. |
| Merchant account | **New PayFast account for SlateOne** (prerequisite — see §9). |

## 3. Verified starting state

Findings from code exploration and the PayFast dashboard. Several correct errors in the handoff.

### 3.1 Code

- Migrations live in `backend/db/migrations/`, `NNN_snake_case.sql`, applied **by hand** — no runner,
  no ledger. Highest is `040_timeline_segments.sql`. (Handoff wrongly implies `supabase/migrations/`.)
- `can_upload_script()` is already a stub returning `True` (`services/subscription_service.py:270`)
  — "Uploads are always free — the paywall is at analysis time." Handoff §3.1's ask is already done.
- `script_upload_limit` / `scripts_uploaded` are vestigial: written by `set-plan`, never read,
  never incremented. The SQL `can_upload_script` / `increment_script_upload` (019) have zero callers.
- `subscription_plan` CHECK is `('trial','monthly')` (`032:10-11`); `signup_plan` has **no CHECK**.
  Two different vocabularies for "plan" on one table.
- Billing is already tracked per-script and idempotently: `track_breakdown_usage`
  (`services/credit_service.py:249`), UNIQUE on `script_id` "prevents double-counting".
- `services/subscription_service.py:482` defines `require_active_subscription` — **dead and broken**:
  reads `g.user_id`, which `middleware/auth.py` never sets, so it fails **open**. Not imported anywhere.
- `credit_bp` is genuinely unregistered (`app.py:17,52`), but `credit_service.track_breakdown_usage`
  is still imported and writing to the deprecated tables on the live analysis path
  (`supabase_routes.py:2785`, `:3134`).
- `frontend/src/hooks/useCredits.js` calls five routes that all 404. Zero importers. Dead.

### 3.2 PayFast dashboard (merchant `33568687`)

- Account is **"Film Resource Africa"** — a *different product*. SlateOne's buttons were generated
  inside it. Fallback Notify URL points at `https://film-resource-africa.com/api/payfast/itn`.
- A **Security Passphrase is set**. Dashboard notes this "would automatically enable subscriptions" —
  which is what makes the Tier 2 annual charge possible.
- **Payment Page Settings → "Enable require signature" is OFF.** This is the live vulnerability:
  PayFast currently accepts unsigned `_paynow` requests.
- ITN Status: **On**. Dashboard text: *"This setting will be overridden if your eCommerce platform
  sends this information with the payments integration"* — so **per-transaction `notify_url` wins**,
  and the query-param discriminator works. (Resolves the handoff's §6.5 open question.)

### 3.3 Why the supplied PayFast snippets are unusable

The snippets in `pricing-model-change-spec.md` §6.4 use `cmd=_paynow` + `receiver=` — the **Pay Now
button** integration, not Custom Integration. They contain no `merchant_id`, no `merchant_key`, and
**no `signature`**. Consequences:

1. **Amount is set by browser JavaScript** — `formReference['amount'].value * custom_quantity` —
   with nothing binding it server-side. The `custom_quantity` input has no `min`/`step`, so a
   devtools edit buys a breakdown for cents. With `require signature` off, PayFast accepts it.
2. **No attribution.** No `custom_str1`, no `m_payment_id`. The ITN's only identifier is the payer's
   *PayFast account* email, which routinely differs from their SlateOne login. This is the same
   weakness that makes `supabase/functions/process-beta-payment` forgeable.
3. The shareable `payf.st` links cannot carry `custom_str1` at all.

**Therefore:** all three charges are regenerated as signed Custom Integration forms. The `payf.st`
links and `_paynow` snippets are retained only for manual/email use, never for the in-app flow.

## 4. Data model

Migration `041_two_tier_pricing.sql` (next free number; applied by hand per repo convention).

### 4.1 `profiles` changes

- `subscription_plan` CHECK → `('none','tier_1_pay_per_breakdown','tier_2_annual_team')`, default `'none'`.
  `trial` / `monthly` dropped (no real legacy users).
- `subscription_status` CHECK → `('none','active','expired','cancelled')`, default `'none'`.
  **`'none'` is the real state for signed-up-but-unpaid** — with no free tier, `'trial'` is meaningless.
- `signup_plan` gains the CHECK it never had: `('tier_1_pay_per_breakdown','tier_2_annual_team')` or NULL.
- **Drop** `script_upload_limit`, `scripts_uploaded` (vestigial).
- No seat column on `profiles` — seats live in `account_seats` (§4.4) so grants carry a term.

### 4.2 `payfast_transactions` — intent + ITN ledger

Every checkout creates a row *before* the user leaves. The ITN reconciles against it.

| Column | Notes |
|---|---|
| `id` | uuid pk |
| `m_payment_id` | uuid, **UNIQUE** — our id, sent to PayFast, used for ITN lookup |
| `pf_payment_id` | text, **UNIQUE NULLABLE** — PayFast's id; the idempotency key |
| `user_id` | fk profiles |
| `charge_type` | `('tier_1_credits','tier_2_license','tier_2_seats')` |
| `expected_amount` | numeric — **server-computed**; the ITN must match this |
| `quantity` | int — credits or seats purchased |
| `status` | `('pending','complete','failed','cancelled')` |
| `raw_payload` | jsonb — full ITN body, for audit/dispute |
| `created_at` / `updated_at` | |

This is what makes amount tampering structurally impossible rather than a check we must remember.

### 4.3 `breakdown_credits` — append-only ledger

| Column | Notes |
|---|---|
| `id` | uuid pk |
| `user_id` | fk profiles |
| `delta` | int — `+N` purchased, `-1` spent |
| `script_id` | uuid nullable — set on spend rows |
| `payfast_transaction_id` | fk nullable — set on purchase rows |
| `reason` | text |
| `created_at` | |

Balance is `SUM(delta)`. Append-only beats a mutable counter: auditable, and no lost-update race.

**Key invariant, enforced by the database:**

```sql
CREATE UNIQUE INDEX breakdown_credits_one_charge_per_script
  ON breakdown_credits (user_id, script_id)
  WHERE delta < 0;
```

This makes "one charge per script, ever" a schema guarantee rather than application logic — and
makes *retry-failed-scenes free automatically*, since the spend row already exists.

### 4.4 `account_seats`

| Column | Notes |
|---|---|
| `id` | uuid pk |
| `owner_id` | fk profiles — the Tier 2 account owner |
| `seats_granted` | int |
| `payfast_transaction_id` | fk |
| `term_expires_at` | timestamptz — seats expire with the license |
| `created_at` | |

Paid seats = `SUM(seats_granted)` where `term_expires_at > now()`. Used seats = accepted invites.

### 4.5 Retirements

Dropped in this migration: `script_credit_purchases`, `script_credit_usage`, functions
`deduct_script_credit`, `add_script_credits`, `activate_monthly_subscription` (SQL copy, dead).
Deleted in code: `routes/credit_routes.py`, `services/credit_service.py`,
`frontend/src/hooks/useCredits.js`, and the `track_breakdown_usage` calls at
`supabase_routes.py:2785` / `:3134`. The new ledger supersedes all of it.

## 5. Entitlement service

New `backend/services/entitlement_service.py` — the single source of truth, replacing the three
copy-pasted `status != 'active'` checks and the dead `require_active_subscription`.

```
get_entitlement(user_id) -> {
  tier, status, breakdown_balance, seats_paid, seats_used,
  can_run_breakdown, can_use_teams
}
```

- `consume_breakdown(user_id, script_id)` — atomic. Active Tier 2 → no-op (unlimited).
  Tier 1 → insert a `-1` row; the unique index makes a re-charge a no-op, not an error.
  Zero balance → raise.
- `grant_credits(user_id, n, txn_id)` / `activate_license(user_id, txn_id)` /
  `grant_seats(owner_id, n, txn_id)` — called only by the ITN handler.
- Decorators `@require_breakdown_entitlement`, `@require_team_tier` — read `get_user_id()` from
  `middleware/auth.py` and **fail closed** (the specific bug in the old decorator).

Tier 2 downgrade on failed renewal: `status='expired'` → `can_use_teams` false for writes, true for
reads. Team endpoints become read-only rather than 403 (business spec §8.2).

## 6. PayFast integration

New `backend/services/payfast_service.py` and `backend/routes/payfast_routes.py`.

### 6.1 Checkout — `POST /api/billing/checkout`

Auth required. Body `{charge_type, quantity}`. Server:
1. Computes `expected_amount` from a server-side price table (never the client).
2. Inserts a `payfast_transactions` row, `status='pending'`, with a generated `m_payment_id`.
3. Returns signed form fields for `https://payment.payfast.io/eng/process`.

Fields: `merchant_id`, `merchant_key`, `m_payment_id`, `amount`, `item_name`, `item_description`,
`return_url`, `cancel_url`, `notify_url`, `custom_str1 = user_id`, `custom_str2 = charge_type`,
`signature`. Tier 2 license adds `subscription_type=1`, `recurring_amount=1850`, `cycles=0`,
`frequency=6`.

**Quantity lives in our UI**, not PayFast's form. No client-side amount arithmetic anywhere.

Signature: MD5 over params in submission order, URL-encoded (uppercase hex, spaces as `+`), with
`&passphrase=<PAYFAST_PASSPHRASE>` appended.

### 6.2 ITN — `POST /api/payfast/notify`

Unauthenticated by necessity (PayFast calls it). Validation chain, **all must pass before any grant**:

1. **Signature** — recompute over received params in received order + passphrase.
2. **Source IP** — resolve PayFast's hosts (`www.payfast.co.za`, `sandbox.payfast.co.za`,
   `w1w.payfast.co.za`, `w2w.payfast.co.za`) and require a match.
3. **Intent match** — look up `m_payment_id`. Must exist. `amount_gross` must equal
   `expected_amount` (±0.01).
4. **Server confirmation** — POST the payload back to PayFast's `/eng/query/validate`; require `VALID`.

Then: dedupe on `pf_payment_id` (UNIQUE — a retry is a no-op), persist `raw_payload`, set
`status='complete'`, and grant via the entitlement service.

**The charge type and amount come from the intent row, never from the request.** The endpoint is
public, so `?plan=tier_2` on the URL and `custom_str2` in the body are attacker-controllable —
they are routing/debug conveniences only. This is precisely the mistake that makes the old beta
payment function forgeable.

Always return HTTP 200 after processing, or PayFast retries indefinitely.

Recurring renewals arrive as further ITNs against the same subscription; they extend
`subscription_expires_at`. A failed renewal ITN triggers the §5 downgrade.

### 6.3 Config

New env vars, gated in `utils/env_validator.py`: `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`,
`PAYFAST_PASSPHRASE`, `PAYFAST_SANDBOX`, `PAYFAST_RETURN_URL`, `PAYFAST_CANCEL_URL`,
`PAYFAST_NOTIFY_URL`. **No credential values in this repo or in any doc.**

## 7. Gating and security fixes

### 7.1 Breakdown gate

Chokepoint: the three live route entrypoints in `routes/supabase_routes.py` — `:2748` (single scene),
`:3098` (bulk), `:3183` (retry-failed). The route layer is where `user_id` exists; per-script
idempotency means the bulk worker thread needs no gate of its own, and retry is free by construction.

Note `extraction_pipeline.py` is **not** on the AI path (PDF parsing only) and
`analysis_queue_service.py` serves the legacy path only — neither is a gate site, contrary to the
handoff's framing.

### 7.2 Team gate

`@require_team_tier` on `routes/invite_routes.py:67` (`create_invite`, the natural chokepoint),
plus the invite/member list and delete routes. Seat check: an owner may hold at most `seats_paid`
accepted members. `GET /api/invite/departments` (`:61`) and `GET /api/departments`
(`supabase_routes.py:3930`) currently have **no decorator** — they get `@require_auth`.

There are **no `/threads` or `/workspace` backend routes** (the handoff assumes them); the
`DepartmentWorkspace.jsx` routes in `App.jsx` are commented out. Notes go via
`/api/scripts/<id>/notes` (`supabase_routes.py:3944`) — gated too.

### 7.3 Pre-existing holes closed here

1. **Anonymous bypass.** Analysis routes are `@optional_auth` with the gate nested under
   `if user_id:` — an unauthenticated request skips the paywall entirely. → `@require_auth`,
   unconditional check.
2. **Ungated legacy path.** `routes/script_routes.py` (`:85, :98, :352, :432, :489, :557, :617`) and
   `routes/analysis_routes.py` (`:70, :102, :243, :279`) trigger AI with no gate. → Delete the
   blueprints if unused (verify no live callers first), else gate them.
3. **`set-plan` account takeover.** `routes/auth_routes.py:202` has no `@require_auth` and takes
   `user_id` from the request **body** — anyone can rewrite any user's plan. → `@require_auth`,
   `user_id` from the token only. Also stop overwriting `created_at` on upsert (`:302`), which
   currently resets account age.
4. **Forgeable beta payments.** `supabase/functions/process-beta-payment` is an unauthenticated
   `Deno.serve` with `Allow-Origin: *` and no signature check. → Delete; the beta is over.
5. **`DEV_MODE` auth bypass** (`middleware/auth.py:29`) grants a synthetic user when
   `FLASK_ENV=development`. Out of scope to remove, but must never be set on Railway — assert in
   `env_validator.py`.

## 8. Frontend

- **Signup plan mapping.** `plan` is read in `context/AuthContext.jsx:229` (not `LoginPage`), stashed
  as `localStorage['pending_profile_plan']`, POSTed to `/api/auth/set-plan` after email verification.
  Map `tier_1`/`tier_2` → full ids there and in `auth_routes.py:236` `VALID_PLANS`. Verify the param
  survives `/auth/callback?type=signup` → `/login?mode=signup&verified=true`.
- **`BillingPage`** — tier-appropriate checkout. Tier 1: quantity picker (1/5/10) → server total.
  Tier 2: license + seat purchase. Posts the server-signed form to PayFast.
- **`/payment/success` + `/payment/cancel`** in `App.jsx` (the old `PaymentSuccessPage` route at
  `:128` is commented out and used a different path). **UX only** — they refetch entitlement and may
  show "processing" until the ITN lands. They never grant access.
- **`useSubscription` → `useEntitlement`** — balance, tier, seats. Remove the `PHASE1_FREE_ACCESS`
  kill switch from both `frontend/src/hooks/useSubscription.js:13` and
  `services/subscription_service.py:15` (two independent constants that must agree).
- Tier 1 team UI: upsell, not a dead button. Tier 2: seat management in settings.
- Delete `frontend/src/hooks/useCredits.js`.

## 9. PayFast account — resolved 2026-07-16

Merchant `33568687` was originally Film Resource Africa's. **FRA is retired with no live payments**,
so the account was renamed to "SlateOne" and reused rather than split. The merchant ID and key are
unchanged from FRA's — worth knowing when reading old FRA records, and note the account's transaction
history (3 txns, R423) is FRA's, not SlateOne's.

Dashboard configuration is **done and verified**:

| Setting | State |
|---|---|
| ITN Status | On |
| Notify URL | `https://api.slateone.studio/api/payfast/notify` (was `film-resource-africa.com/api/payfast/itn`) |
| Enable require signature | **On** — closes §3.3's tampering hole |
| Security Passphrase | Set |

Consequence: **PayFast now rejects unsigned requests.** The `_paynow` snippets and `payf.st` links in
`pricing-model-change-spec.md` §6.4 no longer work and must not be revived — §6.1's signed
server-generated forms are the only supported path.

**Outstanding:**
- The merchant key and passphrase were displayed in plaintext during the browser session that
  configured this, so they are considered exposed. **Rotate both**, then set
  `PAYFAST_MERCHANT_KEY` / `PAYFAST_PASSPHRASE` in Railway. Nothing live depends on the current
  values, so rotation is free right now and gets expensive later.
- Verify the passphrase in Railway matches the dashboard exactly — a trailing space silently breaks
  every signature.

## 10. Testing

- **Unit (pytest):** signature generation against a known-good vector; ITN rejection on bad
  signature / wrong IP / amount mismatch / unknown `m_payment_id`; idempotency (same `pf_payment_id`
  twice → one grant); the one-charge-per-script index; `consume_breakdown` at zero balance;
  Tier 2 unlimited; decorators fail closed with no user.
- **Adversarial:** replay an ITN; POST `/api/payfast/notify?plan=tier_2` directly with no signature;
  attempt analysis unauthenticated; call `set-plan` with someone else's `user_id`. All must fail.
- **E2E (PayFast sandbox):** signup `plan=tier_2` → checkout → sandbox pay → ITN → entitlement →
  team features unlock. Repeat for Tier 1 credits and seats.
- **Gates:** `cd backend && pytest tests/` and `cd frontend && npm run build`.
  `npm run lint` is broken repo-wide — do not gate on it.

## 11. Build sequence

1. Migration `041` — schema, constraints, new tables, retirements. (§4)
2. `entitlement_service.py` + decorators, with tests. (§5)
3. `payfast_service.py` signature/validation, with tests. (§6)
4. `POST /api/payfast/notify` — before checkout, so payments register when they arrive. (§6.2)
5. `POST /api/billing/checkout`. (§6.1)
6. Security fixes §7.3 — independent of the rest; land early.
7. Gating: breakdown + team. (§7.1, §7.2)
8. Frontend: signup mapping, `BillingPage`, payment result routes, entitlement hook. (§8)
9. E2E against sandbox once the new merchant account exists. (§9)

## 12. Out of scope (Phase 2)

Seat proration mid-cycle; refund/credit policy for failed analyses; volume discounts on credit packs;
non-profit/student pricing; invoicing/VAT documents; a grace period before downgrade (needs cron —
none exists in the backend today).
