# SlateOne Email Templates Documentation

## Overview

This directory contains all email templates for the SlateOne platform, organized into a centralized, maintainable system.

## Directory Structure

```
email_templates/
├── __init__.py              # Package initialization
├── base_template.py         # Base template class with design system
├── registry.py              # Central template registry
├── components/              # Reusable email components
│   ├── journey_box.py      # User progress tracker
│   ├── cta_box.py          # Call-to-action boxes
│   ├── profile_reminder.py # Profile completion reminder
│   └── feedback_section.py # Feedback question sections
├── transactional/          # System emails (welcome, password reset, etc.)
├── engagement/             # User engagement emails (feedback, reminders)
├── operational/            # Product notifications (analysis complete, etc.)
└── docs/                   # Documentation
    ├── EMAIL_TEMPLATES.md  # This file
    ├── DESIGN_SYSTEM.md    # Email design guidelines
    └── TESTING_GUIDE.md    # How to test emails
```

## Template Categories

### 1. **Transactional Emails**
System-triggered emails for user actions:
- `welcome` - Welcome email after signup
- `password_reset` - Password reset instructions
- `email_verification` - Email verification link
- `payment_confirmation` - Payment successful notification

### 2. **Engagement Emails**
User engagement and retention:
- `early_access_reminder` - Reminder to try the platform
- `feedback_request` - Request for user feedback
- `feature_announcement` - New feature announcements
- `trial_expiration` - Trial ending reminder

### 3. **Operational Emails**
Product-related notifications:
- `analysis_complete` - Script analysis finished
- `team_invite` - Team member invitation
- `script_shared` - Script shared with you
- `export_ready` - Export file ready for download

## Design System

### Color Palette
```python
COLORS = {
    'primary': '#F59E0B',        # Orange
    'primary_dark': '#D97706',   # Dark orange
    'background': '#0F0F0F',     # Almost black
    'card': '#1A1A1A',           # Dark gray
    'text_primary': '#FFFFFF',   # White
    'text_secondary': '#E5E7EB', # Light gray
    'text_muted': '#9CA3AF',     # Medium gray
    'success': '#10B981',        # Green
    'error': '#EF4444',          # Red
    'info': '#3B82F6',           # Blue
}
```

### Typography
- **Font Family**: System fonts (-apple-system, BlinkMacSystemFont, etc.)
- **Heading XL**: 28px
- **Heading LG**: 24px
- **Body MD**: 15px
- **Body SM**: 14px
- **Caption**: 12px

### Spacing
- **XS**: 8px
- **SM**: 12px
- **MD**: 16px
- **LG**: 24px
- **XL**: 32px
- **XXL**: 40px

## Creating a New Template

### Step 1: Create Template Class

```python
# email_templates/engagement/my_new_email.py

from email_templates.base_template import BaseEmailTemplate
from email_templates.registry import EmailTemplateRegistry
from email_templates.components import JourneyBox, CTABox

@EmailTemplateRegistry.register(
    name='my_new_email',
    category='engagement',
    description='Description of what this email does'
)
class MyNewEmail(BaseEmailTemplate):
    """
    My new email template.
    
    Context variables:
        - user_name: str
        - custom_data: any
    """
    
    def get_subject(self) -> str:
        name = self.context.get('user_name', 'there')
        return f"🎬 {name}, check this out!"
    
    def get_content(self) -> str:
        name = self.context.get('user_name', 'there')
        
        # Use components
        cta = CTABox(
            title="Take action now!",
            subtitle="Click here to continue"
        )
        
        return f"""
        <p style="margin: 0 0 20px 0; font-size: 16px; color: {self.COLORS['text_secondary']};">
            Hi {name},
        </p>
        
        <p style="margin: 0 0 16px 0; font-size: 15px; color: {self.COLORS['text_muted']}; line-height: 1.6;">
            Your email content here...
        </p>
        
        {cta.render()}
        """
```

### Step 2: Use the Template

```python
from email_templates.registry import EmailTemplateRegistry
from services.email_service import send_email

# Get template class
EmailClass = EmailTemplateRegistry.get('my_new_email')

# Create instance with context
email = EmailClass(
    user_name='John Doe',
    custom_data='...'
)

# Build email
subject, html = email.build()

# Send
send_email(to='user@example.com', subject=subject, html=html)
```

## Reusable Components

### JourneyBox
Shows user progress:
```python
from email_templates.components import JourneyBox

journey = JourneyBox([
    {'icon': '✅', 'label': 'UPLOAD', 'value': '1 script(s)'},
    {'icon': '⏸️', 'label': 'ANALYZE', 'value': 'Not started'},
])
html = journey.render()
```

### CTABox
Call-to-action:
```python
from email_templates.components import CTABox

cta = CTABox(
    title="💬 Reply with your thoughts",
    subtitle="We read every response",
    style='primary'  # or 'secondary', 'info'
)
html = cta.render()
```

### ProfileReminder
Profile completion reminder:
```python
from email_templates.components import ProfileReminder

reminder = ProfileReminder()
html = reminder.render()
```

### FeedbackSection
Structured feedback questions:
```python
from email_templates.components import FeedbackSection

section = FeedbackSection(
    title="About the feature:",
    questions=[
        "Did it work as expected?",
        "What could be improved?",
    ]
)
html = section.render()
```

## Testing Templates

### List All Templates
```python
from email_templates.registry import EmailTemplateRegistry

# List all
templates = EmailTemplateRegistry.list_all()
for t in templates:
    print(f"{t['name']} ({t['category']}): {t['description']}")

# List by category
engagement_templates = EmailTemplateRegistry.list_by_category('engagement')
```

### Preview Template
```python
# Create test instance
EmailClass = EmailTemplateRegistry.get('feedback_request')
email = EmailClass(
    user_name='Test User',
    email='test@example.com',
    # ... other context
)

# Build and save to file for preview
subject, html = email.build()
with open('preview.html', 'w') as f:
    f.write(html)
```

## Migration Guide

### Migrating Existing Email Code

**Before:**
```python
def send_welcome_email(to_email, name):
    html = f"""
    <html>
        <body>
            <h1>Welcome {name}!</h1>
            ...
        </body>
    </html>
    """
    send_email(to_email, "Welcome!", html)
```

**After:**
```python
from email_templates.registry import EmailTemplateRegistry

def send_welcome_email(to_email, name):
    EmailClass = EmailTemplateRegistry.get('welcome')
    email = EmailClass(user_name=name)
    subject, html = email.build()
    send_email(to=to_email, subject=subject, html=html)
```

## Best Practices

1. **Always use components** for common UI patterns
2. **Register all templates** in the registry
3. **Document context variables** in docstrings
4. **Test in multiple email clients** (Gmail, Outlook, Apple Mail)
5. **Keep mobile-responsive** (600px max width)
6. **Use design tokens** from BaseEmailTemplate
7. **Version control** template changes
8. **Add descriptions** when registering templates

## Handover Checklist

- [ ] All templates documented in registry
- [ ] Design system tokens defined
- [ ] Components extracted and reusable
- [ ] Testing guide completed
- [ ] Migration path documented
- [ ] Examples provided
- [ ] Email client compatibility tested
- [ ] Monitoring/analytics integrated

## Support

For questions or issues:
1. Check this documentation
2. Review DESIGN_SYSTEM.md for styling guidelines
3. See TESTING_GUIDE.md for testing procedures
4. Contact: dev@slateone.studio
