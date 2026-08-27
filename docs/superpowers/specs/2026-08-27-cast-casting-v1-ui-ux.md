# Cast & Casting (v1) — UI / UX Spec

**Date:** 2026-08-27
**Companion to:** `2026-08-27-cast-casting-v1-design.md` (data model, API,
architecture). This document covers layout, states, interaction, and copy
only. Read the design spec first for what the feature does and why.

---

## 1. Design language — inherited, not invented

This is a feature inside an existing product. It uses the app's established
system verbatim (`frontend/src/index.css`):

- **Surface:** dark slate. `--bg-app` (`--gray-900`) page, `--bg-card`
  (`--gray-800`) rows/panels, `--bg-elevated` (`--gray-700`) hover/active.
- **Accent:** amber (`--primary-400/500`), used with restraint — booking
  progress and primary actions only.
- **Type:** Inter (`--font-sans`). Type scale from the `--text-*` tokens.
- **Grid:** 4px spacing scale (`--space-*`), radius `--radius-md`/`-lg`,
  shadows `--shadow-*`.
- **Status:** `--success`, `--danger`, `--warning` + their `-bg` tints.
- **Primitives:** `Drawer`, `Badge`, `Button`, `EmptyState`, `Spinner`,
  `Skeleton`/`SkeletonList` from `components/ui/`. No new primitives.

Any choice below that is not derivable from these tokens is called out
explicitly.

### The one signature element

The character list **is a casting board**. Every row carries the actor's
headshot at a real size (40px), so a fully-cast script reads top-to-bottom
as a wall of faces — the way a printed call-sheet header or a casting-office
corkboard does. This is the single place the feature spends any visual
boldness. Everything else stays quiet: no gradients, no illustration, no
decorative iconography beyond function.

---

## 2. Navigation placement

Add one entry to `SECTIONS` in `frontend/src/components/layout/SectionNav.jsx`,
positioned **immediately after Scenes** (casting is a pre-production activity
that acts on characters the breakdown detected — it belongs before the
planning cluster):

```
Scenes · Cast · Stripboard · [Board · Schedule] · Reports
```

