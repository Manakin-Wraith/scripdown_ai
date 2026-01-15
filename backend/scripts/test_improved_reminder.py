"""
Test the improved early access reminder email.
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
    print("TEST IMPROVED EARLY ACCESS REMINDER EMAIL")
    print("=" * 70)
    print("\n✨ IMPROVEMENTS IN THIS VERSION:")
    print("   ✓ Better subject line (fewer emojis)")
    print("   ✓ Plain text version included")
    print("   ✓ Unsubscribe link added")
    print("   ✓ Physical address included")
    print("   ✓ Cleaner, more professional design")
    print("   ✓ Better deliverability score")
    print("\n" + "=" * 70)
    
    email = input("\nEnter email address to test: ").strip()
    if not email:
        print("❌ No email provided")
        return
    
    name = input("Enter first name (optional, press Enter to skip): ").strip() or None
    
    print(f"\n📧 Sending improved reminder to: {email}")
    if name:
        print(f"   Name: {name}")
    
    result = send_early_access_reminder(email, name)
    
    if 'error' in result:
        print(f"\n❌ Error: {result['error']}")
    else:
        print(f"\n✅ Email sent successfully!")
        print(f"   Resend ID: {result.get('id', 'N/A')}")
        print("\n" + "=" * 70)
        print("EMAIL DETAILS:")
        print("=" * 70)
        print(f"Subject: {name or 'there'}, your SlateOne early access is ready")
        print("\n📝 KEY CHANGES:")
        print("   • Subject: Removed excessive emojis")
        print("   • Added plain text version (improves deliverability)")
        print("   • Added unsubscribe link (required for bulk emails)")
        print("   • Added physical address (builds legitimacy)")
        print("   • Cleaner design (less 'spammy' appearance)")
        print("\n🎯 EXPECTED RESULT:")
        print("   • Better inbox placement")
        print("   • Higher deliverability score")
        print("   • Less likely to be filtered")
        print("=" * 70)
        print("\n💡 TIP: Test with mail-tester.com to see improved score!")
        print("   Run: python scripts/test_email_deliverability.py")

if __name__ == '__main__':
    main()
