# Early Access User Sync System

## Overview

This system ensures accurate tracking of early access users by cross-referencing the `early_access_users` table with authenticated users in `auth.users`.

## Architecture

### Three-Layer Approach

1. **Database Trigger** (Automatic, Real-time)
   - Syncs users immediately when they sign up
   - No manual intervention needed
   - Most reliable method

2. **Sync Script** (Manual, One-time Cleanup)
   - Fixes existing data inconsistencies
   - Can be run on-demand
   - Supports dry-run mode

3. **Enhanced Query** (Runtime, Auto-correction)
   - Validates data during reminder campaigns
   - Auto-syncs discovered inconsistencies
   - Prevents sending reminders to signed-up users

---

## Components

### 1. Database Migration

**File:** `db/migrations/006_sync_early_access_trigger.sql`

**What it does:**
- Creates `sync_early_access_signup()` function
- Adds trigger on `auth.users` INSERT
- Automatically updates `early_access_users` when user signs up

**To apply:**
```bash
# Apply via Supabase dashboard or CLI
psql $DATABASE_URL -f db/migrations/006_sync_early_access_trigger.sql
```

**Verification:**
```sql
-- Check if trigger exists
SELECT trigger_name, event_manipulation, event_object_table
FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_created';
```

---

### 2. Sync Script

**File:** `scripts/sync_early_access_users.py`

**Purpose:** One-time cleanup of existing data

**Usage:**
```bash
# Dry run (see what would be synced)
python scripts/sync_early_access_users.py --dry-run

# Actually sync
python scripts/sync_early_access_users.py
```

**When to run:**
- After applying the database trigger (to fix existing data)
- Periodically to catch any edge cases
- Before major reminder campaigns

**Output:**
```
======================================================================
EARLY ACCESS USER SYNC
======================================================================
📊 Fetching authenticated users...
   Found 15 authenticated users

📊 Fetching early access users with 'invited' status...
   Found 8 invited users

======================================================================
SYNC RESULTS
======================================================================
✅ Synced: user1@example.com
✅ Synced: user2@example.com
⏳ Not signed up: user3@example.com
⏳ Not signed up: user4@example.com

======================================================================
SUMMARY
======================================================================
Total invited users: 8
Synced: 2
Not signed up: 6
======================================================================
```

---

### 3. Enhanced Reminder Script

**File:** `scripts/send_reminders_to_early_access.py`

**Enhancement:** Cross-references with `auth.users` before sending

**How it works:**
1. Fetches users with status 'invited'
2. Cross-references with authenticated users
3. Auto-syncs any users who signed up but weren't marked
4. Only sends reminders to truly non-signed-up users

**Usage:**
```bash
python scripts/send_reminders_to_early_access.py
```

**Output:**
```
======================================================================
EARLY ACCESS REMINDER CAMPAIGN
======================================================================

📊 Fetching early access users from Supabase...
   Fetching invited users...
   Cross-referencing with authenticated users...
   ✅ Auto-synced: user1@example.com
   ✅ Auto-synced: user2@example.com
   📊 Auto-synced 2 user(s) who had signed up

Found 6 user(s) who haven't signed up yet:
  1. John (john@example.com) - Invited: 2026-01-10
  2. Jane (jane@example.com) - Invited: 2026-01-12
  ...
```

---

## Data Integrity Verification

**File:** `scripts/verify_early_access_integrity.sql`

**Purpose:** Check data accuracy and health

**Queries included:**
1. Users marked 'invited' but actually signed up
2. Users marked 'signed_up' but no auth record
3. Users with mismatched user_id
4. Conversion rate statistics
5. Time to signup analysis
6. Recent signups
7. Users invited but not signed up
8. Sync metadata analysis
9. Duplicate email check
10. Overall health check

**Usage:**
```bash
# Run all queries
psql $DATABASE_URL -f scripts/verify_early_access_integrity.sql

# Or run specific queries in Supabase SQL Editor
```

---

## Workflow

### Initial Setup

1. **Apply database migration**
   ```bash
   psql $DATABASE_URL -f db/migrations/006_sync_early_access_trigger.sql
   ```

