# Waitlist Welcome Email Setup

## Overview
Automatic welcome emails are sent to users when they join the waitlist in the Notel Supabase project.

## Architecture

### 1. Email Template
**Location**: `backend/services/email_service.py`
**Function**: `send_waitlist_welcome_email(to_email, metadata)`

Features:
- Clean, professional design optimized for 10/10 spam score
- Plain text + HTML versions for better deliverability
- Includes feature preview and next steps
- Tracks email sends via `email_tracking_service`

### 2. Supabase Edge Function
**Location**: `supabase/functions/send-waitlist-welcome/index.ts`
**URL**: `https://yoqcitfxarpbfldxanhi.supabase.co/functions/v1/send-waitlist-welcome`

This Edge Function:
- Receives email and metadata from the trigger
- Calls Resend API to send the welcome email
- Returns success/error status

### 3. Database Setup
**Table**: `waitlist` in Notel Supabase project
**New Columns**:
- `welcome_email_sent` (BOOLEAN) - Tracks if email was sent
- `welcome_email_sent_at` (TIMESTAMPTZ) - When email was sent

## Deployment Steps

### Step 1: Deploy the Edge Function
```bash
cd /Users/thecasterymedia/Desktop/PORTFOLIO/SaaS/ScripDown_AI
supabase functions deploy send-waitlist-welcome --project-ref yoqcitfxarpbfldxanhi
```

### Step 2: Set Environment Variables
In Supabase Dashboard (Notel project):
1. Go to Project Settings → Edge Functions
2. Add secret: `RESEND_API_KEY` = your Resend API key

### Step 3: Enable Database Webhooks (Recommended Approach)
Since database triggers with HTTP calls can be complex, use Supabase Database Webhooks:

1. Go to Supabase Dashboard → Database → Webhooks
2. Create new webhook:
   - **Name**: `send-waitlist-welcome-email`
   - **Table**: `waitlist`
   - **Events**: `INSERT`
   - **Type**: `Supabase Edge Function`
   - **Edge Function**: `send-waitlist-welcome`
   - **HTTP Headers**: 
     ```json
     {
       "Content-Type": "application/json"
     }
     ```
   - **Payload**: Use the default (sends full row data)

### Alternative: Manual Processing Script
If webhooks aren't suitable, use the batch processing script:

**Location**: `backend/scripts/send_waitlist_welcome_batch.py`

```python
"""
Process waitlist users who haven't received welcome emails yet.
Run this as a cron job or manually.
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client
from services.email_service import send_waitlist_welcome_email

NOTEL_SUPABASE_URL = os.getenv('NOTEL_SUPABASE_URL')
NOTEL_SUPABASE_KEY = os.getenv('NOTEL_SUPABASE_SERVICE_KEY')

def process_pending_welcomes():
    """Send welcome emails to waitlist users who haven't received one yet."""
    client = create_client(NOTEL_SUPABASE_URL, NOTEL_SUPABASE_KEY)
    
    # Get users who haven't received welcome email
    response = client.table('waitlist')\
        .select('*')\
        .eq('welcome_email_sent', False)\
        .order('created_at', desc=False)\
        .limit(50)\
        .execute()
    
    users = response.data
    print(f"Found {len(users)} users pending welcome email")
    
    for user in users:
        email = user['email']
        metadata = user.get('metadata', {})
        
        print(f"Sending welcome email to {email}...")
        result = send_waitlist_welcome_email(email, metadata)
        
        if 'error' not in result:
            # Mark as sent
            client.table('waitlist')\
                .update({
                    'welcome_email_sent': True,
                    'welcome_email_sent_at': 'now()'
                })\
                .eq('id', user['id'])\
                .execute()
            print(f"  ✓ Sent successfully")
        else:
            print(f"  ✗ Failed: {result['error']}")

if __name__ == '__main__':
    process_pending_welcomes()
```

Run manually:
```bash
cd backend
python scripts/send_waitlist_welcome_batch.py
```

Or set up as cron job (every 5 minutes):
```bash
*/5 * * * * cd /path/to/backend && python scripts/send_waitlist_welcome_batch.py
```

## Testing

### Test the Edge Function Directly
```bash
curl -X POST \
  https://yoqcitfxarpbfldxanhi.supabase.co/functions/v1/send-waitlist-welcome \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","metadata":{}}'
```

### Test via Database Insert
```sql
-- In Notel Supabase SQL Editor
INSERT INTO waitlist (email, source, metadata)
VALUES ('test@example.com', 'test', '{"role": "Director"}');

-- Check if email was marked as sent
SELECT email, welcome_email_sent, welcome_email_sent_at 
FROM waitlist 
WHERE email = 'test@example.com';
```

## Monitoring

### Check Email Logs
```sql
-- In main SlateOne Supabase project
SELECT * FROM email_tracking 
WHERE email_type = 'waitlist_welcome' 
ORDER BY sent_at DESC 
LIMIT 10;
```

### Check Pending Emails
```sql
-- In Notel Supabase project
SELECT COUNT(*) as pending_count
FROM waitlist 
WHERE welcome_email_sent = FALSE;
```

## Troubleshooting

### Emails Not Sending
1. Check Edge Function logs in Supabase Dashboard
2. Verify `RESEND_API_KEY` is set correctly
3. Check Resend dashboard for delivery status
4. Verify webhook is enabled and configured correctly

### Database Trigger Issues
If using database triggers instead of webhooks:
- Check function exists: `\df trigger_waitlist_welcome_email`
- Check trigger exists: `\d+ waitlist`
- View logs: Check Supabase Dashboard → Database → Logs

### Email Goes to Spam
- Verify SPF/DKIM/DMARC records in Resend
- Use verified domain (hello@slateone.studio)
- Test with mail-tester.com

## Email Content

The welcome email includes:
- **Subject**: "Welcome to SlateOne - You're on the list!"
- **From**: hello@slateone.studio
- **Design**: Clean, professional, optimized for deliverability
- **Content**:
  - Welcome message
  - What's next (3 clear points)
  - Feature preview (AI Analysis, Team Collaboration, Reports)
  - Contact information

## Configuration Files

### Environment Variables Required
```bash
# In Notel Supabase Edge Function secrets
RESEND_API_KEY=re_xxxxx

# In backend/.env (for batch script)
NOTEL_SUPABASE_URL=https://yoqcitfxarpbfldxanhi.supabase.co
NOTEL_SUPABASE_SERVICE_KEY=your_service_role_key
RESEND_API_KEY=re_xxxxx
```

## Summary

**Recommended Setup**: Use Supabase Database Webhooks to call the Edge Function automatically when users join the waitlist.

**Alternative**: Run the batch processing script as a cron job to send welcome emails to pending users.

Both approaches ensure new waitlist users receive a professional welcome email immediately after signup.
