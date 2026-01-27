# Credit-Based Pay-Per-Script System Implementation

**Date:** January 27, 2026  
**Model:** Option A - Credit-Based System  
**Pricing:** R49 per script, with volume discounts

---

## Overview

Implemented a credit-based payment system where users purchase credits in packages to upload scripts. Each script upload consumes 1 credit. This replaces the previous unlimited upload model for users who had full access.

---

## Pricing Structure

| Package | Credits | Price | Per Script | Savings |
|---------|---------|-------|------------|---------|
| Single | 1 | R49.00 | R49.00 | - |
| Pack 5 | 5 | R220.00 | R44.00 | 10% |
| Pack 10 | 10 | R390.00 | R39.00 | 20% |
| Pack 25 | 25 | R860.00 | R34.40 | 30% |

---

## Database Schema

### New Tables

#### `script_credit_purchases`
Tracks credit package purchases.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | References auth.users |
| email | TEXT | User's email |
| credits_purchased | INTEGER | Number of credits in package |
| package_type | TEXT | single, pack_5, pack_10, pack_25 |
| amount | DECIMAL(10,2) | Payment amount |
| currency | TEXT | Default 'ZAR' |
| payment_reference | TEXT | Unique payment reference |
| yoco_payment_id | TEXT | Yoco transaction ID |
| status | TEXT | pending, completed, failed, refunded |
| metadata | JSONB | Additional data |
| created_at | TIMESTAMPTZ | Purchase creation |
| paid_at | TIMESTAMPTZ | Payment completion |
| credits_added_at | TIMESTAMPTZ | When credits were added |

#### `script_credit_usage`
Logs credit consumption per script upload.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | References auth.users |
| script_id | UUID | References scripts |
| credits_used | INTEGER | Always 1 per script |
| script_name | TEXT | Script name for reference |
| created_at | TIMESTAMPTZ | Usage timestamp |

### Extended Tables

#### `profiles` (new columns)
| Column | Type | Description |
|--------|------|-------------|
| script_credits | INTEGER | Current available credits |
| total_scripts_purchased | INTEGER | Lifetime credits purchased |
| is_legacy_beta | BOOLEAN | Flag for grandfathered users |

---

## Database Functions

### `deduct_script_credit(p_user_id, p_script_id, p_script_name)`
Atomically deducts 1 credit and logs usage.
- Returns: BOOLEAN (success/failure)
- Transaction-safe with row locking

### `add_script_credits(p_user_id, p_credits, p_purchase_id)`
Adds credits after successful payment.
- Returns: BOOLEAN (success/failure)
- Updates profile and marks purchase as completed

---

## Backend Implementation

### Files Created

#### `backend/db/migrations/005_script_credits_system.sql`
Complete migration with:
- Table creation
- Indexes for performance
- RLS policies
- Helper functions
- Analytics view

#### `backend/services/credit_service.py`
Core credit management service:
- `get_credit_balance(user_id)` - Get balance and stats
- `can_upload_with_credits(user_id)` - Check upload permission
- `deduct_credit_for_script(user_id, script_id, script_name)` - Consume credit
- `add_credits_after_purchase(user_id, credits, purchase_id)` - Add credits
- `create_credit_purchase(...)` - Create purchase record
- `complete_credit_purchase(purchase_id)` - Complete purchase
- `get_purchase_history(user_id)` - Purchase history
- `grant_legacy_credits(user_id, credits)` - Grant to existing users

#### `backend/routes/credit_routes.py`
API endpoints:
- `GET /api/credits/balance` - Get user balance
- `GET /api/credits/can-upload` - Check upload permission
- `POST /api/credits/deduct` - Deduct credit for upload
- `GET /api/credits/packages` - Get available packages
- `POST /api/credits/purchase/create` - Create purchase
- `POST /api/credits/purchase/<id>/complete` - Complete purchase
- `GET /api/credits/purchase/history` - Purchase history
- `POST /api/credits/admin/grant-legacy` - Admin: grant credits

---

## Frontend Implementation

### Files Created

#### `frontend/src/hooks/useCredits.js`
React hook for credit management:
- `credits` - Current balance
- `totalPurchased` - Lifetime total
- `scriptsUploaded` - Usage count
- `isLegacyBeta` - Legacy user flag
- `usageHistory` - Recent usage
- `fetchBalance()` - Refresh balance
- `canUpload()` - Check permission
- `deductCredit(scriptId, scriptName)` - Consume credit
- `getPackages()` - Get pricing
- `createPurchase(packageType)` - Initiate purchase

