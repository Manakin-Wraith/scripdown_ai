#!/usr/bin/env python3
"""
Test email sending in production environment.
This script sends a test email using the production Resend API key.
"""

import os
import sys
import resend
from datetime import datetime

# Set up environment - use production values
RESEND_API_KEY = "re_gtgcoYQP_HTJe9TWSL72aB7jkfjpWZQN1"
RESEND_FROM_EMAIL = "hello@slateone.studio"

print("=" * 80)
print("PRODUCTION EMAIL TEST")
print("=" * 80)
print(f"Timestamp: {datetime.now().isoformat()}")
print(f"From Email: {RESEND_FROM_EMAIL}")
print(f"API Key: {RESEND_API_KEY[:10]}...{RESEND_API_KEY[-4:]}")
print()

# Initialize Resend
resend.api_key = RESEND_API_KEY

# Get recipient email
if len(sys.argv) > 1:
    recipient = sys.argv[1]
else:
    recipient = input("Enter recipient email address: ")

print(f"Sending test email to: {recipient}")
print()

try:
    # Send test email
    params = {
        "from": RESEND_FROM_EMAIL,
        "to": [recipient],
        "subject": "🧪 Production Email Test - ScripDown AI",
        "html": """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
                .container { max-width: 600px; margin: 40px auto; padding: 20px; background: #f9fafb; border-radius: 8px; }
                .header { background: #4f46e5; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }
                .content { background: white; padding: 30px; border-radius: 0 0 8px 8px; }
                .badge { display: inline-block; background: #10b981; color: white; padding: 8px 16px; border-radius: 20px; font-weight: 600; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧪 Production Email Test</h1>
                </div>
                <div class="content">
                    <p><span class="badge">✅ SUCCESS</span></p>
                    <h2>Email Service is Working!</h2>
                    <p>This test email was sent from the <strong>production environment</strong> of ScripDown AI.</p>
                    <hr>
                    <p><strong>Details:</strong></p>
                    <ul>
                        <li>From: hello@slateone.studio</li>
                        <li>Environment: Production (Railway)</li>
                        <li>Service: Resend API</li>
                        <li>Timestamp: """ + datetime.now().isoformat() + """</li>
                    </ul>
                    <p>If you received this email, it confirms that:</p>
                    <ol>
                        <li>✅ Resend API key is valid</li>
                        <li>✅ Email sending is working</li>
                        <li>✅ Domain is properly configured</li>
                        <li>✅ Emails are being delivered</li>
                    </ol>
                </div>
            </div>
        </body>
        </html>
        """,
        "text": f"""
Production Email Test - ScripDown AI

✅ SUCCESS - Email Service is Working!

This test email was sent from the production environment.

Details:
- From: hello@slateone.studio
- Environment: Production (Railway)
- Service: Resend API
- Timestamp: {datetime.now().isoformat()}

If you received this email, it confirms that:
1. ✅ Resend API key is valid
2. ✅ Email sending is working
3. ✅ Domain is properly configured
4. ✅ Emails are being delivered
        """
    }
    
    response = resend.Emails.send(params)
    
    print("✅ EMAIL SENT SUCCESSFULLY!")
    print()
    print("Response from Resend:")
    print(f"  Email ID: {response.get('id', 'N/A')}")
    print(f"  Full Response: {response}")
    print()
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Check your inbox for the test email")
    print("2. Check spam/junk folder if not in inbox")
    print("3. Log into Resend dashboard: https://resend.com/emails")
    print(f"4. Search for email ID: {response.get('id', 'N/A')}")
    print("5. Verify the email appears in your Resend dashboard")
    print()
    
except Exception as e:
    print("❌ ERROR SENDING EMAIL")
    print(f"Error: {e}")
    print()
    print("Possible causes:")
    print("- Invalid API key")
    print("- Domain not verified in Resend")
    print("- Rate limit exceeded")
    print("- Network connectivity issue")
    sys.exit(1)
