# Locations Directory — Build-Sequence Step 3 Design

**Date:** 2026-09-02
**Status:** Design approved — ready for implementation plan
**Type:** Architectural
**Parent:** `docs/superpowers/specs/2026-08-31-production-data-model-design.md`
(umbrella direction spec — build-sequence step 3)
**Siblings:** `2026-08-31-crew-contacts-design.md` (step 2a),
`2026-09-01-production-members-design.md` (step 2b, shipped `8477e82`)

## Purpose

Give the account a reusable directory of real-world shooting locations and
give each production a list of the locations it uses, with
production-specific notes and reference photos. This is the location
half of the umbrella spec's address book — the direct parallel of the
`contacts` / `production_crew` pair shipped in step 2a.

A stage, a farm, a city-hall interior is used across many of a production
company's projects. `locations` is the canonical record (edit the address
once, it updates everywhere); `production_locations` links a location to a
production with notes scoped to that shoot.

## Scope

**In:**

- Migration `053_locations.sql` (applied manually to the Supabase project —
  `run_migration.py` is dead, per the casting/contacts migration notes):
  `locations`, `production_locations`, `location_photos` tables.
- New blueprint `locations_bp` (`routes/location_routes.py` +
  `services/location_service.py`) — account-level directory CRUD, owner-only.
- New `services/geocode_service.py` — thin server-side Mapbox geocoding
  wrapper, degrades to `None` on any error/missing key.
- Production location-link routes added to the existing `production_bp`,
  backed by a new `services/production_location_service.py`, gated by
  `require_production_role` + the existing `can_edit_production` capability.
- Location photo upload/delete following the `casting_photos` pattern
  (Supabase `scripts` bucket).
- Frontend: `/locations` directory page + nav link (owner-only); a
  **Locations** tab on `ProductionDetailPage`.
- Mapbox static-map preview (`<img>`) rendered client-side from `lat`/`lng`.

**Out (named, deferred):**

