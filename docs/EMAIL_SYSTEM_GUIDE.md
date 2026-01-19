# ScripDown AI Email System Guide

## Overview
ScripDown AI uses **Resend** as its email service provider for sending transactional emails to users. This guide explains the current setup and how to create new email templates.

---

## Current Email Infrastructure

### 1. Email Service Configuration

**Location**: `backend/services/email_service.py`

**Key Components**:
- **Provider**: Resend (https://resend.com)
- **API Key**: Configured via `RESEND_API_KEY` environment variable
- **From Email**: Configured via `RESEND_FROM_EMAIL` environment variable
- **App Name**: SlateOne
- **App URL**: Configured via `FRONTEND_URL` environment variable

**Environment Variables** (`.env` file):
```bash
RESEND_API_KEY=your_resend_api_key_here
RESEND_FROM_EMAIL=onboarding@resend.dev  # or your verified domain email
FRONTEND_URL=https://app.slateone.studio
```

### 2. Core Email Functions

#### Base Email Function
```python
send_email(
    to: str,
    subject: str,
    html: str,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None
) -> Dict[str, Any]
```

This is the foundational function that all other email functions use.

---

## Existing Email Templates

### 1. **Welcome Email** (`send_welcome_email`)
- **Trigger**: After user signup
- **Variants**: 
  - Paid users: Confirms beta access
  - Unpaid users: Shows Yoco payment link (R249 for 1 year)
- **Parameters**: `to_email`, `full_name`, `has_paid`
- **Called From**: `backend/routes/auth_routes.py` → `/api/auth/welcome-email`

### 2. **Team Invite Accepted** (`send_invite_accepted_notification`)
- **Trigger**: When someone accepts a team invite
- **Recipient**: The person who sent the invite
- **Parameters**: `to_email`, `inviter_name`, `accepter_name`, `script_title`, `department`, `script_url`
- **Called From**: `backend/routes/invite_routes.py`

### 3. **Early Access Invite** (`send_early_access_invite`)
- **Trigger**: Manual send to early access users
- **Special Feature**: 30-day trial instead of 14 days
- **Parameters**: `to_email`, `first_name`
- **Called From**: `backend/scripts/send_early_access_invites.py`

### 4. **Expiration Reminder** (`send_expiration_reminder_email`)
- **Trigger**: Scheduled job (7, 3, 1 days before expiration)
- **Variants**: Trial vs Paid subscription
- **Parameters**: `to_email`, `full_name`, `days_remaining`, `is_trial`
- **Urgency Colors**: Red (≤3 days), Orange (>3 days)

### 5. **Test Email** (`send_test_email`)
- **Purpose**: Verify email service configuration
- **Parameters**: `to_email`

### 6. **Beta Launch Email** (`send_beta_launch_email`)
- **Trigger**: Manual send to announce beta launch
- **Variants**: 
  - New users: General beta invitation
  - Trial users: Upgrade prompt with script retention message
  - Waitlist users: Early access confirmation
- **Parameters**: `to_email`, `user_name`, `user_status` ('new'|'trial'|'waitlist'), `trial_days_remaining` (optional)
- **Called From**: `backend/routes/beta_routes.py` → `/api/beta/send-launch-email`
- **Features**:
  - Holiday-aware messaging (December 2025)
  - Timeline-agnostic roadmap (no specific dates)
  - Links to slateone.studio landing page
  - Manual referral incentive (email beta@slateone.studio)
  - R249 for 1 year offer
  - 30-day money-back guarantee

---

## Email Design System

All emails follow a consistent design pattern:

### Visual Structure
```
┌─────────────────────────────────┐
│  Header (Gradient Background)   │  ← Orange gradient (#F59E0B → #D97706)
│  🎬 SlateOne                     │
├─────────────────────────────────┤
│  Optional Banner (Status/Alert) │  ← Green/Red/Orange based on context
├─────────────────────────────────┤
│                                 │
│  Main Content                   │  ← Dark theme (#1A1A1A background)
│  - Greeting                     │
│  - Message                      │
│  - CTA Button                   │
│                                 │
├─────────────────────────────────┤
│  Features/Details Section       │  ← Optional info cards
├─────────────────────────────────┤
│  Footer                         │  ← Legal text, copyright
└─────────────────────────────────┘
```

### Color Palette
- **Background**: `#0F0F0F` (outer), `#1A1A1A` (card)
- **Primary**: `#F59E0B` (Orange)
- **Success**: `#10B981` (Green)
- **Warning**: `#F59E0B` (Orange)
- **Error**: `#EF4444` (Red)
- **Text Primary**: `#FFFFFF`
- **Text Secondary**: `#9CA3AF`
- **Text Muted**: `#6B7280`
- **Borders**: `#2A2A2A`, `#3A3A3A`
- **Card Background**: `#262626`

### Typography
- **Font Stack**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`
- **Heading H1**: 24px, bold
- **Heading H2**: 28px, bold
- **Body**: 16px
- **Small**: 14px
- **Tiny**: 12px

---

## How to Create a New Email Template

### Step 1: Define Your Email Function

Add a new function to `backend/services/email_service.py`:

```python
def send_your_new_email(
    to_email: str,
    param1: str,
    param2: Optional[str] = None
) -> Dict[str, Any]:
    """
    Brief description of when this email is sent.
    
    Args:
        to_email: Recipient email address
        param1: Description of parameter
        param2: Optional parameter description
    """
    # Extract first name if needed
    first_name = param1.split(' ')[0] if param1 else 'there'
    
    # Define subject
    subject = f"🎬 Your Subject Line - {APP_NAME}"
    
    # Build HTML template (see template structure below)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0F0F0F; color: #FFFFFF;">
        <!-- Your email content here -->
    </body>
    </html>
    """
    
    # Send the email
    return send_email(to_email, subject, html)
```

### Step 2: HTML Template Structure

Use this boilerplate for consistent styling:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0F0F0F; color: #FFFFFF;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0F0F0F; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1A1A1A; border-radius: 16px; overflow: hidden; border: 1px solid #2A2A2A;">
                    
                    <!-- HEADER -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #F59E0B, #D97706); padding: 32px; text-align: center;">
                            <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #000000;">
                                🎬 SlateOne
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- OPTIONAL BANNER (Status/Alert) -->
                    <tr>
                        <td style="background-color: #10B981; padding: 12px; text-align: center;">
                            <p style="margin: 0; font-size: 14px; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 1px;">
                                ✨ Your Banner Text ✨
                            </p>
                        </td>
                    </tr>
                    
                    <!-- MAIN CONTENT -->
                    <tr>
                        <td style="padding: 40px 32px;">
                            <h2 style="margin: 0 0 16px 0; font-size: 28px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
                                Your Main Heading
                            </h2>
                            
                            <p style="margin: 0 0 24px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                                Your main message goes here.
                            </p>
                            
                            <!-- INFO CARD (Optional) -->
                            <div style="background-color: #262626; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                                <p style="margin: 0; font-size: 14px; color: #9CA3AF;">
                                    Additional information or details
                                </p>
                            </div>
                            
                            <!-- CTA BUTTON -->
                            <a href="{APP_URL}/your-link" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                Your Call to Action →
                            </a>
                        </td>
                    </tr>
                    
                    <!-- FOOTER -->
                    <tr>
                        <td style="padding: 24px 32px; border-top: 1px solid #2A2A2A; text-align: center;">
                            <p style="margin: 0 0 8px 0; font-size: 12px; color: #6B7280;">
                                Questions? Reply to this email or reach out at support@slateone.studio
                            </p>
                            <p style="margin: 0; font-size: 12px; color: #6B7280;">
                                © SlateOne • AI-Powered Script Breakdown
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
```

### Step 3: Create API Endpoint (if needed)

If the email needs to be triggered via API, add a route in the appropriate blueprint:

**Example in `backend/routes/auth_routes.py`**:
```python
@auth_bp.route('/your-email-endpoint', methods=['POST'])
def send_your_email_route():
    """
    Send your custom email.
    """
    data = request.get_json()
    
    # Validate required fields
    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    # Send email
    result = send_your_new_email(
        to_email=email,
        param1=data.get('param1')
    )
    
    if 'error' in result:
        return jsonify({'error': result['error']}), 500
    
    return jsonify({'message': 'Email sent successfully'}), 200
```

### Step 4: Test Your Email

Use the test endpoint or create a simple test script:

```python
# backend/scripts/test_your_email.py
from services.email_service import send_your_new_email

result = send_your_new_email(
    to_email="your-test-email@example.com",
    param1="Test User"
)

print(result)
```

Run it:
```bash
cd backend
python scripts/test_your_email.py
```

---

## Common Email Components

### 1. Info Card
```html
<div style="background-color: #262626; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
    <p style="margin: 0 0 8px 0; font-size: 14px; color: #F59E0B; font-weight: 600;">
        LABEL
    </p>
    <p style="margin: 0; font-size: 16px; color: #FFFFFF;">
        Your content
    </p>
</div>
```

### 2. Success Banner
```html
<tr>
    <td style="background-color: #10B981; padding: 12px; text-align: center;">
        <p style="margin: 0; font-size: 14px; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 1px;">
            ✅ SUCCESS MESSAGE
        </p>
    </td>
</tr>
```

### 3. Warning/Urgency Banner
```html
<tr>
    <td style="background-color: #F59E0B; padding: 16px; text-align: center;">
        <p style="margin: 0; font-size: 18px; font-weight: 700; color: #FFFFFF;">
            ⚠️ Warning Message
        </p>
    </td>
</tr>
```

### 4. Feature List
```html
<table width="100%" cellpadding="0" cellspacing="0">
    <tr>
        <td style="padding: 10px 14px; background-color: #262626; border: 1px solid #3A3A3A; border-radius: 8px; margin-bottom: 6px;">
            <p style="margin: 0; font-size: 14px; color: #FFFFFF;">📄 Feature Name</p>
        </td>
    </tr>
</table>
```

### 5. CTA Button
```html
<a href="{APP_URL}/link" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
    Button Text →
</a>
```

---

## Best Practices

### 1. **Email Compatibility**
- Use inline CSS (no external stylesheets)
- Use tables for layout (not divs/flexbox)
- Test in multiple email clients (Gmail, Outlook, Apple Mail)
- Keep width at 600px max for desktop
- Use `cellpadding="0" cellspacing="0"` on all tables

### 2. **Content Guidelines**
- Keep subject lines under 50 characters
- Use emojis sparingly in subject lines (1-2 max)
- Front-load important information
- Include clear call-to-action
- Always provide unsubscribe option for marketing emails

### 3. **Personalization**
- Use first name when possible
- Reference specific user actions/data
- Segment emails by user type (trial, paid, etc.)

### 4. **Testing Checklist**
- [ ] Test with real Resend API
- [ ] Verify all links work
- [ ] Check mobile rendering
- [ ] Test with long/short names
- [ ] Verify dynamic content renders correctly
- [ ] Check spam score (use mail-tester.com)

### 5. **Error Handling**
```python
if not is_configured():
    print("Warning: Email service not configured")
    return {'error': 'Email service not configured'}

try:
    response = resend.Emails.send(params)
    return response
except Exception as e:
    print(f"Error sending email: {e}")
    return {'error': str(e)}
```

---

## Resend Dashboard Configuration

### 1. **Verify Your Domain**
- Go to https://resend.com/domains
- Add your domain (e.g., `slateone.studio`)
- Add DNS records (SPF, DKIM, DMARC)
- Wait for verification

### 2. **Create API Key**
- Go to https://resend.com/api-keys
- Create new API key with appropriate permissions
- Copy to `.env` file as `RESEND_API_KEY`

### 3. **Set From Email**
- Use verified domain: `hello@slateone.studio`
- Or use Resend's default: `onboarding@resend.dev`
- Update `RESEND_FROM_EMAIL` in `.env`

### 4. **Monitor Emails**
- View sent emails in Resend dashboard
- Check delivery rates
- Monitor bounces and complaints

---

## Example: Creating a "Script Analysis Complete" Email

```python
def send_analysis_complete_email(
    to_email: str,
    user_name: str,
    script_title: str,
    scene_count: int,
    script_url: str
) -> Dict[str, Any]:
    """
    Notify user when their script analysis is complete.
    
    Args:
        to_email: User's email
        user_name: User's full name
        script_title: Title of the analyzed script
        scene_count: Number of scenes detected
        script_url: Direct link to view the script
    """
    first_name = user_name.split(' ')[0] if user_name else 'there'
    
    subject = f"✅ {script_title} - Analysis Complete!"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0F0F0F; color: #FFFFFF;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0F0F0F; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #1A1A1A; border-radius: 16px; overflow: hidden; border: 1px solid #2A2A2A;">
                        
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #F59E0B, #D97706); padding: 32px; text-align: center;">
                                <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #000000;">
                                    🎬 {APP_NAME}
                                </h1>
                            </td>
                        </tr>
                        
                        <!-- Success Banner -->
                        <tr>
                            <td style="background-color: #10B981; padding: 12px; text-align: center;">
                                <p style="margin: 0; font-size: 14px; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 1px;">
                                    ✅ ANALYSIS COMPLETE
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 32px;">
                                <h2 style="margin: 0 0 16px 0; font-size: 28px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
                                    Great news, {first_name}! 🎉
                                </h2>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                                    Your script "<strong style="color: #FFFFFF;">{script_title}</strong>" has been fully analyzed and is ready to view.
                                </p>
                                
                                <!-- Stats Card -->
                                <div style="background-color: #262626; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                                    <p style="margin: 0 0 8px 0; font-size: 14px; color: #F59E0B; font-weight: 600;">📊 ANALYSIS RESULTS</p>
                                    <p style="margin: 0; font-size: 32px; font-weight: 700; color: #FFFFFF;">
                                        {scene_count} <span style="font-size: 16px; color: #9CA3AF; font-weight: 400;">scenes detected</span>
                                    </p>
                                </div>
                                
                                <p style="margin: 0 0 24px 0; font-size: 16px; color: #9CA3AF; line-height: 1.6;">
                                    We've extracted characters, props, wardrobe, and more from each scene. Click below to explore your breakdown.
                                </p>
                                
                                <!-- CTA Button -->
                                <a href="{script_url}" style="display: inline-block; background: linear-gradient(135deg, #F59E0B, #D97706); color: #000000; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    View Script Breakdown →
                                </a>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 32px; border-top: 1px solid #2A2A2A; text-align: center;">
                                <p style="margin: 0 0 8px 0; font-size: 12px; color: #6B7280;">
                                    Questions? Reply to this email or reach out at support@slateone.studio
                                </p>
                                <p style="margin: 0; font-size: 12px; color: #6B7280;">
                                    © {APP_NAME} • AI-Powered Script Breakdown
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
    
    return send_email(to_email, subject, html)
```

---

## Troubleshooting

### Email Not Sending
1. Check `RESEND_API_KEY` is set correctly
2. Verify domain is verified in Resend dashboard
3. Check backend logs for error messages
4. Test with `send_test_email()` function

### Email Goes to Spam
1. Verify SPF, DKIM, DMARC records
2. Use verified domain (not `@resend.dev`)
3. Avoid spam trigger words
4. Test with mail-tester.com
5. Warm up your domain gradually

### Styling Issues
1. Always use inline CSS
2. Test in multiple email clients
3. Use tables for layout
4. Avoid JavaScript
5. Keep images optimized and hosted externally

---

## Resources

- **Resend Documentation**: https://resend.com/docs
- **Email Template Testing**: https://www.mail-tester.com
- **HTML Email Guide**: https://www.campaignmonitor.com/css/
- **Email Client Support**: https://www.caniemail.com

---

## Summary

Your email system is well-structured and ready for expansion. To create new emails:

1. Add function to `email_service.py`
2. Use the HTML boilerplate template
3. Follow the design system (colors, typography, spacing)
4. Create API endpoint if needed
5. Test thoroughly before deploying

All emails maintain consistent branding with the SlateOne dark theme and orange accent colors.
