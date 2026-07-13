# Location Quality Linter — Design

**Date:** 2026-07-13
**Status:** Approved (design), pending implementation plan
**Builds on:** the location parser (`backend/services/location_resolver.py`) and the
Manage Locations panel (`frontend/src/components/scenes/LocationManager.jsx`).
**Areas:** `backend/services/location_quality.py` (new), `location_resolver.py`,
`backend/routes/supabase_routes.py`, `backend/tests/` (+ golden fixture),
`scripts/` (backfill), `frontend/src/components/scenes/LocationManager.jsx`,
`frontend/src/services/apiService.js`, `frontend/src/components/board/*` (button count).

## Problem

Location parsing produces dirty base places / sub-locations on many scripts —
unstripped time-of-day (`OFFICE - EARLY MORNING`, phantom `DAY`), digit noise
(`KITCHEN - 2 7`, `3 A`), INT/EXT residue (`/EXT`), prose captured as a location
(`CAMERA DOLLIES DOWN A CORRIDOR AS PRISON`), space-joined variants that should
group (`HOMELESS SHELTER WORKSHOP` beside `HOMELESS SHELTER`), and near-duplicate
bases (`CHAPMANS PEAK` vs `CHAPMAN'S PEAK`). These have been fixed reactively,
one script at a time. There is no way to (a) *see* where problems exist across
all scripts, (b) prevent the parser from regressing, or (c) know a fix actually
held.

## Goal

One shared **location quality linter** used three ways:

1. **Detect (in-app):** surface flagged locations where the user manages them.
2. **Auto-clean (parser):** the safe issue classes are fixed by the parser and a
   re-derive backfill; judgment-call issues are only surfaced, never auto-changed.
3. **Regression-proof (golden tests):** a corpus of real sluglines → expected
   base/sub/flags, run in CI, so every parser change is measured against reality
   and each new bad pattern is locked in permanently.

## Non-Goals

- No auto-merging or auto-grouping of judgment-call issues (`DESCRIPTION_BLEED`,
  `POSSIBLE_PARENT`, `NEAR_DUPLICATE`) — these are surfaced for user action only.
- No AI/LLM classification — the linter is deterministic rules over the derived
  base/sub and the raw setting.
- No change to nest/unnest/rename/merge behavior.
- Cross-script library badge is a stretch (built last), not core.

## Architecture

### 1. The shared core — `location_quality.py`

Pure, deterministic, no I/O:

```python
def classify_location(base: str, sub: str, setting: str,
                      sibling_bases: list[str]) -> list[dict]:
    """Return issues for one location. Each: {code, severity, message,
    auto_fixable: bool, suggestion?: str}. Empty list == clean."""
```

Issue codes:

| Code | Detects | severity | auto_fixable |
|---|---|---|---|
| `TIME_RESIDUE` | a segment that normalizes to a known time token (incl. compounds) survives in base/sub | warn | true |
| `DIGIT_NOISE` | a segment that is only digits / `\d+ \d+` / `\d+ [A-Z]` (truncated `3 A.M.`) | warn | true |
| `INT_EXT_RESIDUE` | base/sub still contains an INT/EXT token or a stray leading slash | warn | true |
| `DESCRIPTION_BLEED` | a segment is prose: word-count over a threshold, or contains sentence markers (verbs/`AS`/`WHO`/`WHILE`), or length over N chars | warn | false |
| `POSSIBLE_PARENT` | a top-level base equals another base plus trailing words (`"HOMELESS SHELTER WORKSHOP".startswith("HOMELESS SHELTER ")`) | info | false (suggest) |
| `NEAR_DUPLICATE` | two bases cluster via `suggest_merges` (article/case/typo) | info | false (suggest) |

`TIME_RESIDUE`/`NEAR_DUPLICATE` reuse `location_resolver` constants and
`suggest_merges`. `sibling_bases` (all top-level bases in the script) powers
`POSSIBLE_PARENT` and `NEAR_DUPLICATE`.

A script-level helper builds the per-location report:

```python
def lint_script_locations(scenes: list[dict]) -> dict:
    """-> { total: int, by_key: { "<base>": [issues], "<base>|<sub>": [issues] } }"""
```

This helper is the single source consumed by the endpoint, the backfill's
verification pass, and the golden tests.

### 2. Auto-clean (parser + backfill)

Only the `auto_fixable` classes change the parser:

- **Expand the time vocabulary** in `location_resolver.TIME_WORDS` to the
  compounds observed: `EARLY`, `LATE`, `EARLY MORNING`, `LATE MORNING`,
  `LATE NIGHT`, `MOMENTS LATER`, `PRESENT DAY`, `MAGIC HOUR`, `NIGHT/EARLY MORNING`,
  `DAWN`/`DUSK` (present). The segment filter already normalizes before checking,
  so trailing-period variants are covered.
- **Strip digit-noise segments** in `_split_segments`/derivation: drop a segment
  that is only digits or matches `^\d+( \d+| [A-Z])$` (truncated times/scene
  numbers) when it is not the sole segment.
