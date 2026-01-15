#!/usr/bin/env python3
"""
Send personalized feedback request emails to early access users
Based on their actual activity in SlateOne
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

from supabase import create_client
from services.email_service import send_email

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_user_activity(user_id):
    """Get comprehensive activity summary for a user"""
    
    activity = {
        'user_id': user_id,
        'scripts_uploaded': 0,
        'total_scenes': 0,
        'scenes_analyzed': 0,
        'analysis_success_rate': 0,
        'stripboard_used': False,
        'last_activity': None,
        'feature_completion': '0/3',
        'has_incomplete_profile': False
    }
    
    try:
        # Try to get user profile first
        try:
            user = supabase.table('profiles').select('email, full_name, created_at').eq('id', user_id).single().execute()
            activity['email'] = user.data['email']
            activity['name'] = user.data.get('full_name', user.data['email'].split('@')[0])
            activity['signup_date'] = user.data['created_at']
            # Check if profile is incomplete (no full name)
            if not user.data.get('full_name'):
                activity['has_incomplete_profile'] = True
        except Exception as profile_error:
            # Profile doesn't exist, try to get from auth.users via scripts table
            print(f"  ⚠️  Profile not found, checking scripts for email...")
            activity['has_incomplete_profile'] = True
            scripts = supabase.table('scripts').select('user_id').eq('user_id', user_id).limit(1).execute()
            if not scripts.data:
                print(f"  ❌ No scripts found for user")
                return None
            
            # Get email from Supabase auth admin API
            try:
                from supabase.client import ClientOptions
                admin_client = create_client(
                    os.getenv('SUPABASE_URL'),
                    os.getenv('SUPABASE_SERVICE_KEY'),
                    options=ClientOptions(auto_refresh_token=False)
                )
                auth_user = admin_client.auth.admin.get_user_by_id(user_id)
                activity['email'] = auth_user.user.email
                activity['name'] = auth_user.user.email.split('@')[0]
                activity['signup_date'] = auth_user.user.created_at
                print(f"  ✅ Found email from auth: {activity['email']}")
            except Exception as auth_error:
                print(f"  ❌ Could not get user from auth: {auth_error}")
                return None
        
        # Get scripts
        scripts = supabase.table('scripts').select('*').eq('user_id', user_id).execute()
        activity['scripts_uploaded'] = len(scripts.data) if scripts.data else 0
        
        if scripts.data:
            latest_script = scripts.data[0]
            activity['script_title'] = latest_script.get('title', 'Untitled')
            activity['script_id'] = latest_script['id']
            
            # Get scenes for this script
            scenes = supabase.table('scenes').select('*').eq('script_id', latest_script['id']).execute()
            if scenes.data:
                activity['total_scenes'] = len(scenes.data)
                analyzed = [s for s in scenes.data if s.get('analysis_status') == 'complete']
                activity['scenes_analyzed'] = len(analyzed)
                
                if activity['total_scenes'] > 0:
                    activity['analysis_success_rate'] = int((len(analyzed) / activity['total_scenes']) * 100)
            
            # Check if stripboard was accessed (script locked = stripboard used)
            is_locked = latest_script.get('is_locked', False)
            activity['stripboard_used'] = is_locked
            
            activity['last_activity'] = latest_script.get('updated_at', latest_script.get('created_at'))
        
        # Calculate feature completion
        features_complete = 0
        if activity['scripts_uploaded'] > 0:
            features_complete += 1
        if activity['scenes_analyzed'] > 0:
            features_complete += 1
        if activity['stripboard_used']:
            features_complete += 1
        
        activity['feature_completion'] = f"{features_complete}/3"
        
        return activity
        
    except Exception as e:
        print(f"Error getting activity for {user_id}: {e}")
        return None


def generate_feedback_email(activity):
    """Generate personalized feedback request email"""
    
    name = activity['name']
    script_title = activity.get('script_title', 'your script')
    scenes = activity['total_scenes']
    analyzed = activity['scenes_analyzed']
    success_rate = activity['analysis_success_rate']
    stripboard_used = activity['stripboard_used']
    
    # Determine user segment
    if stripboard_used:
        segment = "full_user"
    elif analyzed > 0:
        segment = "analyzer"
    else:
        segment = "uploader"
    
    # Email content based on segment
    if segment == "full_user":
        subject = f"🎬 {name}, you've tried everything! What do you think?"
        body = f"""Hi {name},

