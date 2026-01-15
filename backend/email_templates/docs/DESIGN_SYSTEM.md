# SlateOne Email Design System

## Brand Identity

### Logo & Branding
- **Icon**: 🎬 (Film clapper emoji)
- **Name**: SlateOne
- **Tagline**: AI-Powered Script Breakdown

### Brand Colors
```css
Primary Orange:   #F59E0B (Amber-500)
Primary Dark:     #D97706 (Amber-600)
Primary Light:    #FCD34D (Amber-300)
```

## Color Palette

### Background Colors
```python
'background': '#0F0F0F'      # Main background (almost black)
'card': '#1A1A1A'            # Card background
'card_dark': '#1F1F1F'       # Darker card variant
'border': '#2A2A2A'          # Border color
```

### Text Colors
```python
'text_primary': '#FFFFFF'    # Headings, important text
'text_secondary': '#E5E7EB'  # Body text
'text_muted': '#9CA3AF'      # Secondary info
'text_subtle': '#6B7280'     # Captions, footnotes
```

### Semantic Colors
```python
'success': '#10B981'         # Green - completed, success
'warning': '#F59E0B'         # Orange - warning, attention
'error': '#EF4444'           # Red - error, failed
'info': '#3B82F6'            # Blue - info, reminder
```

## Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
             'Helvetica Neue', Arial, sans-serif;
