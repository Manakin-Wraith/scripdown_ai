# Backend Test Suite CI Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a GitHub Actions workflow that runs `backend/tests/` (pytest) on every pull request, so a backend regression can no longer merge to `main` with a fully green PR.

**Architecture:** A single new workflow file, `.github/workflows/backend-tests.yml`. One job on `ubuntu-latest`: checkout, set up Python 3.13 with pip caching, install `backend/requirements.txt`, run `pytest tests/` from the `backend/` directory with dummy (non-secret) environment variables set inline in the YAML. No application code changes. No branch-protection changes in this plan — the check ships advisory-only.

**Tech Stack:** GitHub Actions, `actions/checkout@v4`, `actions/setup-python@v5`, Python 3.13, pytest (already a dependency in `backend/requirements.txt` — verify in Task 1).

## Global Constraints

- Trigger: `pull_request`, unconditional — no path filter on `backend/**` (spec decision, confirmed with user).
- Credentials: dummy string values checked directly into the workflow YAML — never GitHub repo secrets. Verified live in the design spec: `pytest tests/` passes all 427 tests with `env -i` (no real environment) and only placeholder values for `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `RESEND_API_KEY`, `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`, `PAYFAST_SANDBOX`.
- Enforcement: advisory only. Do not touch branch protection / repo settings in this plan.
- Scope: backend only. Do not add a frontend `npm run build` gate — that is a separate backlog item.
- Python version: 3.13 (matches `backend/venv` and `CLAUDE.md`: "Flask API (Python 3.13)").

---

### Task 1: Create the backend-tests workflow

**Files:**
- Create: `.github/workflows/backend-tests.yml`

**Interfaces:**
- Consumes: `backend/requirements.txt` (existing, unmodified), `backend/tests/` (existing suite, unmodified).
- Produces: a GitHub Actions check named "backend-tests / test" visible on PRs (exact name confirmed in Task 2 once the workflow has run).

- [ ] **Step 1: Confirm pytest is a declared dependency**

Run: `grep -i "^pytest" backend/requirements.txt`
Expected: a line matching `pytest` (e.g. `pytest==8.x.x` or similar). If this returns nothing, stop and add `pytest` to `backend/requirements.txt` pinned to the version installed in `backend/venv` (`backend/venv/bin/pip show pytest`) before continuing — the workflow installs only from `requirements.txt`, not the local venv.

- [ ] **Step 2: Write the workflow file**

Create `.github/workflows/backend-tests.yml`:

```yaml
name: backend-tests

on:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      SUPABASE_URL: https://dummy.supabase.co
      SUPABASE_ANON_KEY: dummy
      SUPABASE_SERVICE_KEY: dummy
      RESEND_API_KEY: dummy
      PAYFAST_MERCHANT_ID: "10000100"
      PAYFAST_MERCHANT_KEY: dummy
      PAYFAST_SANDBOX: "true"
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        working-directory: backend
        run: pip install -r requirements.txt

      - name: Run tests
        working-directory: backend
        run: pytest tests/
```

- [ ] **Step 3: Validate YAML syntax locally**

Run: `python3 -c "import yaml, sys; yaml.safe_load(open('.github/workflows/backend-tests.yml'))" && echo VALID`
Expected: `VALID` printed, no exception. (If `PyYAML` isn't available in the outer environment, run this inside `backend/venv` instead: `backend/venv/bin/python -c "import yaml; yaml.safe_load(open('.github/workflows/backend-tests.yml')); print('VALID')"`.)

- [ ] **Step 4: Sanity-check the install+test commands locally with only dummy env vars**

Run:
```bash
cd backend
env -i PATH="$PATH" HOME="$HOME" \
  SUPABASE_URL="https://dummy.supabase.co" \
  SUPABASE_ANON_KEY="dummy" \
  SUPABASE_SERVICE_KEY="dummy" \
  RESEND_API_KEY="dummy" \
  PAYFAST_MERCHANT_ID="10000100" \
  PAYFAST_MERCHANT_KEY="dummy" \
  PAYFAST_SANDBOX="true" \
  venv/bin/python -m pytest tests/ -q
```
Expected: `427 passed` (or the current suite count — if it differs, that's fine as long as the run ends in `passed` with `0 failed`, confirming the exact env-var set the workflow will use is sufficient).

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/backend-tests.yml
git commit -m "ci: add backend pytest gate on pull requests

Runs backend/tests/ (pytest) on every PR via GitHub Actions. Advisory
only for now -- not wired into branch protection yet. Uses dummy,
non-secret env var values since the test suite mocks the Supabase
boundary and never makes real network calls."
```

---

### Task 2: Verify the workflow runs on a real PR

**Files:** none (verification only).

**Interfaces:**
- Consumes: the workflow committed in Task 1.
- Produces: confirmation the check name and pass/fail behavior work as expected — needed before this backlog item can be marked resolved.

- [ ] **Step 1: Push the branch**

Run: `git push -u origin chore/backend-ci-gate`
Expected: push succeeds, branch appears on the remote.

- [ ] **Step 2: Open a PR (or use the existing one if already open) and confirm the check appears**

Run: `gh pr create --title "ci: add backend pytest gate on pull requests" --body "Adds .github/workflows/backend-tests.yml, running backend/tests/ on every PR. Advisory only (not required via branch protection yet). Uses dummy, non-secret env var values -- verified locally that the full 427-test suite passes with no real credentials."` (skip if a PR for this branch already exists — check with `gh pr view chore/backend-ci-gate` first).

Then run: `gh pr checks --watch` (from a directory on the `chore/backend-ci-gate` branch).
Expected: a check named `backend-tests / test` (or `test` under the `backend-tests` workflow) appears in the list and reports `pass`, alongside the existing GitGuardian/Vercel checks.

- [ ] **Step 3: Confirm it would fail on a real regression (negative test)**

On a scratch local branch off `chore/backend-ci-gate` (do not push), temporarily break one test — e.g. edit `backend/tests/test_authorization.py`'s `test_role_rank_order` to assert something false — then run the same dummy-env pytest command from Task 1 Step 4 locally and confirm it reports `1 failed`. Discard the change (`git checkout -- backend/tests/test_authorization.py` or equivalent) without pushing or committing it. This confirms the workflow's `pytest tests/` step will surface a real regression as a failed check, without needing to actually push a broken commit to prove it.

Expected: local run shows `1 failed`, confirming non-zero exit on failure (standard pytest behavior — this step is a sanity check, not new behavior).

- [ ] **Step 4: Report status back to the user**

No commit in this task (Task 1's commit already covers the workflow file). Summarize for the user: PR URL, check name, pass/fail confirmation, and the note that flipping this check to "required" via branch protection is a deferred follow-up (per the spec).

---

## Self-Review Notes

- **Spec coverage:** trigger scope (unconditional pull_request) ✓ Task 1 Step 2. Dummy credentials, no secrets ✓ Task 1 Steps 2 & 4. Advisory-only ✓ explicitly called out, no branch-protection task included. Backend-only scope ✓ no frontend task added. Pip caching ✓ Task 1 Step 2 (`cache: 'pip'`).
- **Placeholder scan:** none found — every step has literal commands/YAML.
- **Type/name consistency:** single artifact (`backend-tests.yml`), name used consistently across both tasks; no function signatures to cross-check since this is infra-only.
