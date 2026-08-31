# Crew + Contacts — Build-Sequence Step 2a Design

**Date:** 2026-08-31
**Status:** Design approved — ready for implementation plan
**Type:** Architectural
**Parent:** `docs/superpowers/specs/2026-08-31-production-data-model-design.md`
(umbrella direction spec — build-sequence step 2, first half)

## Purpose

Give a production a crew roster and give the account a reusable address
book. The umbrella spec's step 2 bundled the data (`contacts` +
`production_crew` + CSV import) with a new permission layer
(`production_members` + `can_view_sensitive` + the non-owner
directory-scope decision). This spec ships **only the data half (2a),
owner-only**. The permission layer is **slice 2b** — its own brainstorm →
spec → plan.

Sensitive fields (rates, personal phone) are **stored** in 2a but
**ungated** — the owner is the only viewer, so there is nothing to gate
yet. 2b introduces the gate.

## Scope

**In:**

- Migration `051_contacts_crew.sql` (applied manually to the Supabase
  project — `run_migration.py` is dead, per the casting migration notes):
  `contacts` table, `production_crew` table.
- New blueprint `contacts_bp` (`routes/contact_routes.py` +
  `services/contact_service.py`) — account-level directory CRUD.
- Crew routes added to the existing `production_bp`, backed by a new
  `services/production_crew_service.py`.
- CSV crew import: `services/crew_import.py` (pure parser) +
  `POST /api/productions/:id/crew/import`.
- Frontend: `/contacts` directory page + nav link; a **Crew** tab on
  `ProductionDetailPage` (requires extracting the current Overview markup
  into a sub-component and adding a tab strip).

**Out (named, deferred):**

- `production_members`, member-management UI, `can_view_sensitive`,
  non-owner directory scope, permission inheritance, seat consumption for
  production members → **slice 2b**.
- Any non-owner access to crew/contacts. In 2a the Crew tab is hidden for
  non-owner viewers and `/contacts` is absent from their nav.
- `default_call_offset` on `production_crew` → call-sheet slice (step 4);
  no consumer until then.
- `locations` / `production_locations` → step 3.
- Contact photos → follow the `casting_photos` pattern in step 3
  (locations); contacts get no photos in 2a.
- Directory-only CSV import (contacts with no assignment) → fast-follow if
  asked; 2a ships the per-production crew importer only.
- Interactive column mapping for CSV → fixed-header template only.
- AI-parse of an uploaded call sheet / production book → deferred
  (umbrella spec; needs real sample docs).
- Cast ↔ `contacts` unification → known future reconciliation debt
  (umbrella spec).

## Data model

Migration `backend/db/migrations/051_contacts_crew.sql`. Mirrors the
`048_casting.sql` conventions: `gen_random_uuid()` pks, manual apply,
`update_shooting_updated_at()` trigger reuse (from migration 030),
owner-only RLS as a direct-client backstop only.

### `contacts` — account-level directory

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `owner_id` | uuid not null | `REFERENCES profiles(id) ON DELETE CASCADE`. Matches `productions.owner_id`. The cascade is load-bearing for `013_delete_user_safely.sql` (deletes `scripts` then `profiles`); carry a comment saying so. |
| `kind` | text not null | `default 'person'`, `CHECK (kind IN ('person','company'))` |
| `name` | text not null | the person's name, or the company name when `kind='company'` |
| `company_name` | text null | employer / agency when `kind='person'` |
| `role_tags` | text[] not null | `default '{}'::text[]` — freeform search hint ("gaffer", "1st AD", "caterer"). Not authoritative; the assignment's `department_code` is the truth. |
| `phone` | text null | **sensitive** (ungated in 2a) |
| `email` | text null | |
| `agent_contact` | text null | free text (name / phone / email of an agent or manager) |
| `standard_rate` | numeric null | **sensitive** (ungated in 2a) |
| `rate_unit` | text null | `CHECK (rate_unit IS NULL OR rate_unit IN ('day','week','flat'))` |
| `notes` | text null | |
| `created_by` | uuid null | `REFERENCES auth.users(id) ON DELETE SET NULL` |
| `created_at` | timestamptz not null | `default now()` |
| `updated_at` | timestamptz not null | `default now()`; `BEFORE UPDATE` trigger reusing `update_shooting_updated_at()` |

