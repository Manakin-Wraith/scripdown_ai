# Pricing Model Simplification

**Date:** 2026-04-07
**Type:** Feature / Refactor

## Summary

Replaced the multi-tier breakdown pack pricing model with a single flat-rate monthly subscription.

## New Pricing

- **$49/month** — Unlimited breakdowns, full production infrastructure
- **Payment provider:** Wise (`https://wise.com/pay/r/8j9W0j5SUuPivxk`)

## Previous Pricing (Removed)

| Pack          | Price   | Per Breakdown | Provider |
|---------------|---------|---------------|----------|
| 1 Breakdown   | R500    | R500          | Yoco     |
| 5 Breakdowns  | R2,000  | R400          | Yoco     |
| 10 Breakdowns | R3,500  | R350          | Yoco     |
| 25 Breakdowns | R7,500  | R300          | Yoco     |

## Files Changed

### `lib/supabase.ts`
- `SubscriptionTier` type narrowed from `'single_script' | 'pack_5' | 'pack_10' | 'pack_25'` to `'monthly'`
- Removed `TIER_CONFIG` record and Yoco URL construction
- `createSubscriptionLead()` now uses a single Wise payment URL
- Lead records stored with `payment_tier: 'monthly'`

### `components/Pricing.tsx`
- Removed pack table and 4-column CTA grid
- Replaced with single centered plan card: $49/mo, feature checklist, "Get Started" CTA
- Removed `SubscriptionTier` import (no longer needed in component)
- Sections reduced from 4 to 3: Header → Plan Card → Who This Is For

### `components/TierSelectionModal.tsx`
- Removed `TIER_DISPLAY` config record (4 tiers)
- Modal now displays fixed "Monthly Plan · $49/mo" with email capture
- On submit: saves lead to `payment_leads` table, redirects to Wise

## Notes

- `PaymentModal.tsx` (used in `HowItWorks`) was left untouched — it references legacy R49/R249 Yoco tiers but is never triggered (modal open state is never set to `true`).
- Pre-existing `payment_leads` table schema unchanged; `yoco_url` column now stores the Wise link.
