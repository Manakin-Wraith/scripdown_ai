"""
CTA Box Component

Call-to-action boxes for email engagement.
"""


class CTABox:
    """
    Renders a call-to-action box.
    
    Usage:
        cta = CTABox(
            title="💬 Just hit reply with your thoughts",
            subtitle="Even bullet points help us improve!"
        )
        html = cta.render()
    """
    
    def __init__(self, title: str, subtitle: str = '', style: str = 'primary'):
        """
        Initialize CTA box.
        
        Args:
            title: Main CTA text
            subtitle: Optional subtitle text
            style: 'primary', 'secondary', or 'info'
        """
        self.title = title
        self.subtitle = subtitle
        self.style = style
    
    def render(self) -> str:
        """Render CTA box HTML"""
        
        styles = {
            'primary': {
                'background': 'linear-gradient(135deg, #F59E0B15, #D9770615)',
                'border': '2px solid #F59E0B',
            },
            'secondary': {
                'background': '#262626',
                'border': '1px solid #2A2A2A',
            },
            'info': {
                'background': 'linear-gradient(135deg, #3B82F615, #2563EB15)',
                'border': '2px solid #3B82F6',
            }
        }
        
        style_config = styles.get(self.style, styles['primary'])
        subtitle_html = f'<p style="margin: 0; font-size: 14px; color: #D1D5DB;">{self.subtitle}</p>' if self.subtitle else ''
        
        return f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="background: {style_config['background']}; border: {style_config['border']}; border-radius: 12px; margin: 32px 0;">
            <tr>
                <td style="padding: 24px; text-align: center;">
                    <p style="margin: 0 0 8px 0; font-size: 16px; color: #FFFFFF; font-weight: 600;">
                        {self.title}
                    </p>
                    {subtitle_html}
                </td>
            </tr>
        </table>
        """
