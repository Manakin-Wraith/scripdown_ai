"""
Check if email exists in early_access_users table.
This helps diagnose why invite_user_by_email might be failing.
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
print("CHECK EARLY ACCESS USER STATUS")
print("=" * 70)

email = input("\nEnter email address: ").strip()

if not email:
    print("❌ Email address required")
    sys.exit(1)

print(f"\n🔍 Checking: {email}\n")

# Check auth.users
print("1️⃣ Checking auth.users...")
try:
    users = supabase.auth.admin.list_users()
    auth_user = next((u for u in users if u.email == email), None)
    
    if auth_user:
        print(f"   ✅ EXISTS in auth.users")
        print(f"   User ID: {auth_user.id}")
        print(f"   Confirmed: {auth_user.email_confirmed_at or 'Not confirmed'}")
    else:
        print(f"   ❌ NOT FOUND in auth.users")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check early_access_users
print("\n2️⃣ Checking early_access_users...")
try:
    result = supabase.table('early_access_users')\
        .select('*')\
        .eq('email', email)\
        .execute()
    
    if result.data:
        user = result.data[0]
        print(f"   ✅ EXISTS in early_access_users")
        print(f"   Status: {user.get('status')}")
        print(f"   User ID: {user.get('user_id') or 'NULL'}")
        print(f"   Invited: {user.get('invited_at')}")
        print(f"   Signed up: {user.get('signed_up_at') or 'Not yet'}")
    else:
        print(f"   ❌ NOT FOUND in early_access_users")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("DIAGNOSIS")
print("=" * 70)

if not auth_user and result.data:
    print("📋 Status: In early_access_users but NOT in auth.users")
    print("\n💡 Solution:")
    print("   This user was invited to early access but hasn't signed up yet.")
    print("   They need to:")
    print("   1. Go to your app's signup page")
    print("   2. Create an account with this email")
    print("   3. Confirm their email")
    print("\n   OR you can send them a reminder:")
    print("   python scripts/send_reminders_to_early_access.py")
elif auth_user and not result.data:
    print("📋 Status: In auth.users but NOT in early_access_users")
    print("\n💡 This is normal for regular signups (not early access)")
elif auth_user and result.data:
    print("📋 Status: In BOTH tables")
    print("\n✅ User is properly synced")
else:
    print("📋 Status: NOT FOUND in either table")
    print("\n💡 This email has never interacted with your system")

print("=" * 70)
