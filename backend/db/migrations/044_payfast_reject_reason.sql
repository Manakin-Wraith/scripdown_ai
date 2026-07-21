-- Diagnostic column: records why an ITN was rejected (_reject() in
-- payfast_routes.py), so a stuck 'pending' row can be distinguished
-- between "never received an ITN" (NULL) and "received one, rejected it"
-- (this column set) without needing to dig through Railway logs.
ALTER TABLE payfast_transactions
    ADD COLUMN IF NOT EXISTS reject_reason TEXT;

COMMENT ON COLUMN payfast_transactions.reject_reason IS
    'Set by _reject() in payfast_routes.py when an ITN fails validation. NULL means either no ITN was ever received, or it was successfully claimed/granted.';
