"""
Feature Announcement Email Template

Announces new features and updates to existing users.
"""

from typing import List, Dict, Optional
from .base_template import BaseEmailTemplate
from .registry import EmailTemplateRegistry


@EmailTemplateRegistry.register(
    'feature_announcement',
    category='engagement',
    description='Announce new features and updates to users'
)
class FeatureAnnouncementEmail(BaseEmailTemplate):
    """
    Email template for announcing new features.
    
    Context variables:
        - user_name: User's first name
        - features: List of dicts with 'icon', 'title', 'description'
    """
    
    def get_subject(self) -> str:
        """Email subject line"""
        return f"🎉 New Features in {self.APP_NAME}!"
    
    def get_content(self) -> str:
        """Generate email content"""
        user_name = self.context.get('user_name', 'there')
        features = self.context.get('features')
        if features is None:
            features = self._get_default_features()
        
        # Build features HTML
        features_html = self._render_features(features)
        
        return f"""
        <h2 style="margin: 0 0 {self.SPACING['md']} 0; font-size: {self.TYPOGRAPHY['heading_xl']}; font-weight: 700; color: {self.COLORS['text_primary']}; line-height: 1.3;">
            Hey {user_name}! 👋
        </h2>
        
        <p style="margin: 0 0 {self.SPACING['xl']} 0; font-size: {self.TYPOGRAPHY['body_lg']}; color: {self.COLORS['text_muted']}; line-height: 1.6;">
            We've been hard at work improving {self.APP_NAME}, and we're excited to share some powerful new features with you!
        </p>
        
        <!-- Features List -->
        {features_html}
        
        <!-- CTA Section -->
        <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.1)); border: 1px solid {self.COLORS['primary']}; border-radius: 12px; padding: {self.SPACING['lg']}; margin: {self.SPACING['xl']} 0; text-align: center;">
            <p style="margin: 0 0 {self.SPACING['md']} 0; font-size: {self.TYPOGRAPHY['body_lg']}; color: {self.COLORS['text_primary']}; font-weight: 600;">
                Try them out now!
            </p>
            <a href="{self.APP_URL}/scripts" style="display: inline-block; background: linear-gradient(135deg, {self.COLORS['primary']}, {self.COLORS['primary_dark']}); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: {self.TYPOGRAPHY['body_lg']};">
                Open {self.APP_NAME} →
            </a>
        </div>
        
        <!-- Feedback Request -->
        <div style="background-color: #1E293B; border-left: 4px solid {self.COLORS['primary']}; border-radius: 8px; padding: {self.SPACING['lg']}; margin-top: {self.SPACING['lg']};">
            <p style="margin: 0 0 {self.SPACING['sm']} 0; font-size: {self.TYPOGRAPHY['body_lg']}; color: {self.COLORS['text_primary']}; font-weight: 600;">
                💬 We'd Love Your Feedback!
            </p>
            <p style="margin: 0; font-size: {self.TYPOGRAPHY['body_sm']}; color: {self.COLORS['text_muted']}; line-height: 1.6;">
                Your input helps us build better tools for filmmakers. Try out these new features and let us know what you think by replying to this email or using the in-app feedback system.
            </p>
        </div>
        
        <p style="margin: {self.SPACING['xl']} 0 0 0; font-size: {self.TYPOGRAPHY['body_lg']}; color: {self.COLORS['text_muted']}; line-height: 1.6; text-align: center;">
            Thanks for being part of the {self.APP_NAME} community!
        </p>
        """
    
    def _render_features(self, features: List[Dict]) -> str:
        """Render feature cards"""
        features_html = ""
        for feature in features:
            icon = feature.get('icon', '✨')
            title = feature.get('title', 'New Feature')
            description = feature.get('description', '')
            
            features_html += f"""
            <div style="padding: {self.SPACING['lg']}; background-color: {self.COLORS['card_dark']}; border-radius: 12px; border-left: 4px solid {self.COLORS['primary']}; margin-bottom: {self.SPACING['sm']};">
                <p style="margin: 0 0 {self.SPACING['xs']} 0; font-size: {self.TYPOGRAPHY['heading_sm']}; font-weight: 600; color: {self.COLORS['text_primary']};">
                    {icon} {title}
                </p>
                <p style="margin: 0; font-size: {self.TYPOGRAPHY['body_sm']}; color: {self.COLORS['text_muted']}; line-height: 1.6;">
                    {description}
                </p>
            </div>
            """
        
        return features_html
    
    def _get_default_features(self) -> List[Dict]:
        """Default features if none provided"""
        return [
            {
                'icon': '💬',
                'title': 'Feedback System',
                'description': 'Share your thoughts and suggestions directly in the app. We read every piece of feedback!'
            },
            {
                'icon': '📊',
                'title': 'Enhanced Reports',
                'description': 'Generate professional production reports with improved layouts and export options.'
            }
        ]
    
    def render_header(self, subtitle: Optional[str] = None) -> str:
        """Override header to add badge"""
        return f"""
        <tr>
            <td style="background: linear-gradient(135deg, {self.COLORS['primary']}, {self.COLORS['primary_dark']}); padding: {self.SPACING['xl']}; text-align: center;">
                <h1 style="margin: 0; font-size: {self.TYPOGRAPHY['heading_lg']}; font-weight: 700; color: #000000;">
                    🎬 {self.APP_NAME}
                </h1>
            </td>
        </tr>
        <tr>
            <td style="background-color: {self.COLORS['success']}; padding: {self.SPACING['sm']}; text-align: center;">
                <p style="margin: 0; font-size: {self.TYPOGRAPHY['body_sm']}; font-weight: 700; color: {self.COLORS['text_primary']}; text-transform: uppercase; letter-spacing: 1px;">
                    ✨ NEW FEATURES JUST DROPPED ✨
                </p>
            </td>
        </tr>
        """
