"""
Email Service using Resend
Handles sending transactional emails for team invites and notifications.
"""

import os
import resend
from typing import Optional, Dict, Any

# Initialize Resend with API key
resend.api_key = os.getenv('RESEND_API_KEY')

# Import email tracking service
try:
    from services.email_tracking_service import log_email_sent
except ImportError:
    # Fallback if tracking service not available
    def log_email_sent(*args, **kwargs):
        return {'success': False, 'error': 'Tracking service not available'}

# Email configuration
DEFAULT_FROM_EMAIL = os.getenv('RESEND_FROM_EMAIL', 'hello@slateone.studio')
APP_NAME = "SlateOne"
APP_URL = os.getenv('FRONTEND_URL', 'https://app.slateone.studio')


def is_configured() -> bool:
    """Check if email service is properly configured."""
    return bool(resend.api_key)


def send_email(
    to: str,
    subject: str,
    html: str,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
    text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send an email using Resend.
    
    Args:
        to: Recipient email address
        subject: Email subject
        html: HTML content of the email
        from_email: Sender email (defaults to RESEND_FROM_EMAIL)
        reply_to: Reply-to email address
        text: Plain text version (improves deliverability)
    
    Returns:
        Response from Resend API
    """
    if not is_configured():
        print("Warning: Email service not configured (RESEND_API_KEY missing)")
        return {'error': 'Email service not configured'}
    
    try:
        params = {
            "from": from_email or DEFAULT_FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html
        }
        
        if reply_to:
            params["reply_to"] = reply_to
        
        if text:
            params["text"] = text
        
        response = resend.Emails.send(params)
        print(f"Email sent successfully to {to}: {response}")
        return response
    except Exception as e:
        print(f"Error sending email to {to}: {e}")
        return {'error': str(e)}


def send_invite_accepted_notification(
    to_email: str,
    inviter_name: str,
    accepter_name: str,
    script_title: str,
    department: str,
    script_url: str
) -> Dict[str, Any]:
    """
    Send notification email when someone accepts a team invite.
    
    Args:
        to_email: Email of the person who sent the invite
        inviter_name: Name of the person who sent the invite
        accepter_name: Name of the person who accepted
        script_title: Title of the script
        department: Department they joined as
        script_url: URL to the script
    """
    subject = f"🎬 {accepter_name} joined your team on {APP_NAME}!"
    
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
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 32px;">
                                <p style="margin: 0 0 8px 0; font-size: 14px; color: #9CA3AF;">
                                    Hi {inviter_name},
                                </p>
                                
                                <h2 style="margin: 0 0 24px 0; font-size: 28px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
                                    Great news! Your invite was accepted.
                                </h2>
                                
                                <div style="background-color: #262626; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td style="padding-bottom: 16px;">
                                                <span style="font-size: 12px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.5px;">Team Member</span>
                                                <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: 600; color: #FFFFFF;">{accepter_name}</p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding-bottom: 16px;">
                                                <span style="font-size: 12px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.5px;">Script</span>
                                                <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: 600; color: #FFFFFF;">{script_title}</p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td>
                                                <span style="font-size: 12px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.5px;">Department</span>
                                                <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: 600; color: #F59E0B;">{department}</p>
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                
                                <a href="{script_url}" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    View Script →
                                </a>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #2A2A2A; text-align: center;">
                                <p style="margin: 0; font-size: 12px; color: #6B7280;">
                                    You received this email because you invited someone to collaborate on {APP_NAME}.
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
    
    return send_email(to_email, subject, html)


def send_test_email(to_email: str) -> Dict[str, Any]:
    """
    Send a test email to verify the email service is working.
    
    Args:
        to_email: Email address to send test to
    """
    subject = f"🎬 Test Email from {APP_NAME}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 32px; text-align: center;">
                                <h2 style="margin: 0 0 16px 0; font-size: 28px; font-weight: 700; color: #FFFFFF;">
                                    ✅ Email Service Working!
                                </h2>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                                    This is a test email from {APP_NAME}. If you're seeing this, your email service is configured correctly!
                                </p>
                                
                                <div style="background-color: #262626; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                                    <p style="margin: 0; font-size: 14px; color: #6B7280;">
                                        Sent to: <strong style="color: #FFFFFF;">{to_email}</strong>
                                    </p>
                                </div>
                                
                                <a href="{APP_URL}" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    Go to {APP_NAME} →
                                </a>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #2A2A2A; text-align: center;">
                                <p style="margin: 0; font-size: 12px; color: #6B7280;">
                                    This is a test email from {APP_NAME}.
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
    
    return send_email(to_email, subject, html)


# Yoco payment link for beta access
YOCO_PAYMENT_LINK = "https://pay.yoco.com/r/mEDpxp"


def send_welcome_email(
    to_email: str,
    full_name: str,
    has_paid: bool = False
) -> Dict[str, Any]:
    """
    Send welcome email to new users after signup.
    
    Args:
        to_email: User's email address
        full_name: User's full name
        has_paid: Whether user has already paid for beta access
    """
    first_name = full_name.split(' ')[0] if full_name else 'there'
    
    if has_paid:
        # User has already paid - welcome them to full access
        subject = f"🎬 Welcome to {APP_NAME}, {first_name}!"
        cta_section = f"""
                                <div style="background: linear-gradient(135deg, #10B981, #059669); border-radius: 12px; padding: 24px; margin-bottom: 24px; text-align: center;">
                                    <p style="margin: 0 0 8px 0; font-size: 14px; color: rgba(255,255,255,0.8);">✅ BETA ACCESS CONFIRMED</p>
                                    <p style="margin: 0; font-size: 18px; font-weight: 600; color: #FFFFFF;">You have full access to SlateOne!</p>
                                </div>
                                
                                <a href="{APP_URL}/scripts" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    Start Using {APP_NAME} →
                                </a>
        """
    else:
        # User hasn't paid - show Yoco payment link
        subject = f"🎬 Welcome to {APP_NAME}! Complete your beta access"
        cta_section = f"""
                                <div style="background-color: #262626; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                                    <p style="margin: 0 0 8px 0; font-size: 14px; color: #F59E0B; font-weight: 600;">⚡ BETA ACCESS OFFER</p>
                                    <p style="margin: 0 0 16px 0; font-size: 16px; color: #FFFFFF; line-height: 1.5;">
                                        Get <strong>1 year of full access</strong> to SlateOne for a one-time payment of <strong style="color: #F59E0B;">R249</strong>.
                                    </p>
                                    <ul style="margin: 0 0 16px 0; padding-left: 20px; color: #9CA3AF; font-size: 14px; line-height: 1.8;">
                                        <li>AI-powered script breakdown</li>
                                        <li>Unlimited scene analysis</li>
                                        <li>Team collaboration tools</li>
                                        <li>Export reports & stripboards</li>
                                    </ul>
                                </div>
                                
                                <a href="{YOCO_PAYMENT_LINK}" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    💳 Pay R249 & Get Access →
                                </a>
                                
                                <p style="margin: 16px 0 0 0; font-size: 12px; color: #6B7280;">
                                    Secure payment via Yoco. Your access will be activated immediately.
                                </p>
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
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 32px;">
                                <h2 style="margin: 0 0 16px 0; font-size: 28px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
                                    Welcome, {first_name}! 🎉
                                </h2>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                                    Thanks for signing up for {APP_NAME} – the AI-powered script breakdown tool for film and television production teams.
                                </p>
                                
                                {cta_section}
                            </td>
                        </tr>
                        
                        <!-- Features -->
                        <tr>
                            <td style="padding: 0 32px 32px 32px;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding: 16px; background-color: #262626; border-radius: 8px; margin-bottom: 12px;">
                                            <p style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600; color: #FFFFFF;">📄 Upload Scripts</p>
                                            <p style="margin: 0; font-size: 13px; color: #9CA3AF;">Drop your PDF and get instant scene detection</p>
                                        </td>
                                    </tr>
                                </table>
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 12px;">
                                    <tr>
                                        <td style="padding: 16px; background-color: #262626; border-radius: 8px;">
                                            <p style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600; color: #FFFFFF;">🤖 AI Analysis</p>
                                            <p style="margin: 0; font-size: 13px; color: #9CA3AF;">Extract characters, props, wardrobe & more</p>
                                        </td>
                                    </tr>
                                </table>
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 12px;">
                                    <tr>
                                        <td style="padding: 16px; background-color: #262626; border-radius: 8px;">
                                            <p style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600; color: #FFFFFF;">👥 Team Collaboration</p>
                                            <p style="margin: 0; font-size: 13px; color: #9CA3AF;">Invite your crew and work together</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #2A2A2A; text-align: center;">
                                <p style="margin: 0 0 8px 0; font-size: 12px; color: #6B7280;">
                                    Questions? Reply to this email or reach out at hello@slateone.studio
                                </p>
                                <p style="margin: 0; font-size: 12px; color: #6B7280;">
                                    © {APP_NAME} • AI-Powered Script Breakdown
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
    
    return send_email(to_email, subject, html)


# Extended trial duration for early access users
EARLY_ACCESS_TRIAL_DAYS = 30


def send_early_access_invite(
    to_email: str,
    first_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send early access invite email to users who requested early access.
    These users get a 30-day trial with full access to Phase 1 features.
    
    Args:
        to_email: User's email address
        first_name: User's first name (optional, will use "there" if not provided)
    """
    name = first_name if first_name else 'there'
    
    subject = f"🎬 You're in! Early access to {APP_NAME} is here"
    
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
                            </td>
                        </tr>
                        
                        <!-- Early Access Badge -->
                        <tr>
                            <td style="background-color: #10B981; padding: 12px; text-align: center;">
                                <p style="margin: 0; font-size: 14px; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 1px;">
                                    ✨ Early Access Invite ✨
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 32px;">
                                <h2 style="margin: 0 0 16px 0; font-size: 28px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
                                    Hey {name}, you're in! 🎉
                                </h2>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                                    Thanks for your interest in {APP_NAME}! You've been selected for early access to our AI-powered script breakdown tool.
                                </p>
                                
                                <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.2)); border: 1px solid #10B981; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                                    <p style="margin: 0 0 8px 0; font-size: 14px; color: #10B981; font-weight: 600;">🎁 YOUR EARLY ACCESS PERK</p>
                                    <p style="margin: 0; font-size: 20px; font-weight: 700; color: #FFFFFF;">
                                        30 days free access to all features
                                    </p>
                                </div>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                                    Sign up with this email address and start using {APP_NAME} immediately. No credit card required.
                                </p>
                                
                                <a href="{APP_URL}/login" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    Get Started →
                                </a>
                            </td>
                        </tr>
                        
                        <!-- Phase 1 Features -->
                        <tr>
                            <td style="padding: 0 32px 32px 32px;">
                                <p style="margin: 0 0 16px 0; font-size: 14px; color: #10B981; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">✓ What's included</p>
                                
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding: 12px 16px; background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; margin-bottom: 8px;">
                                            <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: #FFFFFF;">📄 Script Upload & Library</p>
                                            <p style="margin: 0; font-size: 13px; color: #9CA3AF;">Upload PDF scripts with automatic scene detection</p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 8px;">
                                    <tr>
                                        <td style="padding: 12px 16px; background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px;">
                                            <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: #FFFFFF;">🎬 Scene Viewer & Breakdown</p>
                                            <p style="margin: 0; font-size: 13px; color: #9CA3AF;">Browse scenes with master-detail layout</p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 8px;">
                                    <tr>
                                        <td style="padding: 12px 16px; background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px;">
                                            <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: #FFFFFF;">🤖 AI Scene Analysis</p>
                                            <p style="margin: 0; font-size: 13px; color: #9CA3AF;">On-demand AI breakdown for characters, props & more</p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 8px;">
                                    <tr>
                                        <td style="padding: 12px 16px; background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px;">
                                            <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: #FFFFFF;">📋 Stripboard & PDF Export</p>
                                            <p style="margin: 0; font-size: 13px; color: #9CA3AF;">View one-liner stripboard and download as PDF</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #2A2A2A; text-align: center;">
                                <p style="margin: 0 0 8px 0; font-size: 12px; color: #6B7280;">
                                    Questions? Just reply to this email – we'd love to hear from you!
                                </p>
                                <p style="margin: 0; font-size: 12px; color: #6B7280;">
                                    © {APP_NAME} • AI-Powered Script Breakdown
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
    
    # Send the email
    result = send_email(
        to=to_email, 
        subject=subject, 
        html=html,
        from_email="hello@slateone.studio",
        reply_to="hello@slateone.studio"
    )
    
    # Log to email tracking if email was sent successfully
    if result and 'error' not in result:
        resend_email_id = result.get('id')
        log_email_sent(
            email_type='early_access_invite',
            recipient_email=to_email,
            recipient_name=first_name or 'Early Access User',
            resend_email_id=resend_email_id,
            user_status='early_access',
            metadata={'trial_days': EARLY_ACCESS_TRIAL_DAYS}
        )
    
    return result


def send_expiration_reminder_email(
    to_email: str,
    full_name: str,
    days_remaining: int,
    is_trial: bool = True
) -> Dict[str, Any]:
    """
    Send expiration reminder email to users whose trial or subscription is ending soon.
    
    Args:
        to_email: User's email address
        full_name: User's full name
        days_remaining: Days until expiration
        is_trial: True if trial, False if paid subscription
    """
    first_name = full_name.split(' ')[0] if full_name else 'there'
    
    if is_trial:
        subject = f"⏰ Your {APP_NAME} trial ends in {days_remaining} days"
        expiry_type = "trial"
        action_text = "Upgrade now to keep your scripts and unlock all features"
    else:
        subject = f"⏰ Your {APP_NAME} subscription expires in {days_remaining} days"
        expiry_type = "subscription"
        action_text = "Renew now to continue using SlateOne without interruption"
    
    urgency_color = "#EF4444" if days_remaining <= 3 else "#F59E0B"
    
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
                            </td>
                        </tr>
                        
                        <!-- Urgency Banner -->
                        <tr>
                            <td style="background-color: {urgency_color}; padding: 16px; text-align: center;">
                                <p style="margin: 0; font-size: 18px; font-weight: 700; color: #FFFFFF;">
                                    ⏰ {days_remaining} {'day' if days_remaining == 1 else 'days'} remaining
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 32px;">
                                <h2 style="margin: 0 0 16px 0; font-size: 24px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
                                    Hey {first_name}, your {expiry_type} is ending soon
                                </h2>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                                    {action_text}. Don't lose access to your scripts and AI-powered breakdowns.
                                </p>
                                
                                <div style="background-color: #262626; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                                    <p style="margin: 0 0 8px 0; font-size: 14px; color: #F59E0B; font-weight: 600;">🚀 WHAT YOU'LL KEEP</p>
                                    <ul style="margin: 0; padding-left: 20px; color: #FFFFFF; font-size: 14px; line-height: 1.8;">
                                        <li>All your uploaded scripts</li>
                                        <li>AI-powered scene breakdowns</li>
                                        <li>Team collaboration features</li>
                                        <li>Reports & stripboard exports</li>
                                    </ul>
                                </div>
                                
                                <a href="{YOCO_PAYMENT_LINK}" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    💳 {'Upgrade Now - R249' if is_trial else 'Renew Now'}
                                </a>
                                
                                <p style="margin: 16px 0 0 0; font-size: 12px; color: #6B7280;">
                                    Secure payment via Yoco. Get 1 year of full access.
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #2A2A2A; text-align: center;">
                                <p style="margin: 0 0 8px 0; font-size: 12px; color: #6B7280;">
                                    Questions? Reply to this email or reach out at hello@slateone.studio
                                </p>
                                <p style="margin: 0; font-size: 12px; color: #6B7280;">
                                    © {APP_NAME} • AI-Powered Script Breakdown
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
    
    return send_email(to_email, subject, html)


def send_early_access_reminder(
    to_email: str,
    first_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send reminder email to early access invitees who haven't signed up yet.
    IMPROVED VERSION with better deliverability.
    
    Args:
        to_email: User's email address
        first_name: User's first name (optional, will use "there" if not provided)
    """
    name = first_name if first_name else 'there'
    
    # DECISION 1 (OPEN): Clear expectation - reader knows what this email is
    subject = f"SlateOne Early Access: Your testing account is waiting"
    
    # DECISION 2 (READ): Point stated in first 3 lines
    text = f"""Hi {name},

Your SlateOne testing account is active. We need you to upload one script and share feedback.

This matters because you're a working filmmaker. Your input shapes what we build next.

What to do:
1. Sign up at {APP_URL}/login
2. Upload one script
3. Reply with what works and what doesn't

You get 30 days free access. No credit card needed.

The ask: 15 minutes of your time to test the AI breakdown and tell us what you think.

Sign up here: {APP_URL}/login

---
SlateOne - Script Breakdown
SlateOne.studio
Cape Town, South Africa

Questions? Reply to this email: hello@slateone.studio
Unsubscribe: {APP_URL}/unsubscribe
"""
    
    # HTML version (cleaner, less aggressive styling)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #F9FAFB; color: #111827;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #F9FAFB; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #FFFFFF; border-radius: 8px; overflow: hidden; border: 1px solid #E5E7EB;">
                        <!-- Header -->
                        <tr>
                            <td style="background-color: #F59E0B; padding: 32px; text-align: center;">
                                <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #000000;">
                                    SlateOne
                                </h1>
                                <p style="margin: 8px 0 0 0; font-size: 14px; color: #78350F;">AI-Powered Script Breakdown</p>
                            </td>
                        </tr>
                        
                        <!-- DECISION 2: Point in first 3 lines -->
                        <tr>
                            <td style="padding: 32px 32px 24px 32px;">
                                <p style="margin: 0 0 16px 0; font-size: 16px; color: #111827; line-height: 1.5;">
                                    Hi {name},
                                </p>
                                
                                <p style="margin: 0 0 8px 0; font-size: 18px; color: #111827; line-height: 1.4; font-weight: 600;">
                                    Your SlateOne testing account is active.
                                </p>
                                
                                <p style="margin: 0 0 24px 0; font-size: 18px; color: #111827; line-height: 1.4; font-weight: 600;">
                                    We need you to upload one script and share feedback.
                                </p>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #4B5563; line-height: 1.6;">
                                    This matters because you're a working filmmaker. Your input shapes what we build next.
                                </p>
                                
                                <!-- What to do - scannable -->
                                <div style="background-color: #F3F4F6; border-radius: 6px; padding: 20px; margin-bottom: 24px;">
                                    <p style="margin: 0 0 12px 0; font-size: 14px; color: #374151; font-weight: 600;">What to do:</p>
                                    
                                    <p style="margin: 0 0 8px 0; font-size: 15px; color: #111827; line-height: 1.6;">
                                        1. Sign up at SlateOne
                                    </p>
                                    <p style="margin: 0 0 8px 0; font-size: 15px; color: #111827; line-height: 1.6;">
                                        2. Upload one script
                                    </p>
                                    <p style="margin: 0; font-size: 15px; color: #111827; line-height: 1.6;">
                                        3. Reply with what works and what doesn't
                                    </p>
                                </div>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #4B5563; line-height: 1.6;">
                                    You get 30 days free access. No credit card needed.
                                </p>
                                
                                <p style="margin: 0 0 32px 0; font-size: 16px; color: #111827; line-height: 1.6; font-weight: 600;">
                                    The ask: 15 minutes of your time to test the AI breakdown and tell us what you think.
                                </p>
                                
                                <!-- DECISION 3: Single primary action -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center">
                                            <a href="{APP_URL}/login" style="display: inline-block; background-color: #F59E0B; color: #000000; text-decoration: none; padding: 16px 48px; border-radius: 6px; font-weight: 600; font-size: 16px;">
                                                Sign Up Now
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Footer - minimal, no competing links -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #E5E7EB; text-align: center;">
                                <p style="margin: 0 0 16px 0; font-size: 14px; color: #6B7280; line-height: 1.6;">
                                    Use <strong>{to_email}</strong> to sign up
                                </p>
                                
                                <!-- Company info - small, non-distracting -->
                                <p style="margin: 0; font-size: 11px; color: #9CA3AF; line-height: 1.6;">
                                    SlateOne · SlateOne.studio · Cape Town, South Africa<br>
                                    <a href="mailto:hello@slateone.studio" style="color: #9CA3AF; text-decoration: none;">hello@slateone.studio</a> · 
                                    <a href="{APP_URL}/unsubscribe" style="color: #9CA3AF; text-decoration: none;">Unsubscribe</a>
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
    
    return send_email(to_email, subject, html, text=text)


def send_waitlist_welcome_email(
    to_email: str,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Send welcome email to new waitlist signups.
    Optimized for 10/10 spam score with clean, professional design.
    
    Args:
        to_email: User's email address
        metadata: Optional metadata from waitlist signup (role, scripts_per_year, etc.)
    """
    # Extract metadata if available
    role = metadata.get('role') if metadata else None
    
    subject = "Welcome to SlateOne - You're on the list!"
    
    # Plain text version for better deliverability
    text = f"""Hi there,

Thanks for joining the SlateOne waitlist! We're building AI-powered script breakdown tools for film and television production teams.

What's next:
- We'll notify you when early access opens
- You'll get 30 days free to test all features
- Your feedback will shape the product

We're launching soon. Keep an eye on your inbox.

---
SlateOne - Script Breakdown
SlateOne.studio
Cape Town, South Africa

Questions? Reply to this email: hello@slateone.studio
"""
    
    # HTML version with clean, professional design
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #F9FAFB; color: #111827;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #F9FAFB; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #FFFFFF; border-radius: 8px; overflow: hidden; border: 1px solid #E5E7EB;">
                        <!-- Header -->
                        <tr>
                            <td style="background-color: #F59E0B; padding: 32px; text-align: center;">
                                <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #000000;">
                                    🎬 SlateOne
                                </h1>
                                <p style="margin: 8px 0 0 0; font-size: 14px; color: #78350F;">AI-Powered Script Breakdown</p>
                            </td>
                        </tr>
                        
                        <!-- Welcome Badge -->
                        <tr>
                            <td style="background-color: #10B981; padding: 12px; text-align: center;">
                                <p style="margin: 0; font-size: 14px; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 1px;">
                                    ✓ You're on the waitlist
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 32px;">
                                <h2 style="margin: 0 0 16px 0; font-size: 22px; font-weight: 700; color: #111827; line-height: 1.3;">
                                    Thanks for joining!
                                </h2>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #4B5563; line-height: 1.6;">
                                    We're building AI-powered script breakdown tools for film and television production teams. You'll be among the first to know when we launch.
                                </p>
                                
                                <!-- What's Next -->
                                <div style="background-color: #F3F4F6; border-radius: 6px; padding: 20px; margin-bottom: 24px;">
                                    <p style="margin: 0 0 12px 0; font-size: 14px; color: #374151; font-weight: 600;">What's next:</p>
                                    
                                    <p style="margin: 0 0 8px 0; font-size: 15px; color: #111827; line-height: 1.6;">
                                        ✓ We'll notify you when early access opens
                                    </p>
                                    <p style="margin: 0 0 8px 0; font-size: 15px; color: #111827; line-height: 1.6;">
                                        ✓ You'll get 30 days free to test all features
                                    </p>
                                    <p style="margin: 0; font-size: 15px; color: #111827; line-height: 1.6;">
                                        ✓ Your feedback will shape the product
                                    </p>
                                </div>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #4B5563; line-height: 1.6;">
                                    We're launching soon. Keep an eye on your inbox for updates.
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Features Preview -->
                        <tr>
                            <td style="padding: 0 32px 32px 32px;">
                                <p style="margin: 0 0 16px 0; font-size: 14px; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">What you'll get:</p>
                                
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding: 12px 16px; background-color: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px; margin-bottom: 8px;">
                                            <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: #111827;">📄 AI Script Analysis</p>
                                            <p style="margin: 0; font-size: 13px; color: #6B7280;">Automatic scene detection and breakdown</p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 8px;">
                                    <tr>
                                        <td style="padding: 12px 16px; background-color: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px;">
                                            <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: #111827;">👥 Team Collaboration</p>
                                            <p style="margin: 0; font-size: 13px; color: #6B7280;">Work together with your crew</p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 8px;">
                                    <tr>
                                        <td style="padding: 12px 16px; background-color: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px;">
                                            <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: #111827;">📊 Production Reports</p>
                                            <p style="margin: 0; font-size: 13px; color: #6B7280;">Export stripboards and breakdowns</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #E5E7EB; text-align: center;">
                                <p style="margin: 0 0 8px 0; font-size: 12px; color: #6B7280;">
                                    Questions? Reply to this email at hello@slateone.studio
                                </p>
                                <p style="margin: 0; font-size: 11px; color: #9CA3AF; line-height: 1.6;">
                                    SlateOne · SlateOne.studio · Cape Town, South Africa
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
    
    # Send the email
    result = send_email(
        to=to_email,
        subject=subject,
        html=html,
        text=text,
        from_email="hello@slateone.studio",
        reply_to="hello@slateone.studio"
    )
    
    # Log to email tracking if email was sent successfully
    if result and 'error' not in result:
        resend_email_id = result.get('id')
        log_email_sent(
            email_type='waitlist_welcome',
            recipient_email=to_email,
            recipient_name='Waitlist User',
            resend_email_id=resend_email_id,
            user_status='waitlist',
            metadata=metadata or {}
        )
    
    return result
