"""
Process waitlist users who haven't received welcome emails yet.
Run this as a cron job or manually to send welcome emails to new signups.
"""
import sys
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client
from services.email_service import send_waitlist_welcome_email

# Notel project (for waitlist table)
NOTEL_SUPABASE_URL = os.getenv('NOTEL_SUPABASE_URL')
NOTEL_SUPABASE_KEY = os.getenv('NOTEL_SUPABASE_SERVICE_KEY')


def process_pending_welcomes():
    """Send welcome emails to waitlist users who haven't received one yet."""
    
    if not NOTEL_SUPABASE_URL or not NOTEL_SUPABASE_KEY:
        print("❌ Error: NOTEL_SUPABASE_URL and NOTEL_SUPABASE_SERVICE_KEY must be set in .env")
        return
    
    try:
        client = create_client(NOTEL_SUPABASE_URL, NOTEL_SUPABASE_KEY)
        
        # Get users who haven't received welcome email
        response = client.table('waitlist')\
            .select('*')\
            .eq('welcome_email_sent', False)\
            .order('created_at', desc=False)\
            .limit(50)\
            .execute()
        
        users = response.data
        
        if not users:
            print("✓ No pending welcome emails to send")
            return
        
        print(f"\n{'='*70}")
        print(f"WAITLIST WELCOME EMAIL BATCH")
        print(f"{'='*70}")
        print(f"Found {len(users)} user(s) pending welcome email\n")
        
        sent_count = 0
        failed_count = 0
        
        for i, user in enumerate(users, 1):
            email = user['email']
            metadata = user.get('metadata', {})
            user_id = user['id']
            
            print(f"[{i}/{len(users)}] Processing: {email}")
            
            # Send welcome email
            result = send_waitlist_welcome_email(email, metadata)
            
            if 'error' not in result:
                # Mark as sent in database
                try:
                    client.table('waitlist')\
                        .update({
                            'welcome_email_sent': True,
                            'welcome_email_sent_at': 'now()'
                        })\
                        .eq('id', user_id)\
                        .execute()
                    
                    print(f"  ✅ Email sent successfully (ID: {result.get('id', 'N/A')})")
                    sent_count += 1
                except Exception as e:
                    print(f"  ⚠️  Email sent but failed to update database: {e}")
                    sent_count += 1
            else:
                print(f"  ❌ Failed to send email: {result['error']}")
                failed_count += 1
            
            # Rate limiting - avoid overwhelming email service
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
        
    except Exception as e:
        print(f"❌ Error processing waitlist: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    process_pending_welcomes()
