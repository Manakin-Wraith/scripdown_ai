-- Migration: PayFast tokenization for the Annual Team License
-- Description: tier_2_license switched from subscription_type=1 (true
--              recurring billing, which this PayFast account doesn't have
--              enabled — confirmed via live sandbox testing, subscription
--              checkout consistently rejects with a signature mismatch
--              while an otherwise-identical tokenization request succeeds)
--              to subscription_type=2 (tokenization). PayFast now only
--              charges when we tell it to via its Recurring Billing API,
--              so we must keep the token it hands back on activation.
-- Date: 2026-07-17

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS subscription_payfast_token TEXT;

COMMENT ON COLUMN profiles.subscription_payfast_token IS
    'PayFast tokenization token from the ITN, used to charge the next '
    'Annual Team License renewal via PayFast''s Recurring Billing API. '
    'NULL for tier_1 users and any tier_2 grant made before this column '
    'existed (e.g. the admin manual-approval path).';