- The scene-`setting` → real-`location` creative mapping (aliases,
  sub-locations, canonical set names) → its own brainstorm ("Separate
  Location (production element) from Sets (creative)"). This spec only
  reserves that `locations` is where it will attach. The existing
  `services/location_resolver.py` / `location_quality.py` are that
  *creative* resolver and are **untouched** here.
- Contact photos → not in this slice; add when asked, reusing this slice's
  photo pattern.
- CSV / XLSX import for locations → fast-follow if asked; the umbrella spec
  scoped CSV import to `contacts` + `production_crew` specifically.
- AI-parse of an uploaded call sheet / production book PDF → deferred
  (umbrella spec; needs real sample docs).
- `default_call_offset` and any call-sheet operational fields → step 4.
- Address geocoding via a free provider (Nominatim) — rejected in the
  brainstorm in favour of Mapbox.
- A `can_edit_locations` capability flag — rejected; reuse
  `can_edit_production`.
- `can_view_sensitive` gating on location fields — nothing on `locations`
  is sensitive. The primary contact's phone/rate stays gated by the
  existing `contacts` sensitive-field logic wherever the contact surfaces.

## Data model

Migration `backend/db/migrations/053_locations.sql`. Mirrors the
`051_contacts_crew.sql` conventions: `gen_random_uuid()` pks, manual apply,
`update_shooting_updated_at()` trigger reuse (from migration 030),
owner-only RLS as a direct-client backstop only (real enforcement is
app-layer — the backend uses the service-role key).

### `locations` — account-level directory

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `owner_id` | uuid not null | `REFERENCES profiles(id) ON DELETE CASCADE`. Matches `contacts.owner_id` / `productions.owner_id`. The cascade is load-bearing for `013_delete_user_safely.sql` (deletes `scripts` then `profiles`); carry a comment saying so. |
| `name` | text not null | e.g. "Cape Town City Hall — Council Chamber" |
| `address` | text null | free text |
| `lat` | numeric null | set by geocoding or manual entry |
| `lng` | numeric null | set by geocoding or manual entry |
| `geocode_status` | text null | `CHECK (geocode_status IS NULL OR geocode_status IN ('ok','failed','manual'))`. `'ok'` = auto-geocoded, `'failed'` = geocode attempted and failed, `'manual'` = coords hand-entered/edited, `NULL` = never attempted (no address, or no Mapbox key). Lets the UI explain an absent pin. |
| `primary_contact_id` | uuid null | `REFERENCES contacts(id) ON DELETE SET NULL` |
| `permit_status` | text null | free text (e.g. "applied 2026-09-01", "granted") |
| `parking_notes` | text null | |
| `loadin_notes` | text null | |
| `restrictions` | text null | e.g. "no filming after 22:00, no drones" |
| `notes` | text null | |
| `created_by` | uuid null | `REFERENCES auth.users(id) ON DELETE SET NULL` |
| `created_at` | timestamptz not null | `default now()` |
| `updated_at` | timestamptz not null | `default now()`; `BEFORE UPDATE` trigger reusing `update_shooting_updated_at()` |

Indexes:
- `idx_locations_owner ON locations(owner_id)`
- `idx_locations_owner_name ON locations(owner_id, lower(name))`

### `production_locations` — link (production ↔ location)

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `production_id` | uuid not null | `REFERENCES productions(id) ON DELETE CASCADE` |
| `location_id` | uuid not null | `REFERENCES locations(id) ON DELETE CASCADE` |
| `production_notes` | text null | e.g. "week 2 only, north field" |
| `created_at` | timestamptz not null | `default now()` |

Constraints / indexes:
- `UNIQUE (production_id, location_id)` — a location links to a production
  at most once.
- `idx_production_locations_production ON production_locations(production_id)`
- `idx_production_locations_location ON production_locations(location_id)` —
  supports the directory "used in N productions" rollup and the delete-guard.

### `location_photos` — reference images (mirrors `casting_photos`)

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `location_id` | uuid not null | `REFERENCES locations(id) ON DELETE CASCADE` |
| `storage_path` | text not null | Supabase `scripts` bucket (same bucket casting photos use), key prefix `locations/<location_id>/<uuid>` |
| `caption` | text null | |
| `sort_order` | int not null | `default 0` |
| `created_at` | timestamptz not null | `default now()` |

Index: `idx_location_photos_location ON location_photos(location_id)`.

Storage cleanup: deleting a photo row deletes the storage object in the
same request (best-effort, matching the casting-photo delete path). Row
cascade on location delete does **not** clean storage — location delete is
blocked while links exist (below), and an unlinked location with photos is
a rare manual cleanup; a follow-up storage-sweep job is out of scope.

### RLS backstop (all three tables)

Owner-only `SELECT`/`ALL` policies keyed to `owner_id` (directly for
`locations`, via `location_id → locations.owner_id` for `location_photos`,
via `location_id → locations.owner_id` for `production_locations`). This is
a direct-client safety net only; the app never relies on it.

## Delete rules

- **`DELETE /api/locations/<id>`** — if the location is referenced by any
  `production_locations` row → `409` with
  `{"error": "Location is linked to productions", "used_in": [...]}` where
  `used_in` lists `{production_id, title}`. Exactly mirrors `delete_contact`
  / `contact_usage`. Unlink from every production first, then delete.
- Deleting a `location` cascades its `location_photos` rows and
  `production_locations` rows at the DB level, but the app-layer 409 guard
  means the cascade on `production_locations` is only ever exercised by a
  direct-client call, not the API.
- Deleting a `contact` that is a location's `primary_contact_id` → the FK is
  `ON DELETE SET NULL`, so the contact delete-guard in `contact_service`
  does **not** need to know about locations; the location's
  `primary_contact_id` simply nulls. (Confirm `contact_service.delete_contact`
  still succeeds — it only blocks on `production_crew` today.)

## Backend

### `services/location_service.py` (owner-scoped directory)

Copy of `contact_service.py`'s shape.

- `NOT_FOUND = object()` sentinel.
- `FIELDS` whitelist: `name`, `address`, `lat`, `lng`, `geocode_status`,
  `primary_contact_id`, `permit_status`, `parking_notes`, `loadin_notes`,
  `restrictions`, `notes`.
- `list_locations(user_id, q=None)` — `owner_id == user_id`, optional
  substring search on `name` / `address` via `or_(...ilike...)`, stripping
  PostgREST filter metacharacters (`%`, `,`) exactly as `contact_service`
  does. Orders by `name`.
- `create_location(user_id, fields)` / `update_location(user_id, id, fields)`
  — owner-scoped; unknown keys ignored; returns the row or `NOT_FOUND`.
- **Geocode-on-write:** in create and update, if `address` is present/changed
  and the caller did **not** supply explicit `lat`/`lng` in the same call,
  call `geocode_service.geocode(address)`:
  - success → set `lat`, `lng`, `geocode_status='ok'`
  - failure/`None` → leave `lat`/`lng` as-is, set `geocode_status='failed'`
  - If the caller **did** supply `lat`/`lng` → store them, set
    `geocode_status='manual'`, skip geocoding.
  - Address cleared to empty → null `lat`/`lng`, null `geocode_status`.
  Geocoding never blocks the write; a geocode exception is caught and
  treated as failure.
- `get_location_with_usage(user_id, id)` — location row + `photos` (ordered)
  + `used_in` (linked productions `{production_id, title}`) or `NOT_FOUND`.
- `location_usage(user_id, id)` — the `used_in` list alone (for the 409 body).
- `delete_location(user_id, id)` → `"not_found"` | `"in_use"` | success.
- `add_photo(user_id, location_id, file, caption)` /
  `delete_photo(user_id, location_id, photo_id)` — owner-scoped; upload to
  the `scripts` bucket, insert/delete the row, best-effort storage delete.
  Match the casting-photo service helpers.

### `services/geocode_service.py` (new, thin)

- `geocode(address: str) -> dict | None` — returns `{"lat": float, "lng": float}`
  or `None`.
- Provider: **Mapbox Geocoding API v6**
  (`https://api.mapbox.com/search/geocode/v6/forward?q=<address>&limit=1&access_token=<MAPBOX_SECRET_TOKEN>`).
- Reads `MAPBOX_SECRET_TOKEN` from env. Missing key → return `None`
  immediately (no request).
- `requests.get` with a short timeout (5s). Any non-200, empty result,
  network error, timeout, or parse error → return `None`. Never raises.
- No caching table — `location_service` only calls this when `address`
  actually changed, which is the natural rate-limiter for v1.

### `services/production_location_service.py` (per-production links)

- `list_for_production(production_id)` — `production_locations` rows for the
  production, each joined to its `locations` row (name, address, lat, lng,
  geocode_status, primary_contact_id → contact name, permit_status, the
  notes fields) plus `production_notes` and the link `id`.
- `link_location(production_id, location_id, notes, owner_id)` — verifies
  the target `location.owner_id == owner_id` (the production's owner; a
  member with `can_edit_production` cannot link a location that isn't in
  the owner's directory) and that no link already exists (unique constraint
  is the backstop; return a clean `409`/`"exists"` on duplicate). Inserts.
- `update_link(link_id, notes)` — updates `production_notes`.
- `unlink(link_id)` — deletes the link row. No-op semantics: match
  `production_crew_service`'s final ruling (confirm at implementation —
  crew's DELETE-of-missing returns 404; mirror whatever it settled on).

### Routes

**`routes/location_routes.py` → `locations_bp`** (all `@require_auth`,
owner-scoped, no production role — the directory is owner-only exactly like
`/api/contacts`):

| Method + path | Handler | Notes |
|---|---|---|
| `GET /api/locations` | `list_locations` | `?q=` search |
| `POST /api/locations` | `create_location` | `name` required (400 otherwise) |
| `GET /api/locations/<location_id>` | `get_location` | 404 → `NOT_FOUND` |
| `PATCH /api/locations/<location_id>` | `update_location` | empty `name` → 400 |
| `DELETE /api/locations/<location_id>` | `delete_location` | 404 / 409 `in_use` / 200 |
| `POST /api/locations/<location_id>/photos` | `add_photo` | multipart |
| `DELETE /api/locations/<location_id>/photos/<photo_id>` | `delete_photo` | |
| `POST /api/locations/geocode` | `geocode_address` | body `{address}`; returns `{lat,lng}` or `{lat:null,lng:null}` — powers the edit form's "Locate" button without exposing the token |

Register `locations_bp` in `app.py` next to `contacts_bp`.

**On `production_bp`** (gated by `require_production_role`; resolver
`from_production_id` for the collection, new `from_production_location_id`
for item routes — added to `production_authz` alongside `from_crew_id`):

| Method + path | Min role / capability |
|---|---|
| `GET /api/productions/<production_id>/locations` | `viewer` |
| `POST /api/productions/<production_id>/locations` | `require_production_role` + `access['can_edit_production']` |
| `PATCH /api/productions/<production_id>/locations/<link_id>` | `can_edit_production` |
| `DELETE /api/productions/<production_id>/locations/<link_id>` | `can_edit_production` |

The `POST` body is `{location_id, production_notes}`. The route passes the
production's `owner_id` (from the authz context / a lookup) into
`link_location` for the ownership check.

## Maps integration — Mapbox

Chosen over Google: no mandatory billing account, generous free tier
(≈100k geocoding req/mo, 50k static-image loads/mo), simpler token model.

- **`MAPBOX_SECRET_TOKEN`** — backend env (Railway). Added to
  `RECOMMENDED_VARS` in `utils/env_validator.py` (**not** `REQUIRED_VARS` —
  geocoding degrades to manual lat/lng entry when absent). Used only by
  `geocode_service` server-side.
- **`VITE_MAPBOX_PUBLIC_TOKEN`** — frontend env (Vercel). A URL-restricted
  public token (`pk.*`) scoped to the Static Images API. Used only to build
  the `<img>` src.
- **Static map preview:** a plain `<img>`, no JS library:
  `https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/pin-s+e11d48(<lng>,<lat>)/<lng>,<lat>,13/480x240@2x?access_token=<pk>`
  Rendered only when `lat` and `lng` are both present **and**
  `VITE_MAPBOX_PUBLIC_TOKEN` is set; otherwise a small "No map — add
  coordinates" / "geocoding unavailable" placeholder keyed off
  `geocode_status`.
- **Edit form "Locate" button:** calls `POST /api/locations/geocode` with
  the typed address, shows the returned pin for confirmation, fills the
  lat/lng inputs. The inputs stay manually editable; a manual edit on save
  sends explicit `lat`/`lng` → `geocode_status='manual'`.
- No Mapbox GL / interactive map, no click-to-drop-pin picker in v1.

## Frontend

### `/locations` directory page — `LocationsDirectoryPage.jsx` (+ `.css`)

Clone of the contacts directory page.

- Search box + "Add location" button.
- List rows (name, address, a small map thumb when coords exist).
- Row → detail panel/drawer: all fields, full-size static map, photo
  gallery (thumbnails, upload, delete, caption), primary-contact name
  (links to the contact), "Used in N productions" list, Edit / Delete.
- Add/Edit modal: `name` (required), `address` + "Locate" button, `lat` /
  `lng` (manual override, shown with the resolved/failed status),
  `primary_contact_id` (`<select>` from `GET /api/contacts`),
  `permit_status`, `parking_notes`, `loadin_notes`, `restrictions`, `notes`.
- Delete → on `409` show "linked to productions X, Y — unlink first" and
  block.
- Nav link added next to "Contacts" in the same nav component, shown only
  to the account owner (match how the `/contacts` link is gated).

### Locations tab on `ProductionDetailPage` — `ProductionLocationsTab.jsx`

- Add to the `tabs` array in `ProductionDetailPage.jsx`:
  `if (isMember) tabs.push({ id: 'locations', label: 'Locations' })`
  and the `activeTab === 'locations'` render branch, plus the same
  `useEffect` reset guard the other tabs have
  (`if (activeTab === 'locations' && !isMember) setActiveTab('overview')`).
- Lists the production's linked locations: name, address, map thumb,
  `production_notes`, primary-contact name.
- Write controls — "Link a location" (picker over the owner's directory),
  edit `production_notes` inline, unlink — gated on
  `access.can_edit_production`, mirroring how `ProductionCrewTab` gates on
  `access.can_edit_crew`.
- The "Link a location" picker lists the owner's locations. For a non-owner
  member with `can_edit_production` it must still see the owner's full
  directory to pick from — match whatever `ProductionCrewTab`'s
  "add from contacts" flow does for the equivalent case (a
  production-scoped endpoint or a shared helper). If 2a's crew tab only
  supports this for the owner, this slice does the same and the gap is
  noted, not solved here.

### `apiService.js`

New functions block (mirrors the contacts/crew block):
`listLocations`, `createLocation`, `getLocation`, `updateLocation`,
`deleteLocation`, `uploadLocationPhoto`, `deleteLocationPhoto`,
`geocodeAddress`, `listProductionLocations`, `linkProductionLocation`,
`updateProductionLocation`, `unlinkProductionLocation`.

## Permissions (settled)

| Surface | Rule |
|---|---|
| `/locations` page + `/api/locations/*` + `/api/locations/geocode` | Owner-only (`@require_auth` + `owner_id` scoping). No production role. Mirrors `/contacts`. |
| `location_photos` write | Owner-only (directory is owner-only). |
| Production Locations tab — read | `require_production_role('viewer')` |
| Production location link / unlink / notes | `require_production_role` + `can_edit_production` capability (no new flag) |
| Non-owner member directory visibility | Only locations linked to productions they belong to, via the tab. No `/locations` nav entry. Mirrors the 2b `contacts` decision. |
| Sensitive-field gating | None on `locations`. Primary contact's phone/rate stays gated by existing `contacts` logic wherever surfaced. |

## Testing

- **`test_geocode_service.py`** — coords on mock 200; `None` on non-200,
  empty result, timeout, network error, missing key. Never raises.
- **`test_location_service.py`** — CRUD; owner-scoping (another owner's
  location is invisible / unmodifiable); search; delete-guard `in_use`
  (409 body shape); geocode-on-address-change (mock `geocode_service`) for
  all four branches (auto-ok, auto-failed, manual coords supplied, address
  cleared); photo add/delete.
- **`test_location_routes.py`** — auth required (401 anon); owner isolation
  (403/404 on another owner's location); 400 (missing/empty name); 404;
  409 (`in_use`); `POST /api/locations/geocode` happy + degraded. Mirror
  the `test_contact_routes` pattern.
- **`test_production_location_routes.py`** — `require_production_role`
  enforcement (non-member 403, `PRODUCTION_NOT_FOUND` 404); `viewer` can
  read, cannot write; `can_edit_production` gate on link/unlink/notes;
  cannot link a location owned by someone other than the production owner;
  duplicate link → clean 409.
- **`test_route_enforcement.py`** — extend the production-scoped-routes
  assertion (added in 2b) to cover the three new writable link routes.
- **`test_env_validator.py`** (if it asserts the recommended list) — add
  `MAPBOX_SECRET_TOKEN`.
- Full backend suite green; frontend `npm run build` green.

## Migration / deploy notes

1. Apply `053_locations.sql` manually to the Supabase project **before**
   deploying the backend (same as 051 / 052).
2. Set `MAPBOX_SECRET_TOKEN` in Railway and `VITE_MAPBOX_PUBLIC_TOKEN` in
   Vercel. The slice functions without them — the map preview hides and
   geocoding returns null coords — so this is not a hard deploy blocker,
   but the map feature is dark until both are set.
3. No data backfill. No changes to existing tables (`scripts`,
   `productions`, `contacts`, `shooting_schedules` all untouched).

## Open items carried forward (not blocking this slice)

- Whether a non-owner member can pick from the owner's **full** locations
  directory when linking (same open question as 2a crew ↔ contacts). This
  slice matches 2a's behaviour, whatever it is.
- Unlinked-location photo storage sweep (rare; manual for now).
- The scene-`setting` → `locations` creative mapping — separate brainstorm.
