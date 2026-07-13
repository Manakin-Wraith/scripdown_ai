# Location Quality Linter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a shared location-quality linter that (1) surfaces messy locations in-app, (2) auto-cleans the safe issue classes via parser + backfill, and (3) is locked by a golden regression corpus.

**Architecture:** A pure deterministic linter (`backend/services/location_quality.py`) is the single source of truth. A `GET /locations/health` endpoint feeds ⚠ flags into the Manage Locations panel and a count onto the Board button. The parser gains a bigger time vocabulary + digit-noise stripping (auto-fixable classes only) plus a generalized backfill. A golden fixture + test locks behavior.

**Tech Stack:** Python 3.13 / Flask / pytest (backend), React 18 + Vite plain JSX (frontend), Supabase.

## Global Constraints

- **Linter is Python-only.** The frontend renders flags it is handed by the endpoint — do NOT reimplement classification in JS (avoids the drift we already hit with `_split_segments`/`splitSegments`).
- **Auto-fix only the auto-fixable classes** (`TIME_RESIDUE`, `DIGIT_NOISE`, `INT_EXT_RESIDUE`). `DESCRIPTION_BLEED`, `POSSIBLE_PARENT`, `NEAR_DUPLICATE` are surfaced only — never auto-changed.
- **These must stay CLEAN (no flags, unchanged base):** `MRS. JONES' HOUSE`, `C-MAX PRISON`, `GARAGE / BACKROOM`, `INTERSTATE 5`. Guard every change against them.
- **Endpoints:** `@require_auth`/`@optional_auth` consistent with siblings + `_user_can_access_script(script_id, user_id)` → 403.
- **Backend gate:** `cd backend && source venv/bin/activate && python -m pytest tests/ -q`. **Frontend gate:** `cd frontend && npm run build`. (repo lint is known-broken.)
- **Commit trailers** on every commit:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN`.
- **Production backfill (Task 3) is applied by the human controller**, not a subagent.

---

### Task 1: Location quality linter core

**Files:**
- Create: `backend/services/location_quality.py`
- Create: `backend/tests/test_location_quality.py`

**Interfaces:**
- Consumes (from `services/location_resolver`): `normalize_place`, `derive_base_place`, `derive_sub_place`, `TIME_WORDS`, `INT_EXT_TOKENS`, `suggest_merges`.
- Produces:
  - `classify_location(base: str, sub: str, setting: str, sibling_bases: list[str]) -> list[dict]`
  - `lint_script_locations(scenes: list[dict]) -> dict` → `{ "total": int, "by_key": { key: [issue,...] } }` where key is `base` or `f"{base}|{sub}"`.
  - Each issue: `{ "code", "severity", "message", "auto_fixable", "suggestion"? }`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_location_quality.py`:
```python
from services.location_quality import classify_location, lint_script_locations


def codes(issues):
    return {i["code"] for i in issues}


def test_time_residue_flagged_autofixable():
    issues = classify_location("OFFICE", "EARLY MORNING", "SHELTER. OFFICE. EARLY MORNING.", ["OFFICE"])
    assert "TIME_RESIDUE" in codes(issues)
    assert all(i["auto_fixable"] for i in issues if i["code"] == "TIME_RESIDUE")


def test_digit_noise_flagged():
    assert "DIGIT_NOISE" in codes(classify_location("KITCHEN", "2 7", "HOME. KITCHEN. 2 7", ["KITCHEN"]))
    assert "DIGIT_NOISE" in codes(classify_location("STREETS", "3 A", "CITY STREETS. 3 A", ["STREETS"]))


def test_int_ext_residue_flagged():
    assert "INT_EXT_RESIDUE" in codes(classify_location("/EXT", "", "/EXT. COCKPIT", ["/EXT"]))


def test_description_bleed_flagged_not_autofixable():
    issues = classify_location("CAMERA DOLLIES DOWN A CORRIDOR AS PRISON", "", "INT. CELLBLOCK", ["CELLBLOCK"])
    assert "DESCRIPTION_BLEED" in codes(issues)
    assert all(not i["auto_fixable"] for i in issues if i["code"] == "DESCRIPTION_BLEED")


def test_possible_parent_suggests_shorter_base():
    issues = classify_location("HOMELESS SHELTER WORKSHOP", "", "INT. HOMELESS SHELTER WORKSHOP",
                               ["HOMELESS SHELTER", "HOMELESS SHELTER WORKSHOP"])
    pp = [i for i in issues if i["code"] == "POSSIBLE_PARENT"]
    assert pp and pp[0]["suggestion"] == "HOMELESS SHELTER"


def test_near_duplicate_flagged():
    issues = classify_location("CHAPMANS PEAK", "", "EXT. CHAPMANS PEAK",
                               ["CHAPMANS PEAK", "CHAPMAN'S PEAK"])
    assert "NEAR_DUPLICATE" in codes(issues)


def test_clean_locations_have_no_flags():
    for b in ["MRS. JONES' HOUSE", "C-MAX PRISON", "GARAGE / BACKROOM", "INTERSTATE 5"]:
        assert classify_location(b, "", f"INT. {b} - DAY", [b]) == [], b


def test_lint_script_shape():
    scenes = [
        {"setting": "INT. OPULENT SANDTON HOME. BEDROOM. DAY.", "int_ext": "INT",
         "time_of_day": "DAY", "location_hierarchy": [], "location_canonical": "OPULENT SANDTON HOME",
         "is_omitted": False},
    ]
    report = lint_script_locations(scenes)
    assert "total" in report and "by_key" in report
    assert isinstance(report["total"], int)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_location_quality.py -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `location_quality.py`**

```python
"""Deterministic quality checks for a scene's derived location.

The single source of truth for "is this location clean?" — consumed by the
locations/health endpoint, the backfill's verification pass, and the golden
regression tests. Pure: no I/O, never raises on odd input.
"""
import re
from typing import List, Dict

from services.location_resolver import (
    normalize_place, derive_base_place, derive_sub_place,
    TIME_WORDS, INT_EXT_TOKENS, suggest_merges,
)

# A segment that is only numbers, "<n> <n>" (split scene-time like "2 7"), or a
# truncated "<n> A(.M.)" — noise, never a real place.
_DIGIT_NOISE = re.compile(r"^\d+(?:[ /]\d+| [A-Z])?$")
# Prose thresholds — a real place is short; longer/among these signals a caught
# stage direction. Flag-only, so false positives are acceptable.
_MAX_PLACE_WORDS = 6
_MAX_PLACE_CHARS = 45


def _issue(code, severity, message, auto_fixable, suggestion=None):
    d = {"code": code, "severity": severity, "message": message, "auto_fixable": auto_fixable}
    if suggestion:
        d["suggestion"] = suggestion
    return d


def _segments(base: str, sub: str) -> List[str]:
    parts = []
    for chunk in (base or "", sub or ""):
        parts.extend(p for p in chunk.split(" - ") if p.strip())
    return parts