```

### Font Sizes
```python
'heading_xl': '28px'   # Hero headings
'heading_lg': '24px'   # Email header
'heading_md': '20px'   # Section headings
'heading_sm': '17px'   # Subsection headings
'body_lg': '16px'      # Large body text
'body_md': '15px'      # Standard body text
'body_sm': '14px'      # Small body text
'body_xs': '13px'      # Extra small text
'caption': '12px'      # Captions, footnotes
```

### Font Weights
- **Regular**: 400 (body text)
- **Medium**: 500 (labels, emphasis)
- **Semibold**: 600 (headings, important)
- **Bold**: 700 (hero headings)

## Spacing System

### Scale
```python
'xs': '8px'    # Tight spacing
'sm': '12px'   # Small spacing
'md': '16px'   # Medium spacing
'lg': '24px'   # Large spacing
'xl': '32px'   # Extra large spacing
'xxl': '40px'  # Hero spacing
```

### Usage Guidelines
- **Between paragraphs**: 16px (md)
- **Between sections**: 32px (xl)
- **Card padding**: 24px (lg) to 32px (xl)
- **Button padding**: 14px vertical, 28px horizontal
- **List item spacing**: 8px (xs) to 12px (sm)

## Layout

### Email Container
```css
max-width: 600px
background: #1A1A1A
border-radius: 16px
border: 1px solid #2A2A2A
```

### Content Padding
```css
padding: 40px 32px
```

### Mobile Responsiveness
- Max width: 600px
- Padding reduces to 20px on mobile
- Font sizes remain consistent
- Tables stack on narrow screens

## Components

### Header
```css
background: linear-gradient(135deg, #F59E0B, #D97706)
padding: 32px
text-align: center
color: #000000 (black text on orange)
```

### Footer
```css
padding: 24px 32px
border-top: 1px solid #2A2A2A
text-align: center
color: #9CA3AF (muted text)
```

### Cards
```css
background: #262626 or #1F1F1F
border-radius: 12px
padding: 20px to 24px
border-left: 4px solid [accent-color]
```

### Buttons/Links
```css
Primary Button:
  background: linear-gradient(135deg, #F59E0B, #D97706)
  color: #000000
  padding: 14px 28px
  border-radius: 8px
  font-weight: 600

Text Link:
  color: #60A5FA (light blue)
  text-decoration: none
  font-weight: 500
```

## Icons & Emojis

### Status Icons
- ✅ Complete/Success
- ⏸️ Pending/Paused
- 🔄 In Progress
- ❌ Failed/Error
- ⚠️ Warning

### Feature Icons
- 🎬 SlateOne brand
- 📤 Upload
- 🤖 AI/Analysis
- 📋 Stripboard
- 👤 Profile
- 💬 Feedback
- 📧 Email
- 🎯 Target/Goal

### Emoji Usage
- Use sparingly for emphasis
- Consistent meaning across emails
- Font-size: 18px-24px for visibility
- Always in `<span>` tags for control

## Email Patterns

### Greeting
```html
<p style="margin: 0 0 20px 0; font-size: 16px; color: #E5E7EB;">
    Hi {name},
</p>
```

### Body Paragraph
```html
<p style="margin: 0 0 16px 0; font-size: 15px; color: #D1D5DB; line-height: 1.6;">
    Your content here...
</p>
```

### Section Heading
```html
<p style="margin: 0 0 16px 0; font-size: 17px; color: #FFFFFF; font-weight: 600;">
    Section Title
</p>
```

### Bullet List
```html
<ul style="margin: 0; padding-left: 20px; list-style: none;">
    <li style="margin: 8px 0; font-size: 14px; color: #D1D5DB; line-height: 1.6;">
        <span style="color: #9CA3AF;">•</span> List item
    </li>
</ul>
```

### Numbered List
```html
<ol style="margin: 0; padding-left: 20px; color: #D1D5DB;">
    <li style="margin: 12px 0; font-size: 15px; line-height: 1.6;">
        List item
    </li>
</ol>
```

## Accessibility

### Color Contrast
- Text on dark background: WCAG AA compliant
- Primary text (#FFFFFF) on #1A1A1A: 15.3:1 ✅
- Secondary text (#E5E7EB) on #1A1A1A: 13.1:1 ✅
- Muted text (#9CA3AF) on #1A1A1A: 7.2:1 ✅

### Alt Text
- Always include alt text for images
- Describe purpose, not appearance
- Keep concise (< 125 characters)

### Semantic HTML
- Use proper heading hierarchy
- Use `<p>` for paragraphs
- Use `<ul>`/`<ol>` for lists
- Use `<table>` for tabular data only

## Email Client Compatibility

### Tested Clients
- ✅ Gmail (Web, iOS, Android)
- ✅ Apple Mail (macOS, iOS)
- ✅ Outlook (Web, Windows, macOS)
- ✅ Yahoo Mail
- ✅ ProtonMail

### Known Issues
- **Outlook Windows**: Limited gradient support (use fallback colors)
- **Gmail Mobile**: Strips some CSS (use inline styles only)
- **Dark Mode**: Test both light and dark mode rendering

### Best Practices
1. **Inline CSS only** - No `<style>` tags
2. **Table-based layouts** - Better compatibility
3. **Absolute URLs** - For images and links
4. **Fallback fonts** - System font stack
5. **Test thoroughly** - Use Litmus or Email on Acid

## Animation & Interactivity

### Hover States
```css
/* Links */
a:hover {
    opacity: 0.8;
}

/* Buttons */
button:hover {
    transform: translateY(-1px);
}
```

### Transitions
- Keep subtle (0.2s ease)
- Only on interactive elements
- Test in all clients

## Dark Mode Support

### Strategy
Our emails are designed dark-first, so they look great in both light and dark mode email clients.

### Media Query
```css
@media (prefers-color-scheme: dark) {
    /* Already optimized for dark mode */
}
```

## Localization

### Text Direction
- Default: LTR (Left-to-Right)
- RTL support: Add `dir="rtl"` to `<html>` tag

### Date Formats
- Use ISO 8601 for dates
- Format in user's timezone
- Example: "Jan 8, 2026"

### Number Formats
- Use locale-appropriate separators
- Currency: R125 (South African Rand)

## Performance

### File Size
- Target: < 100KB per email
- Inline CSS: ~10-15KB
- Images: Optimize and compress
- Total: Aim for < 50KB

### Load Time
- Critical content first
- Lazy load images (if supported)
- Minimize external requests

## Version Control

### Template Versioning
```python
# In template class
VERSION = "1.0.0"
LAST_UPDATED = "2026-01-08"
CHANGELOG = """
1.0.0 (2026-01-08):
  - Initial template creation
  - Added journey box component
  - Implemented feedback sections
"""
```

### Change Log Format
```
[Version] (Date):
  - Change description
  - Another change
```

## Quality Checklist

Before deploying a new template:

- [ ] Design tokens used (no hardcoded colors)
- [ ] Responsive layout (600px max width)
- [ ] Inline CSS only
- [ ] Tested in 3+ email clients
- [ ] Dark mode compatible
- [ ] Accessibility checked (contrast, alt text)
- [ ] Links working (absolute URLs)
- [ ] Emojis rendering correctly
- [ ] Mobile-friendly spacing
- [ ] Registered in template registry
- [ ] Documentation updated
- [ ] Preview HTML generated
- [ ] Peer reviewed

## Resources

### Tools
- **Email Testing**: Litmus, Email on Acid
- **HTML Email Boilerplate**: emailonacid.com/resources
- **Color Contrast**: WebAIM Contrast Checker
- **Preview**: Open HTML in browser

### References
- Campaign Monitor CSS Support: campaignmonitor.com/css
- Can I Email: caniemail.com
- Really Good Emails: reallygoodemails.com
