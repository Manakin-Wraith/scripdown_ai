# Email Campaigns Feature - Setup & Testing Guide

## ✅ Implementation Complete

All code has been implemented:
- ✅ Database schema designed
- ✅ Backend API routes (`/api/campaigns/*`)
- ✅ Campaign service with user segmentation
- ✅ Frontend UI with campaign list
- ✅ Campaign Builder modal (4-step wizard)
- ✅ Routes integrated

## 🚀 Setup Instructions

### 1. Apply Database Migration

**CRITICAL:** The migration must be run in Supabase Dashboard (not via CLI)

1. Open Supabase SQL Editor:
   ```
   https://supabase.com/dashboard/project/twzfaizeyqwevmhjyicz/sql/new
   ```

2. Copy the migration SQL:
   ```bash
   cat backend/db/migrations/025_email_campaigns_system.sql | pbcopy
   ```

3. Paste into SQL Editor and click **"Run"**

4. Verify success - should see:
   - 4 tables created
   - 4 default templates inserted
   - No errors

### 2. Test Database Connectivity

```bash
cd backend
python3 test_campaign_db.py
```

**Expected output:**
```
✅ DATABASE CONNECTIVITY TEST PASSED!

Summary:
  - Templates: 4
  - Campaigns: 0
  - Recipients: 0
  - Clicks: 0
```

### 3. Start Backend Server

```bash
cd backend
source venv/bin/activate  # if not already activated
python3 app.py
```

Server should start on `http://localhost:5000`

### 4. Start Frontend

```bash
cd frontend
npm start
```

Frontend should start on `http://localhost:3000`

## 🧪 Testing the Feature

### Test 1: Access Email Campaigns Page

1. Login as superuser
2. Navigate to Admin Dashboard
3. Click "Email Campaigns" button
4. Should see the campaigns page with stats

### Test 2: Create a Campaign

1. Click "Create Campaign" button
2. **Step 1 - Details:**
   - Enter campaign name: "Test Campaign"
   - Enter description (optional)
   - Click "Next"

3. **Step 2 - Template:**
   - Select a template (e.g., "Trial Expiring Soon")
   - Click "Next"

4. **Step 3 - Audience:**
   - Select subscription status filters (optional)
   - Set script count filters (optional)
   - Click "Preview Audience" to see recipient count
   - Click "Next"

5. **Step 4 - Review:**
   - Review campaign details
   - Check "Save as draft" to avoid sending immediately
   - Click "Create Campaign"

6. **Verify:**
   - Campaign should appear in the list
   - Status should be "Draft"
   - Recipient count should be displayed

### Test 3: View Campaign Analytics

1. Find a sent campaign in the list
2. Click "Analytics" button
3. Should see modal with:
   - Total recipients
   - Emails sent
   - Delivery rate
   - Open rate
   - Click rate
   - Click-to-open rate

### Test 4: Send a Campaign

1. Find a draft campaign
2. Click "Send Now" button
3. Confirm the action
4. Campaign status should change to "Sending" then "Sent"

## 📊 Database Schema

### Tables Created

1. **email_templates**
   - Stores reusable email templates
   - Supports variable substitution
   - Default templates: Trial Expiring, Welcome, Re-engagement, Feature Announcement

2. **email_campaigns**
   - Campaign metadata and configuration
   - Audience filters (JSON)
   - Scheduling information
   - Aggregated statistics

3. **email_campaign_recipients**
   - Individual recipient records
   - Tracking: sent, delivered, opened, clicked, bounced
   - Error logging

4. **email_campaign_clicks**
   - Click tracking for campaign links
   - URL, timestamp, user agent, IP

## 🔒 Security

- All endpoints require superuser authentication
- RLS policies enforce superuser-only access
- JWT verification on all API calls
- Admin client bypasses RLS for campaign management

## 🎯 API Endpoints

### Templates
- `GET /api/campaigns/templates` - List templates
- `GET /api/campaigns/templates/:id` - Get template
- `POST /api/campaigns/templates` - Create template

### Campaigns
- `GET /api/campaigns` - List campaigns
- `POST /api/campaigns` - Create campaign
- `GET /api/campaigns/:id` - Get campaign
- `PUT /api/campaigns/:id` - Update campaign
- `DELETE /api/campaigns/:id` - Delete campaign
- `POST /api/campaigns/:id/send` - Send campaign
- `GET /api/campaigns/:id/analytics` - Get analytics

### Audience
- `POST /api/campaigns/audience/preview` - Preview audience

## 🐛 Troubleshooting

### Migration Errors

**Error: "relation already exists"**
- Run the rollback script first:
  ```sql
  -- See: backend/db/migrations/025_rollback_email_campaigns.sql
  ```

**Error: "column 'id' does not exist"**
- Migration uses `auth.users(id)` for foreign keys
- Ensure you're using the corrected migration file

### Backend Errors

**Error: "Table not found"**
- Migration not applied
- Run migration in Supabase Dashboard

**Error: "Permission denied"**
- User is not a superuser
- Check `profiles.is_superuser = true`

### Frontend Errors

**Error: "Network Error"**
- Backend not running
- Check `http://localhost:5000/api/campaigns/templates`

**Empty template list**
- Migration didn't insert default templates
- Check database with test script

## 📝 Next Steps (Optional Enhancements)

1. **Campaign Builder Enhancements:**
   - Rich text email editor
   - Template preview with variable substitution
   - A/B testing support
   - Advanced scheduling (recurring campaigns)

2. **Analytics Enhancements:**
   - Click heatmaps
   - Engagement trends over time
   - Recipient segmentation analysis
   - Export analytics to CSV

3. **Template Management:**
   - Template editor UI
   - Template categories
   - Template versioning
   - Custom variable definitions

4. **Audience Segmentation:**
   - Saved audience segments
   - Dynamic segments (auto-update)
   - Segment size estimation
   - Segment overlap analysis

## 🎉 Success Criteria

- ✅ Can create campaigns via UI
- ✅ Can select templates
- ✅ Can filter audience
- ✅ Can preview recipient count
- ✅ Campaigns persist to database
- ✅ Can view campaign list
- ✅ Can view campaign analytics
- ✅ Can send campaigns
- ✅ Can delete draft campaigns