You're one of our power users! You've uploaded "{script_title}", analyzed {analyzed} scenes, AND tried the stripboard. 

That's exactly the workflow we're perfecting. Here's what I need to know:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR SLATEONE JOURNEY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ UPLOAD → {activity['scripts_uploaded']} script(s)
✅ ANALYZE → {analyzed}/{scenes} scenes ({success_rate}% success)
✅ STRIPBOARD → Used

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 3 QUICK QUESTIONS:

1. What worked smoothly?
2. What felt clunky or confusing?
3. What would make SlateOne 10x better for your workflow?

Just hit reply with your thoughts. Even bullet points help!

Thanks for being an early adopter,
The SlateOne Team

P.S. Your feedback shapes our roadmap. We read every response.
"""
    
    elif segment == "analyzer":
        subject = f"🎬 {name}, quick question about your SlateOne experience"
        body = f"""Hi {name},

I saw you uploaded "{script_title}" and got {analyzed} scenes analyzed ({success_rate}% success rate). That's awesome! 🎉

Quick question: 

I noticed you haven't tried the Stripboard feature yet. I'm curious:

❓ Was it unclear how to access it?
❓ Do you not need that feature?
❓ Something else?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR SLATEONE JOURNEY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ UPLOAD → {activity['scripts_uploaded']} script(s)
✅ ANALYZE → {analyzed}/{scenes} scenes ({success_rate}% success)
⏸️ STRIPBOARD → Not used yet

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 I NEED YOUR FEEDBACK:

**About UPLOAD & ANALYZE:**
• Did everything work smoothly?
• Did the AI get your scenes/characters right?
• Anything it missed or got wrong?

**About STRIPBOARD:**
• Have you tried it? If not, what's stopping you?
• You can find it in the top menu after analyzing your script

Just hit reply with your thoughts!

Thanks,
The SlateOne Team
"""
    
    else:  # uploader
        subject = f"🎬 {name}, how did the upload go?"
        body = f"""Hi {name},

I saw you uploaded "{script_title}" to SlateOne. Thanks for trying it out!

Quick question: **What happened after the upload?**

I noticed the scenes haven't been analyzed yet. I'm curious:

❓ Was the "Analyze" button unclear?
❓ Did something not work?
❓ Are you planning to come back to it?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR SLATEONE JOURNEY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ UPLOAD → {activity['scripts_uploaded']} script(s)
⏸️ ANALYZE → Not started yet
⏸️ STRIPBOARD → Not used yet

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

We're in early access mode, so your honest feedback helps us fix what's broken.

🎯 QUICK QUESTION:

Was the upload process smooth? Any issues or confusion?

Just hit reply and let me know!

Thanks,
The SlateOne Team

