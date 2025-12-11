# Payment Integration Guide

## Overview

SlateOne uses Yoco payment links for beta user payments. The flow is:

1. User clicks "Pay & Get Access" on signup page
2. User is redirected to Yoco hosted payment page
3. After payment, Yoco redirects to `/payment-success`
4. Edge function records payment and prepares account

## Components

### Frontend

- **`LoginPage.jsx`** - Contains Beta CTA with Yoco payment link
- **`PaymentSuccessPage.jsx`** - Landing page after payment completion
- **Route**: `/payment-success` (public, no auth required)

### Backend

- **`supabase/functions/process-beta-payment/index.ts`** - Edge function to process payments
- **`backend/db/migrations/004_beta_payments.sql`** - Database schema

## Setup Instructions

### 1. Run Database Migration

In Supabase SQL Editor, run the contents of:
```
backend/db/migrations/004_beta_payments.sql
```

This creates:
- `beta_payments` table
- Adds `subscription_status` column to `profiles`

### 2. Deploy Edge Function

```bash
# Install Supabase CLI if not already
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref twzfaizeyqwevmhjyicz

# Deploy the function
supabase functions deploy process-beta-payment
```

### 3. Configure Yoco Redirect URL

In your Yoco dashboard, set the success redirect URL to:
```
https://your-app.com/payment-success
```

Or with email parameter (if Yoco supports it):
```
https://your-app.com/payment-success?email={{customer_email}}
```

### 4. Environment Variables

The Edge Function uses these Supabase environment variables (automatically available):
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## Payment Flow

```
┌─────────────────┐
│   Login Page    │
│  (Signup Mode)  │
└────────┬────────┘
         │ Click "Pay & Get Access"
         ▼
┌─────────────────┐
│  Yoco Payment   │
│     Page        │
└────────┬────────┘
         │ Payment Complete
         ▼
┌─────────────────┐
│ /payment-success│
│   (Frontend)    │
└────────┬────────┘
         │ POST to Edge Function
         ▼
┌─────────────────┐
│ process-beta-   │
│ payment (Edge)  │
└────────┬────────┘
         │ Record in beta_payments
         ▼
┌─────────────────┐
│  Success Page   │
│ "Check email"   │
└─────────────────┘
```

## Database Schema

### beta_payments
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| email | TEXT | User's email (unique) |
| payment_reference | TEXT | Yoco reference |
| amount | DECIMAL | Payment amount (default R350) |
| currency | TEXT | Currency code (default ZAR) |
| status | TEXT | pending/completed/failed/refunded |
| user_id | UUID | Links to auth.users after signup |
| metadata | JSONB | Additional data |
| created_at | TIMESTAMPTZ | Record creation |
| paid_at | TIMESTAMPTZ | Payment completion |

### profiles (extended)
| Column | Type | Description |
|--------|------|-------------|
| subscription_status | TEXT | trial/active/expired/cancelled |
| subscription_expires_at | TIMESTAMPTZ | Expiry date (null = no expiry) |

## Testing

1. Go to `/login` and switch to signup mode
2. Scroll down to see the Beta CTA
3. Click "Pay & Get Access" to test Yoco redirect
4. After payment, verify redirect to `/payment-success`
5. Check `beta_payments` table in Supabase

## Yoco Payment Link

Current link: `https://pay.yoco.com/r/2JB0rQ`

To update, change in:
- `frontend/src/pages/LoginPage.jsx` (line ~372)

## Welcome Email with Yoco Paylink

After signup, users automatically receive a welcome email containing:
- **For unpaid users**: Yoco payment link (R125 for 6 months beta access)
- **For paid users**: Confirmation of beta access with link to start using the app

### Implementation

**Backend:**
- `backend/services/email_service.py` - `send_welcome_email()` function
- `backend/routes/auth_routes.py` - `/api/auth/welcome-email` endpoint

**Frontend:**
- `frontend/src/context/AuthContext.jsx` - Calls welcome email API after signup

### Flow
1. User completes signup form
2. Supabase creates auth user
3. Frontend calls `/api/auth/welcome-email`
4. Backend checks `beta_payments` table for payment status
5. Sends appropriate email variant (paid vs unpaid)

### Email Variants

| User Status | Subject | CTA |
|-------------|---------|-----|
| Not Paid | "Welcome! Complete your beta access" | "Pay R125 & Get Access" (Yoco link) |
| Paid | "Welcome, [Name]!" | "Start Using SlateOne" |

## Future Enhancements

1. **Webhook Integration**: Add Yoco webhook for real-time payment confirmation
2. **Auto Account Creation**: Create user account immediately after payment
3. ~~**Email Notifications**: Send welcome email with credentials~~ ✅ IMPLEMENTED
4. **Subscription Management**: Add renewal/upgrade flows
