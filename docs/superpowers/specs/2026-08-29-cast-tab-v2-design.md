# Cast tab v2 — design

**Date:** 2026-08-29
**Status:** Ready for implementation plan
**Builds on:** `docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md` (shipped 2026-08-28)
**UI / UX companion:** `docs/superpowers/specs/2026-08-29-cast-tab-v2-ui-ux.md` — layout, states, interaction, and copy. §5 here is a summary; that doc is authoritative for the frontend.
**Backlog entry:** "Cast tab v2 — full-body photo, cast tiers, extras as groups, conflict resolution — brainstorm" in `docs/BACKLOG.md`

---

## 1. Summary

Cast & Casting v1 shipped a per-script casting record (one row per character:
actor, status, contact, one headshot, blackout dates) plus an
availability-conflict engine that surfaces (but cannot act on) clashes between a
booked actor's unavailability and a dated shoot day.

v2 adds four things, all on the Cast tab and the schedule board:

1. **Multiple photos per cast entry** — a full-body shot and other reference
   images alongside the existing single headshot.
2. **Cast tiers** — `lead` / `supporting` / `featured` / `background`, set
   manually, used to organise the tab and to scope conflict detection.
3. **Background groups** — anonymous background booked by headcount
   ("Restaurant patrons ×12"), tracked separately from named individuals.
4. **Conflict resolution** — act on a flagged scheduled scene: unassign it,
   move it to a suggested conflict-free day, or acknowledge the conflict with a
   reason.

**Explicitly out of scope:** call sheets, sides, the Day Out of Days conflict
overlay (v1 Task 13), any AI/heuristic tier suggestion, seeding groups from the
AI-extracted `scenes.extras` breakdown data, group participation in the conflict
engine, and wiring tiers/groups into report output. The data model is designed
so those can follow without reshaping it.

---

## 2. Data model

All changes are additive. New tables follow the RLS pattern of migration 048
(`casting`): a select policy for script members, a write policy for
owner-or-admin. The backend uses the Supabase service key and bypasses RLS;
these policies are a defense-in-depth backstop for direct client access.

### 2.1 `casting` — additive columns

| column | definition | notes |
|---|---|---|
| `tier` | `TEXT NOT NULL DEFAULT 'supporting'` `CHECK (tier IN ('lead','supporting','featured','background'))` | Manual only. Migration backfills **every existing row to `'supporting'`** so v1 conflict behaviour is preserved unchanged (§4.1). |

`headshot_path` is unchanged and remains the canonical primary/thumbnail image
shown in Cast tab rows and consumed everywhere it is today.

### 2.2 `casting_photos` — new child table

Additional images beyond the primary headshot.

```sql
CREATE TABLE casting_photos (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    casting_id UUID NOT NULL REFERENCES casting(id) ON DELETE CASCADE,
    path       TEXT NOT NULL,
    kind       TEXT NOT NULL CHECK (kind IN ('headshot','full_body','other')),
    caption    TEXT,
    sort_order INT  NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_casting_photos_casting ON casting_photos(casting_id);
```

- Storage: the existing `scripts` bucket, path
  `casting/<script_id>/<casting_id>/<uuid>.<ext>` (a per-casting subfolder, so
  multiple files coexist — v1's headshot stays at
  `casting/<script_id>/<casting_id>.<ext>`).
- `casting.headshot_path` is **not** migrated into this table. The table is
  purely for the *extra* images. The primary photo continues through the v1
  `POST /api/casting/:id/headshot` path.
- Signed URLs, 3600 s TTL, same `_signed_url` helper as v1 headshots.
- Server-side type/size validation identical to v1 (`image/jpeg|png|webp`,
  5 MB cap).
- Deleting a `casting` row cascades. Deleting a single photo removes the row and
  the storage object (route-level, mirroring v1's headshot cleanup on casting
  delete).

### 2.3 `casting_groups` — new table

