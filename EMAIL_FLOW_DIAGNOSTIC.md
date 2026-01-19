# 📧 Email Flow Diagnostic Report

## 🏗️ System Architecture

### Supabase Projects
1. **Main App** (`twzfaizeyqwevmhjyicz`)
   - Purpose: User authentication, app data
   - URL: https://twzfaizeyqwevmhjyicz.supabase.co
   - Custom SMTP: ✅ Configured (Resend)

2. **Notel Landing Page** (`yoqcitfxarpbfldxanhi`)
   - Purpose: Waitlist collection
   - URL: https://yoqcitfxarpbfldxanhi.supabase.co
   - Custom SMTP: ✅ Configured (Resend)

---

## 📊 Email Flows

### Flow 1: Waitlist Signup (Landing Page → Early Access Email)
**Status: ✅ WORKING**

```
1. User submits email on landing page
   ↓
2. Stored in Notel Supabase 'waitlist' table
   ↓
3. Manual script: send_waitlist_early_access.py
   ↓
4. Backend email_service.py → Resend API
   ↓
5. Email sent from: hello@slateone.studio
```

**Code Path:**
- `backend/scripts/send_waitlist_early_access.py:140-232`
- `backend/services/email_service.py:777-824` (send_early_access_reminder)
- Uses: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`

**Verification:**
- ✅ Tested successfully (4 emails sent Jan 17, 2026)
- ✅ Resend dashboard shows delivery

---

### Flow 2: App User Signup (Registration → Confirmation Email)
**Status: ❌ FAILING**

```
1. User visits app.slateone.studio/login
   ↓
2. Clicks "Sign up" tab
   ↓
3. Enters email, password, full name
   ↓
4. Frontend: LoginPage.jsx calls signup()
   ↓
5. AuthContext.jsx calls signUp() from supabase.js
   ↓
6. supabase.js calls supabase.auth.signUp()
   ↓
7. Supabase Auth creates user in auth.users
   ↓
8. Supabase sends confirmation email via Custom SMTP
   ↓
9. Email should arrive from: hello@slateone.studio
   ❌ FAILING HERE - Error: "Failed to invite user"
```

**Code Path:**
- Frontend: `frontend/src/pages/LoginPage.jsx:135` → `signup(email, password, fullName)`
- Context: `frontend/src/context/AuthContext.jsx:200-250` → signup function
- Supabase: `frontend/src/lib/supabase.js:22-31` → signUp()
- Supabase Auth API: `/auth/v1/signup` endpoint

**Configuration:**
```javascript
// frontend/src/lib/supabase.js:22-31
export const signUp = async (email, password) => {
    const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
            emailRedirectTo: `${window.location.origin}/auth/callback?type=signup`
        }
    });
    return { data, error };
};
```

**Supabase Settings Required:**
- ✅ Custom SMTP configured
- ❓ Email confirmation enabled?
- ❓ Email template configured?
- ❓ Redirect URL correct?

---

### Flow 3: Email Confirmation (Link Click → Verification)
**Status: ❌ NOT TESTED (Flow 2 blocks this)**

```
1. User receives confirmation email
   ↓
2. Clicks "Confirm Email Address" button
   ↓
3. Redirects to: app.slateone.studio/auth/confirm?token_hash=...&type=signup
   ↓
4. Frontend: ConfirmEmailPage.jsx loads
   ↓
5. Extracts token_hash from URL
   ↓
6. Calls supabase.auth.verifyOtp({ token_hash, type: 'signup' })
   ↓
7. Supabase updates email_confirmed_at in auth.users
   ↓
8. Redirects to /scripts
```

**Code Path:**
- Frontend: `frontend/src/pages/ConfirmEmailPage.jsx:24-89`
- Route: `frontend/src/App.jsx:81` → `/auth/confirm`

**Recent Fix:**
- ✅ Updated type parameter from 'email' to 'signup' (Line 47)
- ⚠️ Not deployed yet - needs git commit + push

---

## 🔍 Identified Issues

### Issue 1: Signup Email Not Sending
**Error:** "Failed to invite user: Failed to make POST request"

**Possible Causes:**
1. **SMTP Configuration Issue**
   - Custom SMTP may not be fully enabled
   - API key incorrect
   - Sender email not verified

2. **Email Confirmation Setting**
   - If "Confirm email" is ON but SMTP fails, signup blocks
   - Need to verify Supabase Auth settings

3. **Rate Limiting**
   - Too many signup attempts
   - Temporary block

**Action Items:**
- [ ] Verify Supabase Dashboard → Settings → Auth → SMTP Settings
- [ ] Check "Confirm email" toggle status
- [ ] Verify Resend API key is correct
- [ ] Test with email confirmation temporarily disabled

### Issue 2: Frontend Type Mismatch (FIXED)
**Status:** ✅ Fixed but not deployed

**Change Made:**
```javascript
// Before:
type: type || 'email'

