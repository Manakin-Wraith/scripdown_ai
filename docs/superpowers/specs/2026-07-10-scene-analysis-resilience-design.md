# Scene Analysis Resilience — Design Spec

**Date:** 2026-07-10
**Status:** Approved (design) — pending implementation plan
**Author:** Claude + user

## Problem

Two scenes in a production script failed analysis with these user-facing messages:

- Scene 1: `Analysis failed: 404 This model models/gemini-2.5-flash is no longer available. Please update your code to use a newer model...`
- Scene 2: `Analysis failed: 504 The request timed out. Please try again.`

### Root cause (investigated, confirmed)

Both are **transient-class failures** that the pipeline turns into permanent, user-hostile failures:

1. **No retry.** The live analysis path (`routes/supabase_routes.py`, the `analyze_scene` HTTP endpoint and its inner analysis helper) calls `model.generate_content(...)` exactly once. A 504 timeout or an intermittent 404 permanently fails the scene. A live test proved `gemini-2.5-flash` *succeeds on retry* seconds after throwing the 404 — the model is entering deprecation and returns intermittent 404s during the wind-down (`gemini-2.0-flash` is already permanently retired).

2. **Dying default model.** `utils/gemini_config.py` defaults to `gemini-2.5-flash`, which is being aged out. `get_gemini_model_name()` reads `GEMINI_MODEL` env var or this default.

3. **Errors swallowed into fake-success.** The inner analysis function's `except Exception` block returns a *fallback dict* whose `description` is `f'Analysis failed: {str(e)}'`. The endpoint then writes that fallback with `analysis_status: 'complete'`. So a failed scene is stored as a successful scene with an empty breakdown and a raw exception string dumped into user-facing content. There is no clean "this scene failed, retry it" signal.

4. **No user recovery path in the UI.** A per-scene re-analyze **endpoint already exists** (`POST /api/scenes/<scene_id>/analyze`), but the frontend does not surface failed scenes or expose a re-analyze control.

All three of the user's asks — fix the errors, let users re-analyze specific scenes, make error messaging friendly — are the same underlying problem (transient-failure handling) broken at three layers.

## Goals

- Transient Gemini failures (timeout, rate-limit, 5xx, intermittent model-404) are retried automatically and usually succeed without user involvement.
- The default model stops hitting dead-model 404s (self-healing against deprecation).
- A scene that genuinely fails after retries is stored as **failed**, not fake-complete, with a **friendly** error message and no poisoned breakdown data.
- Users can re-analyze a single failed scene, or retry all failed scenes for a script in one click.
- One shared, tested code path for calling Gemini — no per-call-site fragility.

## Non-Goals (YAGNI)

- No queue/backoff infrastructure beyond in-process retry.
- No automatic end-of-run re-run of failed scenes (explicitly deferred; manual retry chosen).
- No change to the analysis prompt, extraction schema, or story-day logic beyond skipping recalc for failed scenes.
- No per-user model selection UI (env var remains the override mechanism).

## Global Constraints

- Backend: Flask / Python 3.11 on Railway; Supabase (service-role) for DB. Frontend: React 18 + Vite (plain JS/JSX), all backend calls via `frontend/src/services/apiService.js`.
- **No "AI" in any user-facing copy.** Use "analysis", "analysis service", "analysis engine".
- Default model becomes `gemini-flash-latest`. `GEMINI_MODEL` env var still overrides per-environment with no deploy.
- No test may call the real Gemini API — the model is always mocked.
- Existing 179 backend tests must stay green; the analysis-success path is unchanged in behavior.

---

## Architecture

Five layers, one design pass:

1. **Shared resilient client** — `backend/services/gemini_client.py`, the single entry point for Gemini calls.
2. **Error taxonomy & retry policy** — inside the client; classifies exceptions and decides retry + user copy.
3. **Failed-state data model** — new `scenes.analysis_error` / `scenes.analysis_error_category` columns; failed scenes written as `failed`, not `complete`.
4. **Re-analyze surface** — reuse the existing single-scene endpoint; add a `retry-failed` bulk endpoint; surface failed state + controls in the UI.
5. **Testing** — unit tests for client/classifier, endpoint tests for failed-state and retry-failed, regression safety.