Anonymous background, booked by headcount. Never participates in the conflict
engine (no per-person availability to clash).

```sql
CREATE TABLE casting_groups (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id  UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    label      TEXT NOT NULL,
    headcount  INT  NOT NULL DEFAULT 1 CHECK (headcount > 0),
    status     TEXT NOT NULL DEFAULT 'wishlist'
                 CHECK (status IN ('wishlist','offer','booked','declined','released')),
    day_rate   NUMERIC(10,2),
    notes      TEXT,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_casting_groups_script ON casting_groups(script_id);

CREATE TRIGGER trg_casting_groups_updated
    BEFORE UPDATE ON casting_groups
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();  -- shared fn from migration 030
```

`status` reuses the `casting` vocabulary verbatim for consistency, even though
`declined`/`released` are less meaningful for a crowd — keeping one enum is
simpler than inventing a second.

### 2.4 `casting_group_scenes` — join table

```sql
CREATE TABLE casting_group_scenes (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES casting_groups(id) ON DELETE CASCADE,
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    UNIQUE (group_id, scene_id)
);
CREATE INDEX idx_casting_group_scenes_group ON casting_group_scenes(group_id);
CREATE INDEX idx_casting_group_scenes_scene ON casting_group_scenes(scene_id);
```

Populated manually via the group drawer's scene multi-select (replace-all
semantics). No seeding from `scenes.extras` — that JSONB stays independent
breakdown/report data.

### 2.5 `shooting_day_scenes` — additive columns (conflict acknowledge)

```sql
ALTER TABLE shooting_day_scenes
    ADD COLUMN conflict_ack        BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN conflict_ack_reason TEXT,
    ADD COLUMN conflict_ack_at     TIMESTAMPTZ,
    ADD COLUMN conflict_ack_by     UUID REFERENCES auth.users(id) ON DELETE SET NULL;
```

Acknowledgement is scoped to one `shooting_day_scenes` row — i.e. "this scene,
on this day, is fine despite the warning". See §4.4 for staleness handling.

---

## 3. Backend

### 3.1 `casting_service.py`

- `UPDATABLE_FIELDS` gains `tier`. `update_casting` validates `tier` against the
  CHECK set, raising `ValueError` on a bad value (same shape as the existing
  `status` validation).
- `serialize(row, ...)` always includes:
  - `tier` (string).
  - `photos`: list of `{id, kind, caption, sort_order, url}` (signed URLs),
    ordered by `sort_order, created_at`.
- `list_casting` / `get_casting` batch-load `casting_photos` for the row set,
  exactly as they batch-load `casting_unavailability` today.
- New `store_photo(casting_id, script_id, kind, file_bytes, content_type)` →
  uploads to `casting/<script_id>/<casting_id>/<uuid>.<ext>`, inserts a
  `casting_photos` row, returns the serialized photo.
- New `delete_photo(photo_id)` → loads the row, removes the storage object,
  deletes the row.

### 3.2 `casting_group_service.py` (new)

Mirrors `casting_service`'s shape.

- `list_groups(script_id)` → group rows, each with `scene_ids: [...]`
  batch-loaded from `casting_group_scenes`.
- `create_group(script_id, fields, user_id)` — `label` required; `headcount`
  defaults 1; validates `status`.
- `update_group(group_id, fields)` — whitelist `label`, `headcount`, `status`,
  `day_rate`, `notes`; validate `headcount > 0` and `status`.
- `delete_group(group_id)`.
- `set_group_scenes(group_id, scene_ids)` — replace-all: fetch the group's
  `script_id`, reject any `scene_id` not belonging to that script, then
  delete-not-in-list + insert-new.
- `serialize_group(row)` → `{id, script_id, label, headcount, status, day_rate,
  notes, scene_ids, created_at, updated_at}`.

### 3.3 Routes (`casting_routes.py`)

Auth mirrors v1: reads at `viewer`, writes at `admin`, via `@require_script_role`.

