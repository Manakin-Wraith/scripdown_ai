"""
Profile Reminder Component

Reminds users to complete their profile.
"""

import os


class ProfileReminder:
    """
    Renders a profile completion reminder.
    
    Usage:
        reminder = ProfileReminder()
        html = reminder.render()
    """
    
    def __init__(self, app_url: str = None):
        """
        Initialize profile reminder.
        
        Args:
            app_url: Application URL (defaults to env var)
        """
        self.app_url = app_url or os.getenv('FRONTEND_URL', 'https://app.slateone.studio')
    
    def render(self) -> str:
        """Render profile reminder HTML"""
        
        return f"""
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
                                    <a href="{self.app_url}/profile" style="display: inline-block; color: #60A5FA; text-decoration: none; font-size: 14px; font-weight: 500;">
                                        Complete your profile →
                                    </a>
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
        """
