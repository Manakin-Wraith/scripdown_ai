"""
Check Resend DNS requirements for slateone.studio domain.
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
print("RESEND DNS REQUIREMENTS FOR slateone.studio")
print("=" * 70)

# Get domain details
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
slateone = next((d for d in domains if d.get('name') == 'slateone.studio'), None)

if not slateone:
    print("\n⚠️  slateone.studio not found in Resend")
    sys.exit(1)

domain_id = slateone.get('id')

# Get detailed DNS records
detail_response = requests.get(
    f'https://api.resend.com/domains/{domain_id}',
    headers={
        'Authorization': f'Bearer {RESEND_API_KEY}',
        'Content-Type': 'application/json'
    }
)

if detail_response.status_code != 200:
    print(f"\n❌ API Error: {detail_response.status_code}")
    sys.exit(1)

details = detail_response.json()
records = details.get('records', [])

print("\nRequired DNS Records:\n")

for record in records:
    record_type = record.get('record', 'N/A')
    name = record.get('name', 'N/A')
    value = record.get('value', 'N/A')
    status = record.get('status', 'N/A')
    
    status_icon = "✅" if status == "verified" else "❌"
    
    print(f"{status_icon} {record_type} Record")
    print(f"   Name: {name}")
    print(f"   Value: {value}")
    print(f"   Status: {status}")
    print()

print("=" * 70)
print("\nCopy these exact values to your Vercel DNS configuration!")
print("=" * 70)
