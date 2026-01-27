#!/usr/bin/env python3
"""
Send beta unlock email to a single user
Quick script to send access email without interactive prompts
"""

import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from services.email_service import send_early_access_invite


def send_beta_unlock(email: str):
    """Send beta unlock email to specific user."""
    print(f"\n📧 Sending beta unlock email to: {email}")
    
    result = send_early_access_invite(
        to_email=email,
        first_name=None  # Will use "there" as fallback
    )
    
    if result and 'error' not in result:
        print(f"✅ Email sent successfully!")
        print(f"   Resend Email ID: {result.get('id')}")
        return True
    else:
        print(f"❌ Failed to send email: {result.get('error', 'Unknown error')}")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python send_beta_unlock_single.py <email>")
        sys.exit(1)
    
    email = sys.argv[1].strip().lower()
    
    print("=" * 60)
    print("🚀 Send Beta Unlock Email")
    print("=" * 60)
    
    success = send_beta_unlock(email)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DONE - Beta unlock email sent!")
        print("\nThe user can now:")
        print("  1. Go to https://app.slateone.studio/login")
        print("  2. Sign up with their email")
        print("  3. Get 30 days free access")
    else:
        print("❌ FAILED - Could not send email")
    print("=" * 60 + "\n")
    
    sys.exit(0 if success else 1)
