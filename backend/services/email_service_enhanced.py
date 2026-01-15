"""
Enhanced email templates using the 3-decision framework:
1. Open: Clear expectation
2. Read: Point in first 3 lines
3. Act: Single primary action
"""

from typing import Optional, Dict, Any
import os

APP_URL = os.getenv('FRONTEND_URL', 'https://app.slateone.studio')

def send_early_access_reminder_enhanced(
    to_email: str,
    first_name: Optional[str] = None,
    send_email_func = None
) -> Dict[str, Any]:
    """
    Enhanced early access reminder using 3-decision framework.
    
    DECISION 1 (OPEN): Clear expectation in subject
    DECISION 2 (READ): Point stated in first 3 lines
    DECISION 3 (ACT): Single primary action
    """
    name = first_name if first_name else 'there'
    
    # DECISION 1: Clear expectation - reader knows what this email is
    subject = f"SlateOne Early Access: Your testing account is waiting"
    
    # Plain text version
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
    
    # HTML version - optimized for the 3 decisions
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
                            <td style="background-color: #F59E0B; padding: 24px 32px; text-align: center;">
                                <h1 style="margin: 0; font-size: 20px; font-weight: 700; color: #000000;">
                                    SlateOne
                                </h1>
                                <p style="margin: 4px 0 0 0; font-size: 12px; color: #78350F;">Early Access Testing</p>
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
    
    return send_email_func(to_email, subject, html, text=text)


def send_welcome_email_enhanced(
    to_email: str,
    first_name: Optional[str] = None,
    send_email_func = None
) -> Dict[str, Any]:
    """
    Enhanced welcome email using 3-decision framework.
    """
    name = first_name if first_name else 'there'
    
    # DECISION 1: Clear expectation
    subject = f"SlateOne: Your account is ready - upload your first script"
    
    text = f"""Hi {name},

Your SlateOne account is active. Upload your first script to see AI-powered breakdowns.

What happens next:
1. Upload a PDF script
2. AI analyzes it in 2-3 minutes
3. You get scene breakdowns, character tracking, and location reports

Start here: {APP_URL}/upload

Need help? Reply to this email.

---
SlateOne - Script Breakdown
SlateOne.studio
Cape Town, South Africa

Questions? hello@slateone.studio
Unsubscribe: {APP_URL}/unsubscribe
"""
    
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
                        
                        <tr>
                            <td style="background-color: #F59E0B; padding: 24px 32px; text-align: center;">
                                <h1 style="margin: 0; font-size: 20px; font-weight: 700; color: #000000;">SlateOne</h1>
                                <p style="margin: 4px 0 0 0; font-size: 12px; color: #78350F;">Welcome</p>
                            </td>
                        </tr>
                        
                        <tr>
                            <td style="padding: 32px;">
                                <p style="margin: 0 0 16px 0; font-size: 16px; color: #111827;">Hi {name},</p>
                                
                                <p style="margin: 0 0 8px 0; font-size: 18px; color: #111827; font-weight: 600; line-height: 1.4;">
                                    Your SlateOne account is active.
                                </p>
                                
                                <p style="margin: 0 0 24px 0; font-size: 18px; color: #111827; font-weight: 600; line-height: 1.4;">
                                    Upload your first script to see AI-powered breakdowns.
                                </p>
                                
                                <div style="background-color: #F3F4F6; border-radius: 6px; padding: 20px; margin-bottom: 24px;">
                                    <p style="margin: 0 0 12px 0; font-size: 14px; color: #374151; font-weight: 600;">What happens next:</p>
                                    <p style="margin: 0 0 8px 0; font-size: 15px; color: #111827;">1. Upload a PDF script</p>
                                    <p style="margin: 0 0 8px 0; font-size: 15px; color: #111827;">2. AI analyzes it in 2-3 minutes</p>
                                    <p style="margin: 0; font-size: 15px; color: #111827;">3. You get scene breakdowns, character tracking, and location reports</p>
                                </div>
                                
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center">
                                            <a href="{APP_URL}/upload" style="display: inline-block; background-color: #F59E0B; color: #000000; text-decoration: none; padding: 16px 48px; border-radius: 6px; font-weight: 600; font-size: 16px;">
                                                Upload Your First Script
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="margin: 24px 0 0 0; font-size: 14px; color: #6B7280; text-align: center;">
                                    Need help? Reply to this email.
                                </p>
                            </td>
                        </tr>
                        
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #E5E7EB; text-align: center;">
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
    
    return send_email_func(to_email, subject, html, text=text)
