# Credit System Deployment Checklist

**Date:** January 27, 2026  
**Feature:** Pay-Per-Script Credit System (R49/script)

---

## ⚠️ Pre-Deployment Status

### Database Migration Status: ❌ NOT RUN
The credit system tables and columns **do not exist yet** in the database.

---

## 📋 Deployment Steps (In Order)

### Step 1: Run Database Migrations ⏳

**Location:** Supabase SQL Editor  
**Order:** Run these migrations in sequence

#### 1.1 Create Credit System Tables
```bash
# File: backend/db/migrations/005_script_credits_system.sql
# This creates:
# - script_credit_purchases table
# - script_credit_usage table
# - Adds columns to profiles: script_credits, total_scripts_purchased, is_legacy_beta
# - Creates database functions: deduct_script_credit(), add_script_credits()
```

**Action Required:**
1. Open Supabase Dashboard → SQL Editor
2. Copy entire contents of `005_script_credits_system.sql`
3. Execute the migration
4. Verify success (no errors)

**Verification Query:**
```sql
-- Check if columns exist
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'profiles' 
  AND column_name IN ('script_credits', 'total_scripts_purchased', 'is_legacy_beta');

-- Expected: 3 rows returned
```

#### 1.2 Grandfather Existing Users
```bash
# File: backend/db/migrations/014_grandfather_existing_users.sql
# This grants 10 free credits to all existing active users
```

**Action Required:**
1. In Supabase SQL Editor
2. Copy entire contents of `014_grandfather_existing_users.sql`
3. Execute the migration
4. Verify users received credits

**Verification Query:**
```sql
-- Check legacy users
SELECT 
    COUNT(*) as total_legacy_users,
    SUM(script_credits) as total_credits_granted
FROM profiles 
WHERE is_legacy_beta = TRUE;

-- Expected: Shows count of existing users and total credits (count * 10)
```

---

### Step 2: Backend Configuration ✅ DONE

#### 2.1 Disable Phase 1 Free Access ✅
- **File:** `backend/services/subscription_service.py`
- **Status:** ✅ Changed `PHASE1_FREE_ACCESS = False`

#### 2.2 Register Credit Routes ✅
- **File:** `backend/app.py`
- **Status:** ✅ `app.register_blueprint(credit_bp)` added at line 46

---

### Step 3: Create Yoco Payment Links ⏳

**Action Required:**
1. Log into Yoco Dashboard
2. Create 4 payment links with these details:

| Package | Amount | Link Name | Redirect URL |
|---------|--------|-----------|--------------|
| Single | R49.00 | slateone-1-script | `https://app.slateone.studio/purchase-success?package=single` |
| Pack 5 | R220.00 | slateone-5-scripts | `https://app.slateone.studio/purchase-success?package=pack_5` |
| Pack 10 | R390.00 | slateone-10-scripts | `https://app.slateone.studio/purchase-success?package=pack_10` |
| Pack 25 | R860.00 | slateone-25-scripts | `https://app.slateone.studio/purchase-success?package=pack_25` |

**Current Status:**
- ✅ Placeholder links already in `CreditPurchaseModal.jsx`
- ⚠️ Need to verify these are actual Yoco payment links

**Verification:**
```javascript
// frontend/src/components/credits/CreditPurchaseModal.jsx
const YOCO_PAYLINKS = {
    single: 'https://pay.yoco.com/r/4aQyxM',
    pack_5: 'https://pay.yoco.com/r/4W9Vev',
    pack_10: 'https://pay.yoco.com/r/78j6rk',
    pack_25: 'https://pay.yoco.com/r/2Q1ZLN'
};
```

---

### Step 4: Frontend Integration ⏳

#### 4.1 Update ScriptUpload Component
**File:** `frontend/src/components/script/ScriptUpload.jsx`

**Required Changes:**
```javascript
import { useCredits } from '../../hooks/useCredits';

// Inside component
const { credits, canUpload, deductCredit } = useCredits();

// Before upload - check credits
const hasCredits = await canUpload();
if (!hasCredits) {
    // Show purchase modal
    return;
}

// After successful upload - deduct credit
await deductCredit(scriptId, scriptName);
```

**Status:** ⏳ NOT IMPLEMENTED YET

#### 4.2 Add CreditBalance to Sidebar
**File:** `frontend/src/components/layout/Sidebar.jsx`

**Required Changes:**
```javascript
import { CreditBalance } from '../credits';
import { useState } from 'react';
import { CreditPurchaseModal } from '../credits';

// Inside component
const [showPurchaseModal, setShowPurchaseModal] = useState(false);

// In JSX
<CreditBalance 
    compact={true}
    onClick={() => setShowPurchaseModal(true)} 
/>

<CreditPurchaseModal 
    isOpen={showPurchaseModal}
    onClose={() => setShowPurchaseModal(false)}
/>
```

**Status:** ⏳ NOT IMPLEMENTED YET

#### 4.3 Add CreditBalance to Dashboard
**File:** `frontend/src/pages/Dashboard.jsx`

