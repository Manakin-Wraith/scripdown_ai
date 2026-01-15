# Email Inconsistency Diagnosis: Two-Project Architecture

## 🏗️ **Architecture Overview**

### **Project 1: App (app.slateone.studio)**
- **Supabase:** `twzfaizeyqwevmhjyicz.supabase.co`
- **Purpose:** Main SaaS application
- **Email Types:**
  - Supabase Auth emails (confirmation, password reset)
  - Resend transactional emails (welcome, reminders, feedback)

### **Project 2: Marketing Site (slateone.studio)**
- **Supabase:** `yoqcitfxarpbfldxanhi.supabase.co`
- **Purpose:** Marketing/landing page
- **Email Types:**
  - Waitlist signups
  - Early access invitations

---

## 🔍 **Root Causes of Inconsistent Email Delivery**

### **1. DNS Conflicts (Most Likely)**

**Problem:** Both projects using same domain `slateone.studio` for emails

**Symptoms:**
- Some emails deliver, others don't
- Intermittent failures
- Emails go to spam

**Causes:**
- Multiple SPF records (one per project)
- Conflicting DKIM configurations
- Shared email reputation

**Solution:**
```
Use subdomains to separate email sources:
- App: noreply@app.slateone.studio
- Marketing: hello@slateone.studio
```

---

### **2. Supabase Auth Email Configuration**

**Problem:** Two separate Supabase projects with different SMTP configs

**Project 1 (App):**
- May use default Supabase SMTP
- Or custom SMTP (Resend)

**Project 2 (Marketing):**
- Likely different configuration
- May conflict with Project 1

**Check:**
1. Go to Supabase Dashboard for each project
2. Navigate to: **Authentication** → **Email Templates** → **SMTP Settings**
3. Compare configurations

---

### **3. Resend API Key Conflicts**

**Problem:** Same Resend API key used across projects

**Issues:**
- Shared rate limits (100 emails/day on free tier)
- Shared domain reputation
- Difficult to track which project sent what

**Solution:**
- Create separate Resend accounts/API keys
- Or use Resend "environments" feature

---

### **4. Email Service Provider Mixing**

**Current Setup (Likely):**
```
Project 1 (App):
  - Supabase Auth → Supabase SMTP (confirmation emails)
  - Python scripts → Resend API (welcome, reminders)

Project 2 (Marketing):
  - Waitlist form → Supabase Functions → Resend API
```

**Problem:** Two different email paths, hard to debug

---

## 🎯 **Diagnostic Strategy**

### **Phase 1: Identify Current Configuration**

#### **Step 1: Check DNS Records**
```bash
cd backend
python scripts/check_dns_conflicts.py
```

**What to look for:**
- Multiple SPF records (CRITICAL)
- Missing DKIM records
- No DMARC policy

#### **Step 2: Check Supabase Configurations**

**For Project 1 (App):**
1. Go to: https://supabase.com/dashboard/project/twzfaizeyqwevmhjyicz
2. **Authentication** → **Email Templates**
3. Check SMTP settings
4. Screenshot configuration

**For Project 2 (Marketing):**
1. Go to: https://supabase.com/dashboard/project/yoqcitfxarpbfldxanhi
2. Same steps as above
3. Compare with Project 1

#### **Step 3: Check Resend Configuration**
1. Go to: https://resend.com/domains
2. Check which domains are verified
3. Check if both projects use same domain
4. Review sending logs

---

### **Phase 2: Test Email Delivery**

#### **Test Matrix**

| From | To | Expected | Actual | Pass/Fail |
|------|-----|----------|--------|-----------|
| App (Supabase Auth) | Gmail | Inbox | ? | ? |
| App (Resend) | Gmail | Inbox | ? | ? |
| Marketing (Resend) | Gmail | Inbox | ? | ? |
| App (Supabase Auth) | Outlook | Inbox | ? | ? |
| App (Resend) | Outlook | Inbox | ? | ? |

**Run tests:**
```bash
# Test App emails
python scripts/test_email_deliverability.py

# Test Marketing emails (need separate script)
```

---

### **Phase 3: Analyze Patterns**

#### **Questions to Answer:**

1. **Which emails fail consistently?**
   - Auth confirmation emails?
   - Welcome emails?
   - Reminder emails?
   - Waitlist emails?

2. **Which email providers have issues?**
   - Gmail?
   - Outlook?
   - Yahoo?
   - Corporate emails?

3. **Time-based patterns?**
   - Failures during high volume?
   - Failures after rate limit hit?

4. **Project-specific patterns?**
   - Only App emails fail?
   - Only Marketing emails fail?
   - Both fail?

---

## ✅ **Recommended Solutions**

### **Solution 1: Separate Email Domains (Recommended)**

