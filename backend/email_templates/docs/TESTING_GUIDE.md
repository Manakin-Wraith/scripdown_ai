# Email Template Testing Guide

## Overview

This guide covers how to test email templates before deployment to ensure they work correctly across all email clients and scenarios.

## Testing Workflow

```
1. Local Preview → 2. Test Send → 3. Client Testing → 4. A/B Testing → 5. Deploy
```

## 1. Local Preview

### Generate HTML Preview

```python
# scripts/preview_email.py
from email_templates.registry import EmailTemplateRegistry

def preview_template(template_name, **context):
    """Generate HTML preview of a template"""
    
    # Get template
    EmailClass = EmailTemplateRegistry.get(template_name)
    
    # Create instance
    email = EmailClass(**context)
    
    # Build email
    subject, html = email.build()
    
    # Save to file
    filename = f"preview_{template_name}.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Preview saved: {filename}")
    print(f"📧 Subject: {subject}")
    
    return filename

# Example usage
if __name__ == "__main__":
    preview_template(
        'feedback_request',
        user_name='Test User',
        email='test@example.com',
        script_title='Test Script',
        scripts_uploaded=1,
        scenes_analyzed=50,
        total_scenes=100,
        analysis_success_rate=50,
        stripboard_used=False,
        has_incomplete_profile=True
    )
```

### Open in Browser

```bash
# Generate and open
python scripts/preview_email.py
open preview_feedback_request.html
```

## 2. Test Send

### Send to Test Email

```python
# scripts/test_send_email.py
from email_templates.registry import EmailTemplateRegistry
from services.email_service import send_email

def test_send(template_name, to_email, **context):
    """Send test email"""
    
    # Get template
    EmailClass = EmailTemplateRegistry.get(template_name)
    email = EmailClass(**context)
    
    # Build
    subject, html = email.build()
    
    # Add [TEST] prefix
    subject = f"[TEST] {subject}"
    
    # Send
    result = send_email(
        to=to_email,
        subject=subject,
        html=html
    )
    
    print(f"✅ Test email sent to {to_email}")
    print(f"📧 Subject: {subject}")
    print(f"🆔 Resend ID: {result.get('id')}")
    
    return result

# Example usage
if __name__ == "__main__":
    test_send(
        'feedback_request',
        to_email='your-test-email@example.com',
        user_name='Test User',
        # ... other context
    )
```

### Test Email Checklist

Send test emails to:
- [ ] Gmail (personal)
- [ ] Gmail (workspace)
- [ ] Outlook.com
- [ ] Apple Mail
- [ ] Your company email

## 3. Email Client Testing

### Desktop Clients

**Gmail (Web)**
- Open in Chrome, Firefox, Safari
- Check light and dark mode
- Verify links work
- Test reply functionality

**Outlook (Web)**
- Check rendering
- Verify gradients (may not work)
- Test on Windows Outlook if available

**Apple Mail (macOS)**
- Check rendering
- Verify dark mode
- Test on iOS if available

### Mobile Clients

**iOS**
- Gmail app
- Apple Mail app
- Outlook app

**Android**
- Gmail app
- Outlook app
- Samsung Email

### Testing Checklist

For each client, verify:
- [ ] Header renders correctly
- [ ] Logo/branding visible
- [ ] Body text readable
- [ ] Links clickable
- [ ] Buttons/CTAs prominent
- [ ] Images load (if any)
- [ ] Footer visible
- [ ] Emojis render correctly
- [ ] Spacing looks good
- [ ] No horizontal scroll
- [ ] Dark mode compatible

## 4. Automated Testing

### Email Testing Services

**Litmus** (Recommended)
```bash
# Send to Litmus test address
python scripts/test_send_email.py \
  --template feedback_request \
  --to your-test-id@litmus.com
```

**Email on Acid**
```bash
# Similar to Litmus
python scripts/test_send_email.py \
  --template feedback_request \
  --to your-test-id@emailonacid.com
```

### Screenshot Testing

```python
# scripts/screenshot_test.py
import subprocess

def screenshot_email(html_file):
    """Generate screenshot of email"""
    
    # Use headless browser
    subprocess.run([
        'npx', 'playwright', 'screenshot',
        html_file,
        f"{html_file}.png"
    ])
    
    print(f"✅ Screenshot saved: {html_file}.png")
```

## 5. Content Testing

### Spam Score Testing

**Mail Tester**
1. Generate test email
2. Send to provided address
3. Check score (aim for 10/10)
4. Fix any issues

**Common Issues:**
- Missing unsubscribe link
- Too many images
- Suspicious keywords
- No plain text version
- Invalid HTML

### Link Testing

```python
# scripts/test_links.py
import re
from urllib.parse import urlparse

def test_links(html):
    """Extract and validate all links"""
    
    # Find all links
    links = re.findall(r'href="([^"]+)"', html)
    
    print(f"Found {len(links)} links:\n")
    
    for link in links:
        parsed = urlparse(link)
        
        # Check if absolute URL
        if not parsed.scheme:
            print(f"⚠️  Relative URL: {link}")
        else:
            print(f"✅ {link}")
    
    return links
```

### Personalization Testing

Test with various user data:

```python
test_cases = [
    # Normal case
    {'user_name': 'John Doe', 'email': 'john@example.com'},
    
    # No name
    {'user_name': '', 'email': 'test@example.com'},
    
    # Long name
    {'user_name': 'Christopher Alexander Montgomery', 'email': 'long@example.com'},
    
    # Special characters
    {'user_name': "O'Brien", 'email': 'obrien@example.com'},
    
    # Unicode
    {'user_name': 'José García', 'email': 'jose@example.com'},
]

for case in test_cases:
    preview_template('feedback_request', **case)
```

