# Phase 3 Stream D — Dead-CSS Deletion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete one orphaned CSS file and seven orphaned rule-families (left after Phase 1 pruning and the Stream A/C refactors), each proven unreferenced, with zero rendering change.

**Architecture:** Pure CSS removal — no JSX changes. Every deletion is gated on a whole-tree grep proving the selector's class token appears in zero `.jsx` files, so no element can reference it and rendering cannot change.

**Tech Stack:** React 18 + Vite (plain JSX), plain CSS. Verification is `npm run build` green (no test runner exists).

## Global Constraints

- **CSS only** — do not modify any `.jsx` file.
- **Delete only the enumerated targets.** Do not touch anything else, especially the verified-live keep-list: `.back-btn`, `.header-action-btn`(+`.primary`), `.sidebar-*`, `.logo-*`, `.user-avatar`, `no-sidebar`, `--sidebar-width-viewer`, and the six WIP route components + their CSS.
- **Each class must be re-verified at deletion time**: `grep -rn "<class>" --include="*.jsx" frontend/src` must return **zero** matches before its rule is removed. If any target shows a nonzero count, STOP and report it (do not delete) — it means the class became live again.
- For a rule whose selector list contains other (live) selectors, remove **only** the dead selector, not the whole rule.
- Run commands from repo root or `frontend/` as noted. Verify with `npm run build` from `frontend/`.

---

### Task 1: Remove the orphan file and seven orphaned rule-families

**Files:**
- Delete: `frontend/src/components/dashboard/Dashboard.css`
- Modify: `frontend/src/pages/ProfilePage.css`
- Modify: `frontend/src/components/scripts/ScriptLibrary.css`
- Modify: `frontend/src/components/script/ScriptUpload.css`
- Modify: `frontend/src/components/reports/Stripboard.css`
- Modify: `frontend/src/components/reports/ReportBuilder.css`

**Interfaces:** None. This task consumes nothing and produces nothing for other tasks.

- [ ] **Step 1: Pre-verify every target is unreferenced (0 JSX usages)**

Run from repo root:

```bash
cd frontend/src
for cls in profile-header profile-container library-header library-subtitle upload-header stripboard-header report-builder-header; do
  echo "[$(grep -rE "\b${cls}\b" --include="*.jsx" . | wc -l | tr -d ' ')] $cls"
done
# Orphan-file check (path-aware, not bare basename — dashboard/ shares a basename with scenes/):
grep -rn "dashboard/Dashboard.css\|dashboard/Dashboard'" --include="*.jsx" . || echo "dashboard/Dashboard.css: NOT imported (orphan confirmed)"
```

Expected: every class prints `[0]`, and the orphan-file line prints "NOT imported". If any class prints a nonzero count, STOP — do not delete that class's rules; report it as a blocker.

- [ ] **Step 2: Delete the orphan file**

```bash
git rm frontend/src/components/dashboard/Dashboard.css
```

- [ ] **Step 3: `ProfilePage.css` — remove `.profile-container` and the `.profile-header` family**

Delete these rules entirely (base + descendants + the media-query override), leaving every other rule in the file intact:
- `.profile-container { … }`
- `.profile-header { … }`
- `.profile-header .back-btn { … }` (descendant of the removed header — the live `.back-btn` base rules live in other files and are NOT touched)
- `.profile-header .back-btn:hover { … }`
- `.profile-header h1 { … }` (the top-level one)
- inside the `@media (max-width: 768px)` block: the `.profile-header h1 { font-size: 1.5rem; }` rule (remove just this rule; keep the surrounding media block and its other rules such as `.form-row`)

- [ ] **Step 4: `ScriptLibrary.css` — remove the `.library-header` family and `.library-subtitle`**

Delete:
- `.library-header { … }` (top-level)
- `.library-header h1 { … }`
- `.library-subtitle { … }`
- inside the `@media (max-width: 768px)` block: the `.library-header { flex-direction: column; … }` rule (remove just this rule; keep the `.upload-new-btn` rule and the rest of the media block)

- [ ] **Step 5: `ScriptUpload.css` — remove the `.upload-header` family**

Delete:
- `.upload-header { … }`
- `.upload-header h1 { … }`
- `.upload-header p { … }`

- [ ] **Step 6: `Stripboard.css` — remove the `.stripboard-header` family**

Delete:
- `.stripboard-header { … }` (top-level)
- `.stripboard-header h1 { … }`
- In the `@media print` rule `.stripboard-header, .stripboard-stats, .stripboard-filters { display: none !important; }` — remove **only** the `.stripboard-header,` selector line. Keep `.stripboard-stats` and `.stripboard-filters` (both live) and the rule body.

- [ ] **Step 7: `ReportBuilder.css` — remove the `.report-builder-header` family**

Delete:
- `.report-builder-header { … }` (top-level)
- `.report-builder-header h1 { … }`
- inside the `@media` block: the `.report-builder-header { flex-direction: column; gap: 1rem; }` rule (remove just this rule; keep the surrounding media block)

- [ ] **Step 8: Post-verify nothing dead remains and no live selector was harmed**

```bash
cd frontend/src
# The seven deleted classes should now appear in NO css either:
for cls in profile-header profile-container library-header library-subtitle upload-header stripboard-header report-builder-header; do
  echo "[$(grep -rE "\.${cls}\b" --include="*.css" . | wc -l | tr -d ' ')] .${cls} in CSS"
done
# Keep-list sanity: these must STILL be present in CSS (untouched):
grep -c "\.stripboard-stats" components/reports/Stripboard.css
grep -c "\.back-btn" components/metadata/ScriptHeader.css
```

Expected: each deleted class prints `[0]` in CSS; `.stripboard-stats` and `.back-btn` (base rules) still present (nonzero).

- [ ] **Step 9: Build**

Run: `cd frontend && npm run build`
Expected: builds green (only pre-existing unrelated warnings).

- [ ] **Step 10: Commit**

```bash
git add -A frontend/src
git commit -m "refactor(css): delete orphan dashboard/Dashboard.css + 7 dead header rule-families

All targets verified unreferenced (0 JSX usages). Removes CSS left orphaned
after Phase 1 pruning and the Stream C PageHeader adoption. No JSX changes."
```

---

## Post-Task: Final whole-branch review

After Task 1, dispatch the final whole-branch code review per subagent-driven-development, then use superpowers:finishing-a-development-branch. Review focus: confirm every deleted selector was genuinely unreferenced (0 JSX usages), the multi-selector print rule kept its live siblings (`.stripboard-stats`/`.stripboard-filters`), the media-query edits removed only the dead header rule (not the surrounding block), no keep-list class/token was touched, and no `.jsx` was modified.

## Self-Review notes (author)

- **Spec coverage:** orphan file (Dashboard.css) → Step 2; seven rule-families → Steps 3–7; verification method → Steps 1, 8, 9. All spec targets mapped.
- **Risk points handled:** `.profile-header .back-btn` is a descendant of the removed header, distinct from the live base `.back-btn` (defined in ScriptHeader.css and four other files) — deletion is scoped and safe. The Stripboard print rule is multi-selector — only the dead selector is removed. Media-query header rules are standalone within their blocks.
- **No placeholders:** every target names its exact selectors and the surrounding rule/block to preserve.