2. **Run sync script to fix existing data**
   ```bash
   # Dry run first
   python scripts/sync_early_access_users.py --dry-run
   
   # Then actually sync
   python scripts/sync_early_access_users.py
   ```

3. **Verify data integrity**
   ```bash
   psql $DATABASE_URL -f scripts/verify_early_access_integrity.sql
   ```

### Ongoing Operations

**Before sending reminders:**
```bash
# The script now auto-syncs, but you can manually sync first if preferred
python scripts/sync_early_access_users.py

# Send reminders (will auto-sync during query)
python scripts/send_reminders_to_early_access.py
```

**Periodic health checks:**
```bash
# Run integrity queries monthly
psql $DATABASE_URL -f scripts/verify_early_access_integrity.sql
```

---

## Database Schema

### early_access_users Table

```sql
CREATE TABLE early_access_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    first_name TEXT,
    trial_days INTEGER DEFAULT 30,
    status TEXT DEFAULT 'invited' CHECK (status IN ('invited', 'signed_up', 'expired')),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    signed_up_at TIMESTAMPTZ,
    invite_sent_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);
```

### Key Fields

- **email**: Unique identifier for matching with auth.users
- **user_id**: Foreign key to auth.users (populated on signup)
- **status**: 'invited' | 'signed_up' | 'expired'
- **signed_up_at**: Timestamp when user signed up
- **metadata**: JSON field for tracking sync info
  ```json
  {
    "last_sync_check": "2026-01-15T10:30:00Z",
    "sync_source": "trigger|script|auto_reminder_script"
  }
  ```

---

## Troubleshooting

### Issue: Users marked 'invited' but already signed up

**Solution:**
```bash
python scripts/sync_early_access_users.py
```

### Issue: Trigger not firing

**Check:**
```sql
-- Verify trigger exists
SELECT * FROM information_schema.triggers 
WHERE trigger_name = 'on_auth_user_created';

-- Check function exists
SELECT proname FROM pg_proc 
WHERE proname = 'sync_early_access_signup';
```

**Fix:**
```bash
# Reapply migration
psql $DATABASE_URL -f db/migrations/006_sync_early_access_trigger.sql
```

### Issue: Duplicate emails

**Check:**
```sql
SELECT email, COUNT(*) 
FROM early_access_users 
GROUP BY email 
HAVING COUNT(*) > 1;
```

**Fix:**
```sql
-- Keep the most recent record
DELETE FROM early_access_users
WHERE id NOT IN (
    SELECT DISTINCT ON (email) id
    FROM early_access_users
    ORDER BY email, invited_at DESC
);
```

---

## Monitoring

### Key Metrics to Track

1. **Conversion Rate**
   ```sql
   SELECT 
       ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'signed_up') / COUNT(*), 2) as conversion_rate
   FROM early_access_users;
   ```

2. **Sync Source Distribution**
   ```sql
   SELECT 
       metadata->>'sync_source' as source,
       COUNT(*)
   FROM early_access_users
   WHERE status = 'signed_up'
   GROUP BY metadata->>'sync_source';
   ```

3. **Average Time to Signup**
   ```sql
   SELECT 
       AVG(EXTRACT(EPOCH FROM (signed_up_at - invited_at))/3600) as avg_hours
   FROM early_access_users
   WHERE status = 'signed_up';
   ```

---

## Best Practices

1. **Always run dry-run first**
   ```bash
   python scripts/sync_early_access_users.py --dry-run
   ```

2. **Verify before major campaigns**
   ```bash
   psql $DATABASE_URL -f scripts/verify_early_access_integrity.sql
   ```

3. **Monitor sync sources**
   - If most syncs are from 'script' or 'auto_reminder_script', trigger may not be working

4. **Regular health checks**
   - Run integrity queries monthly
   - Check for data inconsistencies

5. **Backup before bulk operations**
   ```bash
   pg_dump $DATABASE_URL -t early_access_users > backup.sql
   ```

---

## Future Enhancements

- [ ] Add email notification when sync fails
- [ ] Create dashboard for conversion metrics
- [ ] Implement A/B testing for reminder timing
- [ ] Add webhook for external CRM sync
- [ ] Track reminder open/click rates