P.S. If you need help getting started, we're happy to jump on a quick call.
"""
    
    return subject, body


def generate_html_email(activity, subject, body_text):
    """Generate professional HTML email matching SlateOne design"""
    
    APP_NAME = "SlateOne"
    APP_URL = os.getenv('FRONTEND_URL', 'https://app.slateone.studio')
    
    # Extract key data from activity
    name = activity['name']
    script_title = activity.get('script_title', 'your script')
    scripts_count = activity['scripts_uploaded']
    scenes_analyzed = activity['scenes_analyzed']
    total_scenes = activity['total_scenes']
    success_rate = activity['analysis_success_rate']
    stripboard_used = activity['stripboard_used']
    has_incomplete_profile = activity.get('has_incomplete_profile', False)
    
    # Determine segment for customized content
    if stripboard_used:
        segment = "full_user"
    elif scenes_analyzed > 0:
        segment = "analyzer"
    else:
        segment = "uploader"
    
    # Build journey status items
    journey_items = f"""
        <tr>
            <td style="padding: 12px 0; border-bottom: 1px solid #333333;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td width="40" style="vertical-align: top;">
                            <span style="font-size: 20px;">✅</span>
                        </td>
                        <td style="vertical-align: middle;">
                            <p style="margin: 0; font-size: 15px; color: #E5E7EB; font-weight: 500;">
                                UPLOAD <span style="color: #9CA3AF;">→</span> {scripts_count} script(s)
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <td style="padding: 12px 0; border-bottom: 1px solid #333333;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td width="40" style="vertical-align: top;">
                            <span style="font-size: 20px;">{'✅' if scenes_analyzed > 0 else '⏸️'}</span>
                        </td>
                        <td style="vertical-align: middle;">
                            <p style="margin: 0; font-size: 15px; color: #E5E7EB; font-weight: 500;">
                                ANALYZE <span style="color: #9CA3AF;">→</span> {scenes_analyzed}/{total_scenes} scenes ({success_rate}% success)
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <td style="padding: 12px 0;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td width="40" style="vertical-align: top;">
                            <span style="font-size: 20px;">{'✅' if stripboard_used else '⏸️'}</span>
                        </td>
                        <td style="vertical-align: middle;">
                            <p style="margin: 0; font-size: 15px; color: #E5E7EB; font-weight: 500;">
                                STRIPBOARD <span style="color: #9CA3AF;">→</span> {'Used' if stripboard_used else 'Not used yet'}
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    """
    
    # Build questions list based on segment
    if segment == "analyzer":
        questions_html = """
            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 8px 0;">
                <tr>
                    <td width="30" style="vertical-align: top; padding-top: 4px;">
                        <span style="font-size: 18px; color: #EF4444;">❓</span>
                    </td>
                    <td style="padding: 4px 0;">
                        <p style="margin: 0; font-size: 15px; color: #D1D5DB; line-height: 1.5;">
                            Was it unclear how to access it?
                        </p>
                    </td>
                </tr>
                <tr>
                    <td width="30" style="vertical-align: top; padding-top: 4px;">
                        <span style="font-size: 18px; color: #EF4444;">❓</span>
                    </td>
                    <td style="padding: 4px 0;">
                        <p style="margin: 0; font-size: 15px; color: #D1D5DB; line-height: 1.5;">
                            Do you not need that feature?
                        </p>
                    </td>
                </tr>
                <tr>
                    <td width="30" style="vertical-align: top; padding-top: 4px;">
                        <span style="font-size: 18px; color: #EF4444;">❓</span>
                    </td>
                    <td style="padding: 4px 0;">
                        <p style="margin: 0; font-size: 15px; color: #D1D5DB; line-height: 1.5;">
                            Something else?
                        </p>
                    </td>
                </tr>
            </table>
        """
    else:
        questions_html = ""
    
    # Build feedback questions based on segment
    if segment == "analyzer":
        feedback_html = f"""
            <div style="margin: 32px 0;">
                <p style="margin: 0 0 16px 0; font-size: 17px; color: #FFFFFF; font-weight: 600;">
                    We'd love your feedback:
                </p>
                
                <div style="background-color: #1F1F1F; border-radius: 8px; padding: 20px; margin-bottom: 16px;">
                    <p style="margin: 0 0 12px 0; font-size: 14px; color: #F59E0B; font-weight: 600;">
                        About UPLOAD & ANALYZE:
                    </p>
                    <ul style="margin: 0; padding-left: 20px; list-style: none;">
                        <li style="margin: 8px 0; font-size: 14px; color: #D1D5DB; line-height: 1.6;">
                            <span style="color: #9CA3AF;">•</span> Did everything work smoothly?
                        </li>
                        <li style="margin: 8px 0; font-size: 14px; color: #D1D5DB; line-height: 1.6;">
                            <span style="color: #9CA3AF;">•</span> Did the AI get your scenes/characters right?
                        </li>
                        <li style="margin: 8px 0; font-size: 14px; color: #D1D5DB; line-height: 1.6;">
                            <span style="color: #9CA3AF;">•</span> Anything it missed or got wrong?
                        </li>
                    </ul>
                </div>
                
                <div style="background-color: #1F1F1F; border-radius: 8px; padding: 20px;">
                    <p style="margin: 0 0 12px 0; font-size: 14px; color: #F59E0B; font-weight: 600;">
                        About STRIPBOARD:
                    </p>
                    <ul style="margin: 0; padding-left: 20px; list-style: none;">
                        <li style="margin: 8px 0; font-size: 14px; color: #D1D5DB; line-height: 1.6;">
                            <span style="color: #9CA3AF;">•</span> Have you tried it? If not, what's stopping you?
                        </li>
                        <li style="margin: 8px 0; font-size: 14px; color: #D1D5DB; line-height: 1.6;">
                            <span style="color: #9CA3AF;">•</span> You can find it in the top menu after analyzing your script
                        </li>
                    </ul>
                </div>
            </div>
        """
    elif segment == "full_user":
        feedback_html = """
            <div style="margin: 32px 0;">
                <p style="margin: 0 0 16px 0; font-size: 17px; color: #FFFFFF; font-weight: 600;">
                    3 quick questions:
                </p>
                
                <div style="background-color: #1F1F1F; border-radius: 8px; padding: 20px;">
                    <ol style="margin: 0; padding-left: 20px; color: #D1D5DB;">
                        <li style="margin: 12px 0; font-size: 15px; line-height: 1.6;">What worked smoothly?</li>
                        <li style="margin: 12px 0; font-size: 15px; line-height: 1.6;">What felt clunky or confusing?</li>
                        <li style="margin: 12px 0; font-size: 15px; line-height: 1.6;">What would make SlateOne 10x better for your workflow?</li>
                    </ol>
                </div>
            </div>
        """
    else:  # uploader
        feedback_html = """
            <div style="margin: 32px 0;">
                <p style="margin: 0 0 16px 0; font-size: 17px; color: #FFFFFF; font-weight: 600;">
                    Quick question:
                </p>
                
                <div style="background-color: #1F1F1F; border-radius: 8px; padding: 20px;">
                    <p style="margin: 0; font-size: 15px; color: #D1D5DB; line-height: 1.6;">
                        Was the upload process smooth? Any issues or confusion?
                    </p>
                </div>
            </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0F0F0F; color: #FFFFFF;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0F0F0F; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1A1A1A; border-radius: 16px; overflow: hidden; border: 1px solid #2A2A2A;">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #F59E0B, #D97706); padding: 32px; text-align: center;">
                                <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #000000;">
                                    🎬 {APP_NAME}
                                </h1>
                                <p style="margin: 8px 0 0 0; font-size: 14px; color: #78350F;">Early Access Feedback</p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 32px;">
                                <!-- Greeting -->
                                <p style="margin: 0 0 20px 0; font-size: 16px; color: #E5E7EB; line-height: 1.5;">
                                    Hi {name},
                                </p>
                                
                                <!-- Main Message -->
                                <p style="margin: 0 0 16px 0; font-size: 15px; color: #D1D5DB; line-height: 1.6;">
                                    I saw you uploaded <strong style="color: #FFFFFF;">"{script_title}"</strong> and got <strong style="color: #FFFFFF;">{scenes_analyzed} scenes analyzed</strong> ({success_rate}% success rate). That's awesome! 🎉
                                </p>
                                
                                <p style="margin: 0 0 20px 0; font-size: 17px; color: #FFFFFF; font-weight: 600;">
                                    Quick question: What happened next?
                                </p>
                                
                                {f'''<p style="margin: 0 0 16px 0; font-size: 15px; color: #D1D5DB; line-height: 1.6;">
                                    I noticed you haven't tried the Stripboard feature yet. I'm curious:
                                </p>
                                {questions_html}''' if segment == "analyzer" else ''}
                                
                                <!-- Journey Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #262626; border-radius: 12px; margin: 32px 0; border-left: 4px solid #F59E0B;">
                                    <tr>
                                        <td style="padding: 24px;">
                                            <p style="margin: 0 0 16px 0; font-size: 13px; color: #F59E0B; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px;">
                                                YOUR SLATEONE JOURNEY
                                            </p>
                                            <table width="100%" cellpadding="0" cellspacing="0">
                                                {journey_items}
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                                
                                <!-- Feedback Section -->
                                {feedback_html}
                                
                                {f'''<!-- Profile Reminder -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #1F2937; border-left: 4px solid #3B82F6; border-radius: 8px; margin: 24px 0;">
                                    <tr>
                                        <td style="padding: 20px;">
                                            <table width="100%" cellpadding="0" cellspacing="0">
                                                <tr>
                                                    <td width="40" style="vertical-align: top;">
                                                        <span style="font-size: 24px;">👤</span>
                                                    </td>
                                                    <td style="vertical-align: top;">
                                                        <p style="margin: 0 0 8px 0; font-size: 14px; color: #60A5FA; font-weight: 600;">
                                                            Quick reminder: Complete your profile
                                                        </p>
                                                        <p style="margin: 0; font-size: 14px; color: #D1D5DB; line-height: 1.5;">
                                                            We noticed your profile is incomplete. Adding your name and details helps us personalize your experience and makes collaboration with your team easier.
                                                        </p>
                                                        <p style="margin: 12px 0 0 0;">
                                                            <a href="{APP_URL}/profile" style="display: inline-block; color: #60A5FA; text-decoration: none; font-size: 14px; font-weight: 500;">
                                                                Complete your profile →
                                                            </a>
                                                        </p>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>''' if has_incomplete_profile else ''}
                                
                                <!-- CTA Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background: linear-gradient(135deg, #F59E0B15, #D9770615); border: 2px solid #F59E0B; border-radius: 12px; margin: 32px 0;">
                                    <tr>
                                        <td style="padding: 24px; text-align: center;">
                                            <p style="margin: 0 0 8px 0; font-size: 16px; color: #FFFFFF; font-weight: 600;">
                                                💬 Just hit reply with your thoughts
                                            </p>
                                            <p style="margin: 0; font-size: 14px; color: #D1D5DB;">
                                                Even bullet points help us improve!
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #2A2A2A; text-align: center;">
                                <p style="margin: 0 0 4px 0; font-size: 14px; color: #9CA3AF;">
                                    Thanks,
                                </p>
                                <p style="margin: 0 0 12px 0; font-size: 14px; color: #FFFFFF; font-weight: 600;">
                                    The SlateOne Team
                                </p>
                                <p style="margin: 0; font-size: 12px; color: #6B7280;">
                                    Building the future of script breakdown with filmmakers like you
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    return html


def send_feedback_request(user_id):
    """Send feedback request email to a specific user"""
    
    print(f"\n{'='*70}")
    print(f"SENDING FEEDBACK REQUEST")
    print(f"{'='*70}\n")
    
    # Get activity
    print(f"📊 Fetching activity for user: {user_id}")
    activity = get_user_activity(user_id)
    
    if not activity:
        print(f"❌ Could not fetch activity for user {user_id}")
        return False
    
    print(f"✅ Activity fetched for: {activity['email']}")
    print(f"   Scripts: {activity['scripts_uploaded']}")
    print(f"   Scenes Analyzed: {activity['scenes_analyzed']}/{activity['total_scenes']}")
    print(f"   Stripboard Used: {'Yes' if activity['stripboard_used'] else 'No'}")
    print(f"   Feature Completion: {activity['feature_completion']}")
    
    # Generate email
    print(f"\n📧 Generating personalized email...")
    subject, body = generate_feedback_email(activity)
    
    print(f"\nSubject: {subject}\n")
    print(f"Preview:\n{body[:300]}...\n")
    
    # Send email
    confirm = input("Send this email? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Email not sent")
        return False
    
    try:
        # Generate professional HTML email matching SlateOne design
        html_body = generate_html_email(activity, subject, body)
        
        result = send_email(
            to=activity['email'],
            subject=subject,
            html=html_body
        )
        print(f"✅ Email sent successfully!")
        print(f"   Resend ID: {result.get('id', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Send feedback request emails')
    parser.add_argument('--user-id', help='Specific user ID to send to')
    parser.add_argument('--all', action='store_true', help='Send to all early access users')
    
    args = parser.parse_args()
    
    if args.user_id:
        send_feedback_request(args.user_id)
    elif args.all:
        # Get all early access users
        users = supabase.table('profiles').select('id').execute()
        print(f"Found {len(users.data)} users")
        
        for user in users.data:
            send_feedback_request(user['id'])
            print("\n" + "="*70 + "\n")
    else:
        print("Usage:")
        print("  python scripts/send_feedback_request.py --user-id <user_id>")
        print("  python scripts/send_feedback_request.py --all")
