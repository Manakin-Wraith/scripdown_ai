# Cast tab v2 — UI / UX spec

**Date:** 2026-08-29
**Companion to:** `2026-08-29-cast-tab-v2-design.md` (data model, API, engine).
Read that first. This document covers layout, states, interaction, and copy.
**Extends the v1 UI:** `2026-08-27-cast-casting-v1-ui-ux.md` — everything there
still holds unless contradicted below.

---

## 1. Design language — inherited, not invented

Same system as v1 (`frontend/src/index.css`), used verbatim:

- **Surface:** `--bg-app` page, `--bg-card` rows/panels, `--bg-elevated`
  hover/active.
- **Accent:** amber (`--primary-400/500`), primary actions and booking state
  only.
- **Type:** Inter, `--text-*` scale. Character names uppercase with
  `letter-spacing: 0.02em` (as the breakdown renders them). Everything else
  sentence case.
- **Spacing/radius/shadow:** `--space-*` (4px scale), `--radius-md/-lg`,
  `--shadow-*`.
- **Status colour:** `--success` / `--danger` / `--warning` + `-bg` tints.
- **Primitives:** `Drawer`, `Badge`, `Button`, `EmptyState`, `Spinner`,
  `Skeleton`/`SkeletonList` from `components/ui/`. **No new primitives.**
- **Icons:** `lucide-react` only. No emoji anywhere in the UI (existing v1
  strings that use `✓`/`⚠` glyphs are left as-is; new UI uses lucide).

### The signature element is unchanged

The Principals list stays a wall of faces — 40px headshots down the left edge.
v2 adds a second, quieter list (Background) that is deliberately face-free:
labels and counts, not portraits, because that is how background is actually
tracked.

---

## 2. Navigation

**No change to `SectionNav`.** Still one `Cast` tab at
`/scripts/:scriptId/cast`. The Principals / Background split is a segmented
control *inside* the page, not a route — deep links stay stable, and the two
lists share one filter bar.

---

## 3. `CastPage` — layout

Full-width workspace page, `--container-max`, centred, `--edge-padding` gutters
(unchanged from v1).

```
┌────────────────────────────────────────────────────────────────────────┐
│  Cast                                                                   │  --text-2xl
│  18 principals · 4 background groups · 6 booked · 3 conflicts           │  summary (--text-sm, --text-secondary; "conflicts" --danger when >0)
│                                                                        │
│  ┌ Principals (13) ┊ Background (9) ┐        [ Search… ] [ Status ▾ ]   │  segmented control (left) + filter bar (right), sticky
│                                                                        │
│  ▾ LEADS · 3                                                            │  tier section header — lucide ChevronDown/Right, count
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ [img] SARAH CONNOR      LEAD    Linda Hamilton   ● Booked   ⚠  ›  │  │
│  │       24 scenes                                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ▾ SUPPORTING · 6                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ [img] DET. REYES        SUPP    A. Smith         ● Offer    ⚠  ›  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ▸ FEATURED · 4                                                         │  collapsed
└────────────────────────────────────────────────────────────────────────┘
```

Background tab:

