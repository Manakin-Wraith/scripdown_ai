#!/usr/bin/env python3
"""
Test email confirmation flow by generating a magic link for an unverified user.
This tests the full flow: email delivery -> link click -> confirmation -> redirect
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

def test_confirmation_email():
    """Generate and send a confirmation email to test the flow."""
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ Missing Supabase credentials")
        return
    
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # Test user
    test_email = 'g.mostertpot@gmail.com'
    
    print("\n" + "=" * 70)
    print("EMAIL CONFIRMATION FLOW TEST")
    print("=" * 70)
    print(f"\n📧 Test user: {test_email}")
    print("\nThis will:")
    print("  1. Generate a confirmation link")
    print("  2. Send email via Resend SMTP (hello@slateone.studio)")
    print("  3. User clicks link → https://app.slateone.studio/auth/confirm")
    print("  4. Frontend verifies token → redirects to /scripts")
    
    confirm = input("\nProceed with test? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Cancelled")
        return
    
    print("\n" + "=" * 70)
    print("GENERATING CONFIRMATION LINK")
    print("=" * 70)
    
    try:
        # Generate email confirmation link
        # This will send an email via the configured SMTP (Resend)
        result = client.auth.admin.generate_link({
            'type': 'signup',
            'email': test_email,
            'options': {
                'redirect_to': 'https://app.slateone.studio/auth/confirm'
            }
        })
        
        print(f"\n✅ Confirmation email sent to: {test_email}")
        print(f"\n🔗 Magic link (for debugging):")
        print(f"   {result.properties.action_link}")
        print(f"\n📬 Email should arrive from: hello@slateone.studio")
        print(f"   Subject: Confirm your signup")
        
        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("\n1. Check Resend dashboard:")
        print("   https://resend.com/emails")
        print("   • Verify email was sent")
        print("   • Check delivery status")
        
        print("\n2. Ask user to check email:")
        print("   • Check inbox AND spam folder")
        print("   • Search for 'SlateOne' or 'hello@slateone.studio'")
        print("   • Click 'Confirm Email Address' button")
        
        print("\n3. Verify confirmation flow:")
        print("   • Link should open: https://app.slateone.studio/auth/confirm?token_hash=...")
        print("   • Should see 'Email Confirmed!' message")
        print("   • Should redirect to /scripts")
        
        print("\n4. Check user status:")
        print("   • Run: python scripts/check_user_verification.py")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  • Verify Custom SMTP is configured in Supabase")
        print("  • Check RESEND_API_KEY is correct")
        print("  • Verify domain (slateone.studio) is verified in Resend")

if __name__ == '__main__':
    test_confirmation_email()
