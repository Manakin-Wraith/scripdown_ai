"""
Sync Early Access Users with Auth

Cross-references early_access_users table with auth.users to:
- Update user_id for users who have signed up
- Update status from 'invited' to 'signed_up'
- Set signed_up_at timestamp
- Track sync metadata

Usage:
    python scripts/sync_early_access_users.py
    python scripts/sync_early_access_users.py --dry-run
"""

import sys
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client

# Initialize Supabase client with admin access
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_all_auth_users():
    """Fetch all authenticated users from Supabase Auth"""
    try:
        # Note: list_users() may be paginated for large user bases
        response = supabase.auth.admin.list_users()
        return {user.email: user for user in response if user.email}
    except Exception as e:
        print(f"❌ Error fetching auth users: {e}")
        return {}


def sync_early_access_with_auth(dry_run=False):
    """
    Cross-reference early_access_users with auth.users
    and update status/user_id for users who have signed up
    
    Args:
        dry_run: If True, only report what would be synced without making changes
    """
    
    print("=" * 70)
    print("EARLY ACCESS USER SYNC")
    print("=" * 70)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")
    
    # Get all authenticated users
    print("📊 Fetching authenticated users...")
    auth_users = get_all_auth_users()
    print(f"   Found {len(auth_users)} authenticated users\n")
    
    # Get all invited early access users
    print("📊 Fetching early access users with 'invited' status...")
    try:
        early_access = supabase.table('early_access_users')\
            .select('id, email, status, user_id, invited_at')\
            .eq('status', 'invited')\
            .execute()
    except Exception as e:
        print(f"❌ Error fetching early access users: {e}")
        return
    
    invited_users = early_access.data if early_access.data else []
    print(f"   Found {len(invited_users)} invited users\n")
    
    if not invited_users:
        print("✅ No invited users to sync")
        return
    
    print("=" * 70)
    print("SYNC RESULTS")
    print("=" * 70)
    
    synced = 0
    not_found = 0
    errors = 0
    
    for user in invited_users:
        email = user['email']
        user_id = user['id']
        
        # Check if user exists in auth.users
        if email in auth_users:
            auth_user = auth_users[email]
            
            if dry_run:
                print(f"🔍 Would sync: {email}")
                print(f"   → user_id: {auth_user.id}")
                print(f"   → signed_up_at: {auth_user.created_at}")
                synced += 1
            else:
                try:
                    # Update early_access_users record
                    supabase.table('early_access_users')\
                        .update({
                            'user_id': auth_user.id,
                            'status': 'signed_up',
                            'signed_up_at': auth_user.created_at.isoformat() if hasattr(auth_user.created_at, 'isoformat') else str(auth_user.created_at),
                            'metadata': {
                                'last_sync_check': datetime.now(timezone.utc).isoformat(),
                                'sync_source': 'script'
                            }
                        })\
                        .eq('id', user_id)\
                        .execute()
                    
                    synced += 1
                    print(f"✅ Synced: {email}")
                except Exception as e:
                    errors += 1
                    print(f"❌ Error syncing {email}: {e}")
        else:
            not_found += 1
            print(f"⏳ Not signed up: {email}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total invited users: {len(invited_users)}")
    print(f"Synced: {synced}")
    print(f"Not signed up: {not_found}")
    if errors > 0:
        print(f"Errors: {errors}")
    
    if dry_run:
        print("\n💡 Run without --dry-run to apply changes")
    
    print("=" * 70)


def main():
    """Main entry point"""
    dry_run = '--dry-run' in sys.argv
    sync_early_access_with_auth(dry_run=dry_run)


if __name__ == '__main__':
    main()