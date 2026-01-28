"""
Test script for welcome credits email.
Send a test email to verify the template looks correct.
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.email_service import send_welcome_credits_email

def test_email():
    """Send test welcome credits email"""
    
    # CHANGE THIS TO YOUR EMAIL
    test_email = "g.mostertpot@gmail.com"
    test_name = "Test User"
    
    print(f"\n{'='*70}")
    print("WELCOME CREDITS EMAIL - TEST")
    print(f"{'='*70}")
    print(f"Sending test email to: {test_email}")
    print(f"User name: {test_name}")
    print(f"Credits: 10")
    print(f"{'='*70}\n")
    
    result = send_welcome_credits_email(
        to_email=test_email,
        full_name=test_name,
        credits=10
    )
    
    if 'error' in result:
        print(f"❌ Error sending email: {result['error']}")
    else:
        print(f"✅ Email sent successfully!")
        print(f"   Email ID: {result.get('id', 'N/A')}")
        print(f"\nCheck your inbox at {test_email}")
    
    print(f"\n{'='*70}\n")

if __name__ == '__main__':
    test_email()