```
│  ┌ Principals (13) ┊ Background (9) ┐        [ Search… ] [ Status ▾ ]   │
│                                                                        │
│  ── Individuals ───────────────────────────────────────────────────    │  divider — only if any background-tier casting rows
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ [img] BARISTA           BG      uncast          Add casting →  ›  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ── Groups ────────────────────────────────────────────────────────    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Restaurant patrons          ×12    3 scenes    ● Booked      ›   │  │
│  │  Protesters                  ×40    2 scenes    ○ Wishlist    ›   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  + New group                                                           │  text button, --primary-400
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Segmented control

- Two segments: `Principals ({n})` / `Background ({n})`. `{n}` = row counts
  (principals = lead+supporting+featured casting rows + non-background orphans;
  background = background-tier casting rows + `casting_groups`).
- Style: the app's existing segmented / pill-toggle treatment (`--bg-card`
  track, `--bg-elevated` active segment, `--text-primary` active /
  `--text-secondary` idle). Sits on the left of the sticky bar; the search +
  status filter move to the right of the same bar.
- Active tab held in `useState`, **not** persisted — defaults to Principals on
  every load. (Rationale: principals is the primary job; a stale Background
  default would hide the main list.)

### 3.2 Summary line

`{n} principals · {n} background groups · {n} booked · {n} conflicts`

- `principals` = count of lead+supporting+featured casting rows.
- `background groups` = count of `casting_groups` (omit the clause when 0).
- `booked` = casting rows (any tier) with `status = 'booked'`.
- `conflicts` = distinct `(character, day)` conflicts against the active
  schedule, **excluding acknowledged ones**; `--danger` when > 0; whole clause
  omitted when there is no active schedule.

### 3.3 Filter bar

Unchanged from v1 (search by character/actor name; status select
`All / Wishlist / Offer / Booked / Declined / Released / Not cast`), plus:

- Filters apply **within the active tab only**.
- On the Background tab, the status filter also filters groups by their
  `status`. Search matches a group's `label`.
- **No tier filter control** — the Principals tab's three sections and the tab
  split itself already are the tier filter.
- Empty result inside a tab: the existing inline "No characters match. · Clear
  filters" treatment.

### 3.4 Tier sections (Principals tab)

- Three sections in fixed order: **Leads**, **Supporting**, **Featured**.
- Header: `lucide` `ChevronDown` (open) / `ChevronRight` (collapsed), the label
  in `--text-xs` uppercase tracked (`.cast-divider` styling), and `· {count}`.
- Collapse state per section persisted in `localStorage`
  (`castTierCollapsed:<scriptId>`), matching `ScriptTable.jsx`'s series-group
  pattern. All sections open by default.
- An empty section (no rows at that tier) still renders its header, collapsed,
  with `· 0` — so the user can see the tier exists and knows where a
  re-tiered row will land. (Alternative — hide empty sections — rejected: it
  makes the page jump when the last row of a tier is moved.)
- Orphaned casting rows (not in the latest breakdown) that are lead/supporting/
  featured tier sit under their tier's section with the existing
  `Not in breakdown` chip — no separate "Not in current breakdown" divider on
  the Principals tab (the tier grouping replaces it). Background-tier orphans
  go under `Individuals` on the Background tab.

### 3.5 Principal / individual row

The existing `CastRow` layout, with one addition: a **tier badge** between the
character name block and the actor name — a small outline chip, `--text-2xs`,
`--gray-500` border, label `LEAD` / `SUPP` / `FEAT` / `BG`. On the Principals
tab the badge is somewhat redundant with the section, but it survives when the
row is shown out of section context (search results that span tiers render
flat, no section headers — the badge is how you tell them apart).

Background-**individual** rows: same `CastRow`, `BG` badge, no scene sub-line
requirement relaxation — they still show `{n} scenes` if the character is in
the breakdown.

### 3.6 Group row

A distinct, lighter row (`CastGroupRow`, presentational):

| Slot | Content |
|---|---|
| **Label** (`--text-sm`, 600, **not** uppercase — it's a description, not a character) | `Restaurant patrons` |
| **Headcount** (`--text-sm`, `--text-secondary`) | `×12` |
| **Scenes** (`--text-xs`, `--text-muted`) | `3 scenes` (or `No scenes` in `--warning` if unlinked) |
| **Status** | `StatusBadge` (same 5-status component) |
| **Chevron** | `lucide` `ChevronRight`, `--text-muted` |

No avatar slot — the row starts at the text. Height ~52px (shorter than a
principal row's ~64px). Whole row is a `<button>` opening the group drawer.

`+ New group` is a text button directly below the groups list (or below the
`Groups` divider when the list is empty), opening the group drawer in create
mode.

---

## 4. `CastingDetailPanel` — principal / individual drawer

The v1 drawer (`Drawer` primitive, `width="440px"`, autosave, `subHeader` save
state, admin-gated contact section and footer) is unchanged except:

### 4.1 Tier + Status row

Directly under the header, **above** the Actor field: two controls side by side
on one row.

```
│  Tier   [ Lead  Supporting  Featured  Background ▾ ]                  │
│  Status [ Wishlist  Offer  Booked  Declined  Released ]              │
```

- **Tier** — a native `<select>` styled to match the app's dropdowns (four
  options). Changing it `PATCH`es immediately (same as status) and re-runs the
  parent's `refresh` so the row jumps to its new section / tab.
- **Status** — the existing 5-button radio group, unchanged, now sharing the
  row with Tier. On narrow widths (< 480px drawer / full-screen sheet) the two
  stack.
- Both are controlled inputs bound to `row.tier` / `row.status` — this also
  closes v1's "Review Important #3" (uncontrolled `defaultValue` fields not
  reflecting a server-normalised value). **Migrate the text fields
  (`actor_name`, contact, notes) to controlled at the same time** while this
  component is open.

### 4.2 Photos section (replaces "Headshot")

```
│  PHOTOS                                                              │
│  ┌────────┐                                                          │
│  │        │   Replace   Remove                                       │  primary — headshot_path, big (~120px)
│  │  img   │                                                          │
│  └────────┘                                                          │
│  ▸ 2 more photos                                                     │  expander — lucide ChevronRight; hidden when photos[] empty
│                                                                      │
│  (expanded:)                                                         │
│  ┌────┐ ┌────┐ ┌────┐                                                │  thumb row, ~72px each
│  │full│ │ref │ │ +  │                                                │  each: kind label under it + hover Remove; last tile = Add
│  └────┘ └────┘ └────┘                                                │
│  Full body   Other                                                   │
```

- **Primary photo** — unchanged from v1: uses `headshot_path`, the existing
  `uploadHeadshot` / remove flow, `Replace` / `Remove` text buttons.
- **"{n} more photos" expander** — only shown when `photos[]` is non-empty
  **or** the user clicks `Add photo`. Collapsed by default.
- **Thumb row (expanded)** — one ~72px tile per `photos[]` entry, ordered by
  `sort_order`. Under each tile: its `kind` label (`Headshot` / `Full body` /
  `Other`). Hovering / focusing a tile reveals a `Remove` control (lucide `X`).
  The final tile is a dashed **Add** tile (lucide `Plus`).
- **Add flow** — clicking the Add tile opens a small inline row: a `kind`
  `<select>` (defaulting to `Full body`) + a file input
  (`accept="image/jpeg,image/png,image/webp"`). On pick → `addCastingPhoto`,
  optimistic append, `kind` label shown. Same 5 MB / type errors as v1.
- **Captions** — not surfaced in v2 UI (the column exists for later). No
  reordering UI in v2 (`sort_order` defaults by creation).
- Read-only (non-admin): primary photo shows with no Replace/Remove; the
  expander still works to view; no Add tile, no per-thumb Remove.

### 4.3 Availability section — tier-gated

- When `row.tier === 'background'`: the **entire Availability section
  (`UnavailabilityEditor`) is not rendered.** In its place, one muted line:
  *"Background cast isn't checked for schedule conflicts."*
- Any existing unavailability rows on a row later moved to `background` are
  retained in the DB but hidden; moving back to lead/supporting/featured brings
  them back and they re-enter conflict detection.
- All other tiers: unchanged from v1.

### 4.4 Conflict callout

Unchanged from v1 (`cd-conflict-callout`, lists the conflicting days). Not
shown for background-tier rows (they have no conflicts).

---

## 5. `CastingGroupPanel` — background group drawer (new)

Same `Drawer` primitive, `width="440px"`, full-screen sheet < 720px, same
autosave-on-blur model and `subHeader` save-state machine as
`CastingDetailPanel`. Reuses `CastingDetailPanel.css` classes (`cd-label`,
`cd-section`, `cd-savestate`, `cd-delete`) — no new stylesheet unless a
group-specific rule is genuinely needed.

```
┌──────────────────────────────────────────┐
│  Restaurant patrons                  ✕    │  header — the label (--text-lg, 600, NOT uppercase)
│  Background group                         │  sub (--text-xs, --text-secondary)
│  ✓ All changes saved                      │  save state
├──────────────────────────────────────────┤
│  Label                                    │
│  [ Restaurant patrons                  ]  │  text input
│                                          │
│  Headcount            Status              │  one row, two controls
│  [ 12 ]               [ ● Booked  ▾ ]     │  number input · status select (5 options)
│                                          │
│  Day rate (optional)                      │
│  [ R                                   ]  │  number input, ZAR prefix
│                                          │
│  SCENES                                   │  section label
│  [ Search scenes…                      ]  │  filter, only shown when > ~12 scenes
│  ☑ 12  INT. BISTRO — NIGHT                │  checkbox list of the script's scenes
│  ☑ 14  INT. BISTRO — NIGHT                │  (scene_number + truncated heading)
│  ☐ 15  EXT. STREET — DAY                  │
│  ☑ 20  EXT. STREET — NIGHT                │
│  …                                        │
│                                          │
│  NOTES                                    │
│  [                                     ]  │  textarea, 3 rows
├──────────────────────────────────────────┤
│  Delete group                            │  footer — cd-delete style, admin only
└──────────────────────────────────────────┘
```

### 5.1 Fields & saving

- `label` — text, `PATCH` on blur. Required; empty label on blur reverts to the
  last saved value (or, in create mode, blocks the first save with an inline
  *"Give the group a name."*).
- `headcount` — `<input type="number" min="1">`, `PATCH` on blur. Below 1 →
  clamps to 1 with an inline *"At least 1."*
- `status` — `<select>`, 5 options, `PATCH` on change.
- `day_rate` — `<input type="number" min="0">` with a static `R` prefix,
  `PATCH` on blur, optional.
- `notes` — textarea, `PATCH` on blur.

### 5.2 Scenes multi-select

- A scrollable checkbox list of every scene in the script, `scene_number` +
  heading (truncated to one line). Scenes the group is linked to are checked.
- Toggling a box updates local state immediately; the full set is written via
  `setCastingGroupScenes(groupId, [...])` (replace-all) **debounced ~600ms**
  after the last toggle, or immediately on drawer close — so rapid ticking is
  one request.
- A search field above the list appears only when the script has more than
  ~12 scenes.
- The row's `3 scenes` / `No scenes` label reflects this set after save.
- Scene list source: reuse whatever `ScheduleKanban` / breakdown already loads;
  a lightweight `getScenes(scriptId)` is acceptable if nothing cached fits.

### 5.3 Create mode

- `+ New group` opens the drawer with `openId = 'new-group'`, all fields empty,
  header *"New background group"*, sub *"Background group"*.
- First `label` blur (non-empty) calls `createCastingGroup`, then the drawer
  swaps to the created id and subsequent edits `PATCH` — the same lazy-create
  pattern `CastingDetailPanel.ensureRow` uses. Scene toggles before the row
  exists are held and flushed on create.

### 5.4 Read-only (non-admin)

All fields render as static text; `—` for empty. Scene list shows checked
scenes only, as plain text. No Delete. Muted line: *"Only the owner and admins
can edit casting."*

### 5.5 Delete

Footer `Delete group` → confirm dialog (the app's `ConfirmDialog`):
title *"Delete this background group?"*, body *"This removes “{label}” and its
scene links. It doesn't affect the breakdown or the schedule."*, confirm
*"Delete group"* (destructive).

---

## 6. Tier badge

A single small component (`TierBadge`), outline chip, not the filled `Badge`:

| tier | label | treatment |
|---|---|---|
| `lead` | `LEAD` | `--text-primary` text, `1px solid --gray-500` |
| `supporting` | `SUPP` | `--text-secondary` text, `1px solid --gray-600` |
| `featured` | `FEAT` | `--text-secondary` text, `1px solid --gray-600` |
| `background` | `BG` | `--text-muted` text, `1px dashed --gray-600` |

`--text-2xs`, `padding: 1px 6px`, `--radius-full`. `background` is dashed to
echo the `released` status badge convention ("lighter-weight thing"). Colour is
never the only signal — the label always shows.

---

## 7. Conflict resolution — schedule board

The v1 surfaces (summary count on `CastPage`, the `ConflictPanel` below the
schedule toolbar, red day-header dots, `.schedule-scene-card.conflict` rings +
`ssc-conflict-note`) are unchanged. v2 adds the ability to act.

### 7.1 On the scene card (`ScheduleSceneCard`)

- When `hasConflict && !conflictAck`: the existing `ssc-conflict-note`
  ("{actor} unavailable") gains a single trailing **`Resolve`** text button
  (lucide `ArrowRight` after the label, `--danger` text). Nothing else on the
  card changes — no extra action row, no height bump beyond the button.
- When `conflictAck`: the card drops the `.conflict` ring and red styling; the
  note becomes a muted line *"Conflict acknowledged"* (`--text-muted`,
  `--text-xs`) with the reason in the `title` attribute. A small lucide
  `Check`.
- The parent (`ScheduleKanban`) passes each card an extended `conflict` value
  that now includes `{ acknowledged, ack_reason }` for that `(scene, day)`.

### 7.2 In the `ConflictPanel`

The panel keeps its collapsible header
(`Availability conflicts ({n})`, `TriangleAlert`, checking spinner). Each
**unacknowledged** conflict row becomes expandable:

```
▾ Day 4 · 12 Mar — A. Smith (DET. REYES) unavailable · on another shoot
    [ Move to Day 7 (18 Mar) ]   [ Unassign ]   [ Acknowledge ]