**Required Changes:**
```javascript
import { CreditBalance } from '../components/credits';

// In JSX (in stats section)
<CreditBalance 
    compact={false}
    onClick={handleBuyCredits}
/>
```

**Status:** ⏳ NOT IMPLEMENTED YET

---

### Step 5: Backend Deployment ⏳

**Action Required:**
1. Restart backend server to load new routes
2. Verify credit endpoints are accessible

**Verification:**
```bash
# Test credit balance endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5000/api/credits/balance

# Expected: JSON with credits, totalPurchased, etc.
```

---

### Step 6: Frontend Deployment ⏳

**Action Required:**
```bash
cd frontend
npm run build
# Deploy to Vercel/Netlify
```

---

### Step 7: Send User Communication Email ⏳

**Template Location:** `docs/CREDIT_SYSTEM_IMPLEMENTATION.md` (Section: Legacy User Migration)

**Action Required:**
1. Prepare email list of all existing users
2. Send announcement email about:
   - New credit system
   - 10 free credits granted
   - Pricing structure
   - How to purchase more credits

---

## 🧪 Testing Checklist

### Backend Tests
- [ ] Migration 005 runs successfully
- [ ] Migration 014 grants credits to existing users
- [ ] `GET /api/credits/balance` returns correct data
- [ ] `GET /api/credits/can-upload` checks credits correctly
- [ ] `POST /api/credits/deduct` deducts credit atomically
- [ ] `GET /api/credits/packages` returns all 4 packages
- [ ] `POST /api/credits/purchase/create` creates purchase record
- [ ] `POST /api/credits/purchase/{id}/complete` adds credits

### Frontend Tests
- [ ] `useCredits` hook fetches balance on mount
- [ ] `CreditBalance` component displays correctly
- [ ] `CreditPurchaseModal` shows all 4 packages
- [ ] Package selection redirects to Yoco
- [ ] Upload blocked when credits = 0
- [ ] Upload deducts credit after success
- [ ] Balance updates after deduction
- [ ] Legacy badge shows for grandfathered users

### Integration Tests
- [ ] Full purchase flow: create → pay → complete → credits added
- [ ] Full upload flow: check → upload → deduct → verify
- [ ] Legacy user has 10 credits after migration
- [ ] New user has 0 credits
- [ ] Concurrent uploads don't cause race conditions

---

## 📊 Current Implementation Status

### ✅ Completed
1. Database migration scripts created
2. Backend service (`credit_service.py`) implemented
3. Backend routes (`credit_routes.py`) implemented
4. Frontend hook (`useCredits.js`) created
5. Frontend components (`CreditBalance`, `CreditPurchaseModal`) created
6. Documentation (`CREDIT_SYSTEM_IMPLEMENTATION.md`) written
7. Backend configuration updated (`PHASE1_FREE_ACCESS = False`)
8. Credit routes registered in `app.py`
9. Yoco payment links configured in modal

### ⏳ Pending
1. **Run database migrations** (CRITICAL - blocks everything else)
2. **Verify Yoco payment links** are active
3. **Integrate credit check in ScriptUpload**
4. **Add CreditBalance to Sidebar**
5. **Add CreditBalance to Dashboard**
6. **Test full flow locally**
7. **Deploy backend**
8. **Deploy frontend**
9. **Send user communication email**

---

## 🚨 Critical Path

**You cannot test the frontend until:**
1. ✅ Database migrations are run (creates tables/columns)
2. ✅ Existing users are grandfathered (have credits to test with)
3. ⏳ Frontend components are integrated into upload flow

**Next Immediate Actions:**
1. Run migration `005_script_credits_system.sql` in Supabase
2. Run migration `014_grandfather_existing_users.sql` in Supabase
3. Verify migrations with SQL queries above
4. Integrate `useCredits` into `ScriptUpload.jsx`
5. Add `CreditBalance` to `Sidebar.jsx` and `Dashboard.jsx`
6. Test locally

---

## 📝 Notes

- SQL linter errors in migration files are **expected** (PostgreSQL vs T-SQL syntax)
- The migration is **idempotent** (safe to run multiple times)
- Legacy users get 10 credits = R490 value
- New users start with 0 credits
- All credit operations are **atomic** (no race conditions)

---

## 🆘 Troubleshooting

**Issue:** Migration fails  
**Solution:** Check Supabase logs, verify syntax, ensure no conflicting columns

**Issue:** Users don't have credits after migration  
**Solution:** Run verification query, check `subscription_status` and `created_at` filters

**Issue:** Credit routes return 404  
**Solution:** Verify `credit_bp` is registered in `app.py`, restart backend

**Issue:** Frontend can't fetch credits  
**Solution:** Check CORS settings, verify auth token, check network tab

---

## ✅ Sign-Off

- [ ] Database migrations run successfully
- [ ] Existing users have 10 credits
- [ ] Backend endpoints tested
- [ ] Frontend components integrated
- [ ] Full flow tested locally
- [ ] Deployed to production
- [ ] User communication sent

**Deployment Lead:** _________________  
**Date:** _________________
