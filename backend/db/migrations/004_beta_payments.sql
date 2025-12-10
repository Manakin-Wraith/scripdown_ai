-- Migration: Beta Payments Table
-- Description: Track beta user payments from Yoco payment link
-- Date: 2024-12-10

-- Beta payments table to track Yoco payments
CREATE TABLE IF NOT EXISTS beta_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    payment_reference TEXT,
    amount DECIMAL(10,2) DEFAULT 350.00,
    currency TEXT DEFAULT 'ZAR',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    paid_at TIMESTAMPTZ,
    
    -- Ensure one payment record per email
    CONSTRAINT unique_email_payment UNIQUE (email)
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_beta_payments_email ON beta_payments(email);
CREATE INDEX IF NOT EXISTS idx_beta_payments_status ON beta_payments(status);
CREATE INDEX IF NOT EXISTS idx_beta_payments_user_id ON beta_payments(user_id);

-- Enable RLS
ALTER TABLE beta_payments ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything (for Edge Functions)
CREATE POLICY "Service role full access" ON beta_payments
    FOR ALL
    USING (auth.role() = 'service_role');

-- Policy: Users can view their own payment record
CREATE POLICY "Users can view own payment" ON beta_payments
    FOR SELECT
    USING (auth.uid() = user_id);

-- Add subscription_status to profiles if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'profiles' AND column_name = 'subscription_status'
    ) THEN
        ALTER TABLE profiles ADD COLUMN subscription_status TEXT DEFAULT 'trial' 
            CHECK (subscription_status IN ('trial', 'active', 'expired', 'cancelled'));
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'profiles' AND column_name = 'subscription_expires_at'
    ) THEN
        ALTER TABLE profiles ADD COLUMN subscription_expires_at TIMESTAMPTZ;
    END IF;
END $$;

-- Comment for documentation
COMMENT ON TABLE beta_payments IS 'Tracks beta user payments from Yoco payment link';
