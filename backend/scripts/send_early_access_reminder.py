"""
Send early access reminder emails to invitees who haven't signed up yet.
Playful and inspiring tone to encourage testing.
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
    print("EARLY ACCESS REMINDER EMAIL")
    print("=" * 70)
    
    email = input("\nEnter email address: ").strip()
    if not email:
        print("❌ No email provided")
        return
    
    name = input("Enter first name (optional, press Enter to skip): ").strip() or None
    
    print(f"\n📧 Sending reminder to: {email}")
    if name:
        print(f"   Name: {name}")
    
    result = send_early_access_reminder(email, name)
    
    if 'error' in result:
        print(f"\n❌ Error: {result['error']}")
    else:
        print(f"\n✅ Reminder sent successfully!")
        print(f"   Resend ID: {result.get('id', 'N/A')}")
        print("\n" + "=" * 70)
        print("EMAIL PREVIEW:")
        print("=" * 70)
        print(f"Subject: 🎬 {name or 'there'}, we're rolling! SlateOne needs you on set")
        print("\nKey Message:")
        print("  • SlateOne is live and working")
        print("  • We need their feedback to make it better")
        print("  • Mission: Upload, breakdown, share thoughts")
        print("  • 30 days free access")
        print("\nTone: Playful, inspiring, urgent but friendly")
        print("=" * 70)

if __name__ == '__main__':
    main()