```

- **Move to Day N** — primary-styled (`Button` `size="sm"`). Label:
  `Move to Day {suggested_day.day_number} ({date})`. Calls the existing move
  endpoint (`from` = this day, `to` = `suggested_day`). When
  `suggested_day === null`: the button renders **disabled** with label
  *"No conflict-free day"* and a `title` *"Every dated day has an availability
  clash for this scene's principals."*
- **Unassign** — ghost `Button`. Calls the existing
  `DELETE /shooting-days/:day/scenes/:scene`. The scene returns to the
  unscheduled pool. Confirm inline (not a dialog): the button swaps to
  *"Remove from Day 4?"* / *"Yes"* on first click.
- **Acknowledge** — ghost `Button`. Reveals an inline row: a text input
  *"Reason (optional)"* + a `Save` button → `acknowledgeSceneConflict(dayId,
  sceneId, { acknowledged: true, reason })`. On success the row moves to the
  Acknowledged sub-section.
- After Move / Unassign the panel refetches via the existing `daysSig` effect;
  after Acknowledge it refetches explicitly.

### 7.3 Acknowledged sub-section

At the bottom of the panel, a collapsed disclosure:

```
▸ Acknowledged (2)
    Day 4 · 12 Mar — A. Smith (DET. REYES) · "spoke to agent, cleared"   [ Un-acknowledge ]