def classify_location(base: str, sub: str, setting: str, sibling_bases: List[str]) -> List[Dict]:
    """Return the list of issues for one location (empty == clean)."""
    issues: List[Dict] = []
    base = (base or "").strip()
    sub = (sub or "").strip()

    for seg in _segments(base, sub):
        n = normalize_place(seg)
        if not n:
            continue
        if n in TIME_WORDS:
            issues.append(_issue("TIME_RESIDUE", "warn", f"'{seg}' looks like a time of day", True))
        if _DIGIT_NOISE.match(n):
            issues.append(_issue("DIGIT_NOISE", "warn", f"'{seg}' looks like stray numbers", True))
        if n in INT_EXT_TOKENS or seg.strip().startswith("/"):
            issues.append(_issue("INT_EXT_RESIDUE", "warn", f"'{seg}' has an INT/EXT remnant", True))
        if len(n.split()) > _MAX_PLACE_WORDS or len(n) > _MAX_PLACE_CHARS:
            issues.append(_issue("DESCRIPTION_BLEED", "warn",
                                 f"'{seg}' looks like description text, not a location", False))

    # POSSIBLE_PARENT: base is another sibling base plus trailing words.
    nb = normalize_place(base)
    for other in sibling_bases:
        no = normalize_place(other)
        if no and no != nb and nb.startswith(no + " "):
            issues.append(_issue("POSSIBLE_PARENT", "info",
                                 f"Could group under '{other}'", False, suggestion=other))
            break

    # NEAR_DUPLICATE: this base clusters with a differently-spelled sibling.
    for group in suggest_merges(sibling_bases):
        members = {normalize_place(m) for m in group.get("members", [])}
        if nb in members and len(members) > 1:
            canonical = group.get("canonical")
            if normalize_place(canonical) != nb:
                issues.append(_issue("NEAR_DUPLICATE", "info",
                                     f"Looks like a duplicate of '{canonical}'", False, suggestion=canonical))
            break

    # De-dupe by (code, suggestion) preserving order.
    seen, out = set(), []
    for i in issues:
        k = (i["code"], i.get("suggestion"))
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out


def lint_script_locations(scenes: List[Dict]) -> Dict:
    """Build the per-location issue report for a script's scenes."""
    entries = []  # (base, sub, setting)
    bases = []
    for s in scenes or []:
        if s.get("is_omitted"):
            continue
        base = s.get("location_canonical") or derive_base_place(
            s.get("setting"), s.get("int_ext"), s.get("time_of_day"), s.get("location_hierarchy"))
        sub = derive_sub_place(
            s.get("setting"), s.get("int_ext"), s.get("time_of_day"), s.get("location_hierarchy"))
        if base:
            entries.append((base, sub, s.get("setting") or ""))
            bases.append(base)

    sibling_bases = sorted(set(bases))
    by_key: Dict[str, List[Dict]] = {}
    for base, sub, setting in entries:
        key = f"{base}|{sub}" if sub else base
        if key in by_key:
            continue
        issues = classify_location(base, sub, setting, sibling_bases)
        if issues:
            by_key[key] = issues
    return {"total": len(by_key), "by_key": by_key}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_location_quality.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Run the full backend suite (no regressions)**

Run: `python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/services/location_quality.py backend/tests/test_location_quality.py
git commit -m "feat(locations): deterministic location quality linter"
```

---

### Task 2: Golden regression corpus

**Files:**
- Create: `backend/tests/fixtures/location_golden.json`
- Create: `backend/tests/test_location_golden.py`
- Create: `scripts/sample_location_settings.py`

**Interfaces:**
- Consumes: `derive_base_place`, `derive_sub_place` (resolver); `classify_location` (linter).
- Produces: a data-driven test asserting base/sub/flag-codes for real cases.

- [ ] **Step 1: Write the golden fixture**

