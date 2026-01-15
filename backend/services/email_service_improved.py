"""
Improved email templates with better deliverability.
Use these to replace the current templates if spam issues persist.
"""

def send_early_access_reminder_improved(
    to_email: str,
    first_name: Optional[str] = None,
    unsubscribe_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Improved version with better deliverability:
    - Less emojis in subject
    - Plain text version included
    - Unsubscribe link
    - Physical address
    - Better text-to-HTML ratio
    """
    name = first_name if first_name else 'there'
    
    # IMPROVED: Fewer emojis, more professional
    subject = f"{name}, your SlateOne early access is ready"
    
    # Plain text version (improves deliverability)
    plain_text = f"""
Hi {name},

Remember that early access invite we sent you? SlateOne is live and working - and we need your creative genius to help us make it even better.

YOUR MISSION:
Upload a script. Break it down. Tell us what you think.

WHY WE NEED YOU:
- You're a real filmmaker working on real projects
- Your feedback shapes what we build next
- You get 30 days free to test everything

Takes 2 minutes to sign up. Upload your next script. See the AI breakdown magic happen. Then let us know what works and what doesn't.

Get started: {APP_URL}/login

WHAT'S WAITING FOR YOU:
✓ AI-powered scene breakdowns in minutes
✓ Character tracking across your entire script
✓ Location reports that actually make sense
✓ 30 days free - no credit card, no catch

EARLY ACCESS WINDOW:
This invite won't last forever. We're keeping our early access group small so we can give you real attention and build what you actually need.

Ready to help us build something great?
Sign up with {to_email} to activate your early access.

---
SlateOne - AI-Powered Script Breakdown
[Your Company Address]
Cape Town, South Africa

Questions? Reply to this email or reach out at hello@slateone.studio
Unsubscribe: {APP_URL}/unsubscribe?token={unsubscribe_token or 'TOKEN'}
"""
    
    # HTML version (same content, styled)
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
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 32px;">
                                <h2 style="margin: 0 0 16px 0; font-size: 24px; font-weight: 700; color: #111827; line-height: 1.3;">
                                    Hi {name}, SlateOne is ready for testing
                                </h2>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #4B5563; line-height: 1.6;">
                                    Remember that early access invite we sent you? SlateOne is <strong>live and working</strong> - and we need your creative genius to help us make it even better.
                                </p>
                                
                                <div style="background-color: #FEF3C7; border-left: 4px solid #F59E0B; border-radius: 4px; padding: 20px; margin-bottom: 24px;">
                                    <p style="margin: 0 0 8px 0; font-size: 14px; color: #92400E; font-weight: 600; text-transform: uppercase;">Your Mission</p>
                                    <p style="margin: 0; font-size: 16px; color: #78350F; font-weight: 600;">
                                        Upload a script. Break it down. Tell us what you think.
                                    </p>
                                </div>
                                
                                <p style="margin: 0 0 12px 0; font-size: 16px; color: #111827; font-weight: 600;">
                                    Why we need you:
                                </p>
                                
                                <ul style="margin: 0 0 24px 0; padding-left: 20px; color: #4B5563; line-height: 1.8;">
                                    <li style="margin-bottom: 8px;">You're a real filmmaker working on real projects</li>
                                    <li style="margin-bottom: 8px;">Your feedback shapes what we build next</li>
                                    <li style="margin-bottom: 8px;">You get 30 days free to test everything</li>
                                </ul>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #4B5563; line-height: 1.6;">
                                    Takes 2 minutes to sign up. Upload your next script. See the AI breakdown magic happen. Then let us know what works and what doesn't.
                                </p>
                                
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center">
                                            <a href="{APP_URL}/login" style="display: inline-block; background-color: #F59E0B; color: #000000; text-decoration: none; padding: 16px 32px; border-radius: 6px; font-weight: 600; font-size: 16px;">
                                                Get Started →
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- What You Get -->
                        <tr>
                            <td style="padding: 0 32px 32px 32px;">
                                <div style="background-color: #F3F4F6; border-radius: 6px; padding: 24px;">
                                    <p style="margin: 0 0 16px 0; font-size: 14px; color: #374151; font-weight: 600; text-transform: uppercase;">What's Waiting For You</p>
                                    
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td style="padding-bottom: 12px;">
                                                <p style="margin: 0; font-size: 15px; color: #111827;">
                                                    ✓ AI-powered scene breakdowns in minutes
                                                </p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding-bottom: 12px;">
                                                <p style="margin: 0; font-size: 15px; color: #111827;">
                                                    ✓ Character tracking across your entire script
                                                </p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding-bottom: 12px;">
                                                <p style="margin: 0; font-size: 15px; color: #111827;">
                                                    ✓ Location reports that actually make sense
                                                </p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td>
                                                <p style="margin: 0; font-size: 15px; color: #111827;">
                                                    ✓ 30 days free - no credit card, no catch
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                            </td>
                        </tr>
                        
                        <!-- Urgency Note -->
                        <tr>
                            <td style="padding: 0 32px 32px 32px;">
                                <div style="background-color: #FEF3C7; border-radius: 6px; padding: 20px; text-align: center;">
                                    <p style="margin: 0 0 8px 0; font-size: 14px; color: #92400E; font-weight: 600;">Early Access Window</p>
                                    <p style="margin: 0; font-size: 14px; color: #78350F; line-height: 1.6;">
                                        This invite won't last forever. We're keeping our early access group small so we can give you real attention and build what you actually need.
                                    </p>
                                </div>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #E5E7EB; text-align: center;">
                                <p style="margin: 0 0 8px 0; font-size: 16px; color: #111827; font-weight: 600;">
                                    Ready to help us build something great?
                                </p>
                                <p style="margin: 0 0 16px 0; font-size: 14px; color: #6B7280;">
                                    Sign up with <strong>{to_email}</strong> to activate your early access
                                </p>
                                
                                <!-- Company Info & Unsubscribe -->
                                <p style="margin: 0; font-size: 12px; color: #9CA3AF; line-height: 1.6;">
                                    SlateOne - AI-Powered Script Breakdown<br>
                                    [Your Company Address]<br>
                                    Cape Town, South Africa<br><br>
                                    Questions? Reply to this email or reach out at <a href="mailto:hello@slateone.studio" style="color: #F59E0B; text-decoration: none;">hello@slateone.studio</a><br>
                                    <a href="{APP_URL}/unsubscribe?token={unsubscribe_token or 'TOKEN'}" style="color: #9CA3AF; text-decoration: underline;">Unsubscribe</a>
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
    
    # Send with both plain text and HTML
    return send_email(to_email, subject, html, plain_text=plain_text)
