"""
Email Service using Resend
Handles sending transactional emails for team invites and notifications.
"""

import os
import resend
from typing import Optional, Dict, Any

# Initialize Resend with API key
resend.api_key = os.getenv('RESEND_API_KEY')

# Default from email
DEFAULT_FROM_EMAIL = os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')

# App name for email templates
APP_NAME = "SlateOne"
APP_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')


def is_configured() -> bool:
    """Check if email service is properly configured."""
    return bool(resend.api_key)


def send_email(
    to: str,
    subject: str,
    html: str,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send an email using Resend.
    
    Args:
        to: Recipient email address
        subject: Email subject
        html: HTML content of the email
        from_email: Sender email (defaults to RESEND_FROM_EMAIL)
        reply_to: Reply-to email address
    
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
