"""
Send waitlist confirmation email to selected users manually.
This script allows you to select specific users from the waitlist and send them
the welcome/confirmation email with the beta access offer.
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
YOCO_PAYMENT_LINK = 'https://pay.yoco.com/r/mEDpxp'
PAYMENT_SUCCESS_URL = 'https://app.slateone.studio/payment-success'


def get_waitlist_users():
    """Fetch all waitlist users."""
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


def send_confirmation_email(email: str, role: str = None, is_vip: bool = False):
    """
    Send the waitlist confirmation email.
    
    Args:
        email: Recipient email address
        role: User's role (e.g., 'Producer', 'Director')
        is_vip: Whether user is VIP
    """
    role = role or 'film professional'
    subject = "Welcome to SlateOne Beta - Let's Build This Together"
    
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
              
              <!-- Welcome -->
              <h1 style="color: #f0f0f0; font-size: 28px; margin: 0 0 16px 0; font-weight: 600;">
                Welcome to SlateOne
              </h1>
              <p style="color: #a0a0a0; font-size: 15px; line-height: 1.7; margin: 0 0 24px 0;">
                Thanks for joining us. You're one of the first 50 SA {role}s to see what we're building.
              </p>
              <p style="color: #a0a0a0; font-size: 15px; line-height: 1.7; margin: 0 0 32px 0;">
                That's not marketing speak—<strong style="color: #E3FF00;">you're literally shaping this product</strong>.
              </p>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- Who We Are -->
              <h2 style="color: #f0f0f0; font-size: 18px; margin: 0 0 16px 0; font-weight: 600;">Who We Are</h2>
              <p style="color: #a0a0a0; font-size: 14px; line-height: 1.7; margin: 0 0 24px 0;">
                We're a small startup in South Africa. Not a big tech company. Just film people who got tired of spending Sundays retyping Excel sheets.
              </p>
              <p style="color: #a0a0a0; font-size: 14px; line-height: 1.7; margin: 0 0 32px 0;">
                We built SlateOne because we needed it. And we're guessing you do too.
              </p>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- Current Status -->
              <h2 style="color: #f0f0f0; font-size: 18px; margin: 0 0 16px 0; font-weight: 600;">🚧 Current Status: Beta</h2>
              
              <div style="margin-bottom: 20px;">
                <div style="color: #4ade80; font-size: 13px; font-weight: 600; margin-bottom: 8px;">✓ What works:</div>
                <ul style="color: #a0a0a0; font-size: 13px; line-height: 1.8; margin: 0 0 16px 0; padding-left: 20px;">
                  <li>AI script breakdown (cast, props, locations)</li>
                  <li>Team collaboration (unlimited seats)</li>
                  <li>SA-specific formatting</li>
                </ul>
              </div>
              
              <div style="margin-bottom: 20px;">
                <div style="color: #E3FF00; font-size: 13px; font-weight: 600; margin-bottom: 8px;">→ What we're perfecting:</div>
                <ul style="color: #a0a0a0; font-size: 13px; line-height: 1.8; margin: 0 0 16px 0; padding-left: 20px;">
                  <li>Accuracy on complex scripts</li>
                  <li>Export formats you actually use</li>
                  <li>Speed improvements</li>
                </ul>
              </div>
              
              <div style="margin-bottom: 24px;">
                <div style="color: #60a5fa; font-size: 13px; font-weight: 600; margin-bottom: 8px;">🔮 What's coming (based on YOUR feedback):</div>
                <ul style="color: #a0a0a0; font-size: 13px; line-height: 1.8; margin: 0; padding-left: 20px;">
                  <li>Features you tell us you need</li>
                  <li>Integrations that make sense</li>
                  <li>Pricing that works for SA budgets</li>
                </ul>
              </div>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- Why You Matter -->
              <h2 style="color: #f0f0f0; font-size: 18px; margin: 0 0 16px 0; font-weight: 600;">Why You Matter</h2>
              <p style="color: #a0a0a0; font-size: 14px; line-height: 1.7; margin: 0 0 16px 0;">
                Here's the truth: <strong style="color: #E3FF00;">We need you more than you need us</strong>.
              </p>
              <p style="color: #a0a0a0; font-size: 14px; line-height: 1.7; margin: 0 0 16px 0;">
                Your feedback determines:
              </p>
              <ul style="color: #a0a0a0; font-size: 14px; line-height: 1.8; margin: 0 0 24px 0; padding-left: 20px;">
                <li>Which features we build next</li>
                <li>How the interface works</li>
                <li>What we charge (and what stays free)</li>
                <li>Whether this becomes the industry standard</li>
              </ul>
              <p style="color: #E3FF00; font-size: 14px; line-height: 1.7; margin: 0 0 32px 0; font-weight: 600;">
                You're not a beta tester. You're a co-creator.
              </p>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- Next Steps -->
              <h2 style="color: #f0f0f0; font-size: 18px; margin: 0 0 16px 0; font-weight: 600;">📋 What Happens Next</h2>
              <ol style="color: #a0a0a0; font-size: 14px; line-height: 1.8; margin: 0 0 24px 0; padding-left: 20px;">
                <li>We'll send login credentials within 24 hours</li>
                <li>Break down your first script (free during beta)</li>
                <li>Tell us what works and what doesn't</li>
                <li>Join our feedback group</li>
              </ol>
              
              <div style="background-color: #1a1a1a; border-left: 3px solid #E3FF00; padding: 16px 20px; margin: 24px 0; border-radius: 4px;">
                <div style="color: #E3FF00; font-size: 13px; font-weight: 600; margin-bottom: 8px;">🎯 Our Promise:</div>
                <ul style="color: #a0a0a0; font-size: 13px; line-height: 1.8; margin: 0; padding-left: 20px;">
                  <li>We read every piece of feedback</li>
                  <li>We ship updates weekly</li>
                  <li>We won't add features you don't need</li>
                  <li>We'll keep pricing fair for SA budgets</li>
                </ul>
              </div>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- Optional Support Section -->
              <h2 style="color: #f0f0f0; font-size: 18px; margin: 0 0 16px 0; font-weight: 600;">💡 Want to Support Development?</h2>
              <p style="color: #a0a0a0; font-size: 14px; line-height: 1.7; margin: 0 0 24px 0;">
                Some early users asked how they can support us while we build. If you want to contribute <strong style="color: #fff;">R249</strong> to help fund development, you'll get:
              </p>
              
              <div style="background-color: #1a1a1a; border: 2px solid #2a2a2a; border-radius: 8px; padding: 24px; margin: 24px 0;">
                <ul style="color: #a0a0a0; font-size: 13px; line-height: 2; margin: 0 0 20px 0; padding-left: 20px;">
                  <li><strong style="color: #E3FF00;">First access</strong> to new features as we roll them out</li>
                  <li><strong style="color: #E3FF00;">Early preview</strong> of our product roadmap</li>
                  <li><strong style="color: #E3FF00;">Direct influence</strong> on which features get prioritized</li>
                  <li><strong style="color: #E3FF00;">Locked-in pricing</strong> when we launch publicly</li>
                  <li><strong style="color: #E3FF00;">Direct line</strong> to the dev team</li>
                </ul>
                <div style="text-align: center;">
                  <a href="{YOCO_PAYMENT_LINK}" style="display: inline-block; background-color: #E3FF00; color: #0a0a0a; padding: 14px 32px; border-radius: 6px; text-decoration: none; font-weight: 700; font-size: 14px;">
                    Support Development (R249) →
                  </a>
                </div>
              </div>
              
              <p style="color: #666; font-size: 13px; margin: 24px 0 0 0; text-align: center; font-style: italic;">
                But it's not required. Your feedback is more valuable than money right now.
              </p>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- Close -->
              <p style="color: #a0a0a0; font-size: 14px; line-height: 1.7; margin: 0 0 16px 0;">
                Thanks for believing in what we're building.
              </p>
              <p style="color: #a0a0a0; font-size: 14px; line-height: 1.7; margin: 0 0 24px 0;">
                Let's make something the SA film industry actually wants to use.
              </p>
              <p style="color: #f0f0f0; font-size: 14px; margin: 0;">
                The SlateOne Team
              </p>
              <p style="color: #666; font-size: 12px; margin: 8px 0 0 0;">
                hello@slateone.studio
              </p>
              <p style="color: #666; font-size: 12px; margin: 16px 0 0 0; font-style: italic;">
                P.S. Seriously, break stuff and tell us. That's how we get better.
              </p>
              
            </td>
          </tr>
          
          <!-- Footer -->
          <tr>
            <td style="padding-top: 32px; text-align: center;">
              <p style="color: #505050; font-size: 12px; margin: 0;">© 2025 SlateOne · Built for the SA Film Industry</p>
              <p style="color: #404040; font-size: 11px; margin: 8px 0 0 0;">You received this because you signed up at slateone.studio</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    
    try:
        response = resend.Emails.send({
            "from": "SlateOne <hello@slateone.studio>",
            "to": [email],
            "subject": subject,
            "html": html_content,
        })
        
        return {'success': True, 'id': response.get('id')}
    except Exception as e:
        return {'error': str(e)}


def display_users(users):
    """Display users in a numbered list."""
    print("\n" + "="*80)
    print("WAITLIST USERS")
    print("="*80)
    
    for i, user in enumerate(users, 1):
        email = user.get('email', 'N/A')
        role = user.get('role') or user.get('metadata', {}).get('role', 'N/A')
        created = user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'
        welcome_sent = user.get('welcome_email_sent', False)
        status = "✅ Sent" if welcome_sent else "⏳ Pending"
        
        print(f"{i:3d}. {email:40s} | {role:20s} | {created} | {status}")
    
    print("="*80 + "\n")


def main():
    """Main function to send confirmation emails to selected users."""
    
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
    print("Select users to send confirmation email:")
    print("  - Enter numbers separated by commas (e.g., 1,3,5)")
    print("  - Enter 'all' to send to all pending users")
    print("  - Enter 'q' to quit")
    
    selection = input("\nYour selection: ").strip().lower()
    
    if selection == 'q':
        print("👋 Exiting...")
        return
    
    # Determine which users to send to
    selected_users = []
    
    if selection == 'all':
        # Send to all users who haven't received welcome email
        selected_users = [u for u in users if not u.get('welcome_email_sent', False)]
        if not selected_users:
            print("✓ All users have already received the welcome email")
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
    print(f"\n📧 You are about to send confirmation emails to {len(selected_users)} user(s):")
    for user in selected_users:
        print(f"  - {user['email']}")
    
    confirm = input("\nProceed? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    # Send emails
    print(f"\n{'='*80}")
    print("SENDING EMAILS")
    print(f"{'='*80}\n")
    
    sent_count = 0
    failed_count = 0
    
    for i, user in enumerate(selected_users, 1):
        email = user['email']
        role = user.get('role') or user.get('metadata', {}).get('role')
        is_vip = user.get('is_vip', False)
        user_id = user['id']
        
        print(f"[{i}/{len(selected_users)}] Sending to: {email}")
        
        result = send_confirmation_email(email, role, is_vip)
        
        if 'error' not in result:
            print(f"  ✅ Email sent successfully (ID: {result.get('id', 'N/A')})")
            sent_count += 1
            
            # Mark as sent in database
            try:
                client = create_client(NOTEL_SUPABASE_URL, NOTEL_SUPABASE_KEY)
                client.table('waitlist')\
                    .update({
                        'welcome_email_sent': True,
                        'welcome_email_sent_at': 'now()'
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
