-- Migration: Script Credits System
-- Description: Implement pay-per-script credit system (R49/script)
-- Date: 2026-01-27

-- ============================================
-- 1. Add credit columns to profiles
-- ============================================

-- Add script credits column
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS script_credits INTEGER DEFAULT 0 CHECK (script_credits >= 0);

-- Add total purchased tracking
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS total_scripts_purchased INTEGER DEFAULT 0 CHECK (total_scripts_purchased >= 0);

-- Add legacy beta flag for existing users
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS is_legacy_beta BOOLEAN DEFAULT FALSE;

-- Create index for credit lookups
CREATE INDEX IF NOT EXISTS idx_profiles_script_credits ON profiles(script_credits);

-- ============================================
-- 2. Script Credit Purchases Table
-- ============================================

CREATE TABLE IF NOT EXISTS script_credit_purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    
    -- Package details
    credits_purchased INTEGER NOT NULL CHECK (credits_purchased > 0),
    package_type TEXT NOT NULL CHECK (package_type IN ('single', 'pack_5', 'pack_10', 'pack_25')),
    
    -- Payment details
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    currency TEXT DEFAULT 'ZAR',
    payment_reference TEXT,
    yoco_payment_id TEXT,
    
    -- Status tracking
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    paid_at TIMESTAMPTZ,
    credits_added_at TIMESTAMPTZ,
    
    -- Ensure payment reference is unique if provided
    CONSTRAINT unique_payment_reference UNIQUE NULLS NOT DISTINCT (payment_reference)
);

-- Indexes for quick lookups
CREATE INDEX IF NOT EXISTS idx_credit_purchases_user_id ON script_credit_purchases(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_purchases_email ON script_credit_purchases(email);
CREATE INDEX IF NOT EXISTS idx_credit_purchases_status ON script_credit_purchases(status);
CREATE INDEX IF NOT EXISTS idx_credit_purchases_yoco_id ON script_credit_purchases(yoco_payment_id);

-- Enable RLS
ALTER TABLE script_credit_purchases ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Users can view own credit purchases" ON script_credit_purchases;
DROP POLICY IF EXISTS "Service role full access on credit purchases" ON script_credit_purchases;

CREATE POLICY "Users can view own credit purchases" ON script_credit_purchases
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on credit purchases" ON script_credit_purchases
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================
-- 3. Script Credit Usage Table
-- ============================================

CREATE TABLE IF NOT EXISTS script_credit_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    script_id UUID REFERENCES scripts(id) ON DELETE SET NULL,
    
    -- Usage details
    credits_used INTEGER DEFAULT 1 CHECK (credits_used > 0),
    script_name TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one credit usage per script
    CONSTRAINT unique_credit_per_script UNIQUE (script_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_credit_usage_user_id ON script_credit_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_usage_script_id ON script_credit_usage(script_id);
CREATE INDEX IF NOT EXISTS idx_credit_usage_created_at ON script_credit_usage(created_at DESC);

-- Enable RLS
ALTER TABLE script_credit_usage ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Users can view own credit usage" ON script_credit_usage;
DROP POLICY IF EXISTS "Service role full access on credit usage" ON script_credit_usage;

CREATE POLICY "Users can view own credit usage" ON script_credit_usage
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on credit usage" ON script_credit_usage
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================
-- 4. Helper Functions
-- ============================================

-- Function to deduct credits and log usage
CREATE OR REPLACE FUNCTION deduct_script_credit(
    p_user_id UUID,
    p_script_id UUID,
    p_script_name TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_current_credits INTEGER;
BEGIN
    -- Get current credits with row lock
    SELECT script_credits INTO v_current_credits
    FROM profiles
    WHERE id = p_user_id
    FOR UPDATE;
    
    -- Check if user has credits
    IF v_current_credits IS NULL OR v_current_credits < 1 THEN
        RETURN FALSE;
    END IF;
    
    -- Deduct credit
    UPDATE profiles
    SET script_credits = script_credits - 1
    WHERE id = p_user_id;
    
    -- Log usage
    INSERT INTO script_credit_usage (user_id, script_id, script_name, credits_used)
    VALUES (p_user_id, p_script_id, p_script_name, 1);
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to add credits after purchase
CREATE OR REPLACE FUNCTION add_script_credits(
    p_user_id UUID,
    p_credits INTEGER,
    p_purchase_id UUID
) RETURNS BOOLEAN AS $$
BEGIN
    -- Add credits to profile
    UPDATE profiles
    SET 
        script_credits = script_credits + p_credits,
        total_scripts_purchased = total_scripts_purchased + p_credits
    WHERE id = p_user_id;
    
    -- Mark purchase as completed
    UPDATE script_credit_purchases
    SET 
        status = 'completed',
        credits_added_at = NOW()
    WHERE id = p_purchase_id;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- 5. Views for Analytics
-- ============================================

-- Credit balance summary view
CREATE OR REPLACE VIEW credit_balance_summary AS
SELECT 
    p.id as user_id,
    p.email,
    p.full_name,
    p.script_credits,
    p.total_scripts_purchased,
    p.is_legacy_beta,
    COUNT(DISTINCT cu.id) as scripts_uploaded,
    COALESCE(SUM(cp.credits_purchased), 0) as total_credits_purchased,
    COALESCE(SUM(cp.amount), 0) as total_spent
FROM profiles p
LEFT JOIN script_credit_usage cu ON p.id = cu.user_id
LEFT JOIN script_credit_purchases cp ON p.id = cp.user_id AND cp.status = 'completed'
GROUP BY p.id, p.email, p.full_name, p.script_credits, p.total_scripts_purchased, p.is_legacy_beta;

-- ============================================
-- 6. Comments for Documentation
-- ============================================

COMMENT ON TABLE script_credit_purchases IS 'Tracks credit package purchases (R49/script model)';
COMMENT ON TABLE script_credit_usage IS 'Logs credit usage per script upload';
COMMENT ON COLUMN profiles.script_credits IS 'Current available credits for script uploads';
COMMENT ON COLUMN profiles.total_scripts_purchased IS 'Lifetime total credits purchased';
COMMENT ON COLUMN profiles.is_legacy_beta IS 'Flag for users who had full access before credit system';
COMMENT ON FUNCTION deduct_script_credit IS 'Atomically deduct 1 credit and log usage';
COMMENT ON FUNCTION add_script_credits IS 'Add credits to user account after successful purchase';
