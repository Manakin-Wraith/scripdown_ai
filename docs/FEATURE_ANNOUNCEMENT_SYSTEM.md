# Feature Announcement Email System

## Overview
System for sending targeted feature announcement emails to users about new features and updates in SlateOne.

## Components

### 1. Email Template
**File**: `backend/services/email_service.py`

**Function**: `send_feature_announcement_email(to_email, full_name, features=None)`

**Default Features**:
- 💬 Feedback System
- 📊 Enhanced Reports

**Template Features**:
- Modern dark theme matching SlateOne branding
- Responsive HTML email design
- Green "NEW FEATURES" badge
- Feature cards with icons, titles, and descriptions
- CTA button linking to app
- Feedback request section

### 2. API Endpoint
**Route**: `POST /api/auth/send-feature-announcement`

**Request Body**:
```json
{
  "recipients": ["user1@example.com", "user2@example.com"],  // Optional
  "send_to_all": false,  // Set to true to send to all users
  "features": [  // Optional, uses defaults if not provided
    {
      "icon": "💬",
      "title": "Feedback System",
      "description": "Share your thoughts directly in the app."
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "sent_count": 10,
  "failed_count": 0,
  "total_recipients": 10,
  "errors": null
}
```

**Behavior**:
- If `send_to_all: true` → sends to all users in `profiles` table
- If `recipients` provided → sends to specific emails
- Fetches user names from database automatically
- Returns detailed success/failure stats

### 3. Admin Script
**File**: `scripts/send_feature_announcement.py`

**Usage Examples**:

```bash
# Preview mode (dry run) - see who would receive emails
python scripts/send_feature_announcement.py --all --preview

# Send to all users with default features
python scripts/send_feature_announcement.py --all

# Send to specific users
python scripts/send_feature_announcement.py --emails user1@example.com user2@example.com

# Send with custom features from JSON file
python scripts/send_feature_announcement.py --all --features-file scripts/example_features.json
```

**Features**:
- ✅ Preview mode for testing
- ✅ Send to all users or specific emails
- ✅ Custom features via JSON file
- ✅ Progress tracking with emoji indicators
- ✅ Detailed error reporting
- ✅ Confirmation prompt before sending

### 4. Example Features File
**File**: `scripts/example_features.json`

```json
[
  {
    "icon": "💬",
    "title": "Feedback System",
    "description": "Share your thoughts and suggestions directly in the app."
  },
  {
    "icon": "📊",
    "title": "Enhanced Reports",
    "description": "Generate professional production reports with improved layouts."
  }
]
```

## Use Cases

### Announcing New Features
When you add new features like feedback and reports:

1. **Create features JSON** (optional):
   ```bash
   # Edit scripts/example_features.json or create new file
   ```

2. **Preview the announcement**:
   ```bash
   python scripts/send_feature_announcement.py --all --preview
   ```

3. **Send to all users**:
   ```bash
   python scripts/send_feature_announcement.py --all
   ```

### Testing with Specific Users
```bash
# Test with your own email first
python scripts/send_feature_announcement.py --emails your@email.com

# Then send to beta testers
python scripts/send_feature_announcement.py --emails \
  tester1@example.com \
  tester2@example.com \
  tester3@example.com
```

### Using the API Directly
```bash
# Send to all users via API
curl -X POST http://localhost:5000/api/auth/send-feature-announcement \
  -H "Content-Type: application/json" \
  -d '{
    "send_to_all": true,
    "features": [
      {
        "icon": "💬",
        "title": "Feedback System",
        "description": "Share your thoughts directly in the app."
      },
      {
        "icon": "📊",
        "title": "Enhanced Reports",
        "description": "Professional production reports with better layouts."
      }
    ]
  }'
```

## Email Template Customization

To customize the email template, edit `send_feature_announcement_email()` in `backend/services/email_service.py`:

- **Subject line**: Line 762
- **Features HTML**: Lines 765-780
- **Main content**: Lines 782-875
- **CTA button**: Lines 832-834
- **Branding colors**: Gradient uses `#F59E0B` and `#D97706`

## Best Practices

### Before Sending
1. ✅ Test with preview mode first
2. ✅ Send to yourself to verify formatting
3. ✅ Check that RESEND_API_KEY is configured
4. ✅ Verify recipient list is correct
5. ✅ Review feature descriptions for clarity

### Feature Descriptions
- Keep titles short (2-4 words)
- Descriptions should be 1-2 sentences
- Use emojis that match the feature theme
- Focus on user benefits, not technical details

### Timing
- Send during business hours (9 AM - 5 PM user timezone)
- Avoid weekends for professional users
- Space announcements at least 1-2 weeks apart
- Consider user's subscription status

## Error Handling

The system handles:
- Missing email configuration → Returns 503 error
- Invalid recipients → Skips and logs error
- Email send failures → Continues with next recipient
- Database connection issues → Exits with error message

## Monitoring

Check email delivery:
1. **Resend Dashboard**: View sent emails and delivery status
2. **Script output**: Shows real-time progress
3. **API response**: Returns detailed stats
4. **Server logs**: Check for error messages

## Environment Variables

Required:
- `RESEND_API_KEY` - Resend API key for sending emails
- `RESEND_FROM_EMAIL` - Sender email (default: hello@slateone.studio)
- `FRONTEND_URL` - App URL for CTA button (default: https://app.slateone.studio)

## Example Workflow: Announcing Feedback & Reports

```bash
# 1. Create custom features file
cat > /tmp/feedback_reports.json << EOF
[
  {
    "icon": "💬",
    "title": "Feedback System",
    "description": "Share your thoughts and suggestions directly in the app. We read every piece of feedback!"
  },
  {
    "icon": "📊",
    "title": "Enhanced Reports",
    "description": "Generate professional production reports with improved layouts and export options."
  }
]
EOF

# 2. Preview
python scripts/send_feature_announcement.py \
  --all \
  --features-file /tmp/feedback_reports.json \
  --preview

# 3. Send to yourself first
python scripts/send_feature_announcement.py \
  --emails your@email.com \
  --features-file /tmp/feedback_reports.json

# 4. Send to all users
python scripts/send_feature_announcement.py \
  --all \
  --features-file /tmp/feedback_reports.json
```

## Troubleshooting

### "Email service not configured"
- Check `RESEND_API_KEY` in `.env`
- Verify API key is valid in Resend dashboard

### "No recipients found"
- Verify emails exist in `profiles` table
- Check for typos in email addresses

### Emails not delivering
- Check Resend dashboard for bounce/spam reports
- Verify sender email is verified in Resend
- Check recipient spam folders

### Script permission denied
```bash
chmod +x scripts/send_feature_announcement.py
```

## Future Enhancements

Potential improvements:
- [ ] Email scheduling (send at specific time)
- [ ] A/B testing different subject lines
- [ ] User segmentation (by subscription tier, activity, etc.)
- [ ] Email analytics tracking (opens, clicks)
- [ ] Unsubscribe management
- [ ] Email templates library
