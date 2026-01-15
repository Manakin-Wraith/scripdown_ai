# Supabase Email Confirmation Guide

## 🎯 Understanding the Problem

The error **"Failed to invite user: Database error saving new user"** occurs when you try to use `admin.invite_user_by_email()` on a user that **already exists** in the database.

### Key Distinction:
- **`invite_user_by_email()`** → Creates NEW users (invite to join)
- **`generate_link()`** → Resends confirmation to EXISTING users

---

## 📧 Three Scenarios for Email Confirmation

### **Scenario 1: New User Signup (Frontend)**
**When:** User signs up through your app  
**Method:** Supabase automatically sends confirmation email  
**Code:** Frontend calls `supabase.auth.signUp()`

```javascript
// Frontend (React/Vue)
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password123',
  options: {
    emailRedirectTo: 'https://yourapp.com/auth/callback'
  }
})
```

**What happens:**
1. User record created in `auth.users` (email_confirmed_at = NULL)
2. Supabase automatically sends confirmation email
3. User clicks link → email_confirmed_at set to NOW()

---

### **Scenario 2: Resend Confirmation (Existing Unconfirmed User)**
**When:** User didn't receive/lost confirmation email  
**Method:** Use `generate_link()` for existing users  
**Error if you use:** `invite_user_by_email()` ❌

```python
# Backend - Resend confirmation to EXISTING user
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def resend_confirmation(email: str):
    """Resend confirmation email to existing unconfirmed user"""
    
    # Get user
    users = supabase.auth.admin.list_users()
    user = next((u for u in users if u.email == email), None)
    
    if not user:
        return {'error': 'User not found'}
    
    if user.email_confirmed_at:
        return {'error': 'User already confirmed'}
    
    # Generate new confirmation link
    result = supabase.auth.admin.generate_link({
        'type': 'signup',
        'email': email
    })
    
    return {'success': True, 'link': result.properties.get('action_link')}
```

---

### **Scenario 3: Invite New User (Admin Creates Account)**
**When:** Admin invites someone to join (creates account for them)  
**Method:** Use `invite_user_by_email()` for NEW users  
**Error if:** User already exists ❌

```python
# Backend - Invite NEW user (admin creates account)
def invite_new_user(email: str):
    """Admin invites a new user - creates account and sends invite"""
    
    try:
        # This CREATES a new user and sends invite email
        result = supabase.auth.admin.invite_user_by_email(
            email,
            options={
                'redirect_to': 'https://yourapp.com/auth/callback'
            }
        )
        
        return {'success': True, 'user': result}
        
    except Exception as e:
        if 'already exists' in str(e).lower():
            return {'error': 'User already exists - use resend_confirmation instead'}
        return {'error': str(e)}
```

---

## 🔧 Your Fixed Script

The updated `resend_confirmation_email.py` now:

1. ✅ Checks if user exists
2. ✅ Checks if already confirmed
3. ✅ Uses `generate_link()` for existing users (correct method)
4. ✅ Falls back to alternative method if needed

**Usage:**
```bash
python scripts/resend_confirmation_email.py
# Enter email: user@example.com
```

---

## 🚨 Common Errors & Solutions

### Error: "Database error saving new user"
**Cause:** Using `invite_user_by_email()` on existing user  
**Solution:** Use `generate_link()` instead

### Error: "User not found"
**Cause:** User doesn't exist in auth.users  
**Solution:** User needs to sign up first via frontend

### Error: "User already confirmed"
**Cause:** email_confirmed_at is already set  
**Solution:** No action needed - user is confirmed

---

## 📊 Decision Tree

```
Need to send confirmation email?
│
├─ Is this a NEW user (doesn't exist yet)?
│  └─ YES → Use invite_user_by_email()
│           (Admin creating account)
│
└─ Is this an EXISTING user?
   │
   ├─ Already confirmed? (email_confirmed_at != NULL)
   │  └─ YES → No action needed
   │
   └─ Not confirmed? (email_confirmed_at == NULL)
      └─ YES → Use generate_link() with type='signup'
                (Resend confirmation)
```

---

## 🎯 Best Practices

### 1. **Check User Status First**
```python
users = supabase.auth.admin.list_users()
user = next((u for u in users if u.email == email), None)

if not user:
    # User doesn't exist - can use invite_user_by_email()
    pass
elif user.email_confirmed_at:
    # Already confirmed - no action needed
    pass
else:
    # Exists but not confirmed - use generate_link()
    pass
```

### 2. **Configure Email Templates**
Go to Supabase Dashboard:
- **Authentication** → **Email Templates**
- Customize confirmation email template
- Set redirect URLs

### 3. **Handle Email Redirects**
```javascript
// Frontend callback handler
useEffect(() => {
  supabase.auth.onAuthStateChange((event, session) => {
    if (event === 'SIGNED_IN') {
      // User confirmed email and signed in
      router.push('/dashboard')
    }
  })
}, [])
```

### 4. **Monitor Confirmation Status**
```python
# Check which users need confirmation
users = supabase.auth.admin.list_users()
unconfirmed = [u for u in users if not u.email_confirmed_at]

print(f"Unconfirmed users: {len(unconfirmed)}")
for user in unconfirmed:
    print(f"  - {user.email} (created: {user.created_at})")
```

---

## 🔐 Security Considerations

1. **Service Role Key** - Only use on backend (never expose to frontend)
2. **Rate Limiting** - Limit confirmation email resends (e.g., 1 per hour)
3. **Link Expiration** - Confirmation links expire after 24 hours by default
4. **Email Verification** - Always verify email format before sending

---

## 📝 Testing Checklist

- [ ] New user signup sends confirmation email
- [ ] Confirmation link works and sets email_confirmed_at
- [ ] Resend confirmation works for unconfirmed users
- [ ] Already confirmed users get appropriate message
- [ ] Non-existent users get appropriate error
- [ ] Email templates are customized and branded
- [ ] Redirect URLs work correctly

---

## 🆘 Troubleshooting

### Emails Not Sending?

1. **Check Supabase Email Settings**
   - Dashboard → Project Settings → Auth
   - Verify "Enable email confirmations" is ON
   - Check SMTP settings if using custom provider

2. **Check Spam Folder**
   - Supabase emails may go to spam initially
   - Add sender to safe list

3. **Verify Environment Variables**
   ```bash
   echo $SUPABASE_URL
   echo $SUPABASE_SERVICE_KEY
   ```

4. **Check Supabase Logs**
   - Dashboard → Logs → Auth Logs
   - Look for email send events

### Still Having Issues?

Run the verification script:
```bash
python scripts/verify_email_confirmation_db.py
```

This will show:
- All users and their confirmation status
- Which users need confirmation emails
- Database connectivity status

---

## 📚 Related Documentation

- [Supabase Auth Docs](https://supabase.com/docs/guides/auth)
- [Email Templates](https://supabase.com/docs/guides/auth/auth-email-templates)
- [Admin API Reference](https://supabase.com/docs/reference/javascript/auth-admin-api)

---

## ✅ Summary

**For NEW users (don't exist yet):**
```python
supabase.auth.admin.invite_user_by_email(email)
```

**For EXISTING unconfirmed users:**
```python
supabase.auth.admin.generate_link({
    'type': 'signup',
    'email': email
})
```

**For EXISTING confirmed users:**
```python
# No action needed - already confirmed
```
