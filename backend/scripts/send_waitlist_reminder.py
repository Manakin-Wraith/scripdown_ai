"""
Send feedback request email to beta users manually.
This script allows you to select specific users and request their feedback
on their SlateOne experience.
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
import resend

# Initialize Resend
resend.api_key = os.getenv('RESEND_API_KEY')

# Notel project (for waitlist table)
NOTEL_SUPABASE_URL = os.getenv('NOTEL_SUPABASE_URL')
NOTEL_SUPABASE_KEY = os.getenv('NOTEL_SUPABASE_SERVICE_KEY')

# Email configuration
APP_URL = os.getenv('FRONTEND_URL', 'https://app.slateone.studio')


def get_waitlist_users():
    """Fetch waitlist users who haven't signed up yet."""
    if not NOTEL_SUPABASE_URL or not NOTEL_SUPABASE_KEY:
        print("❌ Error: NOTEL_SUPABASE_URL and NOTEL_SUPABASE_SERVICE_KEY must be set in .env")
        return []
    
    try:
        client = create_client(NOTEL_SUPABASE_URL, NOTEL_SUPABASE_KEY)
        
        # Get all waitlist users
        response = client.table('waitlist')\
            .select('*')\
            .order('created_at', desc=True)\
            .execute()
        
        return response.data
    except Exception as e:
        print(f"❌ Error fetching waitlist users: {e}")
        return []


