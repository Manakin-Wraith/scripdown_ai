# Supabase Storage Setup for Feedback Screenshots

## Overview
This guide covers setting up the `feedback-screenshots` bucket in Supabase Storage for the Feedback Feature.

---

## 🪣 Bucket Configuration

### Step 1: Create Bucket
1. Go to **Supabase Dashboard** → Your Project
2. Navigate to **Storage** in the left sidebar
3. Click **"New bucket"**
4. Configure:
   - **Name**: `feedback-screenshots`
   - **Public bucket**: ✅ Enabled (for easy viewing by admins)
   - **File size limit**: 5 MB
   - **Allowed MIME types**: `image/png, image/jpeg, image/jpg, image/webp`

### Step 2: Set Bucket Policies

#### Policy 1: Authenticated Upload
Allows authenticated users to upload their own screenshots.

**Via Dashboard:**
- Policy name: `Authenticated users can upload screenshots`
- Allowed operation: INSERT
- Target roles: `authenticated`
- WITH CHECK expression: `bucket_id = 'feedback-screenshots'`

**Via SQL:**
```sql
CREATE POLICY "Authenticated users can upload screenshots"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'feedback-screenshots');
```

#### Policy 2: Public Read
Allows anyone with the URL to view screenshots (needed for admin dashboard).

**Via Dashboard:**
- Policy name: `Public read access`
- Allowed operation: SELECT
- Target roles: `public`
- USING expression: `bucket_id = 'feedback-screenshots'`

**Via SQL:**
```sql
CREATE POLICY "Public read access"
ON storage.objects
FOR SELECT
TO public
USING (bucket_id = 'feedback-screenshots');
```

#### Policy 3: User Delete Own Files
Allows users to delete their own uploaded screenshots.

**Via Dashboard:**
- Policy name: `Users can delete own screenshots`
- Allowed operation: DELETE
- Target roles: `authenticated`
- USING expression: `bucket_id = 'feedback-screenshots' AND auth.uid()::text = (storage.foldername(name))[1]`

**Via SQL:**
```sql
CREATE POLICY "Users can delete own screenshots"
ON storage.objects
FOR DELETE
TO authenticated
USING (
  bucket_id = 'feedback-screenshots' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);
```

#### Policy 4: Superuser Full Access
Allows superusers to manage all screenshots.

**Via Dashboard:**
- Policy name: `Superusers can manage all screenshots`
- Allowed operation: ALL
- Target roles: `authenticated`
- USING expression: 
  ```sql
  bucket_id = 'feedback-screenshots' 
  AND EXISTS (
    SELECT 1 FROM public.profiles
    WHERE profiles.id = auth.uid()
    AND profiles.is_superuser = true
  )
  ```

**Via SQL:**
```sql
CREATE POLICY "Superusers can manage all screenshots"
ON storage.objects
FOR ALL
TO authenticated
USING (
  bucket_id = 'feedback-screenshots' 
  AND EXISTS (
    SELECT 1 FROM public.profiles
    WHERE profiles.id = auth.uid()
    AND profiles.is_superuser = true
  )
);
```

---

## 📁 File Naming Convention

Screenshots will be stored with the following path structure:
```
feedback-screenshots/
  └── {user_id}/
      └── {feedback_id}_{timestamp}.{ext}
```

**Example**:
```
feedback-screenshots/550e8400-e29b-41d4-a716-446655440000/abc123_1706432100000.png
```

This structure:
- ✅ Organizes files by user
- ✅ Prevents naming conflicts
- ✅ Enables easy cleanup
- ✅ Supports RLS policies

---

## 🔒 Security Considerations

### File Size Limit
- **Max size**: 5 MB per file
- **Enforced by**: Supabase Storage + Frontend validation
- **Reason**: Prevent abuse and storage costs

### MIME Type Validation
- **Allowed**: `image/png`, `image/jpeg`, `image/jpg`, `image/webp`
- **Blocked**: All other file types
- **Enforced by**: Supabase Storage + Frontend validation

### Access Control
- **Upload**: Only authenticated users
- **Read**: Public (anyone with URL)
- **Delete**: User (own files) + Superusers (all files)
- **Update**: Not allowed (immutable)

