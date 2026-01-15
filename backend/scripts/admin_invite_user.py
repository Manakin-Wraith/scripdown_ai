"""
Admin Invite User - Create new user account and send invite email.
Use this when you want to create an account for someone as an admin.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Missing Supabase credentials in .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def invite_new_user(email):
    """Admin invites a new user - creates account and sends invite email."""
    print(f"\n📧 Inviting new user: {email}")
    
    try:
        # Check if user already exists
        users = supabase.auth.admin.list_users()
        existing = next((u for u in users if u.email == email), None)
        
        if existing:
            print(f"❌ User already exists: {email}")
            print(f"   User ID: {existing.id}")
            print(f"   Created: {existing.created_at}")
            
            if existing.email_confirmed_at:
                print(f"   ✅ Email already confirmed on: {existing.email_confirmed_at}")
            else:
                print(f"   ⚠️  Email NOT confirmed - use resend_confirmation_email.py instead")
            
            return False
        
        # Invite new user (creates account and sends email)
        result = supabase.auth.admin.invite_user_by_email(
            email,
            options={
                'redirect_to': f'{FRONTEND_URL}/auth/callback'
            }
        )
        
        print(f"✅ User invited successfully!")
        print(f"   Email: {email}")
        print(f"   An invitation email has been sent")
        print(f"   User will set their password when they click the link")
        
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        
        if 'already exists' in error_msg or 'duplicate' in error_msg:
            print(f"❌ User already exists: {email}")
            print(f"   Use resend_confirmation_email.py to resend confirmation")
        else:
            print(f"❌ Error inviting user: {e}")
        
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("ADMIN INVITE NEW USER")
    print("=" * 70)
    print("\nThis creates a NEW user account and sends an invite email.")
    print("If the user already exists, use resend_confirmation_email.py instead.\n")
    
    # Email to invite
    email = input("Enter email address to invite: ").strip()
    
    if not email:
        print("❌ Email address required")
        sys.exit(1)
    
    success = invite_new_user(email)
    
    print("\n" + "=" * 70)
    if success:
        print("✅ DONE - Invitation email sent")
        print(f"   User will receive an email at: {email}")
        print(f"   They'll click the link to set their password")
    else:
        print("❌ FAILED - See error above")
    print("=" * 70)
