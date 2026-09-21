# Call Sheet Customization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let each production define one call sheet template (sections, custom day fields, custom cast/crew/scene columns, department calls, blocks, header) that every day's call sheet and PDF inherit and can override.

**Architecture:** A `call_sheet_templates` table holds one versioned JSONB config per production. Per-day values live in new JSONB columns on `call_sheets` and `extra` JSONB on the cast/crew join rows. Pure helper modules handle validation/merge (`call_sheet_values`) and config (`call_sheet_template_service`); a new pure renderer (`call_sheet_render`) turns the config plus data into PDF HTML. The frontend gets a "Call Sheet" template tab and a template-driven `CallSheetEditor`.

**Tech Stack:** Flask + supabase-py (service role), pytest with the in-memory `MockSupabase`, WeasyPrint, React 18 + Vite (plain JSX).

**Spec:** `docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md` (read it first; this plan implements it).

## Global Constraints

- Run backend tests from `backend/` with `venv/bin/python -m pytest tests/<file> -v`. Frontend gate is `npm run build` in `frontend/` (lint is broken repo-wide; not a gate).
- Migration `055_call_sheet_templates.sql` is applied **manually** to Supabase (no runner). Everything in it is additive with defaults.
- Config version is `"v": 1`. Section keys (exactly these 11, each once): `header, day_info, locations, scenes, cast, extras, crew, dept_calls, catering, notes, advanced`.
- Field/column types: `text, textarea, time, link, number` (internal-only `count` for catering). Keys match `^[a-z][a-z0-9_]{0,39}$` and are immutable.
- Built-in day fields (cannot be deleted, type locked): `weather, sunrise_time, sunset_time, breakfast_time, lunch_time, general_call, nearest_hospital, safety_notes, general_notes, parking_notes`.
- Caps: 40 day fields; 15 columns per table; 30 departments; 20 blocks; 20 key-crew entries. Text values ≤2,000 chars; textarea ≤10,000.
- Times are `HH:MM` in the API (Postgres `HH:MM:SS` is trimmed).
- JSONB value payloads merge **per key**; `null` clears a key; unknown keys are ignored and echoed in `ignored_keys`.
- Sensitive values (per-column/field `sensitive` flag) are stripped for viewers without `can_view_sensitive` in JSON **and** the PDF.
- All user-authored text is HTML-escaped before reaching WeasyPrint.
- Commit trailer on every commit: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.
- Mock harness: new test files import `MockSupabase` and `_store` from `tests/test_call_sheet_service.py` (tests dir has no `__init__.py`, so a bare `from test_call_sheet_service import ...` works).

## File Structure

| File | Responsibility |
|---|---|
| `backend/db/migrations/055_call_sheet_templates.sql` (new) | table, JSONB columns, capability columns, RLS |
| `backend/services/call_sheet_values.py` (new) | pure: type validation, per-key merge, catering defaults |
| `backend/services/call_sheet_template_service.py` (new) | default config, `validate_config`, `get_template`, `save_template` |
| `backend/services/call_sheet_render.py` (new) | pure config-driven HTML renderer (section registry) |
| `backend/services/call_sheet_service.py` (modify) | template in `get_call_sheet`, PATCH merge, roster `extra`, redaction, render wiring |
| `backend/routes/call_sheet_routes.py` (modify) | template GET/PUT, `ignored_keys`, redaction of cast/crew responses, PDF sensitivity |
| `backend/middleware/production_authz.py`, `services/production_member_service.py` (modify) | new capability + presets |
| `frontend/src/services/apiService.js` (modify) | template API functions |
| `frontend/src/components/productions/ProductionMembersTab.jsx` (modify) | capability label + presets |
| `frontend/src/components/productions/callSheetTemplate/*` (new) | template editor panels + utils |
| `frontend/src/components/productions/ProductionCallSheetTab.jsx` (new) + `pages/ProductionDetailPage.jsx` (modify) | the "Call Sheet" tab |
| `frontend/src/components/schedule/CallSheetPanels.jsx` (new), `CallSheetEditor.jsx` (modify) | template-driven per-day editor |

---

### Task 1: Migration 055 + `can_edit_call_sheet_template` capability

**Files:**
- Create: `backend/db/migrations/055_call_sheet_templates.sql`
- Modify: `backend/middleware/production_authz.py:21-24`
- Modify: `backend/services/production_member_service.py:19-21`
- Test: `backend/tests/test_call_sheet_template_permissions.py`

**Interfaces:**
- Produces: capability name `can_edit_call_sheet_template` in `CAPABILITIES`; coordinator/admin presets `True`, viewer `False`; DB objects used by all later tasks (`call_sheet_templates`, `call_sheets.custom_values|dept_overrides|scene_extras|catering|header_values|block_overrides` JSONB, `call_sheets.general_call` TIME, `call_sheet_cast.extra`, `call_sheet_crew.extra` JSONB).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_call_sheet_template_permissions.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from middleware.production_authz import CAPABILITIES
from services.production_member_service import ROLE_PRESETS, apply_role_preset


def test_capability_registered():
    assert "can_edit_call_sheet_template" in CAPABILITIES


def test_coordinator_preset_contains_key_with_true():
    # Explicit key check: the DB column default (false) would mask a missing key.
    assert ROLE_PRESETS["coordinator"]["can_edit_call_sheet_template"] is True


def test_admin_and_viewer_presets():
    assert ROLE_PRESETS["admin"]["can_edit_call_sheet_template"] is True
    assert ROLE_PRESETS["viewer"]["can_edit_call_sheet_template"] is False


def test_override_can_revoke_from_coordinator():
    flags = apply_role_preset("coordinator", {"can_edit_call_sheet_template": False})
    assert flags["can_edit_call_sheet_template"] is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_template_permissions.py -v`
Expected: FAIL (`assert 'can_edit_call_sheet_template' in CAPABILITIES`).

- [ ] **Step 3: Implement**

In `production_authz.py` replace the tuple:

```python
CAPABILITIES = (
    'can_view_sensitive', 'can_edit_crew', 'can_manage_members', 'can_edit_production',
    'can_edit_call_sheets', 'can_edit_call_sheet_template',
)
```

In `production_member_service.py` the coordinator literal becomes:

```python
    'coordinator': {'can_view_sensitive': False, 'can_edit_crew': True,
                    'can_manage_members': False, 'can_edit_production': False,
                    'can_edit_call_sheets': True,
                    'can_edit_call_sheet_template': True},
```

Create `backend/db/migrations/055_call_sheet_templates.sql`:

```sql
-- Migration 055: Call sheet templates (per-production customization)
-- See docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md
-- Apply manually against the Supabase project (run_migration.py is dead).
-- Everything is additive with defaults.

-- 0. New capability column (mirrors 054's can_edit_call_sheets)
ALTER TABLE production_members
    ADD COLUMN IF NOT EXISTS can_edit_call_sheet_template boolean NOT NULL DEFAULT false;
ALTER TABLE production_invites
    ADD COLUMN IF NOT EXISTS can_edit_call_sheet_template boolean NOT NULL DEFAULT false;

-- Existing admins/coordinators get it, matching the new role presets
-- (presets only apply to members created after this migration).
UPDATE production_members SET can_edit_call_sheet_template = true
    WHERE role IN ('admin', 'coordinator');
UPDATE production_invites SET can_edit_call_sheet_template = true
    WHERE role IN ('admin', 'coordinator') AND status = 'pending';

-- 1. call_sheet_templates -- one per production
CREATE TABLE IF NOT EXISTS call_sheet_templates (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id UUID NOT NULL UNIQUE REFERENCES productions(id) ON DELETE CASCADE,
    config        JSONB NOT NULL,
    updated_by    UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_call_sheet_templates_updated
    BEFORE UPDATE ON call_sheet_templates
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

ALTER TABLE call_sheet_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "owner manages call sheet templates"
    ON call_sheet_templates FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = call_sheet_templates.production_id
                  AND p.owner_id = auth.uid())
    );

-- 2. Per-day custom data on call_sheets
ALTER TABLE call_sheets
    ADD COLUMN IF NOT EXISTS general_call    TIME,
    ADD COLUMN IF NOT EXISTS custom_values   JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS dept_overrides  JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS scene_extras    JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS catering        JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS header_values   JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS block_overrides JSONB NOT NULL DEFAULT '{}'::jsonb;

-- 3. Custom column values on roster rows
ALTER TABLE call_sheet_cast
    ADD COLUMN IF NOT EXISTS extra JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE call_sheet_crew
    ADD COLUMN IF NOT EXISTS extra JSONB NOT NULL DEFAULT '{}'::jsonb;
```

- [ ] **Step 4: Verify tests pass and invite-accept copies the column**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_template_permissions.py tests/test_production_authz.py tests/test_production_member_routes.py -v`
Expected: PASS.
Then confirm accept copies capabilities generically: `grep -n "for c in CAPABILITIES" services/production_member_service.py` must show the insert at ~line 318 (`**{c: bool(inv.get(c)) for c in CAPABILITIES}`); no code change needed.

- [ ] **Step 5: Commit**

```bash
git add backend/db/migrations/055_call_sheet_templates.sql backend/middleware/production_authz.py backend/services/production_member_service.py backend/tests/test_call_sheet_template_permissions.py
git commit -m "$(cat <<'EOF'
feat(call-sheets): migration 055 + can_edit_call_sheet_template capability

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `call_sheet_values.py` — validation, merge, catering defaults

**Files:**
- Create: `backend/services/call_sheet_values.py`
- Test: `backend/tests/test_call_sheet_values.py`

**Interfaces:**
- Produces:
  - `normalize_time(value) -> str | None` (raises `ValueError`)
  - `validate_value(ftype, value) -> value | None` (types `text|textarea|time|link|number|count`; `None` means "clear"; raises `ValueError`)
  - `merge_values(existing: dict|None, incoming: dict, types: dict[str,str]) -> (merged: dict, ignored: list[str])`
  - `merge_nested(existing, incoming, allowed_outer, inner_types) -> (merged, ignored)`
  - `MEALS`, `CATERING_GROUPS`, `catering_defaults(crew_rows, cast_rows) -> {meal: {group: int}}`, `effective_catering(defaults, overrides) -> same shape`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_call_sheet_values.py
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_values as v


def test_normalize_time_trims_seconds():
    assert v.normalize_time("06:30:00") == "06:30"
    assert v.normalize_time("06:30") == "06:30"


def test_normalize_time_empty_is_none():
    assert v.normalize_time("") is None
    assert v.normalize_time(None) is None


@pytest.mark.parametrize("bad", ["6:30", "25:00", "06:60", "noon", 630])
def test_normalize_time_rejects(bad):
    with pytest.raises(ValueError):
        v.normalize_time(bad)


def test_validate_text_and_length():
    assert v.validate_value("text", "hi") == "hi"
    with pytest.raises(ValueError):
        v.validate_value("text", "x" * 2001)
    with pytest.raises(ValueError):
        v.validate_value("text", 5)
    assert len(v.validate_value("textarea", "x" * 10000)) == 10000


def test_validate_number():
    assert v.validate_value("number", 5) == 5
    assert v.validate_value("number", "7") == 7
    assert v.validate_value("number", "7.5") == 7.5
    assert v.validate_value("number", "") is None
    with pytest.raises(ValueError):
        v.validate_value("number", True)
    with pytest.raises(ValueError):
        v.validate_value("number", "abc")


def test_validate_link():
    assert v.validate_value("link", "https://maps.app.goo.gl/x") == "https://maps.app.goo.gl/x"
    with pytest.raises(ValueError):
        v.validate_value("link", "javascript:alert(1)")
    with pytest.raises(ValueError):
        v.validate_value("link", "ftp://x.com")


def test_validate_count():
    assert v.validate_value("count", 0) == 0
    with pytest.raises(ValueError):
        v.validate_value("count", -1)
    with pytest.raises(ValueError):
        v.validate_value("count", "3")


def test_none_always_means_clear():
    for t in ("text", "time", "number", "link", "count", "textarea"):
        assert v.validate_value(t, None) is None


def test_merge_values_touches_only_sent_keys():
    merged, ignored = v.merge_values({"a": "1", "b": "2"}, {"a": "9"}, {"a": "text", "b": "text"})
    assert merged == {"a": "9", "b": "2"} and ignored == []


def test_merge_values_null_clears_and_unknown_ignored():
    merged, ignored = v.merge_values({"a": "1", "b": "2"}, {"a": None, "zzz": "x"}, {"a": "text", "b": "text"})
    assert merged == {"b": "2"} and ignored == ["zzz"]


def test_merge_values_error_names_key():
    with pytest.raises(ValueError, match="link"):
        v.merge_values({}, {"link": "nope"}, {"link": "link"})


def test_merge_values_keeps_values_for_keys_not_in_types():
    # a field removed from the template keeps its stored value
    merged, _ = v.merge_values({"old": "keep"}, {"a": "1"}, {"a": "text"})
    assert merged == {"old": "keep", "a": "1"}


def test_merge_nested():
    merged, ignored = v.merge_nested(
        {"s1": {"a": "1"}}, {"s1": {"b": "2"}, "s2": {"a": "x"}, "zzz": {"a": "y"}},
        {"s1", "s2"}, {"a": "text", "b": "text"})
    assert merged == {"s1": {"a": "1", "b": "2"}, "s2": {"a": "x"}}
    assert ignored == ["zzz"]


def test_merge_nested_drops_empty_inner():
    merged, _ = v.merge_nested({"s1": {"a": "1"}}, {"s1": {"a": None}}, {"s1"}, {"a": "text"})
    assert merged == {}


def test_catering_defaults_split_background_from_cast():
    crew = [{}, {}, {}]
    cast = [{"casting": {"tier": "lead"}}, {"casting": {"tier": "background"}}]
    d = v.catering_defaults(crew, cast)
    assert d["lunch"] == {"crew": 3, "cast": 1, "add_crew": 0, "extras": 1}
    assert set(d) == set(v.MEALS)


def test_effective_catering_overrides_only_known():
    d = v.catering_defaults([{}], [])
    eff = v.effective_catering(d, {"lunch": {"crew": 9, "bogus": 1}, "brunch": {"crew": 1}})
    assert eff["lunch"]["crew"] == 9 and "bogus" not in eff["lunch"]
    assert eff["craft"]["crew"] == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_values.py -v`
Expected: FAIL (`ModuleNotFoundError: services.call_sheet_values`).

- [ ] **Step 3: Implement**

```python
# backend/services/call_sheet_values.py
"""Pure value validation / per-key merge helpers for call sheet customization.

No DB access. See docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md
("Validation rules").
"""
import re
from urllib.parse import urlparse

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?$")
MAX_TEXT = 2000
MAX_TEXTAREA = 10000
MAX_COUNT = 10000
MEALS = ("craft", "breakfast", "lunch", "dinner")
CATERING_GROUPS = ("crew", "cast", "add_crew", "extras")


def normalize_time(value):
    """'06:30:00' -> '06:30'; ''/None -> None; anything else -> ValueError."""
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not TIME_RE.match(value):
        raise ValueError("must be a time like 06:30")
    return value[:5]


def validate_value(ftype, value):
    """Validate one value for a field type. None means 'clear this key'."""
    if value is None:
        return None
    if ftype == "time":
        return normalize_time(value)
    if ftype in ("text", "textarea"):
        if not isinstance(value, str):
            raise ValueError("must be text")
        limit = MAX_TEXTAREA if ftype == "textarea" else MAX_TEXT
        if len(value) > limit:
            raise ValueError(f"must be at most {limit} characters")
        return value
    if ftype == "number":
        if isinstance(value, bool):
            raise ValueError("must be a number")
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            if value == "":
                return None
            try:
                return float(value) if "." in value else int(value)
            except ValueError:
                raise ValueError("must be a number")
        raise ValueError("must be a number")
    if ftype == "link":
        if value == "":
            return None
        if not isinstance(value, str) or len(value) > MAX_TEXT:
            raise ValueError("must be a link")
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("must be an http(s) link")
        return value
    if ftype == "count":
        if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > MAX_COUNT:
            raise ValueError(f"must be a whole number 0-{MAX_COUNT}")
        return value
    raise ValueError(f"unknown type {ftype}")


def merge_values(existing, incoming, types):
    """Per-key merge. Returns (merged, ignored_keys).

    Keys not in `types` are ignored (reported), never stored. `None` clears a
    key. Stored keys absent from `types` (e.g. a field later removed from the
    template) are left untouched so re-adding the field restores them.
    """
    if not isinstance(incoming, dict):
        raise ValueError("must be an object")
    merged = dict(existing or {})
    ignored = []
    for key, raw in incoming.items():
        if key not in types:
            ignored.append(key)
            continue
        try:
            value = validate_value(types[key], raw)
        except ValueError as e:
            raise ValueError(f"{key}: {e}")
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged, ignored


def merge_nested(existing, incoming, allowed_outer, inner_types):
    """Two-level per-key merge ({outer: {inner: value}}). Returns (merged, ignored)."""
    if not isinstance(incoming, dict):
        raise ValueError("must be an object")
    merged = {k: dict(val) for k, val in (existing or {}).items() if isinstance(val, dict)}
    ignored = []
    for outer, inner in incoming.items():
        if outer not in allowed_outer:
            ignored.append(outer)
            continue
        try:
            new_inner, ign = merge_values(merged.get(outer, {}), inner, inner_types)
        except ValueError as e:
            raise ValueError(f"{outer}.{e}")
        ignored.extend(f"{outer}.{k}" for k in ign)
        if new_inner:
            merged[outer] = new_inner
        else:
            merged.pop(outer, None)
    return merged, ignored


def catering_defaults(crew_rows, cast_rows):
    """Roster-derived headcounts, the same for every meal until overridden."""
    extras = sum(1 for r in cast_rows if (r.get("casting") or {}).get("tier") == "background")
    counts = {"crew": len(crew_rows), "cast": len(cast_rows) - extras,
              "add_crew": 0, "extras": extras}
    return {meal: dict(counts) for meal in MEALS}


def effective_catering(defaults, overrides):
    out = {meal: dict(groups) for meal, groups in defaults.items()}
    for meal, groups in (overrides or {}).items():
        if meal in out and isinstance(groups, dict):
            for group, n in groups.items():
                if group in out[meal]:
                    out[meal][group] = n
    return out
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_values.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend/services/call_sheet_values.py backend/tests/test_call_sheet_values.py
git commit -m "$(cat <<'EOF'
feat(call-sheets): add pure value validation/merge helpers

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `call_sheet_template_service.py` — default config, validation, storage

**Files:**
- Create: `backend/services/call_sheet_template_service.py`
- Test: `backend/tests/test_call_sheet_template_service.py`

**Interfaces:**
- Consumes: `call_sheet_values.validate_value`.
- Produces:
  - `SECTION_KEYS`, `BUILTIN_TYPES: dict[str,str]`, `BUILTIN_KEYS`
  - `default_config() -> dict` (mirrors v1 output; see spec)
  - `validate_config(config) -> dict` (clean copy) raising `ConfigError(errors: list[{"path","message"}])`
  - `class StaleTemplate(Exception)`
  - `get_template(production_id, supabase=None) -> {"config": dict, "updated_at": str|None, "is_default": bool}` (never creates a row)
  - `save_template(production_id, config, user_id, expected_updated_at=None, supabase=None) -> same shape`; raises `ConfigError` / `StaleTemplate`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_call_sheet_template_service.py
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_template_service as tpl
from test_call_sheet_service import MockSupabase


def _paths(exc):
    return [e["path"] for e in exc.value.errors]


def _custom_field(key="wind", **kw):
    f = {"key": key, "label": "Wind", "type": "text", "section": "day_info",
         "default": "", "sensitive": False, "visible": True, "builtin": False}
    f.update(kw)
    return f


def test_default_config_is_valid_and_round_trips():
    cfg = tpl.default_config()
    assert tpl.validate_config(cfg) == cfg


def test_default_mirrors_v1_visibility_and_order():
    cfg = tpl.default_config()
    assert [s["key"] for s in cfg["sections"]] == list(tpl.SECTION_KEYS)
    visible = {s["key"] for s in cfg["sections"] if s["visible"]}
    assert visible == {"header", "day_info", "locations", "scenes", "cast", "crew", "notes"}
    fields = {f["key"]: f for f in cfg["day_fields"]}
    assert fields["parking_notes"]["visible"] is False       # v1 never printed it
    assert fields["general_call"]["visible"] is False
    assert fields["weather"]["section"] == "day_info"
    assert fields["nearest_hospital"]["section"] == "notes"


def test_custom_field_accepted_and_builtin_flag_forced_by_server():
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field())
    cfg["day_fields"][0]["builtin"] = False  # client lies about a builtin
    clean = tpl.validate_config(cfg)
    by_key = {f["key"]: f for f in clean["day_fields"]}
    assert by_key["weather"]["builtin"] is True
    assert by_key["wind"]["builtin"] is False


def test_duplicate_key_rejected():
    cfg = tpl.default_config()
    cfg["day_fields"] += [_custom_field(), _custom_field()]
    with pytest.raises(tpl.ConfigError) as ei:
        tpl.validate_config(cfg)
    assert any("duplicate" in e["message"].lower() for e in ei.value.errors)


@pytest.mark.parametrize("bad", ["Wind", "1wind", "wind-speed", "", "a" * 41])
def test_bad_key_format_rejected(bad):
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field(key=bad))
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_builtin_removal_rejected():
    cfg = tpl.default_config()
    cfg["day_fields"] = [f for f in cfg["day_fields"] if f["key"] != "weather"]
    with pytest.raises(tpl.ConfigError) as ei:
        tpl.validate_config(cfg)
    assert "day_fields" in _paths(ei)


def test_builtin_type_is_locked():
    cfg = tpl.default_config()
    next(f for f in cfg["day_fields"] if f["key"] == "sunrise_time")["type"] = "text"
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_bad_type_and_section_rejected():
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field(type="color"))
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field(section="footer"))
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_invalid_default_for_time_field_rejected():
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field(key="wrap", type="time", default="soon"))
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_day_field_cap():
    cfg = tpl.default_config()
    cfg["day_fields"] += [_custom_field(key=f"f{i}") for i in range(31)]  # 10 + 31 = 41
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_missing_section_rejected():
    cfg = tpl.default_config()
    cfg["sections"] = [s for s in cfg["sections"] if s["key"] != "crew"]
    with pytest.raises(tpl.ConfigError) as ei:
        tpl.validate_config(cfg)
    assert "sections" in _paths(ei)


def test_columns_departments_blocks_key_crew_round_trip():
    cfg = tpl.default_config()
    cfg["cast_columns"] = [{"key": "pickup", "label": "P/U", "type": "time", "sensitive": False}]
    cfg["crew_columns"] = [{"key": "rate_note", "label": "Rate", "type": "text", "sensitive": True}]
    cfg["scene_columns"] = [{"key": "story_day", "label": "Story day", "type": "text", "sensitive": False}]
    cfg["departments"] = [{"key": "wardrobe", "label": "Wardrobe", "default_call": "06:00", "as_per": "Pippa"}]
    cfg["blocks"] = [{"key": "safety", "label": "Special notes", "body": "Closed shoes"}]
    cfg["key_crew"] = [{"key": "director", "label": "Director", "value": "A. Director"}]
    assert tpl.validate_config(cfg) == cfg


def test_department_call_must_be_time():
    cfg = tpl.default_config()
    cfg["departments"] = [{"key": "art", "label": "Art", "default_call": "early", "as_per": ""}]
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_unknown_props_are_stripped():
    cfg = tpl.default_config()
    cfg["day_fields"][0]["evil"] = "x"
    cfg["surprise"] = 1
    clean = tpl.validate_config(cfg)
    assert "evil" not in clean["day_fields"][0] and "surprise" not in clean


def test_get_template_default_creates_nothing():
    store = {"call_sheet_templates": []}
    got = tpl.get_template("p1", MockSupabase(store))
    assert got["is_default"] is True and got["updated_at"] is None
    assert got["config"] == tpl.default_config()
    assert store["call_sheet_templates"] == []


def test_save_template_creates_then_updates():
    store = {"call_sheet_templates": []}
    sb = MockSupabase(store)
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field())
    saved = tpl.save_template("p1", cfg, "u1", supabase=sb)
    assert saved["is_default"] is False
    assert len(store["call_sheet_templates"]) == 1
    cfg2 = copy.deepcopy(cfg)
    cfg2["day_fields"].append(_custom_field(key="wrap", label="Wrap"))
    tpl.save_template("p1", cfg2, "u1", supabase=sb)
    assert len(store["call_sheet_templates"]) == 1
    keys = [f["key"] for f in store["call_sheet_templates"][0]["config"]["day_fields"]]
    assert "wrap" in keys


def test_save_template_stale_expected_updated_at():
    store = {"call_sheet_templates": [
        {"id": "t1", "production_id": "p1", "config": tpl.default_config(),
         "updated_at": "2026-09-21T10:00:00+00:00"}]}
    sb = MockSupabase(store)
    with pytest.raises(tpl.StaleTemplate):
        tpl.save_template("p1", tpl.default_config(), "u1",
                          expected_updated_at="2026-09-21T09:00:00+00:00", supabase=sb)
    tpl.save_template("p1", tpl.default_config(), "u1",
                      expected_updated_at="2026-09-21T10:00:00+00:00", supabase=sb)


def test_save_template_invalid_raises_and_stores_nothing():
    store = {"call_sheet_templates": []}
    with pytest.raises(tpl.ConfigError):
        tpl.save_template("p1", {"v": 1}, "u1", supabase=MockSupabase(store))
    assert store["call_sheet_templates"] == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_template_service.py -v`
