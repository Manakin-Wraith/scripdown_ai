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


def send_welcome_credits_email(
    to_email: str,
    full_name: str,
    credits: int = 10
) -> Dict[str, Any]:
    """
    Send welcome email to existing users announcing their free credits.
    
    Args:
        to_email: User's email address
        full_name: User's full name
        credits: Number of free credits (default: 10)
    """
    first_name = full_name.split(' ')[0] if full_name else 'there'
    
    subject = f"🎬 Thank you for joining {APP_NAME} - {credits} Free Credits Inside!"
    
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
                        
                        <!-- Thank You Banner -->
                        <tr>
                            <td style="background-color: #10B981; padding: 12px; text-align: center;">
                                <p style="margin: 0; font-size: 14px; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 1px;">
                                    ✨ THANK YOU FOR BEING AN EARLY USER ✨
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 32px;">
                                <h2 style="margin: 0 0 16px 0; font-size: 28px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
                                    Hi {first_name}! 👋
                                </h2>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                                    Thank you for being one of our early users at {APP_NAME}! We're thrilled to have you on board as we build the future of AI-powered script breakdown.
                                </p>
                                
                                <!-- Credits Announcement Card -->
                                <div style="background: linear-gradient(135deg, #F59E0B, #D97706); border-radius: 12px; padding: 32px; margin-bottom: 24px; text-align: center;">
                                    <p style="margin: 0 0 8px 0; font-size: 14px; color: rgba(0,0,0,0.7); font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">🎉 YOU HAVE</p>
                                    <p style="margin: 0 0 8px 0; font-size: 48px; font-weight: 700; color: #000000;">
                                        {credits} <span style="font-size: 24px;">FREE CREDITS</span>
                                    </p>
                                    <p style="margin: 0; font-size: 16px; color: rgba(0,0,0,0.8); font-weight: 500;">
                                        1 credit = 1 script analysis
                                    </p>
                                </div>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                                    These credits are ready to use right now—no payment required. Upload your scripts and let our AI do the heavy lifting!
                                </p>
                                
                                <!-- What You Can Do Section -->
                                <div style="background-color: #262626; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                                    <p style="margin: 0 0 16px 0; font-size: 18px; color: #FFFFFF; font-weight: 600;">
                                        What You Can Do:
                                    </p>
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td style="padding: 8px 0;">
                                                <p style="margin: 0; font-size: 14px; color: #9CA3AF;">
                                                    📄 Upload scripts and get instant AI-powered breakdowns
                                                </p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 8px 0;">
                                                <p style="margin: 0; font-size: 14px; color: #9CA3AF;">
                                                    🎭 Extract characters, props, wardrobe, locations, and more
                                                </p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 8px 0;">
                                                <p style="margin: 0; font-size: 14px; color: #9CA3AF;">
                                                    📊 Export professional stripboards
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                
                                <!-- Feedback Request -->
                                <div style="background-color: #1E293B; border-left: 4px solid #F59E0B; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
                                    <p style="margin: 0 0 12px 0; font-size: 16px; color: #FFFFFF; font-weight: 600;">
                                        💬 We'd Love Your Feedback!
                                    </p>
                                    <p style="margin: 0; font-size: 14px; color: #9CA3AF; line-height: 1.6;">
                                        Your input is invaluable as we refine {APP_NAME}. We'll be sending out a feedback form soon, but in the meantime, feel free to reply to this email with any thoughts, suggestions, or feature requests.
                                    </p>
                                </div>
                                
                                <!-- Spread the Word -->
                                <div style="background-color: #262626; border-radius: 12px; padding: 20px; margin-bottom: 32px; text-align: center;">
                                    <p style="margin: 0 0 8px 0; font-size: 16px; color: #FFFFFF; font-weight: 600;">
                                        🌟 Spread the Word
                                    </p>
                                    <p style="margin: 0; font-size: 14px; color: #9CA3AF; line-height: 1.6;">
                                        Know someone who could benefit from {APP_NAME}? We'd love for you to share it with your network. Every filmmaker, producer, or AD who joins helps us build a better tool for everyone.
                                    </p>
                                </div>
                                
                                <!-- CTA Button -->
                                <div style="text-align: center;">
                                    <a href="{APP_URL}/scripts" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                        Start Using Your Credits →
                                    </a>
                                </div>
                                
                                <p style="margin: 32px 0 0 0; font-size: 16px; color: #9CA3AF; line-height: 1.6; text-align: center;">
                                    Thanks again for being part of our journey!
                                </p>
                                
                                <p style="margin: 16px 0 0 0; font-size: 16px; color: #FFFFFF; font-weight: 500; text-align: center;">
                                    Best,<br>
                                    The {APP_NAME} Team
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
YOCO_PAYMENT_LINK = "https://pay.yoco.com/celebration-house-entertainment?amount=249.00&reference=BetaAccess"


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
                                <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.15)); border: 2px solid #F59E0B; border-radius: 16px; padding: 32px; margin-bottom: 28px; text-align: center;">
                                    <p style="margin: 0 0 12px 0; font-size: 13px; color: #F59E0B; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;">⚡ BETA ACCESS OFFER ⚡</p>
                                    <p style="margin: 0 0 8px 0; font-size: 22px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
                                        Get <strong>1 year of full access</strong>
                                    </p>
                                    <p style="margin: 0 0 20px 0; font-size: 40px; font-weight: 800; color: #F59E0B; line-height: 1;">
                                        R249
                                    </p>
                                    <p style="margin: 0 0 4px 0; font-size: 13px; color: #9CA3AF;">One-time payment · No recurring fees</p>
                                    
                                    <table width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0 0 0;">
                                        <tr>
                                            <td style="padding: 4px 0; text-align: left;"><span style="color: #10B981; font-size: 14px;">✓</span> <span style="color: #D1D5DB; font-size: 14px;">AI-powered script breakdown</span></td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 4px 0; text-align: left;"><span style="color: #10B981; font-size: 14px;">✓</span> <span style="color: #D1D5DB; font-size: 14px;">Unlimited scene analysis</span></td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 4px 0; text-align: left;"><span style="color: #10B981; font-size: 14px;">✓</span> <span style="color: #D1D5DB; font-size: 14px;">Team collaboration tools</span></td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 4px 0; text-align: left;"><span style="color: #10B981; font-size: 14px;">✓</span> <span style="color: #D1D5DB; font-size: 14px;">Export reports & stripboards</span></td>
                                        </tr>
                                    </table>
                                </div>
                                
                                <!-- Primary CTA Button - Full Width -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 12px;">
                                    <tr>
                                        <td align="center">
                                            <a href="{YOCO_PAYMENT_LINK}" style="display: block; width: 100%; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 18px 28px; border-radius: 10px; font-weight: 700; font-size: 18px; text-align: center; box-sizing: border-box;">
                                                💳 Pay R249 & Get Full Access →
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="margin: 0; font-size: 12px; color: #6B7280; text-align: center;">
                                    🔒 Secure payment via Yoco · Access activated immediately
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
                        
                        {"" if has_paid else '''
                        <!-- Second CTA (repeat after features for visibility) -->
                        <tr>
                            <td style="padding: 0 32px 32px 32px;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center">
                                            <a href="''' + YOCO_PAYMENT_LINK + '''" style="display: block; width: 100%; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 16px 28px; border-radius: 10px; font-weight: 700; font-size: 16px; text-align: center; box-sizing: border-box;">
                                                Get Full Access - R249 →
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        '''}
                        
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


