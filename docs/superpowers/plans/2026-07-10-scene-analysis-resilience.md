# Scene Analysis Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Gemini scene analysis resilient to transient failures — retry automatically, stop masking failures as success, and let users re-analyze scenes that still fail.

**Architecture:** A single shared `gemini_client.generate_with_retry()` wraps every Gemini call with retry/backoff and typed error classification. The inner analysis helper stops swallowing exceptions (the root bug); the single-scene and bulk paths record genuinely-failed scenes as `analysis_status='failed'` with a friendly message and category. A new `retry-failed` endpoint plus per-scene and bulk UI controls let users recover.

**Tech Stack:** Flask / Python 3.11 (backend, Railway), `google-generativeai==0.3.0`, Supabase Postgres (service-role), React 18 + Vite (frontend, plain JS/JSX).

## Global Constraints

- No "AI" in any user-facing copy. Use "analysis", "analysis service", "analysis engine".
- Default model is `gemini-flash-latest`; `GEMINI_MODEL` env var still overrides per-environment with no deploy.
- No test may call the real Gemini API — always mock the model / inject sleep.
- Existing backend test suite (`pytest backend/tests/`) must stay green; the analysis-success path stays behavior-identical.
- Failed analysis is recorded as `analysis_status='failed'` (distinct from the existing `'error'` data-guard status used for "no scene text"). On a later successful re-analysis, `analysis_error` and `analysis_error_category` are cleared.
- All frontend backend calls go through `frontend/src/services/apiService.js`.
- Friendly copy strings (verbatim):
  - `timeout`: `The analysis service timed out — this is usually temporary. Click Re-analyze to try again.`
  - `rate_limit`: `The analysis service is busy right now. Wait a moment and Re-analyze.`
  - `server`: `The analysis service had a temporary error. Click Re-analyze to try again.`
  - `model_unavailable`: `The analysis engine was updated. Click Re-analyze to continue.`
  - `bad_response`: `Analysis returned an unreadable result for this scene. Click Re-analyze.`
  - `unknown`: `Analysis couldn't complete for this scene. Click Re-analyze to try again.`

---

### Task 1: Shared resilient Gemini client + error taxonomy

**Files:**
- Create: `backend/services/gemini_client.py`
- Test: `backend/tests/test_gemini_client.py`

**Interfaces:**
- Produces:
  - `class GeminiError(Exception)` with attributes `category: str`, `user_message: str`, `raw: Exception | None`.
  - `classify_exception(exc: Exception) -> str` returning one of `timeout|rate_limit|server|model_unavailable|unknown`.
  - `generate_with_retry(prompt: str, *, generation_config=None, max_attempts: int = 3, _sleep=time.sleep) -> str` — returns `response.text`; raises `GeminiError` on terminal failure.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_gemini_client.py`:

```python
"""Unit tests for the resilient Gemini client. No live API calls."""
import pytest
from services import gemini_client as gc
from services.gemini_client import GeminiError, classify_exception, generate_with_retry


class FakeResp:
    def __init__(self, text):
        self.text = text


def _fake_model_factory(behaviors):
    """behaviors: list of callables; each call to generate_content pops the next.
    A callable returns a FakeResp or raises."""
    calls = {"n": 0}

    class FakeModel:
        def __init__(self, *_a, **_k):
            pass

        def generate_content(self, *_a, **_k):
            i = calls["n"]
            calls["n"] += 1
            return behaviors[i]()

    return FakeModel, calls


def test_success_returns_text(monkeypatch):
    FakeModel, calls = _fake_model_factory([lambda: FakeResp("hello")])
    monkeypatch.setattr(gc.genai, "GenerativeModel", FakeModel)
    out = generate_with_retry("p", _sleep=lambda _s: None)
    assert out == "hello"
    assert calls["n"] == 1


def test_timeout_retries_then_raises(monkeypatch):
    def boom():
        raise Exception("504 The request timed out")
    FakeModel, calls = _fake_model_factory([boom, boom, boom])
    monkeypatch.setattr(gc.genai, "GenerativeModel", FakeModel)
    with pytest.raises(GeminiError) as ei:
        generate_with_retry("p", _sleep=lambda _s: None)
    assert ei.value.category == "timeout"
    assert calls["n"] == 3  # 3 attempts


def test_timeout_recovers_on_retry(monkeypatch):
    def boom():
        raise Exception("504 timed out")
    FakeModel, calls = _fake_model_factory([boom, lambda: FakeResp("ok")])
    monkeypatch.setattr(gc.genai, "GenerativeModel", FakeModel)
    assert generate_with_retry("p", _sleep=lambda _s: None) == "ok"
    assert calls["n"] == 2


def test_model_unavailable_retries_once(monkeypatch):
    def boom():
        raise Exception("404 This model models/x is no longer available")
    FakeModel, calls = _fake_model_factory([boom, boom, boom])
    monkeypatch.setattr(gc.genai, "GenerativeModel", FakeModel)
    with pytest.raises(GeminiError) as ei:
        generate_with_retry("p", _sleep=lambda _s: None)
    assert ei.value.category == "model_unavailable"
    assert calls["n"] == 2  # budget of 2 for model_unavailable


