# Two-Tier Pricing + PayFast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the confirmed two-tier ZAR pricing model end-to-end — landing redirect → signup → in-app PayFast checkout → ITN → entitlement → server-side gating.

**Architecture:** Payment intents are created server-side before the user leaves for PayFast, so the ITN validates the amount against our own record rather than a client-supplied param. Entitlement is an append-only credit ledger whose invariants are enforced by database constraints, not application code. One new `entitlement_service` becomes the single source of truth, replacing three copy-pasted subscription checks and a dead fail-open decorator.

**Tech Stack:** Flask 3 (Python 3.13), Supabase Postgres via `supabase-py` (service role), React 18 + Vite (plain JSX), PayFast Custom Integration, pytest.

**Spec:** `docs/superpowers/specs/2026-07-16-two-tier-pricing-payfast-design.md` — read it before starting.

## Global Constraints

- **Currency: ZAR only.** No free tier, no trial. Prices are **VAT-inclusive**: R450 / breakdown, R1,850 / yr, R150 / seat.
- **No "AI" wording in user-facing copy** (product-owner directive). Use "breakdown" / "script analysis". This applies to UI strings, error messages, and PayFast `item_name` / `item_description`. Internal code identifiers are exempt.
- **One charge per script, ever.** Re-analysis after edits is free. This deliberately overrides business spec §3.1.
- **Never grant entitlement from a browser return URL.** Only a validated ITN grants.
- **Never trust `amount`, `plan`, or `custom_str2` from a request.** They come from the intent row.
- Migrations live in `backend/db/migrations/NNN_name.sql` and are **applied by hand** — there is no runner. The plan does not automate application.
- Backend gate: `cd backend && pytest tests/`. Frontend gate: `cd frontend && npm run build`. **`npm run lint` is broken repo-wide — do not gate on it.**
- Tests use `monkeypatch` + `app.test_client()`. There is no `conftest.py`; each test file does `sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))`.
- Supabase access is via `from db.supabase_client import get_supabase_admin` (service role, bypasses RLS).
- Never commit PayFast credentials. They are already set in Railway as `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE`.

## Prerequisites (already done — do not redo)

- PayFast merchant `33568687` renamed to SlateOne; FRA retired. `require signature` **On**, ITN **On**, Notify URL `https://api.slateone.studio/api/payfast/notify`, passphrase set.
- **Consequence:** PayFast rejects unsigned requests. The `_paynow` snippets and `payf.st` links in `slateone/docs/pricing-model-change-spec.md` §6.4 are dead. Do not revive them.

---

### Task 1: Migration 041 — schema

**Files:**
- Create: `backend/db/migrations/041_two_tier_pricing.sql`

**Interfaces:**
- Produces: tables `payfast_transactions`, `breakdown_credits`, `account_seats`; `profiles.subscription_plan` / `subscription_status` accepting the new tier vocabulary.

- [ ] **Step 1: Write the migration**

```sql
-- Migration: Two-Tier Pricing + PayFast
-- Description: tier_1 pay-per-breakdown (prepaid credits) + tier_2 annual team license
--              with per-seat purchases. Retires the credit-pack and Wise-monthly systems.
-- Date: 2026-07-16

-- ============================================
-- 1. profiles — new plan vocabulary
-- ============================================
-- No real legacy users exist, so 'trial'/'monthly' are dropped outright.
-- 'none' is the real state for signed-up-but-unpaid: there is no free tier.

ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_subscription_plan_check;
UPDATE profiles SET subscription_plan = 'none'
    WHERE subscription_plan IS NULL OR subscription_plan IN ('trial', 'monthly');
ALTER TABLE profiles ALTER COLUMN subscription_plan SET DEFAULT 'none';
ALTER TABLE profiles ADD CONSTRAINT profiles_subscription_plan_check
    CHECK (subscription_plan IN ('none', 'tier_1_pay_per_breakdown', 'tier_2_annual_team'));

ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_subscription_status_check;
UPDATE profiles SET subscription_status = 'none'
    WHERE subscription_status IS NULL OR subscription_status = 'trial';
ALTER TABLE profiles ALTER COLUMN subscription_status SET DEFAULT 'none';
ALTER TABLE profiles ADD CONSTRAINT profiles_subscription_status_check
    CHECK (subscription_status IN ('none', 'active', 'expired', 'cancelled'));

-- signup_plan has never had a constraint; give it one.
UPDATE profiles SET signup_plan = NULL
    WHERE signup_plan IS NOT NULL
      AND signup_plan NOT IN ('tier_1_pay_per_breakdown', 'tier_2_annual_team');
ALTER TABLE profiles ADD CONSTRAINT profiles_signup_plan_check
    CHECK (signup_plan IS NULL OR signup_plan IN ('tier_1_pay_per_breakdown', 'tier_2_annual_team'));

-- Vestigial: written by set-plan, never read, never incremented.
ALTER TABLE profiles DROP COLUMN IF EXISTS script_upload_limit;
ALTER TABLE profiles DROP COLUMN IF EXISTS scripts_uploaded;

COMMENT ON COLUMN profiles.subscription_plan IS 'none | tier_1_pay_per_breakdown | tier_2_annual_team';
COMMENT ON COLUMN profiles.subscription_status IS 'none | active | expired | cancelled';

-- ============================================
-- 2. payfast_transactions — intent + ITN ledger
-- ============================================
CREATE TABLE IF NOT EXISTS payfast_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    m_payment_id UUID NOT NULL UNIQUE,
    pf_payment_id TEXT UNIQUE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    charge_type TEXT NOT NULL
        CHECK (charge_type IN ('tier_1_credits', 'tier_2_license', 'tier_2_seats')),
    expected_amount NUMERIC(10,2) NOT NULL CHECK (expected_amount > 0),
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'complete', 'failed', 'cancelled')),
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payfast_transactions_user ON payfast_transactions(user_id);

COMMENT ON COLUMN payfast_transactions.expected_amount IS
    'Server-computed. The ITN amount_gross must match this — never trust the request.';
COMMENT ON COLUMN payfast_transactions.pf_payment_id IS
    'PayFast payment id. UNIQUE = the ITN idempotency key.';

-- ============================================
-- 3. breakdown_credits — append-only ledger
-- ============================================
CREATE TABLE IF NOT EXISTS breakdown_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    delta INTEGER NOT NULL CHECK (delta <> 0),
    script_id UUID REFERENCES scripts(id) ON DELETE SET NULL,
    payfast_transaction_id UUID REFERENCES payfast_transactions(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_breakdown_credits_user ON breakdown_credits(user_id);

-- THE core invariant: one charge per script, ever. Enforced by the database,
-- not application code. Also makes retry-failed-scenes free by construction.
CREATE UNIQUE INDEX IF NOT EXISTS breakdown_credits_one_charge_per_script
    ON breakdown_credits (user_id, script_id)
    WHERE delta < 0;

-- ============================================
-- 4. account_seats — seat grants with a term
-- ============================================
CREATE TABLE IF NOT EXISTS account_seats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    seats_granted INTEGER NOT NULL CHECK (seats_granted > 0),
    payfast_transaction_id UUID REFERENCES payfast_transactions(id) ON DELETE SET NULL,
    term_expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_account_seats_owner ON account_seats(owner_id);

-- ============================================
-- 5. Retire the credit-pack and Wise-monthly systems
-- ============================================
DROP FUNCTION IF EXISTS deduct_script_credit(UUID, UUID, TEXT);
DROP FUNCTION IF EXISTS add_script_credits(UUID, INTEGER, TEXT);
DROP FUNCTION IF EXISTS activate_monthly_subscription(UUID);
DROP FUNCTION IF EXISTS can_upload_script(UUID);
DROP FUNCTION IF EXISTS increment_script_upload(UUID);
DROP TABLE IF EXISTS script_credit_usage;
DROP TABLE IF EXISTS script_credit_purchases;

ALTER TABLE profiles DROP COLUMN IF EXISTS script_credits;
ALTER TABLE profiles DROP COLUMN IF EXISTS total_scripts_purchased;
```

- [ ] **Step 2: Verify the SQL parses**

There is no migration runner and no local Postgres. Verify by eye against the spec §4, then confirm the file is syntactically plausible:

Run: `python3 -c "import pathlib; s=pathlib.Path('backend/db/migrations/041_two_tier_pricing.sql').read_text(); print(f'{len(s)} chars, {s.count(chr(59))} statements')"`
Expected: a non-zero char count and ~30 statements.

- [ ] **Step 3: STOP — hand off to the human**

Migrations are applied by hand against Supabase. **Do not attempt to apply it.** Report to the human:

> Migration `041_two_tier_pricing.sql` is ready. Apply it in the Supabase SQL editor, then confirm — later tasks assume the tables exist.

Ask them to confirm `scripts(id)` is the correct FK target for `breakdown_credits.script_id` before applying; if the scripts table is named differently, fix the FK first.

- [ ] **Step 4: Commit**

```bash
git add backend/db/migrations/041_two_tier_pricing.sql
git commit -m "feat(billing): migration 041 — two-tier pricing schema"
```

---

### Task 2: PayFast signature generation

**Files:**
- Create: `backend/services/payfast_service.py`
- Test: `backend/tests/test_payfast_signature.py`

**Interfaces:**
- Produces: `generate_signature(fields: dict, passphrase: str | None) -> str` — MD5 hex digest.
- Produces: `PRICES: dict[str, Decimal]` — `{'tier_1_credits': 450, 'tier_2_license': 1850, 'tier_2_seats': 150}`.

