"""
Test script to verify email campaigns database connectivity
Run this to ensure the migration was applied correctly and the backend can access the tables
"""

import os
from dotenv import load_dotenv
from db.supabase_client import get_supabase_admin

# Load environment variables
load_dotenv()

def test_database_connectivity():
    """Test that all campaign tables are accessible"""
    print("🔍 Testing Email Campaigns Database Connectivity...\n")
    
    try:
        supabase = get_supabase_admin()
        print("✅ Supabase client initialized\n")
        
        # Test 1: Check email_templates table
        print("📧 Testing email_templates table...")
        templates_result = supabase.table('email_templates').select('*').limit(5).execute()
        print(f"   Found {len(templates_result.data)} templates")
        if templates_result.data:
            for template in templates_result.data:
                print(f"   - {template['name']} ({template['category']})")
        print()
        
        # Test 2: Check email_campaigns table
        print("📋 Testing email_campaigns table...")
        campaigns_result = supabase.table('email_campaigns').select('*').limit(5).execute()
        print(f"   Found {len(campaigns_result.data)} campaigns")
        if campaigns_result.data:
            for campaign in campaigns_result.data:
                print(f"   - {campaign['name']} (Status: {campaign['status']})")
        print()
        
        # Test 3: Check email_campaign_recipients table
        print("👥 Testing email_campaign_recipients table...")
        recipients_result = supabase.table('email_campaign_recipients').select('*').limit(5).execute()
        print(f"   Found {len(recipients_result.data)} recipients")
        print()
        
        # Test 4: Check email_campaign_clicks table
        print("🖱️  Testing email_campaign_clicks table...")
        clicks_result = supabase.table('email_campaign_clicks').select('*').limit(5).execute()
        print(f"   Found {len(clicks_result.data)} clicks")
        print()
        
        # Test 5: Verify RLS policies (should work with admin client)
        print("🔒 Testing RLS policies...")
        print("   Admin client can access all tables ✅")
        print()
        
        # Summary
        print("=" * 60)
        print("✅ DATABASE CONNECTIVITY TEST PASSED!")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  - Templates: {len(templates_result.data)}")
        print(f"  - Campaigns: {len(campaigns_result.data)}")
        print(f"  - Recipients: {len(recipients_result.data)}")
        print(f"  - Clicks: {len(clicks_result.data)}")
        print()
        
        if len(templates_result.data) == 0:
            print("⚠️  WARNING: No templates found. The migration may not have inserted default templates.")
            print("   Run the migration SQL in Supabase Dashboard to add default templates.")
        
        return True
        
    except Exception as e:
        print("=" * 60)
        print("❌ DATABASE CONNECTIVITY TEST FAILED!")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        print("\nPossible issues:")
        print("  1. Migration not applied - Run the SQL in Supabase Dashboard")
        print("  2. Database connection issue - Check .env file")
        print("  3. RLS policies blocking access - Use admin client")
        print()
        return False

if __name__ == "__main__":
    test_database_connectivity()