Indexes:
- `idx_contacts_owner ON contacts(owner_id)`
- `idx_contacts_owner_email ON contacts(owner_id, lower(email)) WHERE email IS NOT NULL`
  — supports CSV import email matching.

**No unique constraint on email** — a person and their agent can share an
address, users mistype, and a silent merge on a bad match is worse than a
duplicate. Import matching is a deliberate, explained choice (see CSV
import), not a constraint.

### `production_crew` — assignment (join production ↔ contact)

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `production_id` | uuid not null | `REFERENCES productions(id) ON DELETE CASCADE` |
| `contact_id` | uuid not null | `REFERENCES contacts(id) ON DELETE RESTRICT` — DB-level backstop for "block contact delete when referenced" |
| `role` | text null | this job's title (e.g. "Gaffer", "1st AD") |
| `department_code` | text null | **soft reference** to the `departments` list — validated in Python via `get_departments_list()`, NOT a hard FK (the `departments` table is managed directly in Supabase, not in migrations, and `invite_routes.py` already validates department codes in Python). Nullable — vendors (caterer, equipment house) have no shooting department; the UI shows an "Unassigned / Vendors" group. |
| `job_rate` | numeric null | **sensitive** (ungated in 2a) |
| `job_rate_unit` | text null | `CHECK (job_rate_unit IS NULL OR job_rate_unit IN ('day','week','flat'))` |
| `start_date` | date null | for partial-schedule crew |
| `end_date` | date null | |
| `notes` | text null | |
| `created_at` | timestamptz not null | `default now()` |
| `updated_at` | timestamptz not null | `default now()`; trigger reuse |

Table-level constraint:
`CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)`
(mirrors `casting_unavailability`).

Indexes:
- `idx_production_crew_production ON production_crew(production_id)`
- `idx_production_crew_contact ON production_crew(contact_id)`

**No unique constraint** on `(production_id, contact_id)` — a person can
hold two roles on one production (Gaffer weeks 1–3, then a reshoot role),
and dailies recur. The CSV importer has its own dedup guard (below); the
manual "Add crew" form does not prevent a deliberate second assignment.

`default_call_offset` is intentionally omitted — added in the call-sheet
slice (step 4) when a generator reads it. Same YAGNI logic the spine spec
used for `format`.

### RLS

Owner-only policies on both tables — a direct-client backstop only. Real
enforcement is Python + the service-role key, exactly as `045` / `050`.

```sql
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_crew ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner manages contacts"
    ON contacts FOR ALL USING (owner_id = auth.uid());

CREATE POLICY "owner manages production crew"
    ON production_crew FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = production_crew.production_id
                  AND p.owner_id = auth.uid())
    );
```

### User deletion

`013_delete_user_safely.sql` deletes `scripts` then `profiles`.
`contacts.owner_id ON DELETE CASCADE` → contacts vanish with the profile,
which cascades `production_crew` via `production_crew.contact_id` … except
that FK is `ON DELETE RESTRICT`. Resolution: the same script already
deletes `productions` (via `productions.owner_id ON DELETE CASCADE`), and
`production_crew.production_id ON DELETE CASCADE` clears every crew row
**before** the `contacts` cascade fires. Order within a single
`DELETE FROM profiles` is: profile → productions → production_crew (by
production), then profile → contacts (now unreferenced). No FK error.
Migration 051 carries a comment stating this ordering is load-bearing.

If the plan reviewer finds this fragile, the fallback is
`production_crew.contact_id ON DELETE CASCADE` (deleting a contact would
then silently drop its assignments) — rejected here because the friendly
"used on Production X, Y" 409 is the desired product behavior and
`RESTRICT` enforces it even against a direct client.

## Backend API

### New blueprint: `contacts_bp`

`routes/contact_routes.py` (thin) + `services/contact_service.py` (logic).
Registered in `app.py` with one `register_blueprint(contacts_bp)` line
after `production_bp`. All routes `@require_auth`; **every query filters
`owner_id = get_user_id()`**. Contacts have no script axis —
`get_script_role` is not involved.