- **Label:** `Cast`
- **Icon:** lucide `Contact` (a person on a card — reads as "cast
  contacts"). If not present in the installed lucide version, `Users`.
- **Route:** `/scripts/:scriptId/cast`
- `activeKey()` regex in `SectionNav.jsx` extended to match `cast`.

---

## 3. Page layout — `CastPage`

Full-width workspace page under the standard `MainLayout` +
`SectionNav` chrome. Max content width `--container-max` (1400px), centred,
`--edge-padding` gutters — matching Reports and Schedule.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Cast                                                                │  ← page title (--text-2xl)
│  18 characters · 6 booked · 3 availability conflicts                 │  ← summary line (--text-sm, --text-secondary; "conflicts" in --danger when > 0)
│                                                                     │
│  [ Search characters…            ]   [ All statuses ▾ ]              │  ← filter bar (sticky under header)
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ ▢  SARAH CONNOR          Linda Hamilton      ● Booked      ›   │  │  ← row, cast
│  │    24 scenes                                 ⚠ 2 conflicts     │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │ ▢  KYLE REESE           Michael Biehn        ● Booked      ›   │  │
│  │    18 scenes                                                   │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │ ○  T-800                 Add casting →                     ›   │  │  ← row, not cast
│  │    31 scenes                                                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ─── Not in current breakdown ──────────────────────────────────    │  ← divider, only if orphans exist
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ ▢  GINGER            Bess Motta       ● Released   Not in     ›│  │
│  │                                                   breakdown    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.1 Ordering

Characters listed by breakdown prominence — descending scene count — so
leads sit at the top. Reuse the ordering the breakdown character list
already produces. Orphaned casting rows (no matching breakdown character)
are pulled out below a labelled divider, ordered by `actor_name`.

### 3.2 Summary line

`{n} characters · {n} booked · {n} availability conflicts`

- "booked" counts casting rows with `status = 'booked'`.
- "availability conflicts" counts distinct characters with ≥1 conflict
  against the active schedule (see §6). The whole clause is `--danger`
  coloured when the count is > 0; omitted entirely when there is no active
  schedule.

### 3.3 Filter bar

- **Search** — filters the list by character name or actor name,
  case-insensitive, live.
- **Status filter** — `All statuses` (default) / Wishlist / Offer / Booked /
  Declined / Released / Not cast. Standard select styled to match the app's
  existing dropdowns.
- Sticky directly under the page header on scroll (`--z-sticky`).
- When a filter yields nothing: an inline `EmptyState` inside the list area
  — "No characters match." with a "Clear filters" text button.

### 3.4 Row anatomy

One row = one character. Height ~64px, `--bg-card`, `--border-subtle`
divider between rows, `--bg-elevated` on hover, whole row is a button that
opens the drawer (§4).

| Slot | Cast | Not cast | Orphan |
|---|---|---|---|
| **Avatar** (40px, `--radius-md`) | headshot, or initials monogram on `--gray-700` if none | hollow circle outline `○` in `--gray-600` | headshot / monogram |
| **Character name** (`--text-sm`, 600, `--text-primary`, uppercase tracking as breakdown uses) | shown | shown | shown |
| **Sub-line** (`--text-xs`, `--text-secondary`) | `{n} scenes` | `{n} scenes` | — |
| **Actor** (`--text-sm`, `--text-primary`) | `actor_name` | `Add casting →` (amber text button, `--primary-400`) | `actor_name` |
| **Status** | `Badge` (§5) | none | `Badge` |
| **Conflict pill** | `⚠ {n} conflicts` in `--danger` when > 0 (see §6); else nothing | none | shown if applicable |
| **Tag** | — | — | `Not in breakdown` — small outline chip, `--gray-500` |
| **Chevron** `›` | `--text-muted`, right-aligned | same | same |

Mobile (< 720px): the row collapses to two lines — line 1: avatar +
character name + status badge; line 2 (indented past the avatar): actor +
conflict pill. Sub-line and chevron drop.

---

## 4. Detail drawer — `CastingDetailPanel`

Right-side slide-over via the shared `Drawer` primitive. Width 440px
desktop; full-screen sheet < 720px. Backdrop `--scrim`. Esc closes, focus
returns to the originating row (Drawer primitive behaviour).

```
┌──────────────────────────────────────────┐
│  SARAH CONNOR                        ✕    │   header — character name (--text-lg, 600)
│  24 scenes · appears across the script    │   sub (--text-xs, --text-secondary)
│  ⟳ Saving… / ✓ All changes saved          │   autosave status (--text-2xs, --text-muted)
├──────────────────────────────────────────┤
│                                          │
│  ⚠ Conflicts with 2 shoot days           │   conflict callout — only if any; --danger-bg
│     Day 4 (12 Mar) · Day 7 (18 Mar)      │   panel, --danger left border
│                                          │
│  ACTOR                                    │   section label (--text-2xs, tracked, --text-muted)
│  ┌────────────────────────────────────┐  │
│  │ Linda Hamilton                     │  │   actor_name — text input
│  └────────────────────────────────────┘  │
│  Status  [ Wishlist  Offer  ●Booked  …]  │   status — segmented control (5)
│                                          │
│  HEADSHOT                                 │
│  ┌──────┐  Replace   Remove               │   88px square preview; or dashed dropzone
│  │ img  │                                 │   "Drop an image or browse · JPG/PNG/WebP · 5 MB"
│  └──────┘                                 │
│                                          │
│  CONTACT                                  │   ← entire section OWNER/ADMIN ONLY
│  Phone   [ ………………………………… ]                │
│  Email   [ ………………………………… ]                │
│  Agent   [ ………………………………………………… ]          │   textarea, 2 rows — "Agency, name, phone"
│                                          │
│  AVAILABILITY                             │
│  Unavailable dates                        │
│  ┌────────────────────────────────────┐  │
│  │ 12 Mar – 15 Mar   Other shoot   ✕  │  │   one range row
│  │ 02 Apr – 02 Apr    —            ✕  │  │
│  └────────────────────────────────────┘  │
│  + Add unavailable dates                  │   → reveals inline [start] [end] [reason] [Add]
│                                          │
│  NOTES                                    │
│  ┌────────────────────────────────────┐  │
│  │                                    │  │   textarea, 3 rows
│  └────────────────────────────────────┘  │
├──────────────────────────────────────────┤
│  Delete casting                          │   footer — ghost/danger text button, admin only
└──────────────────────────────────────────┘
```

### 4.1 Saving model — autosave

- Text fields (`actor_name`, contact fields, `notes`) → `PATCH` on blur.
- `status` segmented control → `PATCH` immediately on change.
- Headshot upload / remove → immediate.
- Availability ranges → each add and each delete is an immediate,
  independent request (they are discrete records).
- Header shows a quiet state machine: `✓ All changes saved` (idle) →
  `⟳ Saving…` (in flight) → back to saved; on failure →
  `⚠ Couldn't save — retry` with a retry affordance on the affected field.
- No explicit Save button, no draft state. Closing the drawer never loses
  anything.

### 4.2 Not-cast state

Opening the drawer for an uncast character: same layout, all fields empty,
header sub-line reads "Not cast yet." The first edit to any field (or
picking a status) creates the casting row (`POST`), then subsequent edits
`PATCH`. No separate "create" step for the user.

### 4.3 Orphan state

Header shows a `Not in breakdown` chip and a one-line explanation under the
sub-line: *"This character isn't in the latest breakdown — it may have been
renamed or removed. These casting details are kept."* All editing still
works. No scene sub-line.

### 4.4 Read-only (non-admin) state

For a `viewer`/`member` (not owner, not `admin`):

- No "Add casting" affordance on rows; opening the drawer is still allowed.
- Every field renders as static text, not inputs. Empty fields show
  `—`.
- The **Contact section is absent entirely** (the API doesn't return those
  fields for this user).
- No "Add unavailable dates", no per-range `✕`, no headshot Replace/Remove,
  no Delete.
- A single muted line under the header: *"Only the owner and admins can
  edit casting."*

---

## 5. Status badge

Use the `Badge` primitive. Label text is always shown (never colour-only).
Dot + label.

| Status | Treatment | Token basis |
|---|---|---|
| `wishlist` | muted grey, filled | `--text-secondary` on `--gray-800` |
| `offer` | amber, filled | `--primary-400` on `--primary-alpha-15` |
| `booked` | green, filled | `--success` on `--success-bg` |
| `declined` | red, filled | `--danger` on `--danger-bg` |
| `released` | grey, **outline** (dashed border), no fill | `--text-muted`, `1px dashed --gray-600` |

`released` is deliberately the only outline variant so "was cast, no longer
active" is distinguishable at a glance from "not yet pursued" (`wishlist`).

---

## 6. Availability conflicts — where they surface

A conflict = a character works a dated shoot day that falls inside one of
their actor's unavailable ranges (design spec §5.5). **Informational only —
nothing is ever blocked.**

Conflicts are only computed for casting rows whose `status` is `booked` or
`offer` — a `wishlist`, `declined`, or `released` row has no committed actor
to have a conflict with. (This filter lives in
`casting_service.compute_conflicts`; reflected in design spec §5.5.)

### 6.1 On `CastPage`

- Per-row **conflict pill**: `⚠ {n} conflicts`, `--danger` text, no fill,
  `--text-xs`. `aria-label="{n} availability conflicts"`.
- Summary line count (§3.2).
- Only computed when the script has a schedule with `status = 'active'`
  (most recently updated one if several). No active schedule → no pills, no
  summary clause.

### 6.2 On `ShootingSchedulePage`

- A collapsible panel below the schedule toolbar:
  **`Availability conflicts (3)`** — `--danger` left border, collapsed by
  default when 0, auto-expanded when > 0. Each entry:
  *"Day 4 · 12 Mar — Linda Hamilton (SARAH CONNOR) unavailable · Other
  shoot"*. Clicking an entry scrolls to that day.
- A small red dot on the day header of any day with a conflict.
- Dismissible per session (remembered in `localStorage`, per the app's
  existing pattern for such panels) — but re-appears if the conflict set
  changes.

### 6.3 On Day Out of Days

- The character's work-mark cell for the conflicting day gets a `--danger`
  ring (2px inset) around the existing letter code, in both the on-screen
  preview and the WeasyPrint PDF.
- A footnote below the DOOD grid: *"▨ Cast member unavailable on this
  day."* (only rendered when at least one conflict exists).
- Never changes the letter code itself or the day math — purely an overlay.

---

## 7. Page-level states

| State | Trigger | Treatment |
|---|---|---|
| **Loading** | initial fetch | `SkeletonList` — 6 row-height skeletons under a skeleton header. |
| **No characters** | breakdown not run / detected zero characters | `EmptyState`: icon, *"No characters yet"*, body *"Run the breakdown on your scenes to detect characters — then cast them here."*, primary button "Go to Scenes" → `/scenes/:id`. |
| **Characters, none cast** | breakdown done, zero casting rows | Full list renders (all rows "Not cast"). A one-line hint bar above the list: *"Click a character to add an actor, contacts, and availability."* Dismissible, `localStorage`. |
| **Some cast** | normal | As §3. |
| **Only orphans** | every casting row is orphaned (all breakdown chars gone) | Normal list of breakdown characters (all "Not cast") + the "Not in current breakdown" section below. |
| **No active schedule** | script has no `status='active'` schedule | No conflict UI anywhere. Availability editor in the drawer still works; a faint note under "Unavailable dates": *"Set a schedule to Active to check these dates against shoot days."* |
| **Load error** | fetch fails | Inline error card in the list area: *"Couldn't load casting. Check your connection and try again."* + "Retry". |

---

## 8. Copy reference

**Buttons / actions**
- `Add casting` (row, uncast)
- `Add unavailable dates` → inline: `Add`, `Cancel`
- `Replace`, `Remove` (headshot)
- `Delete casting` (drawer footer) → confirm dialog:
  title *"Delete casting for {CHARACTER}?"*, body *"This removes the actor,
  contacts, headshot, and availability for this character. It doesn't
  affect the breakdown."*, confirm *"Delete casting"* (destructive).

**Status control** — `Wishlist` · `Offer` · `Booked` · `Declined` ·
`Released`

**Field labels** — `Actor`, `Status`, `Headshot`, `Phone`, `Email`,
`Agent`, `Unavailable dates`, `Notes`.
`Agent` field placeholder: *"Agency, agent name, phone"*.
Unavailable-range reason placeholder: *"Reason (optional)"*.

**Empty / hint**
- No characters: *"No characters yet"* / *"Run the breakdown on your scenes
  to detect characters — then cast them here."*
- None cast hint: *"Click a character to add an actor, contacts, and
  availability."*
- Read-only: *"Only the owner and admins can edit casting."*
- Orphan: *"This character isn't in the latest breakdown — it may have been
  renamed or removed. These casting details are kept."*
- No schedule: *"Set a schedule to Active to check these dates against
  shoot days."*

**Errors**
- Save: *"Couldn't save — retry."*
- Headshot too large: *"That image is over 5 MB. Use a smaller file."*
- Headshot wrong type: *"Use a JPG, PNG, or WebP image."*
- Load: *"Couldn't load casting. Check your connection and try again."*
- Conflict entry: *"Day {n} · {date} — {actor} ({CHARACTER}) unavailable ·
  {reason}"* (reason omitted with its middle dot when blank).

**Voice:** sentence case everywhere except character names (uppercase, as
the breakdown renders them) and the `Cast` nav label. Active verbs. Errors
state what happened and the fix; no apologies.

---

## 9. Accessibility & quality floor

- Drawer: focus trap, Esc to close, focus returns to the triggering row
  (from the `Drawer` primitive — verify).
- Every row is a real `<button>` (or `role="button"` with key handling) with
  an accessible name: `"{CHARACTER} — {actor or 'not cast'}, {status}"`.
- Status conveyed by text label, not colour alone. Conflict pill has an
  `aria-label`; the `⚠` glyph is `aria-hidden`.
- Segmented status control is a radio group.
- Date fields are native `<input type="date">`.
- Headshot dropzone is keyboard-operable (Enter/Space opens the file
  picker) and has a visible focus ring.
- Respect `prefers-reduced-motion` for the drawer slide (the primitive
  should already).
- Colour contrast: all status text/bg pairs meet 4.5:1 on `--bg-card`
  (verify `released` grey-on-slate during build).
- Responsive to 360px. Drawer → full-screen sheet below 720px. No
  horizontal page scroll.

---

## 10. Out of scope for v1 (UI)

- Bulk actions (multi-select rows, bulk status change).
- CSV import UI.
- Inline editing on the row itself (all editing is in the drawer).
- Drag-to-reorder characters (order is breakdown-derived).
- A season-level cast board (additive later — see design spec §10).
- Printable cast list / contact sheet (that's sub-project E, call sheets).
- Photo gallery per actor (single headshot only).

---

## 11. Component / file inventory (for the plan)

New, under `frontend/src/components/cast/`:

- `CastPage.jsx` / `CastPage.css` — route component, list, filter bar,
  summary, states.
- `CastRow.jsx` — one character row (presentational).
- `CastingDetailPanel.jsx` / `.css` — the drawer, all sections, autosave.
- `UnavailabilityEditor.jsx` — the ranges list + add-row (used only inside
  the panel; split out because it owns its own request lifecycle).
- `StatusBadge.jsx` — thin wrapper over `Badge` mapping the 5 statuses to
  variants (or extend `Badge` with the variants directly).
- `ConflictPanel.jsx` — the collapsible panel for `ShootingSchedulePage`
  (imported there, not in `cast/` if a schedule-local home fits better).

Touched:

- `frontend/src/components/layout/SectionNav.jsx` — new tab + `activeKey`.
- `frontend/src/App.jsx` — new route.
- `frontend/src/services/apiService.js` — the 8 calls (design spec §6.3).
- `frontend/src/components/schedule/ShootingSchedulePage.jsx` — conflict
  panel + day-header dots.
- Day Out of Days render path (report preview component + `report_service`
  DOOD template) — conflict ring + footnote.