`backend/tests/fixtures/location_golden.json` — real cases hit to date:
```json
[
  {"setting": "INT. OPULENT SANDTON HOME. BEDROOM. DAY.", "int_ext": "INT", "time_of_day": "DAY", "location_hierarchy": [], "expect": {"base": "OPULENT SANDTON HOME", "sub": "BEDROOM", "flags": []}},
  {"setting": "INT. HOMELESS SHELTER. GARDEN. DAY.", "int_ext": "INT", "time_of_day": "DAY", "location_hierarchy": [], "expect": {"base": "HOMELESS SHELTER", "sub": "GARDEN", "flags": []}},
  {"setting": "INT. TK'S HOUSE, KITCHEN", "int_ext": "INT", "time_of_day": "MORNING", "location_hierarchy": ["TK'S HOUSE, KITCHEN"], "expect": {"base": "TK'S HOUSE", "sub": "KITCHEN", "flags": []}},
  {"setting": "INT. MRS. JONES' HOUSE, KITCHEN", "int_ext": "INT", "time_of_day": "DAY", "location_hierarchy": [], "expect": {"base": "MRS. JONES' HOUSE", "sub": "KITCHEN", "flags": []}},
  {"setting": "EXT. C-MAX PRISON, DAVEYTON", "int_ext": "EXT", "time_of_day": "NIGHT", "location_hierarchy": ["C-MAX PRISON, DAVEYTON"], "expect": {"base": "C-MAX PRISON", "sub": "DAVEYTON", "flags": []}},
  {"setting": "INT. GARAGE / BACKROOM - DAY", "int_ext": "INT", "time_of_day": "DAY", "location_hierarchy": [], "expect": {"base": "GARAGE / BACKROOM", "sub": "", "flags": []}},
  {"setting": "INTERSTATE 5 - NIGHT", "int_ext": "EXT", "time_of_day": "NIGHT", "location_hierarchy": [], "expect": {"base": "INTERSTATE 5", "sub": "", "flags": []}},
  {"setting": "/EXT. COCKPIT", "int_ext": "EXT", "time_of_day": "DAY", "location_hierarchy": ["/EXT. COCKPIT"], "expect": {"base": "COCKPIT", "sub": "", "flags": []}},
  {"setting": "INT. COURTROOM. DAY.", "int_ext": "INT", "time_of_day": "DAY", "location_hierarchy": [], "expect": {"base": "COURTROOM", "sub": "", "flags": []}}
]
```
(Each new real bad pattern gets appended here — this is the permanent lock.)

- [ ] **Step 2: Write the test**

`backend/tests/test_location_golden.py`:
```python
import json
from pathlib import Path

from services.location_resolver import derive_base_place, derive_sub_place
from services.location_quality import classify_location

CASES = json.loads((Path(__file__).parent / "fixtures" / "location_golden.json").read_text())


def test_golden_corpus():
    failures = []
    for c in CASES:
        base = derive_base_place(c["setting"], c["int_ext"], c["time_of_day"], c["location_hierarchy"])
        sub = derive_sub_place(c["setting"], c["int_ext"], c["time_of_day"], c["location_hierarchy"])
        flags = {i["code"] for i in classify_location(base, sub, c["setting"], [base])}
        exp = c["expect"]
        if base != exp["base"] or sub != exp["sub"] or flags != set(exp["flags"]):
            failures.append(f"{c['setting']!r}: got ({base!r},{sub!r},{sorted(flags)}) "
                            f"expected ({exp['base']!r},{exp['sub']!r},{exp['flags']})")
    assert not failures, "\n".join(failures)
```

- [ ] **Step 3: Run it**

Run: `python -m pytest tests/test_location_golden.py -q`
Expected: PASS. If any case fails, the fixture's `expect` encodes the *desired* output — fix the parser/linter, not the expectation, unless the expectation itself is wrong (then correct it and note why).

- [ ] **Step 4: Write the corpus sampler (curation helper)**