| Method / path | Behavior |
|---|---|
| `GET /api/contacts` | Caller's contacts, `order by name`. Optional `?q=` (ILIKE on `name`, `company_name`, `email`) and `?kind=person\|company`. Returns `{contacts: [...]}`. |
| `POST /api/contacts` | Body: `{kind?, name, company_name?, role_tags?, phone?, email?, agent_contact?, standard_rate?, rate_unit?, notes?}`. `name` required (trimmed, non-empty → 400). `kind` / `rate_unit` validated against the CHECK sets → 400. `role_tags` accepts an array or a comma string (normalized to `text[]`). 201 → `{contact}`. |
| `GET /api/contacts/:id` | 404 if not the caller's. Returns `{contact, assignments: [{crew_id, production_id, production_title, role}]}` — powers the "Used on" list. |
| `PATCH /api/contacts/:id` | Partial update, same field whitelist + validation. 404 if not the caller's. |
| `DELETE /api/contacts/:id` | Pre-check `production_crew WHERE contact_id = :id`. Non-empty → **409** `{error: "Contact is assigned to crew", used_in: [{production_id, production_title}]}`. Empty → delete, 200. The `ON DELETE RESTRICT` FK is the backstop; the route supplies the friendly payload. |

`services/contact_service.py`:
`list_contacts(user_id, q, kind)`, `create_contact(user_id, fields)`,
`get_contact_with_usage(user_id, contact_id)`,
`update_contact(user_id, contact_id, fields)`,
`delete_contact(user_id, contact_id) -> 'ok' | 'not_found' | 'in_use'`,
`_user_owns_contact(user_id, contact_id) -> bool`.

### Crew routes on `production_bp`

Backed by `services/production_crew_service.py`. Every route reuses the
existing `production_service._user_owns_production` guard — **owner-only,
no viewer read-through** (unlike `GET /api/productions/:id`). Non-owner →
403; missing production → 404.

| Method / path | Behavior |
|---|---|
| `GET /api/productions/:id/crew` | `{crew: [{...crew_row, contact: {...}}]}` — assignments with the embedded contact, ordered by `department_code` (nulls last) then `contact.name`. |
| `POST /api/productions/:id/crew` | Body: `{contact_id, role?, department_code?, job_rate?, job_rate_unit?, start_date?, end_date?, notes?}`. Validates `contact_id` belongs to the caller (`contacts.owner_id == caller`) → 400 if not. `department_code`, if present, validated against `get_departments_list()` → 400 if unknown. `job_rate_unit` against the CHECK set. 201 → `{crew}` (with embedded contact). |
| `PATCH /api/productions/:id/crew/:crewId` | Partial update of the assignment's own fields (`role`, `department_code`, `job_rate`, `job_rate_unit`, `start_date`, `end_date`, `notes`). **Not** `contact_id` — to change the person, remove and re-add. 404 if the crew row isn't on this production. |
| `DELETE /api/productions/:id/crew/:crewId` | Plain row delete. 200. A no-match is a 200 no-op (mirrors `remove_script`). |
| `POST /api/productions/:id/crew/import` | CSV upload — see below. |

`services/production_crew_service.py`:
`list_crew(production_id)`, `add_crew(production_id, user_id, fields)`,
`update_crew(production_id, crew_id, fields)`,
`remove_crew(production_id, crew_id)`,
`import_crew_csv(production_id, user_id, csv_text)`.

`get_departments_list()` currently lives in `routes/invite_routes.py`.
Move it to `services/department_service.py` (or `utils/departments.py`) so
both `invite_routes` and `production_crew_service` import it without a
route→route dependency. Small, in-scope refactor; keep the existing cache
behavior.

### `GET /api/productions/:id` — one additive field

Add `is_owner: bool` to the response (`get_production_for_viewer` already
computes `is_owner` locally — just include it). The Crew tab needs it to
hide itself for non-owner viewers, and it lets `ProductionDetailPage`
replace its current optimistic-owner heuristic with the real value. No
other change; crew is still fetched via `GET /api/productions/:id/crew`
when the tab opens, so the detail payload stays small.

### `app.py`

