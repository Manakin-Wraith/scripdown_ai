# Email Deliverability Troubleshooting Guide

## Problem: Resend Shows "Delivered" But Users Don't Receive Emails

When Resend reports an email as "delivered," it means the email was successfully handed off to the recipient's email server. However, this doesn't guarantee the user will see it in their inbox.

---

## Common Causes & Solutions

### 1. **Emails Landing in Spam/Junk Folder** (Most Common)

**Why it happens:**
- New sending domain (slateone.studio is new)
- Email content triggers spam filters
- Low sender reputation (new domain = no reputation yet)
- Emojis in subject lines can trigger filters
- Too many links or "salesy" language

**Solutions:**

#### A. Ask Users to Check Spam Folder
Create a simple instruction email or message:
```
📧 Can't find our email?

1. Check your Spam/Junk folder
2. If you find it there, mark it as "Not Spam"
3. Add hello@slateone.studio to your contacts
4. Move the email to your inbox

This helps future emails reach you directly!
```

#### B. Improve Email Content
- **Remove excessive emojis from subject lines** (use 1 max, or none)
- **Add plain text version** alongside HTML
- **Balance text-to-image ratio** (more text, fewer images)
- **Avoid spam trigger words**: "FREE", "ACT NOW", "LIMITED TIME", "CLICK HERE"
- **Include physical address** in footer (builds trust)
- **Add unsubscribe link** (required for bulk emails)

---

### 2. **Gmail/Outlook Filtering**

**Gmail Specific Issues:**
- Gmail may categorize emails into Promotions/Social tabs
- Users need to check these tabs, not just Primary inbox
- Moving email from Promotions to Primary helps train Gmail

**Outlook/Hotmail Specific Issues:**
- Microsoft has strict filtering
- May require users to add sender to Safe Senders list
- Check "Junk Email" and "Clutter" folders

**Corporate Email (Office 365, Google Workspace):**
- IT departments often have additional filters
- May block emails from new domains automatically
- Users may need to contact IT to whitelist slateone.studio

---

### 3. **Domain Reputation Building**

**Your domain is new, so:**
- Start with small batches (you did this correctly!)
- Gradually increase sending volume over weeks
- Maintain low bounce/complaint rates
- High open rates improve reputation

**Current Status:**
✅ SPF: Configured (send.slateone.studio)
✅ DKIM: Configured via Resend
✅ DMARC: Aligned and passing
✅ Custom Return-Path: Set up

---

## Immediate Action Items

### For You (Sender):

1. **Add Plain Text Version to Emails**
   - Improves deliverability significantly
   - Shows you're not just sending marketing spam

2. **Reduce Emojis in Subject Lines**
   - Current: "🎬 {name}, we're rolling! SlateOne needs you on set"
   - Better: "{name}, SlateOne is ready for testing"
   - Or: "Your SlateOne early access is waiting"

3. **Add Unsubscribe Link**
   - Required for bulk emails
   - Improves trust and deliverability

4. **Add Physical Address in Footer**
   - Builds legitimacy
   - Required by CAN-SPAM Act

5. **Warm Up Your Domain**
   - Continue sending in small batches
   - Monitor open rates and complaints
   - Gradually increase volume

### For Recipients:

**Send this to users who don't receive emails:**

```
Hi [Name],

If you haven't received our email, please try these steps:

1. ✅ Check your Spam/Junk folder
2. ✅ Check Gmail Promotions tab (if using Gmail)
3. ✅ Add hello@slateone.studio to your contacts
4. ✅ Mark our email as "Not Spam" if you find it

If you still can't find it, reply to this message and we'll resend it.

Thanks!
SlateOne Team
```

---

## Testing Email Deliverability

### Use Mail-Tester.com
1. Send a test email to the address provided by mail-tester.com
2. Check your spam score (aim for 8/10 or higher)
3. Review specific issues flagged

### Check Resend Analytics
- Open rates (low = likely spam folder)
- Bounce rates (high = bad)
- Complaint rates (users marking as spam)

---

## Long-Term Solutions

1. **Build Sender Reputation**
   - Consistent sending patterns
   - Low bounce/complaint rates
   - High engagement (opens/clicks)

2. **Authenticate Your Domain**
   - ✅ Already done (SPF, DKIM, DMARC)

3. **Monitor Blacklists**
   - Check if your domain/IP is blacklisted
   - Use tools like MXToolbox

4. **Segment Your Audience**
   - Send to engaged users first
   - Remove bounced/inactive emails

5. **A/B Test Subject Lines**
   - Test with/without emojis
   - Test different tones
   - Monitor deliverability differences

---

## Quick Wins for Your Current Email

### Current Subject Line:
```
🎬 {name}, we're rolling! SlateOne needs you on set
```

### Improved Options (Better Deliverability):
```
Option 1: {name}, your SlateOne early access is ready
Option 2: SlateOne is live - we need your feedback
Option 3: Help us test SlateOne (early access)
```

### Add to Email Footer:
```html
<p style="font-size: 12px; color: #6B7280; margin-top: 24px;">
    SlateOne • AI-Powered Script Breakdown<br>
    [Your Physical Address]<br>
    <a href="{{unsubscribe_url}}" style="color: #9CA3AF;">Unsubscribe</a>
</p>
```

---

## Monitoring & Metrics

**Track these in Resend:**
- Delivery rate (should be >95%)
- Open rate (aim for >20% for cold emails)
- Bounce rate (keep <2%)
- Complaint rate (keep <0.1%)

**Red Flags:**
- ⚠️ Open rate <10% = likely spam folder
- ⚠️ Bounce rate >5% = bad email list
- ⚠️ Complaints >0.5% = content issues

---

## Contact for Help

If issues persist:
1. Check Resend dashboard for specific delivery errors
2. Contact Resend support (they can see backend delivery issues)
3. Ask users which email provider they use (Gmail, Outlook, etc.)
4. Test with mail-tester.com to identify specific problems

---

## Summary Checklist

- [ ] Reduce emojis in subject line
- [ ] Add plain text version of email
- [ ] Add unsubscribe link
- [ ] Add physical address to footer
- [ ] Test with mail-tester.com
- [ ] Ask users to check spam folder
- [ ] Monitor Resend analytics
- [ ] Continue small batch sending (domain warm-up)