### Rate Limiting
- Handled at API level (5 feedback submissions per day)
- Prevents screenshot spam

---

## 🧪 Testing the Setup

### Test 1: Upload as Authenticated User
```javascript
import { supabase } from './supabase';

const file = new File(['test'], 'test.png', { type: 'image/png' });
const userId = 'your-user-id';
const feedbackId = 'test-feedback-id';
const timestamp = Date.now();

const { data, error } = await supabase.storage
  .from('feedback-screenshots')
  .upload(`${userId}/${feedbackId}_${timestamp}.png`, file);

console.log(data, error);
// Expected: data with path, no error
```

### Test 2: Get Public URL
```javascript
const { data } = supabase.storage
  .from('feedback-screenshots')
  .getPublicUrl('path/to/file.png');

console.log(data.publicUrl);
// Expected: https://[project].supabase.co/storage/v1/object/public/...
```

### Test 3: Delete Own File
```javascript
const { error } = await supabase.storage
  .from('feedback-screenshots')
  .remove([`${userId}/${feedbackId}_${timestamp}.png`]);

console.log(error);
// Expected: null (no error)
```

---

## 🛠️ Troubleshooting

### Issue: "new row violates row-level security policy"
**Cause**: RLS policies not set correctly  
**Fix**: Verify policies in Supabase Dashboard → Storage → feedback-screenshots → Policies

### Issue: "File size exceeds limit"
**Cause**: File > 5MB  
**Fix**: Compress image before upload or reject in frontend

### Issue: "Invalid MIME type"
**Cause**: Non-image file uploaded  
**Fix**: Validate file type in frontend before upload

### Issue: "Public URL not working"
**Cause**: Bucket not set to public  
**Fix**: Enable "Public bucket" in bucket settings

---

## 📊 Storage Monitoring

### View Storage Usage
```sql
-- Total storage used by feedback screenshots
SELECT 
  bucket_id,
  COUNT(*) as file_count,
  SUM(metadata->>'size')::bigint as total_bytes,
  pg_size_pretty(SUM(metadata->>'size')::bigint) as total_size
FROM storage.objects
WHERE bucket_id = 'feedback-screenshots'
GROUP BY bucket_id;
```

### List Files by User
```sql
-- Files uploaded by specific user
SELECT 
  name,
  metadata->>'size' as size_bytes,
  created_at
FROM storage.objects
WHERE bucket_id = 'feedback-screenshots'
  AND name LIKE 'user-id-here/%'
ORDER BY created_at DESC;
```

---

## 🧹 Cleanup Strategy

### Orphaned Files
Files may become orphaned if feedback is deleted but screenshot remains.

**Cleanup Script** (run monthly):
```sql
-- Find screenshots without corresponding feedback
SELECT o.name
FROM storage.objects o
WHERE o.bucket_id = 'feedback-screenshots'
  AND NOT EXISTS (
    SELECT 1 FROM feedback_submissions f
    WHERE f.screenshot_url LIKE '%' || o.name
  );

-- Delete orphaned files (run after verification)
DELETE FROM storage.objects
WHERE bucket_id = 'feedback-screenshots'
  AND NOT EXISTS (
    SELECT 1 FROM feedback_submissions f
    WHERE f.screenshot_url LIKE '%' || name
  );
```

### Old Resolved Feedback
Consider archiving screenshots for resolved feedback older than 90 days.

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Bucket `feedback-screenshots` exists
- [ ] Bucket is set to **Public**
- [ ] File size limit is **5 MB**
- [ ] Allowed MIME types configured
- [ ] 4 RLS policies created and enabled
- [ ] Test upload works (authenticated user)
- [ ] Test public URL works
- [ ] Test delete works (own files)
- [ ] Superuser can access all files

---

## 🔗 Related Documentation

- [Supabase Storage Documentation](https://supabase.com/docs/guides/storage)
- [Storage RLS Policies](https://supabase.com/docs/guides/storage/security/access-control)
- [Feedback Feature Task Document](./FEEDBACK_FEATURE_TASK.md)

---

**Last Updated**: 2026-01-28  
**Status**: Ready for Implementation
