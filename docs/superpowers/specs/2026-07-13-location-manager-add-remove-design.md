# Location Manager — Add / Remove Grouping — Design

**Date:** 2026-07-13
**Status:** Approved (design), pending implementation plan
**Builds on:** `2026-07-13-location-manager-nesting-design.md` (v2, shipped) — reuses
its backend verbatim.
**Areas (frontend only):** `frontend/src/components/scenes/LocationManager.jsx`,
`frontend/src/components/scenes/LocationManager.css`. No backend, API, or DB change.

## Problem

The shipped Location Manager groups locations correctly under the hood, but its
interaction model fights the user's mental model, so after three iterations it
still reads as confusing:

1. **Wrong direction.** The panel is *child-centric*: every stray location shows
   a `Move under… ▾` dropdown, so the user must hunt down each room and send it
   somewhere. It even offers `Move under…` on the biggest, most obvious *parent*
   (VILLA, 44 scenes) — asking to move the main location under something else,
   which is nonsensical.
2. **Domain-specific copy.** Labels like "rooms" assume a building. Every script
   differs — a resort's areas, a city's streets — so baked-in vocabulary misleads.
3. **Jargon leftovers.** "Move under" / "Move out" phrasing obscures a simple idea.

## What the user actually wants

After analysis, the user reconciles two jobs the location name does at once:

- **Creative:** rename a location to the name they'll use (e.g. `LUXURY SHOW HOUSE`
  → `THE VILLA`).
- **Logistics (scheduling):** declare that several locations are *one shooting
  location* so production planning groups and schedules them together.

The user works **from the main location outward**: they land on VILLA and *add*
the places that belong to it. Grouped locations **keep their own names** and show
as distinct setups under the VILLA heading (confirmed: not collapsed into one).

## Goal

Rework the Location Manager panel around three plain actions, neutral vocabulary,
and a parent-centric flow — with **zero backend change** (the existing
`nestLocation` / `unnestLocation` / rename endpoints already produce exactly this
grouping, stickily, and propagate to the schedule):

1. **Add** — on any top-level location, open a checklist of the user's other
   standalone locations and group the selected ones underneath it (they keep their
   names).
2. **Remove** — on a grouped location, pop it back out to its own standalone
   location.
3. **Rename** — click any name (top-level or grouped) to edit inline; sticky
   across re-analysis; propagates everywhere including the schedule.

## Non-Goals

- No backend, API-service, or database change. `nestLocation`, `unnestLocation`,
  `renameParentLocation`, `renameSubLocation` are reused exactly as they are.
- No domain vocabulary in the UI ("rooms", "sets", "building"). Verbs are **Add**
  and **Remove**, nothing more.
- Two-level only (unchanged): a location is either standalone, or grouped under
  exactly one top-level location.
- No AI or automatic grouping — every group is a manual user choice.
- No drag-and-drop.

## Architecture

Single component rework: `LocationManager.jsx`. The tree it builds from `scenes`
(`buildTree`, via `locationKey` / `subLocationLabel`) is unchanged — parents with
their real sub-locations, biggest first. Only the controls and copy change.

### The three actions map to existing API calls

| UI action | Existing call (unchanged) | Effect |
|-----------|---------------------------|--------|
| Add location X under parent P | `nestLocation(scriptId, X, P)` | X's scenes group under P, keep name X |
| Remove grouped location S from parent P | `unnestLocation(scriptId, P, S)` | S promoted back to its own standalone location |
| Rename top-level P → newName | `renameParentLocation(scriptId, P, newName)` | sticky rename, propagates |
| Rename grouped S under P → newName | `renameSubLocation(scriptId, P, S, newName)` | sticky rename, propagates |

### Layout

```
VILLA                      44   [ + Add ]
   └ GARAGE / BACKROOM      1   [ Remove ]
   └ MOODY BACKROOM         1   [ Remove ]
   └ TAM'S ROOM             2   [ Remove ]

RESORT POOL                 6   [ + Add ]
WEDDING VENUE               4   [ + Add ]
...
```

- Header: `Manage Locations` (unchanged) + close button.
- Purpose line (generic, no domain words): **"Group the locations you'll shoot
  together — add them under one heading so they schedule as a unit."**
- Each **top-level** row: name (click to rename) · scene count · **`+ Add`**
  button.
- Each **grouped** row (indented): name (click to rename) · scene count ·
  **`Remove`** button.
- No `Move under…` dropdown, no `(main)` row, no browser prompts (all already
  removed in v2; this spec removes the remaining `Move under…` select).

### The Add picker

Clicking `+ Add` on a parent P opens an inline multi-select panel listing
**eligible** locations (checkboxes). The user ticks any number and confirms with
an **`Add selected`** button; a **`Cancel`** button (or clicking `+ Add` again)
closes it without changes. Only one Add picker is open at a time.

