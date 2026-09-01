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


def send_team_invite(
    to_email: str,
    inviter_name: str,
    script_title: str,
    department: str,
    role: str,
    invite_url: str,
) -> Dict[str, Any]:
    """
    Send an invitation email to a prospective team member.

    Args:
        to_email: Email address of the person being invited
        inviter_name: Name of the person sending the invite
        script_title: Title of the script they're invited to
        department: Department name they're invited as
        role: Role they'll have (admin/member/viewer)
        invite_url: Magic link to accept the invite
    """
    import html as _html

    # HTML-escape every interpolated value to prevent HTML/email injection.
    # inviter_name and script_title are user-controlled (profile name / script title).
    safe_name = _html.escape(inviter_name or 'A teammate')
    safe_title = _html.escape(script_title or 'Untitled')
    safe_dept = _html.escape(department or '')
    safe_role = _html.escape(role or '')

    # Only allow invite links on our own frontend origin (blocks javascript:/data: URIs).
    if not invite_url or not invite_url.startswith(APP_URL):
        print(f"Warning: refusing to send invite email with untrusted URL: {invite_url!r}")
        return {'error': 'Invalid invite URL'}
    safe_url = _html.escape(invite_url, quote=True)

    # Strip newlines from subject inputs to avoid header injection.
    subject = f"🎬 {inviter_name} invited you to collaborate on {script_title}".replace('\r', ' ').replace('\n', ' ')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{_html.escape(subject)}</title>
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
                                <h2 style="margin: 0 0 24px 0; font-size: 28px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
                                    You've been invited to collaborate
                                </h2>

                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #D1D5DB; line-height: 1.5;">
                                    <strong>{safe_name}</strong> has invited you to join their production team on {APP_NAME}.
                                </p>

                                <div style="background-color: #262626; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td style="padding-bottom: 16px;">
                                                <span style="font-size: 12px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.5px;">Script</span>
                                                <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: 600; color: #FFFFFF;">{safe_title}</p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding-bottom: 16px;">
                                                <span style="font-size: 12px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.5px;">Department</span>
                                                <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: 600; color: #F59E0B;">{safe_dept}</p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td>
                                                <span style="font-size: 12px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.5px;">Role</span>
                                                <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: 600; color: #FFFFFF; text-transform: capitalize;">{safe_role}</p>
                                            </td>
                                        </tr>
                                    </table>
                                </div>

                                <a href="{safe_url}" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    Accept Invite →
                                </a>

                                <p style="margin: 24px 0 0 0; font-size: 13px; color: #6B7280; line-height: 1.5;">
                                    This invite expires in 7 days. If the button doesn't work, copy and paste this link into your browser:<br>
                                    <a href="{safe_url}" style="color: #F59E0B; word-break: break-all;">{safe_url}</a>
                                </p>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #2A2A2A; text-align: center;">
                                <p style="margin: 0; font-size: 12px; color: #6B7280;">
                                    You received this email because {safe_name} invited you to collaborate on {APP_NAME}.
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
        from_email="hello@slateone.studio",
        reply_to="hello@slateone.studio",
    )

    if result and 'error' not in result:
        log_email_sent(
            email_type='team_invite',
            recipient_email=to_email,
            recipient_name=to_email.split('@')[0],
            resend_email_id=result.get('id'),
            user_status='invited',
            metadata={'script_title': script_title, 'department': department, 'role': role},
        )

    return result


def _production_member_email(
    to_email: str,
    inviter_name: str,
    production_title: str,
    role: str,
    link_url: str,
    verb: str,
    cta_label: str,
) -> Dict[str, Any]:
    """Shared renderer for production member-added / invite emails.

    Modeled on ``send_team_invite``: HTML-escape every interpolated value,
    restrict the link to our own frontend origin, strip CR/LF from the subject.
    """
    import html as _html

    safe_name = _html.escape(inviter_name or 'A teammate')
    safe_title = _html.escape(production_title or 'Untitled')
    safe_role = _html.escape(role or '')

    if not link_url or not link_url.startswith(APP_URL):
        print(f"Warning: refusing to send production email with untrusted URL: {link_url!r}")
        return {'error': 'Invalid production URL'}
    safe_url = _html.escape(link_url, quote=True)

    subject = f"🎬 {inviter_name} {verb} {production_title}".replace('\r', ' ').replace('\n', ' ')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{_html.escape(subject)}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0F0F0F; color: #FFFFFF;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0F0F0F; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1A1A1A; border-radius: 16px; overflow: hidden; border: 1px solid #2A2A2A;">
                        <tr>
                            <td style="background: linear-gradient(135deg, #F59E0B, #D97706); padding: 32px; text-align: center;">
                                <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #000000;">🎬 {APP_NAME}</h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px 32px;">
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #D1D5DB; line-height: 1.5;">
                                    <strong>{safe_name}</strong> {_html.escape(verb)} <strong>{safe_title}</strong> as {safe_role}.
                                </p>
                                <a href="{safe_url}" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    {_html.escape(cta_label)} →
                                </a>
                                <p style="margin: 24px 0 0 0; font-size: 13px; color: #6B7280; line-height: 1.5;">
                                    If the button doesn't work, copy and paste this link into your browser:<br>
                                    <a href="{safe_url}" style="color: #F59E0B; word-break: break-all;">{safe_url}</a>
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

    return send_email(
        to=to_email,
        subject=subject,
        html=html,
        from_email="hello@slateone.studio",
        reply_to="hello@slateone.studio",
    )