```

- `--text-secondary`, no `--danger`.
- **Un-acknowledge** → `acknowledgeSceneConflict(..., { acknowledged: false })`;
  the row returns to the active conflict list on refetch.
- Hidden entirely when there are no acknowledged conflicts.

### 7.4 `Resolve` → panel linkage

Clicking `Resolve` on a card:
1. scrolls the `ConflictPanel` into view (`scrollIntoView`, respect
   `prefers-reduced-motion`),
2. expands the panel if collapsed,
3. expands that specific conflict row and briefly highlights it
   (`--primary-alpha-15` flash, 1s).

Needs the panel's `expandedConflictKey` state and the card's `onResolve`
callback lifted to their common ancestor (`ShootingSchedulePage` /
`ScheduleKanban`) — a small prop pass or a schedule-scoped context value. Key
= `${shooting_day_id}:${character_name}`.

---

## 8. Page-level states (`CastPage`)

Inherits v1's table. Changes / additions:

| State | Treatment |
|---|---|
| **Loading** | `SkeletonList` — now under a skeleton segmented control + filter bar. |
| **No characters** | Unchanged v1 `EmptyState` ("No characters yet" → Go to Scenes). The segmented control is hidden in this state. |
| **Principals empty, background present** | Land on Principals (per §3.1), show an inline note *"No principal cast yet — every character is set to Background, or none are cast."* with the three empty tier headers still visible. |
| **Background tab, nothing** | `EmptyState` inside the tab: icon (`lucide` `UsersRound`), *"No background yet"*, body *"Add a background group for crowd scenes, or set a character's tier to Background."*, primary button *"New group"*. |
| **Group with no scenes** | Row shows `No scenes` in `--warning`; drawer shows all scene checkboxes unticked with a hint *"Link the scenes this group appears in so it shows on the schedule."* |
| **No active schedule** | No conflict UI (v1 behaviour). The `Resolve` affordance and `ConflictPanel` actions simply never appear. |
| **Load error** | Unchanged v1 inline error card + Retry. |

---

## 9. Copy reference

**Tabs / sections**
- Segmented control: `Principals ({n})` · `Background ({n})`
- Tier sections: `Leads` · `Supporting` · `Featured`
- Background dividers: `Individuals` · `Groups`
- `+ New group`

**Tier control** — `Lead` · `Supporting` · `Featured` · `Background`
**Tier badges** — `LEAD` · `SUPP` · `FEAT` · `BG`

**Photos**
- Section label: `Photos`
- `Replace` · `Remove` (primary)
- Expander: `{n} more photo` / `{n} more photos`
- Kind options: `Headshot` · `Full body` · `Other`
- Add tile hint (inline): `Choose a photo type, then pick an image.`

**Group drawer**
- Header (existing): the label · sub `Background group`
- Header (create): `New background group`
- Field labels: `Label`, `Headcount`, `Status`, `Day rate (optional)`,
  `Scenes`, `Notes`
- Validation: *"Give the group a name."* · *"At least 1."*
- Scenes hint: *"Link the scenes this group appears in so it shows on the
  schedule."*
- Delete confirm: title *"Delete this background group?"* / body *"This removes
  “{label}” and its scene links. It doesn't affect the breakdown or the
  schedule."* / confirm *"Delete group"*

**Availability (background tier)** — *"Background cast isn't checked for
schedule conflicts."*

**Conflict resolution**
- Card: `Resolve`
- Card (ack'd): `Conflict acknowledged`
- `Move to Day {n} ({date})` · disabled: `No conflict-free day`
  (title: *"Every dated day has an availability clash for this scene's
  principals."*)
- `Unassign` → `Remove from Day {n}?` / `Yes`
- `Acknowledge` → reason placeholder `Reason (optional)` · `Save`
- `Acknowledged ({n})` · `Un-acknowledge`

**Summary line** — `{n} principals · {n} background groups · {n} booked ·
{n} conflicts`

**Voice:** sentence case except character names and the badge labels. Active
verbs. Errors say what happened and the fix.

---

## 10. Accessibility & quality floor

- Segmented control is a `role="tablist"` with `role="tab"` buttons; the two
  lists are `role="tabpanel"`. Arrow keys move between tabs.
- Tier section headers are `<button aria-expanded>` controlling their section.
- Tier `<select>` and group `<select>`s have real `<label>`s.
- Photo thumb Remove controls are real buttons with
  `aria-label="Remove {kind} photo"`; the `+` Add tile is a labelled button.
- Scene checkbox list: each is a native `<input type="checkbox">` with a
  `<label>`; the list container is a group with an accessible name `Scenes`.
- `Resolve` / `Move` / `Unassign` / `Acknowledge` are real buttons; disabled
  `Move` keeps its `title` reason and `aria-disabled`.
- Conflict state conveyed by text ("unavailable", "Conflict acknowledged"),
  never colour/ring alone; lucide glyphs are `aria-hidden`.
- Group row `<button>` accessible name: `"{label}, {headcount} people,
  {status}, {n} scenes"`.
