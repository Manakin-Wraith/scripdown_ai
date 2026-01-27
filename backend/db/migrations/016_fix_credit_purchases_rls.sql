-- Fix RLS policies for script_credit_purchases table
-- This allows users to create and view their own purchase records

-- Enable RLS on script_credit_purchases if not already enabled
ALTER TABLE script_credit_purchases ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own purchases" ON script_credit_purchases;
DROP POLICY IF EXISTS "Users can create their own purchases" ON script_credit_purchases;
DROP POLICY IF EXISTS "Service role can manage all purchases" ON script_credit_purchases;

-- Policy: Users can view their own purchase records
CREATE POLICY "Users can view their own purchases"
ON script_credit_purchases
FOR SELECT
USING (auth.uid() = user_id);

-- Policy: Users can create their own purchase records
-- Also allow service role (backend) to create purchases on behalf of users
CREATE POLICY "Users can create their own purchases"
ON script_credit_purchases
FOR INSERT
WITH CHECK (
    auth.uid() = user_id 
    OR auth.jwt()->>'role' = 'service_role'
);

-- Policy: Service role can manage all purchases (for webhooks and admin)
CREATE POLICY "Service role can manage all purchases"
ON script_credit_purchases
FOR ALL
USING (auth.jwt()->>'role' = 'service_role');

-- Grant necessary permissions
GRANT SELECT, INSERT ON script_credit_purchases TO authenticated;
GRANT ALL ON script_credit_purchases TO service_role;
