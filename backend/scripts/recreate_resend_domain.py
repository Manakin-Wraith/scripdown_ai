"""
Safe script to delete and recreate Resend domain with custom Return-Path.
This fixes SPF alignment for DMARC compliance.

WHAT THIS DOES:
1. Documents current domain configuration (backup)
2. Deletes existing domain
3. Recreates domain with customReturnPath='send'
4. Shows DNS records to add to Vercel

WHAT YOU WON'T LOSE:
- Your Supabase database (completely separate)
- User accounts and application data
- Resend API key (stays the same)
- Email logs in Resend dashboard
- Your email templates in code

WHAT HAPPENS:
- Domain verification resets (need to re-verify DNS)
- ~15 min - 2 hour downtime while DNS propagates
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv('RESEND_API_KEY')
DOMAIN = 'slateone.studio'
CUSTOM_RETURN_PATH = 'send'  # Creates send.slateone.studio
REGION = 'us-east-1'  # Default region

def make_request(method, endpoint, data=None):
    """Make authenticated request to Resend API."""
    url = f'https://api.resend.com{endpoint}'
    headers = {
        'Authorization': f'Bearer {RESEND_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    if method == 'GET':
        response = requests.get(url, headers=headers)
    elif method == 'POST':
        response = requests.post(url, headers=headers, json=data)
    elif method == 'DELETE':
        response = requests.delete(url, headers=headers)
    
    return response

def list_domains():
    """List all domains."""
    response = make_request('GET', '/domains')
    return response.json()

def get_domain_id(domain_name):
    """Find domain ID by name."""
    domains = list_domains()
    if 'data' in domains:
        for domain in domains['data']:
            if domain['name'] == domain_name:
                return domain['id']
    return None

def delete_domain(domain_id):
    """Delete a domain."""
    response = make_request('DELETE', f'/domains/{domain_id}')
    return response.status_code == 200

def create_domain_with_custom_return_path():
    """Create domain with custom Return-Path."""
    data = {
        'name': DOMAIN,
        'region': REGION
    }
    
    # Add custom Return-Path if specified
    if CUSTOM_RETURN_PATH:
        data['customReturnPath'] = CUSTOM_RETURN_PATH
    
    response = make_request('POST', '/domains', data)
    return response.json()

def main():
    print("=" * 70)
    print("RESEND DOMAIN RECREATION WITH CUSTOM RETURN-PATH")
    print("=" * 70)
    
    if not RESEND_API_KEY:
        print("\n❌ ERROR: RESEND_API_KEY not found in environment")
        print("Make sure your .env file has RESEND_API_KEY set")
        return
    
    print(f"\n📋 Step 1: Checking current domain configuration...")
    print("-" * 70)
    
    # List current domains
    domains = list_domains()
    if 'data' not in domains:
        print(f"❌ Error fetching domains: {domains}")
        return
    
    print(f"✅ Found {len(domains['data'])} domain(s) in your Resend account")
    
    # Find our domain
    domain_id = get_domain_id(DOMAIN)
    
    if not domain_id:
        print(f"\n⚠️  Domain '{DOMAIN}' not found in Resend")
        print("Creating it now with custom Return-Path...")
    else:
        print(f"\n✅ Found domain: {DOMAIN}")
        print(f"   Domain ID: {domain_id}")
        
        # Backup current configuration
        for domain in domains['data']:
            if domain['name'] == DOMAIN:
                print(f"\n📝 Current Configuration:")
                print(f"   Status: {domain['status']}")
                print(f"   Region: {domain.get('region', 'N/A')}")
                print(f"   Return-Path: {domain.get('return_path', 'Not configured (default)')}")
        
        # Confirm deletion
        print("\n" + "=" * 70)
        print("⚠️  WARNING: About to delete and recreate domain")
        print("=" * 70)
        print("\nThis will:")
        print("  ✅ Keep your API key working")
        print("  ✅ Keep all your application data safe")
        print("  ✅ Keep email logs in Resend dashboard")
        print("  ⚠️  Reset domain verification (need to re-add DNS)")
        print("  ⚠️  Cause ~15 min email downtime during DNS propagation")
        
        confirm = input("\nType 'DELETE' to proceed: ").strip()
        
        if confirm != 'DELETE':
            print("\n❌ Cancelled. No changes made.")
            return
        
        print(f"\n🗑️  Step 2: Deleting domain '{DOMAIN}'...")
        print("-" * 70)
        
        if delete_domain(domain_id):
            print("✅ Domain deleted successfully")
        else:
            print("❌ Failed to delete domain")
            return
    
    # Create new domain with custom Return-Path
    print(f"\n🆕 Step 3: Creating domain with custom Return-Path...")
    print("-" * 70)
    print(f"   Domain: {DOMAIN}")
    print(f"   Custom Return-Path: {CUSTOM_RETURN_PATH}")
    print(f"   Full Return-Path: {CUSTOM_RETURN_PATH}.{DOMAIN}")
    
    result = create_domain_with_custom_return_path()
    
    if 'id' in result:
        print(f"\n✅ Domain created successfully!")
        print(f"   Domain ID: {result['id']}")
        print(f"   Status: {result['status']}")
        
        # Show DNS records to add
        print("\n" + "=" * 70)
        print("📋 DNS RECORDS TO ADD TO VERCEL")
        print("=" * 70)
        
        if 'records' in result:
            print("\nAdd these records to Vercel DNS for slateone.studio:\n")
            
            for record in result['records']:
                print(f"Type: {record['record']}")
                print(f"Name: {record['name']}")
                print(f"Value: {record['value']}")
                if 'priority' in record:
                    print(f"Priority: {record['priority']}")
                print()
        
        print("=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print("\n1. Go to Vercel → Your Project → Settings → Domains")
        print("2. Click on 'slateone.studio' → DNS Records")
        print("3. Add the DNS records shown above")
        print("4. Wait 15 minutes for DNS propagation")
        print("5. Go to Resend Dashboard: https://resend.com/domains")
        print(f"6. Click on '{DOMAIN}' → Click 'Verify DNS Records'")
        print("7. Status should change to 'Verified'")
        print("8. Test email sending with: python scripts/test_email_headers.py")
        print("\n✅ After verification, your SPF alignment will be fixed!")
        
    else:
        print(f"\n❌ Error creating domain: {result}")
        if 'message' in result:
            print(f"   Message: {result['message']}")

if __name__ == '__main__':
    main()
