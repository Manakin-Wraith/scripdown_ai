#!/usr/bin/env python3
"""
Admin Script: Send Feature Announcement Emails

This script sends feature announcement emails to specific users or all users.
Use this to notify users about new features like feedback and reports.

Usage:
    # Send to all users with default features
    python scripts/send_feature_announcement.py --all

    # Send to specific users
    python scripts/send_feature_announcement.py --emails user1@example.com user2@example.com

    # Send with custom features
    python scripts/send_feature_announcement.py --all --features-file features.json

    # Preview mode (dry run)
    python scripts/send_feature_announcement.py --all --preview

Example features.json:
[
    {
        "icon": "💬",
        "title": "Feedback System",
        "description": "Share your thoughts and suggestions directly in the app."
    },
    {
        "icon": "📊",
        "title": "Enhanced Reports",
        "description": "Generate professional production reports with improved layouts."
    }
]
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

# Load environment variables from backend/.env manually
env_path = backend_path / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip().strip('"').strip("'")
                os.environ[key.strip()] = value

from services.email_service import send_feature_announcement_email, is_configured
from db.supabase_client import get_supabase_client


def load_features_from_file(filepath):
    """Load features from a JSON file."""
    try:
        with open(filepath, 'r') as f:
            features = json.load(f)
        
        # Validate features
        for feature in features:
            if not all(k in feature for k in ['icon', 'title', 'description']):
                raise ValueError("Each feature must have 'icon', 'title', and 'description'")
        
        return features
    except Exception as e:
        print(f"Error loading features file: {e}")
        sys.exit(1)


def get_all_users():
    """Fetch all users from the database."""
    try:
        supabase = get_supabase_client()
        result = supabase.table('profiles') \
            .select('email, full_name') \
            .execute()
        
        return [
            {'email': p['email'], 'full_name': p.get('full_name', '')}
            for p in result.data
        ]
    except Exception as e:
        print(f"Error fetching users: {e}")
        sys.exit(1)


def get_users_by_email(emails):
    """Fetch specific users by email addresses."""
    try:
        supabase = get_supabase_client()
        result = supabase.table('profiles') \
            .select('email, full_name') \
            .in_('email', emails) \
            .execute()
        
        found_emails = {p['email'] for p in result.data}
        not_found = set(emails) - found_emails
        
        if not_found:
            print(f"Warning: The following emails were not found in the database:")
            for email in not_found:
                print(f"  - {email}")
        
        return [
            {'email': p['email'], 'full_name': p.get('full_name', '')}
            for p in result.data
        ]
    except Exception as e:
        print(f"Error fetching users: {e}")
        sys.exit(1)


def send_announcements(recipients, features=None, preview=False):
    """Send feature announcement emails to recipients."""
    if not is_configured():
        print("Error: Email service not configured (RESEND_API_KEY missing)")
        sys.exit(1)
    
    print(f"\n{'PREVIEW MODE - No emails will be sent' if preview else 'Sending feature announcements...'}")
    print(f"Total recipients: {len(recipients)}")
    
    if features:
        print(f"\nFeatures to announce:")
        for feature in features:
            print(f"  {feature['icon']} {feature['title']}")
    else:
        print("\nUsing default features (Feedback System & Enhanced Reports)")
    
    if preview:
        print("\nRecipients:")
        for recipient in recipients:
            print(f"  - {recipient['email']} ({recipient.get('full_name', 'No name')})")
        print("\nPreview complete. Use without --preview to send emails.")
        return
    
    # Confirm before sending
    print("\n⚠️  WARNING: This will send emails to all recipients listed above.")
    confirm = input("Type 'yes' to continue: ")
    
    if confirm.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Send emails
    sent_count = 0
    failed_count = 0
    errors = []
    
    for i, recipient in enumerate(recipients, 1):
        try:
            print(f"[{i}/{len(recipients)}] Sending to {recipient['email']}...", end=' ')
            
            result = send_feature_announcement_email(
                to_email=recipient['email'],
                full_name=recipient.get('full_name', ''),
                features=features
            )
            
            if 'error' in result:
                failed_count += 1
                errors.append(f"{recipient['email']}: {result['error']}")
                print("❌ FAILED")
            else:
                sent_count += 1
                print("✅ SENT")
        except Exception as e:
            failed_count += 1
            errors.append(f"{recipient['email']}: {str(e)}")
            print(f"❌ ERROR: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total recipients: {len(recipients)}")
    print(f"Successfully sent: {sent_count}")
    print(f"Failed: {failed_count}")
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")


def main():
    parser = argparse.ArgumentParser(
        description='Send feature announcement emails to users',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Recipient options
    recipient_group = parser.add_mutually_exclusive_group(required=True)
    recipient_group.add_argument(
        '--all',
        action='store_true',
        help='Send to all users in the database'
    )
    recipient_group.add_argument(
        '--emails',
        nargs='+',
        help='Send to specific email addresses'
    )
    
    # Feature options
    parser.add_argument(
        '--features-file',
        type=str,
        help='Path to JSON file containing features to announce'
    )
    
    # Preview mode
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Preview mode - show what would be sent without actually sending'
    )
    
    args = parser.parse_args()
    
    # Load features if specified
    features = None
    if args.features_file:
        features = load_features_from_file(args.features_file)
    
    # Get recipients
    if args.all:
        recipients = get_all_users()
    else:
        recipients = get_users_by_email(args.emails)
    
    if not recipients:
        print("No recipients found.")
        sys.exit(1)
    
    # Send announcements
    send_announcements(recipients, features, args.preview)


if __name__ == '__main__':
    main()
