"""
Send reminder emails to early access users who haven't signed up yet.
Fetches users from Supabase early_access_users table.
"""

import sys
import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client
from services.email_service import send_early_access_reminder

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_all_auth_users():
    """Fetch all authenticated users from Supabase Auth"""
    try:
        response = supabase.auth.admin.list_users()
        return {user.email: user for user in response if user.email}
    except Exception as e:
        print(f"❌ Error fetching auth users: {e}")
        return {}


def get_early_access_users_without_signup():
    """
    Fetch early access users who haven't signed up yet.
    
    This function:
    1. Queries users with status 'invited'
    2. Cross-references with auth.users to verify they truly haven't signed up
    3. Auto-syncs any users who signed up but weren't marked as such
    4. Returns only users who genuinely haven't signed up
    """
    try:
        # Get all invited users
        print("   Fetching invited users...")
        invited = supabase.table('early_access_users')\
            .select('*')\
            .eq('status', 'invited')\
            .execute()
        
        if not invited.data:
            return []
        
        # Get all authenticated users
        print("   Cross-referencing with authenticated users...")
        auth_users = get_all_auth_users()
        
        # Filter out users who have actually signed up
        truly_not_signed_up = []
        auto_synced = 0
        
        for user in invited.data:
            email = user['email']
            
            if email in auth_users:
                # User has signed up but status wasn't updated - sync now
                auth_user = auth_users[email]
                
                try:
                    supabase.table('early_access_users')\
                        .update({
                            'user_id': auth_user.id,
                            'status': 'signed_up',
                            'signed_up_at': auth_user.created_at.isoformat() if hasattr(auth_user.created_at, 'isoformat') else str(auth_user.created_at),
                            'metadata': {
                                'last_sync_check': datetime.now(timezone.utc).isoformat(),
                                'sync_source': 'auto_reminder_script'
                            }
                        })\
                        .eq('id', user['id'])\
                        .execute()
                    
                    auto_synced += 1
                    print(f"   ✅ Auto-synced: {email}")
                except Exception as e:
                    print(f"   ⚠️  Failed to auto-sync {email}: {e}")
            else:
                # User genuinely hasn't signed up
                truly_not_signed_up.append(user)
        
        if auto_synced > 0:
            print(f"   📊 Auto-synced {auto_synced} user(s) who had signed up")
        
        return truly_not_signed_up
        
    except Exception as e:
        print(f"❌ Error fetching users from Supabase: {e}")
        return []


def main():
    print("=" * 70)
    print("EARLY ACCESS REMINDER CAMPAIGN")
    print("=" * 70)
    
    # Fetch users who haven't signed up
    print("\n📊 Fetching early access users from Supabase...")
    users = get_early_access_users_without_signup()
    
    if not users:
        print("✅ No users found who need reminders (or error occurred)")
        return
    
    print(f"Found {len(users)} user(s) who haven't signed up yet:\n")
    
    # Display users
    for i, user in enumerate(users, 1):
        email = user.get('email', 'N/A')
        name = user.get('first_name', 'N/A')
        created = user.get('created_at', 'N/A')
        print(f"  {i}. {name} ({email}) - Invited: {created}")
    
    print("\n" + "=" * 70)
    
    # Confirmation
    confirm = input(f"\nSend reminder emails to these {len(users)} user(s)? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Cancelled. No emails sent.")
        return
    
    print("\n" + "=" * 70)
    print("SENDING REMINDERS")
    print("=" * 70)
    
    sent_count = 0
    failed_count = 0
    
    for i, user in enumerate(users, 1):
        email = user.get('email')
        first_name = user.get('first_name')
        
        print(f"\n[{i}/{len(users)}] Sending to: {email}")
        
        if not email:
            print("  ⚠️  Skipped: No email address")
            failed_count += 1
            continue
        
        # Send reminder email
        result = send_early_access_reminder(email, first_name)
        
        if 'error' in result:
            print(f"  ❌ Failed: {result['error']}")
            failed_count += 1
        else:
            print(f"  ✅ Sent successfully (ID: {result.get('id', 'N/A')})")
            sent_count += 1
        
        # Rate limiting: Wait 0.6 seconds between emails (max 2 per second)
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


if __name__ == '__main__':
    main()
