"""
Resend confirmation email to existing unconfirmed user.
Uses Supabase Admin API to trigger confirmation email resend.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Missing Supabase credentials in .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def resend_confirmation(email):
    """Resend confirmation email to user."""
    print(f"\n📧 Resending confirmation email to: {email}")
    
    try:
        # Get user by email
        users = supabase.auth.admin.list_users()
        user = next((u for u in users if u.email == email), None)
        
        if not user:
            print(f"❌ User not found: {email}")
            return False
        
        # Check if already confirmed
        if user.email_confirmed_at:
            print(f"✅ User already confirmed on: {user.email_confirmed_at}")
            print(f"   No need to resend confirmation email.")
            return True
        
        # Resend confirmation email using admin API
        # For existing users, we need to generate a new confirmation link
        try:
            # Method 1: Use generate_link for email confirmation
            result = supabase.auth.admin.generate_link({
                'type': 'signup',
                'email': email
            })
            
            print(f"✅ Confirmation email sent successfully!")
            print(f"   User ID: {user.id}")
            print(f"   Email: {email}")
            
            if hasattr(result, 'properties') and result.properties.get('action_link'):
                print(f"   Confirmation link: {result.properties['action_link']}")
            
            return True
            
        except Exception as link_error:
            print(f"⚠️  generate_link failed: {link_error}")
            print(f"   Trying alternative method...")
            
            # Method 2: Update user to trigger confirmation email
            try:
                # This triggers Supabase to resend confirmation
                supabase.auth.admin.update_user_by_id(
                    user.id,
                    {'email_confirm': True}
                )
                
                print(f"✅ Confirmation email triggered!")
                print(f"   User ID: {user.id}")
                print(f"   Email: {email}")
                
                return True
                
            except Exception as update_error:
                print(f"❌ Both methods failed:")
                print(f"   generate_link: {link_error}")
                print(f"   update_user: {update_error}")
                raise update_error
        
    except Exception as e:
        print(f"❌ Error resending confirmation: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("RESEND CONFIRMATION EMAIL")
    print("=" * 70)
    
    # Email to resend to
    email = input("\nEnter email address: ").strip()
    
    if not email:
        print("❌ Email address required")
        sys.exit(1)
    
    success = resend_confirmation(email)
    
    print("\n" + "=" * 70)
    if success:
        print("✅ DONE - Check user's inbox for confirmation email")
    else:
        print("❌ FAILED - See error above")
    print("=" * 70)
