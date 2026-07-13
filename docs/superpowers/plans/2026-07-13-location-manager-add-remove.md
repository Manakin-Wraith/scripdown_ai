# Location Manager — Add / Remove Grouping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the Location Manager panel to a parent-centric Add/Remove flow with neutral vocabulary, reusing the existing nest/unnest/rename backend unchanged.

**Architecture:** Single React component rework (`LocationManager.jsx`) plus its CSS. The `buildTree` grouping and all API calls (`nestLocation`, `unnestLocation`, `renameParentLocation`, `renameSubLocation`) already exist and are unchanged — only the controls, wiring, and copy change. Adding several locations at once loops the existing single-source `nestLocation` and refetches once via the existing `run` helper.

**Tech Stack:** React 18 (plain JSX, no TypeScript), Vite, existing `apiService.js`, `useToast`, `locationKey`/`subLocationLabel` utils.

## Global Constraints

- **Frontend only.** No change to any backend route, `apiService.js`, or database. Reuse `nestLocation(scriptId, source, parent)`, `unnestLocation(scriptId, parent, set)`, `renameParentLocation(scriptId, from, to)`, `renameSubLocation(scriptId, parent, from, to)` exactly as they are.
- **Neutral verbs only** in the UI: `+ Add`, `Add selected`, `Cancel`, `Remove`. No domain words ("rooms", "sets", "building", "main", "move under", "move out", "nest").
- **Two-level only:** the Add picker offers only other top-level locations that have no sub-locations of their own (`t.subs.length === 0`).
- **Parent-centric:** the grouping action lives on the parent (`+ Add`), never a `Move under…` on the child. Remove the existing `Move under…` `<select>`.
- **Rename behavior is unchanged:** inline edit, Enter commits, Escape cancels without committing (keep the `cancelRef` guard), blur commits.
- **Gate on `npm run build`** (repo lint is known-broken). Run it from `frontend/`.
- **Exact copy strings** (from the spec's Copy Reference):
  - Purpose header: `Group the locations you'll shoot together — add them under one heading so they schedule as a unit.`
  - `+ Add` · `Add selected` · `Cancel` · `Remove` · empty picker: `No other locations to add.`
  - Toasts: `Locations grouped` · `Location removed` · `Location renamed` · `Sub-location renamed`

---

### Task 1: Rework LocationManager to parent-centric Add/Remove

**Files:**
- Modify: `frontend/src/components/scenes/LocationManager.jsx` (full control/JSX rework; keep imports, `buildTree`, rename logic)
- Modify: `frontend/src/components/scenes/LocationManager.css` (add picker + Add-button styles; keep existing classes)

**Interfaces:**
- Consumes (unchanged, already imported): `nestLocation`, `unnestLocation`, `renameParentLocation`, `renameSubLocation` from `../../services/apiService`; `locationKey`, `subLocationLabel` from `../../utils/locationKey`; `useToast`.
- Produces: same component contract — `<LocationManager scriptId scenes onClose onChanged />`. No prop changes.

**Reference — current file** (`frontend/src/components/scenes/LocationManager.jsx`, 175 lines): keep lines 1–76 (imports, `buildTree`, `run`, `startEdit`, `commitEdit`, `onEditKey`) intact except the two edits below. Replace the `doNest`/`doUnnest`/`parentNames` block and the render body.

- [ ] **Step 1: Add picker state and reset**

In the component body, after `const cancelRef = useRef(false);` add:

```javascript
    const [addingUnder, setAddingUnder] = useState(null); // parent name whose Add picker is open
    const [picked, setPicked] = useState([]);             // checked source names
```

In the existing `run` helper's `finally` block, alongside `setEditing(null);`, add the picker reset:

```javascript
        } finally {
            setBusy(false);
            setEditing(null);
            setAddingUnder(null);
            setPicked([]);
        }
```

- [ ] **Step 2: Replace `doNest`/`doUnnest`/`parentNames` with Add/Remove handlers**

Delete the current block (lines ~78–89):

```javascript
    const doNest = (source, parentName) => {
        if (!parentName) return;
        run('Location nested', () => nestLocation(scriptId, source, parentName));
    };

    const doUnnest = (parent, setName) => {
        run('Location moved out', () => unnestLocation(scriptId, parent, setName));
    };

    // A top-level location may be nested under another only if it has no real
    // subs of its own (two-level constraint). Any other top-level is a valid target.
    const parentNames = tree.map((p) => p.name);
```

Replace with:

```javascript
    // Eligible to group under parent P: any OTHER top-level location that does
    // not already hold its own group (keeps grouping two-level).
    const eligibleFor = (parentName) =>
        tree.filter((t) => t.name !== parentName && t.subs.length === 0).map((t) => t.name);

    const openAdd = (parentName) => {
        setAddingUnder((cur) => (cur === parentName ? null : parentName));
        setPicked([]);
    };

    const togglePick = (name) =>
        setPicked((cur) => (cur.includes(name) ? cur.filter((n) => n !== name) : [...cur, name]));

    const doAddSelected = (parentName) => {
        const sources = picked;
        if (!sources.length) return;
        run('Locations grouped', async () => {
            let total = 0;
            for (const src of sources) {
                const res = await nestLocation(scriptId, src, parentName);
                total += res?.scenes_updated ?? 0;
            }
            return { scenes_updated: total };
        });
    };

    const doRemove = (parent, setName) => {
        run('Location removed', () => unnestLocation(scriptId, parent, setName));
    };
```

- [ ] **Step 3: Rework the render body**

Replace the returned JSX's `<div className="locmgr-body">…</div>` block. Keep the overlay, modal, header, and `renderName` helper unchanged; update the purpose header text and the per-parent row. New body:

```javascript
                <p className="locmgr-purpose">
                    Group the locations you'll shoot together — add them under one
                    heading so they schedule as a unit.
                </p>
                <div className="locmgr-body">
                    {tree.length === 0 && <p className="locmgr-empty">No locations yet.</p>}
                    {tree.map((parent) => {
                        const isAdding = addingUnder === parent.name;
                        const candidates = isAdding ? eligibleFor(parent.name) : [];
                        return (
                            <div key={parent.name} className="locmgr-parent">
                                <div className="locmgr-parent-row">
                                    <span className="locmgr-parent-name">
                                        {renderName('parent', null, parent.name)}
                                        <span className="locmgr-count">{parent.count}</span>
                                    </span>
                                    <button
                                        className="locmgr-add"
                                        disabled={busy}
                                        onClick={() => openAdd(parent.name)}
                                    >
                                        {isAdding ? 'Cancel' : '+ Add'}
                                    </button>
                                </div>
                                {parent.subs.map((sub) => (
                                    <div key={sub.name} className="locmgr-sub-row">
                                        <span className="locmgr-sub-name">
                                            {renderName('sub', parent.name, sub.name)}
                                            <span className="locmgr-count">{sub.count}</span>
                                        </span>
                                        <button
                                            className="locmgr-moveout"
                                            disabled={busy}
                                            onClick={() => doRemove(parent.name, sub.name)}
                                        >
                                            Remove
                                        </button>
                                    </div>
                                ))}
                                {isAdding && (
                                    <div className="locmgr-picker">
                                        {candidates.length === 0 && (
                                            <p className="locmgr-picker-empty">No other locations to add.</p>
                                        )}
                                        {candidates.map((name) => (
                                            <label key={name} className="locmgr-picker-row">
                                                <input
                                                    type="checkbox"
                                                    checked={picked.includes(name)}
                                                    onChange={() => togglePick(name)}
                                                    disabled={busy}
                                                />
                                                <span>{name}</span>
                                            </label>
                                        ))}
                                        {candidates.length > 0 && (
                                            <div className="locmgr-picker-actions">
                                                <button
                                                    className="locmgr-add"
                                                    disabled={busy || picked.length === 0}
                                                    onClick={() => doAddSelected(parent.name)}
                                                >
                                                    Add selected
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
```

Note: the `Remove` button keeps the existing `locmgr-moveout` CSS class (only its label text changes) so no CSS churn is needed for it.

- [ ] **Step 4: Add picker CSS**

Append to `frontend/src/components/scenes/LocationManager.css`:

```css
.locmgr-add {
    background: var(--gray-800, #1f2937); color: inherit;
    border: 1px solid var(--gray-700, #374151); border-radius: 6px;
    padding: 0.2rem 0.6rem; font-size: 0.78em; cursor: pointer;
}
.locmgr-add:hover:not(:disabled) { border-color: var(--primary-500, #f59e0b); }
.locmgr-add:disabled { opacity: 0.5; cursor: default; }
.locmgr-picker {
    margin: 0.4rem 0 0.2rem 1.6rem; padding: 0.4rem 0.5rem;
    border: 1px solid var(--gray-700, #374151); border-radius: 8px;
    background: var(--gray-800, #1f2937);
}
.locmgr-picker-empty { margin: 0; padding: 0.3rem 0.15rem; opacity: 0.7; font-size: 0.85em; }
.locmgr-picker-row {
    display: flex; align-items: center; gap: 0.5rem;
    padding: 0.2rem 0.15rem; font-size: 0.9em; cursor: pointer;
}
.locmgr-picker-row input { cursor: pointer; }
.locmgr-picker-actions { display: flex; justify-content: flex-end; padding-top: 0.35rem; }
```

- [ ] **Step 5: Verify the build passes**

Run: `cd frontend && npm run build`
Expected: build completes (`✓ built in …`), no errors referencing `LocationManager`.

- [ ] **Step 6: Manual sanity read of the diff**

Confirm no `Move under…`, `parentNames`, `doNest`, `(main)`, or `window.prompt` remain in `LocationManager.jsx`:
Run: `grep -nE "Move under|parentNames|doNest|\\(main\\)|window\\.prompt" frontend/src/components/scenes/LocationManager.jsx`
Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/scenes/LocationManager.jsx frontend/src/components/scenes/LocationManager.css
git commit -m "feat(locations): parent-centric Add/Remove grouping in Location Manager"
```

---

## Manual E2E (post-merge, user)

On the real script (`19ed4c73…`):
1. `+ Add` on VILLA → check `GARAGE / BACKROOM`, `MOODY BACKROOM`, `TAM'S ROOM` → `Add selected`; confirm all three group under VILLA in one action, keep their names, and the schedule groups them in the VILLA unit.
2. Click a grouped name → rename → confirm it sticks and the schedule label updates.
3. `Remove` on a grouped location → confirm it returns to standalone.
4. Confirm `+ Add` never lists a location that already holds a group; no `Move under…`, `(main)`, or browser prompt appears.
