-- Migration: Pricing Simplification
-- Description: Replace credit pack system with $49/month flat-rate subscription via Wise
-- Date: 2026-04-07

-- ============================================
-- 1. Add subscription plan columns to profiles
-- ============================================

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS subscription_plan TEXT DEFAULT 'trial'
    CHECK (subscription_plan IN ('trial', 'monthly'));

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS subscription_payment_provider TEXT;

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS subscription_amount DECIMAL(10,2);

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS subscription_currency TEXT DEFAULT 'USD';

COMMENT ON COLUMN profiles.subscription_plan IS 'Current subscription plan: trial or monthly ($49/mo)';
COMMENT ON COLUMN profiles.subscription_payment_provider IS 'Payment provider: wise';
COMMENT ON COLUMN profiles.subscription_amount IS 'Monthly subscription amount (49.00 USD)';
COMMENT ON COLUMN profiles.subscription_currency IS 'Subscription currency (USD)';

-- ============================================
-- 2. Subscription Payments Table
-- ============================================

CREATE TABLE IF NOT EXISTS subscription_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,

    -- Plan details
    plan TEXT NOT NULL DEFAULT 'monthly' CHECK (plan IN ('monthly')),
    amount DECIMAL(10,2) NOT NULL DEFAULT 49.00 CHECK (amount > 0),
    currency TEXT NOT NULL DEFAULT 'USD',

    -- Payment provider
    payment_provider TEXT NOT NULL DEFAULT 'wise',
    payment_reference TEXT,

    -- Status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),

    -- Subscription period
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES auth.users(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sub_payments_user_id ON subscription_payments(user_id);
CREATE INDEX IF NOT EXISTS idx_sub_payments_email ON subscription_payments(email);
CREATE INDEX IF NOT EXISTS idx_sub_payments_status ON subscription_payments(status);
CREATE INDEX IF NOT EXISTS idx_sub_payments_period ON subscription_payments(period_start, period_end);

-- Enable RLS
ALTER TABLE subscription_payments ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own subscription payments"
    ON subscription_payments FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on subscription payments"
    ON subscription_payments FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================
-- 3. Deprecate old credit tables (comments only, no drops)
-- ============================================

COMMENT ON TABLE script_credit_purchases IS 'DEPRECATED (2026-04-07): Replaced by subscription_payments. Kept for historical audit.';
COMMENT ON TABLE script_credit_usage IS 'DEPRECATED (2026-04-07): Credit system replaced by $49/mo subscription. Kept for historical audit.';
COMMENT ON COLUMN profiles.script_credits IS 'DEPRECATED (2026-04-07): Credit system removed. Kept for historical data.';
COMMENT ON COLUMN profiles.total_scripts_purchased IS 'DEPRECATED (2026-04-07): Credit system removed. Kept for historical data.';
COMMENT ON COLUMN profiles.is_legacy_beta IS 'DEPRECATED (2026-04-07): Credit system removed. Kept for historical data.';

-- ============================================
-- 4. Helper function: Activate monthly subscription
-- ============================================

CREATE OR REPLACE FUNCTION activate_monthly_subscription(
    p_user_id UUID,
    p_payment_id UUID DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_period_start TIMESTAMPTZ := NOW();
    v_period_end TIMESTAMPTZ := NOW() + INTERVAL '30 days';
BEGIN
    -- Update profile
    UPDATE profiles
    SET
        subscription_status = 'active',
        subscription_plan = 'monthly',
        subscription_expires_at = v_period_end,
        subscription_payment_provider = 'wise',
        subscription_amount = 49.00,
        subscription_currency = 'USD',
        updated_at = NOW()
    WHERE id = p_user_id;

    -- Update payment record if provided
    IF p_payment_id IS NOT NULL THEN
        UPDATE subscription_payments
        SET
            status = 'completed',
            period_start = v_period_start,
            period_end = v_period_end,
            verified_at = NOW()
        WHERE id = p_payment_id;
    END IF;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION activate_monthly_subscription IS 'Activates $49/month subscription for a user. Sets 30-day period.';

-- ============================================
-- 5. Subscription payments summary view
-- ============================================

CREATE OR REPLACE VIEW subscription_payment_summary AS
SELECT
    p.id AS user_id,
    p.email,
    p.full_name,
    p.subscription_status,
    p.subscription_plan,
    p.subscription_expires_at,
    COUNT(sp.id) AS total_payments,
    COALESCE(SUM(CASE WHEN sp.status = 'completed' THEN sp.amount ELSE 0 END), 0) AS total_paid,
    MAX(sp.verified_at) AS last_payment_date
FROM profiles p
LEFT JOIN subscription_payments sp ON p.id = sp.user_id
GROUP BY p.id, p.email, p.full_name, p.subscription_status, p.subscription_plan, p.subscription_expires_at;
