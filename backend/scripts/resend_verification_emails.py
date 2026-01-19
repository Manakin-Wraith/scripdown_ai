#!/usr/bin/env python3
"""
Resend verification emails to unverified users.
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

def resend_verification_emails():
    """Resend verification emails to unverified users."""
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ Missing Supabase credentials")
        return
    
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    print("\n📊 Fetching users from Supabase Admin API...")
    
    try:
        # Use Admin API to list users
        response = client.auth.admin.list_users()
        all_users = response
        
        # Filter for unverified users
        unverified_users = [
            user for user in all_users 
            if not user.email_confirmed_at
        ]
        
        if not unverified_users:
            print("✅ No unverified users found")
            return
        
        print(f"\n📧 Found {len(unverified_users)} unverified user(s):\n")
        
        for user in unverified_users:
            print(f"  • {user.email}")
            print(f"    Created: {user.created_at}")
            print(f"    Last sign in: {user.last_sign_in_at or 'Never'}")
        
        confirm = input(f"\nResend verification emails to {len(unverified_users)} user(s)? (y/N): ").strip().lower()
        
        if confirm != 'y':
            print("❌ Cancelled")
            return
        
        print("\n" + "=" * 70)
        print("RESENDING VERIFICATION EMAILS")
        print("=" * 70)
        
        sent_count = 0
        failed_count = 0
        
        for user in unverified_users:
            email = user.email
            try:
                # Resend verification email via Supabase Admin API
                result = client.auth.admin.invite_user_by_email(
                    email,
                    options={
                        'redirect_to': 'https://app.slateone.studio/auth/confirm'
                    }
                )
                
                print(f"✅ Sent to {email}")
                sent_count += 1
                
            except Exception as e:
                print(f"❌ Failed to send to {email}: {e}")
                failed_count += 1
        
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Emails sent: {sent_count}")
        print(f"Failed: {failed_count}")
        print("=" * 70)
        
        if sent_count > 0:
            print("\n✅ Verification emails resent!")
            print("\nUsers should receive emails from: hello@slateone.studio")
            print("If emails still don't arrive, check Resend dashboard:")
            print("https://resend.com/emails")
        
    except Exception as e:
        print(f"❌ Error fetching users: {e}")
        print("\nTry using Supabase MCP tools instead:")

if __name__ == '__main__':
    resend_verification_emails()