- `scrollIntoView` and the highlight flash respect `prefers-reduced-motion`.
- Colour contrast ≥ 4.5:1 for all badge/label pairs on `--bg-card` (verify
  `BG` dashed-muted during build).
- Responsive to 360px; both drawers → full-screen sheet < 720px; no horizontal
  page scroll; the tier + status row and headcount + status row stack < 480px.

---

## 11. Out of scope (UI)

- Tier filter dropdown (the tab + sections are the filter).
- Photo captions and photo reordering UI (columns exist; not surfaced).
- Bulk re-tiering / bulk status.
- Seeding groups from the breakdown `extras` data (a "suggest groups"
  affordance) — deferred.
- Group availability / group conflict UI (groups are never in the engine).
- Group headcount on the schedule board / call sheet / DOOD (call-sheet slice).
- Drag-to-reorder anything.
- Season-level cast board.

---

## 12. Component / file inventory (for the plan)

**New — `frontend/src/components/cast/`**
- `CastGroupRow.jsx` — presentational group row.
- `CastingGroupPanel.jsx` — the group drawer (reuses `CastingDetailPanel.css`).
- `TierBadge.jsx` — the 4-tier outline chip.
- `PhotoGallery.jsx` (or inline in `CastingDetailPanel`) — primary + expander +
  thumb row + add flow. Split out if `CastingDetailPanel` gets unwieldy.

