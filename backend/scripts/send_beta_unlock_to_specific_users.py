#!/usr/bin/env python3
"""
Send "Unlock Beta SlateOne Access" emails to specific waitlist users.
Interactive script to select and send early access emails one by one.
"""

import sys
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client
from services.email_service import send_early_access_reminder

# Main SlateOne project
MAIN_SUPABASE_URL = os.getenv('SUPABASE_URL')
MAIN_SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Notel project (for waitlist)
NOTEL_SUPABASE_URL = os.getenv('NOTEL_SUPABASE_URL')
NOTEL_SUPABASE_KEY = os.getenv('NOTEL_SUPABASE_SERVICE_KEY')


def get_waitlist_users():
    """Fetch all waitlist users from Notel Supabase project."""
    if not NOTEL_SUPABASE_URL or not NOTEL_SUPABASE_KEY:
        print("⚠️  Notel Supabase credentials not found in .env")
        return []
    
    try:
        notel_client = create_client(NOTEL_SUPABASE_URL, NOTEL_SUPABASE_KEY)
        response = notel_client.table('waitlist').select('*').order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"❌ Error fetching waitlist users: {e}")
        return []


def get_early_access_users():
    """Get all users in early_access_users table."""
    if not MAIN_SUPABASE_URL or not MAIN_SUPABASE_KEY:
        return []
    
    try:
        main_client = create_client(MAIN_SUPABASE_URL, MAIN_SUPABASE_KEY)
        response = main_client.table('early_access_users').select('*').order('invited_at', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"⚠️  Error fetching early access users: {e}")
        return []


def register_in_early_access(email, first_name=None):
    """Register user in early_access_users table if not already there."""
    if not MAIN_SUPABASE_URL or not MAIN_SUPABASE_KEY:
        return False
    
    try:
        main_client = create_client(MAIN_SUPABASE_URL, MAIN_SUPABASE_KEY)
        
        # Upsert to handle duplicates
        main_client.table('early_access_users').upsert({
            'email': email,
            'first_name': first_name,
            'status': 'invited',
            'source': 'waitlist',
            'invited_at': 'now()'
        }, on_conflict='email').execute()
        
        return True
    except Exception as e:
        print(f"  ❌ Error registering: {e}")
        return False


def main():
    print("=" * 70)
    print("🚀 SEND BETA UNLOCK EMAILS TO SPECIFIC USERS")
    print("=" * 70)
    print("\nThis script sends the 'Unlock Beta SlateOne Access' email")
    print("to specific waitlist users you select.\n")
    print("=" * 70)
    
    # Fetch waitlist users
    print("\n📊 Fetching waitlist users from Notel project...")
    waitlist_users = get_waitlist_users()
    
    if not waitlist_users:
        print("❌ No waitlist users found or error occurred.")
        return
    
    print(f"✓ Found {len(waitlist_users)} waitlist user(s)")
    
    # Fetch early access users to show status
    print("\n🔍 Checking early access status...")
    early_access_users = get_early_access_users()
    early_access_emails = {user['email'].lower() for user in early_access_users}
    
    # Display all users with status
    print("\n" + "=" * 70)
    print("WAITLIST USERS")
    print("=" * 70)
    
    for i, user in enumerate(waitlist_users, 1):
        email = user.get('email', 'N/A')
        name = user.get('name') or user.get('first_name', 'N/A')
        created = user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'
        
        # Check if already in early access
        status = "✅ Already invited" if email.lower() in early_access_emails else "⏳ Not invited yet"
        
        print(f"{i:3}. {name:20} | {email:35} | {created} | {status}")
    
    # Interactive selection
    print("\n" + "=" * 70)
    print("SELECT USERS TO SEND EMAILS")
    print("=" * 70)
    print("\nOptions:")
    print("  • Enter user numbers (e.g., 1,3,5 or 1-5)")
    print("  • Enter 'all' to send to everyone")
    print("  • Enter 'new' to send only to users not yet invited")
    print("  • Press Enter to cancel")
    
    selection = input("\nYour selection: ").strip().lower()
    
    if not selection:
        print("❌ Cancelled. No emails sent.")
        return
    
    # Parse selection
    selected_users = []
    
    if selection == 'all':
        selected_users = waitlist_users
    elif selection == 'new':
        selected_users = [
            user for user in waitlist_users 
            if user.get('email', '').lower() not in early_access_emails
        ]
    else:
        # Parse numbers and ranges
        indices = set()
        for part in selection.split(','):
            part = part.strip()
            if '-' in part:
                # Range (e.g., 1-5)
                try:
                    start, end = map(int, part.split('-'))
                    indices.update(range(start, end + 1))
                except:
                    print(f"⚠️  Invalid range: {part}")
            else:
                # Single number
                try:
                    indices.add(int(part))
                except:
                    print(f"⚠️  Invalid number: {part}")
        
        # Get selected users
        selected_users = [
            waitlist_users[i-1] for i in sorted(indices) 
            if 1 <= i <= len(waitlist_users)
        ]
    
    if not selected_users:
        print("❌ No valid users selected.")
        return
    
    # Confirm
    print(f"\n📬 Ready to send emails to {len(selected_users)} user(s):")
    for user in selected_users:
        email = user.get('email', 'N/A')
        name = user.get('name') or user.get('first_name', 'N/A')
        print(f"   • {name} ({email})")
    
    confirm = input(f"\nSend 'Unlock Beta Access' emails? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Cancelled. No emails sent.")
        return
    
    # Send emails
    print("\n" + "=" * 70)
    print("SENDING EMAILS")
    print("=" * 70)
    
    sent_count = 0
    failed_count = 0
    
    for i, user in enumerate(selected_users, 1):
        email = user.get('email')
        first_name = user.get('first_name') or user.get('name')
        
        print(f"\n[{i}/{len(selected_users)}] Processing: {email}")
        
        if not email:
            print("  ⚠️  Skipped: No email address")
            failed_count += 1
            continue
        
        # Register in early access table
        print("  📝 Registering in early_access_users...")
        if not register_in_early_access(email, first_name):
            failed_count += 1
            continue
        
        print("  ✓ Registered")
        
        # Send email
        print("  📧 Sending beta unlock email...")
        result = send_early_access_reminder(email, first_name)
        
        if 'error' in result:
            print(f"  ❌ Failed to send email: {result['error']}")
            failed_count += 1
        else:
            print(f"  ✅ Email sent successfully (ID: {result.get('id', 'N/A')})")
            sent_count += 1
        
        # Rate limiting
        if i < len(selected_users):
            time.sleep(0.6)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total selected: {len(selected_users)}")
    print(f"Emails sent: {sent_count}")
    print(f"Failed: {failed_count}")
    print("=" * 70)
    
    if sent_count > 0:
        print("\n✅ Beta unlock emails sent successfully!")
        print("\n📧 Email details:")
        print("   • Subject: 'SlateOne Early Access: Your testing account is waiting'")
        print("   • From: hello@slateone.studio")
        print("   • CTA: Sign up at app.slateone.studio/login")
        print("   • Benefit: 30 days free access, no credit card")
        print("\n💡 Next steps:")
        print("   1. Check Resend dashboard for delivery status")
        print("   2. Monitor signups in Supabase auth.users table")
        print("   3. Follow up with users who don't sign up within 3-5 days")


if __name__ == '__main__':
    main()
