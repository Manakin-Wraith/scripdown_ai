# Phase 3 Stream B2 — Button Adoption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the in-scope generic-`btn-*` buttons (~14 `<button>` across 5 files) to the `<Button>` primitive, and consolidate the 8 scattered `.btn-*` CSS definitions into one canonical global set in `index.css` — standardizing the primary button to solid `--primary-600`.

**Architecture:** JSX batches swap `<button className="btn-X">` for `<Button variant="Y">` (children kept verbatim). A final CSS task adds a canonical global `.btn-*` set (matching the primitive) so the un-migrated excluded-area buttons that depend on the global cascade keep working, then deletes the 8 local duplicate defs.

**Tech Stack:** React 18 + Vite (plain JSX), lucide-react, plain CSS with design tokens. Verification is `npm run build` green (no test runner).

## Global Constraints

**The conversion rule (faithful element swap — apply to each in-scope `<button>` using a standalone generic `btn-primary`/`btn-secondary`/`btn-tertiary` class):**
- Replace `<button className="btn-primary" …attrs…>…children…</button>` with `<Button variant="primary" …attrs…>…children…</Button>`. Mapping: `btn-primary`→`variant="primary"`, `btn-secondary`→`variant="secondary"`, `btn-tertiary`→`variant="ghost"`.
- **Keep ALL other attributes** (`onClick`, `disabled`, `type`, `form`, `title`, `aria-*`) — they pass through the primitive's `...rest`.
- **Keep ALL children verbatim**, including conditional loading content like `{loading ? <><Spinner size={18}/> Analyzing…</> : <>Preview <ArrowRight size={18}/></>}` and inline icons. Do NOT use the primitive's `loading` prop here (it would drop the dynamic "Analyzing…/Generating…" microcopy) and do NOT use the `icon` prop (keep the icon child to preserve its exact size). This keeps behavior 100% identical; only the button's base styling changes to the primitive (the intended standardization).
- If the class has an extra non-generic token, keep it via `className`: `className="btn-primary generate-btn"` → `<Button variant="primary" className="generate-btn">`.
- Add `import { Button } from '../ui';` (all target files are in `components/<domain>/`). If the file already imports from `'../ui'` (e.g. `Spinner`), add `Button` to that existing import.

**Do NOT convert:**
- `<Link>`/`<a>` elements that carry `btn-primary` (e.g. `SceneViewer.jsx:556` `<Link to="/upload" className="btn-primary">`) — the primitive renders a `<button>`, which would break navigation/semantics. Leave them; they keep the canonical global `.btn-primary` class (Task 3).
- Bespoke button classes (e.g. `upgrade-btn-primary`, toolbar/pill classes) — out of scope.
- Anything in admin/campaigns/auth/WIP.

**Other:** Run from `frontend/`. `<Button>` API: `{ variant, size='md', loading, disabled, icon, iconPosition, fullWidth, className, ...rest }` → `<button class="ui-btn ui-btn--{variant} ui-btn--{size}">`.

---

### Task 1: Reports domain buttons

**Files:** `frontend/src/components/reports/ExportOptionsModal.jsx`, `frontend/src/components/reports/ReportBuilder.jsx`

**Buttons to convert (keep children verbatim):**
- `ExportOptionsModal.jsx:224` `btn-secondary` "Cancel" (`onClick={onClose}`, `disabled={loading}`) → `<Button variant="secondary" …>`.
- `ExportOptionsModal.jsx:231` `btn-primary` (`onClick={handleGenerate}`, `disabled={loading}`) whose children are the `{loading ? <><span className="spinner"/> Generating…</> : <><Download size={16}/> Generate Report</>}` block → `<Button variant="primary" …>` keeping that whole child block.
- `ReportBuilder.jsx:323` `btn-primary generate-btn` (`onClick={handleGenerate}`, `disabled={isGenerating}`) with the `{isGenerating ? <><Spinner size={16}/> Generating…</> : …}` block → `<Button variant="primary" className="generate-btn" …>` keeping children.

- [ ] **Step 1:** Add `import { Button } from '../ui';` to each file (ReportBuilder already imports `Spinner` from `'../ui'` — extend that import). Apply the conversion rule to the three buttons.
- [ ] **Step 2: Build** — `npm run build` → green.
- [ ] **Step 3: Verify** — `grep -nE "<button[^>]*className=\"(btn-|[^\"]* btn-)(primary|secondary|tertiary)" frontend/src/components/reports/*.jsx` returns nothing (no `<button>` generic-btn left in reports).
- [ ] **Step 4: Commit** — `git add -A frontend/src/components/reports && git commit -m "refactor(ui): adopt Button in reports domain"`