def test_empty_text_is_bad_response_no_retry(monkeypatch):
    FakeModel, calls = _fake_model_factory([lambda: FakeResp("   ")])
    monkeypatch.setattr(gc.genai, "GenerativeModel", FakeModel)
    with pytest.raises(GeminiError) as ei:
        generate_with_retry("p", _sleep=lambda _s: None)
    assert ei.value.category == "bad_response"
    assert calls["n"] == 1


def test_classify_exception_shapes():
    assert classify_exception(Exception("504 timed out")) == "timeout"
    assert classify_exception(Exception("429 quota exceeded")) == "rate_limit"
    assert classify_exception(Exception("model no longer available")) == "model_unavailable"
    assert classify_exception(Exception("503 service unavailable")) == "server"
    assert classify_exception(Exception("weird boom")) == "unknown"


def test_messages_never_say_ai():
    for cat in ("timeout", "rate_limit", "server", "model_unavailable", "bad_response", "unknown"):
        assert "ai" not in GeminiError(cat).user_message.lower().split()  # no standalone "AI"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/pytest tests/test_gemini_client.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.gemini_client'`

- [ ] **Step 3: Write the implementation**

Create `backend/services/gemini_client.py`:

```python
"""Resilient single entry point for Gemini generate_content calls.

Centralizes model construction, transient-error retry with backoff, and error
classification into user-friendly messages. Every analysis code path calls
generate_with_retry() instead of talking to google.generativeai directly, so
retries, the model id, and error copy live in exactly one place.
"""
import time
import google.generativeai as genai

from utils.gemini_config import get_gemini_model_name

# User-facing copy per category. No standalone "AI" (product copy rule).
_MESSAGES = {
    "timeout": "The analysis service timed out — this is usually temporary. Click Re-analyze to try again.",
    "rate_limit": "The analysis service is busy right now. Wait a moment and Re-analyze.",
    "server": "The analysis service had a temporary error. Click Re-analyze to try again.",
    "model_unavailable": "The analysis engine was updated. Click Re-analyze to continue.",
    "bad_response": "Analysis returned an unreadable result for this scene. Click Re-analyze.",
    "unknown": "Analysis couldn't complete for this scene. Click Re-analyze to try again.",
}

# Total attempt budget per category (includes the first attempt).
_ATTEMPTS = {
    "timeout": 3,
    "rate_limit": 3,
    "server": 3,
    "model_unavailable": 2,
    "bad_response": 1,
    "unknown": 1,
}

# Base backoff seconds per category (grows as base * 2**(attempt-1)).
_BACKOFF_BASE = {"timeout": 1, "server": 1, "model_unavailable": 1, "rate_limit": 6}

_RETRYABLE = {"timeout", "rate_limit", "server", "model_unavailable"}


class GeminiError(Exception):
    """Terminal Gemini failure (retries exhausted or non-retryable).

    Carries a machine-readable category and a user-facing message.
    """

    def __init__(self, category, user_message=None, raw=None):
        self.category = category
        self.user_message = user_message or _MESSAGES.get(category, _MESSAGES["unknown"])
        self.raw = raw
        super().__init__(self.user_message)


def classify_exception(exc):
    """Map a raised exception to a category string."""
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "deadlineexceeded" in name or "504" in msg or "timed out" in msg or "timeout" in msg:
        return "timeout"
    if "resourceexhausted" in name or "429" in msg or "quota" in msg or "rate" in msg:
        return "rate_limit"
    if "notfound" in name or "no longer available" in msg or "404" in msg:
        return "model_unavailable"
    if "serviceunavailable" in name or "internalservererror" in name \
            or any(code in msg for code in ("500", "502", "503")):
        return "server"
    return "unknown"


def generate_with_retry(prompt, *, generation_config=None, max_attempts=3, _sleep=time.sleep):
    """Call Gemini with retry/backoff on transient errors.

    Builds the model from get_gemini_model_name() each attempt (so an env/model
    change is honored). Returns response.text on success. Raises GeminiError on
    terminal failure. `_sleep` is injectable for tests.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            model = genai.GenerativeModel(get_gemini_model_name())
            response = model.generate_content(prompt, generation_config=generation_config)
            text = getattr(response, "text", None)
            if not text or not text.strip():
                raise GeminiError("bad_response")
            return text
        except GeminiError:
            raise  # already classified (e.g. empty response) — never retried here
        except Exception as exc:  # noqa: BLE001 — classify everything from the SDK
            category = classify_exception(exc)
            budget = min(max_attempts, _ATTEMPTS.get(category, 1))
            if category in _RETRYABLE and attempt < budget:
                _sleep(_BACKOFF_BASE[category] * (2 ** (attempt - 1)))
                continue
            raise GeminiError(category, raw=exc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./venv/bin/pytest tests/test_gemini_client.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/services/gemini_client.py backend/tests/test_gemini_client.py
git commit -m "feat(analysis): shared resilient Gemini client with retry + error taxonomy"
```

---

### Task 2: Switch default model to gemini-flash-latest

**Files:**
- Modify: `backend/utils/gemini_config.py:9`
- Test: `backend/tests/test_gemini_model.py` (existing — verify still green)

**Interfaces:**
- Consumes: nothing new.
- Produces: `DEFAULT_GEMINI_MODEL == "gemini-flash-latest"` (unchanged function signatures).

- [ ] **Step 1: Update the default**

In `backend/utils/gemini_config.py`, change line 9:

```python
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
```

- [ ] **Step 2: Run the existing model tests**