**Touched**
- `CastPage.jsx` / `CastPage.css` — segmented control, two tabs, tier sections,
  groups list, summary line, new states. Collapse-state `localStorage`.
- `CastRow.jsx` — tier badge slot.
- `CastingDetailPanel.jsx` / `.css` — tier + status row, Photos section,
  tier-gated Availability, controlled-input migration.
- `apiService.js` — `addCastingPhoto`, `deleteCastingPhoto`, `getCastingGroups`,
  `createCastingGroup`, `updateCastingGroup`, `deleteCastingGroup`,
  `setCastingGroupScenes`, `acknowledgeSceneConflict`.
- `frontend/src/components/schedule/ConflictPanel.jsx` / `.css` — expandable
  rows, three actions, Acknowledged sub-section, `expandedConflictKey`.
- `frontend/src/components/schedule/ScheduleSceneCard.jsx` — `Resolve` button,
  acknowledged muted state, extended `conflict` prop.
- `frontend/src/components/schedule/ScheduleKanban.jsx` /
  `ShootingSchedulePage.jsx` — lift `expandedConflictKey` + `onResolve`, pass
  ack state to cards.
- No `SectionNav.jsx` / `App.jsx` route changes (Cast tab already exists).

---

## 13. Open UI questions (resolve during the plan / build)

- **Segmented-control vs. sub-nav styling** — confirm the app already has a
  pill/segmented pattern to reuse; if not, it's a `--bg-card` track + active
  `--bg-elevated` segment, ~2px radius inside `--radius-md`. Not a new
  primitive — local to `CastPage.css`.
- **Scene list performance** — a 120-scene script renders 120 checkboxes in the
  group drawer. Plain list is fine; virtualise only if it stutters in
  practice.
- **`Move to Day` when the schedule has one day** — `suggested_day` is `null`
  (no other dated day); button disabled with the standard reason. No special
  copy.