**Why this is its own task:** the signature is pure, deterministic, and the single point where a subtle bug silently breaks every payment. It gets tested in isolation before anything depends on it.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_payfast_signature.py`:

```python
"""PayFast signature generation — order-sensitive MD5 over urlencoded fields."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import hashlib
from urllib.parse import quote_plus

from services.payfast_service import generate_signature


def _expected(pairs, passphrase=None):
    payload = "&".join(f"{k}={quote_plus(str(v))}" for k, v in pairs)
    if passphrase:
        payload += f"&passphrase={quote_plus(passphrase)}"
    return hashlib.md5(payload.encode()).hexdigest()


def test_signature_matches_urlencoded_md5():
    fields = {"merchant_id": "33568687", "amount": "450.00", "item_name": "Breakdown"}
    assert generate_signature(fields, None) == _expected(list(fields.items()))


def test_passphrase_is_appended_last():
    fields = {"merchant_id": "33568687", "amount": "450.00"}
    got = generate_signature(fields, "Secret-Pass-1")
    assert got == _expected(list(fields.items()), "Secret-Pass-1")
    assert got != generate_signature(fields, None)


def test_field_order_is_significant():
    a = generate_signature({"b": "2", "a": "1"}, None)
    b = generate_signature({"a": "1", "b": "2"}, None)
    assert a != b


def test_empty_values_are_excluded():
    # PayFast excludes empty fields from the signature payload entirely.
    with_empty = generate_signature({"a": "1", "b": "", "c": "3"}, None)
    without = generate_signature({"a": "1", "c": "3"}, None)
    assert with_empty == without


def test_spaces_encode_as_plus_and_hex_is_uppercase():
    sig = generate_signature({"item_name": "Team License"}, None)
    assert sig == hashlib.md5(b"item_name=Team+License").hexdigest()
    # Slashes must be %2F (uppercase), not %2f.
    sig2 = generate_signature({"url": "a/b"}, None)
    assert sig2 == hashlib.md5(b"url=a%2Fb").hexdigest()


def test_values_are_stripped():
    # A trailing space in the passphrase is a classic PayFast footgun.
    assert generate_signature({"a": " 1 "}, None) == generate_signature({"a": "1"}, None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_payfast_signature.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.payfast_service'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/services/payfast_service.py`:

```python
"""
PayFast Custom Integration for SlateOne.

Signed server-generated checkout forms + ITN validation. The dashboard's
Pay Now buttons are NOT usable: `require signature` is enabled on merchant
33568687, and unsigned requests are rejected.
"""

import hashlib
import os
from decimal import Decimal
from urllib.parse import quote_plus

# ZAR, VAT-inclusive. The only authority on price — never take an amount from a client.
PRICES = {
    'tier_1_credits': Decimal('450.00'),   # per breakdown
    'tier_2_license': Decimal('1850.00'),  # per year
    'tier_2_seats': Decimal('150.00'),     # per seat
}


def generate_signature(fields: dict, passphrase: str | None) -> str:
    """
    MD5 over `key=urlencoded_value` pairs joined by '&', in the given order,
    with `&passphrase=...` appended last.

    Order is significant and empty values are excluded — both are PayFast
    requirements, not choices. Values are stripped: a stray trailing space
    silently breaks every signature.
    """
    parts = []
    for key, value in fields.items():
        text = str(value).strip()
        if text == '':
            continue
        parts.append(f"{key}={quote_plus(text)}")

    payload = "&".join(parts)
    if passphrase:
        payload += f"&passphrase={quote_plus(passphrase.strip())}"

    return hashlib.md5(payload.encode()).hexdigest()
```

Note: Python's `quote_plus` already emits uppercase hex (`%2F`) and encodes spaces as `+`, which is exactly what PayFast expects — no post-processing needed. The test pins this so a future refactor can't regress it.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_payfast_signature.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/payfast_service.py backend/tests/test_payfast_signature.py
git commit -m "feat(billing): PayFast signature generation"
```

---

### Task 3: PayFast ITN validation

**Files:**
- Modify: `backend/services/payfast_service.py`
- Test: `backend/tests/test_payfast_itn_validation.py`

**Interfaces:**
- Consumes: `generate_signature` (Task 2).
- Produces: `verify_itn_signature(form: dict, passphrase: str | None) -> bool`
- Produces: `is_valid_payfast_ip(ip: str) -> bool`
- Produces: `confirm_with_payfast(form: dict) -> bool`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_payfast_itn_validation.py`:

```python
"""ITN validation: signature over received order, PayFast source IP, server confirmation."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.payfast_service as pf


def test_valid_signature_accepted():
    form = {"pf_payment_id": "1", "amount_gross": "450.00"}
    form["signature"] = pf.generate_signature(form, "pass")
    assert pf.verify_itn_signature(form, "pass") is True


def test_tampered_amount_rejected():
    form = {"pf_payment_id": "1", "amount_gross": "450.00"}
    form["signature"] = pf.generate_signature(form, "pass")
    form["amount_gross"] = "1.00"
    assert pf.verify_itn_signature(form, "pass") is False


def test_missing_signature_rejected():
    assert pf.verify_itn_signature({"pf_payment_id": "1"}, "pass") is False


def test_wrong_passphrase_rejected():
    form = {"pf_payment_id": "1"}
    form["signature"] = pf.generate_signature(form, "pass")
    assert pf.verify_itn_signature(form, "other") is False


def test_signature_excluded_from_its_own_payload():
    # The signature field must not be part of the string it signs.
    form = {"a": "1", "b": "2"}
    sig = pf.generate_signature(form, None)
    form["signature"] = sig
    assert pf.verify_itn_signature(form, None) is True


def test_valid_ip_accepted(monkeypatch):
    monkeypatch.setattr(pf, "_resolve_payfast_ips", lambda: {"1.2.3.4", "5.6.7.8"})
    assert pf.is_valid_payfast_ip("1.2.3.4") is True


def test_unknown_ip_rejected(monkeypatch):
    monkeypatch.setattr(pf, "_resolve_payfast_ips", lambda: {"1.2.3.4"})
    assert pf.is_valid_payfast_ip("9.9.9.9") is False


def test_dns_failure_fails_closed(monkeypatch):
    def boom():
        raise OSError("dns down")
    monkeypatch.setattr(pf, "_resolve_payfast_ips", boom)
    assert pf.is_valid_payfast_ip("1.2.3.4") is False


def test_confirm_returns_true_on_valid(monkeypatch):
    class Resp:
        status_code = 200
        text = "VALID"
    monkeypatch.setattr(pf.requests, "post", lambda *a, **k: Resp())
    assert pf.confirm_with_payfast({"a": "1"}) is True


def test_confirm_returns_false_on_invalid(monkeypatch):
    class Resp:
        status_code = 200
        text = "INVALID"
    monkeypatch.setattr(pf.requests, "post", lambda *a, **k: Resp())
    assert pf.confirm_with_payfast({"a": "1"}) is False