- Re-run a **generalized backfill** (extend the existing
  `scripts/backfill_dirty_location_canonicals.py` pattern) across all scripts to
  re-derive `location_canonical`, then run `lint_script_locations` to confirm the
  `auto_fixable` count drops to ~0. Judgment-call flags remain.

`DESCRIPTION_BLEED`, `POSSIBLE_PARENT`, `NEAR_DUPLICATE` do **not** change the
parser — they are surfaced only.

### 3. In-app signal

**Endpoint** — mirrors the existing `GET /api/scripts/<id>/locations/suggestions`
(auth + `_user_can_access_script` → 403):

```
GET /api/scripts/<script_id>/locations/health
-> { total, by_key: { "<key>": [{code, severity, message, auto_fixable, suggestion?}] } }
```

The linter stays in Python only; the frontend renders flags it is handed (no
duplicated parsing logic — the lesson from `_split_segments`/`splitSegments`).

**Manage Locations panel** (`LocationManager.jsx`):
- Fetch health alongside scenes; render a ⚠ marker on any parent/sub row whose
  key has issues, with the message(s) on hover/title.
- Header line: `N locations need review` (from `total`), hidden when 0.
- `POSSIBLE_PARENT` suggestions render an inline `Add under X` that calls the
  existing `nestLocation` — a flag becomes the fix.

**Board button + Summary:** the "Manage locations" button shows the count
(`Manage locations ⚠6`); the Script Summary header shows the same count. Both
reuse the health endpoint for that one script.

**Library badge (stretch, built last):** a per-script ⚠ count on library cards,
via a small batch endpoint `GET /api/scripts/locations/health-counts` returning
`{ script_id: count }` for the user's scripts. Same linter, aggregated.

### 4. Regression-proof (golden corpus)

- `backend/tests/fixtures/location_golden.json`: a curated list of real cases,
  each `{ setting, int_ext, time_of_day, location_hierarchy, expect: { base, sub,
  flags: [codes] } }`, seeded from every tricky case hit to date
  (`OPULENT SANDTON HOME. BEDROOM. DAY.`, `MRS. JONES' HOUSE, KITCHEN`,
  `C-MAX PRISON, DAVEYTON`, `INT. GARAGE / BACKROOM - DAY`, `INTERSTATE 5 - NIGHT`,
  `HOMELESS SHELTER. GARDEN. DAY.`, digit-noise samples, description-bleed samples).
- `backend/tests/test_location_golden.py`: iterates the corpus, asserting
  `derive_base_place`, `derive_sub_place`, and the linter flag codes match `expect`.
- `scripts/sample_location_settings.py`: samples distinct real settings from the DB
  and prints proposed golden rows for a human to curate into the fixture — never
  auto-trusted.

## Data Flow

```
scenes ──derive_base/sub (parser)──► base, sub
                                      │
        sibling bases ───────────────┤
                                      ▼
                         classify_location() ──► issues
                                      │
   ┌──────────────────────────────────┼───────────────────────────────┐
   ▼                                   ▼                               ▼
locations/health endpoint     backfill verification          golden tests
   ▼                                   ▼                               ▼
Manage Locations ⚠ + count     auto-fixable count ~0        parser can't regress
```

## Error Handling / Edge Cases

- Health endpoint failure is non-fatal: the panel renders without flags (degrade
  to today's behavior), matching how alias-lookup failures already degrade.
- Linter is pure and total: any input string yields a (possibly empty) list; never
  raises on odd data.
- Auto-fix backfill is idempotent and re-runs the linter afterward to prove the
  drop; it only writes `location_canonical` where the value changes (as the
  existing backfill does), and never touches judgment-call locations.
- A location can carry multiple flags; the panel shows all messages, the count
  counts distinct flagged keys (not distinct flags).

## Testing / Verification

- **Backend `pytest`:**
  - `location_quality`: unit tests per issue code (positive + negative), including
    the compound-time and digit-noise cases and the abbreviation/hyphen negatives
    (`MRS. JONES' HOUSE`, `C-MAX PRISON`, `GARAGE / BACKROOM` must be clean).
  - Golden corpus test (above).
  - `locations/health` route: auth/access → 403, shape of response.
- **Frontend gated on `npm run build`.**
- **Manual E2E:** open Manage Locations on a script with known issues (e.g. "The
  Nowhere Man"); confirm ⚠ markers + count appear, `POSSIBLE_PARENT` offers
  `Add under HOMELESS SHELTER`, and that after the auto-clean backfill the
  auto-fixable flags are gone while judgment-call flags remain.

## Build Sequence (for the plan)

1. `location_quality.py` linter + unit tests (the core).
2. Golden fixture + `test_location_golden.py` (lock current correct behavior).
3. Parser auto-clean (expanded time words, digit-noise strip) + generalized
   backfill; re-verify with the linter.
4. `locations/health` endpoint + Manage Locations panel flags/count + button count.
5. Library badge (stretch): batch counts endpoint + card badge.
