"""
Base Email Template

Provides the foundational HTML structure and design system
for all SlateOne emails.
"""

import os
from typing import Dict, Optional


class BaseEmailTemplate:
    """
    Base class for all email templates.
    Provides consistent structure and design tokens.
    """
    
    # Design tokens
    COLORS = {
        'primary': '#F59E0B',
        'primary_dark': '#D97706',
        'primary_light': '#FCD34D',
        'background': '#0F0F0F',
        'card': '#1A1A1A',
        'card_dark': '#1F1F1F',
        'border': '#2A2A2A',
        'text_primary': '#FFFFFF',
        'text_secondary': '#E5E7EB',
        'text_muted': '#9CA3AF',
        'text_subtle': '#6B7280',
        'success': '#10B981',
        'warning': '#F59E0B',
        'error': '#EF4444',
        'info': '#3B82F6',
    }
    
    SPACING = {
        'xs': '8px',
        'sm': '12px',
        'md': '16px',
        'lg': '24px',
        'xl': '32px',
        'xxl': '40px',
    }
    
    TYPOGRAPHY = {
        'font_family': "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
        'heading_xl': '28px',
        'heading_lg': '24px',
        'heading_md': '20px',
        'heading_sm': '17px',
        'body_lg': '16px',
        'body_md': '15px',
        'body_sm': '14px',
        'body_xs': '13px',
        'caption': '12px',
    }
    
    APP_NAME = "SlateOne"
    APP_URL = os.getenv('FRONTEND_URL', 'https://app.slateone.studio')
    
    def __init__(self, **context):
        """
        Initialize template with context data.
        
        Args:
            **context: Template variables (user_name, email, etc.)
        """
        self.context = context
    
    def render_header(self, subtitle: Optional[str] = None) -> str:
        """Render email header with SlateOne branding"""
        subtitle_html = f'<p style="margin: 8px 0 0 0; font-size: 14px; color: #78350F;">{subtitle}</p>' if subtitle else ''
        
        return f"""
        <tr>
            <td style="background: linear-gradient(135deg, {self.COLORS['primary']}, {self.COLORS['primary_dark']}); padding: 32px; text-align: center;">
                <h1 style="margin: 0; font-size: {self.TYPOGRAPHY['heading_lg']}; font-weight: 700; color: #000000;">
                    🎬 {self.APP_NAME}
                </h1>
                {subtitle_html}
            </td>
        </tr>
        """
    
    def render_footer(self, custom_text: Optional[str] = None) -> str:
        """Render email footer"""
        footer_text = custom_text or "Building the future of script breakdown with filmmakers like you"
        
        return f"""
        <tr>
            <td style="padding: {self.SPACING['lg']} {self.SPACING['xl']}; border-top: 1px solid {self.COLORS['border']}; text-align: center;">
                <p style="margin: 0 0 4px 0; font-size: {self.TYPOGRAPHY['body_sm']}; color: {self.COLORS['text_muted']};">
                    Thanks,
                </p>
                <p style="margin: 0 0 {self.SPACING['sm']} 0; font-size: {self.TYPOGRAPHY['body_sm']}; color: {self.COLORS['text_primary']}; font-weight: 600;">
                    The {self.APP_NAME} Team
                </p>
                <p style="margin: 0; font-size: {self.TYPOGRAPHY['caption']}; color: {self.COLORS['text_subtle']};">
                    {footer_text}
                </p>
            </td>
        </tr>
        """
    
    def render(self, content: str, subject: str) -> str:
        """
        Render complete email HTML.
        
        Args:
            content: Main email content HTML
            subject: Email subject line
            
        Returns:
            Complete HTML email string
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: {self.TYPOGRAPHY['font_family']}; background-color: {self.COLORS['background']}; color: {self.COLORS['text_primary']};">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {self.COLORS['background']}; padding: {self.SPACING['xxl']} {self.SPACING['lg']};">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: {self.COLORS['card']}; border-radius: 16px; overflow: hidden; border: 1px solid {self.COLORS['border']};">
                            {self.render_header()}
                            
                            <tr>
                                <td style="padding: {self.SPACING['xxl']} {self.SPACING['xl']};">
                                    {content}
                                </td>
                            </tr>
                            
                            {self.render_footer()}
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
    
    def get_content(self) -> str:
        """
        Override this method in subclasses to define email content.
        
        Returns:
            HTML content for email body
        """
        raise NotImplementedError("Subclasses must implement get_content()")
    
    def get_subject(self) -> str:
        """
        Override this method in subclasses to define email subject.
        
        Returns:
            Email subject line
        """
        raise NotImplementedError("Subclasses must implement get_subject()")
    
    def build(self) -> tuple[str, str]:
        """
        Build complete email.
        
        Returns:
            Tuple of (subject, html_content)
        """
        subject = self.get_subject()
        content = self.get_content()
        html = self.render(content, subject)
        return (subject, html)
