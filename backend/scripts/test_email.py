#!/usr/bin/env python3
"""
Test Email Delivery
Sends a test email to verify email service is working.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from services.email_service import send_test_email

def main():
    print("=" * 70)
    print("EMAIL DELIVERY TEST")
    print("=" * 70)
    
    # Check configuration
    resend_key = os.getenv('RESEND_API_KEY')
    from_email = os.getenv('RESEND_FROM_EMAIL', 'hello@slateone.studio')
    
    if not resend_key:
        print("❌ RESEND_API_KEY not set in .env")
        sys.exit(1)
    
    print(f"\n📧 Configuration:")
    print(f"   From: {from_email}")
    print(f"   API Key: {resend_key[:10]}...{resend_key[-4:]}")
    
    # Get recipient email
    to_email = input("\nEnter recipient email address: ").strip()
    
    if not to_email:
        print("❌ Email address required")
        sys.exit(1)
    
    print(f"\n📤 Sending test email to: {to_email}")
    print("   Please wait...")
    
    # Send test email
    result = send_test_email(to_email)
    
    print("\n" + "=" * 70)
    
    if 'error' in result:
        print("❌ FAILED")
        print(f"   Error: {result['error']}")
        print("\n💡 Common issues:")
        print("   • Domain not verified in Resend")
        print("   • Invalid API key")
        print("   • Rate limit exceeded")
        print("\n🔧 Try:")
        print("   1. Switch to onboarding@resend.dev in .env")
        print("   2. Verify domain in Resend dashboard")
        print("   3. Check Resend logs: https://resend.com/emails")
    else:
        print("✅ SUCCESS")
        print(f"   Email ID: {result.get('id', 'N/A')}")
        print(f"\n📬 Check inbox: {to_email}")
        print("   (May take 1-2 minutes to arrive)")
        print("\n🔍 Verify delivery:")
        print(f"   → Resend Dashboard: https://resend.com/emails/{result.get('id', '')}")
        print("   → Check spam folder if not in inbox")
    
    print("=" * 70)

if __name__ == '__main__':
    main()
