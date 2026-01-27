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

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Email configuration
APP_URL = os.getenv('FRONTEND_URL', 'https://app.slateone.studio')


def get_active_users():
    """Fetch users who have uploaded at least one script."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        return []
    
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Get users with their script count
        response = client.rpc('get_users_with_script_count').execute()
        
        # Filter users with at least 1 script
        active_users = [u for u in response.data if u.get('script_count', 0) > 0]
        
        return active_users
    except Exception as e:
        print(f"❌ Error fetching users: {e}")
        # Fallback: get all profiles
        try:
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            response = client.table('profiles').select('*').execute()
            return response.data
        except Exception as e2:
            print(f"❌ Fallback also failed: {e2}")
            return []


def send_feedback_email(email: str, first_name: str = None):
    """
    Send feedback request email.
    
    Args:
        email: Recipient email address
        first_name: User's first name (optional)
    """
    name = first_name if first_name else 'there'
    
    subject = "Quick question: How's SlateOne working for you?"
    
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
                Hey {name} 👋
              </h1>
              <p style="color: #a0a0a0; font-size: 15px; line-height: 1.7; margin: 0 0 24px 0;">
                Quick check-in from the SlateOne team.
              </p>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- The Ask -->
              <h2 style="color: #f0f0f0; font-size: 20px; margin: 0 0 16px 0; font-weight: 600;">We need your honest feedback</h2>
              <p style="color: #a0a0a0; font-size: 15px; line-height: 1.7; margin: 0 0 16px 0;">
                You've been using SlateOne for a bit now, and we want to know: <strong style="color: #E3FF00;">What's working? What's broken? What's missing?</strong>
              </p>
              <p style="color: #a0a0a0; font-size: 15px; line-height: 1.7; margin: 0 0 32px 0;">
                We're not looking for compliments. We need the truth—the good, the bad, and the "why doesn't this button do what I expect?"
              </p>
              
              <!-- Questions -->
              <div style="background-color: #1a1a1a; border-left: 3px solid #E3FF00; padding: 20px 24px; margin: 24px 0; border-radius: 4px;">
                <p style="color: #E3FF00; font-size: 14px; font-weight: 600; margin: 0 0 16px 0;">Specifically, we'd love to know:</p>
                <ul style="color: #a0a0a0; font-size: 14px; line-height: 1.8; margin: 0; padding-left: 20px;">
                  <li><strong style="color: #fff;">What would you change?</strong> (And why?)</li>
                  <li><strong style="color: #fff;">What's frustrating or confusing?</strong> (Be brutal.)</li>
                  <li><strong style="color: #fff;">What's missing?</strong> (What would make this a must have tool?)</li>
                  <li><strong style="color: #fff;">Would you recommend SlateOne to a colleague?</strong> (Why or why not?)</li>
                </ul>
              </div>
              
              <p style="color: #a0a0a0; font-size: 15px; line-height: 1.7; margin: 24px 0 32px 0;">
                Just hit reply and tell us. No forms, no surveys just a real conversation.
              </p>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- Why This Matters -->
              <h2 style="color: #f0f0f0; font-size: 18px; margin: 0 0 16px 0; font-weight: 600;">Why your feedback matters</h2>
              <p style="color: #a0a0a0; font-size: 14px; line-height: 1.7; margin: 0 0 16px 0;">
                We're a small team building this for <em>actual</em> film professionals in South Africa. Your input directly shapes:
              </p>
              <ul style="color: #a0a0a0; font-size: 14px; line-height: 1.8; margin: 0 0 24px 0; padding-left: 20px;">
                <li>Which features we build next</li>
                <li>What stays free vs. paid</li>
                <li>How the interface works</li>
                <li>Whether this becomes industry standard or just another tool</li>
              </ul>
              <p style="color: #E3FF00; font-size: 14px; line-height: 1.7; margin: 0 0 32px 0; font-weight: 600;">
                You're shaping the product.
              </p>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- Optional: Incentive -->
              <div style="background-color: #1a1a1a; border: 2px solid #2a2a2a; border-radius: 8px; padding: 24px; margin: 24px 0;">
                <p style="color: #a0a0a0; font-size: 13px; line-height: 1.7; margin: 0 0 12px 0;">
                  <strong style="color: #E3FF00;">Bonus:</strong> If you send us detailed feedback (5+ minutes of your time), we'll extend your beta access by an extra month. Just reply to this email.
                </p>
                <p style="color: #666; font-size: 12px; margin: 0; font-style: italic;">
                  We appreciate the time.
                </p>
              </div>
              
              <div style="height: 1px; background-color: #2a2a2a; margin: 32px 0;"></div>
              
              <!-- Close -->
              <p style="color: #a0a0a0; font-size: 14px; line-height: 1.7; margin: 0 0 16px 0;">
                Thanks for being part of this.
              </p>
              <p style="color: #a0a0a0; font-size: 14px; line-height: 1.7; margin: 0 0 24px 0;">
                We're listening.
              </p>
              <p style="color: #f0f0f0; font-size: 14px; margin: 0;">
                The SlateOne Team
              </p>
              <p style="color: #666; font-size: 12px; margin: 8px 0 0 0;">
                hello@slateone.studio
              </p>
              
            </td>
          </tr>
          
          <!-- Footer -->
          <tr>
            <td style="padding-top: 32px; text-align: center;">
              <p style="color: #505050; font-size: 12px; margin: 0;">© 2025 SlateOne · Built for the SA Film Industry</p>
              <p style="color: #404040; font-size: 11px; margin: 8px 0 0 0;">Reply to this email to share your feedback</p>
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

Quick check-in from the SlateOne team.

We need your honest feedback
================================

You've been using SlateOne for a bit now, and we want to know: What's working? What's broken? What's missing?

We're not looking for compliments. We need the truth—the good, the bad, and the "why doesn't this button do what I expect?"

Specifically, we'd love to know:
• What feature do you use most? (And why?)
• What's frustrating or confusing? (Be brutal.)
• What's missing? (What would make this a must-have tool?)
• Would you recommend SlateOne to a colleague? (Why or why not?)

Just hit reply and tell us. No forms, no surveys—just a real conversation.

Why your feedback matters
==========================

We're a small team building this for actual film professionals in South Africa. Your input directly shapes:
• Which features we build next
• What stays free vs. paid
• How the interface works
• Whether this becomes industry-standard or just another tool

You're not just a user. You're shaping the product.

BONUS: If you send us detailed feedback (5+ minutes of your time), we'll extend your beta access by an extra month. Just reply to this email.

Thanks for being part of this. We're listening.

The SlateOne Team
hello@slateone.studio

P.S. If something's broken right now, tell us immediately. We'll fix it.

---
© 2025 SlateOne · Built for the SA Film Industry
Reply to this email to share your feedback
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


def display_users(users):
    """Display users in a numbered list."""
    print("\n" + "="*80)
    print("ACTIVE USERS (with scripts)")
    print("="*80)
    
    for i, user in enumerate(users, 1):
        email = user.get('email', 'N/A')
        name = user.get('full_name', 'N/A')
        script_count = user.get('script_count', 0)
        created = user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'
        
        print(f"{i:3d}. {email:40s} | {name:25s} | {script_count} scripts | {created}")
    
    print("="*80 + "\n")


def main():
    """Main function to send feedback emails to selected users."""
    
    if not resend.api_key:
        print("❌ Error: RESEND_API_KEY must be set in .env")
        return
    
    # Fetch active users
    print("📥 Fetching active users...")
    users = get_active_users()
    
    if not users:
        print("❌ No active users found")
        return
    
    # Display users
    display_users(users)
    
    # Get user selection
    print("Select users to send feedback request:")
    print("  - Enter numbers separated by commas (e.g., 1,3,5)")
    print("  - Enter 'all' to send to all users")
    print("  - Enter 'q' to quit")
    
    selection = input("\nYour selection: ").strip().lower()
    
    if selection == 'q':
        print("👋 Exiting...")
        return
    
    # Determine which users to send to
    selected_users = []
    
    if selection == 'all':
        selected_users = users
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
    print(f"\n📧 You are about to send feedback requests to {len(selected_users)} user(s):")
    for user in selected_users:
        print(f"  - {user['email']} ({user.get('full_name', 'N/A')})")
    
    confirm = input("\nProceed? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    # Send emails
    print(f"\n{'='*80}")
    print("SENDING FEEDBACK REQUESTS")
    print(f"{'='*80}\n")
    
    sent_count = 0
    failed_count = 0
    
    for i, user in enumerate(selected_users, 1):
        email = user['email']
        full_name = user.get('full_name', '')
        first_name = full_name.split(' ')[0] if full_name else None
        
        print(f"[{i}/{len(selected_users)}] Sending to: {email}")
        
        result = send_feedback_email(email, first_name)
        
        if 'error' not in result:
            print(f"  ✅ Email sent successfully (ID: {result.get('id', 'N/A')})")
            sent_count += 1
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