---

### Task 2: Script + Team + Revisions domain buttons

**Files:** `frontend/src/components/script/ScriptUpload.jsx`, `frontend/src/components/team/InviteModal.jsx`, `frontend/src/components/revisions/RevisionImportWizard.jsx`

**Buttons to convert (keep children verbatim, incl. inline icons and loading conditionals):**
- `ScriptUpload.jsx:278` `btn-secondary` "View Full Script" (child `<FileText size={18}/>` + text) → `<Button variant="secondary" onClick={goToSceneViewer}>` keeping the icon child.
- `ScriptUpload.jsx:289` `btn-tertiary` "Upload Different File" → `<Button variant="ghost" onClick={resetUpload}>`.
- `ScriptUpload.jsx:329` `btn-primary` "View Scenes" (trailing `<ArrowRight size={18}/>`) → `<Button variant="primary" onClick={goToSceneViewer}>` keeping children.
- `ScriptUpload.jsx:336` `btn-tertiary` "Upload Another" → `<Button variant="ghost" onClick={resetUpload}>`.
- `InviteModal.jsx:331` `btn-secondary` "Invite Another" → `<Button variant="secondary" onClick={sendAnotherInvite}>`.
- `InviteModal.jsx:337` `btn-primary` "Done" → `<Button variant="primary" onClick={onClose}>`.
- `RevisionImportWizard.jsx:333` `btn-secondary` "Cancel" (`onClick={handleClose}`) → `<Button variant="secondary" …>`.
- `RevisionImportWizard.jsx:337` `btn-primary` (`onClick={handlePreview}`, `disabled={!file || loading}`) with the `{loading ? <><Spinner size={18}/> Analyzing…</> : <>Preview Changes <ArrowRight size={18}/></>}` block → `<Button variant="primary" …>` keeping children.
- `RevisionImportWizard.jsx:358` `btn-secondary` "Back" (`onClick={() => setStep(1)}`) → `<Button variant="secondary" …>`.
- `RevisionImportWizard.jsx:362` `btn-primary` (`onClick={handleImport}`, `disabled={loading}`) with the `{loading ? <><Spinner size={18}/> Importing…</> : <>Apply Changes <CheckCircle size={18}/></>}` block → `<Button variant="primary" …>` keeping children.
- `RevisionImportWizard.jsx:382` `btn-primary` "Done" (`onClick={handleClose}`) → `<Button variant="primary" …>`.

- [ ] **Step 1:** Add `import { Button } from '../ui';` to each file (RevisionImportWizard already imports `Spinner` from `'../ui'` — extend it). Apply the conversion rule to all 11 buttons.
- [ ] **Step 2: Build** — `npm run build` → green.
- [ ] **Step 3: Verify** — `grep -nE "<button[^>]*className=\"(btn-|[^\"]* btn-)(primary|secondary|tertiary)" frontend/src/components/{script,team,revisions}/*.jsx` returns nothing.
- [ ] **Step 4: Commit** — `git add -A frontend/src/components/script frontend/src/components/team frontend/src/components/revisions && git commit -m "refactor(ui): adopt Button in script + team + revisions domains"`

---

### Task 3: CSS consolidation — canonical global `.btn-*` + delete local defs

**Files:**
- Modify: `frontend/src/index.css` (add the canonical global set)
- Modify (delete `.btn-*` rule families from): `frontend/src/components/reports/ExportOptionsModal.css`, `frontend/src/components/reports/ReportBuilder.css`, `frontend/src/components/revisions/RevisionImportWizard.css`, `frontend/src/components/scenes/SceneEditor.css`, `frontend/src/components/scenes/SceneModals.css`, `frontend/src/components/scenes/SceneViewer.css`, `frontend/src/components/script/ScriptUpload.css`, `frontend/src/components/team/InviteModal.css`

**Interfaces:** Consumes Tasks 1–2 (all in-scope `<button>` generic-btn converted). The canonical global must exist BEFORE the local defs are deleted so cascade-dependent excluded-area buttons (and the SceneViewer `<Link>`) keep their styling.

- [ ] **Step 1: Pre-verify no in-scope `<button>` generic-btn remains**

```bash
cd frontend/src
EXCL="pages/Admin/|components/admin/|components/campaigns/|components/auth/|LoginPage|ConfirmEmailPage|AuthCallbackPage|ResetPasswordPage|InvitePage|PaymentSuccessPage|SceneManager|DepartmentWorkspace|ShootingScriptPreview|CharacterProfile|SettingsPage|ScriptEditorPage"
grep -rnE "<button[^>]*className=\"(btn-|[^\"]* btn-)(primary|secondary|tertiary)" --include="*.jsx" . | grep -vE "$EXCL" || echo "no in-scope <button> generic-btn (good)"
```
Expected: "good". (A `<Link className="btn-primary">` in SceneViewer may still match a broader grep — that is expected and stays; this grep targets `<button>` only.)

