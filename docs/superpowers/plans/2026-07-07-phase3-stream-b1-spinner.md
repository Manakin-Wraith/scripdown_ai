# Phase 3 Stream B1 — Canonical Spinner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `<Spinner>` the one loading spinner across the app and collapse the duplicate `@keyframes spin` into a single global keyframe — no visual change except standardizing spin speed to 1s.

**Architecture:** Add one global `@keyframes spin` + `.spin` utility to `index.css` (Task 1), then per-domain batches convert plain loader JSX to `<Spinner>` and delete each file's local `@keyframes spin` / dead `.spin` rule. Semantic `<RefreshCw className="spin">` stays and falls through to the global rule.

**Tech Stack:** React 18 + Vite (plain JSX), lucide-react, plain CSS. Verification is `npm run build` green (no test runner exists).

## Global Constraints

**The conversion rule (apply to every in-scope file in each batch):**
- **JSX (convert):** replace `<Loader … className="spin" />` and `<Loader2 … className="spin" />` with `<Spinner size={N} />`, carrying the numeric `size` (omit `size` if the original had none). If the element has classes beyond `spin`, keep them and drop only `spin`: `<Loader size={18} className="status-icon processing spin" />` → `<Spinner size={18} className="status-icon processing" />`. Add `import { Spinner } from '<rel>/ui';` (barrel at `components/ui/index.js`; depth: files in `components/<domain>/` use `'../ui'`, files in `pages/` use `'../components/ui'`). Remove the `Loader`/`Loader2` specifier from the lucide-react import **only if** it has no other use left in the file.
- **JSX (keep):** leave `<RefreshCw className="spin">` and any non-`Loader` semantic spinner untouched — they animate via the new global `.spin`.
- **CSS:** delete the file's local `@keyframes spin`. Delete a local `.spin` (or equivalently-named, e.g. `.sp-spin`) rule **only if it solely sets the spin animation**; if such a rule sets additional still-needed properties (size/margin/color), keep those extra properties and drop only the `animation` line.
- **Do NOT double-animate:** never leave a `spin`/animation class on an element that became `<Spinner>` (the primitive self-animates via its own `ui-spin`).

**Never touch (exclusion list):** `pages/Admin/**`, `components/admin/**`, `components/campaigns/**`, `components/auth/**`, the auth pages (`LoginPage`, `ConfirmEmailPage`, `AuthCallbackPage`, `ResetPasswordPage`, `InvitePage`, `PaymentSuccessPage`), the six frozen WIP components (`pages/SettingsPage`, `pages/ScriptEditorPage`, `components/scenes/SceneManager`, `components/workspace/DepartmentWorkspace`, `components/scripts/ShootingScriptPreview`, `components/characters/CharacterProfile`), the primitive's own `Spinner.css`/`ui-spin`, and any non-spinner animation.

**Other:** Run commands from `frontend/`. Each batch is its own commit. `<Spinner>` API: `{ size = 16, label = 'Loading', className = '' }` → renders `<span class="ui-spinner" role="status">` wrapping `Loader2`, `color: currentColor`.

---

### Task 1: Global `@keyframes spin` + `.spin` utility in `index.css`

**Files:** Modify `frontend/src/index.css`

**Interfaces:** Produces the global `@keyframes spin` and `.spin` class that every later batch relies on when it deletes a file's local copies. Must land first.

- [ ] **Step 1: Append to `index.css`** (after the scrollbar rules at the end of the file)

```css

/* ========================================
   Canonical spin animation — one keyframe for the whole app.
   <Spinner> uses its own scoped ui-spin (Spinner.css); this global rule
   drives residual .spin icons (e.g. RefreshCw) after local copies are removed.
   ======================================== */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spin {
  animation: spin 1s linear infinite;
}
```

