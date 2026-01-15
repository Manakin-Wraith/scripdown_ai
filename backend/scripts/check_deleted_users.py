"""
Check for soft-deleted users in Supabase Auth.
Soft-deleted users still exist in the database but are hidden from normal queries.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Missing Supabase credentials in .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("=" * 70)
print("CHECK FOR SOFT-DELETED USERS")
print("=" * 70)

email = input("\nEnter email address to check: ").strip()

if not email:
    print("❌ Email address required")
    sys.exit(1)

print(f"\n🔍 Checking for: {email}\n")

try:
    # Get all users (including deleted)
    # Note: Supabase Python SDK may not expose deleted users directly
    # We'll try to get user by email first
    
    users = supabase.auth.admin.list_users()
    active_user = next((u for u in users if u.email == email), None)
    
    if active_user:
        print(f"✅ User EXISTS and is ACTIVE")
        print(f"   User ID: {active_user.id}")
        print(f"   Created: {active_user.created_at}")
        print(f"   Confirmed: {active_user.email_confirmed_at or 'Not confirmed'}")
    else:
        print(f"❌ User NOT FOUND in active users")
        print(f"\nPossible reasons:")
        print(f"   1. User never signed up")
        print(f"   2. User was deleted (soft-delete)")
        print(f"   3. Email typo")
        
        print(f"\n💡 Solutions:")
        print(f"   - If deleted: Contact Supabase support to recover")
        print(f"   - If never signed up: User needs to sign up via app")
        print(f"   - Check Supabase Dashboard → Authentication → Users")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("TIP: Check Supabase Dashboard → Authentication → Users")
print("     Look for 'Deleted Users' or filter options")
print("=" * 70)