## 6. Performance Testing

### File Size

```python
# scripts/check_email_size.py
import os

def check_email_size(html):
    """Check email file size"""
    
    size_bytes = len(html.encode('utf-8'))
    size_kb = size_bytes / 1024
    
    print(f"Email size: {size_kb:.2f} KB")
    
    if size_kb > 100:
        print("⚠️  Warning: Email larger than 100KB")
    elif size_kb > 50:
        print("✅ Good: Email under 100KB")
    else:
        print("✅ Excellent: Email under 50KB")
    
    return size_kb
```

### Load Time

```python
# scripts/test_load_time.py
import time
from selenium import webdriver

def test_load_time(html_file):
    """Test email load time in browser"""
    
    driver = webdriver.Chrome()
    
    start = time.time()
    driver.get(f"file://{html_file}")
    load_time = time.time() - start
    
    print(f"Load time: {load_time:.2f}s")
    
    driver.quit()
    
    return load_time
```

## 7. A/B Testing

### Subject Line Testing

```python
# Test different subject lines
subjects = [
    "🎬 {name}, quick question about your SlateOne experience",
    "Quick question about your SlateOne experience, {name}",
    "How's SlateOne working for you, {name}?",
]

# Send to different segments
for i, subject in enumerate(subjects):
    segment = get_test_segment(i)
    send_to_segment(segment, subject, html)
```

### Content Testing

Test variations:
- CTA placement (top vs bottom)
- CTA wording ("Reply now" vs "Share feedback")
- Tone (formal vs casual)
- Length (short vs detailed)

### Metrics to Track

- **Open rate**: Subject line effectiveness
- **Click rate**: CTA effectiveness
- **Reply rate**: Engagement level
- **Unsubscribe rate**: Content relevance

## 8. Regression Testing

### Template Snapshot Testing

```python
# scripts/snapshot_test.py
import hashlib

def create_snapshot(template_name, context):
    """Create snapshot of template output"""
    
    EmailClass = EmailTemplateRegistry.get(template_name)
    email = EmailClass(**context)
    subject, html = email.build()
    
    # Create hash
    content_hash = hashlib.md5(html.encode()).hexdigest()
    
    # Save snapshot
    snapshot_file = f"snapshots/{template_name}_{content_hash}.html"
    with open(snapshot_file, 'w') as f:
        f.write(html)
    
    return content_hash

def compare_snapshot(template_name, context, expected_hash):
    """Compare current output with snapshot"""
    
    current_hash = create_snapshot(template_name, context)
    
    if current_hash == expected_hash:
        print("✅ Snapshot matches")
    else:
        print("⚠️  Snapshot changed - review changes")
    
    return current_hash == expected_hash
```

## 9. Accessibility Testing

### Color Contrast

```python
# scripts/test_contrast.py
from wcag_contrast_ratio import rgb, passes_AA

def test_contrast():
    """Test color contrast ratios"""
    
    tests = [
        ('text_primary', '#FFFFFF', 'background', '#1A1A1A'),
        ('text_secondary', '#E5E7EB', 'background', '#1A1A1A'),
        ('text_muted', '#9CA3AF', 'background', '#1A1A1A'),
    ]
    
    for name1, color1, name2, color2 in tests:
        ratio = rgb(color1, color2)
        passes = passes_AA(ratio)
        
        print(f"{name1} on {name2}: {ratio:.1f}:1 {'✅' if passes else '❌'}")
```

### Screen Reader Testing

Test with:
- VoiceOver (macOS/iOS)
- NVDA (Windows)
- JAWS (Windows)

## 10. Production Checklist

Before deploying to production:

### Code Quality
- [ ] No hardcoded values
- [ ] Design tokens used
- [ ] Components reused
- [ ] Code reviewed
- [ ] Documentation updated

### Testing
- [ ] Local preview checked
- [ ] Test email sent
- [ ] 3+ email clients tested
- [ ] Mobile tested
- [ ] Dark mode tested
- [ ] Links verified
- [ ] Spam score checked

### Content
- [ ] Copy proofread
- [ ] Personalization tested
- [ ] Emojis rendering
- [ ] CTAs clear
- [ ] Unsubscribe link present

### Performance
- [ ] File size < 100KB
- [ ] Load time < 3s
- [ ] Images optimized
- [ ] No external dependencies

### Compliance
- [ ] CAN-SPAM compliant
- [ ] GDPR compliant (if EU)
- [ ] Unsubscribe link working
- [ ] Physical address included (if required)

## Troubleshooting

### Common Issues

**Emojis not rendering**
- Use Unicode characters, not images
- Wrap in `<span>` with explicit font-size
- Test in target email clients

**Layout broken in Outlook**
- Use table-based layouts
- Avoid flexbox/grid
- Use inline CSS only

**Links not working**
- Use absolute URLs
- Test in incognito/private mode
- Check URL encoding

**Images not loading**
- Use absolute URLs
- Check image permissions
- Provide alt text

**Spam folder**
- Check spam score
- Add unsubscribe link
- Avoid spam trigger words
- Use authenticated domain

## Resources

### Tools
- **Litmus**: litmus.com
- **Email on Acid**: emailonacid.com
- **Mail Tester**: mail-tester.com
- **Can I Email**: caniemail.com

### Documentation
- **Campaign Monitor CSS**: campaignmonitor.com/css
- **Email Client Market Share**: emailclientmarketshare.com
- **WCAG Guidelines**: w3.org/WAI/WCAG21/quickref

### Scripts Location
All testing scripts are in: `backend/scripts/email_testing/`