def test_confirm_fails_closed_on_exception(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(pf.requests, "post", boom)
    assert pf.confirm_with_payfast({"a": "1"}) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_payfast_itn_validation.py -v`
Expected: FAIL — `AttributeError: module 'services.payfast_service' has no attribute 'verify_itn_signature'`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/services/payfast_service.py`:

```python
import socket
import requests

PAYFAST_HOSTS = [
    'www.payfast.co.za',
    'sandbox.payfast.co.za',
    'w1w.payfast.co.za',
    'w2w.payfast.co.za',
    'payment.payfast.io',
]

VALIDATE_URL = os.getenv(
    'PAYFAST_VALIDATE_URL',
    'https://sandbox.payfast.co.za/eng/query/validate'
    if os.getenv('PAYFAST_SANDBOX', 'false').lower() == 'true'
    else 'https://www.payfast.co.za/eng/query/validate'
)


def verify_itn_signature(form: dict, passphrase: str | None) -> bool:
    """
    Recompute the signature over the received fields, in received order,
    excluding `signature` itself.
    """
    received = form.get('signature')
    if not received:
        return False
    payload = {k: v for k, v in form.items() if k != 'signature'}
    return generate_signature(payload, passphrase) == received


def _resolve_payfast_ips() -> set:
    """Resolve PayFast's ITN source hosts. Separated for test injection."""
    ips = set()
    for host in PAYFAST_HOSTS:
        for info in socket.getaddrinfo(host, 443):
            ips.add(info[4][0])
    return ips


def is_valid_payfast_ip(ip: str) -> bool:
    """Fails closed: a DNS failure means we cannot prove the source, so we reject."""
    try:
        return ip in _resolve_payfast_ips()
    except Exception:
        return False


def confirm_with_payfast(form: dict) -> bool:
    """
    Server-to-server confirmation. Fails closed on any error — an
    unconfirmable payment must never grant entitlement.
    """
    payload = {k: v for k, v in form.items() if k != 'signature'}
    try:
        resp = requests.post(VALIDATE_URL, data=payload, timeout=10)
        return resp.status_code == 200 and resp.text.strip().startswith('VALID')
    except Exception:
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_payfast_itn_validation.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/payfast_service.py backend/tests/test_payfast_itn_validation.py
git commit -m "feat(billing): PayFast ITN validation (signature, source IP, confirmation)"
```

---

### Task 4: Checkout field builder

**Files:**
- Modify: `backend/services/payfast_service.py`
- Test: `backend/tests/test_payfast_checkout_fields.py`

**Interfaces:**
- Consumes: `generate_signature`, `PRICES`.
- Produces: `compute_amount(charge_type: str, quantity: int) -> Decimal`
- Produces: `build_checkout_fields(charge_type, quantity, user_id, m_payment_id, amount) -> dict` — includes `signature`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_payfast_checkout_fields.py`:

```python
"""Checkout fields are server-computed and signed. The client never supplies an amount."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from decimal import Decimal
import pytest

import services.payfast_service as pf


def test_compute_amount_multiplies_by_quantity():
    assert pf.compute_amount('tier_1_credits', 3) == Decimal('1350.00')
    assert pf.compute_amount('tier_2_seats', 4) == Decimal('600.00')


def test_license_ignores_quantity():
    # An annual licence is one licence regardless of what the client asks for.
    assert pf.compute_amount('tier_2_license', 7) == Decimal('1850.00')


def test_unknown_charge_type_raises():
    with pytest.raises(ValueError):
        pf.compute_amount('free_stuff', 1)


def test_non_positive_quantity_raises():
    with pytest.raises(ValueError):
        pf.compute_amount('tier_1_credits', 0)
    with pytest.raises(ValueError):
        pf.compute_amount('tier_1_credits', -5)


def test_fields_carry_user_and_intent(monkeypatch):
    monkeypatch.setattr(pf, "MERCHANT_ID", "33568687")
    monkeypatch.setattr(pf, "MERCHANT_KEY", "key123")
    monkeypatch.setattr(pf, "PASSPHRASE", "pass")
    fields = pf.build_checkout_fields(
        'tier_1_credits', 2, 'user-abc', 'mpid-123', Decimal('900.00')
    )
    assert fields['custom_str1'] == 'user-abc'      # attribution
    assert fields['custom_str2'] == 'tier_1_credits'
    assert fields['m_payment_id'] == 'mpid-123'
    assert fields['amount'] == '900.00'
    assert 'signature' in fields


def test_signature_is_valid_over_the_fields(monkeypatch):
    monkeypatch.setattr(pf, "MERCHANT_ID", "33568687")
    monkeypatch.setattr(pf, "MERCHANT_KEY", "key123")
    monkeypatch.setattr(pf, "PASSPHRASE", "pass")
    fields = pf.build_checkout_fields(
        'tier_1_credits', 1, 'u1', 'm1', Decimal('450.00')
    )
    sig = fields.pop('signature')
    assert pf.generate_signature(fields, "pass") == sig


def test_license_includes_subscription_params(monkeypatch):
    monkeypatch.setattr(pf, "MERCHANT_ID", "33568687")
    monkeypatch.setattr(pf, "MERCHANT_KEY", "key123")
    monkeypatch.setattr(pf, "PASSPHRASE", "pass")
    fields = pf.build_checkout_fields(
        'tier_2_license', 1, 'u1', 'm1', Decimal('1850.00')
    )
    assert fields['subscription_type'] == '1'
    assert fields['recurring_amount'] == '1850.00'
    assert fields['cycles'] == '0'
    assert fields['frequency'] == '6'   # annual


def test_one_off_charges_have_no_subscription_params(monkeypatch):
    monkeypatch.setattr(pf, "MERCHANT_ID", "33568687")
    monkeypatch.setattr(pf, "MERCHANT_KEY", "key123")
    monkeypatch.setattr(pf, "PASSPHRASE", "pass")
    fields = pf.build_checkout_fields(
        'tier_2_seats', 2, 'u1', 'm1', Decimal('300.00')
    )
    assert 'subscription_type' not in fields


def test_no_ai_wording_in_customer_facing_copy(monkeypatch):
    monkeypatch.setattr(pf, "MERCHANT_ID", "33568687")
    monkeypatch.setattr(pf, "MERCHANT_KEY", "key123")
    monkeypatch.setattr(pf, "PASSPHRASE", "pass")
    for ct in ('tier_1_credits', 'tier_2_license', 'tier_2_seats'):
        fields = pf.build_checkout_fields(ct, 1, 'u1', 'm1', pf.PRICES[ct])
        copy = f"{fields['item_name']} {fields['item_description']}".lower()
        assert 'ai' not in copy.split()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_payfast_checkout_fields.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'compute_amount'`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/services/payfast_service.py`:

```python
MERCHANT_ID = os.getenv('PAYFAST_MERCHANT_ID', '')
MERCHANT_KEY = os.getenv('PAYFAST_MERCHANT_KEY', '')
PASSPHRASE = os.getenv('PAYFAST_PASSPHRASE', '')

PROCESS_URL = 'https://payment.payfast.io/eng/process'

APP_URL = os.getenv('PAYFAST_APP_URL', 'https://app.slateone.studio')
API_URL = os.getenv('PAYFAST_API_URL', 'https://api.slateone.studio')

# Customer-facing copy. Product-owner directive: no "AI" wording.
CHARGE_COPY = {
    'tier_1_credits': ('Script Breakdown', 'Pay-per-breakdown'),
    'tier_2_license': ('Annual Team License', 'Annual team licence'),
    'tier_2_seats': ('Team Member Seat', 'Additional team seat'),
}


def compute_amount(charge_type: str, quantity: int) -> Decimal:
    """The only authority on what a purchase costs."""
    if charge_type not in PRICES:
        raise ValueError(f"Unknown charge_type: {charge_type}")
    if quantity < 1:
        raise ValueError(f"quantity must be >= 1, got {quantity}")
    # A licence is one licence — quantity applies to credits and seats only.
    if charge_type == 'tier_2_license':
        return PRICES[charge_type]
    return PRICES[charge_type] * quantity


def build_checkout_fields(charge_type: str, quantity: int, user_id: str,
                          m_payment_id: str, amount: Decimal) -> dict:
    """
    Build the signed form fields for PayFast's process endpoint.

    `amount` is passed in (already persisted on the intent) rather than
    recomputed, so the signed form and the stored intent cannot drift.
    """
    item_name, item_description = CHARGE_COPY[charge_type]

    fields = {
        'merchant_id': MERCHANT_ID,
        'merchant_key': MERCHANT_KEY,
        'return_url': f"{APP_URL}/payment/success?type={charge_type}",
        'cancel_url': f"{APP_URL}/payment/cancel?type={charge_type}",
        'notify_url': f"{API_URL}/api/payfast/notify",
        'm_payment_id': m_payment_id,
        'amount': f"{amount:.2f}",
        'item_name': item_name,
        'item_description': item_description,
        'custom_str1': user_id,      # attribution — the whole point
        'custom_str2': charge_type,  # convenience only; the intent is authoritative
        'custom_int1': str(quantity),
    }

    if charge_type == 'tier_2_license':
        fields['subscription_type'] = '1'
        fields['recurring_amount'] = f"{amount:.2f}"
        fields['cycles'] = '0'      # until cancelled
        fields['frequency'] = '6'   # annual

    fields['signature'] = generate_signature(fields, PASSPHRASE)
    return fields
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_payfast_checkout_fields.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/payfast_service.py backend/tests/test_payfast_checkout_fields.py
git commit -m "feat(billing): signed PayFast checkout field builder"
```

---

### Task 5: Entitlement service

**Files:**
- Create: `backend/services/entitlement_service.py`
- Test: `backend/tests/test_entitlement_service.py`

**Interfaces:**
- Produces: `get_entitlement(user_id) -> dict` with keys `tier`, `status`, `breakdown_balance`, `seats_paid`, `seats_used`, `can_run_breakdown`, `can_use_teams`.
- Produces: `consume_breakdown(user_id, script_id) -> bool` — True if the breakdown may proceed.
- Produces: `grant_credits(user_id, n, txn_id)`, `activate_license(user_id, txn_id)`, `grant_seats(owner_id, n, txn_id)`.
- Produces: `InsufficientCredits(Exception)`.
- Produces: decorators `require_breakdown_entitlement(f)`, `require_team_tier(f)`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_entitlement_service.py`:

```python
"""Entitlement is the single source of truth. Decorators must fail CLOSED."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import services.entitlement_service as es


def _profile(plan='tier_1_pay_per_breakdown', status='active'):
    return {'subscription_plan': plan, 'subscription_status': status,
            'subscription_expires_at': '2099-01-01T00:00:00Z'}


def test_tier2_active_can_run_breakdown_with_zero_balance(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_2_annual_team', 'active'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 5)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 2)
    ent = es.get_entitlement('u1')
    assert ent['can_run_breakdown'] is True   # unlimited
    assert ent['can_use_teams'] is True


def test_tier1_needs_a_positive_balance(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_1_pay_per_breakdown'))
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)

    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    assert es.get_entitlement('u1')['can_run_breakdown'] is False

    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 2)
    assert es.get_entitlement('u1')['can_run_breakdown'] is True


def test_tier1_never_gets_teams(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_1_pay_per_breakdown'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 99)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    assert es.get_entitlement('u1')['can_use_teams'] is False


def test_expired_tier2_loses_teams(monkeypatch):
    # Failed renewal: downgrade to tier 1 behaviour, team features read-only.
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_2_annual_team', 'expired'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 3)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 1)
    ent = es.get_entitlement('u1')
    assert ent['can_use_teams'] is False
    assert ent['can_run_breakdown'] is False


def test_unknown_user_fails_closed(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: None)
    ent = es.get_entitlement('ghost')
    assert ent['can_run_breakdown'] is False
    assert ent['can_use_teams'] is False


def test_consume_is_noop_for_tier2(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_2_annual_team', 'active'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 1)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    called = []
    monkeypatch.setattr(es, "_insert_spend", lambda uid, sid: called.append(sid))
    assert es.consume_breakdown('u1', 's1') is True
    assert called == []   # no ledger write — tier 2 is unlimited


def test_consume_spends_one_credit_for_tier1(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_1_pay_per_breakdown'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 1)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    called = []
    monkeypatch.setattr(es, "_insert_spend", lambda uid, sid: called.append(sid) or True)
    assert es.consume_breakdown('u1', 's1') is True
    assert called == ['s1']


def test_consume_is_free_when_script_already_charged(monkeypatch):
    # The DB unique index rejects the second spend; that means "already paid", not an error.
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_1_pay_per_breakdown'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)   # broke, but already paid
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    monkeypatch.setattr(es, "_script_already_charged", lambda uid, sid: True)
    assert es.consume_breakdown('u1', 's1') is True


def test_consume_raises_at_zero_balance(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: _profile('tier_1_pay_per_breakdown'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    monkeypatch.setattr(es, "_script_already_charged", lambda uid, sid: False)
    with pytest.raises(es.InsufficientCredits):
        es.consume_breakdown('u1', 's1')


def test_decorator_fails_closed_with_no_user(monkeypatch):
    # The bug in the OLD decorator: it read g.user_id (never set) and passed everything through.
    from flask import Flask
    app = Flask(__name__)

    monkeypatch.setattr(es, "get_user_id", lambda: None)

    @es.require_team_tier
    def handler():
        return "reached"

    with app.test_request_context('/'):
        resp = handler()
    assert resp[1] == 401       # NOT "reached"


def test_team_decorator_403s_for_tier1(monkeypatch):
    from flask import Flask
    app = Flask(__name__)
    monkeypatch.setattr(es, "get_user_id", lambda: 'u1')
    monkeypatch.setattr(es, "get_entitlement", lambda uid: {'can_use_teams': False})

    @es.require_team_tier
    def handler():
        return "reached"

    with app.test_request_context('/'):
        resp = handler()
    assert resp[1] == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_entitlement_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.entitlement_service'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/services/entitlement_service.py`:

```python
"""
Entitlement — the single source of truth for "may this user do this?".

Replaces the three copy-pasted `status != 'active'` checks in supabase_routes
and the dead, fail-open `require_active_subscription` in subscription_service.

Every decorator here fails CLOSED. The old one read `g.user_id`, which
middleware/auth.py never sets, so it passed every request through.
"""

from functools import wraps
from datetime import datetime, timezone

from flask import jsonify

from db.supabase_client import get_supabase_admin
from middleware.auth import get_user_id

TIER_1 = 'tier_1_pay_per_breakdown'
TIER_2 = 'tier_2_annual_team'


class InsufficientCredits(Exception):
    """Tier 1 user tried to run a breakdown with no credits."""


def _fetch_profile(user_id: str):
    resp = get_supabase_admin().table('profiles').select(
        'subscription_plan, subscription_status, subscription_expires_at'
    ).eq('id', user_id).limit(1).execute()
    return resp.data[0] if resp.data else None


def _fetch_balance(user_id: str) -> int:
    resp = get_supabase_admin().table('breakdown_credits').select(
        'delta'
    ).eq('user_id', user_id).execute()
    return sum(row['delta'] for row in (resp.data or []))


def _fetch_seats_paid(owner_id: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    resp = get_supabase_admin().table('account_seats').select(
        'seats_granted'
    ).eq('owner_id', owner_id).gt('term_expires_at', now).execute()
    return sum(row['seats_granted'] for row in (resp.data or []))


def _fetch_seats_used(owner_id: str) -> int:
    resp = get_supabase_admin().table('script_members').select(
        'id', count='exact'
    ).eq('invited_by', owner_id).execute()
    return resp.count or 0


def _script_already_charged(user_id: str, script_id: str) -> bool:
    resp = get_supabase_admin().table('breakdown_credits').select('id').eq(
        'user_id', user_id
    ).eq('script_id', script_id).lt('delta', 0).limit(1).execute()
    return bool(resp.data)


def _insert_spend(user_id: str, script_id: str) -> bool:
    get_supabase_admin().table('breakdown_credits').insert({
        'user_id': user_id,
        'delta': -1,
        'script_id': script_id,
        'reason': 'breakdown',
    }).execute()
    return True


def get_entitlement(user_id: str) -> dict:
    profile = _fetch_profile(user_id)
    if not profile:
        # Unknown user: deny everything.
        return {'tier': 'none', 'status': 'none', 'breakdown_balance': 0,
                'seats_paid': 0, 'seats_used': 0,
                'can_run_breakdown': False, 'can_use_teams': False}

    tier = profile.get('subscription_plan') or 'none'
    status = profile.get('subscription_status') or 'none'
    balance = _fetch_balance(user_id)
    seats_paid = _fetch_seats_paid(user_id)
    seats_used = _fetch_seats_used(user_id)

    tier2_active = (tier == TIER_2 and status == 'active')

    return {
        'tier': tier,
        'status': status,
        'breakdown_balance': balance,
        'seats_paid': seats_paid,
        'seats_used': seats_used,
        # Tier 2 active is unlimited; everyone else needs credits.
        'can_run_breakdown': tier2_active or balance > 0,
        # Expired tier 2 loses team writes (business spec §8.2).
        'can_use_teams': tier2_active,
    }


def consume_breakdown(user_id: str, script_id: str) -> bool:
    """
    Charge one credit for this script, unless already charged or unlimited.
    Raises InsufficientCredits if the user cannot pay.
    """
    ent = get_entitlement(user_id)

    if ent['tier'] == TIER_2 and ent['status'] == 'active':
        return True   # unlimited, no ledger write

    if _script_already_charged(user_id, script_id):
        return True   # one charge per script, ever

    if ent['breakdown_balance'] <= 0:
        raise InsufficientCredits("No breakdown credits remaining")

    _insert_spend(user_id, script_id)
    return True


def grant_credits(user_id: str, n: int, txn_id: str) -> None:
    get_supabase_admin().table('breakdown_credits').insert({
        'user_id': user_id, 'delta': n,
        'payfast_transaction_id': txn_id, 'reason': 'purchase',
    }).execute()


def activate_license(user_id: str, txn_id: str) -> None:
    expires = datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1)
    get_supabase_admin().table('profiles').update({
        'subscription_plan': TIER_2,
        'subscription_status': 'active',
        'subscription_expires_at': expires.isoformat(),
        'subscription_payment_provider': 'payfast',
        'subscription_amount': 1850.00,
        'subscription_currency': 'ZAR',
    }).eq('id', user_id).execute()


def grant_seats(owner_id: str, n: int, txn_id: str) -> None:
    profile = _fetch_profile(owner_id) or {}
    term = profile.get('subscription_expires_at') or \
        datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1).isoformat()
    get_supabase_admin().table('account_seats').insert({
        'owner_id': owner_id, 'seats_granted': n,
        'payfast_transaction_id': txn_id, 'term_expires_at': term,
    }).execute()


def require_breakdown_entitlement(f):
    """Fails closed: no user id means no access."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        if not get_entitlement(user_id)['can_run_breakdown']:
            return jsonify({
                'error': 'No breakdown credits remaining',
                'code': 'insufficient_credits',
            }), 402
        return f(*args, **kwargs)
    return wrapper


def require_team_tier(f):
    """Fails closed: no user id means no access."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        if not get_entitlement(user_id)['can_use_teams']:
            return jsonify({
                'error': 'Team features require an Annual Team License',
                'code': 'tier_2_required',
            }), 403
        return f(*args, **kwargs)
    return wrapper
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_entitlement_service.py -v`
Expected: 11 passed

If `test_consume_is_free_when_script_already_charged` fails, check that `consume_breakdown` calls `_script_already_charged` **before** checking balance — an already-paid script must work at zero balance.

- [ ] **Step 5: Verify `_fetch_seats_used` against the real schema**

`script_members` / `invited_by` is an assumption. Confirm the table and column that record accepted invites:

Run: `cd backend && grep -rn "script_members\|table('members')" routes/invite_routes.py | head -5`

If the names differ, fix `_fetch_seats_used` and re-run the tests. **Do not leave a guessed table name in.**

- [ ] **Step 6: Commit**

```bash
git add backend/services/entitlement_service.py backend/tests/test_entitlement_service.py
git commit -m "feat(billing): entitlement service with fail-closed decorators"
```

---

### Task 6: ITN webhook

**Files:**
- Create: `backend/routes/payfast_routes.py`
- Modify: `backend/app.py`
- Test: `backend/tests/test_payfast_itn_route.py`

**Interfaces:**
- Consumes: `verify_itn_signature`, `is_valid_payfast_ip`, `confirm_with_payfast` (Task 3); `grant_credits`, `activate_license`, `grant_seats` (Task 5).
- Produces: `POST /api/payfast/notify`; blueprint `payfast_bp`.

**Built before checkout deliberately:** payments must register the moment they can be taken.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_payfast_itn_route.py`:

```python
"""ITN grants entitlement only after full validation, and only from the intent row."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.payfast_routes as pr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _intent(**over):
    base = {'id': 'txn-1', 'user_id': 'u1', 'charge_type': 'tier_1_credits',
            'expected_amount': '450.00', 'quantity': 1, 'status': 'pending'}
    base.update(over)
    return base


def _pass_all(monkeypatch, grants):
    monkeypatch.setattr(pr, "verify_itn_signature", lambda f, p: True)
    monkeypatch.setattr(pr, "is_valid_payfast_ip", lambda ip: True)
    monkeypatch.setattr(pr, "confirm_with_payfast", lambda f: True)
    monkeypatch.setattr(pr, "_load_intent", lambda m: _intent())
    monkeypatch.setattr(pr, "_already_processed", lambda pf: False)
    monkeypatch.setattr(pr, "_mark_complete", lambda *a, **k: None)
    monkeypatch.setattr(pr, "grant_credits", lambda u, n, t: grants.append(('credits', u, n)))
    monkeypatch.setattr(pr, "activate_license", lambda u, t: grants.append(('license', u)))
    monkeypatch.setattr(pr, "grant_seats", lambda u, n, t: grants.append(('seats', u, n)))


def _post(form=None):
    body = {'m_payment_id': 'm1', 'pf_payment_id': 'pf1',
            'amount_gross': '450.00', 'payment_status': 'COMPLETE'}
    if form:
        body.update(form)
    return _client().post("/api/payfast/notify", data=body)


def test_valid_itn_grants_credits(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    resp = _post()
    assert resp.status_code == 200
    assert grants == [('credits', 'u1', 1)]


def test_bad_signature_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "verify_itn_signature", lambda f, p: False)
    resp = _post()
    assert resp.status_code == 200      # always 200, or PayFast retries forever
    assert grants == []                 # but nothing granted


def test_bad_ip_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "is_valid_payfast_ip", lambda ip: False)
    _post()
    assert grants == []


def test_failed_confirmation_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "confirm_with_payfast", lambda f: False)
    _post()
    assert grants == []


def test_unknown_intent_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "_load_intent", lambda m: None)
    _post()
    assert grants == []


def test_amount_mismatch_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    _post({'amount_gross': '1.00'})     # tampered
    assert grants == []


def test_replay_is_idempotent(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "_already_processed", lambda pf: True)
    _post()
    assert grants == []


def test_query_param_cannot_override_the_intent(monkeypatch):
    # The endpoint is public. ?type=tier_2_license must NOT grant a licence
    # when the intent says credits.
    grants = []
    _pass_all(monkeypatch, grants)
    _client().post("/api/payfast/notify?type=tier_2_license",
                   data={'m_payment_id': 'm1', 'pf_payment_id': 'pf1',
                         'amount_gross': '450.00', 'payment_status': 'COMPLETE'})
    assert grants == [('credits', 'u1', 1)]     # intent wins


def test_custom_str2_cannot_override_the_intent(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    _post({'custom_str2': 'tier_2_license'})
    assert grants == [('credits', 'u1', 1)]


def test_seats_grant_uses_intent_quantity(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    monkeypatch.setattr(pr, "_load_intent",
                        lambda m: _intent(charge_type='tier_2_seats',
                                          expected_amount='600.00', quantity=4))
    _post({'amount_gross': '600.00', 'custom_int1': '99'})   # lying client
    assert grants == [('seats', 'u1', 4)]       # intent quantity, not custom_int1


def test_non_complete_status_grants_nothing(monkeypatch):
    grants = []
    _pass_all(monkeypatch, grants)
    _post({'payment_status': 'FAILED'})
    assert grants == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_payfast_itn_route.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'routes.payfast_routes'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/routes/payfast_routes.py`:

```python
"""
PayFast ITN webhook.

This endpoint is PUBLIC — PayFast calls it, so it cannot require auth.
Everything in the request is therefore untrusted. The charge type, amount
and quantity come from the intent row we created at checkout, NEVER from
the request. `?type=` and `custom_str2` are debug conveniences only.

Always returns 200: PayFast retries indefinitely on anything else, and a
retry storm is worse than a silently-ignored bad request (which we log).
"""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify

from db.supabase_client import get_supabase_admin
from services.payfast_service import (
    verify_itn_signature, is_valid_payfast_ip, confirm_with_payfast, PASSPHRASE,
)
from services.entitlement_service import grant_credits, activate_license, grant_seats

payfast_bp = Blueprint('payfast', __name__)


def _load_intent(m_payment_id: str):
    resp = get_supabase_admin().table('payfast_transactions').select('*').eq(
        'm_payment_id', m_payment_id
    ).limit(1).execute()
    return resp.data[0] if resp.data else None


def _already_processed(pf_payment_id: str) -> bool:
    resp = get_supabase_admin().table('payfast_transactions').select('id').eq(
        'pf_payment_id', pf_payment_id
    ).limit(1).execute()
    return bool(resp.data)


def _mark_complete(txn_id: str, pf_payment_id: str, payload: dict) -> None:
    get_supabase_admin().table('payfast_transactions').update({
        'pf_payment_id': pf_payment_id,
        'status': 'complete',
        'raw_payload': payload,
    }).eq('id', txn_id).execute()


def _reject(reason: str):
    # 200 so PayFast stops retrying; the body is for our logs only.
    print(f"[payfast-itn] REJECTED: {reason}")
    return jsonify({'status': 'ignored'}), 200


@payfast_bp.route('/api/payfast/notify', methods=['POST'])
def payfast_notify():
    form = request.form.to_dict()

    if not verify_itn_signature(form, PASSPHRASE):
        return _reject('signature mismatch')

    if not is_valid_payfast_ip(request.remote_addr):
        return _reject(f'untrusted source ip {request.remote_addr}')

    pf_payment_id = form.get('pf_payment_id')
    if not pf_payment_id:
        return _reject('missing pf_payment_id')

    if _already_processed(pf_payment_id):
        return jsonify({'status': 'duplicate'}), 200   # idempotent

    intent = _load_intent(form.get('m_payment_id', ''))
    if not intent:
        return _reject(f"unknown m_payment_id {form.get('m_payment_id')}")

    try:
        paid = Decimal(form.get('amount_gross', '0'))
    except (InvalidOperation, TypeError):
        return _reject('unparseable amount_gross')

    expected = Decimal(str(intent['expected_amount']))
    if abs(paid - expected) > Decimal('0.01'):
        return _reject(f'amount mismatch: paid {paid}, expected {expected}')

    if not confirm_with_payfast(form):
        return _reject('payfast did not confirm')

    if form.get('payment_status') != 'COMPLETE':
        return _reject(f"payment_status {form.get('payment_status')}")

    # Authoritative values — from the intent, not the request.
    user_id = intent['user_id']
    charge_type = intent['charge_type']
    quantity = int(intent['quantity'])
    txn_id = intent['id']

    if charge_type == 'tier_1_credits':
        grant_credits(user_id, quantity, txn_id)
    elif charge_type == 'tier_2_license':
        activate_license(user_id, txn_id)
    elif charge_type == 'tier_2_seats':
        grant_seats(user_id, quantity, txn_id)
    else:
        return _reject(f'unknown charge_type {charge_type}')

    _mark_complete(txn_id, pf_payment_id, form)
    return jsonify({'status': 'ok'}), 200
```

- [ ] **Step 4: Register the blueprint**

In `backend/app.py`, add the import beside the other route imports:

```python
from routes.payfast_routes import payfast_bp
```

and register it beside the others:

```python
app.register_blueprint(payfast_bp)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_payfast_itn_route.py -v`
Expected: 11 passed

- [ ] **Step 6: Commit**

```bash
git add backend/routes/payfast_routes.py backend/app.py backend/tests/test_payfast_itn_route.py
git commit -m "feat(billing): PayFast ITN webhook with full validation and idempotency"
```

---

### Task 7: Checkout route

**Files:**
- Modify: `backend/routes/payfast_routes.py`
- Test: `backend/tests/test_billing_checkout_route.py`

**Interfaces:**
- Consumes: `compute_amount`, `build_checkout_fields` (Task 4).
- Produces: `POST /api/billing/checkout` → `{process_url, fields}`; `GET /api/billing/entitlement` → entitlement dict.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_billing_checkout_route.py`:

```python
"""Checkout creates a server-side intent. The client cannot influence the amount."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from decimal import Decimal
import routes.payfast_routes as pr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_checkout_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/billing/checkout", json={'charge_type': 'tier_1_credits'})
    assert resp.status_code == 401


def test_checkout_creates_intent_with_server_amount(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    saved = {}
    monkeypatch.setattr(pr, "_create_intent",
                        lambda uid, ct, q, amt, mpid: saved.update(
                            user=uid, charge=ct, qty=q, amount=amt))
    resp = _client().post("/api/billing/checkout",
                          json={'charge_type': 'tier_1_credits', 'quantity': 3})
    assert resp.status_code == 200
    assert saved['amount'] == Decimal('1350.00')    # 3 x 450, computed server-side
    assert saved['user'] == 'u1'


def test_client_supplied_amount_is_ignored(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    saved = {}
    monkeypatch.setattr(pr, "_create_intent",
                        lambda uid, ct, q, amt, mpid: saved.update(amount=amt))
    _client().post("/api/billing/checkout",
                   json={'charge_type': 'tier_1_credits', 'quantity': 1, 'amount': '1.00'})
    assert saved['amount'] == Decimal('450.00')     # not 1.00


def test_response_carries_signed_fields(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    monkeypatch.setattr(pr, "_create_intent", lambda *a: None)
    resp = _client().post("/api/billing/checkout",
                          json={'charge_type': 'tier_1_credits', 'quantity': 1})
    body = resp.get_json()
    assert 'signature' in body['fields']
    assert body['fields']['custom_str1'] == 'u1'
    assert body['process_url'].endswith('/eng/process')


def test_bad_charge_type_is_400(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    resp = _client().post("/api/billing/checkout", json={'charge_type': 'free_stuff'})
    assert resp.status_code == 400


def test_bad_quantity_is_400(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    resp = _client().post("/api/billing/checkout",
                          json={'charge_type': 'tier_1_credits', 'quantity': 0})
    assert resp.status_code == 400


def test_non_integer_quantity_is_400(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    resp = _client().post("/api/billing/checkout",
                          json={'charge_type': 'tier_1_credits', 'quantity': 'lots'})
    assert resp.status_code == 400


def test_entitlement_endpoint_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get("/api/billing/entitlement").status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_billing_checkout_route.py -v`
Expected: FAIL — 404s, because the routes don't exist.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/routes/payfast_routes.py`:

```python
import uuid

from middleware.auth import require_auth, get_user_id
from services.payfast_service import (
    compute_amount, build_checkout_fields, PROCESS_URL,
)
from services.entitlement_service import get_entitlement


def _create_intent(user_id, charge_type, quantity, amount, m_payment_id):
    get_supabase_admin().table('payfast_transactions').insert({
        'm_payment_id': m_payment_id,
        'user_id': user_id,
        'charge_type': charge_type,
        'expected_amount': float(amount),
        'quantity': quantity,
        'status': 'pending',
    }).execute()


@payfast_bp.route('/api/billing/checkout', methods=['POST'])
@require_auth
def create_checkout():
    """
    Create a payment intent and return signed PayFast form fields.

    The amount is computed here and persisted before the user leaves, so the
    ITN can validate against our own record. Any `amount` in the request body
    is ignored on purpose.
    """
    user_id = get_user_id()
    body = request.get_json(silent=True) or {}
    charge_type = body.get('charge_type')

    raw_quantity = body.get('quantity', 1)
    try:
        quantity = int(raw_quantity)
    except (TypeError, ValueError):
        return jsonify({'error': 'quantity must be an integer'}), 400

    try:
        amount = compute_amount(charge_type, quantity)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    m_payment_id = str(uuid.uuid4())
    _create_intent(user_id, charge_type, quantity, amount, m_payment_id)

    fields = build_checkout_fields(charge_type, quantity, user_id, m_payment_id, amount)
    return jsonify({'process_url': PROCESS_URL, 'fields': fields}), 200


@payfast_bp.route('/api/billing/entitlement', methods=['GET'])
@require_auth
def read_entitlement():
    return jsonify(get_entitlement(get_user_id())), 200
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_billing_checkout_route.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add backend/routes/payfast_routes.py backend/tests/test_billing_checkout_route.py
git commit -m "feat(billing): server-signed checkout + entitlement endpoints"
```

---

### Task 8: Security fixes

**Files:**
- Modify: `backend/routes/auth_routes.py:202-340`
- Modify: `backend/utils/env_validator.py:13-26`
- Delete: `supabase/functions/process-beta-payment/`
- Test: `backend/tests/test_set_plan_auth.py`

**Interfaces:**
- Produces: `set-plan` that derives `user_id` from the token.

**These are independent of the billing build and close live holes. Land them early.**

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_set_plan_auth.py`:

```python
"""set-plan must never take user_id from the request body (account takeover)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.auth_routes as ar


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_set_plan_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/auth/set-plan",
                          json={'user_id': 'victim', 'plan': 'tier_2_annual_team'})
    assert resp.status_code == 401


def test_body_user_id_is_ignored(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: 'attacker')
    written = {}
    monkeypatch.setattr(ar, "_upsert_profile", lambda uid, data: written.update(uid=uid))
    _client().post("/api/auth/set-plan",
                   json={'user_id': 'victim', 'plan': 'tier_1_pay_per_breakdown'})
    assert written['uid'] == 'attacker'      # the token's user, never the body's


def test_invalid_plan_rejected(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: 'u1')
    resp = _client().post("/api/auth/set-plan", json={'plan': 'free_forever'})
    assert resp.status_code == 400


def test_landing_tier_params_map_to_full_ids(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: 'u1')
    written = {}
    monkeypatch.setattr(ar, "_upsert_profile", lambda uid, data: written.update(data))
    _client().post("/api/auth/set-plan", json={'plan': 'tier_1'})
    assert written['signup_plan'] == 'tier_1_pay_per_breakdown'


def test_created_at_is_not_overwritten(monkeypatch):
    # The old upsert reset created_at, which get_subscription_status used as the
    # trial-start fallback — effectively renewing an expired trial.
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: 'u1')
    written = {}
    monkeypatch.setattr(ar, "_upsert_profile", lambda uid, data: written.update(data))
    _client().post("/api/auth/set-plan", json={'plan': 'tier_2'})
    assert 'created_at' not in written
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_set_plan_auth.py -v`
Expected: FAIL — the first test returns 200 instead of 401 (that is the vulnerability).

- [ ] **Step 3: Rewrite the set-plan route**

Replace the body of the `set-plan` route in `backend/routes/auth_routes.py` (currently at `:202`). Keep the existing `early_access_users` and `subscription_payments` behaviour if present, but the identity and plan handling become:

```python
# Landing sends tier_1 / tier_2; the DB stores the full ids.
PLAN_ALIASES = {
    'tier_1': 'tier_1_pay_per_breakdown',
    'tier_2': 'tier_2_annual_team',
}
VALID_PLANS = {'tier_1_pay_per_breakdown', 'tier_2_annual_team'}


def _upsert_profile(user_id, data):
    from db.supabase_client import get_supabase_admin
    get_supabase_admin().table('profiles').upsert(
        {'id': user_id, **data}, on_conflict='id'
    ).execute()


@auth_bp.route('/api/auth/set-plan', methods=['POST'])
@require_auth
def set_plan():
    # Identity comes from the verified token. A user_id in the body is ignored:
    # honouring it allowed any caller to rewrite any user's plan.
    user_id = get_user_id()
    body = request.get_json(silent=True) or {}

    plan = body.get('plan')
    plan = PLAN_ALIASES.get(plan, plan)
    if plan not in VALID_PLANS:
        return jsonify({'error': f'Invalid plan: {body.get("plan")}'}), 400

    _upsert_profile(user_id, {
        'signup_plan': plan,
        'signup_source': body.get('source', 'direct'),
        'subscription_status': 'none',   # no free tier — payment activates
        'subscription_plan': 'none',
        'updated_at': 'now()',
        # created_at deliberately NOT written: overwriting it reset account age.
    })
    return jsonify({'success': True, 'signup_plan': plan}), 200
```

Ensure `require_auth` and `get_user_id` are imported at the top of `auth_routes.py`:

```python
from middleware.auth import require_auth, get_user_id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_set_plan_auth.py -v`
Expected: 5 passed

- [ ] **Step 5: Add PayFast env vars to the validator**

In `backend/utils/env_validator.py`, add to `REQUIRED_VARS`:

```python
    'PAYFAST_MERCHANT_ID': 'PayFast merchant ID for checkout signing',
    'PAYFAST_MERCHANT_KEY': 'PayFast merchant key for checkout signing',
    'PAYFAST_PASSPHRASE': 'PayFast security passphrase — required, signatures are enforced',
```

- [ ] **Step 6: Delete the forgeable beta payment function**

```bash
rm -rf supabase/functions/process-beta-payment
```

It is an unauthenticated `Deno.serve` with `Access-Control-Allow-Origin: *` and no signature check — anyone who POSTs an email marks a payment. The beta is over.

- [ ] **Step 7: Run the full backend suite**

Run: `cd backend && pytest tests/`
Expected: all pass. If pre-existing tests reference `script_upload_limit` or `can_upload_script`, update them — those are gone as of Task 1.

- [ ] **Step 8: Commit**

```bash
git add backend/routes/auth_routes.py backend/utils/env_validator.py backend/tests/test_set_plan_auth.py
git rm -r --cached supabase/functions/process-beta-payment 2>/dev/null || true
git add -A supabase/functions
git commit -m "fix(security): authenticate set-plan, require PayFast env, drop forgeable beta payment fn"
```

---

### Task 9: Breakdown gating

**Files:**
- Modify: `backend/routes/supabase_routes.py:2748-2790`, `:3098-3140`, `:3183-3210`
- Modify: `backend/routes/script_routes.py:85, 98, 352, 432, 489, 557, 617`
- Modify: `backend/routes/analysis_routes.py:70, 102, 243, 279`
- Test: `backend/tests/test_breakdown_gating.py`

**Interfaces:**
- Consumes: `require_breakdown_entitlement`, `consume_breakdown`, `InsufficientCredits` (Task 5).

- [ ] **Step 1: Verify the shadowed route before gating**

`/api/scripts/<id>/analyze/bulk` is registered by **both** `script_bp` (`script_routes.py:617`) and `supabase_bp` (`supabase_routes.py:3098`). Confirm which wins — gating the shadowed one gates nothing:

Run:
```bash
cd backend && python3 -c "
from app import app
for r in app.url_map.iter_rules():
    if 'analyze/bulk' in str(r):
        print(r.rule, '->', r.endpoint)
"
```
Expected: the `supabase_routes` endpoint appears (registered first at `app.py:42`). **Gate whichever endpoint actually resolves**, and note the finding in the commit message.

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_breakdown_gating.py`:

```python
"""Breakdown routes must be gated — including for anonymous callers."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_anonymous_analysis_is_rejected(monkeypatch):
    # The old gate was `if user_id:` under @optional_auth — anonymous callers
    # skipped the paywall entirely and got free analysis.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/scenes/scene-1/analyze")
    assert resp.status_code == 401


def test_anonymous_bulk_is_rejected(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/scripts/script-1/analyze/bulk")
    assert resp.status_code == 401


def test_tier1_without_credits_gets_402(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: 'u1')
    monkeypatch.setattr("services.entitlement_service.get_entitlement",
                        lambda uid: {'can_run_breakdown': False})
    resp = _client().post("/api/scenes/scene-1/analyze")
    assert resp.status_code == 402
    assert resp.get_json()['code'] == 'insufficient_credits'


def test_legacy_analysis_routes_are_gated(monkeypatch):
    # These have live frontend callers (AnalysisContext etc.) so they are gated,
    # not deleted — but they must not be a free back door.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    for path in ("/api/scripts/s1/analysis/start",
                 "/api/scripts/s1/analysis/retry",
                 "/api/scripts/s1/reanalyze",
                 "/api/scripts/s1/analyze/characters",
                 "/api/scripts/s1/analyze/locations"):
        resp = _client().post(path)
        assert resp.status_code == 401, f"{path} is not gated (got {resp.status_code})"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_breakdown_gating.py -v`
Expected: FAIL — anonymous requests currently reach the handler.

- [ ] **Step 4: Gate the Supabase analysis routes**

For each of `supabase_routes.py:2748` (single), `:3098` (bulk), `:3183` (retry-failed):

Change the decorator from `@optional_auth` to `@require_auth`, add `@require_breakdown_entitlement`, and **delete** the inline Wise block (`sub_status = get_subscription_status(...)` / `upgrade_url`). Example for the single-scene route:

```python
from middleware.auth import require_auth, get_user_id
from services.entitlement_service import (
    require_breakdown_entitlement, consume_breakdown, InsufficientCredits,
)

@supabase_bp.route('/api/scenes/<scene_id>/analyze', methods=['POST'])
@require_auth
@require_breakdown_entitlement
def analyze_scene(scene_id):
    user_id = get_user_id()
    # ... existing lookup of scene -> script_id ...
    try:
        consume_breakdown(user_id, script_id)
    except InsufficientCredits:
        return jsonify({'error': 'No breakdown credits remaining',
                        'code': 'insufficient_credits'}), 402
    # ... existing analysis body unchanged ...
```

Apply the same to bulk and retry-failed. Retry needs no special case: `consume_breakdown` is free for an already-charged script by construction.

Also remove the now-dead `track_breakdown_usage` imports and calls at `:2785` and `:3134`.

- [ ] **Step 5: Gate the legacy analysis routes**

Add `@require_auth` + `@require_breakdown_entitlement` to every route listed in the Files block for `script_routes.py` and `analysis_routes.py`. Do **not** delete them — they have live frontend callers (spec §7.3).

For routes that receive a `script_id`, also call `consume_breakdown(get_user_id(), script_id)` inside a try/except as above. `/analyze/characters` and `/analyze/locations` operate on an already-charged script, so the call is free and serves only to block users with no entitlement at all.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && pytest tests/test_breakdown_gating.py -v`
Expected: 4 passed

- [ ] **Step 7: Run the full suite**

Run: `cd backend && pytest tests/`
Expected: all pass. `test_analyze_scene_endpoint.py`, `test_analyze_scene_errors.py`, `test_bulk_failed_state.py` and `test_retry_failed_endpoint.py` all exercise these routes and will likely need auth/entitlement monkeypatching added.

- [ ] **Step 8: Commit**

```bash
git add backend/routes/supabase_routes.py backend/routes/script_routes.py backend/routes/analysis_routes.py backend/tests/
git commit -m "fix(billing): gate every breakdown entrypoint, close anonymous bypass"
```

---

### Task 10: Team gating

**Files:**
- Modify: `backend/routes/invite_routes.py:61, 67, 205, 245, 611, 724`
- Modify: `backend/routes/supabase_routes.py:3930`
- Test: `backend/tests/test_team_gating.py`

**Interfaces:**
- Consumes: `require_team_tier`, `get_entitlement` (Task 5).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_team_gating.py`:

```python
"""Team features are tier 2 only, and seat limits are enforced server-side."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.invite_routes as ir


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_tier1_cannot_create_invite(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: 'u1')
    monkeypatch.setattr("services.entitlement_service.get_entitlement",
                        lambda uid: {'can_use_teams': False})
    resp = _client().post("/api/scripts/s1/invites", json={'email': 'a@b.com'})
    assert resp.status_code == 403
    assert resp.get_json()['code'] == 'tier_2_required'


def test_departments_list_requires_auth(monkeypatch):
    # Previously had no decorator at all.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get("/api/invite/departments").status_code == 401
    assert _client().get("/api/departments").status_code == 401


def test_invite_blocked_when_seats_exhausted(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: 'owner')
    monkeypatch.setattr("services.entitlement_service.get_entitlement",
                        lambda uid: {'can_use_teams': True})
    monkeypatch.setattr(ir, "get_entitlement",
                        lambda uid: {'can_use_teams': True, 'seats_paid': 2, 'seats_used': 2})
    resp = _client().post("/api/scripts/s1/invites", json={'email': 'a@b.com'})
    assert resp.status_code == 402
    assert resp.get_json()['code'] == 'no_seats_available'


def test_public_invite_token_lookup_stays_public(monkeypatch):
    # An invitee is not yet a member and may not be a tier 2 user — this must
    # NOT be gated, or nobody can ever accept an invite.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().get("/api/invites/token/sometoken")
    assert resp.status_code != 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_team_gating.py -v`
Expected: FAIL — invite creation succeeds for tier 1; departments return 200 anonymously.

- [ ] **Step 3: Write minimal implementation**

In `backend/routes/invite_routes.py`:

```python
from middleware.auth import require_auth, get_user_id
from services.entitlement_service import require_team_tier, get_entitlement
```

Add `@require_team_tier` (after `@require_auth`) to `:67` `create_invite`, `:205` list invites, `:245` delete invite, `:611` list members, `:724` remove member.

Add `@require_auth` to `:61` `/api/invite/departments` and to `supabase_routes.py:3930` `/api/departments` — both currently have no decorator.

**Leave `:298` `/api/invites/token/<token>` and `:344` accept public/`@require_auth` as they are** — an invitee is not a tier 2 user and must still be able to accept.

Inside `create_invite`, before creating the invite, enforce the seat limit:

```python
    ent = get_entitlement(get_user_id())
    if ent['seats_used'] >= ent['seats_paid']:
        return jsonify({
            'error': 'All paid seats are in use. Purchase more seats to invite.',
            'code': 'no_seats_available',
        }), 402
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_team_gating.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/routes/invite_routes.py backend/routes/supabase_routes.py backend/tests/test_team_gating.py
git commit -m "feat(billing): tier-2 gating and seat limits on team endpoints"
```

---

### Task 11: Retire the credit-pack system

**Files:**
- Delete: `backend/routes/credit_routes.py`, `backend/services/credit_service.py`, `frontend/src/hooks/useCredits.js`
- Modify: `backend/app.py:17,52`, `backend/services/subscription_service.py`

- [ ] **Step 1: Confirm nothing still imports them**

Run:
```bash
cd /Users/thecasterymedia/Desktop/PORTFOLIO/SaaS/ScripDown_AI
grep -rn "credit_service\|credit_routes\|useCredits" backend/ frontend/src/ --include="*.py" --include="*.js" --include="*.jsx" | grep -v "^backend/routes/credit_routes.py\|^backend/services/credit_service.py\|^frontend/src/hooks/useCredits.js"
```
Expected: **no output.** Task 9 removed the last `track_breakdown_usage` calls. If anything remains, fix it before deleting.

- [ ] **Step 2: Delete the files**

```bash
rm backend/routes/credit_routes.py backend/services/credit_service.py frontend/src/hooks/useCredits.js
```

- [ ] **Step 3: Remove the commented-out blueprint lines**

Delete `backend/app.py:17` (`# from routes.credit_routes import credit_bp`) and `:52` (`# app.register_blueprint(credit_bp)`).

- [ ] **Step 4: Remove the dead decorator and the kill switch**

In `backend/services/subscription_service.py`, delete `require_active_subscription` (`:482`) and `require_feature` (`:515`) — both are unimported and fail open. Delete `PHASE1_FREE_ACCESS` (`:15`) and any branch reading it.

- [ ] **Step 5: Run the full suite**

Run: `cd backend && pytest tests/`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A backend frontend/src/hooks
git commit -m "chore(billing): retire credit-pack system and dead fail-open decorators"
```

---

### Task 12: Frontend — entitlement hook and signup mapping

**Files:**
- Create: `frontend/src/hooks/useEntitlement.js`
- Modify: `frontend/src/context/AuthContext.jsx:229-250`
- Modify: `frontend/src/services/apiService.js`
- Modify: `frontend/src/hooks/useSubscription.js:13`

**Interfaces:**
- Produces: `useEntitlement()` → `{entitlement, loading, refetch}`.
- Produces: `apiService.getEntitlement()`, `apiService.createCheckout(chargeType, quantity)`.

- [ ] **Step 1: Add the API methods**

In `frontend/src/services/apiService.js`, beside the other exports:

```javascript
export const getEntitlement = async () => {
    const response = await api.get('/api/billing/entitlement');
    return response.data;
};

export const createCheckout = async (chargeType, quantity = 1) => {
    const response = await api.post('/api/billing/checkout', {
        charge_type: chargeType,
        quantity,
    });
    return response.data;
};
```

- [ ] **Step 2: Create the hook**

Create `frontend/src/hooks/useEntitlement.js`:

```javascript
import { useState, useEffect, useCallback } from 'react';
import { getEntitlement } from '../services/apiService';

export const useEntitlement = () => {
    const [entitlement, setEntitlement] = useState(null);
    const [loading, setLoading] = useState(true);

    const refetch = useCallback(async () => {
        setLoading(true);
        try {
            setEntitlement(await getEntitlement());
        } catch {
            // Fail closed in the UI: no entitlement means show the paywall,
            // never accidentally reveal paid features on a network blip.
            setEntitlement({
                tier: 'none', status: 'none', breakdown_balance: 0,
                seats_paid: 0, seats_used: 0,
                can_run_breakdown: false, can_use_teams: false,
            });
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { refetch(); }, [refetch]);

    return { entitlement, loading, refetch };
};
```

- [ ] **Step 3: Map the landing plan param**

In `frontend/src/context/AuthContext.jsx` around `:229`, where the `plan` query param is read into `localStorage['pending_profile_plan']`, normalise it before storing:

```javascript
const PLAN_ALIASES = {
    tier_1: 'tier_1_pay_per_breakdown',
    tier_2: 'tier_2_annual_team',
};

// Landing sends ?plan=tier_1|tier_2; the API expects the full id.
const rawPlan = new URLSearchParams(window.location.search).get('plan');
const plan = PLAN_ALIASES[rawPlan] || null;
if (plan) {
    localStorage.setItem('pending_profile_plan', plan);
}
```

The backend also accepts the short aliases (Task 8), so this is belt-and-braces — but it keeps `localStorage` holding the same vocabulary as the database.

- [ ] **Step 4: Remove the frontend kill switch**

In `frontend/src/hooks/useSubscription.js`, delete `const PHASE1_FREE_ACCESS = false;` (`:13`) and any branch reading it. It had to be kept in sync by hand with the backend constant deleted in Task 11.

- [ ] **Step 5: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds. (`npm run lint` is broken repo-wide — do not run it as a gate.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useEntitlement.js frontend/src/services/apiService.js frontend/src/context/AuthContext.jsx frontend/src/hooks/useSubscription.js
git commit -m "feat(billing): entitlement hook, checkout API, signup plan mapping"
```

---

### Task 13: Frontend — billing page and payment result routes

**Files:**
- Create: `frontend/src/pages/BillingPage.jsx`
- Create: `frontend/src/pages/PaymentResultPage.jsx`
- Modify: `frontend/src/App.jsx:128`

**Interfaces:**
- Consumes: `useEntitlement`, `createCheckout` (Task 12).

- [ ] **Step 1: Create the checkout page**

Create `frontend/src/pages/BillingPage.jsx`. The quantity picker lives here — the server multiplies, so the browser never touches an amount:

```jsx
import { useState } from 'react';
import { createCheckout } from '../services/apiService';
import { useEntitlement } from '../hooks/useEntitlement';

// Display only. The server is the authority on price.
const PRICE_ZAR = { tier_1_credits: 450, tier_2_license: 1850, tier_2_seats: 150 };

const postToPayFast = ({ process_url, fields }) => {
    // PayFast requires a real form POST, not fetch.
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = process_url;
    Object.entries(fields).forEach(([name, value]) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
};

export default function BillingPage() {
    const { entitlement, loading } = useEntitlement();
    const [quantity, setQuantity] = useState(1);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);

    const buy = async (chargeType, qty) => {
        setBusy(true);
        setError(null);
        try {
            postToPayFast(await createCheckout(chargeType, qty));
        } catch {
            setError('Could not start checkout. Please try again.');
            setBusy(false);
        }
    };

    if (loading) return <div>Loading…</div>;

    return (
        <div className="billing-page">
            <h1>Billing</h1>
            {error && <p role="alert">{error}</p>}

            <section>
                <h2>Breakdown credits</h2>
                <p>{entitlement.breakdown_balance} remaining · R{PRICE_ZAR.tier_1_credits} each (incl. VAT)</p>
                <label htmlFor="qty">Quantity</label>
                <select id="qty" value={quantity}
                        onChange={(e) => setQuantity(Number(e.target.value))}>
                    {[1, 5, 10].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
                <p>Total: R{PRICE_ZAR.tier_1_credits * quantity}</p>
                <button disabled={busy} onClick={() => buy('tier_1_credits', quantity)}>
                    Buy breakdowns
                </button>
            </section>

            {entitlement.tier === 'tier_2_annual_team' && entitlement.status === 'active' ? (
                <section>
                    <h2>Team seats</h2>
                    <p>{entitlement.seats_used} of {entitlement.seats_paid} seats in use</p>
                    <button disabled={busy} onClick={() => buy('tier_2_seats', 1)}>
                        Add a seat — R{PRICE_ZAR.tier_2_seats}/yr
                    </button>
                </section>
            ) : (
                <section>
                    <h2>Annual Team License</h2>
                    <p>R{PRICE_ZAR.tier_2_license}/yr — unlimited breakdowns for you and your team.</p>
                    <button disabled={busy} onClick={() => buy('tier_2_license', 1)}>
                        Subscribe
                    </button>
                </section>
            )}
        </div>
    );
}
```

- [ ] **Step 2: Create the payment result page**

Create `frontend/src/pages/PaymentResultPage.jsx`. This is **UX only** — access comes from the ITN:

```jsx
import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useEntitlement } from '../hooks/useEntitlement';

export default function PaymentResultPage({ outcome }) {
    const [params] = useSearchParams();
    const { entitlement, refetch } = useEntitlement();
    const [waited, setWaited] = useState(0);

    // The ITN is a separate server-to-server call and may land after the
    // browser gets back here, so poll briefly rather than claim failure.
    useEffect(() => {
        if (outcome !== 'success' || waited >= 5) return;
        const t = setTimeout(() => { refetch(); setWaited((w) => w + 1); }, 2000);
        return () => clearTimeout(t);
    }, [outcome, waited, refetch]);

    if (outcome === 'cancel') {
        return (
            <div>
                <h1>Payment cancelled</h1>
                <p>You have not been charged.</p>
                <Link to="/billing">Back to billing</Link>
            </div>
        );
    }

    const settled = entitlement?.can_run_breakdown || entitlement?.can_use_teams;

    return (
        <div>
            <h1>Thank you</h1>
            {settled ? (
                <p>Your purchase is active. Type: {params.get('type')}</p>
            ) : (
                <p>Payment received — confirming with our payment provider. This
                   usually takes a few seconds.</p>
            )}
            <Link to="/">Continue</Link>
        </div>
    );
}
```

- [ ] **Step 3: Wire the routes**

In `frontend/src/App.jsx`, replace the commented-out `PaymentSuccessPage` route at `:128` and add the billing route:

```jsx
import BillingPage from './pages/BillingPage';
import PaymentResultPage from './pages/PaymentResultPage';

// ...inside the authenticated routes:
<Route path="billing" element={<BillingPage />} />
<Route path="payment/success" element={<PaymentResultPage outcome="success" />} />
<Route path="payment/cancel" element={<PaymentResultPage outcome="cancel" />} />
```

The paths must be exactly `payment/success` and `payment/cancel` — they are baked into the signed `return_url` / `cancel_url` in `payfast_service.build_checkout_fields`.

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Verify the route paths match the backend**

Run: `cd backend && grep -n "payment/success\|payment/cancel" services/payfast_service.py`
Expected: both appear, matching the `App.jsx` paths exactly. A mismatch means every paying customer lands on a 404.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/BillingPage.jsx frontend/src/pages/PaymentResultPage.jsx frontend/src/App.jsx
git commit -m "feat(billing): billing page and payment result routes"
```

---

### Task 13b: Retire useSubscription and the old subscription-status endpoint

**Files:**
- Modify: `frontend/src/components/scenes/SceneViewer.jsx:53`
- Modify: `frontend/src/components/subscription/SubscriptionGate.jsx:22`
- Modify: `frontend/src/components/subscription/SubscriptionBanner.jsx:13`
- Modify: `frontend/src/components/team/InviteModal.jsx:35`
- Modify: `frontend/src/components/reports/ReportStudio.jsx:50`
- Delete: `frontend/src/hooks/useSubscription.js`
- Modify: `backend/routes/auth_routes.py` (remove `/api/auth/subscription-status`, `/api/auth/can-upload-script`)
- Delete: `backend/services/subscription_service.py`

**Interfaces:**
- Consumes: `useEntitlement` (Task 12).

**Why this task exists:** Task 1 drops `script_upload_limit`, but `subscription_service.py:95` explicitly selects it:

```python
.select('subscription_status, subscription_expires_at, created_at, script_upload_limit')
```

After the migration that select errors, the broad `except` swallows it, and `get_subscription_status()` returns `_default_trial_status()` — status `'trial'`, a value the new CHECK constraint no longer permits. The UI would show every user as "trial" while the backend correctly denies them. Two parallel subscription-state systems that must agree by hand is exactly the failure `PHASE1_FREE_ACCESS` already caused. Delete one.

- [ ] **Step 1: Map the current consumers**

Run: `cd frontend && grep -rn "useSubscription" src/ | grep -v "hooks/useSubscription.js"`
Expected: five files. For each, note which fields it reads (`status`, `canAnalyze`, `scriptLimit`, …) — you must map each to a `useEntitlement` field, not invent one.

Field mapping:

| useSubscription | useEntitlement |
|---|---|
| `subscription.status === 'active'` | `entitlement.can_run_breakdown` |
| gating team UI | `entitlement.can_use_teams` |
| any script-limit field | **delete the branch** — uploads are free and unlimited on both tiers |

- [ ] **Step 2: Migrate each consumer**

In each of the five files, replace the import and call:

```javascript
// before
import { useSubscription } from '../../hooks/useSubscription';
const { subscription, loading } = useSubscription();

// after
import { useEntitlement } from '../../hooks/useEntitlement';
const { entitlement, loading } = useEntitlement();
```

Then replace each read per the table above. For `InviteModal.jsx`, the gate becomes `entitlement.can_use_teams`; when false, show the Tier 2 upsell rather than a disabled button (spec §8). For `SceneViewer.jsx`, the analyse gate becomes `entitlement.can_run_breakdown`; when false, link to `/billing`.

Any upsell copy must follow the Global Constraint: **no "AI" wording** — say "breakdown" or "script analysis".

- [ ] **Step 3: Delete the old hook and service**

```bash
rm frontend/src/hooks/useSubscription.js backend/services/subscription_service.py
```

In `backend/routes/auth_routes.py`, delete the `/api/auth/subscription-status` route (`:97` area), the `/api/auth/can-upload-script` route (`:167`), the `/api/auth/activate-subscription` route (`:443`), and every `from services.subscription_service import ...`.

- [ ] **Step 4: Confirm nothing still references them**

Run:
```bash
cd /Users/thecasterymedia/Desktop/PORTFOLIO/SaaS/ScripDown_AI
grep -rn "useSubscription\|subscription_service\|subscription-status\|can-upload-script" backend/ frontend/src/ --include="*.py" --include="*.js" --include="*.jsx"
```
Expected: **no output.**

If `admin_routes.py:481` calls `activate_monthly_subscription` from the deleted service, replace that call with `entitlement_service.activate_license(user_id, None)` — the admin approve flow must keep working.

- [ ] **Step 5: Verify both gates**

Run: `cd backend && pytest tests/`
Expected: all pass. Delete or rewrite any test that exercises the removed endpoints.

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add -A backend frontend/src
git commit -m "refactor(billing): retire useSubscription and subscription_service for useEntitlement"
```

---

### Task 14: End-to-end verification against the PayFast sandbox

**Files:**
- Modify: none (verification only)

**This task produces no code. It exists because every prior task mocked PayFast, and a signature bug passes 100% of mocked tests.**

- [ ] **Step 1: Confirm the environment**

Run: `cd backend && python3 -c "
import os
for v in ('PAYFAST_MERCHANT_ID','PAYFAST_MERCHANT_KEY','PAYFAST_PASSPHRASE'):
    val = os.getenv(v)
    print(f'{v}: {\"SET\" if val else \"MISSING\"}' + (' (TRAILING SPACE!)' if val and val != val.strip() else ''))
"`
Expected: all three SET, none with a trailing space.

- [ ] **Step 2: Run the whole backend suite**

Run: `cd backend && pytest tests/`
Expected: all pass.

- [ ] **Step 3: STOP — hand off to the human**

The remaining verification needs a real PayFast sandbox transaction and cannot be done by an agent. Report:

> Code complete. To verify end-to-end, in a PayFast **sandbox** merchant:
> 1. Set `PAYFAST_SANDBOX=true` and sandbox credentials locally.
> 2. Sign up with `?plan=tier_1`, go to `/billing`, buy 1 breakdown.
> 3. Confirm you land on PayFast's page with the correct amount (R450) — if it
>    rejects the signature, the passphrase or field order is wrong.
> 4. Complete the sandbox payment.
> 5. Confirm the ITN arrives, `payfast_transactions.status` becomes `complete`,
>    and a `+1` row appears in `breakdown_credits`.
> 6. Run a breakdown; confirm a `-1` row appears. Run it again on the same
>    script; confirm **no second** `-1` row (one charge per script).
> 7. Repeat for `tier_2_license` and `tier_2_seats`.
>
> Adversarial checks that must all fail:
> - `POST /api/payfast/notify` with no signature → no grant.
> - Replay a captured ITN → no second grant.
> - Analyse a scene with no `Authorization` header → 401.
> - `POST /api/auth/set-plan` with another user's `user_id` in the body → the
>   caller's own plan changes, never the victim's.

---

## Self-Review

**Spec coverage:**

| Spec section | Task |
|---|---|
| §4.1 profiles / §4.2 payfast_transactions / §4.3 breakdown_credits / §4.4 account_seats / §4.5 retirements | 1, 11 |
| §5 entitlement service + decorators | 5 |
| §6.1 checkout | 4, 7 |
| §6.2 ITN | 3, 6 |
| §6.3 config | 8 |
| §7.1 breakdown gate | 9 |
| §7.2 team gate | 10 |
| §7.3 security fixes (1 anonymous bypass, 2 legacy gating, 3 set-plan, 4 beta fn, 5 DEV_MODE) | 8, 9 |
| §8 frontend | 12, 13 |
| §9 PayFast account | done before this plan |
| §10 testing | every task; §10 E2E in 14 |

**Known gaps, deliberately deferred:**
- **Failed-renewal downgrade (spec §5, business spec §8.2)** is implemented as a *read* (`get_entitlement` denies teams once `status != 'active'`), but nothing *writes* `status='expired'`. PayFast sends a renewal-failure ITN; wiring it needs a real renewal-failure payload to test against, which the sandbox does not readily produce. **Flagged for the human — this is the one requirement not fully closed.**
- `DEV_MODE` removal (spec §7.3 item 5) is explicitly out of scope in the spec; Task 8 only documents the env var.

**Type consistency:** `charge_type` values (`tier_1_credits` / `tier_2_license` / `tier_2_seats`) are identical across the migration CHECK (Task 1), `PRICES` (Task 2), `CHARGE_COPY` (Task 4), the ITN branch (Task 6) and `BillingPage` (Task 13). Plan ids (`tier_1_pay_per_breakdown` / `tier_2_annual_team`) are identical across Tasks 1, 5, 8, 12. `get_entitlement`'s seven keys are consumed unchanged in Tasks 9, 10, 12, 13.

**Assumptions needing confirmation during execution** (each has a verification step rather than a guess left in):
- `scripts(id)` is the FK target for `breakdown_credits.script_id` — Task 1 Step 3.
- `script_members.invited_by` records accepted invites — Task 5 Step 5.
- `supabase_bp` shadows `script_bp` for `analyze/bulk` — Task 9 Step 1.
