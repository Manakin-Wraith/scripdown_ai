"""
Journey Box Component

Displays user's progress through the product journey.
"""

from typing import List, Dict


class JourneyBox:
    """
    Renders a user journey status box showing completed/pending steps.
    
    Usage:
        journey = JourneyBox([
            {'icon': '✅', 'label': 'UPLOAD', 'value': '1 script(s)'},
            {'icon': '✅', 'label': 'ANALYZE', 'value': '151/151 scenes (100% success)'},
            {'icon': '⏸️', 'label': 'STRIPBOARD', 'value': 'Not used yet'},
        ])
        html = journey.render()
    """
    
    def __init__(self, items: List[Dict[str, str]]):
        """
        Initialize journey box.
        
        Args:
            items: List of journey items with 'icon', 'label', 'value'
        """
        self.items = items
    
    def render(self) -> str:
        """Render journey box HTML"""
        
        items_html = []
        for i, item in enumerate(self.items):
            border_style = 'border-bottom: 1px solid #333333;' if i < len(self.items) - 1 else ''
            
            items_html.append(f"""
                <tr>
                    <td style="padding: 12px 0; {border_style}">
                        <table width="100%" cellpadding="0" cellspacing="0">
                            <tr>
                                <td width="40" style="vertical-align: top;">
                                    <span style="font-size: 20px;">{item['icon']}</span>
                                </td>
                                <td style="vertical-align: middle;">
                                    <p style="margin: 0; font-size: 15px; color: #E5E7EB; font-weight: 500;">
                                        {item['label']} <span style="color: #9CA3AF;">→</span> {item['value']}
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            """)
        
        return f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #262626; border-radius: 12px; margin: 32px 0; border-left: 4px solid #F59E0B;">
            <tr>
                <td style="padding: 24px;">
                    <p style="margin: 0 0 16px 0; font-size: 13px; color: #F59E0B; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px;">
                        YOUR SLATEONE JOURNEY
                    </p>
                    <table width="100%" cellpadding="0" cellspacing="0">
                        {''.join(items_html)}
                    </table>
                </td>
            </tr>
        </table>
        """
