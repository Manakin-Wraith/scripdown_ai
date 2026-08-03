# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product Overview

ScripDown AI (branded **SlateOne**, live at app.slateone.studio) is an AI-powered screenplay breakdown and production-management SaaS: PDF script upload → scene detection → AI extraction of breakdown elements (cast, props, wardrobe, etc.) → scheduling (stripboard), team collaboration, and production reports. Pricing is a two-tier PayFast subscription model (merged 2026-07-18; see `docs/SPEC_Tiered_Business_Model.md`): **Tier 1 — Solo / Pay-Per-Breakdown** (ZAR 2,250 per AI analysis, no team features) and **Tier 2 — Team License**, sold on 4 cadences — monthly (ZAR 1,850/mo, 0 seats included), 3-month (ZAR 5,500, 1 seat), 6-month (ZAR 9,500, 2 seats), annual (ZAR 18,500/yr, 3 seats) — unlimited breakdowns, full team collaboration, extra seats beyond the included bundle always a flat ZAR 250/month. The old flat $49/month Wise subscription and the credit/pack system before that are both fully deprecated — `credit_routes`/`credit_service` are gone entirely, not just unregistered.

## Repo Layout

Two independently deployed apps plus Supabase assets:

- `frontend/` — React 18 + Vite SPA (plain JavaScript/JSX, no TypeScript). Deployed to Vercel; `frontend/vercel.json` rewrites `/api/*` to the Railway backend.
- `backend/` — Flask API (Python 3.13), deployed to Railway via gunicorn (`backend/Procfile`, `backend/railway.json`).
- `supabase/functions/` — Supabase Edge Functions (beta payment, waitlist welcome email).
- `docs/` — feature specs and roadmap (`SLATEONE_FEATURES.md` is the product capability overview).
- `scripts/` — one-off maintenance/backfill scripts run against the database.

## Commands

### Frontend (run in `frontend/`)
```bash
npm run dev       # Vite dev server on :5173
npm run build     # production build
npm run lint      # eslint .
```

### Backend (run in `backend/`; a venv exists at `backend/venv/`)
```bash
pip install -r requirements.txt
python app.py                          # dev server on :5000
pytest tests/                          # run test suite
pytest tests/test_screenplay_parser.py::TestClassName::test_name   # single test
```

Backend refuses to start unless required env vars are set (`utils/env_validator.py`): `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `RESEND_API_KEY`; `GEMINI_API_KEY`/`OPENAI_API_KEY` recommended for AI analysis. Frontend needs `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and optionally `VITE_API_URL` (defaults to `http://localhost:5000`).

Setting `FLASK_ENV=development` enables an auth bypass in the backend (`DEV_USER_ID`).

## Architecture

### Data & auth flow
- Supabase is the single Postgres database and auth provider. The frontend talks to Supabase directly for auth (`frontend/src/lib/supabase.js`) and to the Flask API for everything else via `frontend/src/services/apiService.js` — an axios instance that attaches a cached Supabase JWT to every request.
- Backend JWT verification lives in `backend/middleware/auth.py`: ES256 via the Supabase JWKS endpoint by default, with legacy HS256 (`SUPABASE_JWT_SECRET`) as optional fallback. Routes use its decorators to require auth.
- The backend uses the Supabase **service role key** (bypasses RLS) for database access via `supabase-py`; connection helpers are in `backend/db/`.

### Backend structure
- `app.py` registers Flask blueprints from `routes/` — one blueprint per domain (scripts, analysis, reports, schedules, admin, email campaigns, etc.). Route registration order matters in one case: `webhook_bp` must be registered before `campaign_bp`.
- `routes/` handle HTTP concerns only; business logic lives in `services/`. Admin and email-campaign routes are superuser-only.
- **Script extraction pipeline** (`services/extraction_pipeline.py`) is the core system — a two-phase, page-based design:
  1. **Upload (synchronous):** parse PDF per page → store in `script_pages` (content-hashed for idempotency) → regex-detect scene headers → create `scene_candidates` → return `script_id` immediately.
  2. **Analysis (background, resumable):** a threading-based job queue (`services/analysis_queue_service.py`, `analysis_worker.py`) processes each scene with AI (Gemini primary, OpenAI alternative via `gemini_service.py`), then runs aggregate jobs (characters, locations, story arc). Scene numbers come from the script text, never invented by the AI; failed scenes retry independently.
- Supporting parse layers: `screenplay_parser.py` (grammar parse with regex fallback), `text_normalizer.py`, `entity_resolver.py` (duplicate character-name merging), `utils/pdf_parser.py`, `utils/scene_calculations.py` (scene eighths/page math).
- Report generation (`services/report_service.py`) renders production PDFs with WeasyPrint; transactional email goes through Resend (`email_service.py`, templates in `email_templates/`).

### Frontend structure
- `src/pages/` for routed pages, `src/components/` grouped by domain (breakdown, schedule, reports, team, editor, etc.).
- Global state via React contexts in `src/context/`: `AuthContext`, `ScriptContext`, `AnalysisContext` (polls background analysis progress), `StoryDayContext`, plus `ToastContext`/`ConfirmDialogContext` for UI feedback.
- All backend calls go through the single `apiService.js`; don't create per-feature axios instances.