Expected: FAIL (`ModuleNotFoundError: services.call_sheet_template_service`).

- [ ] **Step 3: Implement**

```python
# backend/services/call_sheet_template_service.py
"""Per-production call sheet template: defaults, validation, storage.

See docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md.
Gated at the route layer by production_authz; this module trusts its caller.
"""
import re

from db.supabase_client import get_supabase_admin
from services import call_sheet_values as values

CONFIG_VERSION = 1

SECTION_KEYS = ("header", "day_info", "locations", "scenes", "cast", "extras",
                "crew", "dept_calls", "catering", "notes", "advanced")
SECTION_LABELS = {
    "header": "Header", "day_info": "Day Info", "locations": "Locations",
    "scenes": "Scene Schedule", "cast": "Cast Call List", "extras": "Extras",
    "crew": "Crew Call List", "dept_calls": "Department Calls",
    "catering": "Catering", "notes": "Notes", "advanced": "Advanced Schedule",
}
# v1 rendered exactly these sections.
DEFAULT_VISIBLE = {"header", "day_info", "locations", "scenes", "cast", "crew", "notes"}

FIELD_TYPES = ("text", "textarea", "time", "link", "number")
FIELD_SECTIONS = ("header", "day_info", "notes")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
CAPS = {"day_fields": 40, "cast_columns": 15, "crew_columns": 15, "scene_columns": 15,
        "departments": 30, "blocks": 20, "key_crew": 20}
MAX_LABEL, MAX_SHORT, MAX_DEFAULT, MAX_BODY = 60, 200, 2000, 10000

# (key, label, type, section, visible) -- v1's weather/sun/meal times print in
# the day-info strip; hospital/safety/general notes print in the footer;
# parking_notes was never printed by v1, so it defaults hidden.
_BUILTIN_SPEC = (
    ("weather", "Weather", "text", "day_info", True),
    ("sunrise_time", "Sunrise", "time", "day_info", True),
    ("sunset_time", "Sunset", "time", "day_info", True),
    ("breakfast_time", "Breakfast", "time", "day_info", True),
    ("lunch_time", "Lunch", "time", "day_info", True),
    ("general_call", "General Call", "time", "header", False),
    ("nearest_hospital", "Nearest Hospital", "text", "notes", True),
    ("safety_notes", "Safety / COVID Officer", "textarea", "notes", True),
    ("general_notes", "General Notes", "textarea", "notes", True),
    ("parking_notes", "Parking Notes", "textarea", "notes", False),
)
BUILTIN_TYPES = {key: ftype for key, _l, ftype, _s, _v in _BUILTIN_SPEC}
BUILTIN_KEYS = tuple(BUILTIN_TYPES)


class ConfigError(Exception):
    def __init__(self, errors):
        super().__init__("Invalid template")
        self.errors = errors


class StaleTemplate(Exception):
    pass


def default_config():
    return {
        "v": CONFIG_VERSION,
        "sections": [{"key": k, "label": SECTION_LABELS[k], "visible": k in DEFAULT_VISIBLE}
                     for k in SECTION_KEYS],
        "day_fields": [
            {"key": k, "label": label, "type": t, "section": s, "default": "",
             "sensitive": False, "visible": vis, "builtin": True}
            for k, label, t, s, vis in _BUILTIN_SPEC],
        "cast_columns": [], "crew_columns": [], "scene_columns": [],
        "departments": [], "blocks": [], "key_crew": [],
    }


# ---------- validation ----------

def _err(errors, path, message):
    errors.append({"path": path, "message": message})


def _items(raw, name, errors):
    if raw is None:
        return []
    if not isinstance(raw, list):
        _err(errors, name, "must be a list")
        return []
    if len(raw) > CAPS[name]:
        _err(errors, name, f"at most {CAPS[name]} entries")
        return []
    return raw


def _key(item, path, seen, errors):
    key = item.get("key") if isinstance(item, dict) else None
    if not isinstance(key, str) or not KEY_RE.match(key):
        _err(errors, f"{path}.key",
             "key must be lowercase letters, digits and underscores, starting with a letter (max 40)")
        return None
    if key in seen:
        _err(errors, f"{path}.key", f"duplicate key '{key}'")
        return None
    seen.add(key)
    return key


def _text(item, field, path, errors, limit, required=True):
    val = item.get(field, "")
    if not isinstance(val, str):
        _err(errors, f"{path}.{field}", "must be text")
        return ""
    if required and not val.strip():
        _err(errors, f"{path}.{field}", "is required")
    if len(val) > limit:
        _err(errors, f"{path}.{field}", f"must be at most {limit} characters")
    return val


def _validate_sections(raw, errors):
    out, seen = [], set()
    if not isinstance(raw, list):
        _err(errors, "sections", "must be a list")
        return out
    for i, item in enumerate(raw):
        path = f"sections[{i}]"
        if not isinstance(item, dict) or item.get("key") not in SECTION_KEYS:
            _err(errors, path, "unknown section key")
            continue
        if item["key"] in seen:
            _err(errors, path, f"duplicate section '{item['key']}'")
            continue
        seen.add(item["key"])
        out.append({"key": item["key"],
                    "label": _text(item, "label", path, errors, MAX_LABEL),
                    "visible": bool(item.get("visible", True))})
    missing = [k for k in SECTION_KEYS if k not in seen]
    if missing:
        _err(errors, "sections", f"missing sections: {', '.join(missing)}")
    return out


def _validate_day_fields(raw, errors):
    out, seen = [], set()
    for i, item in enumerate(_items(raw, "day_fields", errors)):
        path = f"day_fields[{i}]"
        if not isinstance(item, dict):
            _err(errors, path, "must be an object")
            continue
        key = _key(item, path, seen, errors)
        if key is None:
            continue
        builtin = key in BUILTIN_TYPES
        ftype = item.get("type")
        if ftype not in FIELD_TYPES:
            _err(errors, f"{path}.type", f"type must be one of {', '.join(FIELD_TYPES)}")
            continue
        if builtin and ftype != BUILTIN_TYPES[key]:
            _err(errors, f"{path}.type", "type is locked for built-in fields")
            continue
        if item.get("section") not in FIELD_SECTIONS:
            _err(errors, f"{path}.section", f"section must be one of {', '.join(FIELD_SECTIONS)}")
            continue
        default = _text(item, "default", path, errors, MAX_DEFAULT, required=False)
        if default != "":
            try:
                values.validate_value(ftype, default)
            except ValueError as e:
                _err(errors, f"{path}.default", str(e))
        out.append({"key": key, "label": _text(item, "label", path, errors, MAX_LABEL),
                    "type": ftype, "section": item["section"], "default": default,
                    "sensitive": bool(item.get("sensitive", False)),
                    "visible": bool(item.get("visible", True)), "builtin": builtin})
    missing = [k for k in BUILTIN_KEYS if k not in seen]
    if missing:
        _err(errors, "day_fields", f"built-in fields cannot be removed: {', '.join(missing)}")
    return out


def _validate_columns(raw, name, errors):
    out, seen = [], set()
    for i, item in enumerate(_items(raw, name, errors)):
        path = f"{name}[{i}]"
        if not isinstance(item, dict):
            _err(errors, path, "must be an object")
            continue
        key = _key(item, path, seen, errors)
        if key is None:
            continue
        if item.get("type") not in FIELD_TYPES:
            _err(errors, f"{path}.type", f"type must be one of {', '.join(FIELD_TYPES)}")
            continue
        out.append({"key": key, "label": _text(item, "label", path, errors, MAX_LABEL),
                    "type": item["type"], "sensitive": bool(item.get("sensitive", False))})
    return out


def _validate_departments(raw, errors):
    out, seen = [], set()
    for i, item in enumerate(_items(raw, "departments", errors)):
        path = f"departments[{i}]"
        if not isinstance(item, dict):
            _err(errors, path, "must be an object")
            continue
        key = _key(item, path, seen, errors)
        if key is None:
            continue
        call = item.get("default_call", "")
        try:
            call = values.normalize_time(call) or ""
        except ValueError as e:
            _err(errors, f"{path}.default_call", str(e))
            call = ""
        out.append({"key": key, "label": _text(item, "label", path, errors, MAX_LABEL),
                    "default_call": call,
                    "as_per": _text(item, "as_per", path, errors, MAX_SHORT, required=False)})
    return out


def _validate_labelled(raw, name, value_field, limit, errors):
    out, seen = [], set()
    for i, item in enumerate(_items(raw, name, errors)):
        path = f"{name}[{i}]"
        if not isinstance(item, dict):
            _err(errors, path, "must be an object")
            continue
        key = _key(item, path, seen, errors)
        if key is None:
            continue
        out.append({"key": key, "label": _text(item, "label", path, errors, MAX_LABEL),
                    value_field: _text(item, value_field, path, errors, limit, required=False)})
    return out


def validate_config(config):
    """Return a clean copy (unknown props stripped, builtin flags server-set)
    or raise ConfigError with a list of {path, message}."""
    if not isinstance(config, dict):
        raise ConfigError([{"path": "config", "message": "must be an object"}])
    errors = []
    if config.get("v") != CONFIG_VERSION:
        _err(errors, "v", f"unsupported config version (expected {CONFIG_VERSION})")
    clean = {
        "v": CONFIG_VERSION,
        "sections": _validate_sections(config.get("sections"), errors),
        "day_fields": _validate_day_fields(config.get("day_fields"), errors),
        "cast_columns": _validate_columns(config.get("cast_columns"), "cast_columns", errors),
        "crew_columns": _validate_columns(config.get("crew_columns"), "crew_columns", errors),
        "scene_columns": _validate_columns(config.get("scene_columns"), "scene_columns", errors),
        "departments": _validate_departments(config.get("departments"), errors),
        "blocks": _validate_labelled(config.get("blocks"), "blocks", "body", MAX_BODY, errors),
        "key_crew": _validate_labelled(config.get("key_crew"), "key_crew", "value", MAX_SHORT, errors),
    }
    if errors:
        raise ConfigError(errors)
    return clean


# ---------- storage ----------

def _lookup(supabase, production_id):
    res = (supabase.table("call_sheet_templates").select("*")
           .eq("production_id", production_id).limit(1).execute())
    return res.data[0] if res.data else None


def get_template(production_id, supabase=None):
    """Stored config, or the default. Never creates a row."""
    supabase = supabase or get_supabase_admin()
    row = _lookup(supabase, production_id)
    if row:
        return {"config": row["config"], "updated_at": row.get("updated_at"), "is_default": False}
    return {"config": default_config(), "updated_at": None, "is_default": True}


def save_template(production_id, config, user_id, expected_updated_at=None, supabase=None):
    clean = validate_config(config)
    supabase = supabase or get_supabase_admin()
    existing = _lookup(supabase, production_id)
    if existing:
        # Strict: a client that loaded the default (None) while a row now
        # exists is stale too.
        if expected_updated_at != existing.get("updated_at"):
            raise StaleTemplate()
        res = (supabase.table("call_sheet_templates")
               .update({"config": clean, "updated_by": user_id})
               .eq("id", existing["id"]).execute())
        saved = res.data[0]
    else:
        saved = (supabase.table("call_sheet_templates")
                 .insert({"production_id": production_id, "config": clean,
                          "updated_by": user_id}).execute().data[0])
    return {"config": saved["config"], "updated_at": saved.get("updated_at"), "is_default": False}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_template_service.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend/services/call_sheet_template_service.py backend/tests/test_call_sheet_template_service.py
git commit -m "$(cat <<'EOF'
feat(call-sheets): template config defaults, validation and storage

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```


---

### Task 4: Template routes (GET / PUT)

**Files:**
- Modify: `backend/routes/call_sheet_routes.py` (imports + two new routes)
- Modify: `backend/tests/test_call_sheet_routes.py` (`_patch` helper)
- Modify: `backend/tests/test_route_enforcement.py:183`
- Test: `backend/tests/test_call_sheet_template_routes.py`

**Interfaces:**
- Consumes: `tpl.get_template`, `tpl.save_template`, `tpl.ConfigError`, `tpl.StaleTemplate` (Task 3); `from_production_id` (already the decorator default).
- Produces: `GET /api/productions/<production_id>/call-sheet-template` → `{"template": {config, updated_at, is_default, default_config}}` (viewer); `PUT` body `{config, expected_updated_at}` → `{"template": {...}}`, 400 `{"error","details":[{path,message}]}`, 409 `{"error","code":"stale_template"}`.

- [ ] **Step 1: Extend the shared test patch helper**

In `backend/tests/test_call_sheet_routes.py` add the import and one patch line so routes that touch the template service hit the mock:

```python
import services.call_sheet_template_service as tpl
```

and inside `_patch(monkeypatch, store)` after `monkeypatch.setattr(cs_svc, "get_supabase_admin", lambda: mock)`:

```python
    monkeypatch.setattr(tpl, "get_supabase_admin", lambda: mock)
```

- [ ] **Step 2: Write the failing tests**

```python
# backend/tests/test_call_sheet_template_routes.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_template_service as tpl
from test_call_sheet_routes import _client, _store, _member_store, _patch

URL = "/api/productions/p1/call-sheet-template"


def _put(cfg, expected=None):
    return _client().put(URL, json={"config": cfg, "expected_updated_at": expected})


def test_get_returns_default_for_owner_and_creates_nothing(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().get(URL)
    assert resp.status_code == 200
    body = resp.get_json()["template"]
    assert body["is_default"] is True and body["config"] == tpl.default_config()
    assert body["default_config"] == tpl.default_config()
    assert store.get("call_sheet_templates", []) == []


def test_get_allowed_for_viewer_member(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    assert _client().get(URL).status_code == 200


def test_get_non_member_is_403(monkeypatch):
    _patch(monkeypatch, _store(productions=[{"id": "p1", "owner_id": "other", "title": "X"}]))
    assert _client().get(URL).status_code == 403


def test_get_anon_is_401(monkeypatch):
    _patch(monkeypatch, _store())
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get(URL).status_code == 401


def test_put_owner_saves(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _put(tpl.default_config())
    assert resp.status_code == 200
    assert len(store["call_sheet_templates"]) == 1


def test_put_viewer_is_403(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    assert _put(tpl.default_config()).status_code == 403


def test_put_coordinator_needs_capability(monkeypatch):
    _patch(monkeypatch, _member_store("coordinator"))
    assert _put(tpl.default_config()).status_code == 403


def test_put_coordinator_with_capability_ok(monkeypatch):
    _patch(monkeypatch, _member_store("coordinator", can_edit_call_sheet_template=True))
    assert _put(tpl.default_config()).status_code == 200


def test_put_invalid_config_is_400_with_details(monkeypatch):
    _patch(monkeypatch, _store())
    resp = _put({"v": 1})
    assert resp.status_code == 400
    assert resp.get_json()["details"]


def test_put_stale_is_409(monkeypatch):
    store = _store()
    store["call_sheet_templates"] = [{"id": "t1", "production_id": "p1",
                                      "config": tpl.default_config(), "updated_at": "t1"}]
    _patch(monkeypatch, store)
    resp = _put(tpl.default_config(), expected="t0")
    assert resp.status_code == 409
    assert resp.get_json()["code"] == "stale_template"
    assert _put(tpl.default_config(), expected="t1").status_code == 200
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_template_routes.py -v`
Expected: FAIL (404 — routes do not exist yet).

- [ ] **Step 4: Implement**

In `call_sheet_routes.py` add `from services import call_sheet_template_service as tpl` next to the existing service import, then append:

```python
@call_sheet_bp.route("/api/productions/<production_id>/call-sheet-template", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer")
def get_call_sheet_template(production_id):
    template = dict(tpl.get_template(production_id))
    # Lets the editor's "Reset to default" work without duplicating the default client-side.
    template["default_config"] = tpl.default_config()
    return jsonify({"template": template})


@call_sheet_bp.route("/api/productions/<production_id>/call-sheet-template", methods=["PUT"])
@require_auth
@require_production_role(capability="can_edit_call_sheet_template")
def put_call_sheet_template(production_id):
    data = request.get_json(silent=True) or {}
    try:
        saved = tpl.save_template(production_id, data.get("config"), get_user_id(),
                                  data.get("expected_updated_at"))
    except tpl.ConfigError as e:
        return jsonify({"error": "Invalid template", "details": e.errors}), 400
    except tpl.StaleTemplate:
        return jsonify({"error": "The template was changed by someone else",
                        "code": "stale_template"}), 409
    return jsonify({"template": saved})
```

In `backend/tests/test_route_enforcement.py` line 183 add `"production_id"` to `SCOPED_ARGS` so the new routes are checked for an authz marker:

```python
    SCOPED_ARGS = {"day_id", "call_sheet_id", "crew_id", "casting_id", "location_id", "production_id"}
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_template_routes.py tests/test_call_sheet_routes.py tests/test_route_enforcement.py -v`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add backend/routes/call_sheet_routes.py backend/tests/test_call_sheet_routes.py backend/tests/test_route_enforcement.py backend/tests/test_call_sheet_template_routes.py
git commit -m "$(cat <<'EOF'
feat(call-sheets): call sheet template GET/PUT routes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `get_call_sheet` returns the template; PATCH accepts custom data with merge semantics

**Files:**
- Modify: `backend/services/call_sheet_service.py` (imports, `DAY_INFO_FIELDS`, `get_call_sheet`, `update_call_sheet`)
- Modify: `backend/routes/call_sheet_routes.py` (`update_call_sheet` route)
- Create: `backend/tests/call_sheet_customization_support.py` (shared fixtures, not a test module)
- Test: `backend/tests/test_call_sheet_customization_service.py`

**Interfaces:**
- Consumes: `tpl.get_template(production_id, supabase)`, `tpl.BUILTIN_TYPES`, `values.*` (Tasks 2–3).
- Produces:
  - `get_call_sheet(id)` now also returns `template` (config), `template_updated_at`, `catering_defaults`, `catering_effective`, and `HH:MM`-normalized `sunrise_time|sunset_time|breakfast_time|lunch_time|general_call` plus roster `call_time`.
  - `update_call_sheet_with_report(id, fields) -> (row | NOT_FOUND, ignored_keys: list)`; raises `ValueError` on invalid values. `update_call_sheet(id, fields)` still returns just the row.
  - `PATCH /api/call-sheets/<id>` → `{"call_sheet": row, "ignored_keys": [...]}`; 400 `{"error": msg}` on `ValueError`.
  - Test support: `full_config()`, `sheet_row(**kw)`, `make_store(cfg=None, **overrides)`, `patch_svc(monkeypatch, store)`.

- [ ] **Step 1: Create the shared test support module**

```python
# backend/tests/call_sheet_customization_support.py
"""Shared fixtures for call sheet customization tests (not a test module)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_service as svc
import services.call_sheet_template_service as tpl
from test_call_sheet_service import MockSupabase, _store


def full_config():
    cfg = tpl.default_config()
    cfg["day_fields"] += [
        {"key": "wind", "label": "Wind", "type": "text", "section": "day_info",
         "default": "", "sensitive": False, "visible": True, "builtin": False},
        {"key": "map", "label": "Map", "type": "link", "section": "notes",
         "default": "", "sensitive": False, "visible": True, "builtin": False},
    ]
    cfg["scene_columns"] = [{"key": "story_day", "label": "Story day", "type": "text", "sensitive": False}]
    cfg["cast_columns"] = [{"key": "pickup", "label": "P/U", "type": "time", "sensitive": False}]
    cfg["crew_columns"] = [{"key": "vehicle", "label": "Vehicle", "type": "text", "sensitive": False}]
    cfg["departments"] = [{"key": "wardrobe", "label": "Wardrobe", "default_call": "06:00", "as_per": "Pippa"}]
    cfg["blocks"] = [{"key": "safety", "label": "Special notes", "body": "Closed shoes"}]
    cfg["key_crew"] = [{"key": "director", "label": "Director", "value": "A. Director"}]
    return cfg


def sheet_row(**kw):
    row = {"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}
    row.update(kw)
    return row


def make_store(cfg=None, **overrides):
    base = _store(
        call_sheets=[sheet_row()],
        call_sheet_templates=[{"id": "t1", "production_id": "p1",
                               "config": cfg or full_config(),
                               "updated_at": "2026-09-21T00:00:00+00:00"}],
    )
    base.update(overrides)
    return base


def patch_svc(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(svc, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr(tpl, "get_supabase_admin", lambda: mock)
    return mock
```

- [ ] **Step 2: Write the failing tests**

```python
# backend/tests/test_call_sheet_customization_service.py
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_service as svc
import services.call_sheet_template_service as tpl
from call_sheet_customization_support import full_config, make_store, patch_svc, sheet_row
from test_call_sheet_service import _store


def test_get_call_sheet_includes_default_template_when_none_saved(monkeypatch):
    patch_svc(monkeypatch, _store(call_sheets=[sheet_row()]))
    data = svc.get_call_sheet("cs1")
    assert data["template"] == tpl.default_config()
    assert data["template_updated_at"] is None


def test_get_call_sheet_returns_saved_template_and_catering(monkeypatch):
    store = make_store(
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": None}],
        call_sheet_crew=[{"id": "x", "call_sheet_id": "cs1", "crew_id": "cr1", "call_time": "06:00:00"}],
    )
    patch_svc(monkeypatch, store)
    data = svc.get_call_sheet("cs1")
    assert data["template"] == full_config()
    assert data["template_updated_at"] == "2026-09-21T00:00:00+00:00"
    assert data["catering_defaults"]["lunch"]["crew"] == 1
    assert data["catering_effective"]["lunch"]["crew"] == 1
    assert data["crew"][0]["call_time"] == "06:00"


def test_get_call_sheet_normalizes_times(monkeypatch):
    store = make_store(call_sheets=[sheet_row(sunrise_time="06:12:00", general_call="05:30:00")])
    patch_svc(monkeypatch, store)
    data = svc.get_call_sheet("cs1")
    assert data["sunrise_time"] == "06:12" and data["general_call"] == "05:30"


def test_catering_override_wins_in_effective(monkeypatch):
    store = make_store(call_sheets=[sheet_row(catering={"lunch": {"crew": 40}})])
    patch_svc(monkeypatch, store)
    assert svc.get_call_sheet("cs1")["catering_effective"]["lunch"]["crew"] == 40


def _patch_fields(monkeypatch, store, fields):
    patch_svc(monkeypatch, store)
    return svc.update_call_sheet_with_report("cs1", fields)


def test_custom_values_merge_preserves_other_keys(monkeypatch):
    store = make_store(call_sheets=[sheet_row(custom_values={"wind": "SSW", "old_removed": "keep"})])
    row, ignored = _patch_fields(monkeypatch, store, {"custom_values": {"map": "https://x.com/m"}})
    assert row["custom_values"] == {"wind": "SSW", "old_removed": "keep", "map": "https://x.com/m"}
    assert ignored == []


def test_custom_values_null_clears_and_unknown_is_ignored(monkeypatch):
    store = make_store(call_sheets=[sheet_row(custom_values={"wind": "SSW"})])
    row, ignored = _patch_fields(monkeypatch, store, {"custom_values": {"wind": None, "bogus": "x"}})
    assert row["custom_values"] == {}
    assert ignored == ["bogus"]


def test_custom_values_rejects_invalid_link(monkeypatch):
    with pytest.raises(ValueError, match="map"):
        _patch_fields(monkeypatch, make_store(), {"custom_values": {"map": "javascript:alert(1)"}})


def test_builtin_time_normalized_and_blank_clears(monkeypatch):
    store = make_store()
    row, _ = _patch_fields(monkeypatch, store, {"sunrise_time": "06:12:00", "general_call": ""})
    assert row["sunrise_time"] == "06:12" and row["general_call"] is None


def test_builtin_bad_time_rejected(monkeypatch):
    with pytest.raises(ValueError):
        _patch_fields(monkeypatch, make_store(), {"lunch_time": "noonish"})


def test_scene_extras_merge_and_unknown_scene_ignored(monkeypatch):
    store = make_store(
        scenes=[{"id": "sc1", "scene_number": "1"}],
        shooting_day_scenes=[{"shooting_day_id": "d1", "scene_id": "sc1", "sort_order": 0}],
    )
    row, ignored = _patch_fields(monkeypatch, store, {"scene_extras": {
        "sc1": {"story_day": "Day 4", "nope": "x"}, "scX": {"story_day": "y"}}})
    assert row["scene_extras"] == {"sc1": {"story_day": "Day 4"}}
    assert set(ignored) == {"sc1.nope", "scX"}


def test_dept_overrides(monkeypatch):
    row, ignored = _patch_fields(monkeypatch, make_store(), {"dept_overrides": {
        "wardrobe": {"call": "07:00:00", "as_per": "Sam"}, "art": {"call": "06:00"}}})
    assert row["dept_overrides"] == {"wardrobe": {"call": "07:00", "as_per": "Sam"}}
    assert ignored == ["art"]


def test_catering_patch_validates_counts(monkeypatch):
    row, _ = _patch_fields(monkeypatch, make_store(), {"catering": {"lunch": {"crew": 40}}})
    assert row["catering"] == {"lunch": {"crew": 40}}
    with pytest.raises(ValueError):
        _patch_fields(monkeypatch, make_store(), {"catering": {"lunch": {"crew": -2}}})


def test_header_values_and_block_overrides(monkeypatch):
    row, ignored = _patch_fields(monkeypatch, make_store(), {
        "header_values": {"director": "B. Other", "zzz": "x"},
        "block_overrides": {"safety": "Hard hats today"}})
    assert row["header_values"] == {"director": "B. Other"}
    assert row["block_overrides"] == {"safety": "Hard hats today"}
    assert ignored == ["zzz"]


def test_removed_field_value_restored_when_readded(monkeypatch):
    cfg = full_config()
    cfg["day_fields"] = [f for f in cfg["day_fields"] if f["key"] != "wind"]
    store = make_store(cfg=cfg, call_sheets=[sheet_row(custom_values={"wind": "SSW"})])
    patch_svc(monkeypatch, store)
    data = svc.get_call_sheet("cs1")
    assert data["custom_values"] == {"wind": "SSW"}   # stored, just not in template


def test_update_call_sheet_wrapper_returns_row_only(monkeypatch):
    patch_svc(monkeypatch, make_store())
    row = svc.update_call_sheet("cs1", {"weather": "Sunny"})
    assert row["weather"] == "Sunny"


def test_update_not_found(monkeypatch):
    patch_svc(monkeypatch, make_store())
    assert svc.update_call_sheet_with_report("nope", {"weather": "x"}) == (svc.NOT_FOUND, [])
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_customization_service.py -v`
Expected: FAIL (`AttributeError: ... update_call_sheet_with_report` / missing `template` key).

- [ ] **Step 4: Implement the service changes**

In `call_sheet_service.py`, extend the imports and constants:

```python
from services import call_sheet_template_service as tpl
from services import call_sheet_values as values

DAY_INFO_FIELDS = (
    "weather", "sunrise_time", "sunset_time", "breakfast_time", "lunch_time",
    "nearest_hospital", "parking_notes", "safety_notes", "general_notes",
    "general_call",
)
_TIME_FIELDS = ("sunrise_time", "sunset_time", "breakfast_time", "lunch_time", "general_call")


def _safe_time(value):
    """HH:MM:SS -> HH:MM for display; leave anything unparseable untouched."""
    try:
        return values.normalize_time(value)
    except ValueError:
        return value
```

Replace `get_call_sheet` with:

```python
def get_call_sheet(call_sheet_id):
    supabase = get_supabase_admin()
    row = _get(supabase, call_sheet_id)
    if not row:
        return NOT_FOUND
    crew = (supabase.table("call_sheet_crew").select("*")
            .eq("call_sheet_id", call_sheet_id).execute().data or [])
    cast = (supabase.table("call_sheet_cast").select("*")
            .eq("call_sheet_id", call_sheet_id).execute().data or [])
    locations = (supabase.table("call_sheet_locations").select("*")
                 .eq("call_sheet_id", call_sheet_id)
                 .order("sort_order", desc=False).execute().data or [])
    crew = _embed_crew(supabase, crew)
    cast = _embed_cast(supabase, cast)
    for r in crew + cast:
        r["call_time"] = _safe_time(r.get("call_time"))
    sheet = dict(row)
    for f in _TIME_FIELDS:
        if f in sheet:
            sheet[f] = _safe_time(sheet[f])
    template = tpl.get_template(row["production_id"], supabase)
    defaults = values.catering_defaults(crew, cast)
    return {
        **sheet,
        "crew": crew,
        "cast": cast,
        "locations": _embed_locations(supabase, locations),
        "scenes": get_day_scenes(supabase, row["shooting_day_id"]),
        "template": template["config"],
        "template_updated_at": template["updated_at"],
        "catering_defaults": defaults,
        "catering_effective": values.effective_catering(defaults, row.get("catering")),
    }
```

Replace `update_call_sheet` with:

```python
def update_call_sheet_with_report(call_sheet_id, fields):
    """Returns (row | NOT_FOUND, ignored_keys). Raises ValueError on invalid values.
    JSONB payloads merge per key; unknown keys are ignored, not stored."""
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return NOT_FOUND, []
    cfg = tpl.get_template(sheet["production_id"], supabase)["config"]
    patch, ignored = {}, []

    for f in DAY_INFO_FIELDS:
        if f in fields:
            try:
                patch[f] = values.validate_value(tpl.BUILTIN_TYPES[f], fields[f])
            except ValueError as e:
                raise ValueError(f"{f}: {e}")
    if "status" in fields and fields["status"] in ("draft", "published"):
        patch["status"] = fields["status"]

    if "custom_values" in fields:
        types = {d["key"]: d["type"] for d in cfg["day_fields"] if not d["builtin"]}
        patch["custom_values"], ign = values.merge_values(
            sheet.get("custom_values"), fields["custom_values"], types)
        ignored += ign
    if "dept_overrides" in fields:
        patch["dept_overrides"], ign = values.merge_nested(
            sheet.get("dept_overrides"), fields["dept_overrides"],
            {d["key"] for d in cfg["departments"]}, {"call": "time", "as_per": "text"})
        ignored += ign
    if "scene_extras" in fields:
        scene_ids = {s["id"] for s in get_day_scenes(supabase, sheet["shooting_day_id"])}
        types = {c["key"]: c["type"] for c in cfg["scene_columns"]}
        patch["scene_extras"], ign = values.merge_nested(
            sheet.get("scene_extras"), fields["scene_extras"], scene_ids, types)
        ignored += ign
    if "catering" in fields:
        patch["catering"], ign = values.merge_nested(
            sheet.get("catering"), fields["catering"], set(values.MEALS),
            {g: "count" for g in values.CATERING_GROUPS})
        ignored += ign
    if "header_values" in fields:
        patch["header_values"], ign = values.merge_values(
            sheet.get("header_values"), fields["header_values"],
            {k["key"]: "text" for k in cfg["key_crew"]})
        ignored += ign
    if "block_overrides" in fields:
        patch["block_overrides"], ign = values.merge_values(
            sheet.get("block_overrides"), fields["block_overrides"],
            {b["key"]: "textarea" for b in cfg["blocks"]})
        ignored += ign

    if not patch:
        return _get(supabase, call_sheet_id), ignored
    res = (supabase.table("call_sheets").update(patch)
           .eq("id", call_sheet_id).execute())
    return (res.data[0] if res.data else NOT_FOUND), ignored


def update_call_sheet(call_sheet_id, fields):
    return update_call_sheet_with_report(call_sheet_id, fields)[0]
```

Replace the route in `call_sheet_routes.py`:

```python
@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def update_call_sheet(call_sheet_id):
    data = request.get_json(silent=True) or {}
    try:
        result, ignored = svc.update_call_sheet_with_report(call_sheet_id, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Call sheet not found"}), 404
    return jsonify({"call_sheet": result, "ignored_keys": ignored})
```

- [ ] **Step 5: Run to verify it passes (and v1 tests still pass)**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_customization_service.py tests/test_call_sheet_service.py tests/test_call_sheet_routes.py -v`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add backend/services/call_sheet_service.py backend/routes/call_sheet_routes.py backend/tests/call_sheet_customization_support.py backend/tests/test_call_sheet_customization_service.py
git commit -m "$(cat <<'EOF'
feat(call-sheets): return template and accept merged custom values on PATCH

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Roster `extra` (custom cast/crew column values) in the service

**Files:**
- Modify: `backend/services/call_sheet_service.py` (`add_crew`, `update_crew_call`, `add_cast`, `update_cast_call`, new `_column_types`)
- Test: `backend/tests/test_call_sheet_customization_service.py` (append)

**Interfaces:**
- Consumes: `tpl.get_template`, `values.merge_values`; test support from Task 5.
- Produces: `add_crew(call_sheet_id, crew_id, call_time=None, notes=None, extra=None)`, `add_cast(call_sheet_id, casting_id, call_time=None, status_code=None, notes=None, extra=None)`; `update_crew_call` / `update_cast_call` accept an `"extra"` key in `fields` and merge it per key into the row's stored `extra`. Unknown column keys are dropped silently; invalid values raise `ValueError`. Returned rows include `extra`.

- [ ] **Step 1: Write the failing tests (append to `test_call_sheet_customization_service.py`)**

```python
def _roster_store(**overrides):
    return make_store(
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": None}],
        casting=[{"id": "ca1", "script_id": "s1", "character_name": "HERO",
                  "actor_name": "Jo", "tier": "lead"}],
        **overrides)


def test_add_crew_stores_valid_extra_and_drops_unknown(monkeypatch):
    patch_svc(monkeypatch, _roster_store())
    row = svc.add_crew("cs1", "cr1", "06:00", None, {"vehicle": "Van 2", "bogus": "x"})
    assert row["extra"] == {"vehicle": "Van 2"}


def test_add_crew_extra_defaults_to_empty(monkeypatch):
    patch_svc(monkeypatch, _roster_store())
    assert svc.add_crew("cs1", "cr1")["extra"] == {}


def test_add_cast_validates_extra_types(monkeypatch):
    patch_svc(monkeypatch, _roster_store())
    with pytest.raises(ValueError, match="pickup"):
        svc.add_cast("cs1", "ca1", extra={"pickup": "noon"})
    row = svc.add_cast("cs1", "ca1", "07:00", "W", None, {"pickup": "06:15:00"})
    assert row["extra"] == {"pickup": "06:15"}


def test_update_crew_call_merges_extra(monkeypatch):
    store = _roster_store(call_sheet_crew=[
        {"id": "x", "call_sheet_id": "cs1", "crew_id": "cr1", "call_time": None,
         "extra": {"vehicle": "Van 2"}}])
    patch_svc(monkeypatch, store)
    row = svc.update_crew_call("cs1", "cr1", {"extra": {"vehicle": None}})
    assert row["extra"] == {}
    row = svc.update_crew_call("cs1", "cr1", {"extra": {"vehicle": "Truck"}})
    assert row["extra"] == {"vehicle": "Truck"}


def test_update_crew_call_leaves_extra_alone_when_not_sent(monkeypatch):
    store = _roster_store(call_sheet_crew=[
        {"id": "x", "call_sheet_id": "cs1", "crew_id": "cr1", "call_time": None,
         "extra": {"vehicle": "Van 2"}}])
    patch_svc(monkeypatch, store)
    row = svc.update_crew_call("cs1", "cr1", {"call_time": "05:00"})
    assert row["extra"] == {"vehicle": "Van 2"} and row["call_time"] == "05:00"


