"""
Retry sending reminder emails to users who failed in the previous attempt.
Manually specify the failed email addresses.
"""

import sys
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.email_service import send_early_access_reminder

# Failed emails from previous run
FAILED_USERS = [
    {'email': 'pulanemafatshe@gmail.com', 'first_name': 'Pulane'},
    {'email': 'helena.kieser@gmail.com', 'first_name': 'Helena'},
    {'email': 'hlomlad@gmail.com', 'first_name': 'Hlomla'},
    {'email': 'megganr@moleculemedia.co.za', 'first_name': 'Meggan'},
    {'email': 'aooseyemi@gmail.com', 'first_name': 'Ant'},
]


def main():
    print("=" * 70)
    print("RETRY FAILED REMINDER EMAILS")
    print("=" * 70)
    
    print(f"\nRetrying {len(FAILED_USERS)} failed email(s):\n")
    
    for i, user in enumerate(FAILED_USERS, 1):
        print(f"  {i}. {user['first_name']} ({user['email']})")
    
    print("\n" + "=" * 70)
    
    # Confirmation
    confirm = input(f"\nSend reminder emails to these {len(FAILED_USERS)} user(s)? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Cancelled. No emails sent.")
        return
    
    print("\n" + "=" * 70)
    print("SENDING REMINDERS (WITH RATE LIMITING)")
    print("=" * 70)
    
    sent_count = 0
    failed_count = 0
    
    for i, user in enumerate(FAILED_USERS, 1):
        email = user['email']
        first_name = user['first_name']
        
        print(f"\n[{i}/{len(FAILED_USERS)}] Sending to: {email}")
        
        # Send reminder email
        result = send_early_access_reminder(email, first_name)
        
        if 'error' in result:
            print(f"  ❌ Failed: {result['error']}")
            failed_count += 1
        else:
            print(f"  ✅ Sent successfully (ID: {result.get('id', 'N/A')})")
            sent_count += 1
        
        # Rate limiting: Wait 0.6 seconds between emails (max 2 per second)
        if i < len(FAILED_USERS):
            print("  ⏳ Waiting 0.6s (rate limiting)...")
            time.sleep(0.6)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total users: {len(FAILED_USERS)}")
    print(f"Emails sent: {sent_count}")
    print(f"Failed: {failed_count}")
    print("=" * 70)


if __name__ == '__main__':
    main()