`scripts/sample_location_settings.py` — prints proposed golden rows from real DB settings for a human to curate (never auto-added):
```python
#!/usr/bin/env python3
"""Sample distinct real scene settings and print proposed golden-corpus rows.
Human curates the output into backend/tests/fixtures/location_golden.json."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from db.supabase_client import get_supabase_admin
from services.location_resolver import derive_base_place, derive_sub_place
from services.location_quality import classify_location

def main(limit=60):
    client = get_supabase_admin()
    rows, start = [], 0
    while True:
        batch = client.table("scenes").select(
            "setting, int_ext, time_of_day, location_hierarchy").range(start, start + 999).execute().data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        start += 1000
    seen, out = set(), []
    for s in rows:
        key = (s.get("setting") or "").strip().upper()
        if not key or key in seen:
            continue
        seen.add(key)
        base = derive_base_place(s.get("setting"), s.get("int_ext"), s.get("time_of_day"), s.get("location_hierarchy"))
        sub = derive_sub_place(s.get("setting"), s.get("int_ext"), s.get("time_of_day"), s.get("location_hierarchy"))
        flags = sorted({i["code"] for i in classify_location(base, sub, s.get("setting") or "", [base])})
        if flags:  # only surface still-flagged ones for review
            out.append({"setting": s.get("setting"), "int_ext": s.get("int_ext"),
                        "time_of_day": s.get("time_of_day"), "location_hierarchy": s.get("location_hierarchy") or [],
                        "expect": {"base": base, "sub": sub, "flags": flags}})
        if len(out) >= limit:
            break
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Commit**

```bash
git add backend/tests/fixtures/location_golden.json backend/tests/test_location_golden.py scripts/sample_location_settings.py
git commit -m "test(locations): golden regression corpus + sampler"
```

---

### Task 3: Parser auto-clean (time vocabulary + digit noise) and backfill

**Files:**
- Modify: `backend/services/location_resolver.py` (TIME_WORDS, digit-noise drop in `_split_segments`)
- Modify: `backend/tests/test_location_resolver.py` (new cases)
- Create: `scripts/backfill_location_quality.py` (generalized re-derive + linter verify)

**Interfaces:**
- Consumes: existing resolver internals; `lint_script_locations` for the verify pass.
- Produces: cleaner `derive_base_place`/`derive_sub_place`; a backfill that re-derives `location_canonical` and reports the linter delta.

- [ ] **Step 1: Write failing resolver tests**

Add to `backend/tests/test_location_resolver.py`:
```python
def test_compound_time_words_dropped():
    assert derive_sub_place("INT. SHELTER. OFFICE. EARLY MORNING.") == "OFFICE"
    assert derive_sub_place("INT. HOME. LOUNGE. PRESENT DAY.") == "LOUNGE"


def test_digit_noise_dropped_from_sub():
    assert derive_sub_place("INT. HOME. KITCHEN. 2 7") == "KITCHEN"
    assert derive_sub_place("EXT. CITY STREETS. 3 A") == ""
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_location_resolver.py -k "compound_time or digit_noise" -q`
Expected: FAIL.

- [ ] **Step 3: Expand `TIME_WORDS`**

In `backend/services/location_resolver.py`, replace the `TIME_WORDS` set with:
```python
TIME_WORDS = {
    "DAY", "NIGHT", "DUSK", "DAWN", "MORNING", "EVENING",
    "AFTERNOON", "CONTINUOUS", "LATER", "SAME", "MAGIC HOUR",
    "EARLY", "LATE", "EARLY MORNING", "LATE MORNING", "LATE NIGHT",
    "MOMENTS LATER", "PRESENT DAY", "PRESENT", "NIGHT/EARLY MORNING",
}
```

- [ ] **Step 4: Drop digit-noise segments in `_split_segments`**

Add the module-level pattern near the other regexes (after `_ABBREV`):
```python
# A segment that is only numbers, "<n> <n>" (split scene-time "2 7"), or a
# truncated "<n> A(.M.)" — noise, never a real place.
_DIGIT_NOISE = re.compile(r"^\d+(?:[ /]\d+| [A-Z])?$")
```
Then in `_split_segments`, drop digit-noise segments right before the final `out.extend(...)`. Change:
```python
        out.extend(p.strip() for p in segs if p.strip())
```
to:
```python
        segs = [p for p in segs if not _DIGIT_NOISE.match(normalize_place(p))]
        out.extend(p.strip() for p in segs if p.strip())
