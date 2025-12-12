#!/usr/bin/env python3
"""
Early Access Invite Script
Sends bulk early access invite emails to users who requested early access.
These users get an extended 30-day trial instead of the standard 14 days.

Usage:
    python send_early_access_invites.py --emails "email1@example.com,email2@example.com"
    python send_early_access_invites.py --file emails.txt
    python send_early_access_invites.py --test "your@email.com"  # Send test email

The script will:
1. Register each email in the early_access_users table
2. Send the early access invite email from hello@slateone.studio
3. Log results to console
"""

import os
import sys
import argparse
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.email_service import send_early_access_invite, is_configured, EARLY_ACCESS_TRIAL_DAYS
from db.supabase_client import get_supabase_client


def register_early_access_user(email: str, first_name: str = None) -> dict:
    """
    Register an email as an early access user in the database.
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('early_access_users') \
            .upsert({
                'email': email.lower().strip(),
                'first_name': first_name,
                'trial_days': EARLY_ACCESS_TRIAL_DAYS,
                'invited_at': datetime.now().isoformat(),
                'status': 'invited'
            }, on_conflict='email') \
            .execute()
        
        return {'success': True, 'email': email}
        
    except Exception as e:
        return {'success': False, 'email': email, 'error': str(e)}


def update_invite_sent(email: str) -> None:
    """
    Update the invite_sent_at timestamp after successfully sending email.
    """
    try:
        supabase = get_supabase_client()
        
        supabase.table('early_access_users') \
            .update({'invite_sent_at': datetime.now().isoformat()}) \
            .eq('email', email.lower().strip()) \
            .execute()
            
    except Exception as e:
        print(f"  Warning: Could not update invite_sent_at for {email}: {e}")


def send_invites(emails: list, dry_run: bool = False) -> dict:
    """
    Send early access invites to a list of emails.
    
    Args:
        emails: List of email addresses (can include optional names as "email:name")
        dry_run: If True, only register users without sending emails
    
    Returns:
        Summary of results
    """
    results = {
        'total': len(emails),
        'registered': 0,
        'sent': 0,
        'failed': [],
        'skipped': []
    }
    
    print(f"\n{'='*60}")
    print(f"Early Access Invite Script")
    print(f"{'='*60}")
    print(f"Total emails to process: {len(emails)}")
    print(f"Extended trial days: {EARLY_ACCESS_TRIAL_DAYS}")
    print(f"Dry run: {dry_run}")
    print(f"{'='*60}\n")
    
    if not is_configured():
        print("ERROR: Email service not configured (RESEND_API_KEY missing)")
        return results
    
    for i, entry in enumerate(emails, 1):
        # Parse email and optional name (format: "email:name" or just "email")
        parts = entry.strip().split(':')
        email = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 else None
        
        if not email or '@' not in email:
            print(f"[{i}/{len(emails)}] SKIP: Invalid email format: {entry}")
            results['skipped'].append(entry)
            continue
        
        print(f"[{i}/{len(emails)}] Processing: {email}")
        
        # Step 1: Register in database
        reg_result = register_early_access_user(email, first_name)
        if reg_result['success']:
            results['registered'] += 1
            print(f"  ✓ Registered in database")
        else:
            print(f"  ✗ Failed to register: {reg_result.get('error')}")
            results['failed'].append({'email': email, 'error': reg_result.get('error')})
            continue
        
        # Step 2: Send email (unless dry run)
        if dry_run:
            print(f"  ⊘ Dry run - email not sent")
            continue
        
        email_result = send_early_access_invite(email, first_name)
        
        if 'error' not in email_result:
            results['sent'] += 1
            update_invite_sent(email)
            print(f"  ✓ Email sent successfully")
        else:
            print(f"  ✗ Failed to send email: {email_result.get('error')}")
            results['failed'].append({'email': email, 'error': email_result.get('error')})
        
        # Rate limiting - wait 200ms between emails to avoid hitting Resend limits
        if i < len(emails):
            time.sleep(0.2)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total processed: {results['total']}")
    print(f"Registered in DB: {results['registered']}")
    print(f"Emails sent: {results['sent']}")
    print(f"Skipped: {len(results['skipped'])}")
    print(f"Failed: {len(results['failed'])}")
    
    if results['failed']:
        print(f"\nFailed emails:")
        for f in results['failed']:
            print(f"  - {f['email']}: {f['error']}")
    
    print(f"{'='*60}\n")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Send early access invite emails to users',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send to specific emails
  python send_early_access_invites.py --emails "user1@example.com,user2@example.com"
  
  # Send with names (format: email:name)
  python send_early_access_invites.py --emails "user1@example.com:John,user2@example.com:Jane"
  
  # Read from file (one email per line)
  python send_early_access_invites.py --file emails.txt
  
  # Test with a single email
  python send_early_access_invites.py --test "your@email.com"
  
  # Dry run (register only, no emails)
  python send_early_access_invites.py --emails "user@example.com" --dry-run
        """
    )
    
    parser.add_argument(
        '--emails',
        type=str,
        help='Comma-separated list of emails (format: email or email:name)'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='Path to file containing emails (one per line)'
    )
    
    parser.add_argument(
        '--test',
        type=str,
        help='Send a test email to a single address'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Register users in database but do not send emails'
    )
    
    args = parser.parse_args()
    
    emails = []
    
    if args.test:
        emails = [args.test]
        print(f"Test mode: Sending to {args.test}")
    elif args.emails:
        emails = [e.strip() for e in args.emails.split(',') if e.strip()]
    elif args.file:
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        with open(args.file, 'r') as f:
            emails = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    else:
        parser.print_help()
        sys.exit(1)
    
    if not emails:
        print("Error: No emails provided")
        sys.exit(1)
    
    # Confirm before sending
    if not args.dry_run and not args.test:
        print(f"\nAbout to send {len(emails)} early access invite emails.")
        print("Emails will be sent from: hello@slateone.studio")
        confirm = input("Continue? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
    results = send_invites(emails, dry_run=args.dry_run)
    
    # Exit with error code if any failed
    if results['failed']:
        sys.exit(1)


if __name__ == '__main__':
    main()
