#!/usr/bin/env python3
"""
Resend confirmation emails to specific unverified users.
Interactive script to select and send confirmation reminders.
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

def get_unverified_users(client):
    """Get all unverified users."""
    try:
        response = client.auth.admin.list_users()
        
        unverified = [
            user for user in response 
            if user.email_confirmed_at is None
        ]
        
        return unverified
    except Exception as e:
        print(f"❌ Error fetching users: {e}")
        return []


def send_confirmation_email(client, email: str):
    """Send confirmation email to a specific user."""
    try:
        print(f"\n📧 Sending confirmation email to: {email}")
        
        # Generate email confirmation link
        result = client.auth.admin.generate_link({
            'type': 'signup',
            'email': email,
            'options': {
                'redirect_to': 'https://app.slateone.studio/auth/confirm'
            }
        })
        
        print(f"✅ Confirmation email sent successfully!")
        print(f"   From: hello@slateone.studio")
        print(f"   Subject: Confirm your signup")
        
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


def main():
    print("\n" + "=" * 70)
    print("RESEND CONFIRMATION EMAILS TO SPECIFIC USERS")
    print("=" * 70)
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ Missing Supabase credentials")
        return
    
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # Get unverified users
    print("\n🔍 Fetching unverified users...")
    unverified_users = get_unverified_users(client)
    
    if not unverified_users:
        print("\n✅ No unverified users found!")
        return
    
    print(f"\n📋 Found {len(unverified_users)} unverified user(s):")
    print("=" * 70)
    
    for i, user in enumerate(unverified_users, 1):
        print(f"\n{i}. {user.email}")
        print(f"   Created: {user.created_at}")
        print(f"   Last sign in: {user.last_sign_in_at or 'Never'}")
    
    print("\n" + "=" * 70)
    print("\nOptions:")
    print("  • Enter numbers (e.g., '1,3,5' or '1-3')")
    print("  • Enter 'all' to send to all unverified users")
    print("  • Enter 'q' to quit")
    
    selection = input("\nSelect users to send confirmation emails: ").strip().lower()
    
    if selection == 'q':
        print("❌ Cancelled")
        return
    
    # Parse selection
    selected_users = []
    
    if selection == 'all':
        selected_users = unverified_users
    else:
        try:
            # Handle ranges (1-3) and individual numbers (1,2,5)
            indices = []
            for part in selection.split(','):
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    indices.extend(range(start, end + 1))
                else:
                    indices.append(int(part))
            
            selected_users = [unverified_users[i - 1] for i in indices if 0 < i <= len(unverified_users)]
        except (ValueError, IndexError):
            print("❌ Invalid selection")
            return
    
    if not selected_users:
        print("❌ No users selected")
        return
    
    # Confirm
    print("\n" + "=" * 70)
    print(f"📬 About to send confirmation emails to {len(selected_users)} user(s):")
    for user in selected_users:
        print(f"   • {user.email}")
    
    confirm = input("\nProceed? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Cancelled")
        return
    
    # Send emails
    print("\n" + "=" * 70)
    print("SENDING CONFIRMATION EMAILS")
    print("=" * 70)
    
    success_count = 0
    failed_count = 0
    
    for i, user in enumerate(selected_users, 1):
        print(f"\n[{i}/{len(selected_users)}]")
        if send_confirmation_email(client, user.email):
            success_count += 1
        else:
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n✅ Successfully sent: {success_count}")
    print(f"❌ Failed: {failed_count}")
    
    if success_count > 0:
        print("\n📬 Next steps:")
        print("  1. Check Resend dashboard: https://resend.com/emails")
        print("  2. Users should check inbox AND spam folder")
        print("  3. Verify confirmations: python scripts/check_user_verification.py")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
