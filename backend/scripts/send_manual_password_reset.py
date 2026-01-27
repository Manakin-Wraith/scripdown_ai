#!/usr/bin/env python3
"""
Manual Password Reset Email Sender

Sends a custom password reset email via Resend (hello@slateone.studio)
to avoid Supabase emails landing in spam.

Usage:
    python send_manual_password_reset.py <user_email>
"""

import sys
import os
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

from services.email_service import send_password_reset_email
from db.supabase_client import get_supabase_admin


def get_user_info(email: str):
    """Get user info from Supabase."""
    try:
        supabase = get_supabase_admin()
        
        # Get user from profiles table
        response = supabase.table('profiles').select('*').eq('email', email).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None


def generate_reset_link(email: str) -> str:
    """
    Generate a password reset link using Supabase.
    
    Note: This uses Supabase's admin API to generate a recovery link.
    """
    try:
        supabase = get_supabase_admin()
        
        # Generate reset token via Supabase Admin API
        result = supabase.auth.admin.generate_link({
            'type': 'recovery',
            'email': email
        })
        
        # The result has properties attribute with action_link
        if result and hasattr(result, 'properties'):
            props = result.properties
            if hasattr(props, 'action_link'):
                return props.action_link
            # Try as dict if not attribute
            if isinstance(props, dict) and 'action_link' in props:
                return props['action_link']
        
        # Fallback: construct the link manually
        app_url = os.getenv('FRONTEND_URL', 'https://app.slateone.studio')
        return f"{app_url}/reset-password"
        
    except Exception as e:
        print(f"Error generating reset link: {e}")
        # Fallback URL - user can still request reset through UI
        app_url = os.getenv('FRONTEND_URL', 'https://app.slateone.studio')
        return f"{app_url}/reset-password"


def send_reset_email(email: str):
    """Send password reset email to user."""
    print(f"\n🔍 Looking up user: {email}")
    
    # Get user info
    user = get_user_info(email)
    
    if not user:
        print(f"❌ User not found: {email}")
        print("   Make sure the email is correct and the user has signed up.")
        return False
    
    full_name = user.get('full_name', 'User')
    print(f"✅ Found user: {full_name}")
    
    # Generate reset link
    print("\n🔗 Generating password reset link...")
    reset_url = generate_reset_link(email)
    print(f"   Reset URL: {reset_url}")
    
    # Send email via Resend
    print(f"\n📧 Sending password reset email via Resend (hello@slateone.studio)...")
    result = send_password_reset_email(
        to_email=email,
        reset_url=reset_url,
        full_name=full_name
    )
    
    if result and 'error' not in result:
        print(f"✅ Email sent successfully!")
        print(f"   Resend Email ID: {result.get('id')}")
        print(f"\n💡 The user should check their inbox for an email from hello@slateone.studio")
        return True
    else:
        print(f"❌ Failed to send email: {result.get('error', 'Unknown error')}")
        return False


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python send_manual_password_reset.py <user_email>")
        print("\nExample:")
        print("  python send_manual_password_reset.py user@example.com")
        sys.exit(1)
    
    email = sys.argv[1].strip().lower()
    
    print("=" * 60)
    print("🔐 Manual Password Reset Email Sender")
    print("=" * 60)
    
    success = send_reset_email(email)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DONE - Password reset email sent!")
    else:
        print("❌ FAILED - Could not send email")
    print("=" * 60 + "\n")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
