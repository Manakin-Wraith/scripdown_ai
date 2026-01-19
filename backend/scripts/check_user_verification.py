#!/usr/bin/env python3
"""
Check email verification status for users.
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

def check_verification_status():
    """Check verification status of all users."""
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ Missing Supabase credentials")
        return
    
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    print("\n" + "=" * 70)
    print("USER VERIFICATION STATUS")
    print("=" * 70)
    
    try:
        # Get all users
        users = client.auth.admin.list_users()
        
        verified_users = [u for u in users if u.email_confirmed_at]
        unverified_users = [u for u in users if not u.email_confirmed_at]
        
        print(f"\n📊 Total users: {len(users)}")
        print(f"   ✅ Verified: {len(verified_users)}")
        print(f"   ❌ Unverified: {len(unverified_users)}")
        
        if unverified_users:
            print("\n" + "=" * 70)
            print("UNVERIFIED USERS")
            print("=" * 70)
            for user in unverified_users:
                print(f"\n📧 {user.email}")
                print(f"   Created: {user.created_at}")
                print(f"   Last sign in: {user.last_sign_in_at or 'Never'}")
        
        if verified_users:
            print("\n" + "=" * 70)
            print("VERIFIED USERS")
            print("=" * 70)
            for user in verified_users:
                print(f"\n✅ {user.email}")
                print(f"   Verified: {user.email_confirmed_at}")
                print(f"   Last sign in: {user.last_sign_in_at or 'Never'}")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    check_verification_status()