def send_production_member_added(
    to_email: str,
    inviter_name: str,
    production_title: str,
    role: str,
    production_url: str,
) -> Dict[str, Any]:
    """Notify an existing account that they were added to a production."""
    return _production_member_email(
        to_email, inviter_name, production_title, role, production_url,
        verb="added you to", cta_label="Open the production")


def send_production_invite(
    to_email: str,
    inviter_name: str,
    production_title: str,
    role: str,
    invite_url: str,
) -> Dict[str, Any]:
    """Invite a not-yet-registered email to collaborate on a production."""
    return _production_member_email(
        to_email, inviter_name, production_title, role, invite_url,
        verb="invited you to collaborate on", cta_label="Accept invite")


def _render_notice_email(subject: str, heading: str, body_html: str, footer_note: str) -> str:
    """
    Render a simple branded notice email (no call-to-action button).

    Caller is responsible for HTML-escaping any user-controlled values before
    passing them in `heading`, `body_html`, or `footer_note`.
    """
    import html as _html
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{_html.escape(subject)}</title>
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
                                <h2 style="margin: 0 0 24px 0; font-size: 26px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
                                    {heading}
                                </h2>
                                {body_html}
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #2A2A2A; text-align: center;">
                                <p style="margin: 0; font-size: 12px; color: #6B7280;">
                                    {footer_note}
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


def send_member_removed(
    to_email: str,
    member_name: str,
    script_title: str,
    remover_name: str,
) -> Dict[str, Any]:
    """
    Notify a team member that they've been removed from a script's team.

    Args:
        to_email: Email of the removed member
        member_name: Display name of the removed member
        script_title: Title of the script they were removed from
        remover_name: Name of the owner who removed them
    """
    import html as _html

    safe_member = _html.escape(member_name or 'there')
    safe_title = _html.escape(script_title or 'Untitled')
    safe_remover = _html.escape(remover_name or 'The script owner')

    subject = f"Your access to \"{script_title}\" was removed".replace('\r', ' ').replace('\n', ' ')

    body_html = f"""
        <p style="margin: 0 0 16px 0; font-size: 16px; color: #D1D5DB; line-height: 1.6;">
            Hi {safe_member},
        </p>
        <p style="margin: 0 0 16px 0; font-size: 16px; color: #D1D5DB; line-height: 1.6;">
            {safe_remover} has removed you from the production team for
            <strong style="color: #FFFFFF;">{safe_title}</strong> on {APP_NAME}.
            You no longer have access to this script.
        </p>
        <p style="margin: 0; font-size: 14px; color: #9CA3AF; line-height: 1.6;">
            Any notes and contributions you made remain with the production.
            If you think this was a mistake, reach out to the script owner.
        </p>
    """

    html = _render_notice_email(
        subject=subject,
        heading="You've been removed from a team",
        body_html=body_html,
        footer_note=f"You received this email because your access to a {APP_NAME} script changed.",
    )

    result = send_email(
        to=to_email,
        subject=subject,
        html=html,
        from_email="hello@slateone.studio",
        reply_to="hello@slateone.studio",
    )

    if result and 'error' not in result:
        log_email_sent(
            email_type='member_removed',
            recipient_email=to_email,
            recipient_name=member_name or to_email.split('@')[0],
            resend_email_id=result.get('id'),
            user_status='removed',
            metadata={'script_title': script_title},
        )

    return result


def send_invite_revoked(
    to_email: str,
    script_title: str,
    inviter_name: str,
) -> Dict[str, Any]:
    """
    Notify a pending invitee that their invitation was withdrawn.

    Args:
        to_email: Email the invite was sent to
        script_title: Title of the script they were invited to
        inviter_name: Name of the person who withdrew the invite
    """
    import html as _html

    safe_title = _html.escape(script_title or 'Untitled')
    safe_inviter = _html.escape(inviter_name or 'The script owner')

    subject = f"Your invitation to \"{script_title}\" was withdrawn".replace('\r', ' ').replace('\n', ' ')

    body_html = f"""
        <p style="margin: 0 0 16px 0; font-size: 16px; color: #D1D5DB; line-height: 1.6;">
            {safe_inviter} has withdrawn your invitation to join the production team for
            <strong style="color: #FFFFFF;">{safe_title}</strong> on {APP_NAME}.
        </p>
        <p style="margin: 0; font-size: 14px; color: #9CA3AF; line-height: 1.6;">
            The invite link that was sent to you is no longer active.
            If you think this was a mistake, reach out to the person who invited you.
        </p>
    """

    html = _render_notice_email(
        subject=subject,
        heading="Your invitation was withdrawn",
        body_html=body_html,
        footer_note=f"You received this email because you were invited to collaborate on {APP_NAME}.",
    )

    result = send_email(
        to=to_email,
        subject=subject,
        html=html,
        from_email="hello@slateone.studio",
        reply_to="hello@slateone.studio",
    )

    if result and 'error' not in result:
        log_email_sent(
            email_type='invite_revoked',
            recipient_email=to_email,
            recipient_name=to_email.split('@')[0],
            resend_email_id=result.get('id'),
            user_status='invited',
            metadata={'script_title': script_title},
        )

    return result


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


