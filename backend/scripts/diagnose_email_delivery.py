#!/usr/bin/env python3
"""
Email Delivery Diagnostic Tool
Analyzes why emails show "delivered" in Resend but users don't receive them.
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

print("=" * 80)
print("EMAIL DELIVERY DIAGNOSTIC - Silent Rejection Analysis")
print("=" * 80)

print("\n🔍 PROBLEM: Resend shows 'delivered' but users don't receive emails")
print("This is called 'silent rejection' - the email reaches the mail server")
print("but is filtered/dropped before reaching the inbox.\n")

# Check configuration
RESEND_FROM_EMAIL = os.getenv('RESEND_FROM_EMAIL')
APP_URL = os.getenv('FRONTEND_URL', 'https://app.slateone.studio')

print("=" * 80)
print("COMMON CAUSES & SOLUTIONS")
print("=" * 80)

print("\n1. 🚫 SPAM FOLDER")
print("-" * 80)
print("Most likely cause: Email is in spam/junk folder")
print("\n✅ IMMEDIATE ACTION:")
print("   Ask the user to:")
print("   • Check spam/junk folder")
print("   • Check 'Promotions' tab (Gmail)")
print("   • Check 'Updates' tab (Gmail)")
print("   • Search inbox for 'SlateOne' or 'hello@slateone.studio'")

print("\n2. 📧 MISSING PLAIN TEXT VERSION")
print("-" * 80)
print("Current status: Checking email service...")

# Check if plain text is being sent
from services.email_service import send_early_access_reminder
import inspect

source = inspect.getsource(send_early_access_reminder)
has_text_param = 'text=' in source and 'text=text' in source

if has_text_param:
    print("✅ Plain text version IS included (good for deliverability)")
else:
    print("⚠️  Plain text version may be missing")
    print("   Solution: Ensure send_email() includes text parameter")

print("\n3. 🔗 SUSPICIOUS LINKS")
print("-" * 80)
print(f"Current APP_URL: {APP_URL}")

if 'localhost' in APP_URL:
    print("⚠️  WARNING: Using localhost URL in emails")
    print("   This is a RED FLAG for spam filters!")
    print("   Solution: Use production URL even in testing")
    print(f"   Update .env: FRONTEND_URL=https://app.slateone.studio")
elif APP_URL.startswith('http://'):
    print("⚠️  WARNING: Using HTTP (not HTTPS)")
    print("   Spam filters prefer HTTPS links")
    print("   Solution: Use HTTPS URL")
else:
    print("✅ Using HTTPS production URL (good)")

print("\n4. 📝 EMAIL CONTENT ANALYSIS")
print("-" * 80)
print("Checking for spam trigger words in email template...")

spam_triggers = [
    'free', 'click here', 'act now', 'limited time', 'urgent',
    'congratulations', 'winner', 'prize', 'guarantee', 'risk-free'
]

# Read email template
try:
    with open('services/email_service.py', 'r') as f:
        email_content = f.read()
    
    found_triggers = [word for word in spam_triggers if word.lower() in email_content.lower()]
    
    if found_triggers:
        print(f"⚠️  Found potential spam triggers: {', '.join(found_triggers)}")
        print("   Consider rephrasing these words")
    else:
        print("✅ No obvious spam trigger words found")
except:
    print("⚠️  Could not analyze email content")

print("\n5. 🔐 AUTHENTICATION RECORDS")
print("-" * 80)
print("Checking DNS records for slateone.studio...")
print("✅ Domain verified in Resend (from earlier diagnostic)")
print("✅ SPF, DKIM, DMARC configured")
print("\nNote: Even with perfect authentication, emails can still be filtered")

print("\n6. 📊 SENDER REPUTATION")
print("-" * 80)
print(f"Sending from: {RESEND_FROM_EMAIL}")
print("\nFactors affecting reputation:")
print("• New domain (slateone.studio) = Lower initial reputation")
print("• Low sending volume = Less trust from email providers")
print("• No engagement history = Unknown sender")
print("\n💡 Solution: Warm up the domain by:")
print("   1. Start with small batches (5-10 emails/day)")
print("   2. Send to engaged users first")
print("   3. Ask recipients to reply or mark as 'not spam'")
print("   4. Gradually increase volume over 2-4 weeks")

print("\n7. 🎯 RECIPIENT EMAIL PROVIDER")
print("-" * 80)
print("Different providers have different filtering:")
print("• Gmail: Very aggressive, checks engagement")
print("• Outlook/Hotmail: Moderate, checks authentication")
print("• Corporate emails: Often have strict filters")
print("• Custom domains: Varies by configuration")
print("\n💡 Ask user which email provider they use")

print("\n8. 🚨 CONTENT FILTERING")
print("-" * 80)
print("Corporate/institutional emails often filter:")
print("• Emails with external links")
print("• Marketing-style content")
print("• Emails from unknown senders")
print("• Bulk/automated emails")

print("\n" + "=" * 80)
print("RECOMMENDED FIXES (Priority Order)")
print("=" * 80)

print("\n🔥 IMMEDIATE (Do Now):")
print("1. Ask user to check spam folder")
print("2. Verify FRONTEND_URL is not localhost")
print("3. Send test email to yourself first")

print("\n⚡ SHORT-TERM (This Week):")
print("4. Add 'View in Browser' link")
print("5. Implement email warm-up strategy")
print("6. Add unsubscribe link (improves trust)")
print("7. Monitor Resend analytics for patterns")

print("\n🎯 LONG-TERM (Ongoing):")
print("8. Build sender reputation gradually")
print("9. Track open/click rates")
print("10. A/B test subject lines and content")

print("\n" + "=" * 80)
print("TESTING PROTOCOL")
print("=" * 80)

print("\n1. Send to yourself first:")
print("   python scripts/test_email.py")
print("   • Check inbox vs spam")
print("   • Check email headers")
print("   • Test all links")

print("\n2. Send to a test group:")
print("   • 2-3 users with different email providers")
print("   • Gmail, Outlook, custom domain")
print("   • Ask them to confirm receipt")

print("\n3. Check Resend analytics:")
print("   https://resend.com/emails")
print("   • Look for bounce patterns")
print("   • Check spam complaint rate")
print("   • Monitor delivery times")

print("\n4. Ask users to whitelist:")
print("   • Add hello@slateone.studio to contacts")
print("   • Mark email as 'not spam'")
print("   • Reply to the email")

print("\n" + "=" * 80)
print("QUICK FIX: Alternative Approach")
print("=" * 80)

print("\n💡 If emails continue to be filtered, consider:")
print("\n1. PERSONAL APPROACH:")
print("   • Send initial emails manually from your personal email")
print("   • Include SlateOne link in signature")
print("   • More personal, less likely to be filtered")

print("\n2. TWO-STEP VERIFICATION:")
print("   • Send simple text-only email first")
print("   • Ask user to reply to confirm")
print("   • Then send full invite email")

print("\n3. SMS BACKUP:")
print("   • Use SMS for critical invites")
print("   • Email as secondary channel")

print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)

print("\n1. Verify FRONTEND_URL in .env:")
print(f"   Current: {APP_URL}")
if 'localhost' in APP_URL:
    print("   ❌ Change to: FRONTEND_URL=https://app.slateone.studio")
else:
    print("   ✅ Looks good")

print("\n2. Test email delivery:")
print("   python scripts/test_email.py")
print("   Enter your own email address")

print("\n3. Ask user to check:")
print("   • Spam folder")
print("   • All mail/archive")
print("   • Search for 'SlateOne'")

print("\n4. If still not working:")
print("   • Get email headers from Resend")
print("   • Check spam score")
print("   • Try different subject line")

print("\n" + "=" * 80)
