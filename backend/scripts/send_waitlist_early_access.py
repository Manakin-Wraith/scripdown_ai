"""
Send early access emails to waitlist users from Notel Supabase project.
Handles cross-project email sending for www.slateone.studio waitlist.
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

# Main SlateOne project (for early_access_users table)
MAIN_SUPABASE_URL = os.getenv('SUPABASE_URL')
MAIN_SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Notel project (for waitlist table) - need separate credentials
NOTEL_SUPABASE_URL = os.getenv('NOTEL_SUPABASE_URL')
NOTEL_SUPABASE_KEY = os.getenv('NOTEL_SUPABASE_SERVICE_KEY')


def get_waitlist_users():
    """
    Fetch waitlist users from Notel Supabase project.
    Returns list of users who haven't been sent early access yet.
    """
    if not NOTEL_SUPABASE_URL or not NOTEL_SUPABASE_KEY:
        print("⚠️  Notel Supabase credentials not found in .env")
        print("   Add NOTEL_SUPABASE_URL and NOTEL_SUPABASE_SERVICE_KEY")
        return []
    
    try:
        notel_client = create_client(NOTEL_SUPABASE_URL, NOTEL_SUPABASE_KEY)
        
        # Fetch waitlist users (adjust query based on your table structure)
        response = notel_client.table('waitlist')\
            .select('*')\
            .execute()
        
        return response.data
    except Exception as e:
        print(f"❌ Error fetching waitlist users: {e}")
        return []


def register_in_main_project(email, first_name=None):
    """
    Register waitlist user in main SlateOne early_access_users table.
    """
    if not MAIN_SUPABASE_URL or not MAIN_SUPABASE_KEY:
        print("❌ Main Supabase credentials not found")
        return False
    
    try:
        main_client = create_client(MAIN_SUPABASE_URL, MAIN_SUPABASE_KEY)
        
        # Check if already registered
        existing = main_client.table('early_access_users')\
            .select('*')\
            .eq('email', email)\
            .execute()
        
        if existing.data:
            print(f"  ℹ️  Already registered in main project")
            return True
        
        # Register new user
        main_client.table('early_access_users').insert({
            'email': email,
            'first_name': first_name,
            'status': 'invited',
            'source': 'waitlist'
        }).execute()
        
        print(f"  ✓ Registered in main project")
        return True
    except Exception as e:
        print(f"  ❌ Error registering: {e}")
        return False


def main():
    print("=" * 70)
    print("WAITLIST EARLY ACCESS CAMPAIGN")
    print("=" * 70)
    print("\nThis script:")
    print("  1. Fetches waitlist users from Notel Supabase project")
    print("  2. Registers them in main SlateOne project")
    print("  3. Sends enhanced early access emails")
    print("\n" + "=" * 70)
    
    # Option 1: Fetch from Notel Supabase (if credentials available)
    if NOTEL_SUPABASE_URL and NOTEL_SUPABASE_KEY:
        print("\n📊 Fetching waitlist users from Notel project...")
        users = get_waitlist_users()
        
        if users:
            print(f"Found {len(users)} waitlist user(s):\n")
            for i, user in enumerate(users, 1):
                email = user.get('email', 'N/A')
                name = user.get('name') or user.get('first_name', 'N/A')
                created = user.get('created_at', 'N/A')
                print(f"  {i}. {name} ({email}) - Joined: {created}")
        else:
            print("No users found or error occurred.")
            users = []
    else:
        print("\n⚠️  Notel Supabase credentials not configured.")
        print("   Falling back to manual entry mode.\n")
        users = []
    
    # Option 2: Manual entry if no Notel access
    if not users:
        print("\n" + "=" * 70)
        print("MANUAL ENTRY MODE")
        print("=" * 70)
        print("\nEnter waitlist user details (or press Enter to skip):")
        
        manual_users = []
        while True:
            email = input("\nEmail address (or Enter to finish): ").strip()
            if not email:
                break
            
            name = input("First name (optional): ").strip() or None
            manual_users.append({'email': email, 'first_name': name})
        
        if not manual_users:
            print("\n❌ No users to process. Exiting.")
            return
        
        users = manual_users
        print(f"\n✓ {len(users)} user(s) entered manually")
    
    # Confirm before sending
    print("\n" + "=" * 70)
    confirm = input(f"\nSend early access emails to {len(users)} user(s)? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Cancelled. No emails sent.")
        return
    
    # Process each user
    print("\n" + "=" * 70)
    print("PROCESSING WAITLIST USERS")
    print("=" * 70)
    
    sent_count = 0
    failed_count = 0
    
    for i, user in enumerate(users, 1):
        email = user.get('email')
        first_name = user.get('first_name') or user.get('name')
        
        print(f"\n[{i}/{len(users)}] Processing: {email}")
        
        if not email:
            print("  ⚠️  Skipped: No email address")
            failed_count += 1
            continue
        
        # Register in main project
        if not register_in_main_project(email, first_name):
            failed_count += 1
            continue
        
        # Send early access email
        result = send_early_access_reminder(email, first_name)
        
        if 'error' in result:
            print(f"  ❌ Failed to send email: {result['error']}")
            failed_count += 1
        else:
            print(f"  ✅ Email sent successfully (ID: {result.get('id', 'N/A')})")
            sent_count += 1
        
        # Rate limiting
        if i < len(users):
            time.sleep(0.6)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total users: {len(users)}")
    print(f"Emails sent: {sent_count}")
    print(f"Failed: {failed_count}")
    print("=" * 70)
    
    if sent_count > 0:
        print("\n✅ Waitlist users have been sent early access invites!")
        print("   They should receive emails with:")
        print("   • Subject: 'SlateOne Early Access: Your testing account is waiting'")
        print("   • 10/10 spam score optimization")
        print("   • 3-decision framework for better engagement")


if __name__ == '__main__':
    main()
