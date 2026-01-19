# 🚨 SECURITY INCIDENT: Exposed Credentials in Git History

**Date:** January 17, 2026  
**Severity:** CRITICAL  
**Status:** ⚠️ REQUIRES IMMEDIATE ACTION  
**GitGuardian Alert:** Commit `d17080c` - SMTP credentials exposed

---

## 📋 Incident Summary

GitGuardian detected that production credentials were committed to the public git repository in commit `d17080c`. The following sensitive credentials are exposed in git history:

### Exposed Credentials

1. **Supabase Production Database**
   - `SUPABASE_URL`: `https://twzfaizeyqwevmhjyicz.supabase.co`
   - `SUPABASE_ANON_KEY`: `eyJhbGci...VjyI` (exposed)
   - `SUPABASE_SERVICE_KEY`: `eyJhbGci...TWXo` (exposed - **CRITICAL**)
   - `SUPABASE_JWT_SECRET`: `2kL9aUWzsP/O0W6m...` (exposed - **CRITICAL**)

2. **AI API Keys**
   - `GEMINI_API_KEY`: `REDACTED_GEMINI_API_KEY` (exposed)

3. **Email Service (Resend)**
   - `RESEND_API_KEY`: `REDACTED_RESEND_API_KEY` (exposed)
   - `RESEND_FROM_EMAIL`: `hello@slateone.studio`

4. **Notel Supabase (Waitlist)**
   - `NOTEL_SUPABASE_URL`: `https://yoqcitfxarpbfldxanhi.supabase.co`
   - `NOTEL_SUPABASE_SERVICE_KEY`: `eyJhbGci...Y_g` (exposed - **CRITICAL**)

---

## ⚠️ IMMEDIATE ACTIONS REQUIRED (DO THIS NOW)

### Step 1: Rotate ALL Exposed Credentials (URGENT - Do First)

**Priority Order:**

#### 1.1 Supabase Service Role Key (HIGHEST PRIORITY)
```bash
# This key bypasses Row Level Security - ROTATE IMMEDIATELY
```
**Actions:**
1. Go to: https://supabase.com/dashboard/project/twzfaizeyqwevmhjyicz/settings/api
2. Click "Reset service_role key"
3. Update Railway environment variable: `SUPABASE_SERVICE_KEY`
4. Update local `.env` file with new key
5. Restart all services

#### 1.2 Supabase JWT Secret (CRITICAL)
```bash
# This signs all JWTs - if compromised, attackers can forge tokens
```
**Actions:**
1. Go to: https://supabase.com/dashboard/project/twzfaizeyqwevmhjyicz/settings/api
2. Under "JWT Settings" → Reset JWT Secret
3. Update Railway: `SUPABASE_JWT_SECRET`
4. Update local `.env`
5. **NOTE:** This will invalidate ALL existing user sessions

#### 1.3 Resend API Key
```bash
# Can send emails from your domain
```
**Actions:**
1. Go to: https://resend.com/api-keys
2. Delete key: `REDACTED_RESEND_API_KEY`
3. Create new API key
4. Update Railway: `RESEND_API_KEY`
5. Update local `.env`

#### 1.4 Gemini API Key
```bash
# Can consume your AI quota
```
**Actions:**
1. Go to: https://aistudio.google.com/app/apikey
2. Delete key: `REDACTED_GEMINI_API_KEY`
3. Create new API key
4. Update Railway: `GEMINI_API_KEY`
5. Update local `.env`

#### 1.5 Notel Supabase Service Key
```bash
# Access to waitlist database
```
**Actions:**
1. Go to: https://supabase.com/dashboard/project/yoqcitfxarpbfldxanhi/settings/api
2. Reset service_role key
3. Update Railway: `NOTEL_SUPABASE_SERVICE_KEY`
4. Update local `.env`

---

### Step 2: Remove Credentials from Git History

**WARNING:** This will rewrite git history. All collaborators must re-clone.

#### Option A: Using git-filter-repo (Recommended)

```bash
# Install git-filter-repo
pip install git-filter-repo

# Backup your repo first
cd /Users/thecasterymedia/Desktop/PORTFOLIO/SaaS/ScripDown_AI
cp -r .git .git.backup

# Remove .env from entire history
git filter-repo --path backend/.env --invert-paths --force

# Remove any other exposed files
git filter-repo --path .env --invert-paths --force

# Force push to remote (AFTER rotating credentials)
git push origin --force --all
git push origin --force --tags
```

#### Option B: Using BFG Repo-Cleaner (Alternative)

```bash
# Install BFG
brew install bfg

# Backup
cp -r .git .git.backup

# Remove .env files
bfg --delete-files .env

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push
git push origin --force --all
```

---

### Step 3: Verify .gitignore is Correct

Your `.gitignore` already has `.env` patterns, but verify:

```bash
# Check current .gitignore
cat .gitignore | grep env

# Should show:
# .env
# .env.local
# .env.development.local
# .env.test.local
# .env.production.local
# *.env
# !.env.example
# .env*.local
```

✅ `.gitignore` is already configured correctly.

---

### Step 4: Verify Credentials are Removed

```bash
# Search entire git history for exposed keys
git log --all --full-history --source --all -- "*/.env" "**/.env" ".env"

# Should return no results after cleanup

# Search for specific credential patterns
git log -S "SUPABASE_SERVICE_KEY" --all
git log -S "RESEND_API_KEY" --all
git log -S "GEMINI_API_KEY" --all

# Should return no results after cleanup
```