One `register_blueprint(contacts_bp)` line. Crew routes are on
`production_bp` — no new registration.

## CSV import

**Endpoint:** `POST /api/productions/:id/crew/import`,
`multipart/form-data`, one `file` field. Owner-only. Reject > ~1 MB or
> ~2,000 data rows with a 400 before parsing.

### Parser — `services/crew_import.py`

Pure function, **no DB access** (unit-testable in isolation):

```
parse_crew_csv(text: str, valid_department_codes: set, department_names: dict)
    -> {"rows": [ParsedRow, ...], "errors": [{"line": int, "reason": str}]}
```

- Python stdlib `csv.DictReader`. A header row is required.
- Headers normalized: lowercased, trimmed, internal spaces → underscores.
- Recognized headers: `name` (**required column** — its absence is a
  fatal 400, nothing written), `email`, `phone`, `company_name`, `role`,
  `department`, `rate`, `rate_unit`, `notes`. Unknown columns ignored.
- `department` cell → matched to a `departments.code`, else a
  case-insensitive match on `departments.name`; no match → row error
  (row skipped, batch continues).
- Per-row validation, each failure → `errors` entry, **never aborts the
  batch**:
  - missing / blank `name` → skip
  - `rate` present but non-numeric → skip
  - `rate_unit` present but not in `{day, week, flat}` → coerced to null,
    warning entry (row still imported)

### Route flow — `import_crew_csv`

1. Parse. Fatal header problem → 400 `{error: "CSV must have a 'name' column"}`, nothing written.
2. For each valid row:
   - **Match contact by `lower(email)` within `owner_id`** when the row
     has a non-empty email; otherwise **always create a new contact**.
     Never match on name (silent-merge risk).
   - New contact carries `name`, `email`, `phone`, `company_name`,
     `standard_rate` (from `rate`), `rate_unit`. `kind='person'`.
   - Create the `production_crew` assignment: `role`, `department_code`,
     `job_rate` (from `rate`), `job_rate_unit`, no dates (CSV has none in
     v1).
   - **Dedup guard:** if this contact already has an assignment on this
     production with the same `role` (case-insensitive, NULL == NULL) →
     skip, add `{line, reason: "already on crew as <role>"}` to the
     summary. Makes a double-import safe.
3. Response `200`:
   `{created_contacts, matched_contacts, assignments_created, skipped: [{line, reason}]}`.

**Not transactional.** supabase-py has no transaction wrapper and no
existing service attempts one. A mid-import failure leaves earlier rows
written; the summary reflects what landed and re-running is safe (dedup
guard). This matches the app's resumable-idempotent posture (extraction
pipeline, casting group-create).

### Template

Static `frontend/public/crew-import-template.csv`:
`name,email,phone,company_name,role,department,rate,rate_unit,notes`
with two example rows. Linked from the import modal.

## Frontend

### `services/apiService.js`

All through the single axios instance — no new instance:
`listContacts(params)`, `createContact(payload)`, `getContact(id)`,
`updateContact(id, payload)`, `deleteContact(id)`;
`listProductionCrew(prodId)`, `addProductionCrew(prodId, payload)`,
`updateProductionCrew(prodId, crewId, payload)`,
`removeProductionCrew(prodId, crewId)`,
`importProductionCrew(prodId, file)` (builds the `FormData`).

### `/contacts` — account-level directory page

- `pages/ContactsListPage.jsx`; route
  `<Route path="contacts" element={<ContactsListPage />} />` under the
  existing `ProtectedRoute` layout in `App.jsx`.
- `components/layout/TopBar.jsx`: a "Contacts" `NavLink` in `.topbar-nav`
  after "Productions". This makes four top-level items (My Scripts,
  Series, Productions, Contacts) — re-check `.topbar-nav` wrapping /
  overflow at narrow widths, tighten spacing if needed, no redesign.
- Table columns: name, `kind` badge, company, role tags, phone, email.
  Search box (drives `?q=`), kind filter. Full-page loading / error /
  empty states matching the series/production pages.
- "New contact" → modal form: all `contacts` fields; `name` required;
  `kind` toggle; `role_tags` as a simple chip / comma input; `rate` +
  `rate_unit` select.