- [ ] **Step 2: Add the canonical global set to `index.css`** (append near the end, after the spin block). It mirrors the primitive's `.ui-btn` base + md size + primary/secondary/ghost variants:

```css

/* ========================================
   Canonical legacy button classes — visually match the <Button> primitive
   (components/ui/Button.css). For un-migrated buttons (mostly excluded areas)
   and link-styled-as-button (e.g. SceneViewer's /upload Link). Migrated
   buttons use <Button>. One definition replaces the old scattered per-file copies.
   ======================================== */
.btn-primary, .btn-secondary, .btn-tertiary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-5);
  border: 1px solid transparent;
  border-radius: var(--radius-lg);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, opacity 0.2s;
  white-space: nowrap;
  text-decoration: none;
}
.btn-primary:disabled, .btn-secondary:disabled, .btn-tertiary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary { background: var(--primary-600); color: var(--gray-900); }
.btn-primary:hover:not(:disabled) { background: var(--primary-500); }
.btn-secondary { background: var(--gray-700); color: var(--text-primary); border-color: var(--border-color); }
.btn-secondary:hover:not(:disabled) { background: var(--gray-600); }
.btn-tertiary { background: transparent; color: var(--text-secondary); }
.btn-tertiary:hover:not(:disabled) { background: var(--gray-700); color: var(--text-primary); }
```

(The `text-decoration: none` is added so the `<Link>` in SceneViewer renders like a button.)

- [ ] **Step 3: Delete the local `.btn-*` rule families** from the 8 CSS files listed above. In each file remove every rule whose selector is `.btn-primary`, `.btn-secondary`, or `.btn-tertiary` — including their `:hover`, `:disabled`, and descendant (`.btn-primary svg`, `.btn-primary:hover` etc.) variants, and any inside media queries. Do NOT touch bespoke button classes (e.g. `.upgrade-btn-*`, `.generate-btn`, `.import-btn`) or any non-`btn-*` rules.

- [ ] **Step 4: Build** — `npm run build` → green.

- [ ] **Step 5: Verify invariants**

```bash
cd frontend/src
echo "-- .btn-* defs remaining in-scope (expect only index.css; plus untouched excluded SignupSuccess/PersonalEmailModal) --"
grep -rlE "\.btn-(primary|secondary|tertiary)\s*\{" --include="*.css" . | grep -vE "pages/Admin/|components/admin/|components/campaigns/|components/auth/"
echo "-- the 8 target files should no longer define .btn-* --"
grep -rlE "\.btn-(primary|secondary|tertiary)\s*\{" components/reports components/revisions components/scenes components/script components/team && echo "!! still present" || echo "clean"
```
Expected: the first command lists only `index.css`; the second prints "clean".

- [ ] **Step 6: Commit** — `git add -A frontend/src && git commit -m "refactor(css): consolidate scattered .btn-* defs into one canonical global (cascade-safe)"`

---

## Post-Task: Final review

Dispatch the final whole-branch code review (most capable model) per subagent-driven-development, then use superpowers:finishing-a-development-branch. Review focus: every converted button preserves its onClick/disabled/type and children (esp. the loading-conditional microcopy and inline icons); no `<Link>`/`<a>` was converted to `<Button>`; the canonical global visually matches the primitive (so excluded-area + SceneViewer-Link buttons are unchanged); exactly one `.btn-*` def remains in-scope (index.css); no bespoke button class (`upgrade-btn-*`, `generate-btn`) was deleted; build green. The intended visual deltas are only: the ~7 gradient primary buttons → solid, and unified padding/radius across the converted buttons.

## Self-Review notes (author)

- **Spec coverage:** JSX conversions (5 files, ~14 buttons) → Tasks 1–2; canonical global + delete 8 local defs → Task 3; invariants → Task 3 Step 5 + final review.
- **Cascade safety:** the canonical global is added (Step 2) before the local defs are deleted (Step 3), and Task 3 is gated on Tasks 1–2 completing (no in-scope `<button>` generic-btn remains).
- **Link handling:** SceneViewer's `<Link className="btn-primary">` is explicitly NOT converted; it relies on the canonical global (with `text-decoration: none`).
- **Loading/icon props:** deliberately NOT used — children kept verbatim to preserve dynamic microcopy and exact icon sizes; the only intended change is button base styling.
