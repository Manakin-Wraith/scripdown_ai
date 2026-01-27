# Quick Win: Credit Alert Implementation

## Overview
Minimal implementation to guide new signup users (with 0 credits) to purchase credit packages by making the credit icon visually prominent and updating messaging.

---

## Changes Made

### 1. Pulse Animation on Credit Icon
**File**: `frontend/src/components/credits/CreditBalance.css`

**Added**:
- Pulse animation that activates when user has 0 credits
- Red glow effect that pulses every 2 seconds
- Animation stops on hover (better UX)

**CSS Changes**:
```css
.credit-balance.empty {
    animation: pulse-alert 2s ease-in-out infinite;
}

.credit-balance.empty:hover {
    animation: none; /* Stop pulsing on hover */
}

@keyframes pulse-alert {
    0%, 100% {
        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
        transform: scale(1);
    }
    50% {
        box-shadow: 0 0 0 8px rgba(239, 68, 68, 0);
        transform: scale(1.02);
    }
}
```

---

### 2. Updated Upload Blocked Message
**File**: `frontend/src/components/script/ScriptUpload.jsx`

**Changed**: Line 241
```jsx
// Before:
Each script upload costs 1 credit. Purchase credits to continue uploading.

// After:
Each script upload costs 1 credit. Click the pulsing credit icon in the top menu or buy now below.
```

This explicitly directs users to look for the pulsing credit icon in the TopBar.

---

## User Flow

### New Signup User (Landing Page → 1 Credit)

1. **Signs up from landing page**
   - Gets 1 credit via `/set-plan` endpoint
   - `script_upload_limit = 1`
   - `subscription_expires_at = NULL`

2. **Uploads first script**
   - Credit deducted: `credits = 0`
   - Upload succeeds

3. **Credit icon starts pulsing** 🔴⚡
   - TopBar credit balance shows "0 credits"
   - Red pulsing animation draws attention
   - User sees visual indicator something needs action

4. **Tries to upload second script**
   - Upload blocked screen appears
   - Message: "Click the **pulsing credit icon** in the top menu or buy now below"
   - User looks up and sees pulsing icon

5. **Clicks pulsing credit icon**
   - `CreditPurchaseModal` opens
   - Shows 4 packages (single, pack_5, pack_10, pack_25)

6. **Selects package → Redirects to Yoco**
   - Completes payment
   - Credits added to account
   - Can upload again ✅

---

## Visual Design

### Pulsing Credit Icon
- **Color**: Red (#EF4444)
- **Animation**: 2s ease-in-out infinite
- **Effect**: Box shadow expands from 0 to 8px, slight scale (1.02)
- **Trigger**: `credits === 0`
- **Location**: TopBar navigation, between "My Scripts" and notification bell

### Upload Blocked Screen
- **Heading**: "Out of Credits"
- **Icon**: Lock (48px)
- **Message**: Mentions "pulsing credit icon"
- **CTA Button**: "Buy Credits - From R49"

---

## Testing Instructions

### Test 1: Verify Pulse Animation
1. Sign up new user from landing page
2. Upload first script (credit deducted)
3. Navigate to any page
4. **Verify**: Credit icon in TopBar shows "0 credits" with red pulsing animation
5. **Verify**: Hover stops the animation
6. **Verify**: Animation resumes when hover ends

### Test 2: Verify Upload Block Message
1. With 0 credits, navigate to `/upload`
2. **Verify**: Upload blocked screen appears
3. **Verify**: Message mentions "pulsing credit icon in the top menu"
4. **Verify**: "Buy Credits" button opens modal

### Test 3: End-to-End Flow
1. New user signs up → 1 credit
2. Uploads script → 0 credits
3. Sees pulsing icon → clicks it
4. Modal opens → selects package
5. Redirects to Yoco → completes payment
6. Credits added → can upload again

---

## Browser Compatibility

The CSS animations use standard properties supported by all modern browsers:
- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

---

## Performance Impact

**Minimal**: 
- Single CSS animation on one element
- No JavaScript required
- Animation pauses on hover (reduces CPU when interacting)
- No impact on page load or runtime performance

---

## Analytics Tracking (Recommended)

Track these events to measure effectiveness:

```javascript
// When pulse starts (credits hit 0)
analytics.track('credit_icon_pulse_started', {
  user_id: user.id,
  previous_credits: 1,
  current_credits: 0
});

// When user clicks pulsing icon
analytics.track('pulsing_credit_icon_clicked', {
  user_id: user.id,
  credits: 0,
  source: 'pulse_alert'
});

// When modal opens from blocked screen
analytics.track('credit_modal_opened', {
  user_id: user.id,
  source: 'upload_blocked',
  credits: 0
});
```

---

## Success Metrics

After 1 week, measure:

1. **Click-Through Rate**: % of users who click pulsing icon
2. **Conversion Rate**: % of blocked users who purchase credits
3. **Time to Purchase**: Average time from block to purchase
4. **Abandonment Rate**: % who leave without purchasing

**Target**: 30%+ conversion rate from blocked users

---

## Future Enhancements (Optional)

If Quick Win proves successful, consider:

1. **Toast Notification**: Show toast when credits hit 0
2. **Dashboard Banner**: Welcome banner for first-time users
3. **Email Reminder**: Send email when credits depleted
4. **In-App Notification**: Push notification for mobile users

---

## Rollback Plan

If issues occur:

1. **Remove pulse animation**:
   ```css
   .credit-balance.empty {
       /* Remove animation line */
   }
   ```

2. **Revert message**:
   ```jsx
   Purchase credits to continue uploading.
   ```

Both changes are non-breaking and can be reverted instantly.

---

## Implementation Time

- **CSS Changes**: 2 minutes
- **Message Update**: 1 minute
- **Testing**: 5 minutes
- **Total**: ~8 minutes ⚡

---

## Status

✅ **Complete** - Ready for testing and deployment
