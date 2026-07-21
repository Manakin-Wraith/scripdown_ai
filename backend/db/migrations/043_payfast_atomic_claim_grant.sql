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
--
-- DEPLOY ORDER: This migration MUST be applied to the real Supabase project
--              before (or atomically with) deploying the corresponding
--              backend/routes/payfast_routes.py code that calls it. If the
--              Python code goes out first, the `payfast_claim_and_grant` RPC
--              call fails with "function does not exist"; payfast_notify's
--              own exception handling catches that and returns HTTP 200
--              ("ignored"). Per this module's own docstring, PayFast treats
--              any 200 as "stop retrying" -- so a real payment during that
--              window is claimed by nothing, granted nothing, and never
--              retried. Silent payment loss, not a loud failure.

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