| method + path | resolver | purpose |
|---|---|---|
| `POST /api/casting/<casting_id>/photos` (multipart, `?kind=`) | `from_casting` | add a photo |
| `DELETE /api/casting/photos/<photo_id>` | `from_casting_photo` | remove a photo |
| `GET /api/scripts/<script_id>/casting-groups` | `from_script` | list groups |
| `POST /api/scripts/<script_id>/casting-groups` | `from_script` | create group |
| `PATCH /api/casting-groups/<group_id>` | `from_casting_group` | update group |
| `DELETE /api/casting-groups/<group_id>` | `from_casting_group` | delete group |
| `PUT /api/casting-groups/<group_id>/scenes` | `from_casting_group` | replace scene links (`{scene_ids: [...]}`) |

- `tier` rides the existing `PATCH /api/casting/<casting_id>`.
- `GET /api/scripts/<script_id>/casting` response is unchanged in shape; each
  `casting` object now carries `tier` and `photos`.
- New resolvers `from_casting_photo` and `from_casting_group` in
  `middleware/authorization.py`, following `from_casting` (resolve the row →
  its `script_id` → role check).

### 3.4 Conflict-resolution routes

- **Unassign** and **Move** reuse existing schedule endpoints with no change:
  - `DELETE /api/shooting-days/<day_id>/scenes/<scene_id>`
  - `POST /api/shooting-days/<from_day_id>/scenes/<scene_id>/move`
    (body `{to_day_id}`)
- **Acknowledge** — new
  `PATCH /api/shooting-days/<day_id>/scenes/<scene_id>/conflict-ack`,
  `@require_script_role('member', resolver=from_day)` (matches every other
  schedule mutation). Body `{acknowledged: bool, reason: string}`. Sets
  `conflict_ack`, `conflict_ack_reason`, `conflict_ack_at = now()`,
  `conflict_ack_by = user_id` (or clears all four when `acknowledged: false`).

---

## 4. Conflict engine changes

### 4.1 Tier scoping

`casting_service.compute_conflicts` today considers every `casting` row with
`status IN ('booked','offer')`. v2 adds a tier filter:

```
status IN ('booked','offer') AND tier IN ('lead','supporting','featured')
```

`background`-tier rows and all `casting_groups` are excluded from conflict
detection entirely. Because the migration backfills existing rows to
`'supporting'`, **no currently-detected conflict disappears** when v2 ships.

The detail drawer hides the `UnavailabilityEditor` when `tier === 'background'`
(a background individual has no availability tracking). Existing unavailability
rows on a row later moved to `background` are retained but ignored by the engine
and hidden in the UI; moving back to a higher tier restores them.

### 4.2 Acknowledged rows are skipped

`compute_conflicts` joins `shooting_day_scenes` and skips any `(scene, day)`
whose row has `conflict_ack = true`. Acknowledged conflicts are still returned,
separately, so the UI can list them (see §4.3).

Response shape becomes:

```json
{
  "schedule_id": "...",
  "conflicts": [
    {
      "shooting_day_id": "...", "day_number": 4, "shoot_date": "2026-03-05",
      "character_name": "DET. REYES", "actor_name": "A. Smith",
      "reason": "on another shoot",
      "scene_ids": ["..."],
      "suggested_day": { "shooting_day_id": "...", "day_number": 7, "shoot_date": "2026-03-12" }
    }
  ],
  "acknowledged": [
    { "...": "same shape minus suggested_day", "ack_reason": "...", "ack_by": "...", "ack_at": "..." }
  ]
}
```

`suggested_day` is `null` when no dated day clears the conflict.

### 4.3 The "move to a conflict-free day" suggestion

Computed server-side per conflict, in `compute_conflicts`, after the conflict
set is known.

For a conflict on scene `S` currently on day `D`:

1. Candidate days = all **dated** `shooting_days` in the same schedule, excluding
   `D`, ordered by `shoot_date` ascending.
