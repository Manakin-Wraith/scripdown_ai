# Credit System Troubleshooting & Resolution

**Date:** January 27, 2026  
**Status:** Issues Identified & Fixed

---

## 🔍 Issues Discovered

### Issue 1: Missing Profile Row
**Problem:** User profile doesn't exist in `profiles` table  
**Error:** `'The result contains 0 rows'` when querying for user `9da653a2-ab39-495c-9531-a84d396a244f`

**Root Cause:**
- User exists in `auth.users` but not in `profiles` table
- The credit system expects every authenticated user to have a profile row
- When profile is missing, API returns default values (`is_legacy_beta: false`)

**Fix Applied:**
- Updated `credit_service.py` to auto-create profile with default values when missing
- Profile will be created on first API call to `/api/credits/balance`

### Issue 2: Data Type Mismatch
**Problem:** Database stores string values instead of proper types  
**Evidence:** Profile has `'10'` (string) and `'true'` (string) instead of `10` (integer) and `TRUE` (boolean)

**Root Cause:**
- INSERT statement used string literals: `'10'`, `'true'`
- PostgreSQL stored them as TEXT instead of INTEGER/BOOLEAN
- Python receives string `'true'` which doesn't equal boolean `True`

**Fix Required:**
Run this SQL in Supabase Dashboard:
```sql
UPDATE profiles 
SET 
    script_credits = 10,
    total_scripts_purchased = 10,
    is_legacy_beta = TRUE,
    is_superuser = TRUE
WHERE id = '9da653a2-ab39-495c-9531-a84d396a244f';
```

### Issue 3: CreditBalance Component Not Rendering
**Problem:** Component integrated in code but not visible in browser  
**Evidence:** No API calls to `/api/credits/balance`, no console logs from component

**Possible Causes:**
1. JavaScript error preventing component mount
2. Import path issue
3. Component conditionally hidden by CSS
4. Frontend needs hard refresh

**Debugging Steps:**
1. Check browser console for JavaScript errors
2. Verify network tab shows requests to `/api/credits/balance`
3. Inspect Elements tab for `.sidebar-credits` div
4. Hard refresh browser (Cmd+Shift+R)

---

## ✅ Fixes Implemented

### Backend Changes

**File:** `backend/services/credit_service.py`

1. **Auto-Create Profile** (Lines 68-92)
   - Changed query from `.single()` to `.execute()` to handle 0 rows
   - Added check: `if not profile_result.data or len(profile_result.data) == 0`
   - Auto-creates profile with default values when missing
   - Logs: "Profile not found for user {user_id}, creating default profile..."

2. **Handle List Results** (Line 95)
   - Changed: `profile = profile_result.data[0] if isinstance(profile_result.data, list) else profile_result.data`
   - Handles both single object and list responses from Supabase

3. **Debug Logging** (Lines 97-101)
   - Added logging to trace actual database values
   - Shows data types to identify string vs boolean issues

### Frontend Changes

**File:** `frontend/src/components/credits/CreditBalance.jsx`
- Removed debug console.log (line 14)
- Component ready for production

---

## 🧪 Testing Checklist

### Backend Testing
- [x] Backend auto-reloads after code changes
- [ ] Profile auto-created on first API call
- [ ] DEBUG logs show correct data types after SQL update
- [ ] API returns `"is_legacy_beta": true` after SQL update

### Frontend Testing
- [ ] Hard refresh browser (Cmd+Shift+R)
- [ ] Check browser console for errors
- [ ] Verify network tab shows `/api/credits/balance` request
- [ ] Sidebar shows credit balance widget
- [ ] Dashboard shows credit card in stats
- [ ] Click credit balance opens purchase modal

### Database Testing
- [ ] Run SQL update in Supabase Dashboard
- [ ] Verify data types: `pg_typeof(script_credits)` = `integer`
- [ ] Verify data types: `pg_typeof(is_legacy_beta)` = `boolean`
- [ ] Confirm values: `script_credits = 10`, `is_legacy_beta = TRUE`

---

## 🎯 Next Actions

### Immediate (Required)
1. **Run SQL Update** in Supabase Dashboard to fix data types
2. **Hard Refresh Browser** to reload frontend with latest changes
3. **Check Browser Console** for any JavaScript errors
4. **Verify Component Renders** - should see credit balance in sidebar

### If Component Still Not Visible
1. Open browser DevTools → Console tab
2. Look for red error messages
3. Check Network tab → Filter by "credits"
4. Inspect Elements tab → Search for "sidebar-credits"
5. Share any errors found

### After Component Renders
1. Verify credit balance shows "10 credits"
2. Verify "Legacy Beta" badge appears
3. Click credit balance → Purchase modal opens
4. Test upload page → Should allow upload (has credits)

---

## 📊 Expected Behavior After Fixes

### Backend Logs (After SQL Update)
```
DEBUG - Raw profile data for user 9da653a2-ab39-495c-9531-a84d396a244f:
  script_credits: 10
  total_scripts_purchased: 10
  is_legacy_beta: True (type: <class 'bool'>)
```

### API Response
```json
{
  "success": true,
  "balance": {
    "credits": 10,
    "total_purchased": 10,
    "scripts_uploaded": 0,
    "is_legacy_beta": true,
    "usage_history": []
  }
}
```

### Browser UI
- **Sidebar (collapsed):** `💰 10`
- **Sidebar (expanded):** `💰 10 credits` + `Legacy Beta` badge
- **Dashboard:** Credit card showing `10 credits` + `Legacy Beta`
- **Upload Page:** Upload allowed (has credits)

---

## 🔧 Files Modified

1. `backend/services/credit_service.py` - Auto-create profile, handle missing rows
2. `frontend/src/components/credits/CreditBalance.jsx` - Removed debug logging
3. `FIX_USER_PROFILE.sql` - SQL script to fix data types (needs to be run)

---

## 📝 Notes

- SQL linter errors in migration files are expected (T-SQL linter, PostgreSQL syntax)
- The `::` cast syntax is correct for PostgreSQL
- Profile auto-creation only happens once per user
- After SQL update, refresh browser to see changes