SIGNUP_PLAN_COPY = {
    'tier_1_pay_per_breakdown': ('UNLOCK YOUR BREAKDOWN', 'Pay-per-breakdown — no subscription, no seats.'),
    'tier_2_annual_team': ('UNLOCK YOUR TEAM LICENSE', 'Annual or monthly team license — unlimited breakdowns, invite your crew.'),
}


def send_welcome_email(
    to_email: str,
    full_name: str,
    has_paid: bool = False,
    signup_plan: str | None = None
) -> Dict[str, Any]:
    """
    Send welcome email to new users after signup.

    Args:
        to_email: User's email address
        full_name: User's full name
        has_paid: Whether user has already paid for beta access (legacy path)
        signup_plan: The plan the user selected at signup (tier_1_pay_per_breakdown
            or tier_2_annual_team), used to tailor the pricing CTA. Pricing itself
            is never hardcoded here — it always links to /billing, the single
            live source of truth, so this copy can't go stale the way the old
            hardcoded "$49/month" Wise link did.
    """
    first_name = full_name.split(' ')[0] if full_name else 'there'

    if has_paid:
        # User has already paid - welcome them to full access
        subject = f"🎬 Welcome to {APP_NAME}, {first_name}!"
        cta_section = f"""
                                <div style="background: linear-gradient(135deg, #10B981, #059669); border-radius: 12px; padding: 24px; margin-bottom: 24px; text-align: center;">
                                    <p style="margin: 0 0 8px 0; font-size: 14px; color: rgba(255,255,255,0.8);">✅ SUBSCRIPTION ACTIVE</p>
                                    <p style="margin: 0; font-size: 18px; font-weight: 600; color: #FFFFFF;">You have full access to {APP_NAME}!</p>
                                </div>
                                
                                <a href="{APP_URL}/scripts" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    Start Using {APP_NAME} →
                                </a>
        """
    else:
        # User verified email but hasn't paid yet
        subject = f"🎬 You're in, {first_name}! Start using {APP_NAME}"
        plan_label, plan_description = SIGNUP_PLAN_COPY.get(
            signup_plan, ('UNLOCK FULL ACCESS', 'Pick the plan that fits — pay-per-breakdown or a team license.')
        )
        cta_section = f"""
                                <div style="background: linear-gradient(135deg, #10B981, #059669); border-radius: 12px; padding: 20px; margin-bottom: 24px; text-align: center;">
                                    <p style="margin: 0 0 4px 0; font-size: 14px; color: rgba(255,255,255,0.8);">✅ EMAIL VERIFIED</p>
                                    <p style="margin: 0; font-size: 16px; font-weight: 600; color: #FFFFFF;">Your account is ready to use</p>
                                </div>
                                
                                <!-- Primary CTA: Go to App -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
                                    <tr>
                                        <td align="center">
                                            <a href="{APP_URL}/scripts" style="display: block; width: 100%; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 18px 28px; border-radius: 10px; font-weight: 700; font-size: 18px; text-align: center; box-sizing: border-box;">
                                                Open {APP_NAME} →
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <!-- Plan offer (pricing always lives on /billing — never hardcoded here) -->
                                <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.1)); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 12px; padding: 24px; text-align: center;">
                                    <p style="margin: 0 0 8px 0; font-size: 13px; color: #F59E0B; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">{plan_label}</p>
                                    <p style="margin: 0 0 16px 0; font-size: 15px; color: #D1D5DB;">{plan_description}</p>
                                    <a href="{APP_URL}/billing" style="display: inline-block; background: rgba(245, 158, 11, 0.15); border: 2px solid #F59E0B; color: #F59E0B; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px;">
                                        View Pricing & Plans →
                                    </a>
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
                        <!-- Second CTA: App link + subscribe reminder -->
                        <tr>
                            <td style="padding: 0 32px 32px 32px; text-align: center;">
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 12px;">
                                    <tr>
                                        <td align="center">
                                            <a href="''' + APP_URL + '''/scripts" style="display: block; width: 100%; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 16px 28px; border-radius: 10px; font-weight: 700; font-size: 16px; text-align: center; box-sizing: border-box;">
                                                Go to SlateOne →
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                                <a href="''' + APP_URL + '''/billing" style="font-size: 14px; color: #F59E0B; text-decoration: underline;">
                                    Or view pricing & plans
                                </a>
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

