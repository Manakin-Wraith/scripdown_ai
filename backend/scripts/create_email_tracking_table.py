"""
Create email_tracking table in Supabase.
Run this script to set up email tracking.
"""

import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

from db.supabase_client import SupabaseDB

def create_table():
    """Create email_tracking table."""
    
    print("🔧 Creating email_tracking table...")
    print("=" * 50)
    
    db = SupabaseDB()
    
    # Check if table exists by trying to query it
    try:
        result = db.client.table('email_tracking').select('id').limit(1).execute()
        print("✅ Table 'email_tracking' already exists!")
        print(f"   Found {len(result.data)} records")
        return True
    except Exception as e:
        if 'does not exist' in str(e) or 'relation' in str(e):
            print("⚠️  Table 'email_tracking' does not exist yet.")
            print("\n📋 To create the table, please:")
            print("\n1. Go to Supabase SQL Editor:")
            print("   https://supabase.com/dashboard/project/twzfaizeyqwevmhjyicz/sql")
            print("\n2. Copy and paste this SQL:\n")
            
            sql = """
-- Email tracking table for beta launch and other campaigns
CREATE TABLE IF NOT EXISTS email_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_type VARCHAR(50) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(255),
    user_status VARCHAR(50),
    resend_email_id VARCHAR(255),
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivery_status VARCHAR(50) DEFAULT 'sent',
    opened_at TIMESTAMP WITH TIME ZONE,
    clicked_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_email_tracking_recipient ON email_tracking(recipient_email);
CREATE INDEX idx_email_tracking_type ON email_tracking(email_type);
CREATE INDEX idx_email_tracking_sent_at ON email_tracking(sent_at DESC);
CREATE INDEX idx_email_tracking_resend_id ON email_tracking(resend_email_id);

-- Enable RLS
ALTER TABLE email_tracking ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Authenticated users can view email tracking"
    ON email_tracking FOR SELECT TO authenticated USING (true);

CREATE POLICY "Service role can manage email tracking"
    ON email_tracking FOR ALL TO service_role USING (true);
"""
            
            print(sql)
            print("\n3. Click 'Run' to execute")
            print("\n4. Then run this script again to verify")
            
            return False
        else:
            print(f"❌ Error checking table: {e}")
            return False


if __name__ == '__main__':
    success = create_table()
    
    if success:
        print("\n✅ Email tracking is ready to use!")
        print("\nYou can now:")
        print("  • Send test emails (they'll be tracked automatically)")
        print("  • View analytics at: http://localhost:5000/api/email-analytics/metrics")
        print("  • Check recent emails: http://localhost:5000/api/email-analytics/recent")
    else:
        print("\n⏳ Waiting for table creation...")
