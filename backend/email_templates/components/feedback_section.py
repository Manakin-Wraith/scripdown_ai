"""
Feedback Section Component

Structured feedback question sections.
"""

from typing import List, Dict


class FeedbackSection:
    """
    Renders a feedback section with questions.
    
    Usage:
        section = FeedbackSection(
            title="About UPLOAD & ANALYZE:",
            questions=[
                "Did everything work smoothly?",
                "Did the AI get your scenes/characters right?",
                "Anything it missed or got wrong?"
            ]
        )
        html = section.render()
    """
    
    def __init__(self, title: str, questions: List[str]):
        """
        Initialize feedback section.
        
        Args:
            title: Section title
            questions: List of question strings
        """
        self.title = title
        self.questions = questions
    
    def render(self) -> str:
        """Render feedback section HTML"""
        
        questions_html = '\n'.join([
            f"""
            <li style="margin: 8px 0; font-size: 14px; color: #D1D5DB; line-height: 1.6;">
                <span style="color: #9CA3AF;">•</span> {q}
            </li>
            """
            for q in self.questions
        ])
        
        return f"""
        <div style="background-color: #1F1F1F; border-radius: 8px; padding: 20px; margin-bottom: 16px;">
            <p style="margin: 0 0 12px 0; font-size: 14px; color: #F59E0B; font-weight: 600;">
                {self.title}
            </p>
            <ul style="margin: 0; padding-left: 20px; list-style: none;">
                {questions_html}
            </ul>
        </div>
        """


class FeedbackSections:
    """
    Renders multiple feedback sections.
    
    Usage:
        sections = FeedbackSections([
            {'title': 'About UPLOAD:', 'questions': [...]},
            {'title': 'About ANALYZE:', 'questions': [...]}
        ])
        html = sections.render()
    """
    
    def __init__(self, sections: List[Dict[str, any]]):
        """
        Initialize feedback sections.
        
        Args:
            sections: List of section dicts with 'title' and 'questions'
        """
        self.sections = sections
    
    def render(self) -> str:
        """Render all feedback sections"""
        
        sections_html = '\n'.join([
            FeedbackSection(s['title'], s['questions']).render()
            for s in self.sections
        ])
        
        return f"""
        <div style="margin: 32px 0;">
            <p style="margin: 0 0 16px 0; font-size: 17px; color: #FFFFFF; font-weight: 600;">
                We'd love your feedback:
            </p>
            {sections_html}
        </div>
        """