Run: `cd backend && ./venv/bin/pytest tests/test_gemini_model.py -q`
Expected: PASS — `test_gemini_model_name_default` asserts the default is not a retired id; `gemini-flash-latest` passes.

- [ ] **Step 3: Commit**

```bash
git add backend/utils/gemini_config.py
git commit -m "fix(analysis): default to gemini-flash-latest (self-healing vs deprecation)"
```

---

### Task 3: Stop swallowing exceptions in the scene analyzer

**Files:**
- Modify: `backend/routes/supabase_routes.py` — function `analyze_scene_with_gemini` (def at line 2891; the `try/except` around `model.generate_content` at ~3007–3078)
- Test: `backend/tests/test_analyze_scene_errors.py` (new)

**Interfaces:**
- Consumes: `services.gemini_client.generate_with_retry`, `GeminiError`.
- Produces: `analyze_scene_with_gemini(...)` now **raises** `GeminiError` on Gemini failure and on JSON parse failure (`category="bad_response"`), instead of returning a fallback dict. On success it returns the same result dict as before.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_analyze_scene_errors.py`:

```python
"""analyze_scene_with_gemini must raise GeminiError instead of swallowing."""
import pytest
import routes.supabase_routes as sr
from services.gemini_client import GeminiError


def test_analyzer_raises_on_gemini_error(monkeypatch):
    def boom(*_a, **_k):
        raise GeminiError("timeout")
    monkeypatch.setattr(sr, "generate_with_retry", boom)
    with pytest.raises(GeminiError) as ei:
        sr.analyze_scene_with_gemini("INT. ROOM - DAY\nAction.", "INT. ROOM - DAY")
    assert ei.value.category == "timeout"


def test_analyzer_raises_bad_response_on_unparseable_json(monkeypatch):
    monkeypatch.setattr(sr, "generate_with_retry", lambda *_a, **_k: "not json at all")
    with pytest.raises(GeminiError) as ei:
        sr.analyze_scene_with_gemini("INT. ROOM - DAY\nAction.", "INT. ROOM - DAY")
    assert ei.value.category == "bad_response"


def test_analyzer_success_returns_dict(monkeypatch):
    monkeypatch.setattr(
        sr, "generate_with_retry",
        lambda *_a, **_k: '{"characters":["BOB"],"props":[],"description":"x"}',
    )
    out = sr.analyze_scene_with_gemini("INT. ROOM - DAY\nBOB enters.", "INT. ROOM - DAY")
    assert out["characters"] == ["BOB"]
    assert out["description"] == "x"
```

Note: `analyze_scene_with_gemini` calls `genai.configure(...)`. The test does not set `GEMINI_API_KEY`; keep the existing `if not api_key: raise ValueError` guard BUT the monkeypatched `generate_with_retry` replaces the network call. Set the key in the test to pass the guard:

```python
@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
```

Add that fixture at the top of the test module.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/pytest tests/test_analyze_scene_errors.py -q`
Expected: FAIL — the success test may pass, but the two error tests FAIL because the current code returns a fallback dict instead of raising.

- [ ] **Step 3: Edit `analyze_scene_with_gemini`**

At the top of `backend/routes/supabase_routes.py` (with the other imports), add:

```python
from services.gemini_client import generate_with_retry, GeminiError
```

Replace the body of the `try/except` block (currently lines ~3007–3078) so it uses the client and re-raises on failure. The new block:

```python
    try:
        response_text = generate_with_retry(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.3),
        ).strip()

        # Clean up response
        import re
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)

        try:
            result = json.loads(response_text)
        except (ValueError, json.JSONDecodeError) as parse_err:
            raise GeminiError("bad_response", raw=parse_err)

        # Phase 2: Entity resolution — merge speakers with AI characters
        if has_speakers:
            ai_characters = result.get('characters', []) + result.get('non_speaking_characters', [])
            result['characters'] = merge_to_character_list(known_speakers, ai_characters)

        # Normalize story day fields
        result['time_transition'] = result.get('time_transition', '')
        result['is_new_story_day'] = bool(result.get('is_new_story_day', False))
        result['timeline_code'] = result.get('timeline_code', 'PRESENT')

        return result

    except GeminiError:
        raise  # caller records the failed scene state
```

Delete the old `except Exception as e:` fallback block entirely (the one that built the `fallback` dict with `description = f'Analysis failed: {str(e)}'`).

Also delete the now-unused local `model = genai.GenerativeModel(get_gemini_model_name())` line near the top of this function (line ~2911) — the client constructs the model. Keep the `genai.configure(api_key=api_key)` line and the `api_key` guard.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./venv/bin/pytest tests/test_analyze_scene_errors.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_analyze_scene_errors.py
git commit -m "fix(analysis): analyze_scene_with_gemini raises GeminiError instead of masking failures"
```

---

### Task 3B: Migrate the remaining Gemini call sites to the shared client

**Files:**
- Modify: `backend/services/scene_enhancer.py` (~line 108–110)
- Modify: `backend/services/analysis_service.py` (~line 151 and ~line 247)
- Modify: `backend/services/analysis_worker.py` — `call_gemini` (~line 78–91)
- Test: `backend/tests/test_gemini_single_entrypoint.py` (new)

**Interfaces:**
- Consumes: `services.gemini_client.generate_with_retry` (Task 1).
- Produces: no direct `model.generate_content(...)` calls remain anywhere under `routes/` or `services/` except inside `gemini_client.py`. All aggregate/legacy paths gain retry + typed errors for free.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_gemini_single_entrypoint.py`:

```python
"""Every Gemini generate_content call must go through gemini_client.

Enforces the single-entrypoint invariant: only services/gemini_client.py may
call .generate_content( directly; all other call sites use generate_with_retry
so retry + error classification is never bypassed.
"""
import os
import re
import glob

BACKEND = os.path.join(os.path.dirname(__file__), "..")
_CALL_RE = re.compile(r"\.generate_content\s*\(")
_ALLOWED = {os.path.normpath(os.path.join(BACKEND, "services", "gemini_client.py"))}


def _source_files():
    for sub in ("routes", "services"):
        yield from glob.glob(os.path.join(BACKEND, sub, "*.py"))


def test_only_client_calls_generate_content():
    offenders = []
    for path in _source_files():
        if os.path.normpath(path) in _ALLOWED:
            continue
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                if _CALL_RE.search(line):
                    offenders.append(f"{os.path.relpath(path, BACKEND)}:{lineno}")
    assert not offenders, (
        "generate_content called outside gemini_client — route through "
        "generate_with_retry instead:\n" + "\n".join(offenders)
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/pytest tests/test_gemini_single_entrypoint.py -q`
Expected: FAIL — offenders list includes `services/scene_enhancer.py`, `services/analysis_service.py` (×2), `services/analysis_worker.py` (plus any other stragglers the scan finds; migrate all of them in Step 3).

- [ ] **Step 3: Migrate each call site**

Add near the top imports of each of the three files:

```python
from services.gemini_client import generate_with_retry
```

**`scene_enhancer.py`** — replace the block at ~line 108:

```python
        rate_limit_wait()

        model = get_gemini_model()
        response = model.generate_content(prompt)

        # Parse response
        response_text = response.text.strip()
```

with:

```python
        rate_limit_wait()

        response_text = generate_with_retry(prompt).strip()
```

**`analysis_service.py`** — both occurrences (~line 151 and ~line 247) look like:

```python
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.7)
        )

        response_text = response.text.strip()
```

Replace each with:

```python
        response_text = generate_with_retry(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.7),
        ).strip()
```

(If `model` becomes unused in the enclosing function after this, delete its assignment too.)

**`analysis_worker.py`** — `call_gemini` at ~line 78:

```python
    rate_limit_wait()

    model = get_gemini_model()
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=temperature)
    )

    response_text = response.text.strip()
```

with:

```python
    rate_limit_wait()

    response_text = generate_with_retry(
        prompt,
        generation_config=genai.GenerationConfig(temperature=temperature),
    ).strip()
```

Leave each file's `get_gemini_model()` helper and `genai.configure(...)` in place (harmless; still used to configure the key). Leave the existing `rate_limit_wait()`, regex cleanup, and `json.loads` exactly as-is.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./venv/bin/pytest tests/test_gemini_single_entrypoint.py -q`
Expected: PASS — no offenders.

- [ ] **Step 5: Import-sanity + regression**

Run: `cd backend && ./venv/bin/python -c "import services.scene_enhancer, services.analysis_service, services.analysis_worker; print('imports OK')" && ./venv/bin/pytest tests/ -q`
Expected: `imports OK` then all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/services/scene_enhancer.py backend/services/analysis_service.py backend/services/analysis_worker.py backend/tests/test_gemini_single_entrypoint.py
git commit -m "refactor(analysis): route all Gemini call sites through the resilient client"
```

---

### Task 4: Add failed-state columns + backfill migration

**Files:**
- Create: `backend/db/migrations/036_add_scenes_analysis_error.sql`
- Create: `backend/db/migrations/037_backfill_failed_scenes.sql`

**Interfaces:**
- Produces: `scenes.analysis_error text` (nullable), `scenes.analysis_error_category text` (nullable). Existing poisoned scenes flipped to `analysis_status='failed'`.

- [ ] **Step 1: Write migration 036 (columns)**

Create `backend/db/migrations/036_add_scenes_analysis_error.sql`:

```sql
-- Failed-scene detail: friendly message + machine category for the UI.
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS analysis_error text;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS analysis_error_category text;
```

- [ ] **Step 2: Write migration 037 (backfill)**

Create `backend/db/migrations/037_backfill_failed_scenes.sql`:

```sql
-- Flip historically-poisoned scenes (masked as complete with the raw error in
-- description) to the real failed state so they surface and become retryable.
UPDATE scenes
SET analysis_status = 'failed',
    analysis_error_category = 'unknown',
    analysis_error = 'Analysis couldn''t complete for this scene. Click Re-analyze to try again.',
    description = ''
WHERE analysis_status = 'complete'
  AND description LIKE 'Analysis failed:%';