2. Determine `S`'s relevant cast: the canonical character names in
   `scenes.characters` for `S` (alias-resolved via `character_aliases`, the same
   map `compute_conflicts` already builds) that have a `casting` row with
   `status IN ('booked','offer')` and `tier IN ('lead','supporting','featured')`.
3. The first candidate day `D'` whose `shoot_date` falls in **no** unavailability
   range of **any** of those cast members is the suggestion. Return its id,
   number, and date.
4. If none qualifies, `suggested_day = null`.

This only checks the moving scene against the target day — it does not
re-evaluate the rest of that day's scenes (moving `S` only *adds* `S`'s cast to
`D'`). It also does not consider page-count balance, INT/EXT, or D/N — those are
the "Auto AI scheduling" item's job. This is a deliberately small, honest
suggestion: "here is a day where this scene's principals are all free".

### 4.4 Acknowledgement staleness

`conflict_ack` lives on the `shooting_day_scenes` row and means "this scene, on
this day, is fine despite the warning".

- **Move** (via the existing move endpoint) creates a new `shooting_day_scenes`
  row on the target day / deletes the old — the ack does not travel. Correct.
- **Unassign** deletes the row — ack gone. Correct.
- **The day's `shoot_date` changes** after an ack: the ack is now stale (it was
  made against the old date). v2 handles this with a trigger — updating
  `shooting_days.shoot_date` clears `conflict_ack` (and the three companion
  columns) on all that day's `shooting_day_scenes` rows. The user re-evaluates
  against the new date.
- **The actor's unavailability changes** (range added/removed/edited) after an
  ack: **not** auto-cleared in v2. Rationale: the ack expresses a human decision
  ("I've spoken to the actor, it's handled") that a data edit shouldn't silently
  undo, and the conflict panel still lists the row under "Acknowledged" where the
  user can un-acknowledge it. Documented as a known limitation; revisit if it
  causes real confusion.

---

## 5. Frontend

### 5.1 `apiService.js`

New methods, following existing naming conventions:
`addCastingPhoto(castingId, file, kind)`, `deleteCastingPhoto(photoId)`,
`getCastingGroups(scriptId)`, `createCastingGroup(scriptId, fields)`,
`updateCastingGroup(groupId, fields)`, `deleteCastingGroup(groupId)`,
`setCastingGroupScenes(groupId, sceneIds)`,
`acknowledgeSceneConflict(dayId, sceneId, { acknowledged, reason })`.
Tier rides the existing `updateCasting(castingId, { tier })`.

### 5.2 `CastPage.jsx` — two sub-tabs

A tab strip below the page head: **Principals (N)** / **Background (N)**, plain
buttons on the existing dark/amber tokens, `lucide-react` icons only (no emoji).
Active tab in `useState` — not routed; the URL stays `/scripts/:id/cast`.
Search + status filter stay above the strip and apply within the active tab.

**Principals tab** — `casting` rows with `tier ∈ {lead, supporting, featured}`,
plus orphaned casting rows that aren't `background`. Rendered as three
collapsible sections (`Leads` / `Supporting` / `Featured`), each a header with
count + chevron; collapse state persisted in `localStorage` (the
`ScriptTable.jsx` series-group pattern). Within a section, the existing
scene-count sort is kept.

**Background tab** — `casting` rows with `tier === 'background'` in one list,
then a `cast-divider` ("Background groups"), then the `casting_groups` list
(`label ×headcount · N scenes`), then a `+ New group` button.

Row click → `CastingDetailPanel` (principals + background individuals) or
`CastingGroupPanel` (groups). The `conflicts` prop and per-row conflict
indicators are unchanged (background rows never carry conflicts by §4.1).

`fetchData` additionally calls `getCastingGroups`; groups go in their own state
slice.

### 5.3 `CastRow.jsx`

