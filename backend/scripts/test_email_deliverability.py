"""
Test email deliverability by sending to mail-tester.com
This will give you a spam score and identify specific issues.
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.email_service import send_early_access_reminder

def main():
    print("=" * 70)
    print("EMAIL DELIVERABILITY TEST")
    print("=" * 70)
    print("\nThis script helps you test if your emails are landing in spam.")
    print("\nSTEPS:")
    print("1. Go to https://www.mail-tester.com")
    print("2. Copy the unique email address shown (e.g., test-abc123@srv1.mail-tester.com)")
    print("3. Paste it below")
    print("4. We'll send your reminder email to that address")
    print("5. Go back to mail-tester.com and click 'Then check your score'")
    print("6. Review your spam score (aim for 8/10 or higher)")
    print("\n" + "=" * 70)
    
    test_email = input("\nPaste the mail-tester.com email address: ").strip()
    
    if not test_email:
        print("❌ No email address provided")
        return
    
    # Accept both mail-tester.com and srv1.mail-tester.com formats
    if 'mail-tester.com' not in test_email:
        print("❌ Invalid mail-tester.com email address")
        print("   Expected format: test-xxxxx@srv1.mail-tester.com")
        return
    
    print(f"\n📧 Sending test email to: {test_email}")
    print("   Using: Early Access Reminder template")
    
    # Send the reminder email
    result = send_early_access_reminder(test_email, "Test User")
    
    if 'error' in result:
        print(f"\n❌ Error: {result['error']}")
    else:
        print(f"\n✅ Email sent successfully!")
        print(f"   Resend ID: {result.get('id', 'N/A')}")
        print("\n" + "=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print("1. Go back to https://www.mail-tester.com")
        print("2. Click 'Then check your score'")
        print("3. Review your spam score and issues")
        print("\n📊 WHAT TO LOOK FOR:")
        print("   • Score 8-10/10 = Good deliverability")
        print("   • Score 5-7/10 = May land in spam")
        print("   • Score 0-4/10 = Will likely be blocked")
        print("\n🔧 COMMON ISSUES:")
        print("   • Missing SPF/DKIM/DMARC (we have these ✅)")
        print("   • Spam trigger words in content")
        print("   • Too many links")
        print("   • Missing unsubscribe link")
        print("   • Missing physical address")
        print("=" * 70)

if __name__ == '__main__':
    main()