**Implementation:**
```
App emails:     noreply@app.slateone.studio
Marketing:      hello@slateone.studio
No-reply:       noreply@slateone.studio
```

**DNS Setup:**
```
# SPF for app.slateone.studio
v=spf1 include:_spf.resend.com ~all

# SPF for slateone.studio
v=spf1 include:_spf.resend.com include:_spf.google.com ~all

# DKIM for each subdomain
app._domainkey.slateone.studio
_domainkey.slateone.studio
```

**Benefits:**
- No DNS conflicts
- Separate email reputation
- Easy to track which project sent email
- Can use different email providers per project

---

### **Solution 2: Consolidate Email Service**

**Option A: All emails through Resend**
```
Project 1 (App):
  - Supabase Auth → Custom SMTP (Resend)
  - Python scripts → Resend API

Project 2 (Marketing):
  - Waitlist → Resend API
```

**Option B: All emails through Supabase**
```
Project 1 (App):
  - Supabase Auth → Supabase SMTP
  - Python scripts → Supabase Edge Functions → Resend

Project 2 (Marketing):
  - Waitlist → Supabase Edge Functions → Resend
```

---

### **Solution 3: Separate Resend Accounts**

**Setup:**
- Resend Account 1 → App emails
- Resend Account 2 → Marketing emails

**Benefits:**
- Separate rate limits
- Separate billing
- Separate analytics
- No shared reputation

---

## 🛠️ **Implementation Checklist**

### **Immediate Actions (Fix Critical Issues)**

- [ ] Run DNS diagnostics: `python scripts/check_dns_conflicts.py`
- [ ] Check for multiple SPF records
- [ ] Verify DKIM records exist
- [ ] Add DMARC policy if missing

### **Short-term (Fix Configuration)**

- [ ] Document current Supabase SMTP settings (both projects)
- [ ] Document current Resend configuration
- [ ] Decide on email domain strategy (subdomains vs single domain)
- [ ] Update DNS records accordingly
- [ ] Test email delivery after changes

### **Long-term (Monitoring & Prevention)**

- [ ] Set up email delivery monitoring
- [ ] Create alerting for failed emails
- [ ] Implement email logging/tracking
- [ ] Regular DNS audits
- [ ] Document email architecture

---

## 📊 **Monitoring Strategy**

### **Metrics to Track**

1. **Delivery Rate**
   - Total sent
   - Total delivered
   - Total bounced
   - Total spam

2. **Response Time**
   - Time from trigger to send
   - Time from send to delivery

3. **Provider-specific Rates**
   - Gmail delivery rate
   - Outlook delivery rate
   - Corporate email delivery rate

4. **Project-specific Rates**
   - App email delivery rate
   - Marketing email delivery rate

### **Tools**

- **Resend Dashboard** - Delivery logs, bounce tracking
- **Supabase Logs** - Auth email logs
- **Custom tracking** - Database logging of email events

---

## 🚨 **Common Issues & Quick Fixes**

### **Issue 1: Emails go to spam**
**Cause:** Missing/incorrect SPF, DKIM, or DMARC  
**Fix:** Run DNS diagnostics, add missing records

### **Issue 2: Some emails deliver, others don't**
**Cause:** Rate limiting or DNS conflicts  
**Fix:** Check Resend usage, verify DNS has no conflicts

### **Issue 3: Confirmation emails not received**
**Cause:** Supabase SMTP misconfiguration  
**Fix:** Check Supabase Auth settings, test with different email

### **Issue 4: Intermittent failures**
**Cause:** Shared rate limits or reputation issues  
**Fix:** Separate email sources, use subdomains

---

## 📝 **Next Steps**

1. **Run diagnostics:**
   ```bash
   python scripts/diagnose_email_architecture.py
   python scripts/check_dns_conflicts.py
   ```

2. **Document findings:**
   - Current DNS configuration
   - Current Supabase settings (both projects)
   - Current Resend configuration

3. **Decide on solution:**
   - Separate subdomains? (Recommended)
   - Consolidate email service?
   - Separate Resend accounts?

4. **Implement changes:**
   - Update DNS records
   - Update Supabase configurations
   - Update application code
   - Test thoroughly

5. **Monitor:**
   - Track delivery rates
   - Set up alerts
   - Regular audits

---

## 🔗 **Resources**

- [Resend Documentation](https://resend.com/docs)
- [Supabase Auth Email Configuration](https://supabase.com/docs/guides/auth/auth-email-templates)
- [SPF Record Checker](https://mxtoolbox.com/spf.aspx)
- [DKIM Record Checker](https://mxtoolbox.com/dkim.aspx)
- [Email Deliverability Guide](backend/docs/email_deliverability_guide.md)