#### `frontend/src/components/credits/CreditBalance.jsx`
Credit balance display widget:
- Shows current credits
- Color-coded states (normal, low, empty)
- Legacy beta badge
- Compact mode for sidebar
- Click to open purchase modal

#### `frontend/src/components/credits/CreditPurchaseModal.jsx`
Package selection modal:
- Grid layout with 4 packages
- Visual hierarchy (Popular, Best Value badges)
- Per-script pricing display
- Savings percentage
- Redirect to Yoco payment links

#### `frontend/src/components/credits/CreditBalance.css`
Styling for balance widget

#### `frontend/src/components/credits/CreditPurchaseModal.css`
Styling for purchase modal

#### `frontend/src/components/credits/index.js`
Barrel export

---

## Integration Points

### 1. Disable Phase 1 Free Access
```python
# backend/services/subscription_service.py
PHASE1_FREE_ACCESS = False  # Change from True
```

### 2. Register Credit Routes
```python
# backend/app.py
from routes.credit_routes import credit_bp
app.register_blueprint(credit_bp)
```

### 3. Update ScriptUpload Component
```javascript
// frontend/src/components/script/ScriptUpload.jsx
import { useCredits } from '../../hooks/useCredits';

// Check credits before upload
const { credits, canUpload, deductCredit } = useCredits();

// After successful upload
await deductCredit(scriptId, scriptName);
```

### 4. Add Credit Balance to Sidebar
```javascript
// frontend/src/components/layout/Sidebar.jsx
import { CreditBalance } from '../credits';

<CreditBalance onClick={() => setShowPurchaseModal(true)} />
```

### 5. Add Credit Balance to Dashboard
```javascript
// frontend/src/pages/Dashboard.jsx
import { CreditBalance } from '../components/credits';

<CreditBalance compact={false} onClick={handleBuyCredits} />
```

---

## Yoco Payment Integration

### Payment Links (To Be Created)

| Package | URL |
|---------|-----|
| Single (R49) | `https://pay.yoco.com/slateone-1-script` |
| Pack 5 (R220) | `https://pay.yoco.com/slateone-5-scripts` |
| Pack 10 (R390) | `https://pay.yoco.com/slateone-10-scripts` |
| Pack 25 (R860) | `https://pay.yoco.com/slateone-25-scripts` |

### Payment Flow

1. User clicks package in `CreditPurchaseModal`
2. Frontend calls `POST /api/credits/purchase/create`
3. Backend creates purchase record with `status='pending'`
4. Frontend redirects to Yoco paylink
5. User completes payment on Yoco
6. Yoco redirects to `/purchase-success?package={type}`
7. Frontend calls `POST /api/credits/purchase/{id}/complete`
8. Backend adds credits via `add_script_credits()` function
9. User sees updated balance

### Webhook (Optional Enhancement)
For automatic credit addition without user return:
- Yoco webhook → `POST /api/credits/purchase/{id}/complete`
- Verify payment signature
- Add credits automatically

---

## Legacy User Migration

### Grandfather Existing Users

Run this SQL to grant 10 free credits to all current users:

```sql
UPDATE profiles 
SET 
    script_credits = 10,
    total_scripts_purchased = 10,
    is_legacy_beta = TRUE
WHERE subscription_status = 'active' 
  AND created_at < '2026-02-01'
  AND script_credits = 0;
```

### Communication Email

**Subject:** Thank You for Being an Early Adopter!

**Body:**
> Hi [Name],
>
> As a valued early adopter of SlateOne, we want to thank you for your support!
>
> We're introducing a new credit system where each script upload requires 1 credit. To show our appreciation, **we've added 10 free credits to your account** – that's R490 worth of uploads on us!
>
> **Your Credits:** 10 free credits  
> **After that:** R49 per script, or buy in bulk to save up to 30%
>
> [View Credit Packages]
>
> Thank you for being part of our journey!
>
> The SlateOne Team

---

## Testing Checklist

### Backend Tests
- [ ] Migration runs successfully on Supabase
- [ ] `deduct_script_credit()` function works atomically
- [ ] `add_script_credits()` function updates correctly
- [ ] Credit balance API returns correct data
- [ ] Purchase creation works
- [ ] Purchase completion adds credits
- [ ] RLS policies prevent unauthorized access

