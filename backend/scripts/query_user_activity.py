#!/usr/bin/env python3
"""
Query specific user and script activity from Supabase
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

load_dotenv()

from supabase import create_client

# Initialize Supabase with admin access
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

USER_ID = 'f9666301-7c92-4046-afeb-1112f350aee9'
SCRIPT_ID = '835f46b2-eb34-4ed7-9982-a3cd418fdf62'

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def format_timestamp(ts):
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return ts

# 1. User Profile
print_section("USER PROFILE")
try:
    user = supabase.table('profiles').select('*').eq('id', USER_ID).execute()
    if user.data:
        u = user.data[0]
        print(f"Email: {u.get('email', 'N/A')}")
        print(f"Full Name: {u.get('full_name', 'N/A')}")
        print(f"Job Title: {u.get('job_title', 'N/A')}")
        print(f"Phone: {u.get('phone', 'N/A')}")
        print(f"Created: {format_timestamp(u.get('created_at'))}")
        print(f"Updated: {format_timestamp(u.get('updated_at'))}")
    else:
        print("❌ User not found")
except Exception as e:
    print(f"Error fetching user: {e}")

# 2. Payment Status
print_section("PAYMENT STATUS")
try:
    user_data = supabase.table('profiles').select('email').eq('id', USER_ID).single().execute()
    if user_data.data:
        email = user_data.data['email']
        payment = supabase.table('beta_payments').select('*').eq('email', email).execute()
        if payment.data:
            p = payment.data[0]
            print(f"✅ PAID USER")
            print(f"Payment Reference: {p.get('payment_reference', 'N/A')}")
            print(f"Payment Date: {format_timestamp(p.get('payment_date'))}")
            print(f"Amount: R{p.get('amount', 'N/A')}")
            print(f"Status: {p.get('status', 'N/A')}")
        else:
            print("🆓 TRIAL USER (No payment found)")
except Exception as e:
    print(f"Error checking payment: {e}")

# 3. Script Details
print_section("SCRIPT DETAILS")
try:
    script = supabase.table('scripts').select('*').eq('id', SCRIPT_ID).execute()
    if script.data:
        s = script.data[0]
        print(f"Title: {s.get('title', 'N/A')}")
        print(f"Uploaded: {format_timestamp(s.get('created_at'))}")
        print(f"Updated: {format_timestamp(s.get('updated_at'))}")
        print(f"Analysis Status: {s.get('analysis_status', 'N/A')}")
        print(f"Is Locked: {s.get('is_locked', False)}")
        print(f"Locked At: {format_timestamp(s.get('locked_at'))}")
        print(f"Current Revision: {s.get('current_revision_color', 'N/A')}")
        
        # Check ownership
        if s.get('user_id') == USER_ID:
            print(f"✅ User owns this script")
        else:
            print(f"⚠️  User does NOT own this script (Owner: {s.get('user_id')})")
    else:
        print("❌ Script not found")
except Exception as e:
    print(f"Error fetching script: {e}")

# 4. Script Pages
print_section("SCRIPT PAGES")
try:
    pages = supabase.table('script_pages').select('*', count='exact').eq('script_id', SCRIPT_ID).execute()
    print(f"Total Pages: {pages.count}")
    if pages.data:
        print(f"Page Range: {min(p['page_number'] for p in pages.data)} - {max(p['page_number'] for p in pages.data)}")
except Exception as e:
    print(f"Error fetching pages: {e}")

# 5. Scenes Analysis
print_section("SCENES ANALYSIS")
try:
    scenes = supabase.table('scenes').select('*').eq('script_id', SCRIPT_ID).order('scene_order').execute()
    
    if scenes.data:
        print(f"Total Scenes: {len(scenes.data)}\n")
        
        analyzed = [s for s in scenes.data if s.get('analysis_status') == 'complete']
        pending = [s for s in scenes.data if s.get('analysis_status') == 'pending']
        analyzing = [s for s in scenes.data if s.get('analysis_status') == 'analyzing']
        failed = [s for s in scenes.data if s.get('analysis_status') == 'failed']
        
        print(f"✅ Analyzed: {len(analyzed)}")
        print(f"⏳ Pending: {len(pending)}")
        print(f"🔄 Analyzing: {len(analyzing)}")
        print(f"❌ Failed: {len(failed)}\n")
        
        print("Scene Breakdown:")
        print(f"{'Scene':<10} {'Status':<12} {'INT/EXT':<10} {'Setting':<30} {'Characters':<15}")
        print("-" * 80)
        
        for scene in scenes.data[:20]:  # Show first 20
            scene_num = scene.get('scene_number', 'N/A')
            status = scene.get('analysis_status', 'N/A')
            int_ext = scene.get('int_ext', 'N/A')
            setting = (scene.get('setting', 'N/A') or 'N/A')[:28]
            
            # Count characters
            chars = scene.get('characters', [])
            char_count = len(chars) if chars else 0
            
            status_icon = {
                'complete': '✅',
                'pending': '⏳',
                'analyzing': '🔄',
                'failed': '❌'
            }.get(status, '?')
            
            print(f"{scene_num:<10} {status_icon} {status:<10} {int_ext:<10} {setting:<30} {char_count} chars")
        
        if len(scenes.data) > 20:
            print(f"\n... and {len(scenes.data) - 20} more scenes")
            
    else:
        print("❌ No scenes found")
except Exception as e:
    print(f"Error fetching scenes: {e}")

# 6. Analysis Jobs
print_section("ANALYSIS JOBS")
try:
    jobs = supabase.table('analysis_jobs').select('*').eq('script_id', SCRIPT_ID).order('created_at', desc=True).execute()
    
    if jobs.data:
        print(f"Total Jobs: {len(jobs.data)}\n")
        
        queued = [j for j in jobs.data if j.get('status') == 'queued']
        processing = [j for j in jobs.data if j.get('status') == 'processing']
        completed = [j for j in jobs.data if j.get('status') == 'completed']
        failed = [j for j in jobs.data if j.get('status') == 'failed']
        
        print(f"⏳ Queued: {len(queued)}")
        print(f"🔄 Processing: {len(processing)}")
        print(f"✅ Completed: {len(completed)}")
        print(f"❌ Failed: {len(failed)}\n")
        
        print("Recent Jobs:")
        print(f"{'Job Type':<20} {'Status':<12} {'Created':<20} {'Completed':<20}")
        print("-" * 80)
        
        for job in jobs.data[:10]:  # Show last 10
            job_type = job.get('job_type', 'N/A')
            status = job.get('status', 'N/A')
            created = format_timestamp(job.get('created_at'))
            completed = format_timestamp(job.get('completed_at'))
            
            print(f"{job_type:<20} {status:<12} {created:<20} {completed:<20}")
            
    else:
        print("No analysis jobs found")
except Exception as e:
    print(f"Error fetching jobs: {e}")

# 7. Reports Generated
print_section("REPORTS GENERATED")
try:
    reports = supabase.table('reports').select('*').eq('script_id', SCRIPT_ID).order('created_at', desc=True).execute()
    
    if reports.data:
        print(f"Total Reports: {len(reports.data)}\n")
        
        for report in reports.data:
            print(f"Report ID: {report.get('id')}")
            print(f"  Type: {report.get('report_type', 'N/A')}")
            print(f"  Created: {format_timestamp(report.get('created_at'))}")
            print(f"  Generated By: {report.get('generated_by', 'N/A')}")
            print(f"  Has PDF: {'✅' if report.get('pdf_url') else '❌'}")
            print()
    else:
        print("No reports generated yet")
except Exception as e:
    print(f"Error fetching reports: {e}")

# 8. Report Shares (PDF Downloads)
print_section("REPORT SHARES & DOWNLOADS")
try:
    # First get all reports for this script
    script_reports = supabase.table('reports').select('id').eq('script_id', SCRIPT_ID).execute()
    
    if script_reports.data:
        report_ids = [r['id'] for r in script_reports.data]
        
        # Then get shares for those reports
        shares = supabase.table('report_shares').select('*').in_('report_id', report_ids).order('created_at', desc=True).execute()
        
        if shares.data:
            print(f"Total Shares: {len(shares.data)}\n")
            
            for share in shares.data:
                print(f"Share Token: {share.get('share_token', 'N/A')}")
                print(f"  Report ID: {share.get('report_id', 'N/A')}")
                print(f"  Created: {format_timestamp(share.get('created_at'))}")
                print(f"  Expires: {format_timestamp(share.get('expires_at'))}")
                print(f"  Can Print: {'✅' if share.get('can_print') else '❌'}")
                print(f"  Can Download: {'✅' if share.get('can_download') else '❌'}")
                print(f"  Access Count: {share.get('access_count', 0)}")
                print()
        else:
            print("No report shares found")
    else:
        print("No reports generated yet (so no shares)")
except Exception as e:
    print(f"Error fetching shares: {e}")

# 9. Script Versions (Revisions)
print_section("SCRIPT VERSIONS")
try:
    versions = supabase.table('script_versions').select('*').eq('script_id', SCRIPT_ID).order('version_number', desc=True).execute()
    
    if versions.data:
        print(f"Total Versions: {len(versions.data)}\n")
        
        for version in versions.data:
            print(f"Version {version.get('version_number', 'N/A')}")
            print(f"  Revision Color: {version.get('revision_color', 'N/A')}")
            print(f"  Created: {format_timestamp(version.get('created_at'))}")
            print(f"  Created By: {version.get('created_by', 'N/A')}")
            print()
    else:
        print("No versions found (script not locked yet)")
except Exception as e:
    print(f"Error fetching versions: {e}")

# 10. Department Notes
print_section("DEPARTMENT NOTES")
try:
    notes = supabase.table('department_notes').select('*', count='exact').eq('script_id', SCRIPT_ID).execute()
    
    if notes.data:
        print(f"Total Notes: {notes.count}\n")
        
        # Group by note type
        by_type = {}
        for note in notes.data:
            note_type = note.get('note_type', 'general')
            if note_type not in by_type:
                by_type[note_type] = []
            by_type[note_type].append(note)
        
        for note_type, type_notes in by_type.items():
            print(f"{note_type.upper()}: {len(type_notes)} notes")
    else:
        print("No department notes found")
except Exception as e:
    print(f"Error fetching notes: {e}")

# 11. Team Members
print_section("TEAM COLLABORATION")
try:
    members = supabase.table('script_members').select('*').eq('script_id', SCRIPT_ID).execute()
    
    if members.data:
        print(f"Total Team Members: {len(members.data)}\n")
        
        for member in members.data:
            print(f"User ID: {member.get('user_id', 'N/A')}")
            print(f"  Role: {member.get('role', 'N/A')}")
            print(f"  Joined: {format_timestamp(member.get('joined_at'))}")
            print()
    else:
        print("No team members (solo project)")
except Exception as e:
    print(f"Error fetching team: {e}")

print_section("ACTIVITY REPORT COMPLETE")
print(f"User ID: {USER_ID}")
print(f"Script ID: {SCRIPT_ID}")
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()