- [ ] **Step 2: Build** — `npm run build` → green. (Local `@keyframes spin`/`.spin` copies still exist and are identical, so duplicate definitions are harmless during the transition.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(ui): add global @keyframes spin + .spin utility (canonical spinner foundation)"
```

---

### Task 2: Reports domain

**Files (apply the conversion rule):**
- `frontend/src/components/reports/ExportOptionsModal.css`
- `frontend/src/components/reports/ReportBuilder.{jsx,css}`
- `frontend/src/components/reports/SharedReportView.{jsx,css}`
- `frontend/src/components/reports/ShareModal.{jsx,css}`
- `frontend/src/components/reports/Stripboard.{jsx,css}`

No known edge cases in this batch (plain `Loader`/`Loader2` + `spin`, and possibly `RefreshCw` to keep).

- [ ] **Step 1:** In each `.jsx`, convert plain `<Loader/Loader2 className="spin">` to `<Spinner size={N} />` per the rule; add `import { Spinner } from '../ui';`; drop now-unused `Loader`/`Loader2` imports; keep any `<RefreshCw className="spin">`.
- [ ] **Step 2:** In each `.css`, remove the local `@keyframes spin` and any `.spin` rule that solely animates.
- [ ] **Step 3: Build** — `npm run build` → green.
- [ ] **Step 4: Verify batch invariants**

```bash
cd frontend/src/components/reports
grep -rl "@keyframes spin" . || echo "no local keyframes (good)"
grep -rnE "<Loader2?[^>]*className=\"[^\"]*\bspin\b" . || echo "no plain-loader spin JSX (good)"
```
Expected: both "good".

- [ ] **Step 5: Commit** — `git add -A frontend/src/components/reports && git commit -m "refactor(ui): adopt Spinner in reports domain"`

---

### Task 3: Scenes + Schedule domains

**Files (in-scope only — SceneManager is EXCLUDED WIP, do not touch it):**
- `frontend/src/components/scenes/Dashboard.css`
- `frontend/src/components/scenes/SceneDetail.{jsx,css}`
- `frontend/src/components/scenes/SceneList.{jsx,css}`
- `frontend/src/components/scenes/SceneModals.css`
- `frontend/src/components/scenes/SceneViewer.{jsx,css}`
- `frontend/src/components/schedule/ShootingSchedulePage.jsx`

- [ ] **Step 1:** Apply the JSX conversion rule to each `.jsx` (import from `'../ui'`).
- [ ] **Step 2:** Apply the CSS rule to each `.css`.
- [ ] **Step 3: Build** → green.
- [ ] **Step 4: Verify**

```bash
cd frontend/src
for d in components/scenes components/schedule; do
  grep -rl "@keyframes spin" "$d" | grep -v SceneManager || echo "$d: no stray keyframes (good)"
  grep -rnE "<Loader2?[^>]*className=\"[^\"]*\bspin\b" "$d" | grep -v SceneManager || echo "$d: no plain-loader JSX (good)"
done
```

- [ ] **Step 5: Commit** — `git add -A frontend/src/components/scenes frontend/src/components/schedule && git commit -m "refactor(ui): adopt Spinner in scenes + schedule domains"`

---

### Task 4: Common + Layout + PDF domains

**Files:**
- `frontend/src/components/common/AnalysisProgressModal.{jsx,css}` — **edge case:** `<Loader size={18} className="status-icon processing spin" />` (line ~141) → `<Spinner size={18} className="status-icon processing" />`.
- `frontend/src/components/common/AnalysisStatusBadge.{jsx,css}`
- `frontend/src/components/common/AnalyzePrompt.{jsx,css}`
- `frontend/src/components/layout/Layout.css` (remove local `@keyframes spin`; the layout uses `.spin` on an indicator — verify it now resolves to the global rule) and `frontend/src/components/layout/TopBar.jsx`
- `frontend/src/components/pdf/PdfViewerPanel.{jsx,css}`

- [ ] **Step 1:** JSX conversions (import from `'../ui'`), including the AnalysisProgressModal multi-class edge case above. Keep any RefreshCw.
- [ ] **Step 2:** CSS rule per file. Note: `Layout.css` had its `.spin`/`@keyframes spin` used by the analysis indicator (`.analysis-indicator .spin`); after removing the local `@keyframes spin`, keep `.analysis-indicator .spin` only if that element is NOT converted to `<Spinner>` — if TopBar's indicator icon is converted, remove the rule; otherwise it falls through to the global keyframe.
- [ ] **Step 3: Build** → green.
- [ ] **Step 4: Verify** (per the same two greps, scoped to `components/common`, `components/layout`, `components/pdf`).
- [ ] **Step 5: Commit** — `git commit -m "refactor(ui): adopt Spinner in common + layout + pdf domains"`

---

### Task 5: Team + Notes + Feedback domains

**Files:**
- `frontend/src/components/team/InviteModal.{jsx,css}`
- `frontend/src/components/team/TeamDrawer.{jsx,css}`
- `frontend/src/components/notes/DepartmentNotesSection.{jsx,css}`
- `frontend/src/components/notes/NoteDrawer.{jsx,css}`
- `frontend/src/components/feedback/FeedbackDrawer.{jsx,css}`

- [ ] **Step 1–2:** Apply JSX + CSS rules (import from `'../ui'`); keep RefreshCw.
- [ ] **Step 3: Build** → green.
- [ ] **Step 4: Verify** (two greps scoped to `components/team`, `components/notes`, `components/feedback`).
- [ ] **Step 5: Commit** — `git commit -m "refactor(ui): adopt Spinner in team + notes + feedback domains"`

---

### Task 6: Board + Breakdown + Revisions + Workspace domains

**Files:**
- `frontend/src/components/board/ZoomableStripboard.{jsx,css}`
- `frontend/src/components/board/SchedulePopover.jsx` — **edge case:** `<Loader2 size={16} className="sp-spin" />` (line ~99) and `<Loader2 size={14} className="sp-spin" />` (line ~110) → `<Spinner size={16} />` / `<Spinner size={14} />`. Then find the `.sp-spin` rule (in `SchedulePopover.css` or `ZoomableStripboard.css`) and remove it if it solely animates; also remove its `@keyframes` if separate.
- `frontend/src/components/breakdown/BreakdownDrawer.{jsx,css}`
- `frontend/src/components/revisions/RevisionImportWizard.{jsx,css}`
- `frontend/src/components/workspace/CameraDeptView.jsx` (live component — NOT the WIP DepartmentWorkspace)

- [ ] **Step 1:** JSX conversions incl. the `sp-spin` edge case (import from `'../ui'`); keep RefreshCw.
- [ ] **Step 2:** CSS rule per file, incl. removing `.sp-spin`.
- [ ] **Step 3: Build** → green.
- [ ] **Step 4: Verify** (two greps scoped to `components/board`, `components/breakdown`, `components/revisions`, `components/workspace`; also `grep -rn "sp-spin" components/board` → expect none).
- [ ] **Step 5: Commit** — `git commit -m "refactor(ui): adopt Spinner in board + breakdown + revisions + workspace domains"`

---

### Task 7: Scripts + Script + Credits + Profile domains

**Files:**
- `frontend/src/components/scripts/ScriptLibrary.{jsx,css}` (LockScriptModal below)
- `frontend/src/components/scripts/ScriptTable.css`
- `frontend/src/components/scripts/LockScriptModal.{jsx,css}`
- `frontend/src/components/script/AnalysisStepper.css`
- `frontend/src/components/script/ScriptUpload.jsx` — **edge case:** `<Loader size={32} className="spin upload-spinner" />` (line ~195) → `<Spinner size={32} className="upload-spinner" />` (keep `.upload-spinner` if it sets size/margin, dropping only its `animation` line).
- `frontend/src/components/credits/CreditBalance.{jsx,css}`
- `frontend/src/pages/ProfilePage.{jsx,css}` — import from `'../components/ui'` (pages depth).

- [ ] **Step 1:** JSX conversions incl. the `upload-spinner` edge case; correct import depth per file (`components/*` → `'../ui'`, `pages/*` → `'../components/ui'`); keep RefreshCw.
- [ ] **Step 2:** CSS rule per file.
- [ ] **Step 3: Build** → green.
- [ ] **Step 4: Verify** (two greps scoped to `components/scripts`, `components/script`, `components/credits`, `pages/ProfilePage.*`).
- [ ] **Step 5: Commit** — `git commit -m "refactor(ui): adopt Spinner in scripts + script + credits + profile domains"`

---

## Post-Task: Whole-stream invariants + final review

- [ ] **Global invariant check** (from `frontend/src`):

```bash
# Exactly ONE @keyframes spin (index.css) + the primitive's ui-spin — among in-scope files.
grep -rn "@keyframes spin" . --include="*.css"
grep -rn "@keyframes ui-spin" . --include="*.css"
# No plain-loader spinner JSX remains in-scope (excluding the frozen WIP + auth):
grep -rnE "<Loader2?[^>]*className=\"[^\"]*\bspin\b" . --include="*.jsx" \
  | grep -vE "SceneManager|DepartmentWorkspace|ShootingScriptPreview|CharacterProfile|SettingsPage|ScriptEditorPage|components/auth/"
```
Expected: one `@keyframes spin` in `index.css`; the WIP/auth files are the only place any local `@keyframes spin` or plain-loader spin JSX still exists; the last grep prints nothing.

Then dispatch the final whole-branch code review (most capable model) per subagent-driven-development, and use superpowers:finishing-a-development-branch. Review focus: every converted site renders the same spinning icon (no double-animation, positioning classes preserved); no `Loader`/`Loader2` import left dangling or wrongly removed while still used; RefreshCw spins preserved; only the 4 known non-1s spinners changed speed; nothing in the exclusion list touched.

## Self-Review notes (author)

- **Spec coverage:** global keyframe/utility → Task 1; convert plain loaders + dedup per domain → Tasks 2–7 (all 30 in-scope CSS + 26 JSX files assigned to exactly one batch); RefreshCw kept (Global Constraints); invariants → Post-Task.
- **Edge cases mapped:** `status-icon processing spin` (Task 4), `sp-spin` (Task 6), `spin upload-spinner` (Task 7); `status-icon analyzing spin` is in SceneManager (excluded) — not assigned.
- **Ordering:** Task 1 lands the global rule first so every later local-copy deletion falls through safely.
- **Import depth:** `components/<domain>/*` → `'../ui'`; `pages/*` → `'../components/ui'` (called out in Tasks 1/7).