---

## 📊 Impact Assessment

### Potential Security Risks

1. **Database Access (CRITICAL)**
   - Service role key bypasses Row Level Security
   - Attacker could read/modify/delete ALL data
   - Could create admin accounts
   - Could export entire database

2. **Authentication Bypass (CRITICAL)**
   - JWT secret allows forging authentication tokens
   - Attacker could impersonate any user
   - Could access all user accounts

3. **Email Abuse (HIGH)**
   - Could send emails from your domain
   - Phishing attacks using your domain
   - Quota exhaustion

4. **AI Quota Abuse (MEDIUM)**
   - Could consume your Gemini API quota
   - Financial impact from API usage

5. **Waitlist Data Access (HIGH)**
   - Access to user email addresses
   - Privacy violation (GDPR/CCPA)

---

## 🔍 Monitoring & Detection

After rotating credentials, monitor for suspicious activity:

### Supabase Dashboard
1. Go to: https://supabase.com/dashboard/project/twzfaizeyqwevmhjyicz
2. Check "Logs" → "API" for unusual requests
3. Check "Database" → "Roles" for unauthorized users
4. Check "Auth" → "Users" for suspicious accounts

### Resend Dashboard
1. Go to: https://resend.com/emails
2. Check for unauthorized emails sent
3. Review API usage logs

### Gemini API Console
1. Go to: https://aistudio.google.com/app/apikey
2. Check usage metrics for spikes

---

## 📝 Post-Incident Actions

### 1. Audit Database for Unauthorized Changes
```sql
-- Check for recently created admin users
SELECT * FROM auth.users 
WHERE created_at > '2026-01-17 07:43:00' 
ORDER BY created_at DESC;

-- Check for suspicious data modifications
SELECT * FROM scripts 
WHERE updated_at > '2026-01-17 07:43:00' 
ORDER BY updated_at DESC;
```

### 2. Review Access Logs
- Check Supabase API logs for unusual patterns
- Look for requests from unknown IP addresses
- Check for bulk data exports

### 3. Notify Affected Users (if breach confirmed)
- Draft incident disclosure
- Notify users of potential data exposure
- Recommend password changes

### 4. Update Security Practices
- Implement secrets management (e.g., Doppler, AWS Secrets Manager)
- Add pre-commit hooks to prevent credential commits
- Regular security audits
- Implement least-privilege access

---

## 🛡️ Prevention Measures

### 1. Install git-secrets or gitleaks

```bash
# Install gitleaks
brew install gitleaks

# Scan repository
gitleaks detect --source . --verbose

# Install as pre-commit hook
gitleaks protect --staged --verbose
```

### 2. Use Environment Variable Management

**Option A: Doppler (Recommended)**
```bash
# Install Doppler CLI
brew install dopplerhq/cli/doppler

# Login and setup
doppler login
doppler setup

# Run app with Doppler
doppler run -- python app.py
```

**Option B: direnv**
```bash
# Install direnv
brew install direnv

# Add to shell config
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc

# Use .envrc instead of .env
```

### 3. Add Pre-commit Hook

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Prevent committing .env files

if git diff --cached --name-only | grep -E "\.env$|\.env\..*$"; then
    echo "❌ ERROR: Attempting to commit .env file!"
    echo "Please remove .env files from staging area"
    exit 1
fi

# Check for potential secrets
if git diff --cached | grep -E "SUPABASE_SERVICE_KEY|JWT_SECRET|API_KEY"; then
    echo "⚠️  WARNING: Potential secret detected in commit!"
    echo "Please review your changes carefully"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
```

### 4. Railway Environment Variables

Ensure all production secrets are ONLY in Railway, never in code:

```bash
# List Railway environment variables
railway variables

# Add new variable
railway variables set SUPABASE_SERVICE_KEY=<new-key>
```

---

## ✅ Completion Checklist

- [ ] **CRITICAL:** Rotate Supabase service_role key
- [ ] **CRITICAL:** Rotate Supabase JWT secret
- [ ] **CRITICAL:** Rotate Notel Supabase service_role key
- [ ] Rotate Resend API key
- [ ] Rotate Gemini API key
- [ ] Update Railway environment variables
- [ ] Update local `.env` file
- [ ] Remove `.env` from git history using git-filter-repo
- [ ] Force push cleaned history to GitHub
- [ ] Verify credentials removed from history
- [ ] Audit database for unauthorized access
- [ ] Review Supabase API logs
- [ ] Review Resend email logs
- [ ] Install gitleaks pre-commit hook
- [ ] Document incident in security log
- [ ] Update team on security practices

---

## 📞 Support Contacts

- **Supabase Support:** https://supabase.com/dashboard/support
- **Resend Support:** support@resend.com
- **GitGuardian:** https://dashboard.gitguardian.com/

---

## 🔗 References

- [GitGuardian Incident Response](https://docs.gitguardian.com/internal-repositories-monitoring/incidents/incident-response)
- [GitHub: Removing Sensitive Data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [git-filter-repo Documentation](https://github.com/newren/git-filter-repo)
- [OWASP: Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

**REMEMBER:** The credentials are ALREADY exposed. Cleaning git history alone is NOT sufficient. You MUST rotate all credentials first.