def send_feature_announcement_email(
    to_email: str,
    full_name: str,
    features: list = None
) -> Dict[str, Any]:
    """
    Send feature announcement email to existing users about new features.
    Uses the proper email template system.
    
    Args:
        to_email: User's email address
        full_name: User's full name
        features: List of feature dicts with 'title', 'description', 'icon' keys
    """
    from email_templates.registry import EmailTemplateRegistry
    
    first_name = full_name.split(' ')[0] if full_name else 'there'
    
    # Get the feature announcement template
    FeatureAnnouncementEmail = EmailTemplateRegistry.get('feature_announcement')
    
    # Build email
    email = FeatureAnnouncementEmail(
        user_name=first_name,
        features=features
    )
    
    subject, html = email.build()
    
    # Send email
    result = send_email(to_email, subject, html)
    
    # Log to email tracking if email was sent successfully
    if result and 'error' not in result:
        resend_email_id = result.get('id')
        log_email_sent(
            email_type='feature_announcement',
            recipient_email=to_email,
            recipient_name=full_name or first_name,
            resend_email_id=resend_email_id,
            user_status='active',
            metadata={'features_count': len(features) if features else 2}
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
1. Sign up at {APP_URL}/login?mode=signup
2. Upload one script
3. Reply with what works and what doesn't

You get 30 days free access. No credit card needed.

The ask: 15 minutes of your time to test the AI breakdown and tell us what you think.

Sign up here: {APP_URL}/login?mode=signup

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
                                            <a href="{APP_URL}/login?mode=signup" style="display: inline-block; background-color: #F59E0B; color: #000000; text-decoration: none; padding: 16px 48px; border-radius: 6px; font-weight: 600; font-size: 16px;">
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
    
    result = send_email(to_email, subject, html, text=text)
    
    # Log to email tracking if email was sent successfully
    if result and 'error' not in result:
        resend_email_id = result.get('id')
        log_email_sent(
            email_type='beta_unlock',
            recipient_email=to_email,
            recipient_name=first_name or 'Beta User',
            user_status='early_access',
            resend_email_id=resend_email_id,
            metadata={
                'subject': subject,
                'campaign': 'beta_unlock_reminder'
            }
        )
    
    return result


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


def send_password_reset_email(
    to_email: str,
    reset_url: str,
    full_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send password reset email via Resend (avoids Supabase spam issues).
    
    Args:
        to_email: User's email address
        reset_url: The password reset URL (from Supabase or custom)
        full_name: User's full name (optional)
    """
    first_name = full_name.split(' ')[0] if full_name else 'there'
    
    subject = f"🔐 Reset your {APP_NAME} password"
    
    # Plain text version for better deliverability
    text = f"""Hi {first_name},

You requested to reset your password for SlateOne.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour for security reasons.

If you didn't request this password reset, you can safely ignore this email.

---
SlateOne - Script Breakdown
{APP_URL}

Questions? Reply to this email: hello@slateone.studio
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
                                    Reset your password
                                </h2>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                                    Hi {first_name}, we received a request to reset your password for {APP_NAME}.
                                </p>
                                
                                <div style="background-color: #262626; border-radius: 12px; padding: 24px; margin-bottom: 24px; text-align: center;">
                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #9CA3AF;">
                                        Click the button below to reset your password:
                                    </p>
                                    <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                        🔐 Reset Password
                                    </a>
                                </div>
                                
                                <div style="background-color: rgba(239, 68, 68, 0.1); border: 1px solid #EF4444; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
                                    <p style="margin: 0; font-size: 14px; color: #FCA5A5; line-height: 1.6;">
                                        ⏰ <strong>This link expires in 1 hour</strong> for security reasons.
                                    </p>
                                </div>
                                
                                <p style="margin: 0 0 8px 0; font-size: 14px; color: #6B7280; line-height: 1.6;">
                                    If you didn't request this password reset, you can safely ignore this email. Your password will remain unchanged.
                                </p>
                                
                                <p style="margin: 0; font-size: 12px; color: #6B7280; line-height: 1.6;">
                                    If the button doesn't work, copy and paste this link into your browser:<br>
                                    <span style="color: #9CA3AF; word-break: break-all;">{reset_url}</span>
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
            email_type='password_reset',
            recipient_email=to_email,
            recipient_name=full_name or 'User',
            resend_email_id=resend_email_id,
            user_status='active',
            metadata={'reset_url': reset_url}
        )
    
    return result


def send_feedback_confirmation_email(
    user_email: str,
    user_name: str,
    feedback_id: str,
    category: str,
    subject: str
) -> Dict[str, Any]:
    """
    Send confirmation email after feedback submission.
    
    Args:
        user_email: User's email address
        user_name: User's full name
        feedback_id: Feedback UUID
        category: Feedback category
        subject: Feedback subject
    """
    category_labels = {
        'bug': '🐛 Bug Report',
        'feature': '✨ Feature Request',
        'ui_ux': '🎨 UI/UX Issue',
        'general': '💬 General Feedback'
    }
    
    category_label = category_labels.get(category, 'Feedback')
    email_subject = f"Feedback Received - {category_label}"
    
    tracking_url = f"{APP_URL}/profile/feedback/{feedback_id}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
            .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #f59e0b, #d97706); padding: 40px 30px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 28px; font-weight: 700; }}
            .content {{ padding: 40px 30px; }}
            .feedback-box {{ background: #f9fafb; border-left: 4px solid #f59e0b; padding: 20px; margin: 20px 0; border-radius: 4px; }}
            .feedback-box strong {{ color: #1f2937; display: block; margin-bottom: 8px; }}
            .feedback-box p {{ margin: 0; color: #4b5563; }}
            .button {{ display: inline-block; padding: 14px 28px; background: #f59e0b; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
            .button:hover {{ background: #d97706; }}
            .footer {{ background: #f9fafb; padding: 30px; text-align: center; color: #6b7280; font-size: 14px; border-top: 1px solid #e5e7eb; }}
            .emoji {{ font-size: 48px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="emoji">✅</div>
                <h1>Feedback Received!</h1>
            </div>
            <div class="content">
                <p>Hi {user_name or 'there'},</p>
                <p>Thank you for taking the time to share your feedback with us! We've received your submission and our team will review it shortly.</p>
                
                <div class="feedback-box">
                    <strong>Category:</strong>
                    <p>{category_label}</p>
                    <strong style="margin-top: 12px;">Subject:</strong>
                    <p>{subject}</p>
                </div>
                
                <p>We take all feedback seriously and use it to continuously improve {APP_NAME}. If we need any additional information, we'll reach out to you via email.</p>
                
                <p style="text-align: center;">
                    <a href="{tracking_url}" class="button">Track Your Feedback</a>
                </p>
                
                <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                    <strong>What happens next?</strong><br>
                    • Our team will review your feedback within 48 hours<br>
                    • You'll receive updates if your feedback status changes<br>
                    • We may reach out if we need more details
                </p>
            </div>
            <div class="footer">
                <p>Thanks for helping us improve {APP_NAME}!</p>
                <p style="margin-top: 10px;">
                    <a href="{APP_URL}" style="color: #f59e0b; text-decoration: none;">Visit {APP_NAME}</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Feedback Received - {category_label}
    
    Hi {user_name or 'there'},
    
    Thank you for taking the time to share your feedback with us! We've received your submission and our team will review it shortly.
    
    Category: {category_label}
    Subject: {subject}
    
    We take all feedback seriously and use it to continuously improve {APP_NAME}. If we need any additional information, we'll reach out to you via email.
    
    Track your feedback: {tracking_url}
    
    What happens next?
    • Our team will review your feedback within 48 hours
    • You'll receive updates if your feedback status changes
    • We may reach out if we need more details
    
    Thanks for helping us improve {APP_NAME}!
    
    - The {APP_NAME} Team
    """
    
    result = send_email(
        to=user_email,
        subject=email_subject,
        html=html,
        text=text,
        from_email="hello@slateone.studio"
    )
    
    # Log to email tracking if email was sent successfully
    if result and 'error' not in result:
        resend_email_id = result.get('id')
        log_email_sent(
            email_type='feedback_confirmation',
            recipient_email=user_email,
            recipient_name=user_name or 'User',
            resend_email_id=resend_email_id,
            user_status='active',
            metadata={'feedback_id': feedback_id, 'category': category}
        )
    
    return result


def send_feedback_reply_email(
    user_email: str,
    user_name: str,
    feedback_id: str,
    subject: str,
    category: str,
    reply_message: str
) -> Dict[str, Any]:
    """
    Send email reply to feedback submitter.
    
    Args:
        user_email: User's email address
        user_name: User's full name
        feedback_id: Feedback UUID
        subject: Original feedback subject
        category: Feedback category
        reply_message: Admin's reply message
    """
    category_labels = {
        'bug': '🐛 Bug Report',
        'feature': '✨ Feature Request',
        'ui_ux': '🎨 UI/UX Issue',
        'general': '💬 General Feedback'
    }
    
    category_label = category_labels.get(category, 'Feedback')
    email_subject = f"Re: {subject}"
    
    feedback_url = f"{APP_URL}/profile/feedback/{feedback_id}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
            .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #f59e0b, #d97706); padding: 40px 30px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 28px; font-weight: 700; }}
            .content {{ padding: 40px 30px; }}
            .reply-box {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; margin: 20px 0; border-radius: 4px; }}
            .reply-box p {{ margin: 0; color: #1f2937; white-space: pre-wrap; }}
            .original-box {{ background: #f9fafb; border-left: 4px solid #9ca3af; padding: 20px; margin: 20px 0; border-radius: 4px; }}
            .original-box strong {{ color: #1f2937; display: block; margin-bottom: 8px; }}
            .original-box p {{ margin: 0; color: #6b7280; }}
            .button {{ display: inline-block; padding: 14px 28px; background: #f59e0b; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
            .button:hover {{ background: #d97706; }}
            .footer {{ background: #f9fafb; padding: 30px; text-align: center; color: #6b7280; font-size: 14px; border-top: 1px solid #e5e7eb; }}
            .emoji {{ font-size: 48px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="emoji">💬</div>
                <h1>Response to Your Feedback</h1>
            </div>
            <div class="content">
                <p>Hi {user_name or 'there'},</p>
                <p>We've reviewed your feedback and wanted to respond:</p>
                
                <div class="reply-box">
                    <p>{reply_message}</p>
                </div>
                
                <div class="original-box">
                    <strong>Your Original Feedback:</strong>
                    <p><strong>Category:</strong> {category_label}</p>
                    <p><strong>Subject:</strong> {subject}</p>
                </div>
                
                <p>If you have any follow-up questions or additional information to share, feel free to submit new feedback or reply to this email.</p>
                
                <p style="text-align: center;">
                    <a href="{feedback_url}" class="button">View Feedback Details</a>
                </p>
            </div>
            <div class="footer">
                <p>Thank you for helping us improve {APP_NAME}!</p>
                <p style="margin-top: 10px;">
                    <a href="{APP_URL}" style="color: #f59e0b; text-decoration: none;">Visit {APP_NAME}</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
    Response to Your Feedback
    
    Hi {user_name or 'there'},
    
    We've reviewed your feedback and wanted to respond:
    
    {reply_message}
    
    Your Original Feedback:
    Category: {category_label}
    Subject: {subject}
    
    If you have any follow-up questions or additional information to share, feel free to submit new feedback or reply to this email.
    
    View feedback details: {feedback_url}
    
    Thank you for helping us improve {APP_NAME}!
    
    - The {APP_NAME} Team
    """
    
    result = send_email(
        to=user_email,
        subject=email_subject,
        html=html,
        text=text,
        from_email="hello@slateone.studio",
        reply_to="hello@slateone.studio"
    )
    
    # Log to email tracking if email was sent successfully
    if result and 'error' not in result:
        resend_email_id = result.get('id')
        log_email_sent(
            email_type='feedback_reply',
            recipient_email=user_email,
            recipient_name=user_name or 'User',
            resend_email_id=resend_email_id,
            user_status='active',
            metadata={'feedback_id': feedback_id, 'category': category}
        )
    
    return result


def send_admin_feedback_alert_email(
    feedback_id: str,
    user_name: str,
    user_email: str,
    category: str,
    priority: str,
    subject: str,
    description: str,
    admin_emails: list
) -> Dict[str, Any]:
    """
    Send alert email to admins about new feedback submission.
    Only sent for high-priority or bug feedback.
    
    Args:
        feedback_id: Feedback UUID
        user_name: Name of user who submitted feedback
        user_email: Email of user who submitted feedback
        category: Feedback category (bug, feature, ui_ux, general)
        priority: Feedback priority (low, medium, high)
        subject: Feedback subject
        description: Feedback description
        admin_emails: List of admin email addresses
    
    Returns:
        dict: Resend API response
    """
    # Category emoji mapping
    category_emoji = {
        'bug': '🐛',
        'feature': '✨',
        'ui_ux': '🎨',
        'general': '💬'
    }
    
    # Priority badge color
    priority_color = {
        'low': '#10b981',
        'medium': '#f59e0b',
        'high': '#ef4444'
    }
    
    emoji = category_emoji.get(category, '💬')
    badge_color = priority_color.get(priority, '#f59e0b')
    
    # HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>New Feedback Alert</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a; color: #f8fafc;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0f172a; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 15px rgba(0, 0, 0, 0.5);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 30px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">
                                    {emoji} New Feedback Alert
                                </h1>
                            </td>
                        </tr>
                        
                        <!-- Priority Badge -->
                        <tr>
                            <td style="padding: 20px 30px 10px;">
                                <div style="display: inline-block; background-color: {badge_color}; color: #ffffff; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                                    {priority} Priority
                                </div>
                                <div style="display: inline-block; background-color: #334155; color: #cbd5e1; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; text-transform: uppercase; margin-left: 8px;">
                                    {category.replace('_', '/')}
                                </div>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 20px 30px;">
                                <h2 style="margin: 0 0 10px 0; color: #f8fafc; font-size: 18px; font-weight: 600;">
                                    {subject}
                                </h2>
                                <p style="margin: 0 0 20px 0; color: #cbd5e1; font-size: 14px; line-height: 1.6;">
                                    {description[:300]}{'...' if len(description) > 300 else ''}
                                </p>
                                
                                <div style="background-color: #334155; border-radius: 8px; padding: 15px; margin: 20px 0;">
                                    <p style="margin: 0 0 5px 0; color: #94a3b8; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                                        Submitted by
                                    </p>
                                    <p style="margin: 0; color: #f8fafc; font-size: 14px;">
                                        {user_name or 'User'} ({user_email})
                                    </p>
                                </div>
                            </td>
                        </tr>
                        
                        <!-- CTA Button -->
                        <tr>
                            <td style="padding: 10px 30px 30px;">
                                <a href="https://app.slateone.studio/admin/feedback/{feedback_id}" 
                                   style="display: inline-block; background-color: #f59e0b; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px;">
                                    View in Admin Dashboard →
                                </a>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #0f172a; padding: 20px 30px; text-align: center; border-top: 1px solid #334155;">
                                <p style="margin: 0; color: #64748b; font-size: 12px;">
                                    SlateOne - Script Breakdown & Analysis
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
    
    # Plain text version
    text_content = f"""
    NEW FEEDBACK ALERT
    
    Priority: {priority.upper()}
    Category: {category.replace('_', '/')}
    
    Subject: {subject}
    
    {description}
    
    Submitted by: {user_name or 'User'} ({user_email})
    
    View in Admin Dashboard:
    https://app.slateone.studio/admin/feedback/{feedback_id}
    
    ---
    SlateOne - Script Breakdown & Analysis
    """
    
    # Send to all admin emails
    result = send_email(
        to_emails=admin_emails,
        subject=f"{emoji} New {priority.capitalize()} Priority Feedback: {subject[:50]}",
        html_content=html_content,
        text_content=text_content
    )
    
    # Log email sent
    if result and result.get('id'):
        for admin_email in admin_emails:
            log_email_sent(
                email_type='admin_feedback_alert',
                recipient_email=admin_email,
                recipient_name='Admin',
                resend_email_id=result.get('id'),
                user_status='active',
                metadata={'feedback_id': feedback_id, 'category': category, 'priority': priority}
            )
    
    return result
