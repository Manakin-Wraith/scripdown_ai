-- Fix payment_reference unique constraint to allow multiple NULL values
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/twzfaizeyqwevmhjyicz/sql

-- Drop the problematic constraint
ALTER TABLE script_credit_purchases 
DROP CONSTRAINT IF EXISTS unique_payment_reference;

-- Add a partial unique index that only enforces uniqueness for non-NULL values
CREATE UNIQUE INDEX IF NOT EXISTS unique_payment_reference_not_null 
ON script_credit_purchases(payment_reference) 
WHERE payment_reference IS NOT NULL;

-- Verify the fix
SELECT 
    conname as constraint_name,
    contype as constraint_type
FROM pg_constraint 
WHERE conrelid = 'script_credit_purchases'::regclass
AND conname LIKE '%payment_reference%';

-- This should now allow multiple purchases with NULL payment_reference
-- but still enforce uniqueness when a payment_reference is provided
