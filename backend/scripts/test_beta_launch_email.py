"""
Test script for beta launch email.
Run this to send a test beta launch email to verify the email service is working.

Usage:
    python scripts/test_beta_launch_email.py
"""

import sys
import os
from dotenv import load_dotenv

# Add parent directory to path to import from services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env file
load_dotenv()

from services.email_service import send_beta_launch_email, is_configured


def main():
    """Send test beta launch email."""
    
    # Check if email service is configured
    if not is_configured():
        print("❌ Error: Email service not configured")
        print("Please set RESEND_API_KEY in your .env file")
        return
    
    print("🎬 SlateOne Beta Launch Email Test")
    print("=" * 50)
    
    # Get test email from user
    test_email = input("\nEnter test email address: ").strip()
    
    if not test_email:
        print("❌ Error: Email address is required")
        return
    
    # Get test user name
    test_name = input("Enter test user name (default: Test User): ").strip()
    if not test_name:
        test_name = "Test User"
    
    # Get user status
    print("\nSelect user status:")
    print("1. New user (default)")
    print("2. Trial user")
    print("3. Waitlist user")
    status_choice = input("Enter choice (1-3): ").strip()
    
    status_map = {
        '1': 'new',
        '2': 'trial',
        '3': 'waitlist'
    }
    user_status = status_map.get(status_choice, 'new')
    
    print(f"\n📧 Sending beta launch email to: {test_email}")
    print(f"👤 User name: {test_name}")
    print(f"📊 User status: {user_status}")
    print("\nSending...")
    
    # Send email
    result = send_beta_launch_email(
        to_email=test_email,
        user_name=test_name,
        user_status=user_status
    )
    
    # Check result
    if 'error' in result:
        print(f"\n❌ Error sending email: {result['error']}")
    else:
        print(f"\n✅ Email sent successfully!")
        print(f"📬 Email ID: {result.get('id', 'N/A')}")
        print(f"\nCheck your inbox at: {test_email}")
        print("\nNote: Check spam folder if you don't see it in a few minutes.")


if __name__ == '__main__':
    main()
