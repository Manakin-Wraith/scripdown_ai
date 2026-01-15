"""
Diagnose Email Architecture Across Two Projects
Identifies conflicts, misconfigurations, and delivery issues.
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("EMAIL ARCHITECTURE DIAGNOSIS")
print("=" * 80)

# Project 1: App (twzfaizeyqwevmhjyicz.supabase.co)
print("\n📱 PROJECT 1: APP (app.slateone.studio)")
print("-" * 80)

app_config = {
    "SUPABASE_URL": os.getenv('SUPABASE_URL', 'NOT SET'),
    "RESEND_API_KEY": os.getenv('RESEND_API_KEY', 'NOT SET'),
    "RESEND_FROM_EMAIL": os.getenv('RESEND_FROM_EMAIL', 'NOT SET'),
    "RESEND_FROM_NAME": os.getenv('RESEND_FROM_NAME', 'NOT SET'),
}

for key, value in app_config.items():
    masked_value = value[:10] + "..." if len(value) > 10 and value != 'NOT SET' else value
    print(f"   {key}: {masked_value}")

# Check if using Supabase Auth emails
print("\n📧 Email Types in App:")
print("   1. Supabase Auth Emails (confirmation, password reset)")
print("   2. Resend Transactional Emails (welcome, reminders)")

# Project 2: Marketing Site (yoqcitfxarpbfldxanhi.supabase.co)
print("\n\n🌐 PROJECT 2: MARKETING SITE (slateone.studio)")
print("-" * 80)
print("   ⚠️  Configuration not accessible from this environment")
print("   Need to check separately")

print("\n\n" + "=" * 80)
print("POTENTIAL CONFLICTS")
print("=" * 80)

issues = []

# Check 1: Same domain for both projects
if 'slateone.studio' in app_config.get('RESEND_FROM_EMAIL', ''):
    issues.append({
        'severity': 'HIGH',
        'issue': 'Both projects likely using same domain (slateone.studio)',
        'impact': 'DNS conflicts, SPF/DKIM issues, email reputation problems',
        'solution': 'Use subdomains: app@slateone.studio vs hello@slateone.studio'
    })

# Check 2: Resend API key
if app_config['RESEND_API_KEY'] != 'NOT SET':
    issues.append({
        'severity': 'MEDIUM',
        'issue': 'Using Resend for transactional emails',
        'impact': 'Rate limits shared across projects if same API key',
        'solution': 'Use separate Resend API keys for each project'
    })

# Check 3: Supabase Auth emails
if 'twzfaizeyqwevmhjyicz' in app_config['SUPABASE_URL']:
    issues.append({
        'severity': 'MEDIUM',
        'issue': 'Supabase Auth emails use default SMTP',
        'impact': 'May go to spam, inconsistent delivery',
        'solution': 'Configure custom SMTP in Supabase Dashboard'
    })

if not issues:
    print("\n✅ No obvious conflicts detected")
else:
    for i, issue in enumerate(issues, 1):
        print(f"\n{i}. [{issue['severity']}] {issue['issue']}")
        print(f"   Impact: {issue['impact']}")
        print(f"   Solution: {issue['solution']}")

print("\n\n" + "=" * 80)
print("RECOMMENDED DIAGNOSTIC STEPS")
print("=" * 80)

steps = [
    "1. Check DNS Records",
    "   - Run: dig TXT slateone.studio",
    "   - Look for multiple SPF records (causes conflicts)",
    "   - Verify DKIM records for both projects",
    "",
    "2. Check Resend Dashboard",
    "   - View sending domains",
    "   - Check if both projects use same domain",
    "   - Review delivery logs for patterns",
    "",
    "3. Check Supabase Auth Settings",
    "   - Project 1: twzfaizeyqwevmhjyicz.supabase.co",
    "   - Project 2: yoqcitfxarpbfldxanhi.supabase.co",
    "   - Compare SMTP configurations",
    "   - Check email template settings",
    "",
    "4. Test Email Delivery",
    "   - Send test from Project 1 (app)",
    "   - Send test from Project 2 (marketing)",
    "   - Check headers for authentication results",
    "",
    "5. Review Email Logs",
    "   - Supabase logs for auth emails",
    "   - Resend logs for transactional emails",
    "   - Look for patterns in failures"
]

for step in steps:
    print(step)

print("\n" + "=" * 80)
print("NEXT ACTIONS")
print("=" * 80)
print("\n1. Run DNS diagnostics:")
print("   python scripts/check_dns_conflicts.py")
print("\n2. Compare Supabase configurations:")
print("   python scripts/compare_supabase_configs.py")
print("\n3. Test email delivery:")
print("   python scripts/test_email_both_projects.py")
print("\n" + "=" * 80)
