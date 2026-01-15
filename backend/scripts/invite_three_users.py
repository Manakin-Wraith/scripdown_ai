"""
Invite 3 specific users: Meggan, Andre, and ttntshabele.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from supabase import create_client
from services.email_service import send_early_access_reminder

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def invite_user(email, first_name=None):
    """Invite user and send early access email."""
    print(f"\n📧 Processing: {email}")
    
    try:
        # Check if user already exists
        users = supabase.auth.admin.list_users()
        existing_user = next((u for u in users if u.email == email), None)
        
        if existing_user:
            if existing_user.email_confirmed_at:
                print(f"   ✅ User already exists and confirmed")
                print(f"      Sending early access reminder...")
                result = send_early_access_reminder(email, first_name)
                if result.get('success'):
                    print(f"   ✅ Early access email sent!")
                else:
                    print(f"   ❌ Failed to send email: {result.get('error')}")
                return True
            else:
                print(f"   ⚠️  User exists but not confirmed")
                print(f"      Resending confirmation email...")
                supabase.auth.admin.invite_user_by_email(email)
                print(f"   ✅ Confirmation email resent!")
                return True
        
        # Create new user via admin invite
        print(f"   Creating new user account...")
        result = supabase.auth.admin.invite_user_by_email(email)
        
        print(f"   ✅ User created! Confirmation email sent.")
        print(f"   User ID: {result.user.id}")
        
        # Also send early access email
        print(f"   Sending early access email...")
        email_result = send_early_access_reminder(email, first_name)
        if email_result.get('success'):
            print(f"   ✅ Early access email sent!")
        else:
            print(f"   ⚠️  Early access email failed: {email_result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

print("=" * 70)
print("INVITING 3 USERS")
print("=" * 70)

users = [
    {"email": "megganr@moleculemedia.co.za", "first_name": "Meggan"},
    {"email": "andrevanheerden@thevideoagency.co.za", "first_name": "Andre"},
    {"email": "ttntshabele@gmail.com", "first_name": None},
]

success_count = 0
failed_count = 0

for user in users:
    if invite_user(user['email'], user['first_name']):
        success_count += 1
    else:
        failed_count += 1

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total users: {len(users)}")
print(f"Successful: {success_count}")
print(f"Failed: {failed_count}")
print("=" * 70)