**Eligible = a location that can be grouped under P** — i.e. every *other*
top-level location that is **not itself currently holding a group** (has no real
sub-locations). This preserves two-level grouping: a location that already holds
rooms cannot become a room. Concretely, from the built `tree`:
`eligible(P) = tree.filter(t => t.name !== P.name && t.subs.length === 0)`.

A parent whose only candidates are themselves grouped shows an empty picker with
a muted line: *"No other locations to add."*

### Adding several at once

`Add selected` groups every checked location under P, then refetches **once**:

```javascript
const doAddSelected = (parentName, sourceNames) => {
    if (!sourceNames.length) return;
    run('Locations grouped', async () => {
        let total = 0;
        for (const src of sourceNames) {
            const res = await nestLocation(scriptId, src, parentName);
            total += res?.scenes_updated ?? 0;
        }
        return { scenes_updated: total };
    });
};
```

`run(...)` (existing helper) already wraps in busy-guard, toast, single
`onChanged()` refetch, and error handling — so the batch refetches once, not
per-pick. Sequential `await` avoids hammering the backend and keeps ordering
deterministic; the set sizes here are small (a handful of locations).

### Remove

`Remove` on a grouped row S under parent P calls `unnestLocation(scriptId, P, S)`
via `run('Location removed', …)` — unchanged from the current `Move out` handler,
only the label/verb changes.

### Rename

Unchanged from v2: click a name → inline `<input>`; Enter commits via
`renameParentLocation` / `renameSubLocation`; Escape cancels without committing
(the `cancelRef` guard stays); blur commits. Sticky + propagating behavior lives
in the backend and is untouched.

## Component State

```javascript
const [busy, setBusy]         = useState(false);   // existing
const [editing, setEditing]   = useState(null);    // existing rename target
const [editValue, setEditValue] = useState('');    // existing
const cancelRef               = useRef(false);     // existing Esc guard
const [addingUnder, setAddingUnder] = useState(null); // NEW: parent name whose Add picker is open, or null
const [picked, setPicked]     = useState([]);      // NEW: checked source names in the open picker
```

Opening a picker sets `addingUnder = parentName`, `picked = []`. Confirm/cancel/
successful action resets `addingUnder = null`, `picked = []` (fold this reset into
the existing `run` `finally`, alongside `setEditing(null)`).

## Data Flow

```
User clicks "+ Add" on VILLA
  -> addingUnder = "VILLA"; picker lists standalone locations w/ no subs
User ticks GARAGE / BACKROOM, MOODY BACKROOM, TAM'S ROOM -> picked=[...3]
User clicks "Add selected"
  -> for each: nestLocation(scriptId, name, "VILLA")   (existing endpoint)
  -> single onChanged() refetch
     -> tree now shows the three under VILLA, each keeping its name
     -> schedule groups them in the VILLA unit
     -> re-analysis keeps them grouped (existing set_name alias stickiness)
```

## Error Handling / Edge Cases

- **Empty picker** (no eligible locations): show the muted "No other locations to
  add." line; `Add selected` disabled.
- **Zero checked** + `Add selected`: no-op (guarded), picker stays open.
- **One nest in a batch fails:** the `run` catch surfaces a toast; already-applied
  nests persist (each is its own committed backend write). Acceptable — the user
  re-opens Add for whatever didn't move. (No transactional batch endpoint; not
  worth the complexity for a handful of manual picks.)
- **Adding a location that has scenes but no subs under a parent that later gets
  renamed/merged:** already handled by the shipped backend (nest-alias re-point
  fix, commit `b05f774`).
- **Busy state:** all buttons and checkboxes `disabled={busy}` during any action
  (existing pattern).

## Testing / Verification

- **Frontend gated on `npm run build`** (repo lint is known-broken; build is the
  gate). The change is presentational + wiring to existing calls.
- **Backend unchanged** — the 54 existing location tests (resolver + routes) and
  the nest/unnest/rename endpoints already cover the data behavior; no new backend
  tests are in scope because no backend code changes.
- **Manual E2E on the real script (`19ed4c73…`):**
  1. `+ Add` on VILLA → check `GARAGE / BACKROOM`, `MOODY BACKROOM`, `TAM'S ROOM`
     → `Add selected`; confirm all three nest under VILLA in one action, keeping
     their names, and the schedule groups them in the VILLA unit.
  2. Click `TAM'S ROOM` (grouped) → rename → confirm it sticks and the schedule
     label updates.
  3. `Remove` on `MOODY BACKROOM` → confirm it returns to a standalone location.
  4. Confirm no `+ Add` control offers a location that already holds a group, and
     no `Move under…` / `(main)` / browser prompt appears anywhere.

## Copy Reference (exact strings)

- Purpose header: `Group the locations you'll shoot together — add them under one heading so they schedule as a unit.`
- Add button: `+ Add`
- Picker confirm: `Add selected`
- Picker cancel: `Cancel`
- Empty picker: `No other locations to add.`
- Remove button: `Remove`
- Toasts: `Locations grouped`, `Location removed`, `Location renamed`,
  `Sub-location renamed` (rename toasts unchanged from v2).
