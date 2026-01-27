-- Fix payment_reference unique constraint to allow multiple NULL values
-- The previous constraint prevented multiple purchases without payment references

-- Drop the problematic constraint
ALTER TABLE script_credit_purchases 
DROP CONSTRAINT IF EXISTS unique_payment_reference;

-- Add a new constraint that only enforces uniqueness for non-NULL values
-- This uses a partial unique index instead
CREATE UNIQUE INDEX IF NOT EXISTS unique_payment_reference_not_null 
ON script_credit_purchases(payment_reference) 
WHERE payment_reference IS NOT NULL;

-- Comment
COMMENT ON INDEX unique_payment_reference_not_null IS 
'Ensures payment references are unique when provided, but allows multiple NULL values';
