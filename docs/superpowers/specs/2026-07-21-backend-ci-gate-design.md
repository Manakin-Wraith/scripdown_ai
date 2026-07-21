# Backend test suite CI gate — design

**Date:** 2026-07-21
**Status:** Approved, ready for implementation plan
**Backlog item:** `docs/BACKLOG.md` — "Backend test suite has no CI gate"

## Problem

There is no `.github/workflows/` directory in this repo. The only checks
currently wired to GitHub PRs are GitGuardian (secret scanning) and Vercel's
preview-deploy + comment bot — both frontend/deploy concerned. The 427-test
backend suite (`backend/tests/`) is only ever run locally; a backend
regression can merge to `main` with a fully green PR (confirmed on PR #7).

## Decisions

- **Trigger:** `pull_request`, unconditional — no path filter on
  `backend/**`. The suite runs in ~38s, and unconditional coverage catches
  regressions from changes that touch shared code without obviously
  looking like "backend" changes.
- **Credentials:** dummy values checked directly into the workflow YAML, not
  GitHub repo secrets. Verified live: `pytest tests/` passes all 427 tests
  with `env -i` (no real environment, no `.env` file) and only placeholder
  values for `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`,
  `RESEND_API_KEY`, `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`,
  `PAYFAST_SANDBOX`. `backend/utils/env_validator.py` only checks presence,
  not validity, and the test suite mocks the Supabase boundary
  (`tests/conftest.py::FakeSupabase`) rather than hitting a real database.
  No secrets are needed for this workflow.
- **Enforcement:** advisory only in this change — the check appears in the
  PR checks list but does not block merge. Flipping it to required (branch
  protection) is a deliberate follow-up once it's proven stable across a
  few real PRs, not bundled into this change.
- **Scope:** backend only. An equivalent `npm run build` frontend gate is
  out of scope here and tracked as its own backlog item.

## Implementation

New file: `.github/workflows/backend-tests.yml`

- Runs on `ubuntu-latest`.
- `actions/setup-python@v5` with `python-version: '3.13'` and
  `cache: 'pip'` (cache key derived from `backend/requirements.txt`) to keep
  runs fast.
- `pip install -r backend/requirements.txt`.
- `pytest tests/`, run with `working-directory: backend`.
- Dummy env vars set at the job or step level (see Decisions above).

No other files change. No branch protection / repo settings change in this
pass — that's the deferred follow-up noted under Enforcement.

## Testing

- Push the workflow on a branch and open/update a PR; confirm the check
  appears in the PR checks list and reports success.
- Deliberately break a test locally first (sanity check only, not committed)
  to confirm the workflow would report failure — or rely on the fact that
  `pytest tests/` already exits non-zero on failure, which is standard
  `pytest` behavior and doesn't need re-proving.

## Follow-ups (not in this change)

- Flip the check to required via branch protection once stable.
- Add an equivalent frontend `npm run build` CI gate (separate backlog item).
