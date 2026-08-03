-- Migration: 4-cadence Team License with included seats
-- Description: The Team License grows from 2 cadences (monthly, annual) to
--              4 (monthly, 3-month, 6-month, annual). Each cadence now
--              bundles a number of free seats (monthly=0, 3month=1,
--              6month=2, annual=3), granted as an account_seats row in the
--              same transaction as the license itself. Seats purchased
--              beyond that bundle stay a flat R250/month with no
--              long-term discount (3month=R750, 6month=R1,500,
--              annual=R3,000 -- replaces the old discounted R2,500/yr).
-- Date: 2026-08-03

ALTER TABLE payfast_transactions DROP CONSTRAINT IF EXISTS payfast_transactions_billing_cycle_check;
ALTER TABLE payfast_transactions ADD CONSTRAINT payfast_transactions_billing_cycle_check
    CHECK (billing_cycle IS NULL OR billing_cycle IN ('monthly', '3month', '6month', 'annual'));

ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_subscription_billing_cycle_check;
ALTER TABLE profiles ADD CONSTRAINT profiles_subscription_billing_cycle_check
    CHECK (subscription_billing_cycle IS NULL OR subscription_billing_cycle IN ('monthly', '3month', '6month', 'annual'));

-- Same signature as migration 046 (8 args) -- CREATE OR REPLACE is sufficient,
-- no DROP needed.
CREATE OR REPLACE FUNCTION payfast_claim_and_grant(
    p_txn_id UUID,
    p_pf_payment_id TEXT,
    p_raw_payload JSONB,
    p_charge_type TEXT,
    p_user_id UUID,
    p_quantity INTEGER,
    p_payfast_token TEXT DEFAULT NULL,
    p_billing_cycle TEXT DEFAULT 'annual'
) RETURNS TEXT AS $$
DECLARE
    v_term TIMESTAMPTZ;
    v_interval INTERVAL;
    v_amount NUMERIC;
    v_cycle TEXT;
    v_included_seats INTEGER;
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
        v_cycle := COALESCE(p_billing_cycle, 'annual');
        CASE v_cycle
            WHEN 'monthly' THEN
                v_interval := INTERVAL '30 days';
                v_amount := 1850.00;
                v_included_seats := 0;
            WHEN '3month' THEN
                v_interval := INTERVAL '90 days';
                v_amount := 5500.00;
                v_included_seats := 1;
            WHEN '6month' THEN
                v_interval := INTERVAL '180 days';
                v_amount := 9500.00;
                v_included_seats := 2;
            ELSE
                v_cycle := 'annual';
                v_interval := INTERVAL '365 days';
                v_amount := 18500.00;
                v_included_seats := 3;
        END CASE;

        UPDATE profiles SET
            subscription_plan = 'tier_2_annual_team',
            subscription_status = 'active',
            subscription_expires_at = NOW() + v_interval,
            subscription_payment_provider = 'payfast',
            subscription_amount = v_amount,
            subscription_currency = 'ZAR',
            subscription_billing_cycle = v_cycle,
            subscription_payfast_token = COALESCE(p_payfast_token, subscription_payfast_token)
        WHERE id = p_user_id;

        -- Seats bundled with this cadence, granted as part of the same
        -- purchase/transaction. seats_granted has a CHECK (> 0), so the
        -- monthly cadence (0 included) inserts nothing.
        IF v_included_seats > 0 THEN
            INSERT INTO account_seats (owner_id, seats_granted, payfast_transaction_id, term_expires_at)
            VALUES (p_user_id, v_included_seats, p_txn_id, NOW() + v_interval);
        END IF;

    ELSIF p_charge_type = 'tier_2_seats' THEN
        -- Seat term always tracks the license's own term_expires_at
        -- regardless of cycle -- unchanged from migration 043. Price is
        -- computed and persisted at checkout (payfast_service.py), not
        -- recomputed here.
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
    'Atomically claims a payfast_transactions row and performs its grant in one transaction. tier_2_license term/amount/included-seats depend on p_billing_cycle (monthly=30d/R1850/0 seats, 3month=90d/R5500/1 seat, 6month=180d/R9500/2 seats, annual=365d/R18500/3 seats). ITN-only -- the admin manual-approval path uses the plain Python grant functions in entitlement_service.py, which have no race to close.';

REVOKE EXECUTE ON FUNCTION payfast_claim_and_grant FROM PUBLIC;
GRANT EXECUTE ON FUNCTION payfast_claim_and_grant TO service_role;