Adds a small tier badge (styled `<span>`, existing tokens). Background-individual
rows use a lighter variant and omit the headshot thumbnail when none is set.

### 5.4 `CastingDetailPanel.jsx`

- **Photos** — the primary image (from `headshot_path`, existing upload path)
  shown large, with an **"N more" expander**. Expanded: a thumbnail row of
  `photos[]` — each with its `kind` label, an optional caption, and a delete
  control — plus an "Add photo" control with a `kind` picker
  (headshot / full body / other) that calls `addCastingPhoto`.
- **Tier + Status** — two dropdowns side by side on one row. Tier options:
  Lead / Supporting / Featured / Background. Changing tier autosaves (same
  on-blur/on-change convention as the rest of the panel).
- When `tier === 'background'`: the `UnavailabilityEditor` block is not rendered.
- Actor name, contact, agent, notes, autosave — unchanged.
- Fixes v1's "Review Important #3" opportunistically: the tier/status controls
  are controlled inputs bound to props, so a server-normalised value reflects
  without a remount.

### 5.5 `CastingGroupPanel.jsx` (new)

Same slide-in drawer chrome as `CastingDetailPanel` (reuses
`CastingDetailPanel.css` / a shared drawer class).

- Fields: `label`, `headcount` (number input), `status` dropdown, `day_rate`
  (optional number), `notes` (textarea). Autosave on blur, matching the panel
  convention.
- **Scenes** — a checkbox list of the script's scenes (`scene_number` +
  truncated heading). Toggling writes the full set through
  `setCastingGroupScenes` (replace-all, debounced or on-close). The scene list
  is fetched via a lightweight existing scenes call.
- Footer: a Delete button (`deleteCastingGroup`), with the app's standard
  confirm dialog.
- Creating: the `+ New group` button opens the panel in a "new" state
  (`openId = 'new-group'`), first save calls `createCastingGroup` then swaps to
  the created id — the same `onCreated` pattern `CastingDetailPanel` uses.

### 5.6 Schedule board — conflict resolution

**`ScheduleSceneCard.jsx`** — when `hasConflict && !conflict_ack`, the existing
conflict note gains a single **`Resolve →`** button (lucide icon, e.g.
`ArrowRight`). When `conflict_ack`, the ring/danger styling is replaced by a
muted "conflict acknowledged" line (with the reason on hover/title). The
per-card `conflict` prop is extended by the parent to include the ack state for
that `(scene, day)`.

**`ConflictPanel.jsx`** — each unacknowledged conflict row expands to three
actions:

- **Move to Day N** — label shows `suggested_day.day_number` + date; calls the
  existing move endpoint (`from_day` → `to_day` = `suggested_day`). When
  `suggested_day` is `null`, the button renders **disabled** with the text
  `no conflict-free day`.
- **Unassign** — existing delete endpoint; the scene returns to the unscheduled
  pool.
- **Acknowledge** — reveals a short reason input; on submit calls
  `acknowledgeSceneConflict(dayId, sceneId, { acknowledged: true, reason })`.

A collapsed **"Acknowledged (N)"** sub-section at the bottom lists ack'd
conflicts, each with an **un-acknowledge** control
(`acknowledgeSceneConflict(..., { acknowledged: false })`).

`Resolve →` on a card scrolls the panel into view and expands that conflict's
row. This needs the panel's expanded-row state and the card's callback lifted to
their common ancestor (`ScheduleKanban.jsx` / `ShootingSchedulePage.jsx`) — a
small prop-drill or a shared context value.

**Refetch** — `ConflictPanel` already re-runs `getCastingConflicts` whenever the
schedule signature (`daysSig`) changes, so Move and Unassign refresh naturally.
Acknowledge / un-acknowledge do not change `daysSig`, so they call an explicit
refetch on success.

---

## 6. Migration

One new migration file, `049_cast_tab_v2.sql`, applied manually against the
Supabase project (per the repo convention — `run_migration.py` is dead):

