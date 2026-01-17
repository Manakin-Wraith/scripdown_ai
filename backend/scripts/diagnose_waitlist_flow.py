#!/usr/bin/env python3
"""
Diagnose Waitlist Email Flow
Traces the complete email communication pipeline from Notel waitlist to user inbox.
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from supabase import create_client

# Configuration
NOTEL_SUPABASE_URL = os.getenv('NOTEL_SUPABASE_URL')
NOTEL_SUPABASE_KEY = os.getenv('NOTEL_SUPABASE_SERVICE_KEY')
MAIN_SUPABASE_URL = os.getenv('SUPABASE_URL')
MAIN_SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
RESEND_FROM_EMAIL = os.getenv('RESEND_FROM_EMAIL')

print("=" * 80)
print("WAITLIST EMAIL FLOW DIAGNOSTIC")
print("=" * 80)

# Step 1: Check Notel Supabase Connection
print("\n📊 STEP 1: Notel Supabase (Waitlist Source)")
print("-" * 80)

if not NOTEL_SUPABASE_URL or not NOTEL_SUPABASE_KEY:
    print("❌ CRITICAL: Notel Supabase credentials missing")
    print("   Required in .env:")
    print("   - NOTEL_SUPABASE_URL")
    print("   - NOTEL_SUPABASE_SERVICE_KEY")
    print("\n⚠️  Without these, waitlist users cannot be fetched!")
else:
    print(f"✅ Credentials configured")
    print(f"   URL: {NOTEL_SUPABASE_URL}")
    
    try:
        notel_client = create_client(NOTEL_SUPABASE_URL, NOTEL_SUPABASE_KEY)
        
        # Test connection and fetch waitlist
        result = notel_client.table('waitlist').select('*').limit(5).execute()
        
        if result.data:
            print(f"✅ Connection successful")
            print(f"   Found {len(result.data)} waitlist entries (showing first 5)")
            print("\n   Sample waitlist data:")
            for i, user in enumerate(result.data[:3], 1):
                email = user.get('email', 'N/A')
                name = user.get('name') or user.get('first_name', 'N/A')
                created = user.get('created_at', 'N/A')
                print(f"   {i}. {email} - {name} (joined: {created})")
        else:
            print("⚠️  Connection OK but no waitlist entries found")
            print("   Table 'waitlist' exists but is empty")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   Possible issues:")
        print("   - Wrong credentials")
        print("   - Table 'waitlist' doesn't exist")
        print("   - Network/firewall issue")

# Step 2: Check Main Supabase (early_access_users table)
print("\n📊 STEP 2: Main Supabase (early_access_users table)")
print("-" * 80)

if not MAIN_SUPABASE_URL or not MAIN_SUPABASE_KEY:
    print("❌ CRITICAL: Main Supabase credentials missing")
else:
    print(f"✅ Credentials configured")
    print(f"   URL: {MAIN_SUPABASE_URL}")
    
    try:
        main_client = create_client(MAIN_SUPABASE_URL, MAIN_SUPABASE_KEY)
        
        # Check early_access_users table
        result = main_client.table('early_access_users').select('*').limit(5).execute()
        
        print(f"✅ Table 'early_access_users' accessible")
        print(f"   Total entries: {len(result.data) if result.data else 0}")
        
        if result.data:
            print("\n   Sample entries:")
            for i, user in enumerate(result.data[:3], 1):
                email = user.get('email', 'N/A')
                status = user.get('status', 'N/A')
                invited = user.get('invited_at', 'N/A')
                print(f"   {i}. {email} - Status: {status} (invited: {invited})")
        
        # Check status distribution
        statuses = main_client.table('early_access_users').select('status').execute()
        if statuses.data:
            from collections import Counter
            status_counts = Counter(u['status'] for u in statuses.data)
            print(f"\n   Status distribution:")
            for status, count in status_counts.items():
                print(f"   - {status}: {count}")
                
    except Exception as e:
        print(f"❌ Error accessing early_access_users: {e}")

# Step 3: Check Email Service Configuration
print("\n📊 STEP 3: Email Service (Resend)")
print("-" * 80)

if not RESEND_API_KEY:
    print("❌ CRITICAL: RESEND_API_KEY missing")
else:
    print(f"✅ API Key configured: {RESEND_API_KEY[:10]}...{RESEND_API_KEY[-4:]}")

if not RESEND_FROM_EMAIL:
    print("❌ CRITICAL: RESEND_FROM_EMAIL missing")
else:
    print(f"✅ From email: {RESEND_FROM_EMAIL}")
    
    if RESEND_FROM_EMAIL == 'onboarding@resend.dev':
        print("   ℹ️  Using Resend's test domain (works immediately)")
    elif 'slateone.studio' in RESEND_FROM_EMAIL:
        print("   ✅ Using custom domain (must be verified in Resend)")
        print("   → Verify at: https://resend.com/domains")

# Step 4: Trace Email Flow
print("\n📊 STEP 4: Email Flow Analysis")
print("-" * 80)

print("\nCurrent email pipeline:")
print("1. Notel Waitlist (waitlist table)")
print("   ↓")
print("2. Script: send_waitlist_early_access.py")
print("   - Fetches from Notel waitlist")
print("   - Registers in main early_access_users")
print("   - Sends email via Resend")
print("   ↓")
print("3. Main Project (early_access_users table)")
print("   - Status: 'invited'")
print("   - Tracks invite_sent_at")
print("   ↓")
print("4. Email Service (Resend)")
print("   - Sends from: hello@slateone.studio")
print("   - Template: Early Access Invite")
print("   ↓")
print("5. User Inbox")

# Step 5: Identify Issues
print("\n🔍 STEP 5: Potential Issues")
print("-" * 80)

issues = []

if not NOTEL_SUPABASE_URL or not NOTEL_SUPABASE_KEY:
    issues.append({
        'severity': 'CRITICAL',
        'issue': 'Cannot fetch waitlist users',
        'fix': 'Add NOTEL_SUPABASE_URL and NOTEL_SUPABASE_SERVICE_KEY to .env'
    })

if not RESEND_API_KEY:
    issues.append({
        'severity': 'CRITICAL',
        'issue': 'Cannot send emails',
        'fix': 'Add RESEND_API_KEY to .env'
    })

if RESEND_FROM_EMAIL and 'slateone.studio' in RESEND_FROM_EMAIL:
    issues.append({
        'severity': 'HIGH',
        'issue': 'Custom domain may not be verified',
        'fix': 'Verify slateone.studio in Resend dashboard'
    })

if issues:
    print(f"Found {len(issues)} issue(s):\n")
    for i, issue in enumerate(issues, 1):
        print(f"{i}. [{issue['severity']}] {issue['issue']}")
        print(f"   Fix: {issue['fix']}\n")
else:
    print("✅ No configuration issues detected")
    print("\nIf emails still not working, check:")
    print("1. Resend domain verification status")
    print("2. Supabase SMTP configuration (for auth emails)")
    print("3. Email logs in Resend dashboard")

# Step 6: Recommended Actions
print("\n🔧 STEP 6: Recommended Actions")
print("-" * 80)

print("\n1. Test Notel connection:")
print("   python scripts/send_waitlist_early_access.py")

print("\n2. Verify email delivery:")
print("   python scripts/test_email.py")

print("\n3. Check Resend logs:")
print("   https://resend.com/emails")

print("\n4. Sync existing users:")
print("   python scripts/sync_early_access_users.py")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
