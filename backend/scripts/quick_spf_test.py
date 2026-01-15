"""
Quick SPF alignment test - send email to yourself and check headers.
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.email_service import send_email

def main():
    print("=" * 70)
    print("QUICK SPF/DMARC ALIGNMENT TEST")
    print("=" * 70)
    
    email = input("\nEnter your email address: ").strip()
    
    if not email:
        print("❌ No email provided")
        return
    
    print(f"\n📧 Sending test email to: {email}")
    
    subject = "🔍 SPF/DMARC Alignment Test"
    html = """
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px;">
            <h2 style="color: #333;">✅ SPF/DMARC Alignment Test</h2>
            <p>If you received this email, the basic sending is working!</p>
            
            <div style="background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Next Steps:</h3>
                <ol>
                    <li>View the email headers (Show Original / Message Source)</li>
                    <li>Look for these key indicators:</li>
                </ol>
                
                <h4>✅ Success Indicators:</h4>
                <pre style="background: #e8f5e9; padding: 10px; border-radius: 5px; overflow-x: auto;">
Return-Path: &lt;bounces@send.slateone.studio&gt;
Authentication-Results:
  spf=pass smtp.mailfrom=send.slateone.studio
  dkim=pass header.i=@slateone.studio
  dmarc=pass header.from=slateone.studio
                </pre>
                
                <h4>❌ If Still Not Aligned:</h4>
                <pre style="background: #ffebee; padding: 10px; border-radius: 5px; overflow-x: auto;">
Return-Path: &lt;bounces@amazonses.com&gt;
Authentication-Results:
  spf=fail
                </pre>
            </div>
            
            <p><strong>Domain:</strong> slateone.studio</p>
            <p><strong>Custom Return-Path:</strong> send.slateone.studio</p>
        </div>
    </body>
    </html>
    """
    
    result = send_email(email, subject, html)
    
    if 'error' in result:
        print(f"\n❌ Error: {result['error']}")
        return
    
    print(f"\n✅ Email sent successfully!")
    print(f"   Resend ID: {result.get('id', 'N/A')}")
    
    print("\n" + "=" * 70)
    print("HOW TO CHECK HEADERS:")
    print("=" * 70)
    print("\n📧 Gmail:")
    print("   1. Open the email")
    print("   2. Click three dots (⋮) → 'Show original'")
    print("   3. Look for 'Return-Path' and 'Authentication-Results'")
    
    print("\n📧 Outlook:")
    print("   1. Open the email")
    print("   2. File → Properties → Internet headers")
    print("   3. Or: View → Message source")
    
    print("\n" + "=" * 70)
    print("WHAT TO LOOK FOR:")
    print("=" * 70)
    print("\n✅ If SPF is aligned:")
    print("   Return-Path: <...@send.slateone.studio>")
    print("   spf=pass")
    print("   dmarc=pass")
    
    print("\n❌ If NOT aligned:")
    print("   Return-Path: <...@amazonses.com>")
    print("   spf=fail")
    print("=" * 70)

if __name__ == '__main__':
    main()
