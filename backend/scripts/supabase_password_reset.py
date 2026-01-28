#!/usr/bin/env python3
"""
Supabase Native Password Reset

Uses Supabase's built-in password reset system which has better deliverability
than custom emails. Supabase sends the email directly from their infrastructure.

Usage:
    python supabase_password_reset.py <user_email>
"""

import sys
import os
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

from db.supabase_client import get_supabase_admin


def trigger_password_reset(email: str):
    """
    Trigger Supabase's native password reset email.
    
    This uses Supabase's built-in email system which:
    - Has better deliverability (less likely to be spam)
    - Uses Supabase's email infrastructure
    - Automatically handles the reset flow
    """
    try:
        supabase = get_supabase_admin()
        
        print(f"\n🔍 Checking if user exists: {email}")
        
        # Check if user exists in profiles
        response = supabase.table('profiles').select('*').eq('email', email).execute()
        
        if not response.data or len(response.data) == 0:
            print(f"❌ User not found: {email}")
            print("   Make sure the email is correct and the user has signed up.")
            return False
        
        user = response.data[0]
        full_name = user.get('full_name', 'User')
        print(f"✅ Found user: {full_name}")
        
        # Trigger password reset via Supabase Auth
        print(f"\n📧 Triggering Supabase password reset email...")
        print(f"   This will send an email from Supabase's system")
        
        # Use Supabase's password reset API
        reset_response = supabase.auth.reset_password_email(
            email,
            {
                'redirect_to': f"{os.getenv('FRONTEND_URL', 'https://app.slateone.studio')}/reset-password"
            }
        )
        
        print(f"✅ Password reset email triggered successfully!")
        print(f"\n💡 Instructions for user:")
        print(f"   1. Check inbox for email from Supabase (noreply@mail.app.supabase.io)")
        print(f"   2. Check spam/junk folder if not in inbox")
        print(f"   3. Click the reset link in the email")
        print(f"   4. Set a new password")
        print(f"\n📝 Note: The reset link expires in 1 hour")
        
        return True
        
    except Exception as e:
        print(f"❌ Error triggering password reset: {e}")
        print(f"\n🔧 Troubleshooting:")
        print(f"   1. Verify SUPABASE_SERVICE_KEY is set correctly")
        print(f"   2. Check Supabase email settings in dashboard")
        print(f"   3. Ensure email templates are configured")
        return False


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python supabase_password_reset.py <user_email>")
        print("\nExample:")
        print("  python supabase_password_reset.py jawitz@gmail.com")
        sys.exit(1)
    
    email = sys.argv[1].strip().lower()
    
    print("=" * 70)
    print("🔐 Supabase Native Password Reset")
    print("=" * 70)
    
    success = trigger_password_reset(email)
    
    print("\n" + "=" * 70)
    if success:
        print("✅ DONE - Password reset email sent via Supabase!")
    else:
        print("❌ FAILED - Could not trigger password reset")
    print("=" * 70 + "\n")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
