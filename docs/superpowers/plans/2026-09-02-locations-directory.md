# Locations Directory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an account-level `locations` directory (parallel to `contacts`), a per-production `production_locations` link with a Locations tab, location reference photos, and a Mapbox static-map preview.

**Architecture:** Mirrors build-sequence step 2a (crew + contacts) exactly. A new owner-scoped `locations_bp` blueprint for directory CRUD; production-scoped link routes on the existing `production_bp` gated by `require_production_role` + the existing `can_edit_production` capability (no new flag); a thin server-side `geocode_service` (Mapbox) that degrades to `None` on any failure; a client-side `<img>` static map keyed off `lat`/`lng` + `VITE_MAPBOX_PUBLIC_TOKEN`. All DB access via the Supabase service-role client; app-layer authorization; owner-only RLS as a direct-client backstop only.

**Tech Stack:** Flask (Python 3.13), `supabase-py` (service-role key), pytest; React 18 + Vite (plain JSX), axios via `frontend/src/services/apiService.js`; Supabase Postgres + Storage (`scripts` bucket); Mapbox Geocoding v6 + Static Images APIs.

**Spec:** `docs/superpowers/specs/2026-09-02-locations-directory-design.md`

## Global Constraints

- **Supabase is the only datastore.** All backend DB access through `db.supabase_client.get_supabase_admin()` (service-role, bypasses RLS). Never SQLite.
- **Migrations are applied manually** to the Supabase project (`slateone` / `twzfaizeyqwevmhjyicz`). `run_migration.py` is dead. The plan's migration task produces the `.sql` file; a human applies it.
- **Authorization is app-layer**, in Python, via decorators. RLS policies are a direct-client backstop only and the app never relies on them.
- **Backend gate:** `pytest tests/` from `backend/` must stay green. **Frontend gate:** `npm run build` from `frontend/` (NOT `npm run lint` — lint is broken repo-wide).
- **Directory is owner-only.** `locations` has no script axis and no production axis; every `location_service` query filters `owner_id == caller`. `get_script_role` / `get_production_role` are not involved in directory routes.
- **Naming collision:** `backend/services/location_resolver.py` and `location_quality.py` already exist — those are the *creative* scene-`setting`→canonical-place resolver, unrelated to this slice. New files (`location_service.py`, `location_routes.py`, `production_location_service.py`, `test_location_service.py`, `test_location_routes.py`, `test_production_location_routes.py`, `test_geocode_service.py`) MUST carry a one-line header comment: `# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative scene-setting resolver in location_resolver.py.`
- **Sensitive fields:** nothing on `locations` is sensitive. No `can_view_sensitive` redaction on location fields. The primary contact's phone/rate stays gated by existing `contact_service` logic wherever a contact is surfaced.
- **Commit message trailer** on every commit:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01AkGMJqKXBEh21LAWc1xKwi
  ```
- **Branch:** `feat/locations-directory-3` (already created, spec + backlog committed on it).

---

## File Structure

**Backend — create:**
- `backend/db/migrations/053_locations.sql` — `locations`, `production_locations`, `location_photos` tables + indexes + triggers + RLS backstop.
- `backend/services/geocode_service.py` — `geocode(address) -> {lat,lng} | None` via Mapbox; never raises.
- `backend/services/location_service.py` — owner-scoped directory CRUD + geocode-on-write + photo helpers.
- `backend/services/production_location_service.py` — per-production link list/create/update/delete.
- `backend/routes/location_routes.py` — `locations_bp` (`/api/locations/*`).
- `backend/tests/test_geocode_service.py`, `test_location_service.py`, `test_location_routes.py`, `test_production_location_routes.py`.

**Backend — modify:**
- `backend/db/migrations/013_delete_user_safely.sql` — add a comment noting `locations` cascades cleanly (no RESTRICT FK, so no explicit `DELETE FROM` needed) — see Task 1.
- `backend/middleware/production_authz.py` — add `from_production_location_id` resolver.
- `backend/routes/production_routes.py` — add 4 location-link routes.
- `backend/routes/__init__` registration in `backend/app.py` — register `locations_bp`.
- `backend/utils/env_validator.py` — add `MAPBOX_SECRET_TOKEN` to `RECOMMENDED_VARS`.
- `backend/tests/test_route_enforcement.py` — extend the production-scoped assertion's allow-list / coverage for the new routes.

**Frontend — create:**
- `frontend/src/pages/LocationsListPage.jsx` — directory page (clone of `ContactsListPage.jsx`).
- `frontend/src/components/locations/LocationFormModal.jsx` — add/edit form.
- `frontend/src/components/locations/LocationDetailDrawer.jsx` — detail panel (fields, map, photos, usage).
- `frontend/src/components/locations/StaticMap.jsx` — the `<img>` Mapbox static-map component.
- `frontend/src/components/productions/ProductionLocationsTab.jsx` — production tab.
- `frontend/src/components/productions/LocationPickerModal.jsx` — pick a location to link.

**Frontend — modify:**
- `frontend/src/services/apiService.js` — new functions block.
- `frontend/src/App.jsx` — `<Route path="locations" ...>`.
- `frontend/src/components/layout/TopBar.jsx` — nav link.
- `frontend/src/pages/ProductionDetailPage.jsx` — add the Locations tab.
- `frontend/src/pages/ProductionPages.css` — reuse; add location-specific rules as needed.

---

## Task 1: Migration `053_locations.sql`

**Files:**
- Create: `backend/db/migrations/053_locations.sql`
- Modify: `backend/db/migrations/013_delete_user_safely.sql` (comment only)

**Interfaces:**
- Produces: tables `locations` (cols: `id, owner_id, name, address, lat, lng, geocode_status, primary_contact_id, permit_status, parking_notes, loadin_notes, restrictions, notes, created_by, created_at, updated_at`), `production_locations` (`id, production_id, location_id, production_notes, created_at`), `location_photos` (`id, location_id, storage_path, caption, sort_order, created_at`).

- [ ] **Step 1: Write the migration file**

```sql
-- Migration 053: Locations directory + production locations + photos (build-sequence step 3)
-- See docs/superpowers/specs/2026-09-02-locations-directory-design.md
-- Apply manually against the Supabase project (run_migration.py is dead).
--
-- This is the account-level real-world LOCATIONS directory. It is NOT the
-- creative scene-setting -> canonical-place resolver (scenes.location_canonical,
-- services/location_resolver.py) -- that is a separate, untouched system.
--
-- Delete-user note (013_delete_user_safely.sql deletes scripts then profiles):
-- locations.owner_id is ON DELETE CASCADE and has NO inbound RESTRICT FK
-- (production_locations.location_id and location_photos.location_id are both
-- ON DELETE CASCADE). So the profiles -> locations cascade clears everything
-- with no ordering hazard -- unlike production_crew.contact_id (RESTRICT),
-- which needed an explicit DELETE in 013. No 013 code change required here.

-- ============================================
-- 1. locations -- account-level reusable directory
-- ============================================
CREATE TABLE IF NOT EXISTS locations (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id           UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name               TEXT NOT NULL,
    address            TEXT,
    lat                NUMERIC,
    lng                NUMERIC,
    geocode_status     TEXT CHECK (geocode_status IS NULL
                         OR geocode_status IN ('ok','failed','manual')),
    primary_contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
    permit_status      TEXT,
    parking_notes      TEXT,
    loadin_notes       TEXT,
    restrictions       TEXT,
    notes              TEXT,
    created_by         UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_locations_owner ON locations(owner_id);
CREATE INDEX IF NOT EXISTS idx_locations_owner_name ON locations(owner_id, lower(name));

CREATE TRIGGER trg_locations_updated
    BEFORE UPDATE ON locations
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 2. production_locations -- link (production <-> location)
-- ============================================
CREATE TABLE IF NOT EXISTS production_locations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id     UUID NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    location_id       UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    production_notes  TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (production_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_production_locations_production ON production_locations(production_id);
CREATE INDEX IF NOT EXISTS idx_production_locations_location ON production_locations(location_id);

-- ============================================
-- 3. location_photos -- reference images (mirrors casting_photos)
-- ============================================
CREATE TABLE IF NOT EXISTS location_photos (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    location_id   UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    storage_path  TEXT NOT NULL,
    caption       TEXT,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_location_photos_location ON location_photos(location_id);

-- ============================================
-- 4. RLS -- owner-only, direct-client backstop only
-- ============================================
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE location_photos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner manages locations"
    ON locations FOR ALL USING (owner_id = auth.uid());

CREATE POLICY "owner manages production locations"
    ON production_locations FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = production_locations.production_id
                  AND p.owner_id = auth.uid())
    );

CREATE POLICY "owner manages location photos"
    ON location_photos FOR ALL USING (
        EXISTS (SELECT 1 FROM locations l
                WHERE l.id = location_photos.location_id
                  AND l.owner_id = auth.uid())
    );
```

- [ ] **Step 2: Add the clarifying comment to `013_delete_user_safely.sql`**

Immediately after the existing `DELETE FROM production_crew ...` block (both function bodies — there are two, around lines 23 and 62), add:

```sql
    -- locations (053) needs no explicit delete here: profiles -> locations is
    -- ON DELETE CASCADE and nothing references locations with RESTRICT.
```

- [ ] **Step 3: Sanity-check the SQL locally (no DB)**

Run: `python -c "import pathlib; s=pathlib.Path('backend/db/migrations/053_locations.sql').read_text(); assert s.count('CREATE TABLE')==3 and 'geocode_status' in s and 'UNIQUE (production_id, location_id)' in s; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/db/migrations/053_locations.sql backend/db/migrations/013_delete_user_safely.sql
git commit -m "feat(db): migration 053 — locations directory + production_locations + photos"
```

- [ ] **Step 5: Flag for manual apply**

Print a note to the human operator: "Apply `backend/db/migrations/053_locations.sql` to the Supabase project before deploying. Subsequent tasks mock the DB, so local tests pass without it, but staging/live need it."

---

## Task 2: `geocode_service.py`

**Files:**
- Create: `backend/services/geocode_service.py`
- Test: `backend/tests/test_geocode_service.py`

**Interfaces:**
- Produces: `geocode(address: str) -> dict | None` — returns `{"lat": float, "lng": float}` on success, `None` on missing key / empty address / non-200 / empty result / timeout / any exception. Never raises.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_geocode_service.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
from unittest.mock import patch, MagicMock
import services.geocode_service as gs


def _resp(status=200, json_body=None):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_body or {}
    return m


def test_returns_none_when_key_missing(monkeypatch):
    monkeypatch.delenv("MAPBOX_SECRET_TOKEN", raising=False)
    assert gs.geocode("1 Main Rd, Cape Town") is None


def test_returns_none_for_blank_address(monkeypatch):
    monkeypatch.setenv("MAPBOX_SECRET_TOKEN", "tok")
    assert gs.geocode("   ") is None


def test_parses_coordinates_from_mapbox_v6(monkeypatch):
    monkeypatch.setenv("MAPBOX_SECRET_TOKEN", "tok")
    body = {"features": [{"geometry": {"type": "Point", "coordinates": [18.42, -33.92]}}]}
    with patch("services.geocode_service.requests.get", return_value=_resp(200, body)) as g:
        out = gs.geocode("1 Main Rd, Cape Town")
    assert out == {"lat": -33.92, "lng": 18.42}
    assert g.call_args.kwargs.get("timeout") == 5


def test_returns_none_on_empty_features(monkeypatch):
    monkeypatch.setenv("MAPBOX_SECRET_TOKEN", "tok")
    with patch("services.geocode_service.requests.get", return_value=_resp(200, {"features": []})):
        assert gs.geocode("nowhere") is None


def test_returns_none_on_http_error(monkeypatch):
    monkeypatch.setenv("MAPBOX_SECRET_TOKEN", "tok")
    with patch("services.geocode_service.requests.get", return_value=_resp(422, {})):
        assert gs.geocode("x") is None


def test_returns_none_on_exception(monkeypatch):
    monkeypatch.setenv("MAPBOX_SECRET_TOKEN", "tok")
    with patch("services.geocode_service.requests.get", side_effect=RuntimeError("boom")):
        assert gs.geocode("x") is None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_geocode_service.py -v`
Expected: FAIL — `ModuleNotFoundError: services.geocode_service`

- [ ] **Step 3: Implement**

```python
# backend/services/geocode_service.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
"""Thin server-side geocoder (Mapbox Geocoding v6). Never raises; returns
None on any failure so callers can degrade to manual lat/lng entry."""
import os

import requests

_FORWARD_URL = "https://api.mapbox.com/search/geocode/v6/forward"


def geocode(address):
    token = os.getenv("MAPBOX_SECRET_TOKEN")
    if not token or not address or not str(address).strip():
        return None
    try:
        resp = requests.get(
            _FORWARD_URL,
            params={"q": str(address).strip(), "limit": 1, "access_token": token},
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        features = resp.json().get("features") or []
        if not features:
            return None
        lng, lat = features[0]["geometry"]["coordinates"][:2]
        return {"lat": float(lat), "lng": float(lng)}
    except Exception:
        return None
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && pytest tests/test_geocode_service.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/services/geocode_service.py backend/tests/test_geocode_service.py
git commit -m "feat(locations): Mapbox geocode_service — degrades to None on any failure"
```

---

## Task 3: `location_service.py` — directory CRUD + geocode-on-write

**Files:**
- Create: `backend/services/location_service.py`
- Test: `backend/tests/test_location_service.py`

**Interfaces:**
- Consumes: `geocode_service.geocode` (Task 2); `db.supabase_client.get_supabase_admin`.
- Produces:
  - `NOT_FOUND` sentinel
  - `list_locations(user_id, q=None) -> list[dict]`
  - `create_location(user_id, fields: dict) -> dict`
  - `update_location(user_id, location_id, fields: dict) -> dict | NOT_FOUND`
  - `get_location_with_usage(user_id, location_id) -> dict | NOT_FOUND` — `{"location": row, "photos": [...], "used_in": [{"production_id","production_title"}]}`
  - `location_usage(user_id, location_id) -> list[dict]`
  - `delete_location(user_id, location_id) -> "not_found" | "in_use" | "ok"`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_location_service.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
import pytest
import services.location_service as svc


class FakeTable:
    def __init__(self, store, name):
        self.store, self.name, self._f, self._payload = store, name, {}, None
        self._op = None
    def select(self, *a): self._op = "select"; return self
    def insert(self, row): self._op, self._payload = "insert", row; return self
    def update(self, row): self._op, self._payload = "update", row; return self
    def delete(self): self._op = "delete"; return self
    def eq(self, k, v): self._f[k] = v; return self
    def in_(self, k, vals): self._f[(k, "in")] = set(vals); return self
    def or_(self, expr): self._f["_or"] = expr; return self
    def limit(self, n): return self
    def order(self, *a, **k): return self
    def _match(self, row):
        for k, v in self._f.items():
            if k == "_or":
                continue
            if isinstance(k, tuple) and k[1] == "in":
                if row.get(k[0]) not in v: return False
            elif row.get(k) != v:
                return False
        return True
    def execute(self):
        rows = self.store.setdefault(self.name, [])
        if self._op == "insert":
            r = dict(self._payload); r.setdefault("id", f"{self.name}-{len(rows)+1}")
            rows.append(r); return type("R", (), {"data": [r]})
        if self._op == "select":
            return type("R", (), {"data": [dict(r) for r in rows if self._match(r)]})
        if self._op == "update":
            hit = [r for r in rows if self._match(r)]
            for r in hit: r.update(self._payload)
            return type("R", (), {"data": [dict(r) for r in hit]})
        if self._op == "delete":
            keep = [r for r in rows if not self._match(r)]
            self.store[self.name] = keep
            return type("R", (), {"data": []})
        return type("R", (), {"data": []})


class FakeSupabase:
    def __init__(self): self.store = {}
    def table(self, name): return FakeTable(self.store, name)


@pytest.fixture
def fake(monkeypatch):
    fs = FakeSupabase()
    monkeypatch.setattr(svc, "get_supabase_admin", lambda: fs)
    monkeypatch.setattr(svc.geocode_service, "geocode", lambda a: None)
    return fs


def test_create_requires_owner_and_name(fake):
    row = svc.create_location("u1", {"name": "  Stage 6  "})
    assert row["owner_id"] == "u1" and row["created_by"] == "u1"
    assert row["name"] == "Stage 6"


def test_list_is_owner_scoped(fake):
    svc.create_location("u1", {"name": "A"})
    svc.create_location("u2", {"name": "B"})
    assert [r["name"] for r in svc.list_locations("u1")] == ["A"]


def test_update_geocodes_on_new_address(fake, monkeypatch):
    monkeypatch.setattr(svc.geocode_service, "geocode",
                        lambda a: {"lat": -33.9, "lng": 18.4})
    loc = svc.create_location("u1", {"name": "X"})
    out = svc.update_location("u1", loc["id"], {"address": "1 Main Rd"})
    assert out["lat"] == -33.9 and out["lng"] == 18.4 and out["geocode_status"] == "ok"


def test_update_failed_geocode_sets_failed_status(fake):
    loc = svc.create_location("u1", {"name": "X"})
    out = svc.update_location("u1", loc["id"], {"address": "??"})
    assert out["geocode_status"] == "failed" and out.get("lat") is None


def test_explicit_coords_skip_geocode_and_mark_manual(fake, monkeypatch):
    called = []
    monkeypatch.setattr(svc.geocode_service, "geocode",
                        lambda a: called.append(a) or {"lat": 1, "lng": 2})
    loc = svc.create_location("u1", {"name": "X"})
    out = svc.update_location("u1", loc["id"],
                              {"address": "1 Main Rd", "lat": 5, "lng": 6})
    assert out["lat"] == 5 and out["geocode_status"] == "manual" and called == []


def test_clearing_address_nulls_coords(fake):
    loc = svc.create_location("u1", {"name": "X", "lat": 1, "lng": 2,
                                     "geocode_status": "manual"})
    out = svc.update_location("u1", loc["id"], {"address": ""})
    assert out.get("lat") is None and out.get("geocode_status") is None


def test_update_other_owner_returns_not_found(fake):
    loc = svc.create_location("u1", {"name": "X"})
    assert svc.update_location("u2", loc["id"], {"name": "Y"}) is svc.NOT_FOUND


def test_delete_blocked_when_linked(fake):
    loc = svc.create_location("u1", {"name": "X"})
    fake.store.setdefault("production_locations", []).append(
        {"id": "pl1", "production_id": "p1", "location_id": loc["id"]})
    assert svc.delete_location("u1", loc["id"]) == "in_use"


def test_delete_ok_when_unlinked(fake):
    loc = svc.create_location("u1", {"name": "X"})
    assert svc.delete_location("u1", loc["id"]) == "ok"
    assert svc.list_locations("u1") == []


def test_get_with_usage_lists_productions(fake):
    loc = svc.create_location("u1", {"name": "X"})
    fake.store.setdefault("production_locations", []).append(
        {"id": "pl1", "production_id": "p1", "location_id": loc["id"],
         "production_notes": "week 2"})
    fake.store.setdefault("productions", []).append({"id": "p1", "title": "Feature"})
    out = svc.get_location_with_usage("u1", loc["id"])
    assert out["used_in"] == [{"production_id": "p1", "production_title": "Feature"}]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_location_service.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# backend/services/location_service.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
"""Owner-scoped locations directory. Every query filters owner_id == caller;
no script or production axis. Mirrors services/contact_service.py."""
from db.supabase_client import get_supabase_admin
from services import geocode_service

NOT_FOUND = object()

# Fields a caller may set directly. `geocode_status` is derived, never taken raw
# from create/update input except by internal helpers below.
FIELDS = ("name", "address", "lat", "lng", "primary_contact_id",
          "permit_status", "parking_notes", "loadin_notes", "restrictions", "notes")

PHOTO_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_BUCKET = "scripts"
SIGNED_URL_TTL = 3600


def _get(supabase, user_id, location_id):
    res = (supabase.table("locations").select("*")
           .eq("id", location_id).eq("owner_id", user_id).limit(1).execute())
    return res.data[0] if res.data else None


def _apply_geocode(fields, patch):
    """Fill lat/lng/geocode_status on `patch` from `fields`. Rules:
      - explicit lat AND lng supplied -> store them, status 'manual', no geocode
      - address present/changed, no explicit coords -> geocode; ok/failed
      - address explicitly blank -> null coords + status
    """
    has_addr = "address" in fields
    addr = (fields.get("address") or "").strip() if has_addr else None
    explicit = fields.get("lat") is not None and fields.get("lng") is not None
    if explicit:
        patch["lat"], patch["lng"] = fields["lat"], fields["lng"]
        patch["geocode_status"] = "manual"
        return
    if not has_addr:
        return
    if not addr:
        patch["lat"] = None
        patch["lng"] = None
        patch["geocode_status"] = None
        return
    hit = geocode_service.geocode(addr)
    if hit:
        patch["lat"], patch["lng"] = hit["lat"], hit["lng"]
        patch["geocode_status"] = "ok"
    else:
        patch["geocode_status"] = "failed"


def list_locations(user_id, q=None):
    query = get_supabase_admin().table("locations").select("*").eq("owner_id", user_id)
    if q:
        needle = q.strip().replace("%", "").replace(",", "")
        if needle:
            query = query.or_(f"name.ilike.%{needle}%,address.ilike.%{needle}%")
    return query.order("name").execute().data or []


def create_location(user_id, fields):
    supabase = get_supabase_admin()
    row = {"owner_id": user_id, "created_by": user_id,
           "name": (fields.get("name") or "").strip()}
    for f in FIELDS:
        if f != "name" and fields.get(f) is not None:
            row[f] = fields[f]
    _apply_geocode(fields, row)
    return supabase.table("locations").insert(row).execute().data[0]


def update_location(user_id, location_id, fields):
    supabase = get_supabase_admin()
    if not _get(supabase, user_id, location_id):
        return NOT_FOUND
    patch = {f: fields[f] for f in FIELDS if f in fields}
    if "name" in patch:
        patch["name"] = (patch["name"] or "").strip()
    _apply_geocode(fields, patch)
    if not patch:
        return _get(supabase, user_id, location_id)
    res = (supabase.table("locations").update(patch)
           .eq("id", location_id).eq("owner_id", user_id).execute())
    return res.data[0] if res.data else NOT_FOUND


def _linked_rows(supabase, location_id):
    return (supabase.table("production_locations").select("*")
            .eq("location_id", location_id).execute().data or [])


def location_usage(user_id, location_id):
    supabase = get_supabase_admin()
    links = _linked_rows(supabase, location_id)
    pids = list({l["production_id"] for l in links})
    if not pids:
        return []
    prods = (supabase.table("productions").select("id, title")
             .in_("id", pids).execute().data or [])
    return [{"production_id": p["id"], "production_title": p.get("title")} for p in prods]


def get_location_with_usage(user_id, location_id):
    supabase = get_supabase_admin()
    loc = _get(supabase, user_id, location_id)
    if not loc:
        return NOT_FOUND
    photos = (supabase.table("location_photos").select("*")
              .eq("location_id", location_id)
              .order("sort_order").order("created_at").execute().data or [])
    return {"location": loc,
            "photos": [_serialize_photo(p) for p in photos],
            "used_in": location_usage(user_id, location_id)}


def delete_location(user_id, location_id):
    supabase = get_supabase_admin()
    if not _get(supabase, user_id, location_id):
        return "not_found"
    if _linked_rows(supabase, location_id):
        return "in_use"
    supabase.table("locations").delete().eq("id", location_id).eq("owner_id", user_id).execute()
    return "ok"


# --- photos (Task 4 adds the tested surface; helper stub here) ---
def _serialize_photo(row):
    return {"id": row["id"], "caption": row.get("caption"),
            "sort_order": row.get("sort_order", 0), "url": _photo_url(row["storage_path"])}


def _photo_url(path):
    if not path:
        return None
    try:
        signed = (get_supabase_admin().storage.from_(PHOTO_BUCKET)
                  .create_signed_url(path, SIGNED_URL_TTL))
        return signed.get("signedURL") or signed.get("signed_url")
    except Exception:
        return None
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && pytest tests/test_location_service.py -v`
Expected: PASS (all tests). Then `pytest tests/ -q` — no regressions.

- [ ] **Step 5: Commit**

```bash
git add backend/services/location_service.py backend/tests/test_location_service.py
git commit -m "feat(locations): owner-scoped directory CRUD + geocode-on-write"
```

---

## Task 4: `location_service` photos — add / delete / list

**Files:**
- Modify: `backend/services/location_service.py`
- Test: `backend/tests/test_location_service.py` (append)

**Interfaces:**
- Produces:
  - `add_photo(user_id, location_id, file_bytes, content_type, caption=None) -> dict` — raises `ValueError` on bad type; returns serialized photo `{id,caption,sort_order,url}`.
  - `delete_photo(user_id, location_id, photo_id) -> "ok" | "not_found"`
  - `list_photos(user_id, location_id) -> list[dict]`

- [ ] **Step 1: Write the failing tests (append to `test_location_service.py`)**

```python
class FakeStorage:
    def __init__(self): self.uploaded, self.removed = [], []
    def from_(self, bucket): self.bucket = bucket; return self
    def upload(self, path, blob, opts=None): self.uploaded.append(path)
    def remove(self, paths): self.removed.extend(paths)
    def create_signed_url(self, path, ttl): return {"signedURL": f"https://x/{path}"}


@pytest.fixture
def fake_with_storage(fake):
    fake.storage = FakeStorage()
    return fake


def test_add_photo_rejects_bad_type(fake_with_storage):
    loc = svc.create_location("u1", {"name": "X"})
    with pytest.raises(ValueError):
        svc.add_photo("u1", loc["id"], b"x", "application/pdf")


def test_add_photo_stores_and_rows(fake_with_storage):
    loc = svc.create_location("u1", {"name": "X"})
    out = svc.add_photo("u1", loc["id"], b"bytes", "image/png", caption="north")
    assert out["caption"] == "north" and out["url"].startswith("https://x/locations/")
    assert svc.list_photos("u1", loc["id"])[0]["id"] == out["id"]


def test_add_photo_other_owner_rejected(fake_with_storage):
    loc = svc.create_location("u1", {"name": "X"})
    with pytest.raises(svc.NotOwner):
        svc.add_photo("u2", loc["id"], b"b", "image/png")


def test_delete_photo(fake_with_storage):
    loc = svc.create_location("u1", {"name": "X"})
    p = svc.add_photo("u1", loc["id"], b"b", "image/png")
    assert svc.delete_photo("u1", loc["id"], p["id"]) == "ok"
    assert svc.list_photos("u1", loc["id"]) == []
    assert svc.delete_photo("u1", loc["id"], p["id"]) == "not_found"
```

(Extend `FakeSupabase` with a `.storage` attribute passthrough: add `self.storage = None` in `__init__` and, in the fixture `fake`, it is set by `fake_with_storage`. Also make `get_supabase_admin()` in `_photo_url`/`add_photo` reach `fs.storage` — the service calls `get_supabase_admin().storage`, so `FakeSupabase` needs a `storage` property returning `self._storage`.)

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_location_service.py -k photo -v`
Expected: FAIL — `add_photo` / `NotOwner` undefined.

- [ ] **Step 3: Implement (append to `location_service.py`)**

```python
import uuid as _uuid


class NotOwner(Exception):
    pass


def _require_owned(supabase, user_id, location_id):
    loc = _get(supabase, user_id, location_id)
    if not loc:
        raise NotOwner(location_id)
    return loc


def list_photos(user_id, location_id):
    supabase = get_supabase_admin()
    _require_owned(supabase, user_id, location_id)
    rows = (supabase.table("location_photos").select("*")
            .eq("location_id", location_id)
            .order("sort_order").order("created_at").execute().data or [])
    return [_serialize_photo(r) for r in rows]


def add_photo(user_id, location_id, file_bytes, content_type, caption=None):
    supabase = get_supabase_admin()
    _require_owned(supabase, user_id, location_id)
    ext = PHOTO_TYPES.get(content_type)
    if not ext:
        raise ValueError("Use a JPG, PNG, or WebP image.")
    if len(file_bytes) > MAX_PHOTO_BYTES:
        raise ValueError("That image is over 5 MB. Use a smaller file.")
    path = f"locations/{location_id}/{_uuid.uuid4().hex}.{ext}"
    supabase.storage.from_(PHOTO_BUCKET).upload(path, file_bytes, {"content-type": content_type})
    row = {"location_id": location_id, "storage_path": path, "caption": caption}
    return _serialize_photo(supabase.table("location_photos").insert(row).execute().data[0])


def delete_photo(user_id, location_id, photo_id):
    supabase = get_supabase_admin()
    _require_owned(supabase, user_id, location_id)
    res = (supabase.table("location_photos").select("*")
           .eq("id", photo_id).eq("location_id", location_id).limit(1).execute())
    if not res.data:
        return "not_found"
    try:
        supabase.storage.from_(PHOTO_BUCKET).remove([res.data[0]["storage_path"]])
    except Exception:
        pass
    supabase.table("location_photos").delete().eq("id", photo_id).execute()
    return "ok"
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && pytest tests/test_location_service.py -v && pytest tests/ -q`
Expected: PASS; no regressions.

- [ ] **Step 5: Commit**

```bash
git add backend/services/location_service.py backend/tests/test_location_service.py
git commit -m "feat(locations): location photo add/list/delete (casting-photos pattern)"
```

---

## Task 5: `location_routes.py` — `locations_bp` + registration

**Files:**
- Create: `backend/routes/location_routes.py`
- Modify: `backend/app.py` (import + `register_blueprint`)
- Test: `backend/tests/test_location_routes.py`

**Interfaces:**
- Consumes: `location_service` (Tasks 3-4), `geocode_service` (Task 2), `middleware.auth.require_auth` / `get_user_id`.
- Produces routes on `locations_bp`:
  - `GET /api/locations` → `{"locations": [...]}`
  - `POST /api/locations` (name required) → `{"location": {...}}` 201
  - `GET /api/locations/<id>` → `{"location","photos","used_in"}` or 404
  - `PATCH /api/locations/<id>` → `{"location": {...}}` or 404
  - `DELETE /api/locations/<id>` → `{"success": true}` / 404 / 409 `{"error","used_in"}`
  - `POST /api/locations/<id>/photos` (multipart `file`, `?caption=`) → `{"photo": {...}}` 201 / 400 / 404
  - `DELETE /api/locations/<id>/photos/<photo_id>` → `{"success": true}` / 404
  - `POST /api/locations/geocode` (`{address}`) → `{"lat": <n>|null, "lng": <n>|null}`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_location_routes.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
import pytest
from unittest.mock import patch
import services.location_service as svc


@pytest.fixture
def client(app_client_authed_as):
    # Reuse the repo's existing authed-client fixture used by test_contact_routes.
    return app_client_authed_as("u1")


def test_list_requires_auth(app_client_anon):
    assert app_client_anon.get("/api/locations").status_code == 401


def test_create_requires_name(client):
    r = client.post("/api/locations", json={})
    assert r.status_code == 400


def test_create_and_list(client):
    with patch.object(svc, "create_location", return_value={"id": "l1", "name": "Stage 6"}):
        r = client.post("/api/locations", json={"name": "Stage 6"})
    assert r.status_code == 201 and r.get_json()["location"]["name"] == "Stage 6"


def test_get_404(client):
    with patch.object(svc, "get_location_with_usage", return_value=svc.NOT_FOUND):
        assert client.get("/api/locations/nope").status_code == 404


def test_delete_conflict_returns_409_with_used_in(client):
    with patch.object(svc, "delete_location", return_value="in_use"), \
         patch.object(svc, "location_usage", return_value=[{"production_id": "p1", "production_title": "F"}]):
        r = client.delete("/api/locations/l1")
    assert r.status_code == 409 and r.get_json()["used_in"][0]["production_id"] == "p1"


def test_geocode_route_passes_through(client):
    with patch("routes.location_routes.geocode_service.geocode", return_value={"lat": 1.0, "lng": 2.0}):
        r = client.post("/api/locations/geocode", json={"address": "1 Main Rd"})
    assert r.get_json() == {"lat": 1.0, "lng": 2.0}


def test_geocode_route_degraded(client):
    with patch("routes.location_routes.geocode_service.geocode", return_value=None):
        r = client.post("/api/locations/geocode", json={"address": "x"})
    assert r.get_json() == {"lat": None, "lng": None}
```

> If the repo has no shared `app_client_authed_as` / `app_client_anon` fixtures, copy the client-construction pattern from `backend/tests/test_contact_routes.py` verbatim (same auth-bypass via `FLASK_ENV`/`DEV_USER_ID` or JWT stub) into this file.

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_location_routes.py -v`
Expected: FAIL — routes 404 / blueprint missing.

- [ ] **Step 3: Implement the blueprint**

```python
# backend/routes/location_routes.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
"""Locations directory HTTP routes. Logic in services/location_service.py.
Owner-scoped: every route acts only on the caller's own locations."""
from flask import Blueprint, request, jsonify

from middleware.auth import require_auth, get_user_id
from services import location_service as svc
from services import geocode_service

locations_bp = Blueprint("locations", __name__)


@locations_bp.route("/api/locations", methods=["GET"])
@require_auth
def list_locations():
    return jsonify({"locations": svc.list_locations(get_user_id(), request.args.get("q"))})


@locations_bp.route("/api/locations", methods=["POST"])
@require_auth
def create_location():
    data = request.get_json(silent=True) or {}
    if not (data.get("name") or "").strip():
        return jsonify({"error": "name is required"}), 400
    return jsonify({"location": svc.create_location(get_user_id(), data)}), 201


@locations_bp.route("/api/locations/<location_id>", methods=["GET"])
@require_auth
def get_location(location_id):
    result = svc.get_location_with_usage(get_user_id(), location_id)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Location not found"}), 404
    return jsonify(result)


@locations_bp.route("/api/locations/<location_id>", methods=["PATCH"])
@require_auth
def update_location(location_id):
    data = request.get_json(silent=True) or {}
    if "name" in data and not (data.get("name") or "").strip():
        return jsonify({"error": "name cannot be empty"}), 400
    result = svc.update_location(get_user_id(), location_id, data)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Location not found"}), 404
    return jsonify({"location": result})


@locations_bp.route("/api/locations/<location_id>", methods=["DELETE"])
@require_auth
def delete_location(location_id):
    user_id = get_user_id()
    outcome = svc.delete_location(user_id, location_id)
    if outcome == "not_found":
        return jsonify({"error": "Location not found"}), 404
    if outcome == "in_use":
        return jsonify({"error": "Location is linked to productions",
                        "used_in": svc.location_usage(user_id, location_id)}), 409
    return jsonify({"success": True})


@locations_bp.route("/api/locations/<location_id>/photos", methods=["POST"])
@require_auth
def add_location_photo(location_id):
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400
    blob = file.read()
    try:
        photo = svc.add_photo(get_user_id(), location_id, blob, file.mimetype,
                              caption=request.args.get("caption"))
    except svc.NotOwner:
        return jsonify({"error": "Location not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"photo": photo}), 201


@locations_bp.route("/api/locations/<location_id>/photos/<photo_id>", methods=["DELETE"])
@require_auth
def delete_location_photo(location_id, photo_id):
    try:
        outcome = svc.delete_photo(get_user_id(), location_id, photo_id)
    except svc.NotOwner:
        return jsonify({"error": "Location not found"}), 404
    if outcome == "not_found":
        return jsonify({"error": "Photo not found"}), 404
    return jsonify({"success": True})


@locations_bp.route("/api/locations/geocode", methods=["POST"])
@require_auth
def geocode_address():
    data = request.get_json(silent=True) or {}
    hit = geocode_service.geocode(data.get("address"))
    return jsonify(hit or {"lat": None, "lng": None})
```

- [ ] **Step 4: Register in `app.py`**

Near `from routes.contact_routes import contacts_bp` (line ~25):
```python
from routes.location_routes import locations_bp
```
Near `app.register_blueprint(contacts_bp)` (line ~70):
```python
app.register_blueprint(locations_bp)  # Account-level locations directory at /api/locations/*
```

- [ ] **Step 5: Run to verify pass**

Run: `cd backend && pytest tests/test_location_routes.py -v && python -c "import app" && pytest tests/ -q`
Expected: PASS; app imports; no regressions.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/location_routes.py backend/app.py backend/tests/test_location_routes.py
git commit -m "feat(locations): locations_bp directory routes + register blueprint"
```

---

## Task 6: `production_location_service.py` + `from_production_location_id` resolver

**Files:**
- Create: `backend/services/production_location_service.py`
- Modify: `backend/middleware/production_authz.py` (add resolver)
- Test: `backend/tests/test_production_location_routes.py` (service-level tests in this task; route tests in Task 7)

**Interfaces:**
- Consumes: `get_supabase_admin`.
- Produces:
  - `list_for_production(production_id) -> list[dict]` — each `{link_id, location_id, production_notes, name, address, lat, lng, geocode_status, permit_status, parking_notes, loadin_notes, restrictions, primary_contact_name}`
  - `link_location(production_id, location_id, owner_id, notes=None) -> dict | "not_owned" | "exists"`
  - `update_link(link_id, notes) -> dict | "not_found"`
  - `unlink(production_id, link_id) -> "ok" | "not_found"`
- `production_authz.from_production_location_id(kwargs) -> production_id | None` (looks up `production_locations` by `kwargs["link_id"]`).

- [ ] **Step 1: Write failing service tests**

```python
# backend/tests/test_production_location_routes.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
import pytest
import services.production_location_service as pls
from tests.test_location_service import FakeSupabase  # reuse the fake


@pytest.fixture
def fake(monkeypatch):
    fs = FakeSupabase()
    monkeypatch.setattr(pls, "get_supabase_admin", lambda: fs)
    return fs


def _seed_location(fake, owner="owner1", lid="loc1"):
    fake.store.setdefault("locations", []).append(
        {"id": lid, "owner_id": owner, "name": "Stage 6", "address": "1 Main"})


def test_link_rejects_location_not_owned_by_production_owner(fake):
    _seed_location(fake, owner="someone_else")
    assert pls.link_location("p1", "loc1", owner_id="owner1") == "not_owned"


def test_link_creates_row(fake):
    _seed_location(fake)
    out = pls.link_location("p1", "loc1", owner_id="owner1", notes="week 2")
    assert out["production_id"] == "p1" and out["production_notes"] == "week 2"


def test_link_duplicate_returns_exists(fake):
    _seed_location(fake)
    pls.link_location("p1", "loc1", owner_id="owner1")
    assert pls.link_location("p1", "loc1", owner_id="owner1") == "exists"


def test_list_for_production_embeds_location_fields(fake):
    _seed_location(fake)
    pls.link_location("p1", "loc1", owner_id="owner1", notes="n")
    rows = pls.list_for_production("p1")
    assert rows[0]["name"] == "Stage 6" and rows[0]["production_notes"] == "n"


def test_unlink(fake):
    _seed_location(fake)
    link = pls.link_location("p1", "loc1", owner_id="owner1")
    assert pls.unlink("p1", link["id"]) == "ok"
    assert pls.list_for_production("p1") == []
    assert pls.unlink("p1", link["id"]) == "not_found"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_production_location_routes.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the service**

```python
# backend/services/production_location_service.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
"""Per-production location links. Production-authz scoped at the route layer;
this module trusts its caller has already passed require_production_role."""
from db.supabase_client import get_supabase_admin

_LOC_FIELDS = ("name", "address", "lat", "lng", "geocode_status", "permit_status",
               "parking_notes", "loadin_notes", "restrictions", "primary_contact_id")


def _location_owned_by(supabase, location_id, owner_id):
    res = (supabase.table("locations").select("*")
           .eq("id", location_id).eq("owner_id", owner_id).limit(1).execute())
    return res.data[0] if res.data else None


def link_location(production_id, location_id, owner_id, notes=None):
    supabase = get_supabase_admin()
    if not _location_owned_by(supabase, location_id, owner_id):
        return "not_owned"
    dup = (supabase.table("production_locations").select("id")
           .eq("production_id", production_id).eq("location_id", location_id)
           .limit(1).execute())
    if dup.data:
        return "exists"
    row = {"production_id": production_id, "location_id": location_id,
           "production_notes": notes}
    return supabase.table("production_locations").insert(row).execute().data[0]


def _link(supabase, link_id):
    res = (supabase.table("production_locations").select("*")
           .eq("id", link_id).limit(1).execute())
    return res.data[0] if res.data else None


def update_link(link_id, notes):
    supabase = get_supabase_admin()
    if not _link(supabase, link_id):
        return "not_found"
    res = (supabase.table("production_locations").update({"production_notes": notes})
           .eq("id", link_id).execute())
    return res.data[0] if res.data else "not_found"


def unlink(production_id, link_id):
    supabase = get_supabase_admin()
    row = _link(supabase, link_id)
    if not row or row.get("production_id") != production_id:
        return "not_found"
    supabase.table("production_locations").delete().eq("id", link_id).execute()
    return "ok"


def list_for_production(production_id):
    supabase = get_supabase_admin()
    links = (supabase.table("production_locations").select("*")
             .eq("production_id", production_id).execute().data or [])
    if not links:
        return []
    loc_ids = list({l["location_id"] for l in links})
    locs = {l["id"]: l for l in (supabase.table("locations").select("*")
            .in_("id", loc_ids).execute().data or [])}
    contact_ids = [l.get("primary_contact_id") for l in locs.values() if l.get("primary_contact_id")]
    contacts = {}
    if contact_ids:
        contacts = {c["id"]: c for c in (supabase.table("contacts").select("id, name")
                    .in_("id", contact_ids).execute().data or [])}
    out = []
    for link in links:
        loc = locs.get(link["location_id"], {})
        row = {"link_id": link["id"], "location_id": link["location_id"],
               "production_notes": link.get("production_notes")}
        for f in _LOC_FIELDS:
            row[f] = loc.get(f)
        pc = loc.get("primary_contact_id")
        row["primary_contact_name"] = contacts.get(pc, {}).get("name") if pc else None
        out.append(row)
    return out
```

- [ ] **Step 4: Add the resolver to `production_authz.py`**

After `from_production_invite_id` (line ~99):
```python
def from_production_location_id(kwargs):
    return _lookup_production_id('production_locations', kwargs.get('link_id'))
```

- [ ] **Step 5: Run to verify pass**

Run: `cd backend && pytest tests/test_production_location_routes.py tests/test_production_authz.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/production_location_service.py backend/middleware/production_authz.py backend/tests/test_production_location_routes.py
git commit -m "feat(locations): production_location_service + from_production_location_id resolver"
```

---

## Task 7: Production location-link routes on `production_bp`

**Files:**
- Modify: `backend/routes/production_routes.py`
- Modify: `backend/tests/test_route_enforcement.py`
- Test: `backend/tests/test_production_location_routes.py` (append route tests)

**Interfaces:**
- Consumes: `production_location_service` (Task 6), `require_production_role`, `from_production_location_id`, `from_production_id`, `g.production_access`, `g.resolved_production_id`.
- Produces routes:
  - `GET /api/productions/<production_id>/locations` — `min_role="viewer"` → `{"locations": [...]}`
  - `POST /api/productions/<production_id>/locations` — `capability="can_edit_production"`, body `{location_id, production_notes}` → `{"location": {...}}` 201 / 400 / 404 `not_owned` / 409 `exists`
  - `PATCH /api/productions/<production_id>/locations/<link_id>` — `capability="can_edit_production"`, resolver `from_production_location_id`, body `{production_notes}` → `{"location": {...}}` / 404
  - `DELETE /api/productions/<production_id>/locations/<link_id>` — `capability="can_edit_production"`, resolver `from_production_location_id` → `{"success": true}` / 404

- [ ] **Step 1: Write failing route tests (append to `test_production_location_routes.py`)**

```python
# --- route-layer tests (mirror test_production_crew_routes.py's client setup) ---
from unittest.mock import patch
import services.production_location_service as plsvc


def test_list_requires_viewer(prod_client_non_member):
    assert prod_client_non_member.get("/api/productions/p1/locations").status_code == 403


def test_viewer_cannot_link(prod_client_viewer):
    r = prod_client_viewer.post("/api/productions/p1/locations",
                                json={"location_id": "loc1"})
    assert r.status_code == 403


def test_admin_links_location(prod_client_admin):
    with patch.object(plsvc, "link_location", return_value={"id": "pl1", "production_id": "p1"}):
        r = prod_client_admin.post("/api/productions/p1/locations",
                                   json={"location_id": "loc1", "production_notes": "n"})
    assert r.status_code == 201


def test_link_not_owned_is_404(prod_client_admin):
    with patch.object(plsvc, "link_location", return_value="not_owned"):
        r = prod_client_admin.post("/api/productions/p1/locations", json={"location_id": "x"})
    assert r.status_code == 404


def test_link_duplicate_is_409(prod_client_admin):
    with patch.object(plsvc, "link_location", return_value="exists"):
        r = prod_client_admin.post("/api/productions/p1/locations", json={"location_id": "loc1"})
    assert r.status_code == 409


def test_post_requires_location_id(prod_client_admin):
    assert prod_client_admin.post("/api/productions/p1/locations", json={}).status_code == 400
```

> Use whatever member-role client fixtures `test_production_crew_routes.py` / `test_production_member_routes.py` already define (`prod_client_admin`, `prod_client_viewer`, `prod_client_non_member` or equivalent). If they are local to those files, lift the fixture setup into a shared `conftest.py` or copy it into this file — match the existing approach in the repo.

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_production_location_routes.py -v`
Expected: FAIL — routes 404.

- [ ] **Step 3: Implement the routes**

Add near the crew routes in `production_routes.py` (after `remove_production_crew`, before the members section). Add `from_production_location_id` to the `production_authz` import line, and `from services import production_location_service as ploc_svc`.

```python
@production_bp.route("/api/productions/<production_id>/locations", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer")
def list_production_locations(production_id):
    return jsonify({"locations": ploc_svc.list_for_production(production_id)})


@production_bp.route("/api/productions/<production_id>/locations", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_production")
def link_production_location(production_id):
    data = request.get_json(silent=True) or {}
    location_id = (data.get("location_id") or "").strip()
    if not location_id:
        return jsonify({"error": "location_id is required"}), 400
    owner_id = svc.get_production_owner_id(production_id)  # see note below
    result = ploc_svc.link_location(production_id, location_id, owner_id,
                                    notes=data.get("production_notes"))
    if result == "not_owned":
        return jsonify({"error": "That location is not in this production owner's directory"}), 404
    if result == "exists":
        return jsonify({"error": "That location is already linked to this production"}), 409
    return jsonify({"location": result}), 201


@production_bp.route("/api/productions/<production_id>/locations/<link_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_edit_production", resolver=from_production_location_id)
def update_production_location(production_id, link_id):
    data = request.get_json(silent=True) or {}
    result = ploc_svc.update_link(link_id, data.get("production_notes"))
    if result == "not_found":
        return jsonify({"error": "Not found"}), 404
    return jsonify({"location": result})


@production_bp.route("/api/productions/<production_id>/locations/<link_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_edit_production", resolver=from_production_location_id)
def unlink_production_location(production_id, link_id):
    if ploc_svc.unlink(production_id, link_id) == "not_found":
        return jsonify({"error": "Not found"}), 404
    return jsonify({"success": True})
```

> **Owner-id lookup:** `production_crew` routes get the owner via `crew_svc._production_owner_id(supabase, production_id)`. Reuse the same helper — either import it, or add a small public `production_service.get_production_owner_id(production_id)` and use it in both places (prefer the latter; leave crew's private helper delegating to it). Pick whichever keeps the diff smallest and note the choice in the commit.

- [ ] **Step 4: Extend `test_route_enforcement.py`**

The `test_production_scoped_routes_carry_authz_marker` test iterates `production_bp` routes. The 3 new writable routes + the GET already carry `_authz_min_role` / `_authz_capability`, so they pass automatically. Confirm none of the new endpoint names are in the "intentionally NOT scoped" allow-lists; if the test enumerates expected endpoints explicitly, add `production.list_production_locations`, `production.link_production_location`, `production.update_production_location`, `production.unlink_production_location` to the scoped set. Run the test to confirm.

- [ ] **Step 5: Run to verify pass**

Run: `cd backend && pytest tests/test_production_location_routes.py tests/test_route_enforcement.py -v && pytest tests/ -q`
Expected: PASS; full suite green.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/production_routes.py backend/services/production_service.py backend/services/production_crew_service.py backend/tests/
git commit -m "feat(locations): production location-link routes gated on can_edit_production"
```

---

## Task 8: `MAPBOX_SECRET_TOKEN` in env validator

**Files:**
- Modify: `backend/utils/env_validator.py`
- Test: `backend/tests/test_env_validator.py` (if it exists; otherwise skip the test step)

**Interfaces:**
- Produces: `MAPBOX_SECRET_TOKEN` listed in `RECOMMENDED_VARS` (NOT `REQUIRED_VARS`).

- [ ] **Step 1: (If `test_env_validator.py` exists) add a test**

```python
def test_mapbox_token_is_recommended_not_required():
    from utils.env_validator import RECOMMENDED_VARS, REQUIRED_VARS
    assert "MAPBOX_SECRET_TOKEN" in RECOMMENDED_VARS
    assert "MAPBOX_SECRET_TOKEN" not in REQUIRED_VARS
```

- [ ] **Step 2: Run to verify failure** (or confirm no test file — then just do Step 3)

Run: `cd backend && pytest tests/test_env_validator.py -v`
Expected: FAIL on the new test, or "no such file" (skip to Step 3).

- [ ] **Step 3: Implement**

In `RECOMMENDED_VARS`:
```python
    'MAPBOX_SECRET_TOKEN': 'Mapbox secret token for server-side address geocoding (locations directory); geocoding degrades to manual lat/lng entry when absent',
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && pytest tests/ -q && python -c "import app"`
Expected: PASS; app boots (var is only recommended, so no failure when unset).

- [ ] **Step 5: Commit**

```bash
git add backend/utils/env_validator.py backend/tests/
git commit -m "feat(locations): MAPBOX_SECRET_TOKEN as a recommended env var"
```

---

## Task 9: `apiService.js` — locations client functions

**Files:**
- Modify: `frontend/src/services/apiService.js`

**Interfaces:**
- Produces (all `async`, throwing on error, mirroring the contacts block at line ~2516):
  - `listLocations({ q } = {}) -> {locations}`
  - `createLocation(payload) -> {location}`
  - `getLocation(id) -> {location, photos, used_in}`
  - `updateLocation(id, payload) -> {location}`
  - `deleteLocation(id) -> {success}` (surfaces 409 body via thrown error's `response.data.used_in`)
  - `uploadLocationPhoto(id, file, caption) -> {photo}` (multipart)
  - `deleteLocationPhoto(id, photoId) -> {success}`
  - `geocodeAddress(address) -> {lat, lng}`
  - `listProductionLocations(productionId) -> {locations}`
  - `linkProductionLocation(productionId, { location_id, production_notes }) -> {location}`
  - `updateProductionLocation(productionId, linkId, { production_notes }) -> {location}`
  - `unlinkProductionLocation(productionId, linkId) -> {success}`

- [ ] **Step 1: Add the functions block**

After the contacts/crew block (locate the `// Contacts directory + production crew (build-sequence step 2a)` section and its end), add:

```javascript
// ---------------------------------------------------------------------------
// Locations directory + production locations (build-sequence step 3)
// ---------------------------------------------------------------------------

/** List the current user's locations. @param {{q?: string}} params */
export const listLocations = async (params = {}) => {
    const response = await api.get('/api/locations', { params });
    return response.data;
};