### Frontend Tests
- [ ] `useCredits` hook fetches balance
- [ ] `CreditBalance` displays correctly
- [ ] `CreditPurchaseModal` shows packages
- [ ] Package selection redirects to Yoco
- [ ] Upload blocked when credits = 0
- [ ] Upload deducts credit successfully
- [ ] Balance updates after deduction
- [ ] Legacy beta badge shows for grandfathered users

### Integration Tests
- [ ] Full purchase flow (create → pay → complete → credits added)
- [ ] Upload flow (check credits → upload → deduct → verify)
- [ ] Legacy user has 10 credits
- [ ] New user has 0 credits
- [ ] Credit deduction is atomic (no race conditions)

---

## Deployment Steps

### 1. Database Migration
```bash
# In Supabase SQL Editor
# Run: backend/db/migrations/005_script_credits_system.sql
```

### 2. Backend Deployment
```bash
# Update subscription service
# Set PHASE1_FREE_ACCESS = False

# Register credit routes in app.py
# Deploy backend
```

### 3. Create Yoco Payment Links
- Create 4 paylinks in Yoco dashboard
- Set redirect URLs to `/purchase-success?package={type}`
- Update `YOCO_PAYLINKS` in `CreditPurchaseModal.jsx`

### 4. Grant Legacy Credits
```sql
-- Run migration script for existing users
UPDATE profiles SET script_credits = 10, is_legacy_beta = TRUE WHERE ...
```

### 5. Frontend Deployment
```bash
# Deploy frontend with new components
npm run build
# Deploy to Vercel/Netlify
```

### 6. Send Communication Email
- Send email to all existing users
- Announce credit system
- Highlight 10 free credits

---

## Monitoring & Analytics

### Key Metrics to Track

1. **Credit Balance Distribution**
   - How many users have 0, 1-5, 6-10, 10+ credits

2. **Package Popularity**
   - Which packages sell most
   - Average credits purchased per user

3. **Conversion Rate**
   - Users who hit 0 credits → purchase rate
   - Time to first purchase

4. **Revenue Metrics**
   - Total revenue from credit sales
   - Average revenue per user
   - Monthly recurring credit purchases

### Analytics Queries

```sql
-- Credit balance distribution
SELECT 
    CASE 
        WHEN script_credits = 0 THEN '0 credits'
        WHEN script_credits BETWEEN 1 AND 5 THEN '1-5 credits'
        WHEN script_credits BETWEEN 6 AND 10 THEN '6-10 credits'
        ELSE '10+ credits'
    END as balance_range,
    COUNT(*) as user_count
FROM profiles
GROUP BY balance_range;

-- Package sales summary
SELECT 
    package_type,
    COUNT(*) as purchases,
    SUM(credits_purchased) as total_credits_sold,
    SUM(amount) as total_revenue
FROM script_credit_purchases
WHERE status = 'completed'
GROUP BY package_type;

-- Top spenders
SELECT 
    p.email,
    p.full_name,
    p.total_scripts_purchased,
    COUNT(scp.id) as purchase_count,
    SUM(scp.amount) as total_spent
FROM profiles p
LEFT JOIN script_credit_purchases scp ON p.id = scp.user_id
WHERE scp.status = 'completed'
GROUP BY p.id, p.email, p.full_name, p.total_scripts_purchased
ORDER BY total_spent DESC
LIMIT 20;
```

---

## Future Enhancements

1. **Subscription Model**
   - Monthly subscription (R99/month) includes 3 credits
   - Additional credits at R39 each

2. **Credit Expiry**
   - Optional: Credits expire after 12 months
   - Encourages regular usage

3. **Referral Program**
   - Give 1 free credit for each referral signup
   - Referrer gets 1 credit when referee makes first purchase

4. **Team Credits**
   - Shared credit pool for team accounts
   - Admin can allocate credits to team members

5. **Auto-Reload**
   - Automatically purchase credits when balance hits 0
   - Saved payment method

---

## Support & Troubleshooting

### Common Issues

**Issue:** User says they paid but credits not added  
**Solution:** Check `script_credit_purchases` table for status. If `pending`, manually run `complete_credit_purchase(purchase_id)`.

**Issue:** Credit deduction failed during upload  
**Solution:** Check `script_credit_usage` table for duplicate entries. Refund credit if upload failed.

**Issue:** Legacy user doesn't have 10 credits  
**Solution:** Manually grant via admin endpoint: `POST /api/credits/admin/grant-legacy`

---

## Contact

For questions or issues, contact:
- **Developer:** [Your Name]
- **Email:** support@slateone.com
- **Slack:** #slateone-dev
