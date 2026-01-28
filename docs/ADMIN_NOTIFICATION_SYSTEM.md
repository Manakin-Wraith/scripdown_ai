# Admin Notification System for Feedback

## Overview

The admin notification system provides real-time alerts to superusers when users submit feedback. It uses a **hybrid approach** combining in-app notifications with conditional email alerts.

---

## Notification Flow

```
User submits feedback
    ↓
1. Save to feedback_submissions table ✅
2. Send confirmation email to user ✅
3. Create in-app notification for ALL superusers (NEW) ✅
4. IF priority="high" OR category="bug":
   → Send email alert to ALL superusers (NEW) ✅
```

---

## Components

### 1. Database Migration (020)

**File**: `backend/db/migrations/020_notifications_system.sql`

Creates the `notifications` table:
- `id` - UUID primary key
- `user_id` - References auth.users (superuser ID)
- `type` - Notification type (e.g., 'feedback_submitted')
- `title` - Short notification title
- `message` - Notification message
- `data` - JSONB with additional context (feedback_id, category, priority, etc.)
- `read` - Boolean flag
- `created_at` - Timestamp
- `read_at` - Timestamp when marked as read

**Apply Migration**:
```bash
cd backend
python db/apply_migration_020.py
```

Or manually via Supabase Dashboard SQL Editor.

---

### 2. Email Service

**File**: `backend/services/email_service.py`

**New Function**: `send_admin_feedback_alert_email()`

Sends styled email alerts to all superusers with:
- Priority badge (color-coded: high=red, medium=amber, low=green)
- Category badge
- Feedback subject and description (truncated to 300 chars)
- User information (name and email)
- Direct link to admin dashboard: `/admin/feedback/{feedback_id}`

**Email Template**: Dark theme matching SlateOne design system

---

### 3. Feedback Service

**File**: `backend/services/feedback_service.py`

**Modified Function**: `submit_feedback()`

Now includes:

1. **User confirmation email** (existing)
2. **In-app notifications** (NEW):
   - Queries all superusers from `profiles` table
   - Creates notification record for each superuser
   - Notification appears in NotificationBell component
3. **Conditional email alerts** (NEW):
   - Only sent when `priority='high'` OR `category='bug'`
   - Sent to all superuser email addresses
   - Non-blocking (errors logged but don't fail submission)

---

### 4. Frontend Integration

**Component**: `frontend/src/components/notifications/NotificationBell.jsx`

Already implemented with:
- Real-time Supabase subscription to `notifications` table
- Unread count badge
- Dropdown list of notifications
- Mark as read functionality
- Browser notifications (if permission granted)

**No changes required** - the existing NotificationBell automatically displays feedback notifications!

---

## Notification Rules

### In-App Notifications (ALL feedback)
- ✅ Bug reports
- ✅ Feature requests
- ✅ UI/UX issues
- ✅ General feedback
- ✅ All priority levels (low, medium, high)

### Email Alerts (Conditional)
- ✅ High priority feedback (any category)
- ✅ Bug reports (any priority)
- ❌ Low/medium priority feature requests
- ❌ Low/medium priority UI/UX issues
- ❌ Low/medium priority general feedback

---

## Admin Dashboard Integration

### Notification Click Behavior

When admin clicks a feedback notification:
1. Marks notification as read
2. Navigates to: `/admin/feedback/{feedback_id}`

**Note**: The admin feedback management page needs to be created to handle this route.

---

## Testing

### Test In-App Notifications

1. Submit feedback as a regular user
2. Log in as superuser
3. Check NotificationBell in TopBar
4. Should see new notification with unread badge
5. Click notification → should mark as read

### Test Email Alerts

**High Priority Feedback**:
```bash
# Submit with priority="high"
# Check superuser email inbox
# Should receive styled email alert
```

**Bug Report**:
```bash
# Submit with category="bug"
# Check superuser email inbox
# Should receive styled email alert
```

**Low Priority Feature Request**:
```bash
# Submit with priority="low" and category="feature"
# Check superuser email inbox
# Should NOT receive email (only in-app notification)
```

---

## Configuration

### Superuser Setup

Superusers are identified by `is_superuser=true` in the `profiles` table.

To make a user a superuser:
```sql
UPDATE profiles 
SET is_superuser = true 
WHERE email = 'admin@example.com';
```

### Email Settings

Email alerts use the existing Resend integration:
- **From**: `hello@slateone.studio`
- **Subject**: `{emoji} New {priority} Priority Feedback: {subject}`
- **Template**: Dark theme HTML email

---

## Notification Types

Currently implemented:
- `feedback_submitted` - New feedback from user

Future types (for reference):
- `invite_accepted` - Team member accepted invite
- `member_joined` - New team member joined
- `script_shared` - Script shared with user

---

## Database Schema

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- RLS Policy
CREATE POLICY "Users can view own notifications"
    ON notifications FOR SELECT
    USING (auth.uid() = user_id);
```

---

## API Endpoints (Existing)

The NotificationBell component uses these existing endpoints:

- `GET /api/notifications?limit=10` - Fetch notifications
- `POST /api/notifications/{id}/read` - Mark single as read
- `POST /api/notifications/read-all` - Mark all as read

---

## Benefits

### For Admins
✅ **Immediate awareness** of high-priority issues and bugs  
✅ **In-app notifications** for all feedback (non-intrusive)  
✅ **Email alerts** for urgent items only (reduces noise)  
✅ **Real-time updates** via Supabase subscriptions  
✅ **Direct links** to feedback details  

### For Users
✅ **Confirmation email** acknowledging their feedback  
✅ **No change** to submission experience  
✅ **Faster response** on critical issues  

---

## Troubleshooting

### Notifications not appearing

1. **Check migration applied**:
   ```bash
   # Verify notifications table exists in Supabase Dashboard
   ```

2. **Check superuser flag**:
   ```sql
   SELECT id, email, is_superuser FROM profiles WHERE is_superuser = true;
   ```

3. **Check browser console** for WebSocket errors

### Email alerts not sending

1. **Check Resend API key** in `.env`
2. **Check superuser has email** in profiles table
3. **Check backend logs** for email errors
4. **Verify condition**: Only high priority OR bug category

### Frontend not updating

1. **Check Supabase realtime** is enabled for notifications table
2. **Verify RLS policies** allow superuser to read notifications
3. **Check browser notification permissions**

---

## Future Enhancements

- [ ] Admin dashboard page for feedback management
- [ ] Notification preferences (email frequency, categories)
- [ ] Digest emails (daily/weekly summary)
- [ ] Slack/Discord webhook integration
- [ ] Push notifications (mobile)
- [ ] Notification sound/visual indicators
- [ ] Bulk actions (mark multiple as read)

---

## Summary

The admin notification system provides a **balanced approach** to keeping admins informed:

- **All feedback** → In-app notification (passive)
- **Urgent feedback** → Email alert (active)

This ensures admins never miss critical issues while avoiding email fatigue from every submission.