// After:
type: type || 'signup'
```

**Action Items:**
- [ ] Commit fix: `git add frontend/src/pages/ConfirmEmailPage.jsx`
- [ ] Push to deploy: `git commit -m "fix: handle type=signup in email confirmation"`
- [ ] Verify Vercel deployment

---

## 🧪 Testing Plan

### Test 1: Verify SMTP Configuration
```bash
# Check Supabase Dashboard
1. Go to: https://supabase.com/dashboard/project/twzfaizeyqwevmhjyicz/settings/auth
2. Scroll to "SMTP Settings"
3. Verify:
   - ✅ Enable Custom SMTP: ON
   - ✅ Host: smtp.resend.com
   - ✅ Port: 587
   - ✅ Username: resend
   - ✅ Password: re_gtgcoYQP_HTJe9TWSL72aB7jkfjpWZQN1
   - ✅ Sender email: hello@slateone.studio
   - ✅ Sender name: SlateOne
```

### Test 2: Check Email Confirmation Setting
```bash
# Supabase Dashboard → Settings → Auth
1. Find "Confirm email" toggle
2. Current status: ?
3. If ON: SMTP must work or signups fail
4. Temporary fix: Turn OFF for testing
5. Re-enable after SMTP verified
```

### Test 3: Test Signup Flow
```bash
# After fixing SMTP
1. Go to: https://app.slateone.studio/login
2. Click "Sign up"
3. Enter test email: test+$(date +%s)@yourdomain.com
4. Submit form
5. Check for errors
6. Verify user created: python backend/scripts/check_user_verification.py
```

### Test 4: Test Confirmation Flow
```bash
# After signup works
1. Check email inbox
2. Click confirmation link
3. Should redirect to /auth/confirm
4. Should see "Email Confirmed!"
5. Should redirect to /scripts
6. Verify: python backend/scripts/check_user_verification.py
```

---

## 📝 Configuration Checklist

### Supabase Main Project (twzfaizeyqwevmhjyicz)
- [ ] Custom SMTP enabled
- [ ] SMTP credentials correct
- [ ] Email confirmation setting verified
- [ ] Email templates configured
- [ ] Redirect URLs correct

### Frontend Environment
- [ ] VITE_SUPABASE_URL set
- [ ] VITE_SUPABASE_ANON_KEY set
- [ ] Build deployed to Vercel

### Backend Environment
- [ ] SUPABASE_URL set
- [ ] SUPABASE_SERVICE_KEY set
- [ ] RESEND_API_KEY set
- [ ] RESEND_FROM_EMAIL set

---

## 🎯 Next Steps

1. **Verify Supabase SMTP Configuration**
   - Check all SMTP settings in dashboard
   - Verify API key is correct
   - Test email sending

2. **Deploy Frontend Fix**
   - Commit ConfirmEmailPage.jsx changes
   - Push to trigger Vercel deployment
   - Verify deployment successful

3. **Test Signup Flow**
   - Create test account
   - Monitor for errors
   - Check Resend dashboard

4. **Document Working Configuration**
   - Update this file with verified settings
   - Create troubleshooting guide
   - Add to project documentation

---

## 📞 Support Resources

- **Supabase Dashboard:** https://supabase.com/dashboard/project/twzfaizeyqwevmhjyicz
- **Resend Dashboard:** https://resend.com/emails
- **Vercel Dashboard:** https://vercel.com/manakin-wraiths-projects/frontend
- **Backend Scripts:** `/backend/scripts/`
  - `check_user_verification.py` - Check user status
  - `test_confirmation_email.py` - Test email sending
  - `send_waitlist_early_access.py` - Waitlist emails (working)