```

- [ ] **Step 3: Apply both migrations to Supabase**

Apply through the project's standard migration path (Supabase SQL editor or `backend/db/run_migration.py`). Verify:

```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'scenes' AND column_name IN ('analysis_error', 'analysis_error_category');
```
Expected: both rows returned.

```sql
SELECT count(*) FROM scenes WHERE analysis_status = 'failed';
```
Expected: ≥ the number of previously-poisoned scenes (e.g. the 2 reported).

- [ ] **Step 4: Commit**

```bash
git add backend/db/migrations/036_add_scenes_analysis_error.sql backend/db/migrations/037_backfill_failed_scenes.sql
git commit -m "feat(db): add scenes.analysis_error columns + backfill poisoned scenes to failed"
```

---

### Task 5: Single-scene endpoint records failed state + clears on success

**Files:**
- Modify: `backend/routes/supabase_routes.py` — `analyze_scene` endpoint (def line 2709); the `analysis = analyze_scene_with_gemini(...)` call (~line 2802) and the `update_data` block (~2838–2856)
- Test: `backend/tests/test_analyze_scene_endpoint.py` (new)

**Interfaces:**
- Consumes: `GeminiError` (already imported in Task 3).
- Produces: on `GeminiError`, the endpoint writes `analysis_status='failed'`, `analysis_error`, `analysis_error_category`, skips story-day recalc, and returns HTTP 200 with `{scene_id, analysis_status:'failed', analysis_error, analysis_error_category}`. On success, `update_data` additionally sets `analysis_error=None`, `analysis_error_category=None`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_analyze_scene_endpoint.py`:

```python
"""Endpoint-level: failed analysis is recorded as failed, not fake-complete."""
import pytest
import routes.supabase_routes as sr
from services.gemini_client import GeminiError


class FakeTable:
    def __init__(self, store): self.store = store; self._id = None; self._upd = None
    def select(self, *_a, **_k): return self
    def eq(self, _c, v): self._id = v; return self
    def single(self): return self
    def order(self, *_a, **_k): return self
    def in_(self, *_a, **_k): return self
    def update(self, data): self._upd = data; return self
    def execute(self):
        if self._upd is not None:
            self.store.setdefault(self._id, {}).update(self._upd)
            u, self._upd = self._upd, None
            return type("R", (), {"data": [self.store[self._id]]})()
        return type("R", (), {"data": self.store.get(self._id)})()


@pytest.fixture
def client(monkeypatch):
    store = {"scene-1": {"id": "scene-1", "script_id": "scr-1", "scene_text": "INT. ROOM - DAY\nAction here.",
                          "scene_order": 1, "setting": "INT. ROOM - DAY"}}
    fake = FakeTable(store)
    monkeypatch.setattr(sr, "supabase", type("S", (), {"table": lambda self, _n: fake})())
    monkeypatch.setattr(sr, "get_user_id", lambda: None)  # skip subscription gate
    from app import app
    app.config["TESTING"] = True
    return app.test_client(), store


def test_failed_scene_recorded_as_failed(client, monkeypatch):
    c, store = client
    monkeypatch.setattr(sr, "analyze_scene_with_gemini", lambda *a, **k: (_ for _ in ()).throw(GeminiError("timeout")))
    resp = c.post("/api/scenes/scene-1/analyze")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["analysis_status"] == "failed"
    assert body["analysis_error_category"] == "timeout"
    assert store["scene-1"]["analysis_status"] == "failed"
    assert store["scene-1"]["analysis_error"]  # non-empty friendly message
```

Note: if wiring a full Flask `test_client` against the real `app` proves too heavy to mock (blueprint import side effects), fall back to calling the endpoint view function directly with a Flask `test_request_context()`. Keep the same assertions on `store["scene-1"]`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/pytest tests/test_analyze_scene_endpoint.py -q`
Expected: FAIL — endpoint currently has no `GeminiError` handling; scene is not marked `failed`.

- [ ] **Step 3: Wrap the analyzer call in the endpoint**

In `analyze_scene`, replace the `analysis = analyze_scene_with_gemini(...)` call (~line 2802) with a try/except:

```python
        try:
            analysis = analyze_scene_with_gemini(
                scene_text, scene.get('setting', ''),
                known_speakers=known_speakers if has_speakers else None,
                shot_type=scene_shot_type,
                location_hierarchy=scene_location_hierarchy,
                prev_scene_context=prev_scene_context,
            )
        except GeminiError as ge:
            supabase.table('scenes').update({
                'analysis_status': 'failed',
                'analysis_error': ge.user_message,
                'analysis_error_category': ge.category,
            }).eq('id', scene_id).execute()
            return jsonify({
                'message': 'Scene analysis failed',
                'scene_id': scene_id,
                'analysis_status': 'failed',
                'analysis_error': ge.user_message,
                'analysis_error_category': ge.category,
            }), 200
```

- [ ] **Step 4: Clear error fields on success**

In the success `update_data` block (~2838), add these two keys so a recovered scene shows no stale error:

```python
            'analysis_status': 'complete',
            'analysis_error': None,
            'analysis_error_category': None,
```

(Insert the two new lines adjacent to the existing `'analysis_status': 'complete',` line.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && ./venv/bin/pytest tests/test_analyze_scene_endpoint.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_analyze_scene_endpoint.py
git commit -m "feat(analysis): single-scene endpoint records failed state, clears on recovery"
```

---

### Task 6: Bulk worker marks failed scenes with friendly detail

**Files:**
- Modify: `backend/routes/supabase_routes.py` — `process_bulk_analysis_job` terminal-failure branch (~line 3195, the `supabase.table('scenes').update({'analysis_status': 'error'})` inside `if attempt == max_retries`)
- Test: extend `backend/tests/test_analyze_scene_errors.py` OR new `backend/tests/test_bulk_failed_state.py`