def test_update_cast_call_merges_extra(monkeypatch):
    store = _roster_store(call_sheet_cast=[
        {"id": "y", "call_sheet_id": "cs1", "casting_id": "ca1", "call_time": None,
         "extra": {"pickup": "06:00"}}])
    patch_svc(monkeypatch, store)
    row = svc.update_cast_call("cs1", "ca1", {"extra": {"pickup": "07:30", "zzz": "1"}})
    assert row["extra"] == {"pickup": "07:30"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_customization_service.py -k "extra" -v`
Expected: FAIL (`TypeError: add_crew() takes from 3 to 5 positional arguments` / missing `extra`).

- [ ] **Step 3: Implement**

Add the helper near `_get` in `call_sheet_service.py`:

```python
def _column_types(supabase, sheet, list_key):
    """{column_key: type} for cast_columns / crew_columns / scene_columns."""
    cfg = tpl.get_template(sheet["production_id"], supabase)["config"]
    return {c["key"]: c["type"] for c in cfg[list_key]}
```

Replace the four roster functions:

```python
def add_crew(call_sheet_id, crew_id, call_time=None, notes=None, extra=None):
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    crew_res = (supabase.table("production_crew").select("*")
                .eq("id", crew_id).limit(1).execute())
    if not crew_res.data or crew_res.data[0].get("production_id") != sheet["production_id"]:
        return "cross_production"
    extra_clean, _ = values.merge_values(
        {}, extra or {}, _column_types(supabase, sheet, "crew_columns"))
    row = {"call_sheet_id": call_sheet_id, "crew_id": crew_id,
           "call_time": call_time, "notes": notes, "extra": extra_clean}
    created = supabase.table("call_sheet_crew").insert(row).execute().data[0]
    return _embed_crew(supabase, [created])[0]


def update_crew_call(call_sheet_id, crew_id, fields):
    """UPDATE (not insert) an existing call_sheet_crew row -- crew rows are
    added once via add_crew and then edited in place (a plain insert would
    collide with UNIQUE (call_sheet_id, crew_id)). `extra` merges per key."""
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    existing = (supabase.table("call_sheet_crew").select("*")
                .eq("call_sheet_id", call_sheet_id).eq("crew_id", crew_id)
                .limit(1).execute())
    if not existing.data:
        return "not_found"
    patch = {f: fields[f] for f in _CREW_CALL_FIELDS if f in fields}
    if "extra" in fields:
        patch["extra"], _ = values.merge_values(
            existing.data[0].get("extra"), fields["extra"],
            _column_types(supabase, sheet, "crew_columns"))
    if not patch:
        return _embed_crew(supabase, existing.data)[0]
    res = (supabase.table("call_sheet_crew").update(patch)
           .eq("call_sheet_id", call_sheet_id).eq("crew_id", crew_id).execute())
    return _embed_crew(supabase, [res.data[0]])[0] if res.data else "not_found"


def add_cast(call_sheet_id, casting_id, call_time=None, status_code=None, notes=None, extra=None):
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    script_id = _script_id_for_day(supabase, sheet["shooting_day_id"])
    casting_res = (supabase.table("casting").select("*")
                   .eq("id", casting_id).limit(1).execute())
    if not casting_res.data or casting_res.data[0].get("script_id") != script_id:
        return "cross_script"
    extra_clean, _ = values.merge_values(
        {}, extra or {}, _column_types(supabase, sheet, "cast_columns"))
    row = {"call_sheet_id": call_sheet_id, "casting_id": casting_id,
           "call_time": call_time, "status_code": status_code, "notes": notes,
           "extra": extra_clean}
    created = supabase.table("call_sheet_cast").insert(row).execute().data[0]
    return _embed_cast(supabase, [created])[0]


def update_cast_call(call_sheet_id, casting_id, fields):
    """UPDATE counterpart to add_cast -- same UNIQUE constraint rationale;
    `extra` merges per key."""
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    existing = (supabase.table("call_sheet_cast").select("*")
                .eq("call_sheet_id", call_sheet_id).eq("casting_id", casting_id)
                .limit(1).execute())
    if not existing.data:
        return "not_found"
    patch = {f: fields[f] for f in _CAST_CALL_FIELDS if f in fields}
    if "extra" in fields:
        patch["extra"], _ = values.merge_values(
            existing.data[0].get("extra"), fields["extra"],
            _column_types(supabase, sheet, "cast_columns"))
    if not patch:
        return _embed_cast(supabase, existing.data)[0]
    res = (supabase.table("call_sheet_cast").update(patch)
           .eq("call_sheet_id", call_sheet_id).eq("casting_id", casting_id).execute())
    return _embed_cast(supabase, [res.data[0]])[0] if res.data else "not_found"
```

(Keep `_CREW_CALL_FIELDS`, `_CAST_CALL_FIELDS`, `remove_crew`, `remove_cast` unchanged.)

- [ ] **Step 4: Run to verify it passes (v1 roster tests too)**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_customization_service.py tests/test_call_sheet_service.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add backend/services/call_sheet_service.py backend/tests/test_call_sheet_customization_service.py
git commit -m "$(cat <<'EOF'
feat(call-sheets): custom cast/crew column values (extra) in service

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Redaction of sensitive custom data + route wiring

**Files:**
- Modify: `backend/services/call_sheet_service.py` (`redact_roster`, `render_call_sheet_pdf`)
- Modify: `backend/routes/call_sheet_routes.py` (GET routes, crew/cast add+update routes, PDF route)
- Test: `backend/tests/test_call_sheet_customization_service.py` (append), `backend/tests/test_call_sheet_customization_routes.py` (new)

**Interfaces:**
- Consumes: `tpl.default_config`, `tpl.get_template`; `g.resolved_production_id` and `g.production_access` (set by `require_production_role`).
- Produces:
  - `redact_roster(call_sheet_data, can_view_sensitive, template=None)` — also strips `sensitive` custom values from cast/crew `extra`, `scene_extras`, day fields (custom → removed from `custom_values`; builtin → set to `None`). Falls back to `call_sheet_data["template"]`, then the default template.
  - `render_call_sheet_pdf(call_sheet_id, can_view_sensitive=False)` (safe default) redacts before rendering.
  - GET call-sheet routes add `"can_view_sensitive": bool` to `call_sheet`; crew/cast add+update responses are redacted; add/update pass `extra` and return 400 on `ValueError`.

- [ ] **Step 1: Write the failing service tests (append)**

```python
def _sensitive_cfg():
    cfg = full_config()
    cfg["crew_columns"] = [
        {"key": "vehicle", "label": "Vehicle", "type": "text", "sensitive": True},
        {"key": "note", "label": "Note", "type": "text", "sensitive": False}]
    cfg["cast_columns"] = [
        {"key": "pickup", "label": "P/U", "type": "time", "sensitive": False},
        {"key": "fee", "label": "Fee", "type": "text", "sensitive": True}]
    cfg["scene_columns"] = [
        {"key": "story_day", "label": "Story day", "type": "text", "sensitive": False},
        {"key": "budget", "label": "Budget", "type": "text", "sensitive": True}]
    cfg["day_fields"] += [{"key": "secret", "label": "Secret", "type": "text", "section": "notes",
                           "default": "", "sensitive": True, "visible": True, "builtin": False}]
    next(f for f in cfg["day_fields"] if f["key"] == "nearest_hospital")["sensitive"] = True
    return cfg


def _sensitive_data(monkeypatch):
    store = make_store(
        cfg=_sensitive_cfg(),
        call_sheets=[sheet_row(nearest_hospital="City Hospital",
                               custom_values={"secret": "s3", "wind": "SSW"},
                               scene_extras={"sc1": {"story_day": "4", "budget": "9"}})],
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": None, "job_rate": 5}],
        call_sheet_crew=[{"id": "x", "call_sheet_id": "cs1", "crew_id": "cr1",
                          "extra": {"vehicle": "Van", "note": "n"}}],
        casting=[{"id": "ca1", "script_id": "s1", "character_name": "H", "tier": "lead"}],
        call_sheet_cast=[{"id": "y", "call_sheet_id": "cs1", "casting_id": "ca1",
                          "extra": {"pickup": "06:00", "fee": "1000"}}],
    )
    patch_svc(monkeypatch, store)
    return svc.get_call_sheet("cs1")


def test_redact_strips_sensitive_custom_data(monkeypatch):
    data = svc.redact_roster(_sensitive_data(monkeypatch), can_view_sensitive=False)
    assert data["crew"][0]["extra"] == {"note": "n"}
    assert data["cast"][0]["extra"] == {"pickup": "06:00"}
    assert data["scene_extras"] == {"sc1": {"story_day": "4"}}
    assert data["custom_values"] == {"wind": "SSW"}
    assert data["nearest_hospital"] is None            # sensitive builtin blanked
    assert "job_rate" not in data["crew"][0]["crew"]   # v1 behaviour retained


def test_redact_noop_for_sensitive_viewer(monkeypatch):
    data = svc.redact_roster(_sensitive_data(monkeypatch), can_view_sensitive=True)
    assert data["crew"][0]["extra"]["vehicle"] == "Van"
    assert data["custom_values"]["secret"] == "s3"
    assert data["nearest_hospital"] == "City Hospital"


def test_redact_row_with_explicit_template(monkeypatch):
    row = {"crew": [{"extra": {"vehicle": "Van", "note": "n"}}]}
    out = svc.redact_roster(row, False, _sensitive_cfg())
    assert out["crew"][0]["extra"] == {"note": "n"}


def test_pdf_render_redacts_by_default(monkeypatch):
    _sensitive_data(monkeypatch)
    captured = {}

    def fake_render(data, day):
        captured["data"] = data
        return "<html></html>"

    monkeypatch.setattr(svc, "_render_pdf_html", fake_render)
    svc.render_call_sheet_pdf("cs1")
    assert captured["data"]["cast"][0]["extra"] == {"pickup": "06:00"}
    svc.render_call_sheet_pdf("cs1", can_view_sensitive=True)
    assert captured["data"]["cast"][0]["extra"]["fee"] == "1000"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_customization_service.py -k "redact or pdf_render" -v`
Expected: FAIL (`redact_roster() got an unexpected keyword` / sensitive values still present).

- [ ] **Step 3: Implement the service changes**

Replace `redact_roster` in `call_sheet_service.py`:

```python
def _pop_keys(mapping, keys):
    if isinstance(mapping, dict):
        for k in keys:
            mapping.pop(k, None)


def _sensitive_keys(template, list_key):
    return {c["key"] for c in template.get(list_key, []) if c.get("sensitive")}


def redact_roster(call_sheet_data, can_view_sensitive, template=None):
    """Strip rate fields (v1) plus any column/field the template flags
    `sensitive`. `template` falls back to the data's own, then the default."""
    if can_view_sensitive:
        return call_sheet_data
    template = template or call_sheet_data.get("template") or tpl.default_config()

    crew_cols = _sensitive_keys(template, "crew_columns")
    for row in call_sheet_data.get("crew", []):
        _pop_keys(row.get("extra"), crew_cols)
        crew = row.get("crew")
        if isinstance(crew, dict):
            for k in _SENSITIVE_CREW:
                crew.pop(k, None)
            contact = crew.get("contact")
            if isinstance(contact, dict):
                for k in _SENSITIVE_CONTACT:
                    contact.pop(k, None)

    cast_cols = _sensitive_keys(template, "cast_columns")
    for row in call_sheet_data.get("cast", []):
        _pop_keys(row.get("extra"), cast_cols)

    scene_cols = _sensitive_keys(template, "scene_columns")
    for extras in (call_sheet_data.get("scene_extras") or {}).values():
        _pop_keys(extras, scene_cols)

    for field in template.get("day_fields", []):
        if not field.get("sensitive"):
            continue
        if field.get("builtin"):
            if field["key"] in call_sheet_data:
                call_sheet_data[field["key"]] = None
        else:
            _pop_keys(call_sheet_data.get("custom_values"), [field["key"]])
    return call_sheet_data
```

Update `render_call_sheet_pdf` (signature + redaction, safe default):

```python
def render_call_sheet_pdf(call_sheet_id, can_view_sensitive=False):
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("weasyprint is not installed")
    supabase = get_supabase_admin()
    data = get_call_sheet(call_sheet_id)
    if data is NOT_FOUND:
        return NOT_FOUND
    data = redact_roster(data, can_view_sensitive)
    day_res = (supabase.table("shooting_days").select("*")
               .eq("id", data["shooting_day_id"]).limit(1).execute())
    day = day_res.data[0] if day_res.data else {}
    html_content = _render_pdf_html(data, day)
    css = report_service._get_report_css()
    from weasyprint import CSS
    return HTML(string=html_content).write_pdf(stylesheets=[CSS(string=css)])
```

- [ ] **Step 4: Write the failing route tests**

```python
# backend/tests/test_call_sheet_customization_routes.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_service as cs_svc
from call_sheet_customization_support import full_config, sheet_row
from test_call_sheet_routes import _client, _store, _member_store, _patch


def _cfg():
    cfg = full_config()
    cfg["cast_columns"] = [
        {"key": "pickup", "label": "P/U", "type": "time", "sensitive": False},
        {"key": "fee", "label": "Fee", "type": "text", "sensitive": True}]
    return cfg


def _extra_tables(store):
    store["casting"] = [{"id": "ca1", "script_id": "s1", "character_name": "HERO", "tier": "lead"}]
    store["call_sheet_templates"] = [{"id": "t1", "production_id": "p1", "config": _cfg(),
                                      "updated_at": "t"}]
    return store


def _coordinator_store():
    return _extra_tables(_member_store("coordinator", can_edit_call_sheets=True))


def _owner_store():
    return _extra_tables(_store(call_sheets=[sheet_row()]))


BODY = {"casting_id": "ca1", "extra": {"pickup": "06:00", "fee": "1000"}}


def test_cast_add_redacts_sensitive_extra_for_non_sensitive_member(monkeypatch):
    _patch(monkeypatch, _coordinator_store())
    resp = _client().post("/api/call-sheets/cs1/cast", json=BODY)
    assert resp.status_code == 201
    assert resp.get_json()["cast"]["extra"] == {"pickup": "06:00"}


def test_cast_add_shows_sensitive_extra_to_owner(monkeypatch):
    _patch(monkeypatch, _owner_store())
    resp = _client().post("/api/call-sheets/cs1/cast", json=BODY)
    assert resp.get_json()["cast"]["extra"] == {"pickup": "06:00", "fee": "1000"}


def test_cast_update_redacts(monkeypatch):
    store = _coordinator_store()
    store["call_sheet_cast"] = [{"id": "y", "call_sheet_id": "cs1", "casting_id": "ca1",
                                 "extra": {"pickup": "06:00", "fee": "1000"}}]
    _patch(monkeypatch, store)
    resp = _client().patch("/api/call-sheets/cs1/cast/ca1", json={"extra": {"pickup": "07:00"}})
    assert resp.status_code == 200
    assert resp.get_json()["cast"]["extra"] == {"pickup": "07:00"}


def test_cast_add_bad_extra_is_400(monkeypatch):
    _patch(monkeypatch, _owner_store())
    resp = _client().post("/api/call-sheets/cs1/cast",
                          json={"casting_id": "ca1", "extra": {"pickup": "noon"}})
    assert resp.status_code == 400


def test_get_call_sheet_redacts_and_flags_sensitivity(monkeypatch):
    store = _coordinator_store()
    store["call_sheet_cast"] = [{"id": "y", "call_sheet_id": "cs1", "casting_id": "ca1",
                                 "extra": {"pickup": "06:00", "fee": "1000"}}]
    _patch(monkeypatch, store)
    body = _client().get("/api/call-sheets/cs1").get_json()["call_sheet"]
    assert body["can_view_sensitive"] is False
    assert body["cast"][0]["extra"] == {"pickup": "06:00"}


def test_get_by_day_flags_sensitivity_for_owner(monkeypatch):
    _patch(monkeypatch, _owner_store())
    body = _client().get("/api/shooting-days/d1/call-sheet").get_json()["call_sheet"]
    assert body["can_view_sensitive"] is True


def test_patch_returns_ignored_keys(monkeypatch):
    _patch(monkeypatch, _owner_store())
    resp = _client().patch("/api/call-sheets/cs1", json={"custom_values": {"wind": "SSW", "gone": "x"}})
    assert resp.status_code == 200
    assert resp.get_json()["ignored_keys"] == ["gone"]
    assert resp.get_json()["call_sheet"]["custom_values"] == {"wind": "SSW"}


def test_patch_invalid_value_is_400(monkeypatch):
    _patch(monkeypatch, _owner_store())
    resp = _client().patch("/api/call-sheets/cs1", json={"custom_values": {"map": "javascript:x"}})
    assert resp.status_code == 400 and "map" in resp.get_json()["error"]


def test_pdf_route_passes_sensitivity(monkeypatch):
    seen = {}

    def fake(call_sheet_id, can_view_sensitive=False):
        seen["v"] = can_view_sensitive
        return b"%PDF-1.4"

    monkeypatch.setattr(cs_svc, "render_call_sheet_pdf", fake)
    _patch(monkeypatch, _coordinator_store())
    assert _client().get("/api/call-sheets/cs1/pdf").status_code == 200
    assert seen["v"] is False
    _patch(monkeypatch, _owner_store())
    _client().get("/api/call-sheets/cs1/pdf")
    assert seen["v"] is True
```

- [ ] **Step 5: Run to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_customization_routes.py -v`
Expected: FAIL (`KeyError: 'can_view_sensitive'`; cast responses unredacted).

- [ ] **Step 6: Implement the route changes**

In `call_sheet_routes.py` add the helper below the blueprint definition:

```python
def _redact_one(kind, row):
    """Redact a single crew/cast row using this production's template."""
    template = tpl.get_template(g.resolved_production_id)["config"]
    return svc.redact_roster({kind: [row]}, g.production_access["can_view_sensitive"],
                             template)[kind][0]
```

Replace the two GET routes' bodies (after `redact_roster`) to add the flag:

```python
    result = svc.redact_roster(result, g.production_access["can_view_sensitive"])
    result["can_view_sensitive"] = bool(g.production_access["can_view_sensitive"])
    return jsonify({"call_sheet": result})
```

(apply to both `get_call_sheet_by_day` and `get_call_sheet`). Replace the four roster write routes:

```python
@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/crew", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def add_call_sheet_crew(call_sheet_id):
    data = request.get_json(silent=True) or {}
    crew_id = data.get("crew_id")
    if not crew_id:
        return jsonify({"error": "crew_id is required"}), 400
    try:
        result = svc.add_crew(call_sheet_id, crew_id, data.get("call_time"),
                              data.get("notes"), data.get("extra"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if result == "not_found":
        return jsonify({"error": "Call sheet not found"}), 404
    if result == "cross_production":
        return jsonify({"error": "That crew member is not part of this production"}), 400
    return jsonify({"crew": _redact_one("crew", result)}), 201


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/crew/<crew_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def update_call_sheet_crew(call_sheet_id, crew_id):
    data = request.get_json(silent=True) or {}
    try:
        result = svc.update_crew_call(call_sheet_id, crew_id, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if result == "not_found":
        return jsonify({"error": "Call sheet or crew row not found"}), 404
    return jsonify({"crew": _redact_one("crew", result)})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/cast", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def add_call_sheet_cast(call_sheet_id):
    data = request.get_json(silent=True) or {}
    casting_id = data.get("casting_id")
    if not casting_id:
        return jsonify({"error": "casting_id is required"}), 400
    try:
        result = svc.add_cast(call_sheet_id, casting_id, data.get("call_time"),
                              data.get("status_code"), data.get("notes"), data.get("extra"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if result == "not_found":
        return jsonify({"error": "Call sheet not found"}), 404
    if result == "cross_script":
        return jsonify({"error": "That cast member is not part of this shooting day's script"}), 400
    return jsonify({"cast": _redact_one("cast", result)}), 201


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/cast/<casting_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def update_call_sheet_cast(call_sheet_id, casting_id):
    data = request.get_json(silent=True) or {}
    try:
        result = svc.update_cast_call(call_sheet_id, casting_id, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if result == "not_found":
        return jsonify({"error": "Call sheet or cast row not found"}), 404
    return jsonify({"cast": _redact_one("cast", result)})
```

Replace the PDF route's render call:

```python
    pdf_bytes = svc.render_call_sheet_pdf(call_sheet_id, g.production_access["can_view_sensitive"])
```

- [ ] **Step 7: Run to verify everything passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_customization_routes.py tests/test_call_sheet_customization_service.py tests/test_call_sheet_service.py tests/test_call_sheet_routes.py tests/test_route_enforcement.py -v`
Expected: PASS (all).

- [ ] **Step 8: Commit**

```bash
git add backend/services/call_sheet_service.py backend/routes/call_sheet_routes.py backend/tests/test_call_sheet_customization_service.py backend/tests/test_call_sheet_customization_routes.py
git commit -m "$(cat <<'EOF'
feat(call-sheets): redact sensitive custom data in JSON, roster responses and PDF

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Config-driven renderer — header, day info, locations, scenes, cast, crew, notes

**Files:**
- Create: `backend/services/call_sheet_render.py`
- Modify: `backend/services/call_sheet_service.py` (remove `_esc` and `_render_pdf_html`; add `_render_context`, `build_call_sheet_html`; rewrite `render_call_sheet_pdf`)
- Modify: `backend/tests/test_call_sheet_customization_service.py` (fix the Task 7 PDF test to the new seam)
- Test: `backend/tests/test_call_sheet_render.py`

**Interfaces:**
- Consumes: `tpl.default_config`, `values`, `department_service.get_departments_list/get_department_name`.
- Produces:
  - `call_sheet_render.render_html(data, ctx) -> str` — pure. `data` is `get_call_sheet` output (already redacted); `ctx = {"day": dict, "production_title": str|None, "days_total": int|None, "advanced": {"day": dict, "scenes": list}|None}`.
  - `call_sheet_render.SECTION_RENDERERS: dict[str, callable(data, cfg, ctx) -> str | None]` (Task 9 adds the remaining four sections); a renderer returning `None` omits its section.
  - `call_sheet_render.split_cast(data, cfg) -> (main_rows, extras_rows)`.
  - `call_sheet_service.build_call_sheet_html(call_sheet_id, can_view_sensitive=False) -> str | NOT_FOUND`; `render_call_sheet_pdf` delegates to it.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_call_sheet_render.py
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_render as render
import services.call_sheet_template_service as tpl
import services.department_service as ds
from call_sheet_customization_support import full_config


def _data(cfg=None, **kw):
    data = {
        "status": "published", "template": cfg or tpl.default_config(),
        "weather": "Sunny", "sunrise_time": "06:12", "nearest_hospital": "City Hospital",
        "safety_notes": "Officer Jo", "general_notes": "Bring water",
        "parking_notes": "SECRET-PARKING", "custom_values": {},
        "locations": [{"is_primary": True, "sort_order": 0,
                       "location": {"name": "Warehouse", "address": "1 Main St", "parking_notes": "Lot B"}}],
        "scenes": [{"id": "sc1", "scene_number": "12", "int_ext": "INT", "setting": "OFFICE",
                    "time_of_day": "DAY", "page_length_eighths": 3}],
        "scene_extras": {},
        "cast": [{"call_time": "06:00", "status_code": "W", "extra": {},
                  "casting": {"character_name": "HERO", "actor_name": "Jo", "tier": "lead"}}],
        "crew": [{"call_time": "05:30", "extra": {},
                  "crew": {"department_code": "camera", "role": "DoP",
                           "contact": {"name": "Gary"}}}],
    }
    data.update(kw)
    return data


CTX = {"day": {"day_number": 3, "shoot_date": "2026-10-01"},
       "production_title": "Farm Feature", "days_total": 12, "advanced": None}


def _html(data, ctx=None, monkeypatch=None):
    return render.render_html(data, ctx or CTX)


def _patch_depts(monkeypatch):
    monkeypatch.setattr(ds, "get_departments_list",
                        lambda: [{"code": "camera", "name": "Camera", "color": "#1"}])


def test_default_template_renders_v1_content_only(monkeypatch):
    _patch_depts(monkeypatch)
    html = _html(_data())
    for expected in ("Weather", "Sunny", "City Hospital", "Officer Jo", "Bring water",
                     "Warehouse", "Lot B", "HERO", "Gary", "OFFICE"):
        assert expected in html
    assert "SECRET-PARKING" not in html          # parking_notes hidden by default
    assert "General Call" not in html            # hidden by default
    assert "Extras" not in html and "Catering" not in html


def test_default_section_order_matches_v1(monkeypatch):
    _patch_depts(monkeypatch)
    html = _html(_data())
    order = [html.index(t) for t in ("Locations", "Scene Schedule", "Cast Call List", "Crew Call List")]
    assert order == sorted(order)


def test_header_shows_title_day_of_total_and_draft_banner(monkeypatch):
    _patch_depts(monkeypatch)
    html = _html(_data(status="draft"))
    assert "Farm Feature" in html and "Day 3 of 12" in html and "2026-10-01" in html
    assert "DRAFT" in html
    assert "DRAFT" not in _html(_data(status="published"))


def test_hidden_section_is_omitted(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = tpl.default_config()
    next(s for s in cfg["sections"] if s["key"] == "scenes")["visible"] = False
    html = _html(_data(cfg))
    assert "Scene Schedule" not in html and "OFFICE" not in html


def test_section_order_and_label_follow_template(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = tpl.default_config()
    secs = {s["key"]: s for s in cfg["sections"]}
    secs["crew"]["label"] = "Crew Calls"
    cfg["sections"] = [secs["header"], secs["crew"], secs["cast"]] + \
        [s for s in cfg["sections"] if s["key"] not in ("header", "crew", "cast")]
    html = _html(_data(cfg))
    assert html.index("Crew Calls") < html.index("Cast Call List")


def test_custom_field_renders_only_in_its_section_and_once(monkeypatch):
    _patch_depts(monkeypatch)
    html = _html(_data(full_config(), custom_values={"wind": "SSW 15"}))
    assert html.count("SSW 15") == 1
    assert html.index("Wind") < html.index("Locations")     # day_info is above locations


def test_field_default_used_when_no_value(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = full_config()
    next(f for f in cfg["day_fields"] if f["key"] == "wind")["default"] = "Calm"
    assert "Calm" in _html(_data(cfg))


def test_link_field_renders_anchor_and_escapes(monkeypatch):
    _patch_depts(monkeypatch)
    html = _html(_data(full_config(), custom_values={"map": "https://x.com/m?a=1&b=2"}))
    assert '<a href="https://x.com/m?a=1&amp;b=2">' in html


def test_user_text_is_escaped(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = full_config()
    cfg["day_fields"][0]["label"] = "<script>alert(1)</script>"
    cfg["blocks"][0]["body"] = "<img src=x onerror=alert(1)>"
    html = _html(_data(cfg, weather="<b>bold</b>"))
    assert "<script>" not in html and "<img" not in html and "<b>bold</b>" not in html
    assert "&lt;script&gt;" in html


def test_scene_and_cast_and_crew_custom_columns(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = full_config()
    data = _data(cfg,
                 scene_extras={"sc1": {"story_day": "Day 4"}},
                 cast=[{"call_time": "06:00", "status_code": "W", "extra": {"pickup": "05:15"},
                        "casting": {"character_name": "HERO", "actor_name": "Jo", "tier": "lead"}}],
                 crew=[{"call_time": "05:30", "extra": {"vehicle": "Van 2"},
                        "crew": {"department_code": "camera", "role": "DoP", "contact": {"name": "Gary"}}}])
    html = _html(data)
    for expected in ("Story day", "Day 4", "P/U", "05:15", "Vehicle", "Van 2"):
        assert expected in html


def test_background_cast_stays_in_cast_when_extras_hidden():
    cfg = tpl.default_config()
    bg = {"call_time": None, "extra": {}, "casting": {"character_name": "CROWD", "tier": "background"}}
    main, extras = render.split_cast(_data(cfg, cast=[bg]), cfg)
    assert main == [bg] and extras == []


def test_background_cast_moves_to_extras_when_visible():
    cfg = tpl.default_config()
    next(s for s in cfg["sections"] if s["key"] == "extras")["visible"] = True
    lead = {"extra": {}, "casting": {"character_name": "HERO", "tier": "lead"}}
    bg = {"extra": {}, "casting": {"character_name": "CROWD", "tier": "background"}}
    main, extras = render.split_cast(_data(cfg, cast=[lead, bg]), cfg)
    assert main == [lead] and extras == [bg]


def test_notes_blocks_with_day_override(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = full_config()
    html = _html(_data(cfg))
    assert "Special notes" in html and "Closed shoes" in html
    html = _html(_data(cfg, block_overrides={"safety": "Hard hats today"}))
    assert "Hard hats today" in html and "Closed shoes" not in html


def test_key_crew_and_general_call_in_header(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = full_config()
    next(f for f in cfg["day_fields"] if f["key"] == "general_call")["visible"] = True
    data = _data(cfg, general_call="06:00", header_values={"director": "B. Other"})
    html = _html(data)
    assert "General Call" in html and "06:00" in html
    assert "Director" in html and "B. Other" in html and "A. Director" not in html


def test_unknown_section_key_in_config_is_a_noop(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = tpl.default_config()
    cfg["sections"].append({"key": "mystery", "label": "Mystery", "visible": True})
    assert "Mystery" not in _html(_data(cfg))
```

Also update the Task 7 test `test_pdf_render_redacts_by_default` in `test_call_sheet_customization_service.py` to the new seam (the v1 `_render_pdf_html` is being removed): replace its body with

```python
def test_pdf_html_redacts_by_default(monkeypatch):
    _sensitive_data(monkeypatch)
    captured = {}

    def fake_render(data, ctx):
        captured["data"] = data
        return "<html></html>"

    monkeypatch.setattr(svc.render, "render_html", fake_render)
    svc.build_call_sheet_html("cs1")
    assert captured["data"]["cast"][0]["extra"] == {"pickup": "06:00"}
    svc.build_call_sheet_html("cs1", can_view_sensitive=True)
    assert captured["data"]["cast"][0]["extra"]["fee"] == "1000"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_render.py -v`
Expected: FAIL (`ModuleNotFoundError: services.call_sheet_render`).

- [ ] **Step 3: Implement the renderer**

```python
# backend/services/call_sheet_render.py
"""Config-driven call sheet HTML renderer.

Pure: takes the assembled (already redacted) call sheet dict plus a render
context and returns HTML for WeasyPrint. No DB access. All user-authored text
is escaped. See docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md.
"""
import html as _html

from services import department_service
from services import call_sheet_values as values
from services.call_sheet_template_service import default_config

# Repeats a compact header on every page (WeasyPrint running element).
CSS_EXTRA = """
@page { margin-top: 22mm; @top-center { content: element(csrunning); font-size: 9pt; color: #555; } }
.cs-running { position: running(csrunning); }
.cs-section { margin-bottom: 10px; }
.cs-field { margin: 2px 0; }
.cs-block { margin: 6px 0; }
.cs-key-crew span { margin-right: 14px; }
"""


def esc(value):
    return _html.escape(str(value)) if value is not None else ""


def _fmt(ftype, value):
    text = esc(value)
    if ftype == "link" and str(value).lower().startswith(("http://", "https://")):
        return f'<a href="{text}">{text}</a>'
    if ftype == "textarea":
        return f'<span style="white-space: pre-wrap">{text}</span>'
    return text


def _cell(column, value):
    return "" if value in (None, "") else _fmt(column["type"], value)


def _effective(field, data):
    if field.get("builtin"):
        value = data.get(field["key"])
    else:
        value = (data.get("custom_values") or {}).get(field["key"])
    if value in (None, ""):
        value = field.get("default") or ""
    return value


def _fields_html(data, cfg, section):
    out = []
    for field in cfg.get("day_fields", []):
        if field.get("section") != section or not field.get("visible", True):
            continue
        value = _effective(field, data)
        if value in (None, ""):
            continue
        out.append(f'<div class="cs-field"><strong>{esc(field["label"])}:</strong> '
                   f'{_fmt(field["type"], value)}</div>')
    return "".join(out)


def _key_crew_html(data, cfg):
    overrides = data.get("header_values") or {}
    spans = []
    for entry in cfg.get("key_crew", []):
        value = overrides.get(entry["key"], entry.get("value", ""))
        if value:
            spans.append(f'<span><strong>{esc(entry["label"])}:</strong> {esc(value)}</span>')
    return f'<div class="cs-key-crew">{"".join(spans)}</div>' if spans else ""


def split_cast(data, cfg):
    """(main_rows, extras_rows). Background-tier rows only leave the cast table
    when the extras section is visible, so hiding it never drops anyone."""
    rows = data.get("cast", [])
    extras_visible = any(s["key"] == "extras" and s.get("visible", True) for s in cfg["sections"])
    if not extras_visible:
        return rows, []
    bg = [r for r in rows if (r.get("casting") or {}).get("tier") == "background"]
    return [r for r in rows if r not in bg], bg


def _cast_table(rows, cfg, first_labels=("Character", "Actor", "Status", "Call Time")):
    cols = cfg.get("cast_columns", [])
    head = "".join(f"<th>{esc(h)}</th>" for h in first_labels) + \
        "".join(f'<th>{esc(c["label"])}</th>' for c in cols)
    body = ""
    for row in rows:
        casting = row.get("casting") or {}
        extra = row.get("extra") or {}
        body += (f'<tr><td>{esc(casting.get("character_name"))}</td>'
                 f'<td>{esc(casting.get("actor_name"))}</td>'
                 f'<td>{esc(row.get("status_code") or "")}</td>'
                 f'<td>{esc(row.get("call_time") or "")}</td>'
                 + "".join(f'<td>{_cell(c, extra.get(c["key"]))}</td>' for c in cols)
                 + "</tr>")
    return f'<table class="report-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


# ---------- section renderers: (data, cfg, ctx) -> html | None ----------

def _render_header(data, cfg, ctx):
    day = ctx.get("day") or {}
    day_line = f'Day {esc(day.get("day_number"))}'
    if ctx.get("days_total"):
        day_line += f' of {esc(ctx["days_total"])}'
    if day.get("shoot_date"):
        day_line += f' &middot; {esc(day["shoot_date"])}'
    title = f'<h1>{esc(ctx["production_title"])}</h1>' if ctx.get("production_title") else ""
    return (f'<div class="cs-header">{title}<h2>{day_line}</h2>'
            f'{_fields_html(data, cfg, "header")}{_key_crew_html(data, cfg)}</div>')


def _render_day_info(data, cfg, ctx):
    return f'<div class="cs-day-info">{_fields_html(data, cfg, "day_info")}</div>'


def _render_locations(data, cfg, ctx):
    locs = sorted(data.get("locations", []),
                  key=lambda r: (not r.get("is_primary"), r.get("sort_order", 0)))
    return "".join(
        f'<div class="cs-location"><strong>{esc((l.get("location") or {}).get("name"))}</strong>'
        f'{" (Primary)" if l.get("is_primary") else ""}<br>'
        f'{esc((l.get("location") or {}).get("address") or "")}<br>'
        f'Parking: {esc((l.get("location") or {}).get("parking_notes") or "-")}</div>'
        for l in locs)


def _render_scenes(data, cfg, ctx):
    cols = cfg.get("scene_columns", [])
    extras = data.get("scene_extras") or {}
    head = "<th>Sc</th><th>I/E</th><th>Set</th><th>D/N</th><th>Pgs</th>" + \
        "".join(f'<th>{esc(c["label"])}</th>' for c in cols)
    body = ""
    for s in data.get("scenes", []):
        ex = extras.get(s.get("id")) or {}
        body += (f'<tr><td>{esc(s.get("scene_number"))}</td><td>{esc(s.get("int_ext"))}</td>'
                 f'<td>{esc(s.get("setting") or s.get("location_canonical"))}</td>'
                 f'<td>{esc(s.get("time_of_day"))}</td>'
                 f'<td>{esc(s.get("page_length_eighths", 8))}/8</td>'
                 + "".join(f'<td>{_cell(c, ex.get(c["key"]))}</td>' for c in cols) + "</tr>")
    return f'<table class="report-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _render_cast(data, cfg, ctx):
    main, _ = split_cast(data, cfg)
    return _cast_table(main, cfg)


def _render_crew(data, cfg, ctx):
    cols = cfg.get("crew_columns", [])
    dept_order = [d["code"] for d in department_service.get_departments_list()]
    by_dept = {}
    for row in data.get("crew", []):
        by_dept.setdefault((row.get("crew") or {}).get("department_code"), []).append(row)
    head = "<th>Name</th><th>Role</th><th>Call</th>" + \
        "".join(f'<th>{esc(c["label"])}</th>' for c in cols)
    sections = []
    for code in dept_order + [c for c in by_dept if c not in dept_order]:
        rows = by_dept.get(code)
        if not rows:
            continue
        label = department_service.get_department_name(code) if code else "Other"
        body = "".join(
            f'<tr><td>{esc(((r.get("crew") or {}).get("contact") or {}).get("name"))}</td>'
            f'<td>{esc((r.get("crew") or {}).get("role") or "")}</td>'
            f'<td>{esc(r.get("call_time") or "")}</td>'
            + "".join(f'<td>{_cell(c, (r.get("extra") or {}).get(c["key"]))}</td>' for c in cols)
            + "</tr>" for r in rows)
        sections.append(f'<h4>{esc(label)}</h4><table class="report-table">'
                        f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')
    return "".join(sections)


def _render_notes(data, cfg, ctx):
    overrides = data.get("block_overrides") or {}
    blocks = ""
    for block in cfg.get("blocks", []):
        body = overrides.get(block["key"], block.get("body", ""))
        if body and body.strip():
            blocks += (f'<div class="cs-block"><strong>{esc(block["label"])}</strong>'
                       f'<div style="white-space: pre-wrap">{esc(body)}</div></div>')
    return _fields_html(data, cfg, "notes") + blocks


SECTION_RENDERERS = {
    "header": _render_header,
    "day_info": _render_day_info,
    "locations": _render_locations,
    "scenes": _render_scenes,
    "cast": _render_cast,
    "crew": _render_crew,
    "notes": _render_notes,
}


def render_html(data, ctx):
    cfg = data.get("template") or default_config()
    day = ctx.get("day") or {}
    banner = '<div class="cs-draft-banner">DRAFT</div>' if data.get("status", "draft") == "draft" else ""
    running = (f'<div class="cs-running">{esc(ctx.get("production_title") or "")} &middot; '
               f'Day {esc(day.get("day_number"))} &middot; {esc(day.get("shoot_date") or "")}</div>')
    body = []
    for section in cfg["sections"]:
        if not section.get("visible", True):
            continue
        renderer = SECTION_RENDERERS.get(section["key"])
        if renderer is None:
            continue
        inner = renderer(data, cfg, ctx)
        if inner is None:
            continue
        heading = "" if section["key"] == "header" else f'<h3>{esc(section["label"])}</h3>'
        body.append(f'<section class="cs-section cs-section-{section["key"]}">{heading}{inner}</section>')
    return (f"<html><head><style>{CSS_EXTRA}</style></head><body>"
            f"{running}{banner}{''.join(body)}</body></html>")
```

- [ ] **Step 4: Wire the service to the renderer**

In `call_sheet_service.py`: add `from services import call_sheet_render as render`, delete `_esc` and `_render_pdf_html`, and replace `render_call_sheet_pdf` with:

```python
def _render_context(supabase, data, day):
    prod = (supabase.table("productions").select("title")
            .eq("id", data["production_id"]).limit(1).execute().data or [])
    days = (supabase.table("shooting_days").select("*")
            .eq("schedule_id", day.get("schedule_id")).execute().data or []) if day else []
    return {
        "day": day,
        "production_title": prod[0].get("title") if prod else None,
        "days_total": len(days) or None,
        "advanced": None,
    }


def build_call_sheet_html(call_sheet_id, can_view_sensitive=False):
    supabase = get_supabase_admin()
    data = get_call_sheet(call_sheet_id)
    if data is NOT_FOUND:
        return NOT_FOUND
    data = redact_roster(data, can_view_sensitive)
    day_res = (supabase.table("shooting_days").select("*")
               .eq("id", data["shooting_day_id"]).limit(1).execute())
    day = day_res.data[0] if day_res.data else {}
    return render.render_html(data, _render_context(supabase, data, day))


def render_call_sheet_pdf(call_sheet_id, can_view_sensitive=False):
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("weasyprint is not installed")
    html_content = build_call_sheet_html(call_sheet_id, can_view_sensitive)
    if html_content is NOT_FOUND:
        return NOT_FOUND
    css = report_service._get_report_css()
    from weasyprint import CSS
    return HTML(string=html_content).write_pdf(stylesheets=[CSS(string=css)])
```

- [ ] **Step 5: Run to verify everything passes (incl. the v1 PDF smoke tests)**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_render.py tests/test_call_sheet_customization_service.py tests/test_call_sheet_service.py tests/test_call_sheet_customization_routes.py -v`
Expected: PASS (all; `test_render_call_sheet_pdf_returns_pdf_bytes` still yields `%PDF` bytes).

- [ ] **Step 6: Commit**

```bash
git add backend/services/call_sheet_render.py backend/services/call_sheet_service.py backend/tests/test_call_sheet_render.py backend/tests/test_call_sheet_customization_service.py
git commit -m "$(cat <<'EOF'
feat(call-sheets): config-driven PDF renderer for core sections

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Renderer — extras, department calls, catering, advanced schedule

**Files:**
- Modify: `backend/services/call_sheet_render.py` (four renderers + registry)
- Modify: `backend/services/call_sheet_service.py` (`_render_context` computes `advanced`)
- Test: `backend/tests/test_call_sheet_render.py` (append), `backend/tests/test_call_sheet_customization_service.py` (append)

**Interfaces:**
- Consumes: `split_cast`, `_cast_table`, `values.catering_defaults/effective_catering` (already imported), `ctx["advanced"]`.
- Produces: renderers for `extras`, `dept_calls`, `catering`, `advanced` registered in `SECTION_RENDERERS`; `_render_context` sets `ctx["advanced"] = {"day", "scenes"}` for the next-higher `day_number` in the same schedule, or `None` when there is no next day or it has no scenes.

- [ ] **Step 1: Write the failing tests (append to `test_call_sheet_render.py`)**

```python
def _enable(cfg, *keys):
    for s in cfg["sections"]:
        if s["key"] in keys:
            s["visible"] = True
    return cfg


def test_extras_section_lists_background_rows(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "extras")
    lead = {"call_time": "06:00", "extra": {}, "casting": {"character_name": "HERO", "actor_name": "Jo", "tier": "lead"}}
    bg = {"call_time": "07:00", "extra": {"pickup": "06:30"},
          "casting": {"character_name": "CROWD", "actor_name": "Extras Co", "tier": "background"}}
    html = _html(_data(cfg, cast=[lead, bg]))
    extras_part = html[html.index("Extras"):]
    assert "CROWD" in extras_part and "06:30" in extras_part
    cast_part = html[html.index("Cast Call List"):html.index("Extras")]
    assert "HERO" in cast_part and "CROWD" not in cast_part


def test_extras_section_omitted_when_no_background(monkeypatch):
    _patch_depts(monkeypatch)
    assert "Extras" not in _html(_data(_enable(full_config(), "extras")))


def test_dept_calls_use_default_then_override(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "dept_calls")
    html = _html(_data(cfg))
    assert "Wardrobe" in html and "06:00" in html and "Pippa" in html
    html = _html(_data(cfg, dept_overrides={"wardrobe": {"call": "07:15", "as_per": "Sam"}}))
    assert "07:15" in html and "Sam" in html and "Pippa" not in html


def test_dept_calls_omitted_when_none_configured(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(tpl.default_config(), "dept_calls")
    assert "Department Calls" not in _html(_data(cfg))


def test_catering_grid_uses_effective_counts_and_totals(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "catering")
    eff = {m: {"crew": 40, "cast": 10, "add_crew": 0, "extras": 1}
           for m in ("craft", "breakfast", "lunch", "dinner")}
    eff["dinner"] = {"crew": 0, "cast": 0, "add_crew": 0, "extras": 0}
    html = _html(_data(cfg, catering_effective=eff))
    assert "Catering" in html and "<td>40</td>" in html and "<td>51</td>" in html


def test_catering_falls_back_to_roster_counts(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "catering")
    html = _html(_data(cfg))       # 1 crew + 1 cast in _data()
    assert "Catering" in html and "<td>2</td>" in html


def test_catering_omitted_when_everything_is_zero(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "catering")
    assert "Catering" not in _html(_data(cfg, crew=[], cast=[]))


def test_advanced_schedule_renders_next_day_scenes(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "advanced")
    ctx = dict(CTX, advanced={
        "day": {"day_number": 4, "shoot_date": "2026-10-02"},
        "scenes": [{"id": "n1", "scene_number": "44", "int_ext": "EXT", "setting": "FARM",
                    "time_of_day": "NIGHT", "page_length_eighths": 5}]})
    html = _html(_data(cfg), ctx)
    assert "Advanced Schedule" in html and "Day 4" in html and "FARM" in html and "5/8" in html


def test_advanced_schedule_omitted_without_next_day(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "advanced")
    assert "Advanced Schedule" not in _html(_data(cfg), CTX)
```

Append to `test_call_sheet_customization_service.py`:

```python
def _multi_day_store(**overrides):
    return make_store(
        shooting_days=[
            {"id": "d1", "schedule_id": "sch1", "day_number": 1, "shoot_date": "2026-10-01"},
            {"id": "d2", "schedule_id": "sch1", "day_number": 2, "shoot_date": "2026-10-02"},
            {"id": "d3", "schedule_id": "sch1", "day_number": 3, "shoot_date": "2026-10-03"},
            {"id": "x9", "schedule_id": "other", "day_number": 2, "shoot_date": "2026-10-09"}],
        **overrides)


def test_render_context_finds_next_day_with_scenes(monkeypatch):
    store = _multi_day_store(
        scenes=[{"id": "sc2", "scene_number": "7"}],
        shooting_day_scenes=[{"shooting_day_id": "d2", "scene_id": "sc2", "sort_order": 0}])
    sb = patch_svc(monkeypatch, store)
    data = svc.get_call_sheet("cs1")
    day = store["shooting_days"][0]
    ctx = svc._render_context(sb, data, day)
    assert ctx["days_total"] == 3                      # other schedule's day excluded
    assert ctx["advanced"]["day"]["id"] == "d2"
    assert [s["id"] for s in ctx["advanced"]["scenes"]] == ["sc2"]


def test_render_context_advanced_none_when_next_day_has_no_scenes(monkeypatch):
    sb = patch_svc(monkeypatch, _multi_day_store())
    ctx = svc._render_context(sb, svc.get_call_sheet("cs1"), _multi_day_store()["shooting_days"][0])
    assert ctx["advanced"] is None


def test_render_context_advanced_none_on_last_day(monkeypatch):
    store = _multi_day_store(call_sheets=[sheet_row(shooting_day_id="d3")])
    sb = patch_svc(monkeypatch, store)
    ctx = svc._render_context(sb, svc.get_call_sheet("cs1"), store["shooting_days"][2])
    assert ctx["advanced"] is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_render.py tests/test_call_sheet_customization_service.py -k "extras or dept_calls or catering or advanced or render_context" -v`
Expected: FAIL (sections not rendered; `advanced` always `None`).

- [ ] **Step 3: Implement the renderers**

Add to `call_sheet_render.py` (above `SECTION_RENDERERS`) and register them:

```python
GROUP_LABELS = (("crew", "Crew"), ("cast", "Cast"), ("add_crew", "Add. crew"), ("extras", "Extras"))
MEAL_LABELS = (("craft", "Craft"), ("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner"))


def _render_extras(data, cfg, ctx):
    _, extras = split_cast(data, cfg)
    if not extras:
        return None
    return _cast_table(extras, cfg, first_labels=("Role", "Name", "Status", "Call Time"))


def _render_dept_calls(data, cfg, ctx):
    overrides = data.get("dept_overrides") or {}
    rows = ""
    for dept in cfg.get("departments", []):
        ov = overrides.get(dept["key"]) or {}
        call = ov.get("call") or dept.get("default_call") or ""
        as_per = ov.get("as_per") or dept.get("as_per") or ""
        if call or as_per:
            rows += f'<tr><td>{esc(dept["label"])}</td><td>{esc(call)}</td><td>{esc(as_per)}</td></tr>'
    if not rows:
        return None
    return ('<table class="report-table"><thead><tr><th>Department</th><th>Call</th>'
            f'<th>As per</th></tr></thead><tbody>{rows}</tbody></table>')


def _render_catering(data, cfg, ctx):
    eff = data.get("catering_effective") or values.effective_catering(
        values.catering_defaults(data.get("crew", []), data.get("cast", [])), data.get("catering"))
    totals = {m: sum(eff.get(m, {}).get(g, 0) for g, _ in GROUP_LABELS) for m, _ in MEAL_LABELS}
    if not any(totals.values()):
        return None
    head = "<th></th>" + "".join(f"<th>{label}</th>" for _, label in MEAL_LABELS)
    rows = "".join(
        f"<tr><td>{glabel}</td>"
        + "".join(f'<td>{esc(eff.get(m, {}).get(g, 0))}</td>' for m, _ in MEAL_LABELS) + "</tr>"
        for g, glabel in GROUP_LABELS)
    total_row = "<tr><td><strong>Total</strong></td>" + \
        "".join(f"<td>{esc(totals[m])}</td>" for m, _ in MEAL_LABELS) + "</tr>"
    return f'<table class="report-table"><thead><tr>{head}</tr></thead><tbody>{rows}{total_row}</tbody></table>'


def _render_advanced(data, cfg, ctx):
    adv = ctx.get("advanced")
    if not adv:
        return None
    day = adv["day"]
    caption = f'<p>Day {esc(day.get("day_number"))} &middot; {esc(day.get("shoot_date") or "")}</p>'
    rows = "".join(
        f'<tr><td>{esc(s.get("scene_number"))}</td><td>{esc(s.get("int_ext"))}</td>'
        f'<td>{esc(s.get("setting") or s.get("location_canonical"))}</td>'
        f'<td>{esc(s.get("time_of_day"))}</td><td>{esc(s.get("page_length_eighths", 8))}/8</td></tr>'
        for s in adv["scenes"])
    return (f'{caption}<table class="report-table"><thead><tr><th>Sc</th><th>I/E</th><th>Set</th>'
            f'<th>D/N</th><th>Pgs</th></tr></thead><tbody>{rows}</tbody></table>')
```

and extend the registry:

```python
SECTION_RENDERERS = {
    "header": _render_header,
    "day_info": _render_day_info,
    "locations": _render_locations,
    "scenes": _render_scenes,
    "cast": _render_cast,
    "extras": _render_extras,
    "crew": _render_crew,
    "dept_calls": _render_dept_calls,
    "catering": _render_catering,
    "notes": _render_notes,
    "advanced": _render_advanced,
}
```

- [ ] **Step 4: Compute `advanced` in the service**

Replace `_render_context` in `call_sheet_service.py`:

```python
def _render_context(supabase, data, day):
    prod = (supabase.table("productions").select("title")
            .eq("id", data["production_id"]).limit(1).execute().data or [])
    days = (supabase.table("shooting_days").select("*")
            .eq("schedule_id", day.get("schedule_id")).execute().data or []) if day else []
    current = (day or {}).get("day_number") or 0
    later = [d for d in days if (d.get("day_number") or 0) > current]
    advanced = None
    if later:
        nxt = min(later, key=lambda d: d["day_number"])
        scenes = get_day_scenes(supabase, nxt["id"])
        if scenes:
            advanced = {"day": nxt, "scenes": scenes}
    return {
        "day": day,
        "production_title": prod[0].get("title") if prod else None,
        "days_total": len(days) or None,
        "advanced": advanced,
    }
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_call_sheet_render.py tests/test_call_sheet_customization_service.py tests/test_call_sheet_service.py -v`
Expected: PASS (all).

- [ ] **Step 6: Visual check of a real PDF (skip if WeasyPrint is unavailable locally)**

Run from `backend/` (writes to the scratchpad, not the repo):

```bash
venv/bin/python - <<'EOF'
import sys; sys.path.insert(0, "tests")
import services.call_sheet_render as r, services.call_sheet_template_service as t
from call_sheet_customization_support import full_config
from weasyprint import HTML, CSS
from services.report_service import report_service
cfg = full_config()
for s in cfg["sections"]: s["visible"] = True
data = {"status": "draft", "template": cfg, "weather": "Sunny", "custom_values": {"wind": "SSW 15"},
        "locations": [], "scenes": [], "cast": [], "crew": []}
ctx = {"day": {"day_number": 3, "shoot_date": "2026-10-01"}, "production_title": "Farm Feature",
       "days_total": 12, "advanced": None}
out = "/private/tmp/claude-501/-Users-thecasterymedia-Desktop-PORTFOLIO-SaaS-ScripDown-AI/bbe6adf7-bf87-4f09-8361-767d1f2125ae/scratchpad/sample_call_sheet.pdf"
HTML(string=r.render_html(data, ctx)).write_pdf(out, stylesheets=[CSS(string=report_service._get_report_css())])
print(out)
EOF
```

Open the PDF with the Read tool and confirm: the running header appears at the top, the DRAFT banner shows, "Wind: SSW 15" is under Day Info, and the first page layout is not clipped by the added top margin. If the running header collides with content, raise `margin-top` in `CSS_EXTRA`.

- [ ] **Step 7: Commit**

```bash
git add backend/services/call_sheet_render.py backend/services/call_sheet_service.py backend/tests/test_call_sheet_render.py backend/tests/test_call_sheet_customization_service.py
git commit -m "$(cat <<'EOF'
feat(call-sheets): extras, department calls, catering and advanced schedule sections

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Frontend API functions + Members tab capability

**Files:**
- Modify: `frontend/src/services/apiService.js` (after `updateCallSheet`, ~line 2673)
- Modify: `frontend/src/components/productions/ProductionMembersTab.jsx:12-44`

**Interfaces:**
- Produces: `getCallSheetTemplate(productionId) -> {template: {config, updated_at, is_default, default_config}}`; `saveCallSheetTemplate(productionId, config, expectedUpdatedAt) -> {template}` (rejects with the axios error; `err.response.status` 400 → `err.response.data.details`, 409 → stale); capability label + role presets for `can_edit_call_sheet_template`.

- [ ] **Step 1: Add the API functions**

Insert after `updateCallSheet` in `apiService.js`:

```js
export const getCallSheetTemplate = async (productionId) => {
    try {
        const response = await api.get(`/api/productions/${productionId}/call-sheet-template`);
        return response.data;
    } catch (error) {
        console.error('Error getting call sheet template:', error);
        throw error;
    }
};

export const saveCallSheetTemplate = async (productionId, config, expectedUpdatedAt) => {
    try {
        const response = await api.put(`/api/productions/${productionId}/call-sheet-template`, {
            config,
            expected_updated_at: expectedUpdatedAt ?? null,
        });
        return response.data;
    } catch (error) {
        console.error('Error saving call sheet template:', error);
        throw error;
    }
};
```

- [ ] **Step 2: Update the Members tab**

In `ProductionMembersTab.jsx` add the label and the flag to all three presets:

```js
const CAP_LABELS = {
    can_view_sensitive: 'See rates & phone',
    can_edit_crew: 'Edit crew',
    can_manage_members: 'Manage members',
    can_edit_production: 'Edit production',
    can_edit_call_sheets: 'Edit call sheets',
    can_edit_call_sheet_template: 'Edit call sheet template',
};
```

and inside `PRESETS` add `can_edit_call_sheet_template: true` to `admin` and `coordinator`, `can_edit_call_sheet_template: false` to `viewer` (next to each `can_edit_call_sheets` line).

- [ ] **Step 3: Confirm the checkbox list is driven by `CAP_LABELS`**

Run: `cd frontend && grep -n "CAP_LABELS" src/components/productions/ProductionMembersTab.jsx`
Expected: a `Object.entries(CAP_LABELS)` (or equivalent) map that renders the per-member checkboxes, so the new key appears with no further UI change. If a checkbox list is hand-written instead, add one for `can_edit_call_sheet_template` next to `can_edit_call_sheets`.

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/apiService.js frontend/src/components/productions/ProductionMembersTab.jsx
git commit -m "$(cat <<'EOF'
feat(call-sheets): template API client and members-tab capability

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Template editor — "Call Sheet" tab on the production page

**Files:**
- Create: `frontend/src/components/productions/callSheetTemplate/templateUtils.js`
- Create: `frontend/src/components/productions/callSheetTemplate/SectionsPanel.jsx`
- Create: `frontend/src/components/productions/callSheetTemplate/FieldListPanel.jsx`
- Create: `frontend/src/components/productions/callSheetTemplate/DepartmentsPanel.jsx`
- Create: `frontend/src/components/productions/callSheetTemplate/KeyValueListPanel.jsx`
- Create: `frontend/src/components/productions/ProductionCallSheetTab.jsx`
- Create: `frontend/src/components/productions/ProductionCallSheetTab.css`
- Modify: `frontend/src/pages/ProductionDetailPage.jsx` (imports, tab list, tab guard, tab render)

**Interfaces:**
- Consumes: `getCallSheetTemplate`, `saveCallSheetTemplate` (Task 10); `useToast()` (`toast.success|error|warning(title, message)`); `access` prop (`role`, `can_edit_call_sheet_template`).
- Produces: pure helpers `slugKey(label, existingKeys)`, `moveItem(list, index, delta)`, `updateAt(list, index, patch)`, `removeAt(list, index)`, `errorsFor(errors, prefix)`, `panelErrors(errors, path)`, `blankDayField(items)`, `blankColumn(items)`, `blankDepartment(items)`, `blankLabelled(items, valueField)`; panels take `{items|sections, onChange, canEdit, errors, errorPrefix}`.

- [ ] **Step 1: Pure helpers**

```js
// frontend/src/components/productions/callSheetTemplate/templateUtils.js
export const FIELD_TYPES = ['text', 'textarea', 'time', 'link', 'number'];
export const DAY_FIELD_SECTIONS = [['header', 'Header'], ['day_info', 'Day info'], ['notes', 'Notes']];

/** Keys are immutable and generated once: lowercase slug, unique within the list (max 40 chars). */
export function slugKey(label, existingKeys = []) {
    let base = String(label || '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    if (!base) base = 'field';
    if (!/^[a-z]/.test(base)) base = `f_${base}`;
    base = base.slice(0, 36);
    let key = base;
    let n = 2;
    while (existingKeys.includes(key)) {
        key = `${base}_${n}`;
        n += 1;
    }
    return key;
}

export function moveItem(list, index, delta) {
    const target = index + delta;
    if (target < 0 || target >= list.length) return list;
    const next = [...list];
    [next[index], next[target]] = [next[target], next[index]];
    return next;
}

export const updateAt = (list, index, patch) =>
    list.map((item, i) => (i === index ? { ...item, ...patch } : item));

export const removeAt = (list, index) => list.filter((_, i) => i !== index);

/** Messages for errors at or under `prefix` (e.g. `day_fields[3]` matches `day_fields[3].key`). */
export function errorsFor(errors, prefix) {
    return (errors || [])
        .filter((e) => e.path === prefix || e.path.startsWith(`${prefix}.`) || e.path.startsWith(`${prefix}[`))
        .map((e) => e.message);
}

/** Messages attached exactly to `path` (list-level errors such as "built-in fields cannot be removed"). */
export const panelErrors = (errors, path) =>
    (errors || []).filter((e) => e.path === path).map((e) => e.message);

const keysOf = (items) => items.map((i) => i.key);

export const blankDayField = (items) => ({
    key: slugKey('New field', keysOf(items)), label: 'New field', type: 'text',
    section: 'day_info', default: '', sensitive: false, visible: true, builtin: false,
});

export const blankColumn = (items) => ({
    key: slugKey('New column', keysOf(items)), label: 'New column', type: 'text', sensitive: false,
});

export const blankDepartment = (items) => ({
    key: slugKey('New department', keysOf(items)), label: 'New department', default_call: '', as_per: '',
});

export const blankLabelled = (items, valueField) => ({
    key: slugKey('New entry', keysOf(items)), label: 'New entry', [valueField]: '',
});
```

- [ ] **Step 2: Verify the helpers with a throwaway node check**

Run from `frontend/`:

```bash
node --input-type=module -e "
import assert from 'node:assert/strict';
import { slugKey, moveItem, updateAt, removeAt, errorsFor, panelErrors } from './src/components/productions/callSheetTemplate/templateUtils.js';
assert.equal(slugKey('Wind Speed!', []), 'wind_speed');
assert.equal(slugKey('9 lives', []), 'f_9_lives');
assert.equal(slugKey('', []), 'field');
assert.equal(slugKey('Wind', ['wind']), 'wind_2');
assert.ok(slugKey('x'.repeat(80), ['x'.repeat(36)]).length <= 40);
assert.deepEqual(moveItem([1, 2, 3], 0, 1), [2, 1, 3]);
assert.deepEqual(moveItem([1, 2, 3], 0, -1), [1, 2, 3]);
assert.deepEqual(updateAt([{ a: 1 }, { a: 2 }], 1, { a: 9 }), [{ a: 1 }, { a: 9 }]);
assert.deepEqual(removeAt([1, 2, 3], 1), [1, 3]);
const errs = [{ path: 'day_fields[3].key', message: 'dup' }, { path: 'day_fields', message: 'missing' }, { path: 'day_fields[33].key', message: 'other' }];
assert.deepEqual(errorsFor(errs, 'day_fields[3]'), ['dup']);
assert.deepEqual(panelErrors(errs, 'day_fields'), ['missing']);
console.log('templateUtils ok');
"
```

Expected: `templateUtils ok`.

- [ ] **Step 3: Sections panel**

```jsx
// frontend/src/components/productions/callSheetTemplate/SectionsPanel.jsx
import { ArrowUp, ArrowDown } from 'lucide-react';
import { moveItem, updateAt, errorsFor, panelErrors } from './templateUtils';

export default function SectionsPanel({ sections, onChange, canEdit, errors }) {
    return (
        <section className="cst-panel">
            <div className="cst-panel-head">
                <h4>Sections</h4>
                <span className="cst-hint">Show, hide, rename and reorder the parts of each call sheet.</span>
            </div>
            {panelErrors(errors, 'sections').map((m) => <div key={m} className="cst-error">{m}</div>)}
            {sections.map((s, i) => (
                <div key={s.key} className="cst-row">
                    <label className="cst-check">
                        <input type="checkbox" checked={s.visible} disabled={!canEdit}
                               onChange={(e) => onChange(updateAt(sections, i, { visible: e.target.checked }))} />
                        Show
                    </label>
                    <input aria-label="Section label" value={s.label} disabled={!canEdit}
                           onChange={(e) => onChange(updateAt(sections, i, { label: e.target.value }))} />
                    <span className="cst-key">{s.key}</span>
                    {canEdit && (
                        <span className="cst-actions">
                            <button type="button" aria-label="Move up" onClick={() => onChange(moveItem(sections, i, -1))}><ArrowUp size={14} /></button>
                            <button type="button" aria-label="Move down" onClick={() => onChange(moveItem(sections, i, 1))}><ArrowDown size={14} /></button>
                        </span>
                    )}
                    {errorsFor(errors, `sections[${i}]`).map((m) => <div key={m} className="cst-error">{m}</div>)}
                </div>
            ))}
        </section>
    );
}
```

- [ ] **Step 4: Field/column list panel (used for day fields and the three column lists)**

```jsx
// frontend/src/components/productions/callSheetTemplate/FieldListPanel.jsx
import { ArrowUp, ArrowDown, Trash2, Lock, Plus } from 'lucide-react';
import {
    FIELD_TYPES, DAY_FIELD_SECTIONS, moveItem, updateAt, removeAt,
    errorsFor, panelErrors, blankDayField, blankColumn,
} from './templateUtils';

/** mode 'day': built-in-aware day-info fields. mode 'column': table columns. */
export default function FieldListPanel({ title, hint, items, onChange, mode, canEdit, errors, errorPrefix }) {
    const isDay = mode === 'day';
    const set = (i, patch) => onChange(updateAt(items, i, patch));
    return (
        <section className="cst-panel">
            <div className="cst-panel-head">
                <h4>{title}</h4>
                {hint && <span className="cst-hint">{hint}</span>}
            </div>
            {panelErrors(errors, errorPrefix).map((m) => <div key={m} className="cst-error">{m}</div>)}
            {items.map((item, i) => (
                <div key={item.key} className="cst-row">
                    {item.builtin && <Lock size={12} title="Built-in field: can be hidden or renamed, not removed" />}
                    <input aria-label="Label" value={item.label} disabled={!canEdit}
                           onChange={(e) => set(i, { label: e.target.value })} />
                    <select aria-label="Type" value={item.type} disabled={!canEdit || item.builtin}
                            onChange={(e) => set(i, { type: e.target.value })}>
                        {FIELD_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                    {isDay && (
                        <select aria-label="Section" value={item.section} disabled={!canEdit}
                                onChange={(e) => set(i, { section: e.target.value })}>
                            {DAY_FIELD_SECTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                        </select>
                    )}
                    {isDay && (
                        <input aria-label="Default value" placeholder="Default" value={item.default} disabled={!canEdit}
                               onChange={(e) => set(i, { default: e.target.value })} />
                    )}
                    <label className="cst-check">
                        <input type="checkbox" checked={item.sensitive} disabled={!canEdit}
                               onChange={(e) => set(i, { sensitive: e.target.checked })} />
                        Sensitive
                    </label>
                    {isDay && (
                        <label className="cst-check">
                            <input type="checkbox" checked={item.visible} disabled={!canEdit}
                                   onChange={(e) => set(i, { visible: e.target.checked })} />
                            Show
                        </label>
                    )}
                    {canEdit && (
                        <span className="cst-actions">
                            <button type="button" aria-label="Move up" onClick={() => onChange(moveItem(items, i, -1))}><ArrowUp size={14} /></button>
                            <button type="button" aria-label="Move down" onClick={() => onChange(moveItem(items, i, 1))}><ArrowDown size={14} /></button>
                            <button type="button" aria-label="Remove" disabled={item.builtin}
                                    onClick={() => onChange(removeAt(items, i))}><Trash2 size={14} /></button>
                        </span>
                    )}
                    {errorsFor(errors, `${errorPrefix}[${i}]`).map((m) => <div key={m} className="cst-error">{m}</div>)}
                </div>
            ))}
            {canEdit && (
                <button type="button" className="cst-add"
                        onClick={() => onChange([...items, isDay ? blankDayField(items) : blankColumn(items)])}>
                    <Plus size={14} /> Add {isDay ? 'field' : 'column'}
                </button>
            )}
        </section>
    );
}
```

- [ ] **Step 5: Departments panel and key/value list panel**

```jsx
// frontend/src/components/productions/callSheetTemplate/DepartmentsPanel.jsx
import { ArrowUp, ArrowDown, Trash2, Plus } from 'lucide-react';
import { moveItem, updateAt, removeAt, errorsFor, panelErrors, blankDepartment } from './templateUtils';

export default function DepartmentsPanel({ items, onChange, canEdit, errors }) {
    const set = (i, patch) => onChange(updateAt(items, i, patch));
    return (
        <section className="cst-panel">
            <div className="cst-panel-head">
                <h4>Department calls</h4>
                <span className="cst-hint">Default call time and &ldquo;As per&rdquo; contact per department. Each day can override.</span>
            </div>
            {panelErrors(errors, 'departments').map((m) => <div key={m} className="cst-error">{m}</div>)}
            {items.map((d, i) => (
                <div key={d.key} className="cst-row">
                    <input aria-label="Department" value={d.label} disabled={!canEdit}
                           onChange={(e) => set(i, { label: e.target.value })} />
                    <input aria-label="Default call" type="time" value={d.default_call} disabled={!canEdit}
                           onChange={(e) => set(i, { default_call: e.target.value })} />
                    <input aria-label="As per" placeholder="As per…" value={d.as_per} disabled={!canEdit}
                           onChange={(e) => set(i, { as_per: e.target.value })} />
                    {canEdit && (
                        <span className="cst-actions">
                            <button type="button" aria-label="Move up" onClick={() => onChange(moveItem(items, i, -1))}><ArrowUp size={14} /></button>
                            <button type="button" aria-label="Move down" onClick={() => onChange(moveItem(items, i, 1))}><ArrowDown size={14} /></button>
                            <button type="button" aria-label="Remove" onClick={() => onChange(removeAt(items, i))}><Trash2 size={14} /></button>
                        </span>
                    )}
                    {errorsFor(errors, `departments[${i}]`).map((m) => <div key={m} className="cst-error">{m}</div>)}
                </div>
            ))}
            {canEdit && (
                <button type="button" className="cst-add" onClick={() => onChange([...items, blankDepartment(items)])}>
                    <Plus size={14} /> Add department
                </button>
            )}
        </section>
    );
}
```

```jsx
// frontend/src/components/productions/callSheetTemplate/KeyValueListPanel.jsx
import { ArrowUp, ArrowDown, Trash2, Plus } from 'lucide-react';
import { moveItem, updateAt, removeAt, errorsFor, panelErrors, blankLabelled } from './templateUtils';

/** Label + one value: used for boilerplate blocks (body, multiline) and key crew (value, single line). */
export default function KeyValueListPanel({
    title, hint, items, onChange, valueField, multiline, canEdit, errors, errorPrefix, addLabel,
}) {
    const set = (i, patch) => onChange(updateAt(items, i, patch));
    return (
        <section className="cst-panel">
            <div className="cst-panel-head">
                <h4>{title}</h4>
                {hint && <span className="cst-hint">{hint}</span>}
            </div>
            {panelErrors(errors, errorPrefix).map((m) => <div key={m} className="cst-error">{m}</div>)}
            {items.map((item, i) => (
                <div key={item.key} className="cst-row">
                    <input aria-label="Label" value={item.label} disabled={!canEdit}
                           onChange={(e) => set(i, { label: e.target.value })} />
                    {multiline ? (
                        <textarea aria-label="Text" rows={3} value={item[valueField]} disabled={!canEdit}
                                  onChange={(e) => set(i, { [valueField]: e.target.value })} />
                    ) : (
                        <input aria-label="Value" value={item[valueField]} disabled={!canEdit}
                               onChange={(e) => set(i, { [valueField]: e.target.value })} />
                    )}
                    {canEdit && (
                        <span className="cst-actions">
                            <button type="button" aria-label="Move up" onClick={() => onChange(moveItem(items, i, -1))}><ArrowUp size={14} /></button>
                            <button type="button" aria-label="Move down" onClick={() => onChange(moveItem(items, i, 1))}><ArrowDown size={14} /></button>
                            <button type="button" aria-label="Remove" onClick={() => onChange(removeAt(items, i))}><Trash2 size={14} /></button>
                        </span>
                    )}
                    {errorsFor(errors, `${errorPrefix}[${i}]`).map((m) => <div key={m} className="cst-error">{m}</div>)}
                </div>
            ))}
            {canEdit && (
                <button type="button" className="cst-add"
                        onClick={() => onChange([...items, blankLabelled(items, valueField)])}>
                    <Plus size={14} /> {addLabel}
                </button>
            )}
        </section>
    );
}
```

- [ ] **Step 6: The tab (load / dirty / save / reset / 400 / 409)**

```jsx
// frontend/src/components/productions/ProductionCallSheetTab.jsx
import { useState, useEffect, useCallback, useMemo } from 'react';
import { getCallSheetTemplate, saveCallSheetTemplate } from '../../services/apiService';
import { Spinner } from '../ui';
import { useToast } from '../../context/ToastContext';
import SectionsPanel from './callSheetTemplate/SectionsPanel';
import FieldListPanel from './callSheetTemplate/FieldListPanel';
import DepartmentsPanel from './callSheetTemplate/DepartmentsPanel';
import KeyValueListPanel from './callSheetTemplate/KeyValueListPanel';
import './ProductionCallSheetTab.css';

export default function ProductionCallSheetTab({ productionId, access }) {
    const toast = useToast();
    const canEdit = access.role === 'owner' || !!access.can_edit_call_sheet_template;
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(null);
    const [saved, setSaved] = useState(null);   // { config, updated_at, is_default, default_config }
    const [draft, setDraft] = useState(null);
    const [saving, setSaving] = useState(false);
    const [errors, setErrors] = useState([]);

    const load = useCallback(async () => {
        setLoading(true);
        setLoadError(null);
        try {
            const { template } = await getCallSheetTemplate(productionId);
            setSaved(template);
            setDraft(template.config);
            setErrors([]);
        } catch (err) {
            console.error('Failed to load call sheet template:', err);
            setLoadError('Could not load the call sheet template.');
        } finally {
            setLoading(false);
        }
    }, [productionId]);

    useEffect(() => { load(); }, [load]);

    const dirty = useMemo(
        () => !!draft && !!saved && JSON.stringify(draft) !== JSON.stringify(saved.config),
        [draft, saved],
    );

    const part = (name) => (value) => setDraft((d) => ({ ...d, [name]: value }));

    const save = async () => {
        setSaving(true);
        setErrors([]);
        try {
            const res = await saveCallSheetTemplate(productionId, draft, saved.updated_at);
            setSaved({ ...saved, ...res.template });
            setDraft(res.template.config);
            toast.success('Template saved', 'New call sheets and PDFs will use it.');
        } catch (err) {
            const status = err.response?.status;
            if (status === 400) {
                setErrors(err.response.data.details || []);
                toast.error('Fix the highlighted fields', 'The template was not saved.');
            } else if (status === 409) {
                toast.warning('Template changed', 'Someone else saved a newer version. Reloading it now.');
                await load();
            } else {
                toast.error('Save failed', 'Could not save the template.');
            }
        } finally {
            setSaving(false);
        }
    };

    const resetToDefault = () => {
        if (saved?.default_config) {
            setDraft(saved.default_config);
            setErrors([]);
        }
    };

    if (loading) return <Spinner />;
    if (loadError || !draft) return <p className="cst-error">{loadError || 'No template.'}</p>;

    return (
        <div className="cst-tab">
            <div className="cst-toolbar">
                <p className="cst-intro">
                    This template controls what every call sheet and PDF for this production contains.
                    {saved.is_default && ' Using the standard layout; save to customize.'}
                </p>
                {canEdit ? (
                    <div className="cst-toolbar-actions">
                        {dirty && <span className="cst-dirty">Unsaved changes</span>}
                        <button type="button" onClick={resetToDefault} disabled={saving}>Reset to default</button>
                        <button type="button" className="cst-primary" onClick={save} disabled={saving || !dirty}>
                            {saving ? 'Saving…' : 'Save template'}
                        </button>
                    </div>
                ) : (
                    <span className="cst-hint">Read-only: you don&rsquo;t have permission to edit the template.</span>
                )}
            </div>

            <SectionsPanel sections={draft.sections} onChange={part('sections')} canEdit={canEdit} errors={errors} />
            <FieldListPanel title="Day fields" hint="Built-ins can be hidden or renamed. Add your own (wind, base camp, wrap…)."
                            items={draft.day_fields} onChange={part('day_fields')} mode="day" canEdit={canEdit}
                            errors={errors} errorPrefix="day_fields" />
            <KeyValueListPanel title="Key crew (header)" hint="Producer, director, DoP… shown in the header block."
                               items={draft.key_crew} onChange={part('key_crew')} valueField="value"
                               canEdit={canEdit} errors={errors} errorPrefix="key_crew" addLabel="Add person" />
            <FieldListPanel title="Cast columns" hint="Extra columns on the cast table (P/U, costume, M-UP&H, mic'ing…)."
                            items={draft.cast_columns} onChange={part('cast_columns')} mode="column" canEdit={canEdit}
                            errors={errors} errorPrefix="cast_columns" />
            <FieldListPanel title="Crew columns" hint="Extra columns on the crew table."
                            items={draft.crew_columns} onChange={part('crew_columns')} mode="column" canEdit={canEdit}
                            errors={errors} errorPrefix="crew_columns" />
            <FieldListPanel title="Scene columns" hint="Extra columns on the scene table (story day, story time, BG…)."
                            items={draft.scene_columns} onChange={part('scene_columns')} mode="column" canEdit={canEdit}
                            errors={errors} errorPrefix="scene_columns" />
            <DepartmentsPanel items={draft.departments} onChange={part('departments')} canEdit={canEdit} errors={errors} />
            <KeyValueListPanel title="Boilerplate blocks" hint="Standing notices (safety, no-photos, water bottles…). Each day can override."
                               items={draft.blocks} onChange={part('blocks')} valueField="body" multiline
                               canEdit={canEdit} errors={errors} errorPrefix="blocks" addLabel="Add block" />
        </div>
    );
}
```

- [ ] **Step 7: Styles (match the production pages' hard-coded dark palette)**

```css
/* frontend/src/components/productions/ProductionCallSheetTab.css */
.cst-tab { display: flex; flex-direction: column; gap: 16px; padding-top: 16px; color: #e6ecf5; }
.cst-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.cst-intro { margin: 0; color: #9fb0c9; font-size: 14px; }
.cst-toolbar-actions { display: flex; align-items: center; gap: 8px; }
.cst-toolbar button, .cst-add {
    background: #26324a; color: #e6ecf5; border: none; border-radius: 6px;
    padding: 6px 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;
}
.cst-toolbar button:hover, .cst-add:hover { background: #33415a; }
.cst-toolbar button:disabled { opacity: 0.5; cursor: default; }
.cst-primary { background: #f5b301 !important; color: #1a1300 !important; font-weight: 600; }
.cst-dirty { color: #f5b301; font-size: 13px; }
.cst-panel { background: #182135; border: 1px solid #26324a; border-radius: 8px; padding: 12px 14px; }
.cst-panel-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
.cst-panel-head h4 { margin: 0; font-size: 14px; }
.cst-hint { color: #6b7a94; font-size: 12px; }
.cst-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 4px 0; }
.cst-row input:not([type="checkbox"]), .cst-row select, .cst-row textarea {
    background: #0f1729; color: #e6ecf5; border: 1px solid #26324a; border-radius: 6px;
    padding: 5px 8px; font-size: 13px; font-family: inherit;
}
.cst-row input:not([type="checkbox"]) { flex: 1 1 140px; min-width: 0; }
.cst-row textarea { flex: 2 1 260px; }
.cst-row input:disabled, .cst-row select:disabled, .cst-row textarea:disabled { opacity: 0.6; }
.cst-check { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: #9fb0c9; }
.cst-key { color: #6b7a94; font-size: 11px; font-family: monospace; }
.cst-actions { display: inline-flex; gap: 4px; }
.cst-actions button {
    background: none; border: 1px solid #26324a; color: #9fb0c9; border-radius: 6px;
    padding: 4px; cursor: pointer; display: inline-flex;
}
.cst-actions button:hover:not(:disabled) { color: #e6ecf5; border-color: #33415a; }
.cst-actions button:disabled { opacity: 0.35; cursor: default; }
.cst-add { margin-top: 8px; }
.cst-error { flex-basis: 100%; color: #f87171; font-size: 12px; }
```

- [ ] **Step 8: Wire the tab into `ProductionDetailPage.jsx`**

Add the import next to the other tab imports:

```jsx
import ProductionCallSheetTab from '../components/productions/ProductionCallSheetTab';
```

In the effect that resets disallowed tabs (lines ~62-65) add:

```jsx
        if (activeTab === 'callsheet' && !isMember) setActiveTab('overview');
```

In the tab list (after the Locations push, ~line 118) add:

```jsx
    if (isMember) tabs.push({ id: 'callsheet', label: 'Call Sheet' });
```

and render it beside the other tab bodies (before the Members block, ~line 161):

```jsx
            {activeTab === 'callsheet' && isMember && (
                <ProductionCallSheetTab productionId={productionId} access={access} />
            )}
```

Also add `can_edit_call_sheet_template: false` to the `NO_ACCESS` object (line ~15) for shape consistency.

- [ ] **Step 9: Build and manual check**

Run: `cd frontend && npm run build`
Expected: build succeeds.

Manual (dev servers: `python app.py` in `backend/`, `npm run dev` in `frontend/`, with `FLASK_ENV=development`): open a production → "Call Sheet" tab. Verify: default sections and built-in fields appear with lock icons; adding a field + Save shows "Template saved" and persists after reload; deleting a built-in is impossible (button disabled); an invalid edit (blank label) shows an inline error on that row; a read-only member sees disabled inputs and no Save.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/productions/callSheetTemplate frontend/src/components/productions/ProductionCallSheetTab.jsx frontend/src/components/productions/ProductionCallSheetTab.css frontend/src/pages/ProductionDetailPage.jsx
git commit -m "$(cat <<'EOF'
feat(call-sheets): per-production call sheet template editor tab

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Template-driven per-day `CallSheetEditor`

**Files:**
- Create: `frontend/src/components/schedule/CallSheetPanels.jsx`
- Modify (full rewrite): `frontend/src/components/schedule/CallSheetEditor.jsx`
- Modify: `frontend/src/components/schedule/CallSheetEditor.css` (append)

**Interfaces:**
- Consumes: `getCallSheet`/`getCallSheetByDay` responses from the backend (Tasks 5–7): `callSheet.template` (config), `callSheet.custom_values`, `dept_overrides`, `scene_extras`, `header_values`, `block_overrides`, `catering_effective`, `can_view_sensitive`, roster rows with `extra`; `updateCallSheet` response `{call_sheet, ignored_keys}`; `updateCallSheetCrew|Cast(callSheetId, id, {call_time?, extra?})`.
- Produces (from `CallSheetPanels.jsx`): `TypedInput`, `DayFieldsPanel`, `KeyCrewPanel`, `BlocksPanel`, `DeptCallsPanel`, `CateringPanel`, `ColumnInputs`. Each takes an `onPatch(payload, {reload?})` or `onCommit` callback; empty input → `null` (which clears the stored key server-side).

- [ ] **Step 1: Write the panels**

```jsx
// frontend/src/components/schedule/CallSheetPanels.jsx
const MEALS = [['craft', 'Craft'], ['breakfast', 'Breakfast'], ['lunch', 'Lunch'], ['dinner', 'Dinner']];
const GROUPS = [['crew', 'Crew'], ['cast', 'Cast'], ['add_crew', 'Add. crew'], ['extras', 'Extras']];

const toNull = (raw) => (raw === '' ? null : raw);

/** Uncontrolled input that commits on blur, only when the value actually changed. */
export function TypedInput({ type, value, onCommit, disabled, placeholder }) {
    const initial = value ?? '';
    const commit = (e) => {
        if (e.target.value !== String(initial)) onCommit(e.target.value);
    };
    if (type === 'textarea') {
        return <textarea defaultValue={initial} disabled={disabled} placeholder={placeholder} onBlur={commit} />;
    }
    const inputType = type === 'time' ? 'time' : type === 'number' ? 'number' : 'text';
    return <input type={inputType} defaultValue={initial} disabled={disabled} placeholder={placeholder} onBlur={commit} />;
}

/** Day-info fields for one template section (header | day_info | notes). */
export function DayFieldsPanel({ callSheet, section, onPatch }) {
    const canSee = !!callSheet.can_view_sensitive;
    const fields = callSheet.template.day_fields.filter(
        (f) => f.section === section && f.visible && (canSee || !f.sensitive));
    const valueOf = (f) => (f.builtin ? callSheet[f.key] : (callSheet.custom_values || {})[f.key]);
    const commit = (f, raw) => {
        const value = toNull(raw);
        onPatch(f.builtin ? { [f.key]: value } : { custom_values: { [f.key]: value } });
    };
    return fields.map((f) => (
        <label key={`${f.key}:${valueOf(f) ?? ''}`} className="cs-field">
            <span>{f.label}</span>
            <TypedInput type={f.type} value={valueOf(f) ?? f.default ?? ''} onCommit={(raw) => commit(f, raw)} />
        </label>
    ));
}

export function KeyCrewPanel({ callSheet, onPatch }) {
    const overrides = callSheet.header_values || {};
    return (callSheet.template.key_crew || []).map((k) => (
        <label key={`${k.key}:${overrides[k.key] ?? ''}`} className="cs-field">
            <span>{k.label}</span>
            <TypedInput type="text" value={overrides[k.key] ?? k.value}
                        onCommit={(raw) => onPatch({ header_values: { [k.key]: toNull(raw) } })} />
        </label>
    ));
}

/** Template blocks: shown with the template text; editing stores a day-only override. */
export function BlocksPanel({ callSheet, onPatch }) {
    const overrides = callSheet.block_overrides || {};
    return (callSheet.template.blocks || []).map((b) => {
        const overridden = overrides[b.key] !== undefined;
        return (
            <label key={`${b.key}:${overrides[b.key] ?? ''}`} className="cs-field">
                <span>{b.label}{overridden && <em className="cs-overridden"> (edited for this day)</em>}</span>
                <TypedInput type="textarea" value={overrides[b.key] ?? b.body}
                            onCommit={(raw) => onPatch({
                                // Identical to the template text = drop the override.
                                block_overrides: { [b.key]: raw === b.body ? null : raw },
                            })} />
            </label>
        );
    });
}

export function DeptCallsPanel({ callSheet, onPatch }) {
    const overrides = callSheet.dept_overrides || {};
    const depts = callSheet.template.departments || [];
    if (!depts.length) return <p className="cs-note">No departments in the template yet.</p>;
    return (
        <table className="cs-scene-table">
            <thead><tr><th>Department</th><th>Call</th><th>As per</th></tr></thead>
            <tbody>
                {depts.map((d) => {
                    const ov = overrides[d.key] || {};
                    return (
                        <tr key={`${d.key}:${ov.call ?? ''}:${ov.as_per ?? ''}`}>
                            <td>{d.label}</td>
                            <td><TypedInput type="time" value={ov.call ?? d.default_call}
                                            onCommit={(raw) => onPatch({ dept_overrides: { [d.key]: { call: toNull(raw) } } })} /></td>
                            <td><TypedInput type="text" value={ov.as_per ?? d.as_per}
                                            onCommit={(raw) => onPatch({ dept_overrides: { [d.key]: { as_per: toNull(raw) } } })} /></td>
                        </tr>
                    );
                })}
            </tbody>
        </table>
    );
}

/** Per-meal headcount grid, prefilled from roster counts (catering_effective). */
export function CateringPanel({ callSheet, onPatch }) {
    const eff = callSheet.catering_effective || {};
    return (
        <table className="cs-scene-table cs-catering-table">
            <thead><tr><th></th>{MEALS.map(([m, label]) => <th key={m}>{label}</th>)}</tr></thead>
            <tbody>
                {GROUPS.map(([g, glabel]) => (
                    <tr key={g}>
                        <td>{glabel}</td>
                        {MEALS.map(([m]) => (
                            <td key={`${m}:${eff[m]?.[g] ?? 0}`}>
                                <TypedInput type="number" value={eff[m]?.[g] ?? 0}
                                            onCommit={(raw) => onPatch(
                                                { catering: { [m]: { [g]: raw === '' ? null : Number(raw) } } },
                                                { reload: true })} />
                            </td>
                        ))}
                    </tr>
                ))}
            </tbody>
        </table>
    );
}

/** Inline inputs for a table's custom columns. Sensitive columns are hidden from viewers who can't see them. */
export function ColumnInputs({ columns, values, onCommit, canSeeSensitive }) {
    const visible = (columns || []).filter((c) => canSeeSensitive || !c.sensitive);
    if (!visible.length) return null;
    return (
        <span className="cs-inline-cols">
            {visible.map((c) => (
                <label key={`${c.key}:${values?.[c.key] ?? ''}`} className="cs-inline-col">
                    <small>{c.label}</small>
                    <TypedInput type={c.type} value={values?.[c.key] ?? ''}
                                onCommit={(raw) => onCommit(c.key, toNull(raw))} />
                </label>
            ))}
        </span>
    );
}
```

- [ ] **Step 2: Rewrite `CallSheetEditor.jsx`**

The load logic, crew/cast/location handlers and footer are unchanged from v1; the changes are the template-driven section loop, the column inputs, `patchCallSheet` with `ignored_keys`, and the new panels.

```jsx
// frontend/src/components/schedule/CallSheetEditor.jsx
import { useState, useEffect, useCallback } from 'react';
import { X, Download } from 'lucide-react';
import {
    getOrCreateCallSheet, getCallSheet, getCallSheetByDay, updateCallSheet,
    addCallSheetCrew, updateCallSheetCrew, removeCallSheetCrew,
    addCallSheetCast, updateCallSheetCast, removeCallSheetCast,
    addCallSheetLocation, removeCallSheetLocation,
    downloadCallSheetPdf,
    listProductionCrew, listProductionLocations, getCasting,
} from '../../services/apiService';
import { Spinner } from '../ui';
import { useToast } from '../../context/ToastContext';
import {
    DayFieldsPanel, KeyCrewPanel, BlocksPanel, DeptCallsPanel, CateringPanel, ColumnInputs,
} from './CallSheetPanels';
import './CallSheetEditor.css';

const CallSheetEditor = ({ dayId, dayNumber, productionId, scriptId, onClose }) => {
    const toast = useToast();
    const [callSheet, setCallSheet] = useState(null);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [crewOptions, setCrewOptions] = useState([]);
    const [locationOptions, setLocationOptions] = useState([]);
    const [castOptions, setCastOptions] = useState([]);

    // Sequencing matters here: production_id isn't known until the call
    // sheet itself has loaded, so the crew/location fetches (keyed off it)
    // run AFTER that resolves rather than in the same Promise.all batch.
    const load = useCallback(async () => {
        setLoading(true);
        setLoadError(null);
        try {
            let full;
            try {
                // Viewer-accessible GET first -- a read-only member can open
                // an existing call sheet without ever hitting the edit-gated
                // POST below.
                full = await getCallSheetByDay(dayId);
            } catch (err) {
                if (err.response?.status !== 404) throw err;
                try {
                    const created = await getOrCreateCallSheet(dayId);
                    full = await getCallSheet(created.call_sheet.id);
                } catch (createErr) {
                    if (createErr.response?.status === 403) {
                        setLoadError("You don't have permission to create a call sheet for this day.");
                        return;
                    }
                    throw createErr;
                }
            }
            setCallSheet(full.call_sheet);

            const pid = full.call_sheet.production_id;
            if (pid) {
                const [crewRes, locRes] = await Promise.all([
                    listProductionCrew(pid),
                    listProductionLocations(pid),
                ]);
                setCrewOptions(crewRes.crew || []);
                setLocationOptions((locRes.locations || []).map((l) => {
                    const loc = l.location || l;
                    return { ...loc, id: loc.id || l.location_id };
                }));
            }
            if (scriptId) {
                const castRes = await getCasting(scriptId);
                setCastOptions(castRes.casting || []);
            }
        } catch (err) {
            console.error('Failed to load call sheet:', err);
            setLoadError('Could not load the call sheet for this day.');
            toast.error('Error', 'Could not load the call sheet for this day.');
        } finally {
            setLoading(false);
        }
    }, [dayId, scriptId, toast]);

    useEffect(() => { load(); }, [load]);

    // One save path for every day-level edit. Keys the template no longer
    // defines come back in ignored_keys -> reload so the UI matches the template.
    const patchCallSheet = async (payload, { reload = false } = {}) => {
        setSaving(true);
        try {
            const res = await updateCallSheet(callSheet.id, payload);
            if (res.ignored_keys?.length) {
                toast.warning('Template changed', 'Some fields were removed from the template. Reloading.');
                await load();
            } else if (reload) {
                await load();
            } else {
                setCallSheet((prev) => ({ ...prev, ...res.call_sheet }));
            }
        } catch (err) {
            console.error('Failed to update call sheet:', err);
            toast.error('Update Failed', err.response?.data?.error || 'Could not save that change.');
        } finally {
            setSaving(false);
        }
    };

    const publish = () => patchCallSheet({ status: 'published' });
    const unpublish = () => patchCallSheet({ status: 'draft' });

    const addCrewRow = async (crewId) => {
        if (!crewId) return;
        try {
            await addCallSheetCrew(callSheet.id, { crew_id: crewId });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not add crew member.');
        }
    };

    const updateCrewRow = async (crewId, payload) => {
        try {
            await updateCallSheetCrew(callSheet.id, crewId, payload);
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not update crew row.');
        }
    };

    const removeCrewRow = async (crewId) => {
        await removeCallSheetCrew(callSheet.id, crewId);
        await load();
    };

    const addLocationRow = async (locationId) => {
        if (!locationId) return;
        try {
            await addCallSheetLocation(callSheet.id, { location_id: locationId });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not add location.');
        }
    };

    const removeLocationRow = async (locationId) => {
        await removeCallSheetLocation(callSheet.id, locationId);
        await load();
    };

    const addCastRow = async (castingId) => {
        if (!castingId) return;
        try {
            await addCallSheetCast(callSheet.id, { casting_id: castingId });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not add cast member.');
        }
    };

    const updateCastRow = async (castingId, payload) => {
        try {
            await updateCallSheetCast(callSheet.id, castingId, payload);
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not update cast row.');
        }
    };

    const removeCastRow = async (castingId) => {
        await removeCallSheetCast(callSheet.id, castingId);
        await load();
    };

    if (loading || (!callSheet && !loadError)) {
        return (
            <div className="cs-modal-backdrop" onClick={onClose}>
                <div className="cs-modal" onClick={(e) => e.stopPropagation()}><Spinner /></div>
            </div>
        );
    }

    if (loadError) {
        return (
            <div className="cs-modal-backdrop" onClick={onClose}>
                <div className="cs-modal" onClick={(e) => e.stopPropagation()}>
                    <div className="cs-modal-header">
                        <h3>Call Sheet &middot; Day {dayNumber}</h3>
                        <button className="cs-modal-close" onClick={onClose}><X size={18} /></button>
                    </div>
                    <p className="cs-load-error">{loadError}</p>
                </div>
            </div>
        );
    }

    const template = callSheet.template;
    const canSeeSensitive = !!callSheet.can_view_sensitive;
    const extrasVisible = template.sections.some((s) => s.key === 'extras' && s.visible);
    const isBackground = (row) => row.casting?.tier === 'background';
    const castRows = extrasVisible ? (callSheet.cast || []).filter((r) => !isBackground(r)) : (callSheet.cast || []);
    const extrasRows = extrasVisible ? (callSheet.cast || []).filter(isBackground) : [];

    const castList = (rows) => (
        <ul className="cs-roster-list">
            {rows.map((row) => (
                <li key={row.id}>
                    {row.casting?.character_name} ({row.casting?.actor_name || 'unbooked'})
                    <input type="time" defaultValue={row.call_time || ''}
                           onBlur={(e) => updateCastRow(row.casting_id, { call_time: e.target.value || null })} />
                    <button onClick={() => removeCastRow(row.casting_id)}>Remove</button>
                    <ColumnInputs columns={template.cast_columns} values={row.extra} canSeeSensitive={canSeeSensitive}
                                  onCommit={(key, value) => updateCastRow(row.casting_id, { extra: { [key]: value } })} />
                </li>
            ))}
        </ul>
    );

    const renderSection = (key) => {
        switch (key) {
            case 'header':
                return (
                    <>
                        <DayFieldsPanel callSheet={callSheet} section="header" onPatch={patchCallSheet} />
                        <KeyCrewPanel callSheet={callSheet} onPatch={patchCallSheet} />
                    </>
                );
            case 'day_info':
                return <DayFieldsPanel callSheet={callSheet} section="day_info" onPatch={patchCallSheet} />;
            case 'locations':
                return (
                    <>
                        <select defaultValue="" onChange={(e) => addLocationRow(e.target.value)}>
                            <option value="" disabled>Add a location…</option>
                            {locationOptions.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                        </select>
                        <ul className="cs-roster-list">
                            {(callSheet.locations || []).map((row) => (
                                <li key={row.id}>
                                    {row.location?.name} {row.is_primary && '(Primary)'}
                                    <button onClick={() => removeLocationRow(row.location_id)}>Remove</button>
                                </li>
                            ))}
                        </ul>
                    </>
                );
            case 'scenes':
                return (
                    <table className="cs-scene-table">
                        <thead><tr><th>Sc</th><th>I/E</th><th>Set</th><th>D/N</th></tr></thead>
                        <tbody>
                            {(callSheet.scenes || []).map((s) => (
                                <tr key={s.id}>
                                    <td>{s.scene_number}</td><td>{s.int_ext}</td>
                                    <td>{s.setting || s.location_canonical}</td><td>{s.time_of_day}</td>
                                    {template.scene_columns.some((c) => canSeeSensitive || !c.sensitive) && (
                                        <td>
                                            <ColumnInputs columns={template.scene_columns}
                                                          values={(callSheet.scene_extras || {})[s.id]}
                                                          canSeeSensitive={canSeeSensitive}
                                                          onCommit={(k, v) => patchCallSheet({ scene_extras: { [s.id]: { [k]: v } } })} />
                                        </td>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                );
            case 'cast':
                return (
                    <>
                        <select defaultValue="" onChange={(e) => addCastRow(e.target.value)}>
                            <option value="" disabled>Add a cast member…</option>
                            {castOptions.map((c) => (
                                <option key={c.id} value={c.id}>{c.character_name} — {c.actor_name || 'unbooked'}</option>
                            ))}
                        </select>
                        {castList(castRows)}
                    </>
                );
            case 'extras':
                return extrasRows.length
                    ? castList(extrasRows)
                    : <p className="cs-note">Background cast added in the Cast section appear here.</p>;
            case 'crew':
                return (
                    <>
                        <select defaultValue="" onChange={(e) => addCrewRow(e.target.value)}>
                            <option value="" disabled>Add a crew member…</option>
                            {crewOptions.map((c) => <option key={c.id} value={c.id}>{c.contact?.name} — {c.role}</option>)}
                        </select>
                        <ul className="cs-roster-list">
                            {(callSheet.crew || []).map((row) => (
                                <li key={row.id}>
                                    {row.crew?.contact?.name}
                                    <input type="time" defaultValue={row.call_time || ''}
                                           onBlur={(e) => updateCrewRow(row.crew_id, { call_time: e.target.value || null })} />
                                    <button onClick={() => removeCrewRow(row.crew_id)}>Remove</button>
                                    <ColumnInputs columns={template.crew_columns} values={row.extra} canSeeSensitive={canSeeSensitive}
                                                  onCommit={(k, v) => updateCrewRow(row.crew_id, { extra: { [k]: v } })} />
                                </li>
                            ))}
                        </ul>
                    </>
                );
            case 'dept_calls':
                return <DeptCallsPanel callSheet={callSheet} onPatch={patchCallSheet} />;
            case 'catering':
                return <CateringPanel callSheet={callSheet} onPatch={patchCallSheet} />;
            case 'notes':
                return (
                    <>
                        <DayFieldsPanel callSheet={callSheet} section="notes" onPatch={patchCallSheet} />
                        <BlocksPanel callSheet={callSheet} onPatch={patchCallSheet} />
                    </>
                );
            case 'advanced':
                return <p className="cs-note">The next shooting day&rsquo;s scenes are added to the PDF automatically.</p>;
            default:
                return null;
        }
    };

    return (
        <div className="cs-modal-backdrop" onClick={onClose}>
            <div className="cs-modal" onClick={(e) => e.stopPropagation()}>
                <div className="cs-modal-header">
                    <h3>Call Sheet &middot; Day {dayNumber}</h3>
                    <span className={`cs-status-chip cs-status-${callSheet.status}`}>{callSheet.status}</span>
                    <button className="cs-modal-close" onClick={onClose}><X size={18} /></button>
                </div>

                <div className="cs-modal-body">
                    {template.sections.filter((s) => s.visible).map((s) => (
                        <section key={s.key} className="cs-section">
                            <h4>{s.label}</h4>
                            {renderSection(s.key)}
                        </section>
                    ))}
                </div>

                <div className="cs-modal-footer">
                    <button className="cs-download-btn" onClick={() => downloadCallSheetPdf(callSheet.id, dayNumber)}>
                        <Download size={14} /> Download PDF
                    </button>
                    {callSheet.status === 'draft' ? (
                        <button className="cs-publish-btn" disabled={saving} onClick={publish}>Publish</button>
                    ) : (
                        <button className="cs-unpublish-btn" disabled={saving} onClick={unpublish}>Move back to draft</button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CallSheetEditor;
```

- [ ] **Step 3: Append styles to `CallSheetEditor.css`**

```css
.cs-modal input[type="number"] {
    padding: 0.4rem 0.5rem;
    background-color: var(--gray-800, #1e293b) !important;
    border: 1px solid var(--border-color, #334155);
    border-radius: 8px;
    color: var(--text-primary, #f8fafc) !important;
    font-size: 0.875rem;
    width: 100%;
    box-sizing: border-box;
}

.cs-note { color: var(--text-secondary, #94a3b8); font-size: 0.8rem; margin: 0.25rem 0; }
.cs-overridden { color: var(--primary-500, #f59e0b); font-style: normal; font-size: 0.75rem; }
.cs-inline-cols { display: flex; flex-wrap: wrap; gap: 0.5rem; width: 100%; }
.cs-inline-col { display: flex; flex-direction: column; gap: 0.15rem; flex: 1 1 110px; }
.cs-inline-col small { color: var(--text-secondary, #94a3b8); font-size: 0.7rem; }
.cs-roster-list li { flex-wrap: wrap; }
.cs-catering-table td { padding: 0.15rem 0.25rem; }
.cs-scene-table input[type="time"], .cs-scene-table input[type="text"] { width: 100%; }
```

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Manual end-to-end check**

With both dev servers running and the migration applied to the dev Supabase project:

1. Production → Call Sheet tab: add day field "Wind" (day_info), cast column "P/U at base" (time), scene column "Story day" (text), a department "Wardrobe" (06:00, As per Pippa), a block "Special notes", key-crew "Director"; enable Extras, Dept calls, Catering, Advanced; **Save**.
2. Schedule → open a day's call sheet: confirm the sections appear in the template order; fill Wind, a P/U value on a cast row, Story day on a scene, a catering number, a dept override, a block edit ("edited for this day" tag appears).
3. Reload the modal: every value persisted; catering shows roster-prefilled counts where not overridden.
4. **Download PDF**: confirm each value renders in the right section; open with the Read tool to confirm the header repeats on page 2+ if the sheet spans pages.
5. In the template tab remove "Wind" and Save; reopen the call sheet: no crash and the Wind input is gone, but the browser Network tab shows the GET response still carries `custom_values.wind` (removed fields keep their stored values).
6. As a viewer-role member: template tab is read-only, call sheet editor opens (viewer), PATCH controls fail with a friendly toast.
7. Mark a cast column "Sensitive", save; as a coordinator without "See rates & phone" confirm the column is hidden in the editor and absent from the PDF.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/schedule/CallSheetPanels.jsx frontend/src/components/schedule/CallSheetEditor.jsx frontend/src/components/schedule/CallSheetEditor.css
git commit -m "$(cat <<'EOF'
feat(call-sheets): template-driven per-day call sheet editor

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: Docs, spec reconciliation and final verification

**Files:**
- Modify: `docs/BACKLOG.md` (the "Call sheets: robustness + per-production customization pass" entry, ~line 2042; and the "Do next" item 1, ~line 140)
- Modify: `docs/SLATEONE_FEATURES.md` (call sheets section)
- Modify: `docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md` (rollout note)

- [ ] **Step 1: Reconcile the spec with two implementation decisions**

In the spec's "Rollout" section replace item 3 (`No env vars, no backfill.`) with:

```
3. No env vars. The migration backfills `can_edit_call_sheet_template = true`
   for existing admin/coordinator members and pending invites so current
   admins aren't locked out of the template (presets only apply to members
   created afterwards).
```

and add under "Routes" that the template GET response also carries `default_config` (used by the editor's "Reset to default").

- [ ] **Step 2: Update the backlog**

At the top of the customization entry set:

```
**Status:** SHIPPED (per-production templates) — <merge date>. Design:
`docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md`,
plan: `docs/superpowers/plans/2026-09-21-call-sheet-customization.md`.
Migration `055_call_sheet_templates.sql` must be applied to Supabase.
```

and add a "Still open after this slice" list: multi-script shoot days (reference sheet covers 3 episodes in one day; schedules/casting are per script), extras from `casting_groups`, drag-and-drop section reordering, multiple named templates, cross-production template copy, first-class scheduled per-scene timings, config `v2` migration story. In "Do next" item 1, note that the customization pass is done.

- [ ] **Step 3: Update the features overview**

Run: `grep -n -i "call sheet" docs/SLATEONE_FEATURES.md`
Under the existing call sheets text add a short paragraph: each production has one call sheet template (Production → Call Sheet tab) controlling section visibility/order/labels, custom day fields, custom cast/crew/scene columns, department call times, boilerplate blocks and a header/key-crew block; sensitive columns are hidden from members without "See rates & phone"; days inherit the template and can override.

- [ ] **Step 4: Full verification**

Run:
```bash
cd backend && venv/bin/python -m pytest tests/ -q
cd ../frontend && npm run build
```
Expected: the full backend suite is green (no regressions in the crew/location/member/authz/route-enforcement suites) and the frontend build succeeds. Report any failure with its output instead of claiming success.

- [ ] **Step 5: Hand-off note (do NOT apply the migration yourself)**

Applying `055_call_sheet_templates.sql` to the production Supabase project is an outward-facing step for the account owner. Finish by telling them: apply migration 055, then deploy the backend before the frontend (a missing template row resolves to the v1 default, so existing sheets keep working either way).

- [ ] **Step 6: Commit**

```bash
git add docs/BACKLOG.md docs/SLATEONE_FEATURES.md docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md
git commit -m "$(cat <<'EOF'
docs(call-sheets): document shipped customization and remaining follow-ups

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes (spec coverage)

| Spec section | Task |
|---|---|
| Data model (template table, JSONB columns, `general_call`, capability columns) | 1 |
| Validation rules (types, merge, unknown keys, caps, locked builtins, keys) | 2, 3, 5 |
| Permissions (capability, presets, invite copy, coordinator key test) | 1 (+ Members tab in 10) |
| Routes (template GET/PUT, PATCH merge, `ignored_keys`, roster `extra`) | 4, 5, 6, 7 |
| Redaction (cast/crew/scene/day, JSON + roster responses + PDF) | 7 (+ 8 seam) |
| Template editor UI | 10, 11 |
| Per-day editor (template-driven, dept, catering, key crew, blocks, extras, advanced) | 12 |
| PDF rendering (registry, sections, escaping, running header, no single-page limit) | 8, 9 |
| Default-config parity with v1 | 3 (config), 8 (tests) |
| Rollout / docs / multi-script out-of-scope | 13 |