### Section 1 — Shared resilient Gemini client

New module `backend/services/gemini_client.py` exposing:

```python
class GeminiError(Exception):
    def __init__(self, category: str, user_message: str, raw: Exception | None = None):
        self.category = category          # e.g. "timeout", "rate_limit", ...
        self.user_message = user_message  # friendly, no "AI"
        self.raw = raw
        super().__init__(user_message)

def generate_with_retry(prompt: str, *, generation_config=None, max_attempts: int = 3) -> str:
    """Call Gemini with retry/backoff on transient errors.

    Builds the model from get_gemini_model_name() so flash-latest / env override apply.
    Returns response.text on success.
    Raises GeminiError(category, user_message, raw) when retries are exhausted or the
    error is non-retryable.
    """
```

Behavior:
- Builds the model via `genai.GenerativeModel(get_gemini_model_name())` on each attempt (so an env-var/model change is picked up).
- Calls `model.generate_content(prompt, generation_config=generation_config)`.
- On a **retryable** category, sleeps with exponential backoff (base ≈1s → 2s → 4s; `rate_limit` uses a longer base ≈4s) and retries up to the category's attempt budget.
- On success returns `response.text` (caller does its own JSON cleanup/parse as today).
- On exhausted/non-retryable, raises `GeminiError`.
- `genai.configure(api_key=...)` continues to be handled by callers (as today) or centralized in the client — implementer's choice, but must not require each call site to duplicate key loading. Preference: centralize `configure` in the client using `GEMINI_API_KEY`.

**Call sites migrated to the client** (their local `get_model()` helpers removed):
- `routes/supabase_routes.py` — inner scene-analysis helper (the live path).
- `services/scene_enhancer.py:110`.
- `services/analysis_service.py:151`, `:247`.
- `services/analysis_worker.py:81`.

JSON parsing stays at each call site (the client returns raw text). A JSON parse failure at the call site is converted to `GeminiError("bad_response", ...)` so failed-state handling is uniform.

### Section 2 — Error taxonomy & retry policy

The client maps each raised exception to a category. Classification is by inspecting the exception type/message for status codes and known phrases (the `google-generativeai==0.3.0` SDK surfaces `google.api_core.exceptions` types and HTTP status codes in messages).

| Category | Triggers | Retried? | Attempt budget | User message |
|---|---|---|---|---|
| `timeout` | 504, DeadlineExceeded, "timed out" | yes | 3 | The analysis service timed out — this is usually temporary. Click Re-analyze to try again. |
| `rate_limit` | 429, ResourceExhausted | yes (longer backoff) | 3 | The analysis service is busy right now. Wait a moment and Re-analyze. |
| `server` | 500 / 502 / 503, ServiceUnavailable, InternalServerError | yes | 3 | The analysis service had a temporary error. Click Re-analyze to try again. |
| `model_unavailable` | 404 "no longer available" / NotFound | yes, once | 2 | The analysis engine was updated. Click Re-analyze to continue. |
| `bad_response` | JSON parse failure / empty response (raised by caller) | no | 1 | Analysis returned an unreadable result for this scene. Click Re-analyze. |
| `unknown` | anything else | no | 1 | Analysis couldn't complete for this scene. Click Re-analyze to try again. |

Rationale:
- `model_unavailable` retries **once** (the live 2.5 404 was intermittent) but is really fixed by the `flash-latest` default — we do not burn 3 retries × N scenes on a truly-dead model.
- `bad_response` is not auto-retried — re-running the same prompt rarely fixes a parse failure; that is what the manual Re-analyze button is for.

Model default change: `utils/gemini_config.py` → `DEFAULT_GEMINI_MODEL = "gemini-flash-latest"`.

### Section 3 — Failed-state data model

**Schema (two migrations against `scenes`):**
- `analysis_error text` — the friendly, user-facing message (nullable).
- `analysis_error_category text` — machine-readable category for UI icon/behavior (nullable).

**Write path change** (in `analyze_scene` and the worker analysis paths): when the analysis call raises `GeminiError` (or the call-site JSON parse raises `bad_response`), write the scene as:

