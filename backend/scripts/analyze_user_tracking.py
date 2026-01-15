"""
Analyze current user tracking capabilities in Supabase.
Check what data we have and what we need to add.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("=" * 70)
print("USER TRACKING ANALYSIS")
print("=" * 70)

# 1. Check auth.users table
print("\n📊 AUTH.USERS TABLE")
print("-" * 70)

users = supabase.auth.admin.list_users()

print(f"\nTotal users: {len(users)}\n")

for user in users:
    email = user.email
    created = user.created_at
    confirmed = user.email_confirmed_at
    last_sign_in = user.last_sign_in_at
    
    status = "✅ Confirmed" if confirmed else "⏳ Pending"
    
    print(f"{status} | {email}")
    print(f"   Created: {created}")
    print(f"   Confirmed: {confirmed or 'Not yet'}")
    print(f"   Last Sign In: {last_sign_in or 'Never'}")
    print()

# 2. Check if profiles table exists
print("\n📊 PROFILES TABLE")
print("-" * 70)

try:
    profiles = supabase.table('profiles').select('*').execute()
    print(f"Found {len(profiles.data)} profile(s)")
    
    for profile in profiles.data:
        print(f"  - {profile.get('email', 'N/A')}: {profile.get('full_name', 'N/A')}")
except Exception as e:
    print(f"⚠️  Profiles table not accessible or doesn't exist: {e}")

# 3. Check for waitlist table
print("\n📊 WAITLIST TABLE")
print("-" * 70)

try:
    # Try to query waitlist table
    waitlist = supabase.table('waitlist').select('*').execute()
    print(f"Found {len(waitlist.data)} waitlist entry(ies)")
    
    for entry in waitlist.data:
        print(f"  - {entry.get('email', 'N/A')}: Invited on {entry.get('created_at', 'N/A')}")
except Exception as e:
    print(f"⚠️  Waitlist table not accessible or doesn't exist: {e}")

# 4. Summary and recommendations
print("\n" + "=" * 70)
print("TRACKING CAPABILITIES")
print("=" * 70)

print("\n✅ AVAILABLE DATA:")
print("   - User email (auth.users)")
print("   - Created timestamp (auth.users)")
print("   - Email confirmed timestamp (auth.users)")
print("   - Last sign in timestamp (auth.users)")
print("   - User ID (auth.users)")

print("\n⚠️  MISSING DATA:")
print("   - Invitation source (email, manual, waitlist)")
print("   - Who invited them")
print("   - Invitation timestamp")
print("   - Early access email sent status")
print("   - User's first name/full name")

print("\n💡 RECOMMENDATIONS:")
print("   1. Create 'user_invitations' table to track:")
print("      - email, invited_at, invited_by, source, status")
print("   2. Create 'profiles' table to store:")
print("      - user_id, full_name, email, created_at")
print("   3. Link auth.users to profiles via user_id")

print("\n" + "=" * 70)