**Interfaces:**
- Consumes: `GeminiError` (imported in Task 3). `analyze_scene_internal` now propagates `GeminiError` because it shares `analyze_scene_with_gemini` (Task 3) and does not catch it.
- Produces: bulk terminal failures write `analysis_status='failed'` + `analysis_error` + `analysis_error_category` (category from `GeminiError` when available, else `'unknown'`).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_bulk_failed_state.py`:

```python
"""Bulk worker records terminal scene failures as failed + friendly detail."""
import routes.supabase_routes as sr
from services.gemini_client import GeminiError


class OneSceneTable:
    def __init__(self): self.updates = []
    def update(self, data): self._u = data; return self
    def eq(self, _c, _v): return self
    def execute(self):
        self.updates.append(self._u); return type("R", (), {"data": []})()
    def select(self, *_a, **_k): return self
    def in_(self, *_a, **_k): return self
    def order(self, *_a, **_k): return self
    def insert(self, *_a, **_k): return self


def test_bulk_terminal_failure_marks_failed(monkeypatch):
    tbl = OneSceneTable()
    monkeypatch.setattr(sr, "supabase", type("S", (), {"table": lambda self, _n: tbl})())
    # analyze_scene_internal raises a terminal GeminiError every attempt
    monkeypatch.setattr(sr, "analyze_scene_internal",
                        lambda _sid: (_ for _ in ()).throw(GeminiError("timeout")))
    monkeypatch.setattr(sr.time, "sleep", lambda _s: None)
    sr.process_bulk_analysis_job("job-1", "scr-1", ["scene-1"])
    # The scene must have been marked failed with a category
    failed_updates = [u for u in tbl.updates if u.get("analysis_status") == "failed"]
    assert failed_updates, "scene was not marked failed"
    assert failed_updates[0]["analysis_error_category"] == "timeout"
    assert failed_updates[0]["analysis_error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/pytest tests/test_bulk_failed_state.py -q`
Expected: FAIL — current code writes `analysis_status='error'` with no `analysis_error_category`.

- [ ] **Step 3: Edit the terminal-failure branch**

In `process_bulk_analysis_job`, replace the terminal failure write (inside `if attempt == max_retries:`) — currently:

```python
                    if attempt == max_retries:
                        failed += 1
                        try:
                            supabase.table('scenes').update({'analysis_status': 'error'}).eq('id', scene_id).execute()
                        except:
                            pass
```

with:

```python
                    if attempt == max_retries:
                        failed += 1
                        if isinstance(e, GeminiError):
                            err_msg, err_cat = e.user_message, e.category
                        else:
                            err_msg = "Analysis couldn't complete for this scene. Click Re-analyze to try again."
                            err_cat = "unknown"
                        try:
                            supabase.table('scenes').update({
                                'analysis_status': 'failed',
                                'analysis_error': err_msg,
                                'analysis_error_category': err_cat,
                            }).eq('id', scene_id).execute()
                        except Exception:
                            pass
```

Rationale: the shared client (Task 1) already owns transient retry/backoff. The bulk loop's own rate-limit retry stays as a coarse outer safety net for sustained rate-limiting; it does not double-retry non-rate-limit terminal errors (those fail on attempt 1). No further change to the loop.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./venv/bin/pytest tests/test_bulk_failed_state.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_bulk_failed_state.py
git commit -m "feat(analysis): bulk worker records failed scenes with friendly message + category"
```

---

### Task 7: Add the retry-failed endpoint

**Files:**
- Modify: `backend/routes/supabase_routes.py` — add a new route near `analyze_bulk_scenes` (~line 3057)
- Test: `backend/tests/test_retry_failed_endpoint.py` (new)

**Interfaces:**
- Consumes: existing `process_bulk_analysis_job(job_id, script_id, scene_ids)`, `uuid`, `threading`.
- Produces: `POST /api/scripts/<script_id>/scenes/retry-failed` → 202 `{job_id, retrying: <count>, status:'queued'}` when there are failed scenes; 200 `{retrying: 0}` when none.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_retry_failed_endpoint.py`:

```python
"""retry-failed enqueues only failed scenes."""
import pytest
import routes.supabase_routes as sr


class SelectTable:
    """Returns a fixed set of failed scenes; captures inserts; no-ops threads."""
    def __init__(self, failed): self.failed = failed
    def select(self, *_a, **_k): return self
    def eq(self, *_a, **_k): return self
    def in_(self, *_a, **_k): return self
    def order(self, *_a, **_k): return self
    def insert(self, *_a, **_k): return self
    def update(self, *_a, **_k): return self
    def execute(self):
        return type("R", (), {"data": self.failed})()


def test_retry_failed_enqueues_failed_only(monkeypatch):
    failed = [{"id": "s1", "scene_number": 1}, {"id": "s2", "scene_number": 2}]
    monkeypatch.setattr(sr, "supabase", type("S", (), {"table": lambda self, _n: SelectTable(failed)})())
    monkeypatch.setattr(sr, "get_user_id", lambda: None)
    started = {}
    monkeypatch.setattr(sr.threading, "Thread",
                        lambda **kw: type("T", (), {"start": lambda self: started.update(kw.get("args") and {"args": kw["args"]})})())
    from app import app
    app.config["TESTING"] = True
    resp = app.test_client().post("/api/scripts/scr-1/scenes/retry-failed")
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["retrying"] == 2


def test_retry_failed_zero(monkeypatch):
    monkeypatch.setattr(sr, "supabase", type("S", (), {"table": lambda self, _n: SelectTable([])})())
    monkeypatch.setattr(sr, "get_user_id", lambda: None)
    from app import app
    app.config["TESTING"] = True
    resp = app.test_client().post("/api/scripts/scr-1/scenes/retry-failed")
    assert resp.status_code == 200
    assert resp.get_json()["retrying"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/pytest tests/test_retry_failed_endpoint.py -q`
Expected: FAIL — 404 (route does not exist yet).

- [ ] **Step 3: Add the endpoint**

Insert after the `analyze_bulk_scenes` function (before `process_bulk_analysis_job`):

```python
@supabase_bp.route('/api/scripts/<script_id>/scenes/retry-failed', methods=['POST'])
@optional_auth
def retry_failed_scenes(script_id):
    """Re-run every scene currently marked 'failed' for a script.

    Reuses the bulk background worker. Does not touch 'pending' scenes.
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    user_id = get_user_id()
    if user_id:
        from services.subscription_service import get_subscription_status
        sub_status = get_subscription_status(user_id)
        if sub_status.get('status') != 'active':
            return jsonify({
                'error': 'Active subscription required for analysis',
                'upgrade_url': 'https://wise.com/pay/r/8j9W0j5SUuPivxk',
                'subscription_required': True
            }), 403

    try:
        result = supabase.table('scenes').select('id, scene_number').eq(
            'script_id', script_id).eq('analysis_status', 'failed').order('scene_number').execute()
        failed_scenes = result.data or []
        count = len(failed_scenes)

        if count == 0:
            return jsonify({'message': 'No failed scenes to retry', 'retrying': 0}), 200

        job_id = str(uuid.uuid4())
        scene_ids = [s['id'] for s in failed_scenes]
        supabase.table('analysis_jobs').insert({
            'id': job_id,
            'script_id': script_id,
            'job_type': 'retry_failed_scenes',
            'status': 'queued',
            'progress': 0,
            'result_summary': f'Queued {count} failed scenes for retry',
        }).execute()

        threading.Thread(
            target=process_bulk_analysis_job,
            args=(job_id, script_id, scene_ids),
            daemon=True,
        ).start()

        return jsonify({
            'message': 'Retry started',
            'job_id': job_id,
            'retrying': count,
            'status': 'queued',
        }), 202

    except Exception as e:
        print(f"Error starting failed-scene retry: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./venv/bin/pytest tests/test_retry_failed_endpoint.py -q`
Expected: PASS

- [ ] **Step 5: Run the whole backend suite (regression gate)**

Run: `cd backend && ./venv/bin/pytest tests/ -q`
Expected: PASS — all prior tests plus the new ones green.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_retry_failed_endpoint.py
git commit -m "feat(analysis): add /scenes/retry-failed endpoint (failed scenes only)"
```

---

### Task 8: Frontend apiService method

**Files:**
- Modify: `frontend/src/services/apiService.js` (near `analyzeBulkScenes`, ~line 470)

**Interfaces:**
- Produces: `retryFailedScenes(scriptId)` returning `response.data` (`{retrying, job_id, ...}`). `analyzeScene(sceneId)` already exists and is reused for per-scene re-analyze.

- [ ] **Step 1: Add the method**

After `analyzeBulkScenes` in `frontend/src/services/apiService.js`:

```javascript
/**
 * Retry every scene currently marked 'failed' for a script.
 * @param {string} scriptId - The script UUID
 * @returns {Promise<Object>} { retrying, job_id, status }
 */
export const retryFailedScenes = async (scriptId) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/scenes/retry-failed`);
        return response.data;
    } catch (error) {
        console.error('Error retrying failed scenes:', error);
        throw error;
    }
};
```

- [ ] **Step 2: Lint**

Run: `cd frontend && npm run lint`
Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(frontend): add retryFailedScenes api method"
```

---

### Task 9: Per-scene failed state + Re-analyze button

**Files:**
- Modify: `frontend/src/components/scenes/SceneViewer.jsx` (analysis-status rendering; the analyze handler at ~line 233 already calls `analyzeScene`)

**Interfaces:**
- Consumes: `analyzeScene(sceneId)` (already imported, line 14). Scene objects now may carry `analysis_status === 'failed'`, `analysis_error`, `analysis_error_category`.
- Produces: a failed scene renders a warning block with `analysis_error` text and a **Re-analyze** button; clicking re-runs the scene and refreshes.

- [ ] **Step 1: Handle the failed response in the analyze handler**

The existing handler at ~line 233 does `const result = await analyzeScene(sceneId);` then sets the scene to `analysis_status: 'complete'`. Make it respect a failed result. Replace the optimistic update so it uses the returned status:

```javascript
            const result = await analyzeScene(sceneId);
            const newStatus = result?.analysis_status === 'failed' ? 'failed' : 'complete';
            setScenes(prev => prev.map(s => s.id === sceneId ? {
                ...s,
                ...result,
                analysis_status: newStatus,
                analysis_error: result?.analysis_error || null,
                analysis_error_category: result?.analysis_error_category || null,
            } : s));
```

(Adapt to the exact `setScenes` shape already used around line 233–245 — keep the existing merge of `result` fields; only add the status/error handling.)

- [ ] **Step 2: Render the failed state**

Where the component branches on `analysis_status` (near `isAnalyzed = scene.analysis_status === 'complete'`, line ~188), add a failed branch in the render. Add this block wherever the scene body/breakdown is rendered, guarded by failed status:

```jsx
{scene.analysis_status === 'failed' && (
    <div className="scene-analysis-failed" role="alert">
        <span className="scene-analysis-failed__icon" aria-hidden="true">⚠️</span>
        <p className="scene-analysis-failed__msg">
            {scene.analysis_error || "Analysis couldn't complete for this scene. Click Re-analyze to try again."}
        </p>
        <button
            type="button"
            className="scene-analysis-failed__btn"
            onClick={() => handleAnalyzeScene(scene.id)}
            disabled={analyzingSceneIds?.includes(scene.id)}
        >
            {analyzingSceneIds?.includes(scene.id) ? 'Re-analyzing…' : 'Re-analyze'}
        </button>
    </div>
)}
```

Use the component's existing analyze handler name (shown as `handleAnalyzeScene` here — match the real handler that wraps `analyzeScene` around line 233) and its existing per-scene in-progress tracking (`analyzingSceneIds` or the equivalent already in the component). If no per-scene spinner state exists, add a local `useState` set of in-flight scene ids and toggle it in the handler.

- [ ] **Step 3: Add minimal styling**

Add to the component's stylesheet (co-located CSS the component already imports):

```css
.scene-analysis-failed {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    border: 1px solid var(--color-warning, #d97706);
    border-radius: 8px;
    background: rgba(217, 119, 6, 0.08);
}
.scene-analysis-failed__msg { margin: 0; flex: 1; font-size: 0.9rem; }
.scene-analysis-failed__btn {
    padding: 0.4rem 0.9rem;
    border-radius: 6px;
    border: 1px solid var(--color-warning, #d97706);
    background: transparent;
    cursor: pointer;
}
.scene-analysis-failed__btn:disabled { opacity: 0.6; cursor: default; }
```

- [ ] **Step 4: Verify in dev**

Run: `cd frontend && npm run dev`
Manually: open a script with a failed scene (from the Task 4 backfill) → the warning + Re-analyze button render; clicking re-runs and, on success, replaces the block with the normal breakdown.

- [ ] **Step 5: Lint + commit**

```bash
cd frontend && npm run lint
git add frontend/src/components/scenes/SceneViewer.jsx frontend/src/components/scenes/*.css
git commit -m "feat(frontend): per-scene failed state with Re-analyze button"
```

---

### Task 10: "Retry all failed (N)" bulk control

**Files:**
- Modify: `frontend/src/components/scenes/ScriptSummary.jsx`

**Interfaces:**
- Consumes: `retryFailedScenes(scriptId)` (Task 8). Scene list / stats already available in the component (it renders `stats.analyzed` at line ~288).
- Produces: when the script has ≥1 failed scene, a "Retry all failed (N)" button that calls the endpoint and lets existing `AnalysisContext` polling pick up progress.

- [ ] **Step 1: Import the method**

Add to the imports in `ScriptSummary.jsx`:

```javascript
import { retryFailedScenes } from '../../services/apiService';
```

- [ ] **Step 2: Compute the failed count and render the button**

Derive the count from the scenes the component already has (match the existing prop/state name for the scene list — e.g. `scenes`):

```jsx
{(() => {
    const failedCount = (scenes || []).filter(s => s.analysis_status === 'failed').length;
    if (failedCount === 0) return null;
    return (
        <button
            type="button"
            className="retry-all-failed-btn"
            onClick={async () => {
                try {
                    await retryFailedScenes(scriptId);
                    // AnalysisContext polling surfaces per-scene progress;
                    // trigger the component's existing refresh if present.
                    onScenesChanged?.();
                } catch (e) {
                    console.error('Retry all failed error:', e);
                }
            }}
        >
            Retry all failed ({failedCount})
        </button>
    );
})()}
```

Match `scriptId`, `scenes`, and the refresh callback to the props/state the component already uses (it already receives the script and scene data to compute `stats`). If a toast context is in scope, surface success/error through it instead of `console.error`.

- [ ] **Step 3: Style the button**

Add to the component's stylesheet:

```css
.retry-all-failed-btn {
    padding: 0.45rem 1rem;
    border-radius: 6px;
    border: 1px solid var(--color-warning, #d97706);
    background: rgba(217, 119, 6, 0.08);
    cursor: pointer;
    font-size: 0.88rem;
}
```

- [ ] **Step 4: Verify in dev**

Run: `cd frontend && npm run dev`
Manually: a script with failed scenes shows "Retry all failed (N)"; clicking starts a job and scenes move out of the failed state as they recover.

- [ ] **Step 5: Lint + commit**

```bash
cd frontend && npm run lint
git add frontend/src/components/scenes/ScriptSummary.jsx frontend/src/components/scenes/*.css
git commit -m "feat(frontend): Retry all failed bulk control on script summary"
```

---

## Rollout

- Ship backend (Tasks 1–7) and run migrations 036 + 037 together, then frontend (Tasks 8–10).
- Backend-first is preferred so the `analysis_error` columns exist when the UI reads them; the UI degrades gracefully (falls back to generic copy) if a field is absent.
- After deploy: confirm a real failed scene shows the friendly message + Re-analyze, and that a transient blip during a bulk run now recovers automatically (no scene left `failed` unless retries were genuinely exhausted).