1. `ALTER TABLE casting ADD COLUMN tier ...` then
   `UPDATE casting SET tier = 'supporting'` (the DEFAULT covers new rows; the
   explicit UPDATE covers the backfill of existing rows — both land on
   `'supporting'`).
2. `CREATE TABLE casting_photos ...` + index + RLS policies.
3. `CREATE TABLE casting_groups ...` + index + `updated_at` trigger + RLS.
4. `CREATE TABLE casting_group_scenes ...` + indexes + RLS.
5. `ALTER TABLE shooting_day_scenes ADD COLUMN conflict_ack ...` (+ 3 companion
   columns).
6. `CREATE FUNCTION` + `CREATE TRIGGER` on `shooting_days`: when `shoot_date`
   changes, clear `conflict_ack` / `conflict_ack_reason` / `conflict_ack_at` /
   `conflict_ack_by` on that day's `shooting_day_scenes` rows.

RLS on the three new tables mirrors migration 048 (`casting` /
`casting_unavailability`) — a member select policy and an owner-or-admin write
policy, keyed through `casting_groups.script_id` (directly, or via the parent
for the join table).

---

## 7. Testing

**Backend (`pytest tests/`):**

- `test_casting_photos.py` — add/list/delete photos; signed URLs present;
  type/size rejection; cascade on casting delete; auth (viewer read, admin
  write, non-member 403).
- `test_casting_groups.py` — CRUD; `headcount > 0` and `status` validation;
  `set_group_scenes` replace-all + cross-script `scene_id` rejection; scene-link
  cascade on group delete and on scene delete; auth.
- `test_casting_tier.py` — `PATCH` sets tier; invalid tier 400; serialize
  includes tier; migration backfill leaves existing-row behaviour intact.
- `test_casting_conflicts.py` (extend v1's) — tier filter (background &
  group excluded); `suggested_day` picks the earliest clear dated day;
  `suggested_day: null` when none; acknowledged `(scene, day)` omitted from
  `conflicts` and present in `acknowledged`; `shoot_date` change clears the ack.
- `test_conflict_ack_route.py` — the new PATCH endpoint: set, clear, `member`
  role required, `from_day` resolver.
- `test_route_enforcement.py` — new script-scoped routes carry the
  `_authz_min_role` marker.

**Frontend (`npm run build` — lint is repo-broken):**

- Build passes. Manual verification in a real script:
  - Principals/Background sub-tabs; tier sections collapse and persist.
  - Add a full-body photo; it appears in the "N more" gallery; delete it.
  - Change a row to `background` → it moves to the Background tab and the
    unavailability editor disappears from its drawer.
  - Create a group, set headcount + scenes, see it on the Background tab.
  - On the schedule: a conflicted card shows `Resolve →`; it opens the panel row;
    Move to the suggested day clears the conflict; Acknowledge with a reason
    clears the ring and files the row under "Acknowledged"; changing that day's
    shoot date brings the conflict back.

---

## 8. Open questions / deferred

- **Featured extras** are handled as `casting` rows at `tier = 'featured'` — a
  named individual with photos, contact, and (optionally) availability. No
  separate mechanism. If productions want a distinct call-sheet line for
  "featured background" vs. "day player", that is a call-sheet-slice concern,
  not a data-model one.
- **Groups in reports / DOOD / call sheets** — deferred with the rest of the
  call-sheet work. The `casting_groups` shape (label, headcount, scene links,
  status) is what those consumers will need.
- **Group conflict checking** — out of scope; groups have no per-person
  availability. If a specific background person must be tracked, they are a
  `background`-tier `casting` row, not a group member.
- **Ack invalidation on unavailability edits** (§4.4) — known limitation.
- **`suggested_day` sophistication** — page balance, INT/EXT, D/N clustering all
  belong to the "Auto AI scheduling (first pass)" backlog item, which this
  suggestion is a first honest step toward.
