"""
Check Resend domain verification status via API.
"""

import os
import sys
from dotenv import load_dotenv
import requests

load_dotenv()

RESEND_API_KEY = os.getenv('RESEND_API_KEY')

if not RESEND_API_KEY:
    print("❌ RESEND_API_KEY not found in .env")
    sys.exit(1)

print("=" * 70)
print("RESEND DOMAIN VERIFICATION STATUS")
print("=" * 70)

# Get all domains
response = requests.get(
    'https://api.resend.com/domains',
    headers={
        'Authorization': f'Bearer {RESEND_API_KEY}',
        'Content-Type': 'application/json'
    }
)

if response.status_code != 200:
    print(f"\n❌ API Error: {response.status_code}")
    print(response.text)
    sys.exit(1)

domains = response.json().get('data', [])

if not domains:
    print("\n⚠️  No domains found in Resend account")
    sys.exit(0)

print(f"\nFound {len(domains)} domain(s):\n")

for domain in domains:
    domain_name = domain.get('name', 'N/A')
    domain_id = domain.get('id', 'N/A')
    status = domain.get('status', 'N/A')
    region = domain.get('region', 'N/A')
    created = domain.get('created_at', 'N/A')
    
    print(f"Domain: {domain_name}")
    print(f"ID: {domain_id}")
    print(f"Status: {status}")
    print(f"Region: {region}")
    print(f"Created: {created}")
    
    # Get detailed verification status
    detail_response = requests.get(
        f'https://api.resend.com/domains/{domain_id}',
        headers={
            'Authorization': f'Bearer {RESEND_API_KEY}',
            'Content-Type': 'application/json'
        }
    )
    
    if detail_response.status_code == 200:
        details = detail_response.json()
        records = details.get('records', [])
        
        print("\nDNS Records Status:")
        for record in records:
            record_type = record.get('record', 'N/A')
            name = record.get('name', 'N/A')
            value = record.get('value', 'N/A')
            status = record.get('status', 'N/A')
            
            status_icon = "✅" if status == "verified" else "❌"
            print(f"  {status_icon} {record_type}: {name}")
            print(f"     Status: {status}")
            if status != "verified":
                print(f"     Expected: {value[:60]}...")
    
    print("\n" + "-" * 70 + "\n")

print("=" * 70)
print("\nRECOMMENDATIONS:")
print("=" * 70)

# Check if slateone.studio is verified
slateone_domain = next((d for d in domains if d.get('name') == 'slateone.studio'), None)

if not slateone_domain:
    print("\n⚠️  slateone.studio not found in Resend")
    print("   Action: Add domain in Resend dashboard")
elif slateone_domain.get('status') != 'verified':
    print("\n❌ slateone.studio is NOT verified")
    print("   Action: Fix DNS records or re-verify domain")
    print("   URL: https://resend.com/domains")
else:
    print("\n✅ slateone.studio is verified")
    print("   If emails still bounce, check:")
    print("   1. Recipient email address is valid")
    print("   2. Resend dashboard for specific bounce reason")
    print("   3. Supabase email template for errors")