- Row click → **Contact detail drawer**: the edit form + a "Used on"
  list (`assignments` from `GET /api/contacts/:id`), each linking to
  `/productions/:id`. Delete button; on 409 render "Used on Production X,
  Y — remove those assignments first."
- Styling: reuse `ProductionPages.css` / the series token system. No
  photos.

### Crew tab on `ProductionDetailPage.jsx`

- The spine page renders Overview + associated scripts inline. **Refactor:**
  extract the Overview markup into `components/productions/ProductionOverviewTab.jsx`,
  add a tab strip **Overview | Crew** (Locations / Schedule / Call Sheets
  appear as later slices ship), add
  `components/productions/ProductionCrewTab.jsx`. Keeps the page file
  focused.
- The Crew tab is **owner-only** — hidden entirely for a non-owner viewer
  (who can still open the page read-only for Overview + scripts, per the
  spine). Detect via the same owner check the page already uses for the
  Overview edit controls.
- **Crew tab body:** assignments grouped by department (headers from the
  departments list; an "Unassigned / Vendors" group for null
  `department_code`). Each row: contact name, role, rate + unit, date
  range, edit / remove actions.
- **"Add crew"** → modal:
  - Contact field = a combobox: type to search existing contacts
    (`listContacts({ q })`), **or** "＋ Create new contact" expands inline
    contact fields → `POST /api/contacts` first, then the returned id
    feeds the assignment.
  - Assignment fields: role, department `<select>` (+ "Vendor / none"),
    job rate + unit, start / end date, notes.
  - Submit → `POST /api/productions/:id/crew`.
- **Edit** an assignment row → same modal in edit mode → `PATCH`.
- **Remove** → confirm → `DELETE`.
- **"Import CSV"** button → modal: file picker, "Download template" link,
  on upload show the summary
  (`"3 added, 1 matched existing, 2 skipped: line 4 no name, line 9 bad rate"`),
  then refresh the crew list. No client-side parsing.

## Testing

### Backend — new test files

`backend/tests/test_contact_routes.py`:

- **Auth / ownership:** anonymous → 401 every route; `GET /api/contacts`
  returns only the caller's; another user's contact → 404 on
  `GET/PATCH/DELETE :id`.
- **CRUD:** `POST` requires `name`; rejects bad `kind` / `rate_unit`;
  `role_tags` accepts array and comma string; `PATCH` updates only
  provided fields.
- **Delete guard:** contact with a `production_crew` row → 409 with
  `used_in`; unassigned contact → 200; a second delete → 404.
- **`GET :id` usage:** `assignments` lists every production the contact
  is crewed on, with title and role.

`backend/tests/test_production_crew_routes.py`:

- **Access:** non-owner (even a `script_members` viewer on an associated
  script) → 403 on every crew route; missing production → 404.
- **CRUD:** `POST` with a contact the caller doesn't own → 400; unknown
  `department_code` → 400; null `department_code` accepted; `PATCH`
  ignores `contact_id`; `DELETE` then re-`DELETE` → 200 no-op.
- **Grouping order:** `GET .../crew` orders by department then name;
  nulls last.
- **Cascade:** deleting the production removes its `production_crew` rows
  (assert) and leaves `contacts` intact.
- **Multi-role:** the same contact added twice with different roles →
  both rows persist (no unique constraint).

`backend/tests/test_crew_import.py` (pure parser, no HTTP):

- header normalization (spaces, case); missing `name` column → fatal
  error signal; blank-name row → skipped with line number; non-numeric
  `rate` → skipped; bad `rate_unit` → coerced + warning; unknown
  `department` → skipped; unknown extra columns ignored.

`backend/tests/test_production_crew_routes.py` (import route):

- happy path: 2 new + 1 email-match + 1 skip → correct summary counts and
  DB state.
- **idempotency:** importing the same file twice → second run creates 0
  assignments (dedup guard), summary lists them as skipped.
- email match is scoped to `owner_id` (another owner's identical email is
  not matched).

Full suite (`pytest tests/`) stays green.

### Frontend

- `npm run build` green (repo lint is broken — see project memory — so
  build is the gate).
