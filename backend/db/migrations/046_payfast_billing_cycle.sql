-- Migration: Monthly/annual billing cycle for the Team License
-- Description: The Annual Team License is being joined by a monthly option
--              at the same per-seat structure, priced so annual is a
--              discounted prepay of the same product (not a separate
--              offering): monthly R1,850 license + R250/seat, annual
--              R18,500 license + R2,500/seat.
--
--              billing_cycle is recorded on the intent row at checkout
--              (server-computed, same trust boundary as expected_amount)
--              so the ITN grant knows which term/price to apply without
--              trusting the request. NULL for tier_1_credits, where it's
--              not meaningful.
-- Date: 2026-07-31

ALTER TABLE payfast_transactions ADD COLUMN IF NOT EXISTS billing_cycle TEXT
    CHECK (billing_cycle IS NULL OR billing_cycle IN ('monthly', 'annual'));

COMMENT ON COLUMN payfast_transactions.billing_cycle IS
    'monthly | annual | NULL (tier_1_credits, not applicable). Selects term length and price for tier_2_license/tier_2_seats grants — server-computed at checkout, same trust boundary as expected_amount.';

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS subscription_billing_cycle TEXT
    CHECK (subscription_billing_cycle IS NULL OR subscription_billing_cycle IN ('monthly', 'annual'));

COMMENT ON COLUMN profiles.subscription_billing_cycle IS
    'Which cycle the active tier_2_annual_team license was purchased under — drives the term length applied on activation/renewal.';

-- Postgres identifies functions by name AND argument types, so
-- CREATE OR REPLACE with a different parameter list creates a SECOND
-- overload instead of replacing migration 043's original one — leaving
-- the unqualified COMMENT/GRANT/REVOKE below ambiguous ("function name
-- ... is not unique"). Drop the exact old signature first so only the
-- new one exists afterward.
DROP FUNCTION IF EXISTS payfast_claim_and_grant(
    UUID, TEXT, JSONB, TEXT, UUID, INTEGER, TEXT
);
-- Also drop the new signature in case a prior partial run of this
-- migration already created it (makes this migration safely re-runnable).
DROP FUNCTION IF EXISTS payfast_claim_and_grant(
    UUID, TEXT, JSONB, TEXT, UUID, INTEGER, TEXT, TEXT
);

-- Re-create payfast_claim_and_grant (migration 043) with a billing_cycle
-- parameter. Defaults to 'annual' to preserve behavior for any in-flight
-- rows created before this migration (their billing_cycle column is NULL).
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
        IF v_cycle = 'monthly' THEN
            v_interval := INTERVAL '30 days';
            v_amount := 1850.00;
        ELSE
            v_interval := INTERVAL '365 days';
            v_amount := 18500.00;
        END IF;

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

    ELSIF p_charge_type = 'tier_2_seats' THEN
        -- Seat term always tracks the license's own term_expires_at
        -- regardless of cycle — unchanged from migration 043.
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
    'Atomically claims a payfast_transactions row and performs its grant in one transaction. tier_2_license term/amount now depend on p_billing_cycle (monthly=30 days/R1850, annual=365 days/R18500). ITN-only -- the admin manual-approval path uses the plain Python grant functions in entitlement_service.py, which have no race to close.';

REVOKE EXECUTE ON FUNCTION payfast_claim_and_grant FROM PUBLIC;
GRANT EXECUTE ON FUNCTION payfast_claim_and_grant TO service_role;