def send_waitlist_reminder_email(email: str, first_name: str = None):
    """
    Send waitlist conversion reminder email.
    
    Args:
        email: Recipient email address
        first_name: User's first name (optional)
    """
    name = first_name if first_name else 'there'
    
    subject = f"Hey {name}, we'd love to have you on SlateOne"
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #0a0a0a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px;">
          <!-- Header -->
          <tr>
            <td style="padding-bottom: 32px;">
              <span style="font-size: 28px; font-weight: bold; color: #f0f0f0;">Slate<span style="color: #E3FF00;">One</span></span>
            </td>
          </tr>
          
          <!-- Main Content -->
          <tr>
            <td style="background-color: #161616; border-radius: 12px; padding: 48px 40px; border: 1px solid #2a2a2a;">
              
              <!-- Greeting -->
              <h1 style="color: #f0f0f0; font-size: 28px; margin: 0 0 16px 0; font-weight: 600;">
                Hey {name}
              </h1>
              <p style="color: #d0d0d0; font-size: 15px; line-height: 1.7; margin: 0 0 24px 0;">
                Thanks for joining our waitlist a while back. We wanted to reach out personally because we think SlateOne could really help with your workflow.
              </p>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- What We've Built -->
              <h2 style="color: #f0f0f0; font-size: 20px; margin: 0 0 16px 0; font-weight: 600;">What we've been building</h2>
              <p style="color: #d0d0d0; font-size: 15px; line-height: 1.7; margin: 0 0 16px 0;">
                Since you joined the waitlist, we've been working hard. Here's where we're at:
              </p>
              
              <div style="background-color: #1a1a1a; border-radius: 8px; padding: 20px 24px; margin: 24px 0;">
                <p style="color: #E3FF00; font-size: 14px; font-weight: 600; margin: 0 0 16px 0;">📊 Real Numbers from 511 Pages Analyzed</p>
                <div style="margin-bottom: 16px;">
                  <p style="color: #c0c0c0; font-size: 13px; margin: 0 0 12px 0;">Core Elements:</p>
                  <ul style="color: #d0d0d0; font-size: 14px; line-height: 1.8; margin: 0 0 16px 0; padding-left: 20px;">
                    <li><strong style="color: #fff;">229 Unique Characters</strong> 🎭</li>
                    <li><strong style="color: #fff;">230 Unique Locations</strong> 📍</li>
                    <li><strong style="color: #fff;">535 Individual Scenes</strong> 🎬</li>
                  </ul>
                </div>
                <div>
                  <p style="color: #c0c0c0; font-size: 13px; margin: 0 0 12px 0;">Granular Details Auto-Identified:</p>
                  <ul style="color: #d0d0d0; font-size: 14px; line-height: 1.8; margin: 0 0 16px 0; padding-left: 20px;">
                    <li><strong style="color: #fff;">1,548 Props</strong> 🔫</li>
                    <li><strong style="color: #fff;">250 Special FX moments</strong> ✨</li>
                    <li><strong style="color: #fff;">157 Vehicles</strong> 🚗</li>
                    <li><strong style="color: #fff;">118 Wardrobe items</strong> 👗</li>
                  </ul>
                </div>
                <p style="color: #E3FF00; font-size: 15px; font-weight: 600; margin: 16px 0 0 0; padding-top: 16px; border-top: 1px solid #2a2a2a;">
                  ⚡ Average analysis time: 9 minutes 44 seconds per 90 page script
                </p>
              </div>
              
              <p style="color: #d0d0d0; font-size: 15px; line-height: 1.7; margin: 24px 0 0 0;">
                We'd love for you to be part of this. Your account is ready whenever you are.
              </p>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- The Offer -->
              <h2 style="color: #f0f0f0; font-size: 20px; margin: 0 0 16px 0; font-weight: 600;">Simple, honest pricing</h2>
              <p style="color: #d0d0d0; font-size: 15px; line-height: 1.7; margin: 0 0 24px 0;">
                We're keeping it straightforward. No complicated tiers or hidden fees.
              </p>
              
              <!-- CTA -->
              <div style="text-align: center; margin: 32px 0;">
                <a href="https://app.slateone.studio/login?mode=signup" style="display: inline-block; background: linear-gradient(135deg, #E3FF00, #C4D600); color: #000000; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                  Create Your Account →
                </a>
                <p style="color: #999; font-size: 12px; margin: 16px 0 0 0;">
                  Start your first breakdown today.
                </p>
              </div>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- Social Proof -->
              <h2 style="color: #f0f0f0; font-size: 18px; margin: 0 0 16px 0; font-weight: 600;">From our early users</h2>
              <div style="background-color: #1a1a1a; border-radius: 8px; padding: 20px; margin: 16px 0;">
                <p style="color: #d0d0d0; font-size: 14px; line-height: 1.7; margin: 0 0 12px 0; font-style: italic;">
                  "This would've saved me 3 days on my last breakdown. Honestly a game changer for our workflow."
                </p>
                <p style="color: #999; font-size: 12px; margin: 0;">
                  — Assistant Director, Cape Town
                </p>
              </div>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- Close -->
              <p style="color: #d0d0d0; font-size: 14px; line-height: 1.7; margin: 0 0 16px 0;">
                No pressure at all. If you have questions or want to chat about how SlateOne might fit your workflow, just reply to this email. We're here to help.
              </p>
              <p style="color: #d0d0d0; font-size: 14px; line-height: 1.7; margin: 0 0 24px 0;">
                Thanks for your interest in what we're building.
              </p>
              <p style="color: #f0f0f0; font-size: 14px; margin: 0;">
                The SlateOne Team
              </p>
              <p style="color: #999; font-size: 12px; margin: 8px 0 0 0;">
                hello@slateone.studio
              </p>
              
            </td>
          </tr>
          
          <!-- Footer -->
          <tr>
            <td style="padding-top: 32px; text-align: center;">
              <p style="color: #505050; font-size: 12px; margin: 0;">© 2025 SlateOne · Built for the SA Film Industry</p>
              <p style="color: #404040; font-size: 11px; margin: 8px 0 0 0;">You're on the waitlist. <a href="#" style="color: #666;">Unsubscribe</a></p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    
    # Plain text version
    text_content = f"""Hey {name},

Thanks for joining our waitlist a while back. We wanted to reach out personally because we think SlateOne could really help with your workflow.

What we've been building
========================

Since you joined the waitlist, we've been working hard. Here's where we're at:

Real Numbers from 511 Pages Analyzed:

Core Elements:
• 229 Unique Characters 🎭
• 230 Unique Locations 📍
• 535 Individual Scenes 🎬

Granular Details Auto-Identified:
• 1,548 Props 🔫
• 250 Special FX moments ✨
• 157 Vehicles 🚗
• 118 Wardrobe items 👗

⚡ Average analysis time: 9 minutes 44 seconds per 90 page script

We'd love for you to be part of this. Your account is ready whenever you are.

Simple, honest pricing
======================

We're keeping it straightforward. No complicated tiers or hidden fees.

EARLY ACCESS PRICING: R99/month
Cancel anytime. No contracts. No surprises.

• Unlimited script uploads
• AI-powered breakdowns
• Export to PDF

Create Your Account: {APP_URL}/login?source=waitlist
Start your first breakdown today.

From our early users:
"This would've saved me 3 days on my last breakdown. Honestly a game changer for our workflow."
— Assistant Director, Cape Town

No pressure at all. If you have questions or want to chat about how SlateOne might fit your workflow, just reply to this email. We're here to help.

Thanks for your interest in what we're building.

The SlateOne Team
hello@slateone.studio

---
© 2025 SlateOne · Built for the SA Film Industry
"""
    
    try:
        response = resend.Emails.send({
            "from": "SlateOne <hello@slateone.studio>",
            "to": [email],
            "subject": subject,
            "html": html_content,
            "text": text_content,
            "reply_to": "hello@slateone.studio"
        })
        
        return {'success': True, 'id': response.get('id')}
    except Exception as e:
        return {'error': str(e)}


