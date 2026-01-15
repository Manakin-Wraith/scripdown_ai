"""
Check DNS Configuration for Email Conflicts
Identifies SPF, DKIM, and DMARC issues that may cause delivery problems.
"""

import subprocess
import re

def run_dns_query(domain, record_type):
    """Run DNS query and return results."""
    try:
        result = subprocess.run(
            ['dig', '+short', record_type, domain],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except Exception as e:
        return [f"Error: {e}"]

print("=" * 80)
print("DNS CONFIGURATION ANALYSIS")
print("=" * 80)

domain = "slateone.studio"

# Check SPF Records
print(f"\n📧 SPF Records for {domain}")
print("-" * 80)
spf_records = run_dns_query(domain, 'TXT')
spf_found = [r for r in spf_records if 'v=spf1' in r]

if not spf_found:
    print("❌ No SPF record found")
    print("   Impact: Emails may be marked as spam")
    print("   Solution: Add SPF record in DNS")
elif len(spf_found) > 1:
    print("⚠️  MULTIPLE SPF RECORDS FOUND (CONFLICT!)")
    for i, record in enumerate(spf_found, 1):
        print(f"   {i}. {record}")
    print("\n   Impact: Email authentication will FAIL")
    print("   Solution: Merge into single SPF record")
else:
    print(f"✅ SPF Record: {spf_found[0]}")
    
    # Analyze SPF record
    spf = spf_found[0]
    if 'include:_spf.resend.com' in spf:
        print("   ✓ Resend authorized")
    else:
        print("   ⚠️  Resend NOT authorized in SPF")
    
    if 'include:_spf.google.com' in spf:
        print("   ✓ Google Workspace authorized")
    
    if spf.count('include:') > 5:
        print("   ⚠️  Too many includes (>5) - may cause DNS lookup failures")

# Check DKIM Records
print(f"\n🔐 DKIM Records")
print("-" * 80)
dkim_selectors = ['resend', 'google', 'default', 'mail']
dkim_found = []

for selector in dkim_selectors:
    dkim_domain = f"{selector}._domainkey.{domain}"
    dkim_records = run_dns_query(dkim_domain, 'TXT')
    if dkim_records and dkim_records[0] != '':
        dkim_found.append((selector, dkim_records[0]))
        print(f"✅ {selector}: Found")

if not dkim_found:
    print("❌ No DKIM records found")
    print("   Impact: Emails may be marked as spam")
else:
    print(f"\n   Total DKIM records: {len(dkim_found)}")

# Check DMARC
print(f"\n🛡️  DMARC Policy")
print("-" * 80)
dmarc_records = run_dns_query(f"_dmarc.{domain}", 'TXT')
dmarc_found = [r for r in dmarc_records if 'v=DMARC1' in r]

if not dmarc_found:
    print("⚠️  No DMARC record found")
    print("   Impact: No policy for failed authentication")
    print("   Recommendation: Add DMARC record")
else:
    print(f"✅ DMARC: {dmarc_found[0]}")
    
    dmarc = dmarc_found[0]
    if 'p=none' in dmarc:
        print("   Policy: Monitor only (p=none)")
    elif 'p=quarantine' in dmarc:
        print("   Policy: Quarantine failed emails")
    elif 'p=reject' in dmarc:
        print("   Policy: Reject failed emails")

# Check MX Records
print(f"\n📬 MX Records")
print("-" * 80)
mx_records = run_dns_query(domain, 'MX')
if mx_records and mx_records[0] != '':
    for mx in mx_records:
        print(f"   {mx}")
else:
    print("❌ No MX records found")

print("\n\n" + "=" * 80)
print("DIAGNOSIS SUMMARY")
print("=" * 80)

issues = []

if len(spf_found) > 1:
    issues.append("🔴 CRITICAL: Multiple SPF records causing authentication failures")
elif not spf_found:
    issues.append("🔴 CRITICAL: No SPF record - emails will be marked as spam")
elif 'include:_spf.resend.com' not in spf_found[0]:
    issues.append("🟡 WARNING: Resend not authorized in SPF")

if not dkim_found:
    issues.append("🟡 WARNING: No DKIM records - reduces email trustworthiness")

if not dmarc_found:
    issues.append("🟡 WARNING: No DMARC policy - no protection against spoofing")

if not issues:
    print("\n✅ DNS configuration looks good!")
else:
    print("\nIssues found:")
    for issue in issues:
        print(f"   {issue}")

print("\n\n" + "=" * 80)
print("RECOMMENDED ACTIONS")
print("=" * 80)

if len(spf_found) > 1:
    print("\n1. FIX CRITICAL: Merge SPF records")
    print("   Current SPF records:")
    for record in spf_found:
        print(f"   - {record}")
    print("\n   Merge into single record:")
    print("   v=spf1 include:_spf.resend.com include:_spf.google.com ~all")

if 'include:_spf.resend.com' not in (spf_found[0] if spf_found else ''):
    print("\n2. Add Resend to SPF:")
    print("   Update SPF record to include: include:_spf.resend.com")

if not dkim_found:
    print("\n3. Configure DKIM:")
    print("   - Go to Resend Dashboard → Domains")
    print("   - Copy DKIM records")
    print("   - Add to DNS provider")

if not dmarc_found:
    print("\n4. Add DMARC policy:")
    print("   Record: _dmarc.slateone.studio")
    print("   Value: v=DMARC1; p=none; rua=mailto:dmarc@slateone.studio")

print("\n" + "=" * 80)
