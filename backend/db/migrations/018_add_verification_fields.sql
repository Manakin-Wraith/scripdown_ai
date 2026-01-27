-- Add verification tracking fields to script_credit_purchases
-- This supports manual admin verification workflow

ALTER TABLE script_credit_purchases 
ADD COLUMN IF NOT EXISTS verified_by UUID REFERENCES auth.users(id),
ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS verification_notes TEXT,
ADD COLUMN IF NOT EXISTS admin_reference TEXT; -- For admin to add Yoco reference

-- Add index for quick lookup of pending purchases
CREATE INDEX IF NOT EXISTS idx_credit_purchases_pending 
ON script_credit_purchases(status, created_at) 
WHERE status = 'pending';

-- Comment
COMMENT ON COLUMN script_credit_purchases.verified_by IS 'Admin user who verified the payment';
COMMENT ON COLUMN script_credit_purchases.verified_at IS 'When the payment was verified';
COMMENT ON COLUMN script_credit_purchases.verification_notes IS 'Admin notes about verification';
COMMENT ON COLUMN script_credit_purchases.admin_reference IS 'Yoco reference number added by admin';
