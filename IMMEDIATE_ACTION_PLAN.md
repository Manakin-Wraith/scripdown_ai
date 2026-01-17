# ScripDown AI - Immediate Action Plan
**Priority:** Critical Issues Requiring Immediate Attention  
**Timeline:** Week 1

---

## 🚨 Critical Issues (Fix This Week)

### 1. Remove Duplicate Email Services
**Impact:** High - Code bloat, maintenance confusion

```bash
# Delete these files immediately:
rm backend/services/email_service_enhanced.py
rm backend/services/email_service_improved.py
```

**Verification:**
```bash
grep -r "email_service_enhanced\|email_service_improved" backend/
# Should return no results
```

---

### 2. Fix Database Schema Documentation
**Impact:** High - Misleading documentation

**Option A: Delete MySQL schema**
```bash
rm backend/db/schema.sql
```

**Option B: Mark as deprecated**
```sql
-- Add to top of backend/db/schema.sql:
-- ⚠️ DEPRECATED: This MySQL schema is NOT used in production
-- ⚠️ Production uses Supabase (PostgreSQL)
-- ⚠️ For current schema, see Supabase Dashboard
```

---

### 3. Fix requirements.txt Duplicate
**Impact:** Medium - Deployment issues

**File:** `backend/requirements.txt`

```diff
- PyMuPDF==1.25.1
- PyMuPDF
+ pymupdf==1.25.1
```

**Verification:**
```bash
pip install -r backend/requirements.txt --dry-run
```

---

### 4. Add Environment Variable Validation
**Impact:** High - Prevents runtime failures

**Create:** `backend/utils/env_validator.py`

```python
import os
import sys

REQUIRED_VARS = {
    'SUPABASE_URL': 'Supabase project URL',
    'SUPABASE_ANON_KEY': 'Supabase anonymous key',
    'SUPABASE_SERVICE_KEY': 'Supabase service role key',
    'SUPABASE_JWT_SECRET': 'JWT secret for token verification',
    'RESEND_API_KEY': 'Resend email service API key',
    'GEMINI_API_KEY': 'Google Gemini API key'
}

def validate_required_env():
    """Validate all required environment variables are set."""
    missing = []
    
    for var, description in REQUIRED_VARS.items():
        if not os.getenv(var):
            missing.append(f"  - {var}: {description}")
    
    if missing:
        print("❌ Missing required environment variables:")
        print("\n".join(missing))
        print("\nPlease set these in your .env file")
        sys.exit(1)
    
    print("✅ All required environment variables are set")
```

**Update:** `backend/app.py`

```python
# Add after line 16 (after load_dotenv())
from utils.env_validator import validate_required_env
validate_required_env()
```

---

### 5. Consolidate Migration Naming
**Impact:** Medium - Migration order confusion

**Current conflicts:**
- `001_add_script_metadata.sql`
- `001_create_early_access_users.sql`
- `001_create_early_access_users_safe.sql`

**Recommendation:** Rename to sequential order

```bash
cd backend/db/migrations/

# Rename files to proper sequence
mv 001_create_early_access_users_safe.sql 007_create_early_access_users.sql
mv add_analysis_cache.sql 008_add_analysis_cache.sql
mv create_email_tracking.sql 009_create_email_tracking.sql

# Delete duplicate
rm 001_create_early_access_users.sql
rm 005_early_access_users.sql  # Also duplicate
```

---

## 📋 Verification Checklist

After completing the above actions, run these checks:

### Backend Health Check
```bash
cd backend
python -c "from app import app; print('✅ App imports successfully')"
python -c "from utils.env_validator import validate_required_env; validate_required_env()"
```

### Dependency Check
```bash
pip install -r requirements.txt
pip list | grep -i pymupdf  # Should show only one entry
```

### Code Quality Check
```bash
# Check for duplicate email services
find . -name "*email_service*.py" | wc -l
# Should return 2 (email_service.py and email_tracking_service.py)
```

### Migration Check
```bash
cd backend/db/migrations
ls -1 *.sql | sort
# Should show sequential numbering: 001, 002, 003, etc.
```

---

## 🎯 Success Criteria

- [ ] Only 2 email service files remain (email_service.py, email_tracking_service.py)
- [ ] schema.sql is deleted or marked DEPRECATED
- [ ] requirements.txt has no duplicates
- [ ] Environment validation runs on app startup
- [ ] All migrations have sequential numbering
- [ ] Backend starts without errors
- [ ] All environment variables are documented

---

## 📊 Estimated Time

- **Task 1:** 5 minutes
- **Task 2:** 5 minutes
- **Task 3:** 5 minutes
- **Task 4:** 30 minutes
- **Task 5:** 15 minutes

**Total:** ~1 hour

---

## 🔄 Next Steps (Week 2)

After completing this immediate action plan, proceed to:

1. **Testing Infrastructure** - Set up pytest and Jest
2. **Dependency Updates** - Update outdated packages
3. **Code Cleanup** - Remove commented-out code in App.jsx

See `CODEBASE_AUDIT_REPORT.md` for full recommendations.