- Manual: create a contact in `/contacts`; open a production → Crew tab →
  add crew picking that contact; add crew creating a new contact inline;
  edit a rate; remove an assignment; import the template CSV and confirm
  the summary; try to delete a still-assigned contact and see the 409
  message; delete the production and confirm the contact survives in
  `/contacts`.

## Reconciliation with existing systems

| System | Change |
|---|---|
| `productions` / `units` / spine routes | `production_bp` gains crew routes + `production_crew_service`. `GET /api/productions/:id` gains an additive `is_owner` field. `ProductionDetailPage` refactored into tabs and switched to the real `is_owner`. |
| `series` / `seasons` | None. |
| `casting` / `casting_unavailability` | None. Cast stays its own per-script system. A person who is both cast and crew is duplicated across systems — accepted (umbrella "known future reconciliation debt"). |
| `script_members` / `departments` / `department_notes` | None to the tables. `get_departments_list()` **moves** from `routes/invite_routes.py` to a shared service module (both callers updated). `production_crew.department_code` is a Python-validated soft reference to the same list. |
| `shooting_schedules` | None. |
| Billing / seats | None. Contacts and crew consume nothing. Production-member seats are slice 2b. |
| `013_delete_user_safely.sql` | No edit — cascade ordering (productions → production_crew, then contacts) is clean. Migration 051 carries a comment. |
| `app.py` | One `register_blueprint(contacts_bp)` line. |
| `GET /api/contacts` in `apiService.js` / `TopBar` / `App.jsx` | New page, route, nav link. |

## Open questions resolved in the brainstorm

- **Slice the permission layer out?** → Yes. 2a = data, owner-only. 2b =
  `production_members` + `can_view_sensitive` + directory scope +
  inheritance + seats.
- **`contacts` shape?** → One table, `kind` discriminator defaulting to
  `person`. `role_tags text[]` freeform on the contact; authoritative
  department on the assignment.
- **`production_crew` shape?** → No `default_call_offset` (step 4). No
  unique constraint (multi-role / dailies). Nullable `department_code`
  (vendors bucket).
- **CSV import target?** → Per-production crew importer only. Email-only
  matching (scoped to owner), never name. Fixed-header template, no
  interactive mapping. Dedup guard on (contact, production, role).
- **Manual entry?** → Baseline. "Add crew" form + inline contact create;
  CSV is an accelerator, not the only path.
- **Standalone `/contacts` page?** → Yes, in 2a — the address book needs a
  list view to fix a number globally and to see unassigned contacts.
- **Delete semantics?** → Block contact delete when referenced (409 +
  `used_in`; `ON DELETE RESTRICT` backstop). Remove-assignment is a plain
  row delete. Production delete cascades crew rows, contacts untouched.
- **Non-owner access in 2a?** → None. Crew tab hidden, `/contacts` not in
  their nav. 2b owns the entire "who else can see this" question.
- **Code organization?** → `contacts_bp` (its own resource + page +
  lifecycle); crew routes on `production_bp`; pure `crew_import.py`
  parser.

## References

- `docs/superpowers/specs/2026-08-31-production-data-model-design.md` —
  parent umbrella spec (entity model, permissions direction, ingestion
  policy)
- `docs/superpowers/specs/2026-08-31-production-spine-design.md` — step 1;
  the `production_bp` / `production_service` / `_user_owns_production`
  pattern this extends, and the tab-strip refactor target
- `backend/db/migrations/048_casting.sql` — directory + manual-migration +
  `update_shooting_updated_at()` trigger + RLS-as-backstop pattern
- `backend/db/migrations/050_productions.sql` — `owner_id → profiles(id)
  ON DELETE CASCADE`, delete-user cascade comment pattern
- `backend/routes/invite_routes.py` — `get_departments_list()` (to be
  moved) and Python-side department-code validation
- `backend/services/entitlement_service.py` — seat accounting (untouched
  in 2a; the model slice 2b must extend)
- `frontend/src/pages/ProductionDetailPage.jsx`,
  `frontend/src/pages/ProductionsListPage.jsx`,
  `frontend/src/pages/ProductionPages.css` — page + token patterns
- `frontend/src/components/layout/TopBar.jsx`,
  `frontend/src/App.jsx` — nav + route registration