export const createLocation = async (payload) => {
    const response = await api.post('/api/locations', payload);
    return response.data;
};

export const getLocation = async (id) => {
    const response = await api.get(`/api/locations/${id}`);
    return response.data;
};

export const updateLocation = async (id, payload) => {
    const response = await api.patch(`/api/locations/${id}`, payload);
    return response.data;
};

export const deleteLocation = async (id) => {
    const response = await api.delete(`/api/locations/${id}`);
    return response.data;
};

export const uploadLocationPhoto = async (id, file, caption) => {
    const form = new FormData();
    form.append('file', file);
    const response = await api.post(`/api/locations/${id}/photos`, form, {
        params: caption ? { caption } : undefined,
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const deleteLocationPhoto = async (id, photoId) => {
    const response = await api.delete(`/api/locations/${id}/photos/${photoId}`);
    return response.data;
};

export const geocodeAddress = async (address) => {
    const response = await api.post('/api/locations/geocode', { address });
    return response.data;
};

export const listProductionLocations = async (productionId) => {
    const response = await api.get(`/api/productions/${productionId}/locations`);
    return response.data;
};

export const linkProductionLocation = async (productionId, payload) => {
    const response = await api.post(`/api/productions/${productionId}/locations`, payload);
    return response.data;
};

export const updateProductionLocation = async (productionId, linkId, payload) => {
    const response = await api.patch(`/api/productions/${productionId}/locations/${linkId}`, payload);
    return response.data;
};

export const unlinkProductionLocation = async (productionId, linkId) => {
    const response = await api.delete(`/api/productions/${productionId}/locations/${linkId}`);
    return response.data;
};
```

> Match the exact error-handling idiom used by the adjacent contacts functions — if they wrap in `try/catch` + `console.error` + rethrow, do the same; if they are bare (as the newer ones above appear), keep them bare. Consistency with the immediate neighbours wins.

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(locations): apiService client functions for locations + production links"
```

---

## Task 10: `StaticMap` component + `LocationFormModal`

**Files:**
- Create: `frontend/src/components/locations/StaticMap.jsx`
- Create: `frontend/src/components/locations/LocationFormModal.jsx`

**Interfaces:**
- `StaticMap({ lat, lng, geocodeStatus, height })` — renders an `<img>` from the Mapbox Static Images API when `lat`, `lng`, and `import.meta.env.VITE_MAPBOX_PUBLIC_TOKEN` are all present; otherwise a placeholder `<div>` whose text is keyed off `geocodeStatus` (`'failed'` → "Address couldn't be located", else → "Add coordinates to show a map"). No token → "Map preview unavailable".
- `LocationFormModal({ initial, contacts, onSave, onClose, saving })` — controlled form over `name` (required), `address`, `lat`, `lng`, `primary_contact_id` (`<select>` from `contacts`), `permit_status`, `parking_notes`, `loadin_notes`, `restrictions`, `notes`, plus a "Locate" button calling `geocodeAddress`. `onSave(payload)` — payload includes `lat`/`lng` only when the user set/changed them (so the backend's manual-vs-geocode branch fires correctly).

- [ ] **Step 1: Write `StaticMap.jsx`**

```jsx
// frontend/src/components/locations/StaticMap.jsx
const TOKEN = import.meta.env.VITE_MAPBOX_PUBLIC_TOKEN;

export default function StaticMap({ lat, lng, geocodeStatus, height = 240 }) {
    const hasCoords = lat != null && lng != null && lat !== '' && lng !== '';
    if (!TOKEN) {
        return <div className="static-map static-map--empty" style={{ height }}>Map preview unavailable</div>;
    }
    if (!hasCoords) {
        const msg = geocodeStatus === 'failed'
            ? "Address couldn't be located — add coordinates manually"
            : 'Add an address or coordinates to show a map';
        return <div className="static-map static-map--empty" style={{ height }}>{msg}</div>;
    }
    const src = `https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/`
        + `pin-s+e11d48(${lng},${lat})/${lng},${lat},13/640x${height}@2x`
        + `?access_token=${TOKEN}`;
    return <img className="static-map" src={src} alt="Location map" style={{ height, width: '100%', objectFit: 'cover' }} />;
}
```

- [ ] **Step 2: Write `LocationFormModal.jsx`**

Model it on `frontend/src/components/contacts/ContactFormModal.jsx` (same modal chrome, same `blankFromInitial` pattern, same save/close button layout). Key differences:
- Fields listed above (no `kind`, no `role_tags`, no `rate_unit`).
- `primary_contact_id` is a `<select>`: `<option value="">— none —</option>` then `contacts.map(c => <option value={c.id}>{c.name}</option>)`.
- A "Locate" button next to the address input:
  ```jsx
  const [locating, setLocating] = useState(false);
  const locate = async () => {
      setLocating(true);
      try {
          const { lat, lng } = await geocodeAddress(form.address);
          if (lat != null) setForm(f => ({ ...f, lat, lng, _coordsTouched: true }));
      } finally { setLocating(false); }
  };
  ```
- Track `_coordsTouched` — set it `true` when the user edits `lat`/`lng` directly or clicks Locate. On submit, build the payload; include `lat`/`lng` keys **only if `_coordsTouched`** (or if editing and they already had values that changed).
- Import `geocodeAddress` from `../../services/apiService`.

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: PASS (components compile; not yet routed).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/locations/
git commit -m "feat(locations): StaticMap + LocationFormModal components"
```

---

## Task 11: `LocationDetailDrawer` + `LocationsListPage` + route + nav

**Files:**
- Create: `frontend/src/components/locations/LocationDetailDrawer.jsx`
- Create: `frontend/src/pages/LocationsListPage.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/layout/TopBar.jsx`

**Interfaces:**
- `LocationDetailDrawer({ locationId, onClose, onChanged })` — fetches `getLocation(locationId)`; renders all fields, `<StaticMap>`, a photo gallery (thumbnails from `photos[].url`, upload input → `uploadLocationPhoto`, delete → `deleteLocationPhoto`), the primary-contact name, `used_in` productions list, Edit (opens `LocationFormModal` → `updateLocation`) and Delete (`deleteLocation`; on 409 show `err.response.data.used_in` names and block).
- `LocationsListPage` — clone of `ContactsListPage.jsx`: search box, "Add location" button (opens `LocationFormModal` with `initial=null` → `createLocation`), list rows (name + address + small `<StaticMap height={64}>` thumb), row click → `LocationDetailDrawer`.

- [ ] **Step 1: Build `LocationDetailDrawer.jsx`**

Model on `frontend/src/components/contacts/ContactDetailDrawer.jsx`. Add the photo-gallery block (model on `frontend/src/components/casting/` photo UI if one exists; otherwise a simple `<input type="file" accept="image/*">` + thumbnail grid with a × delete button per photo). Fetch `contacts` via `listContacts()` to populate the edit modal's `contacts` prop.

- [ ] **Step 2: Build `LocationsListPage.jsx`**

Copy `ContactsListPage.jsx` structure verbatim, swap:
- imports → `listLocations, createLocation` + `LocationFormModal` + `LocationDetailDrawer`
- `import { MapPin, Plus } from 'lucide-react'`
- state: drop `kindFilter`
- `load()` → `listLocations({ q })`, `setLocations(data.locations || [])`
- `PageHeader` title "Locations", icon `<MapPin>`
- render `LocationFormModal` needs `contacts` — fetch once on mount via `listContacts()` and hold in state; pass down.

- [ ] **Step 3: Route in `App.jsx`**

Add import near `ContactsListPage` (line ~52):
```jsx
import LocationsListPage from './pages/LocationsListPage';
```
Add route after the `contacts` route (line ~87):
```jsx
<Route path="locations" element={<LocationsListPage />} />
```

- [ ] **Step 4: Nav link in `TopBar.jsx`**

After the `/contacts` `NavLink` block (line ~95-100), add:
```jsx
          <NavLink
            to="/locations"
            className={({ isActive }) => `topbar-nav-item ${isActive ? 'active' : ''}`}
          >
            <MapPin size={18} />
            <span>Locations</span>
          </NavLink>
```
Add `MapPin` to the existing `lucide-react` import in `TopBar.jsx`.

- [ ] **Step 5: Verify build + manual smoke**

Run: `cd frontend && npm run build`
Expected: PASS. Then `npm run dev`, visit `/locations`, confirm: add a location, see it listed, open the drawer, edit it, add a photo, try to delete (should work with no links). If `VITE_MAPBOX_PUBLIC_TOKEN` is unset the map shows the placeholder — that's correct.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/LocationsListPage.jsx frontend/src/components/locations/ frontend/src/App.jsx frontend/src/components/layout/TopBar.jsx
git commit -m "feat(locations): /locations directory page + nav link + detail drawer"
```

---

## Task 12: `ProductionLocationsTab` + `LocationPickerModal` + wire into `ProductionDetailPage`

**Files:**
- Create: `frontend/src/components/productions/ProductionLocationsTab.jsx`
- Create: `frontend/src/components/productions/LocationPickerModal.jsx`
- Modify: `frontend/src/pages/ProductionDetailPage.jsx`

**Interfaces:**
- `ProductionLocationsTab({ productionId, access })` — `listProductionLocations`; table of linked locations (name, address, `<StaticMap height={48}>` thumb, `production_notes` editable inline, `primary_contact_name`). Write controls gated on `access?.can_edit_production`: "Link a location" button (opens `LocationPickerModal`), inline notes edit → `updateProductionLocation`, unlink button → `unlinkProductionLocation`.
- `LocationPickerModal({ onPick, onClose, excludeIds })` — `listLocations()` (owner's directory), searchable list, excludes already-linked `location_id`s, `onPick(locationId, notes)` → caller calls `linkProductionLocation`.

- [ ] **Step 1: Build `LocationPickerModal.jsx`**

Model on `frontend/src/components/productions/ProductionScriptPicker.jsx` or `CrewAssignmentModal.jsx`'s contact-picker portion. Simple: fetch `listLocations()`, filter by a search box and `excludeIds`, each row a button calling `onPick(loc.id)`. Optional notes textarea.

- [ ] **Step 2: Build `ProductionLocationsTab.jsx`**

Model closely on `frontend/src/components/productions/ProductionCrewTab.jsx` (same `{ productionId, access }` signature, same `loading`/`error`/`load` pattern, same `canEdit = access?.can_edit_production`). Render the linked-locations table; gate the add/edit/unlink controls on `canEdit`. On link: `await linkProductionLocation(productionId, { location_id, production_notes }); load();` — catch 409/404 and show `err.response?.data?.error` in the error banner.

- [ ] **Step 3: Wire the tab into `ProductionDetailPage.jsx`**

- Import: `import ProductionLocationsTab from '../components/productions/ProductionLocationsTab';`
- In the `tabs` array build (line ~114-116), after the crew push:
  ```jsx
  if (isMember) tabs.push({ id: 'locations', label: 'Locations' });
  ```
- In the reset `useEffect` (line ~61-62):
  ```jsx
  if (activeTab === 'locations' && !isMember) setActiveTab('overview');
  ```
- In the render section (after the crew tab block, line ~152-154):
  ```jsx
  {activeTab === 'locations' && isMember && (
      <ProductionLocationsTab productionId={productionId} access={access} />
  )}
  ```

- [ ] **Step 4: Verify build + manual smoke**

Run: `cd frontend && npm run build`
Expected: PASS. Then `npm run dev` as the owner: open a production, click Locations, link a location from the directory, add production notes, unlink it.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/productions/ProductionLocationsTab.jsx frontend/src/components/productions/LocationPickerModal.jsx frontend/src/pages/ProductionDetailPage.jsx
git commit -m "feat(locations): Locations tab on ProductionDetailPage + location picker"
```

---

## Task 13: Full-stack verification + docs

**Files:**
- Modify: `docs/BACKLOG.md`
- Modify: `docs/SLATEONE_FEATURES.md` (add a Locations section)

- [ ] **Step 1: Backend suite**

Run: `cd backend && pytest tests/ -q`
Expected: all green (baseline was 672 passed / 1 skipped at 2b; this slice adds ~35 tests).

- [ ] **Step 2: Frontend build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 3: End-to-end manual check (dev server, `FLASK_ENV=development`)**

Apply migration 053 to a local/staging Supabase first (or the dev project). Then:
1. `/locations` → add "Cape Town City Hall", address "Darling St, Cape Town" → click Locate (needs `MAPBOX_SECRET_TOKEN` on the backend; if absent, enter lat/lng manually: `-33.925, 18.423`).
2. Map preview renders (needs `VITE_MAPBOX_PUBLIC_TOKEN`; else placeholder).
3. Add a photo; delete it.
4. Set a primary contact from the dropdown.
5. Open a production → Locations tab → Link the city-hall location → add note "Council chamber, day 3" → confirm it appears with the map thumb and contact name.
6. Unlink it. Back on `/locations`, delete the location (should succeed now it's unlinked). Re-link, then try to delete → expect the 409 "linked to productions" block.
7. As a non-owner `coordinator` member with `can_edit_production`: Locations tab visible, can link/unlink. As a `viewer`: tab visible, read-only. `/locations` nav entry absent for both.

- [ ] **Step 4: Update `docs/BACKLOG.md`**

Replace the step-3 START HERE block: mark step 3 shipped (branch, commit range), move START HERE to **step 4: call sheets / sides**. Note migration 053 applied + the two Mapbox env vars set (or still pending). Drop item 9-cluster additions if a locations UI/UX pass is wanted → add "9f. Locations pages UI/UX pass (directory + tab + map/photo UI shipped functional, no design pass)".

- [ ] **Step 5: Update `docs/SLATEONE_FEATURES.md`**

Add a "Locations" subsection under the production-management area: account-level reusable directory, per-production links with notes, reference photos, Mapbox map preview, owner-only directory / member-visible via the production tab.

- [ ] **Step 6: Commit**

```bash
git add docs/BACKLOG.md docs/SLATEONE_FEATURES.md
git commit -m "docs(locations): step 3 shipped; features + backlog updated"
```

- [ ] **Step 7: Whole-branch review + finish**

Invoke `superpowers:requesting-code-review` for the full branch diff, address findings, then `superpowers:finishing-a-development-branch`.

---

## Self-Review

**1. Spec coverage:**
- Migration `053_locations.sql` (3 tables) → Task 1 ✓
- `013_delete_user_safely` note → Task 1 Step 2 ✓
- `geocode_service` (Mapbox, degrades) → Task 2 ✓
- `location_service` directory CRUD + geocode-on-write (4 branches) → Task 3 ✓
- Delete-guard 409 `in_use` → Task 3 (`test_delete_blocked_when_linked`) + Task 5 (route 409) ✓
- `location_photos` (casting-photos pattern) → Task 4 ✓
- `locations_bp` routes incl. `/geocode` → Task 5 ✓
- `production_location_service` + `from_production_location_id` → Task 6 ✓
- Production link routes gated by `can_edit_production` → Task 7 ✓
- `require_production_role` viewer-read / capability-write → Task 7 ✓
- Can't link a location not owned by the production owner → Task 6 (`not_owned`) + Task 7 (404) ✓
- `test_route_enforcement` extension → Task 7 Step 4 ✓
- `MAPBOX_SECRET_TOKEN` recommended-not-required → Task 8 ✓
- `apiService` functions → Task 9 ✓
- `/locations` page + nav (owner-only) → Task 11 ✓
- `StaticMap` `<img>` keyed on coords + token → Task 10 ✓
- `LocationFormModal` with Locate button → Task 10 ✓
- Photo gallery UI → Task 11 ✓
- Locations tab on `ProductionDetailPage` (viewer sees, `can_edit_production` edits) → Task 12 ✓
- `LocationPickerModal` over owner's directory → Task 12 ✓
- Non-owner member: no `/locations` nav, tab-only visibility → Tasks 11 (nav gated) + 12 (tab `isMember`) + verified Task 13 Step 3.7 ✓
- No `can_view_sensitive` on location fields; primary contact stays gated → not-a-change, noted in Global Constraints ✓
- Deploy notes (apply 053, set tokens, no backfill) → Task 1 Step 5 + Task 13 ✓

**2. Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N". Frontend Tasks 10-12 point at specific existing files to model on and give the non-obvious snippets (geocode/coords-touched logic, tab wiring, StaticMap URL) inline; the mechanical modal/list chrome is "copy file X and swap these named things", which is a concrete instruction, not a placeholder.

**3. Type consistency:**
- `NOT_FOUND` sentinel — `location_service` (Task 3) and referenced in routes (Task 5) consistently.
- `NotOwner` exception — defined Task 4, caught in routes Task 5. ✓
- Photo serialization keys `{id, caption, sort_order, url}` — Task 3 `_serialize_photo`, consumed Task 4 tests + Task 11 UI. ✓
- `link_location(production_id, location_id, owner_id, notes=None)` — Task 6 def, Task 7 call site match. ✓
- Return sentinels `"not_owned"` / `"exists"` / `"not_found"` / `"ok"` — Task 6 produces, Task 7 maps to 404/409/404/200. ✓
- `list_for_production` row keys (`link_id`, `location_id`, `production_notes`, `name`, ...) — Task 6 produces, Task 12 UI consumes; `link_id` (not `id`) is the link identifier used by PATCH/DELETE routes (`<link_id>` param → `from_production_location_id` resolver). ✓
- `from_production_location_id` reads `kwargs["link_id"]` — matches the route param name `<link_id>` in Task 7. ✓
- apiService names (Task 9) match component call sites (Tasks 10-12): `geocodeAddress`, `linkProductionLocation`, `unlinkProductionLocation`, `updateProductionLocation`, `listProductionLocations`. ✓

All consistent.
