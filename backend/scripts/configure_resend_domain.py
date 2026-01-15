"""
Configure Resend domain with custom Return-Path for SPF alignment.
This fixes the DMARC SPF alignment issue.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv('RESEND_API_KEY')
DOMAIN = 'slateone.studio'
CUSTOM_RETURN_PATH = 'send'  # Creates send.slateone.studio

def list_domains():
    """List all domains in Resend account."""
    response = requests.get(
        'https://api.resend.com/domains',
        headers={'Authorization': f'Bearer {RESEND_API_KEY}'}
    )
    return response.json()

def get_domain_details(domain_id):
    """Get details for a specific domain."""
    response = requests.get(
        f'https://api.resend.com/domains/{domain_id}',
        headers={'Authorization': f'Bearer {RESEND_API_KEY}'}
    )
    return response.json()

def update_domain_with_custom_return_path():
    """
    Update domain to use custom Return-Path.
    Note: Resend API may require deleting and re-creating the domain.
    """
    print("=" * 60)
    print("RESEND DOMAIN CONFIGURATION")
    print("=" * 60)
    
    if not RESEND_API_KEY:
        print("❌ RESEND_API_KEY not found in environment")
        return
    
    # List existing domains
    print(f"\n📋 Fetching domains...")
    domains = list_domains()
    
    if 'data' in domains:
        print(f"\n✅ Found {len(domains['data'])} domain(s):")
        for domain in domains['data']:
            print(f"\n  Domain: {domain['name']}")
            print(f"  ID: {domain['id']}")
            print(f"  Status: {domain['status']}")
            print(f"  Region: {domain.get('region', 'N/A')}")
            
            # Check if custom Return-Path is set
            if 'return_path' in domain:
                print(f"  Return-Path: {domain['return_path']}")
            else:
                print(f"  Return-Path: Not configured (using default)")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("\n1. Go to Resend Dashboard: https://resend.com/domains")
    print(f"2. Click on '{DOMAIN}'")
    print("3. Look for 'Custom Return-Path' or 'Edit' option")
    print(f"4. Set custom Return-Path to: '{CUSTOM_RETURN_PATH}'")
    print(f"   (This creates: {CUSTOM_RETURN_PATH}.{DOMAIN})")
    print("\n5. Resend will show DNS records to add:")
    print(f"   - MX record for {CUSTOM_RETURN_PATH}.{DOMAIN}")
    print(f"   - TXT record for {CUSTOM_RETURN_PATH}.{DOMAIN}")
    print("\n6. Add those DNS records to Vercel")
    print("7. Click 'Verify' in Resend")
    print("\n" + "=" * 60)

if __name__ == '__main__':
    update_domain_with_custom_return_path()
