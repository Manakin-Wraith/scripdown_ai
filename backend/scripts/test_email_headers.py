"""
Test script to send email and display what Resend is actually sending.
This helps diagnose SPF alignment issues.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.email_service import send_test_email

def main():
    print("=" * 60)
    print("EMAIL HEADER DIAGNOSTIC TEST")
    print("=" * 60)
    
    email = input("\nEnter your email address to receive test: ").strip()
    
    if not email:
        print("❌ No email provided")
        return
    
    print(f"\n📧 Sending test email to: {email}")
    print("\nAfter receiving the email:")
    print("1. Open the email in Gmail/Outlook")
    print("2. Click 'Show Original' or 'View Source'")
    print("3. Look for these headers:")
    print("   - Return-Path: (should be @slateone.studio)")
    print("   - From: (should be hello@slateone.studio)")
    print("   - Authentication-Results: (check SPF and DKIM)")
    print("\n" + "=" * 60)
    
    result = send_test_email(email)
    
    if 'error' in result:
        print(f"\n❌ Error: {result['error']}")
    else:
        print(f"\n✅ Email sent successfully!")
        print(f"Resend ID: {result.get('id', 'N/A')}")
        print("\nCheck your inbox and examine the headers.")

if __name__ == '__main__':
    main()