def send_to_custom_email():
    """Send waitlist reminder to a custom email address not on the waitlist."""
    print("\n" + "="*80)
    print("SEND TO CUSTOM EMAIL")
    print("="*80)
    
    email = input("\nEnter email address: ").strip()
    
    if not email or '@' not in email:
        print("❌ Invalid email address")
        return
    
    first_name = input("Enter first name (optional, press Enter to skip): ").strip()
    first_name = first_name if first_name else None
    
    # Confirm
    print(f"\n📧 You are about to send a waitlist reminder to: {email}")
    confirm = input("Proceed? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    print(f"\nSending to: {email}")
    result = send_waitlist_reminder_email(email, first_name)
    
    if 'error' not in result:
        print(f"✅ Email sent successfully (ID: {result.get('id', 'N/A')})")
    else:
        print(f"❌ Failed: {result['error']}")
    
    print("\n" + "="*80 + "\n")


def display_users(users):
    """Display users in a numbered list."""
    print("\n" + "="*80)
    print("WAITLIST USERS (not yet signed up)")
    print("="*80)
    
    for i, user in enumerate(users, 1):
        email = user.get('email', 'N/A')
        role = user.get('role') or user.get('metadata', {}).get('role', 'N/A')
        created = user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'
        reminder_sent = user.get('reminder_email_sent', False)
        status = "✅ Sent" if reminder_sent else "⏳ Pending"
        
        print(f"{i:3d}. {email:40s} | {role:20s} | {created} | {status}")
    
    print("="*80 + "\n")


def main():
    """Main function to send waitlist reminder emails to selected users."""
    
    if not resend.api_key:
        print("❌ Error: RESEND_API_KEY must be set in .env")
        return
    
    # Fetch waitlist users
    print("📥 Fetching waitlist users...")
    users = get_waitlist_users()
    
    if not users:
        print("❌ No waitlist users found")
        return
    
    # Display users
    display_users(users)
    
    # Get user selection
    print("Select users to send waitlist reminder:")
    print("  - Enter numbers separated by commas (e.g., 1,3,5)")
    print("  - Enter 'all' to send to all pending users")
    print("  - Enter 'custom' to send to a specific email address")
    print("  - Enter 'q' to quit")
    
    selection = input("\nYour selection: ").strip().lower()
    
    if selection == 'q':
        print("👋 Exiting...")
        return
    
    if selection == 'custom':
        send_to_custom_email()
        return
    
    # Determine which users to send to
    selected_users = []
    
    if selection == 'all':
        # Send to all users who haven't received reminder
        selected_users = [u for u in users if not u.get('reminder_email_sent', False)]
        if not selected_users:
            print("✓ All users have already received the reminder email")
            return
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            selected_users = [users[i] for i in indices if 0 <= i < len(users)]
        except (ValueError, IndexError) as e:
            print(f"❌ Invalid selection: {e}")
            return
    
    if not selected_users:
        print("❌ No users selected")
        return
    
    # Confirm
    print(f"\n📧 You are about to send waitlist reminders to {len(selected_users)} user(s):")
    for user in selected_users:
        print(f"  - {user['email']}")
    
    confirm = input("\nProceed? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    # Send emails
    print(f"\n{'='*80}")
    print("SENDING WAITLIST REMINDERS")
    print(f"{'='*80}\n")
    
    sent_count = 0
    failed_count = 0
    
    for i, user in enumerate(selected_users, 1):
        email = user['email']
        # Try to extract first name from email or metadata
        first_name = user.get('metadata', {}).get('first_name') if isinstance(user.get('metadata'), dict) else None
        user_id = user['id']
        
        print(f"[{i}/{len(selected_users)}] Sending to: {email}")
        
        result = send_waitlist_reminder_email(email, first_name)
        
        if 'error' not in result:
            print(f"  ✅ Email sent successfully (ID: {result.get('id', 'N/A')})")
            sent_count += 1
            
            # Mark as sent in database
            try:
                client = create_client(NOTEL_SUPABASE_URL, NOTEL_SUPABASE_KEY)
                client.table('waitlist')\
                    .update({
                        'reminder_email_sent': True,
                        'reminder_email_sent_at': 'now()'
                    })\
                    .eq('id', user_id)\
                    .execute()
            except Exception as e:
                print(f"  ⚠️  Email sent but failed to update database: {e}")
        else:
            print(f"  ❌ Failed: {result['error']}")
            failed_count += 1
        
        # Rate limiting
        if i < len(selected_users):
            time.sleep(0.6)
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total selected: {len(selected_users)}")
    print(f"Emails sent: {sent_count}")
    print(f"Failed: {failed_count}")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
