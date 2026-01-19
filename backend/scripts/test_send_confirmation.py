#!/usr/bin/env python3
"""
Test script to send confirmation emails to unconfirmed users one by one.
This uses Supabase Admin API to generate confirmation links.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    sys.exit(1)

# Initialize Supabase client with service role key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_unconfirmed_users():
    """Get all users who haven't confirmed their email."""
    try:
        # Query auth.users for unconfirmed users
        response = supabase.auth.admin.list_users()
        
        unconfirmed = [
            user for user in response 
            if user.email_confirmed_at is None
        ]
        
        return unconfirmed
    except Exception as e:
        print(f"❌ Error fetching users: {e}")
        return []


def send_confirmation_email(email: str):
    """
    Send a confirmation email to a specific user.
    Uses Supabase Admin API to generate a new confirmation link.
    """
    try:
        print(f"\n📧 Sending confirmation email to: {email}")
        
        # Generate a new signup confirmation link
        result = supabase.auth.admin.generate_link({
            'type': 'signup',
            'email': email,
            'options': {
                'redirect_to': 'https://app.slateone.studio/auth/callback?type=signup'
            }
        })
        
        if result:
            print(f"✅ Confirmation email sent successfully!")
            print(f"   Email: {email}")
            if hasattr(result, 'properties'):
                action_link = result.properties.get('action_link', 'N/A')
                print(f"   Confirmation link: {action_link[:80]}...")
            return True
        else:
            print(f"❌ Failed to send confirmation email")
            return False
            
    except Exception as e:
        print(f"❌ Error sending confirmation email: {e}")
        return False


def main():
    print("=" * 60)
    print("🧪 Supabase Confirmation Email Test")
    print("=" * 60)
    
    # Get unconfirmed users
    print("\n🔍 Fetching unconfirmed users...")
    unconfirmed_users = get_unconfirmed_users()
    
    if not unconfirmed_users:
        print("\n✅ No unconfirmed users found!")
        return
    
    print(f"\n📋 Found {len(unconfirmed_users)} unconfirmed user(s):")
    for i, user in enumerate(unconfirmed_users, 1):
        print(f"   {i}. {user.email} (signed up: {user.created_at})")
    
    # Interactive mode - send one by one
    print("\n" + "=" * 60)
    print("📬 Send confirmation emails one by one")
    print("=" * 60)
    
    for i, user in enumerate(unconfirmed_users, 1):
        print(f"\n[{i}/{len(unconfirmed_users)}] User: {user.email}")
        
        choice = input("   Send confirmation email? (y/n/q to quit): ").strip().lower()
        
        if choice == 'q':
            print("\n👋 Exiting...")
            break
        elif choice == 'y':
            success = send_confirmation_email(user.email)
            if success:
                input("\n   ✅ Press Enter to continue to next user...")
            else:
                retry = input("\n   ❌ Failed. Retry? (y/n): ").strip().lower()
                if retry == 'y':
                    send_confirmation_email(user.email)
        else:
            print("   ⏭️  Skipped")
    
    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60)
    print("\n💡 Tips:")
    print("   1. Check your email inbox (and spam folder)")
    print("   2. Check Supabase Auth logs for email send events")
    print("   3. Verify SMTP settings in Supabase Dashboard if emails don't arrive")


if __name__ == "__main__":
    main()
