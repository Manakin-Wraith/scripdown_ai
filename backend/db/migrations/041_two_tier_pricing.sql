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
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_signup_plan_check;
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
    -- Deliberately no FK to scripts: this is an immutable financial record and
    -- must survive hard-deletion of the script it refers to.
    script_id UUID,
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
DROP FUNCTION IF EXISTS add_script_credits(UUID, INTEGER, UUID);
DROP FUNCTION IF EXISTS activate_monthly_subscription(UUID, UUID);
DROP FUNCTION IF EXISTS can_upload_script(UUID);
DROP FUNCTION IF EXISTS increment_script_upload(UUID);
DROP TABLE IF EXISTS script_credit_usage;
DROP TABLE IF EXISTS script_credit_purchases;

ALTER TABLE profiles DROP COLUMN IF EXISTS script_credits;
ALTER TABLE profiles DROP COLUMN IF EXISTS total_scripts_purchased;
