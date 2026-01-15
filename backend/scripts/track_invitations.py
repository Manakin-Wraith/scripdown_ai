"""
Track invitations and signups using existing Supabase auth.users table.
No schema changes required - uses built-in Supabase Auth data.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta
from collections import defaultdict

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def get_invitation_stats():
    """Get comprehensive invitation and signup statistics."""
    
    users = supabase.auth.admin.list_users()
    
    # Basic counts
    total = len(users)
    confirmed = [u for u in users if u.email_confirmed_at]
    pending = [u for u in users if not u.email_confirmed_at]
    active = [u for u in users if u.last_sign_in_at]
    
    # Recent signups (last 7 days)
    from dateutil import parser
    week_ago = datetime.now() - timedelta(days=7)
    recent_signups = []
    today_signups = []
    today = datetime.now().date()
    
    for u in users:
        try:
            created = parser.parse(u.created_at)
            if created > week_ago:
                recent_signups.append(u)
            if created.date() == today:
                today_signups.append(u)
        except:
            pass
    
    return {
        'total': total,
        'confirmed': len(confirmed),
        'pending': len(pending),
        'active': len(active),
        'recent_signups': len(recent_signups),
        'today_signups': len(today_signups),
        'confirmed_users': confirmed,
        'pending_users': pending,
        'active_users': active,
        'today_users': today_signups
    }

def display_dashboard():
    """Display invitation tracking dashboard."""
    
    print("=" * 70)
    print("INVITATION & SIGNUP TRACKING DASHBOARD")
    print("=" * 70)
    
    stats = get_invitation_stats()
    
    # Overview
    print("\n📊 OVERVIEW")
    print("-" * 70)
    print(f"Total Signups:        {stats['total']}")
    print(f"Confirmed:            {stats['confirmed']} ({stats['confirmed']/stats['total']*100:.1f}%)" if stats['total'] > 0 else "Confirmed: 0")
    print(f"Pending:              {stats['pending']} ({stats['pending']/stats['total']*100:.1f}%)" if stats['total'] > 0 else "Pending: 0")
    print(f"Active (logged in):   {stats['active']} ({stats['active']/stats['total']*100:.1f}%)" if stats['total'] > 0 else "Active: 0")
    
    # Recent activity
    print("\n📈 RECENT ACTIVITY")
    print("-" * 70)
    print(f"Last 7 days:          {stats['recent_signups']} new signup(s)")
    print(f"Today:                {stats['today_signups']} new signup(s)")
    
    # Today's signups detail
    if stats['today_users']:
        print("\n🆕 TODAY'S SIGNUPS")
        print("-" * 70)
        for user in stats['today_users']:
            status = "✅ Confirmed" if user.email_confirmed_at else "⏳ Pending"
            logged_in = "🟢 Active" if user.last_sign_in_at else "⚪ Not logged in"
            print(f"{status} {logged_in} | {user.email}")
            print(f"   Created: {user.created_at}")
            if user.email_confirmed_at:
                print(f"   Confirmed: {user.email_confirmed_at}")
            if user.last_sign_in_at:
                print(f"   Last Login: {user.last_sign_in_at}")
            print()
    
    # Pending confirmations
    if stats['pending_users']:
        print("\n⏳ PENDING CONFIRMATIONS")
        print("-" * 70)
        from dateutil import parser as date_parser
        for user in stats['pending_users']:
            try:
                created = date_parser.parse(user.created_at)
                hours_ago = (datetime.now(created.tzinfo) - created).total_seconds() / 3600
                print(f"❌ {user.email}")
                print(f"   Waiting {hours_ago:.1f} hours")
                print()
            except:
                print(f"❌ {user.email}")
                print(f"   Created: {user.created_at}")
                print()
    
    # Conversion funnel
    print("\n🎯 CONVERSION FUNNEL")
    print("-" * 70)
    if stats['total'] > 0:
        print(f"Invited → Signed Up:  {stats['total']} users (100%)")
        print(f"Signed Up → Confirmed: {stats['confirmed']} users ({stats['confirmed']/stats['total']*100:.1f}%)")
        print(f"Confirmed → Active:    {stats['active']} users ({stats['active']/stats['confirmed']*100:.1f}%)" if stats['confirmed'] > 0 else "Confirmed → Active: 0 users (0%)")
    else:
        print("No users yet")
    
    print("\n" + "=" * 70)

def export_csv():
    """Export user data to CSV."""
    import csv
    from datetime import datetime
    
    users = supabase.auth.admin.list_users()
    
    filename = f"user_invitations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Email', 'Created At', 'Confirmed At', 'Last Sign In', 'Status'])
        
        for user in users:
            status = 'Confirmed' if user.email_confirmed_at else 'Pending'
            writer.writerow([
                user.email,
                user.created_at,
                user.email_confirmed_at or 'Not confirmed',
                user.last_sign_in_at or 'Never',
                status
            ])
    
    print(f"\n✅ Exported to: {filename}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--export':
        export_csv()
    else:
        display_dashboard()
        
        print("\n💡 TIP: Run with --export to save data to CSV")
        print("   python3 scripts/track_invitations.py --export")
