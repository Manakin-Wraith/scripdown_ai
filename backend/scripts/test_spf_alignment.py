"""
Test SPF/DMARC alignment by sending to authentication checker services.
This will provide detailed authentication reports.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.email_service import send_email, APP_NAME

def test_authentication():
    """
    Send test emails to authentication verification services.
    These services will reply with detailed SPF/DKIM/DMARC analysis.
    """
    print("=" * 70)
    print("SPF/DMARC ALIGNMENT TEST")
    print("=" * 70)
    
    # Port25 authentication checker
    port25_email = "check-auth@verifier.port25.com"
    
    print("\n📧 Sending test email to authentication checker...")
    print(f"   To: {port25_email}")
    print(f"   From: hello@slateone.studio")
    
    subject = f"Authentication Test from {APP_NAME}"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>SPF/DMARC Alignment Test</h2>
        <p>This is a test email to verify authentication configuration.</p>
        <p><strong>Domain:</strong> slateone.studio</p>
        <p><strong>Custom Return-Path:</strong> send.slateone.studio</p>
        <p><strong>Expected Results:</strong></p>
        <ul>
            <li>SPF: PASS (for send.slateone.studio)</li>
            <li>DKIM: PASS</li>
            <li>DMARC: PASS (alignment with slateone.studio)</li>
        </ul>
    </body>
    </html>
    """
    
    result = send_email(port25_email, subject, html)
    
    if 'error' in result:
        print(f"\n❌ Error sending email: {result['error']}")
        return
    
    print(f"\n✅ Email sent successfully!")
    print(f"   Resend ID: {result.get('id', 'N/A')}")
    
    print("\n" + "=" * 70)
    print("WHAT TO EXPECT:")
    print("=" * 70)
    print("\nYou will receive an automated reply from Port25 with:")
    print("  • Full authentication results")
    print("  • SPF check details")
    print("  • DKIM signature verification")
    print("  • DMARC alignment status")
    print("  • Detailed header analysis")
    
    print("\n" + "=" * 70)
    print("WHAT TO LOOK FOR IN THE REPLY:")
    print("=" * 70)
    print("\n✅ SUCCESS indicators:")
    print("   SPF check:          pass")
    print("   DKIM check:         pass")
    print("   DMARC check:        pass")
    print("   Return-Path:        @send.slateone.studio")
    print("   SPF alignment:      aligned")
    
    print("\n❌ If you see:")
    print("   SPF check:          fail")
    print("   Return-Path:        @amazonses.com")
    print("   → Custom Return-Path not configured correctly")
    
    print("\n" + "=" * 70)
    print("\nAlternatively, send a test to your own email and check headers:")
    print("  1. Open email in Gmail/Outlook")
    print("  2. View 'Show Original' or 'Message Source'")
    print("  3. Look for 'Authentication-Results' header")
    print("=" * 70)

if __name__ == '__main__':
    test_authentication()
