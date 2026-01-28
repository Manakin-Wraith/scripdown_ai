"""
Manual script to send welcome credits email to all users with profiles.
This script queries the database for users and sends them a personalized email.
"""
import sys
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.supabase_client import get_supabase_admin
from services.email_service import send_welcome_credits_email

def send_welcome_emails():
    """Send welcome credits email to all users with profiles"""
    
    try:
        supabase = get_supabase_admin()
        
        # Get all users with profiles and email addresses
        response = supabase.table('profiles')\
            .select('id, email, full_name, script_credits')\
            .not_.is_('email', 'null')\
            .gte('script_credits', 10)\
            .order('created_at', desc=False)\
            .execute()
        
        users = response.data
        
        if not users:
            print("✓ No users found to send emails to")
            return
        
        print(f"\n{'='*70}")
        print("WELCOME CREDITS EMAIL - MANUAL SEND")
        print(f"{'='*70}")
        print(f"Found {len(users)} user(s) to email\n")
        
        # Show preview of users
        print("Users to email:")
        for i, user in enumerate(users, 1):
            print(f"  {i}. {user['email']} - {user['full_name']} ({user['script_credits']} credits)")
        
        print(f"\n{'='*70}")
        
        # Ask for confirmation
        confirm = input("\nDo you want to send emails to these users? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("\n❌ Cancelled. No emails sent.")
            return
        
        print(f"\n{'='*70}")
        print("SENDING EMAILS...")
        print(f"{'='*70}\n")
        
        sent_count = 0
        failed_count = 0
        
        for i, user in enumerate(users, 1):
            email = user['email']
            full_name = user.get('full_name') or 'there'
            credits = user.get('script_credits', 10)
            
            print(f"[{i}/{len(users)}] Sending to: {email} ({full_name})")
            
            # Send email
            result = send_welcome_credits_email(
                to_email=email,
                full_name=full_name,
                credits=credits
            )
            
            if 'error' not in result:
                print(f"  ✅ Email sent successfully (ID: {result.get('id', 'N/A')})")
                sent_count += 1
            else:
                print(f"  ❌ Failed to send email: {result['error']}")
                failed_count += 1
            
            # Rate limiting - avoid overwhelming email service (0.6s = ~100 emails/min)
            if i < len(users):
                time.sleep(0.6)
        
        # Summary
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"Total users: {len(users)}")
        print(f"Emails sent: {sent_count}")
        print(f"Failed: {failed_count}")
        print(f"{'='*70}\n")
        
        if sent_count > 0:
            print("✅ Welcome emails sent successfully!")
            print("\nNext steps:")
            print("1. Monitor email open rates in Resend dashboard")
            print("2. Collect feedback responses")
            print("3. Create feedback form (Google Forms or Typeform)")
            print("4. Send feedback form link in follow-up email")
        
    except Exception as e:
        print(f"❌ Error sending welcome emails: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    send_welcome_emails()