- `analysis_status: 'failed'`
- `analysis_error: <GeminiError.user_message>`
- `analysis_error_category: <GeminiError.category>`
- breakdown fields (`characters`, `props`, `wardrobe`, …, `description`) left **untouched/empty** — no fake data.
- **Skip** `recalculate_story_days(...)` for this scene (a failed scene has no reliable `is_new_story_day`), so the day sequence is not corrupted.

On a later **successful** re-analysis of that scene, the success path must **clear** `analysis_error` and `analysis_error_category` (set to null) and set `analysis_status: 'complete'`, so a recovered scene shows no stale error.

**Backfill migration (one-time)** for scenes already poisoned by the old behavior:
- Target scenes where `analysis_status = 'complete'` AND `description LIKE 'Analysis failed:%'`.
- Set `analysis_status = 'failed'`, `analysis_error_category = 'unknown'`, `analysis_error = 'Analysis couldn''t complete for this scene. Click Re-analyze to try again.'`, and clear `description` to empty string.
- This makes historical failures show the new failed state and become retryable.

### Section 4 — Re-analyze surface

**Backend:**
- **Reuse** `POST /api/scenes/<scene_id>/analyze` unchanged for single-scene re-analyze.
- **Add** `POST /api/scripts/<script_id>/scenes/retry-failed`:
  - Auth + subscription gate identical to the existing bulk analyze endpoint.
  - Selects scenes for the script with `analysis_status = 'failed'`.
  - Enqueues them through the **existing** bulk background analysis path (same job/thread mechanism as `analyze_bulk_scenes`).
  - Returns `202 Accepted` with `{ "retrying": <count> }`. If zero failed scenes, returns `200` with `{ "retrying": 0 }`.

**Frontend (`frontend/src/`, via `apiService.js`):**
- **Per-scene** (`components/scenes/SceneViewer.jsx`): a scene with `analysis_status === 'failed'` renders a distinct **failed state** — warning styling, the `analysis_error` text, and a **Re-analyze** button — instead of an empty breakdown. The button calls the existing single-scene endpoint, shows an inline spinner, and refreshes the scene on completion.
- **Bulk** (`components/scenes/ScriptSummary.jsx`): when any scene is `failed`, show a **"Retry all failed (N)"** button wired to the new endpoint, reusing the existing analysis-progress polling (`AnalysisContext`).
- New `apiService.js` methods: `reanalyzeScene(sceneId)` (if not already present) and `retryFailedScenes(scriptId)`.

### Section 5 — Error handling summary

- Transient errors: retried in-client; on success the user never sees them.
- Exhausted/non-retryable: surfaced as a failed scene with friendly copy; recoverable via Re-analyze.
- Aggregate jobs (characters/locations/story arc) run on whatever scenes succeeded; failed scenes contribute nothing rather than empty/garbage data.
- Story-day recalc is skipped for failed scenes and runs normally once they recover.

## Testing

- **Unit — `gemini_client`:** with a mocked model, verify: retries on `timeout`/`rate_limit`/`server` up to budget then raises; retries `model_unavailable` exactly once; does **not** retry `bad_response`/`unknown`; returns `response.text` on success; backoff is invoked (patch sleep). No live API.
- **Unit — classifier:** each exception shape (404-no-longer-available, 504, 429, 500, arbitrary) → correct `category` + friendly `user_message` (assert no substring "AI").
- **Endpoint — `analyze_scene`:** forcing a `GeminiError` writes `analysis_status='failed'`, sets `analysis_error`/`analysis_error_category`, leaves breakdown empty, and skips story-day recalc. A subsequent forced-success clears the error fields and sets `complete`.
- **Endpoint — `retry-failed`:** selects only `failed` scenes, returns the count, and enqueues via the bulk path; zero-failed returns `{retrying: 0}`.
- **Regression:** existing 179 backend tests stay green; the success path is behavior-identical.

## Rollout notes

- Deploy backend (client + endpoint + model default) and run the two schema migrations + the backfill migration together.
- Frontend deploys separately (Vercel); failed-state UI degrades gracefully if the backend columns are absent (treats missing `analysis_error` as generic copy), so ordering is not strict — but backend-first is preferred so the columns exist when the UI reads them.

## Open questions

None — all design decisions resolved during brainstorming.