```
(Filtering here — not in the derivation kept-lists — keeps base and sub derivation consistent, since both call `_split_segments`.)

- [ ] **Step 5: Run resolver + full suite**

Run: `python -m pytest tests/test_location_resolver.py tests/test_location_golden.py tests/test_location_quality.py -q`
Then: `python -m pytest tests/ -q`
Expected: all pass. If a golden case now changes, update its `expect` to the new (correct) value and note it.

- [ ] **Step 6: Write the generalized backfill (dry-run first)**

`scripts/backfill_location_quality.py` — re-derive `location_canonical` for scenes whose linter flags include an auto-fixable code, then re-lint to report the delta:
```python
#!/usr/bin/env python3
"""Re-derive location_canonical wherever the linter finds an AUTO-FIXABLE issue
(time/digit/INT-EXT residue), then re-lint to confirm the auto-fixable count drops.
Judgment-call locations are never touched.

Usage: python scripts/backfill_location_quality.py [--dry-run]"""
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from db.supabase_client import get_supabase_admin
from services.location_resolver import derive_base_place
from services.location_quality import classify_location

AUTO = {"TIME_RESIDUE", "DIGIT_NOISE", "INT_EXT_RESIDUE"}

def main(dry_run):
    client = get_supabase_admin()
    rows, start = [], 0
    while True:
        batch = client.table("scenes").select(
            "id, setting, int_ext, time_of_day, location_hierarchy, location_canonical"
        ).range(start, start + 999).execute().data or []
        rows.extend(batch); 
        if len(batch) < 1000: break
        start += 1000
    changes = []
    for s in rows:
        cur = (s.get("location_canonical") or "").strip()
        # flags on the current base itself (sibling context not needed for auto classes)
        flags = {i["code"] for i in classify_location(cur, "", s.get("setting") or "", [cur])}
        if not (flags & AUTO):
            continue
        new = derive_base_place(s.get("setting"), s.get("int_ext"), s.get("time_of_day"), s.get("location_hierarchy"))
        if new and len(new) >= 2 and new != cur:
            changes.append((s["id"], cur, new))
    print(f"Scanned {len(rows)} scenes; {len(changes)} auto-fixable canonicals to re-derive.")
    for _id, cur, new in changes:
        print(f"  {cur!r:45} -> {new!r}")
    if dry_run:
        print("[dry-run] no writes."); return
    for _id, _cur, new in changes:
        client.table("scenes").update({"location_canonical": new}).eq("id", _id).execute()
    print(f"Applied {len(changes)} updates.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    main(ap.parse_args().dry_run)
```

- [ ] **Step 7: Commit the code (backfill runs in Task 3b, by the controller)**

```bash
git add backend/services/location_resolver.py backend/tests/test_location_resolver.py scripts/backfill_location_quality.py
git commit -m "feat(locations): expand time vocabulary + strip digit noise; quality backfill script"
```

- [ ] **Step 8: (Controller-run) Apply the backfill to production**

The human controller runs (NOT a subagent):
```
cd backend && source venv/bin/activate
python ../scripts/backfill_location_quality.py --dry-run   # review
python ../scripts/backfill_location_quality.py             # apply
```
Then re-run the sampler or a spot linter pass to confirm auto-fixable flags dropped to ~0.

---

### Task 4: locations/health endpoint + Manage Locations flags

**Files:**
- Modify: `backend/routes/supabase_routes.py` (new `GET /locations/health`)
- Create: `backend/tests/test_location_health_route.py`
- Modify: `frontend/src/services/apiService.js` (`getLocationHealth`)
- Modify: `frontend/src/components/scenes/LocationManager.jsx` (⚠ flags + count + Add-under suggestion)
- Modify: `frontend/src/components/scenes/LocationManager.css` (flag styles)
- Modify: `frontend/src/components/board/BoardToolbar.jsx` + `ZoomableStripboard.jsx` (button count)

**Interfaces:**
- `GET /api/scripts/<id>/locations/health` → `{ script_id, total, by_key }`.
- `getLocationHealth(scriptId)` → that payload.
- `LocationManager` renders flags from `by_key`, keyed as `parent.name` and `${parent.name}|${sub.name}`.

- [ ] **Step 1: Write the route test**

`backend/tests/test_location_health_route.py` (mirror the auth/stub pattern in `test_location_manager_routes.py`):
```python
import routes.supabase_routes as sr
import middleware.auth as auth


def test_health_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr(auth, "DEV_MODE", False)
    monkeypatch.setattr(sr, "_user_can_access_script", lambda *a, **k: False)
    app = sr.supabase_bp
    client = _client(app)  # helper as used in sibling tests
    r = client.get("/api/scripts/s1/locations/health")
    assert r.status_code in (401, 403)
```
(Use the exact app/client fixture style already present in `test_location_manager_routes.py`; if that file uses a shared harness, import it. The reviewer will confirm the harness match.)

- [ ] **Step 2: Add the endpoint**

In `backend/routes/supabase_routes.py`, after `get_location_suggestions` (~line 5356), add — importing `lint_script_locations` at the top of the file alongside the other `services.location_*` imports:
```python
@supabase_bp.route('/api/scripts/<script_id>/locations/health', methods=['GET'])
@optional_auth
def get_location_health(script_id):
    """Quality flags for a script's locations (messy time/digit/prose/duplicates)."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        user_id = get_user_id()
        if not _user_can_access_script(script_id, user_id):
            return jsonify({'error': 'Not authorized for this script'}), 403
        scenes = supabase.table('scenes').select(
            'setting, int_ext, time_of_day, location_hierarchy, location_canonical, is_omitted'
        ).eq('script_id', script_id).execute().data or []
        report = lint_script_locations(scenes)
        return jsonify({'script_id': script_id, **report}), 200
    except Exception as e:
        print(f"Error building location health: {e}")
        return jsonify({'error': str(e)}), 500
```
Add the import (top of file, with sibling resolver imports):
```python
from services.location_quality import lint_script_locations
```

- [ ] **Step 3: Run backend gate**

Run: `python -m pytest tests/test_location_health_route.py tests/ -q`
Expected: pass.

- [ ] **Step 4: apiService**

In `frontend/src/services/apiService.js` add:
```javascript
export const getLocationHealth = async (scriptId) => {
    const { data } = await api.get(`/api/scripts/${scriptId}/locations/health`);
    return data; // { script_id, total, by_key }
};
```

- [ ] **Step 5: LocationManager — fetch + render flags**

In `LocationManager.jsx`:
- Import `getLocationHealth` and `AlertTriangle` (lucide-react).
- Add `const [health, setHealth] = useState({ total: 0, by_key: {} });`
- Fetch on mount and after `onChanged`:
```javascript
    const loadHealth = useCallback(async () => {
        try { setHealth(await getLocationHealth(scriptId)); }
        catch { setHealth({ total: 0, by_key: {} }); }
    }, [scriptId]);
    useEffect(() => { loadHealth(); }, [loadHealth, scenes]);
```
- Header count under the purpose line:
```jsx
{health.total > 0 && (
    <p className="locmgr-review"><AlertTriangle size={13} /> {health.total} location{health.total === 1 ? '' : 's'} need review</p>
)}
```
- Helper + markers:
```javascript
    const flagsFor = (key) => health.by_key?.[key] || [];
```
- On the parent name row, after the count, render a marker when `flagsFor(parent.name).length`:
```jsx
{flagsFor(parent.name).length > 0 && (
    <span className="locmgr-flag" title={flagsFor(parent.name).map((f) => f.message).join('\n')}>
        <AlertTriangle size={13} />
    </span>
)}
```
- Same on each sub row with key `` `${parent.name}|${sub.name}` ``.
- `POSSIBLE_PARENT` suggestion → inline Add: if a parent-row flag has `code === 'POSSIBLE_PARENT'` and a `suggestion`, render a small button `Add under {suggestion}` calling `run('Location grouped', () => nestLocation(scriptId, parent.name, flag.suggestion))`.

- [ ] **Step 6: CSS**

Append to `LocationManager.css`:
```css
.locmgr-review { margin: 0; padding: 0.3rem 1rem 0.5rem; font-size: 0.8em; color: var(--primary-400, #fbbf24); display: inline-flex; align-items: center; gap: 0.35rem; }
.locmgr-flag { color: var(--primary-400, #fbbf24); display: inline-flex; align-items: center; cursor: help; }
.locmgr-suggest { background: none; border: 1px solid var(--primary-500, #f59e0b); color: var(--primary-400, #fbbf24); border-radius: 6px; padding: 0.15rem 0.5rem; font-size: 0.75em; cursor: pointer; }
```

- [ ] **Step 7: Board button count**

- `ZoomableStripboard.jsx`: add `const [locHealth, setLocHealth] = useState(0);`, fetch on load via `getLocationHealth(scriptId).then(h => setLocHealth(h.total)).catch(() => {})`, and pass `locationIssueCount={locHealth}` to `<BoardToolbar>`.
- `BoardToolbar.jsx`: accept `locationIssueCount` and render it in the button:
```jsx
<MapPin size={14} /> Manage locations{locationIssueCount ? ` ⚠${locationIssueCount}` : ''}
```

- [ ] **Step 8: Frontend gate**

Run: `cd frontend && npm run build`
Expected: builds clean.

- [ ] **Step 9: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_location_health_route.py frontend/src/services/apiService.js frontend/src/components/scenes/LocationManager.jsx frontend/src/components/scenes/LocationManager.css frontend/src/components/board/BoardToolbar.jsx frontend/src/components/board/ZoomableStripboard.jsx
git commit -m "feat(locations): in-app location health flags in Manage Locations + board count"
```

---

### Task 5: Library badge (stretch)

**Files:**
- Modify: `backend/routes/supabase_routes.py` (`GET /api/scripts/locations/health-counts`)
- Modify: `frontend/src/services/apiService.js` (`getLocationHealthCounts`)
- Modify: `frontend/src/pages/ScriptLibrary.jsx` (or the library card component — confirm exact file during implementation) to show a ⚠ count per card.

**Interfaces:**
- `GET /api/scripts/locations/health-counts` → `{ counts: { script_id: total } }` for the caller's owned/member scripts.
- `getLocationHealthCounts()` → that payload.

- [ ] **Step 1: Batch endpoint**

Add a route that resolves the user's script ids (owner + `script_members`), loads their scenes, and returns `lint_script_locations(...)["total"]` per script. Guard for the unauthenticated case (return `{counts: {}}`). Keep it one query per script's scenes but only for the user's own scripts (bounded).

- [ ] **Step 2: apiService + library card**

`getLocationHealthCounts()` in apiService; in the library page, fetch once and render a small `⚠ N` badge on each card whose count > 0 (link/opens that script's board). Confirm the exact library component file before editing.

- [ ] **Step 3: Gates + commit**

Run backend `pytest tests/ -q` and frontend `npm run build`.
```bash
git commit -m "feat(locations): per-script location health badge in the library"
```

---

## Manual E2E (post-merge, user)

1. Open **Manage locations** on "The Nowhere Man" board — confirm a "N locations need review" line and ⚠ markers on the messy rows (e.g. the description-bleed `BUILDING`/`CELLBLOCK` subs), with reasons on hover.
2. Confirm a `POSSIBLE_PARENT` row (e.g. `HOMELESS SHELTER WORKSHOP`) offers **Add under HOMELESS SHELTER**, and clicking it nests correctly.
3. Confirm the board's **Manage locations** button shows the ⚠ count.
4. After the Task 3 backfill, confirm the time/digit/INT-EXT flags are gone and only judgment-call flags remain.
5. (If Task 5 shipped) confirm the library shows a ⚠ count on scripts with issues.
