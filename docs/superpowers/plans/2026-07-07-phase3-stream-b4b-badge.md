# Phase 3 · Stream B4b — Badge Adoption — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the 4 clean status-state pills to the shared `<Badge>` primitive (copy verbatim, color preserved), after extending `<Badge>` to forward `className`/`...rest`.

**Architecture:** Each bespoke pill (`<span className="…-badge …">…</span>`) becomes `<Badge variant="…" [icon={…}] [title/className via rest]>text</Badge>`. First, `components/ui/Badge.jsx` is extended to append an optional `className` and forward `...rest` (title/aria/etc.) onto its span, so an attributed or positioned pill converts without losing behavior. Bespoke CSS is pruned; where a pill carried layout (e.g. `margin-left:auto`), a minimal positioning rule is kept and re-attached via the appended `className`.

**Tech Stack:** React 18 + Vite (plain JSX, no TypeScript), lucide-react icons, plain CSS with design tokens in `frontend/src/index.css`.

## Global Constraints

- No test runner exists and live-drive is login-gated. Verification per task = `npm run build` green (from `frontend/`) + the task's grep invariant. No unit tests.
- `<Badge>` API after Task 1: `Badge({ variant='neutral'|'primary'|'success'|'warning'|'danger'|'info', size='sm'|'md', dot=false, icon, className='', children, ...rest })` → `<span class="ui-badge ui-badge--{variant} ui-badge--{size} {className}" {...rest}>`. The computed `ui-badge` classes are ALWAYS present (never overridden); `className` is appended; `...rest` (e.g. `title`) is forwarded. `icon` renders at 11px for `sm`, 13px for `md`.
- **Copy verbatim:** each badge's text must exactly match what it replaces (note MultiMergeModal uses "KEEP"/"OMIT"; SceneMergeModal uses "KEPT"/"OMITTED").
- **Color preserved via variant:** every mapping is green→`success` / red→`danger`; do not introduce a variant that changes the pill's color intent.
- Import `Badge` from the `ui` barrel: `import { Badge } from '../ui';` (all target files are `components/<domain>/*`, so `'../ui'`; extend an existing `../ui` import where present).
- CSS prune cascade-safe: delete a bespoke class family only after grep-confirming no remaining JSX uses it; keep sibling badge classes (e.g. `.scene-badge`, `.preview-badge`) untouched.
- **Staging discipline:** stage only the files a task changed (`git add <paths>`); never `git add .`/`-A`/`commit -a` (untracked `.claude/` must never be committed).
- Out of scope: all excluded badge categories (guarded `timeline-*`, semantic IE/time/type, dynamic-color dept/role/entity/category, count chips, WIP/auth areas, and the interactive `AnalysisStatusBadge`).

---

### Task 1: Extend `<Badge>` to forward `className` and `...rest`

Additive enhancement so attributed/positioned pills (a tooltip, a `margin-left:auto`) can adopt the primitive. Existing `<Badge>` calls pass no `className`/rest, so their output is unchanged.

**Files:**
- Modify: `frontend/src/components/ui/Badge.jsx`

**Interfaces:**
- Produces: `Badge({ variant, size, dot, icon, className, children, ...rest })` — `className` appended to the computed classes; `...rest` spread onto the span. Tasks 2–3 rely on `className` and `title` passthrough.

- [ ] **Step 1: Replace the component body**

Current `frontend/src/components/ui/Badge.jsx`:
```jsx
import './Badge.css';

/**
 * @param {{
 *  variant?: 'neutral'|'primary'|'success'|'warning'|'danger'|'info',
 *  size?: 'sm'|'md', dot?: boolean,
 *  icon?: React.ComponentType<{size?: number}>, children?: React.ReactNode
 * }} props
 */
const Badge = ({ variant = 'neutral', size = 'sm', dot = false, icon: Icon, children }) => (
  <span className={`ui-badge ui-badge--${variant} ui-badge--${size}`}>
    {dot && <span className="ui-badge-dot" />}
    {Icon && <Icon size={size === 'sm' ? 11 : 13} />}
    {children}
  </span>
);

export default Badge;
```
Replace with:
```jsx
import './Badge.css';

/**
 * @param {{
 *  variant?: 'neutral'|'primary'|'success'|'warning'|'danger'|'info',
 *  size?: 'sm'|'md', dot?: boolean,
 *  icon?: React.ComponentType<{size?: number}>, className?: string,
 *  children?: React.ReactNode
 * }} props
 * Extra props (title, aria-*, onClick, …) are forwarded onto the span.
 */
const Badge = ({ variant = 'neutral', size = 'sm', dot = false, icon: Icon, className = '', children, ...rest }) => (
  <span
    className={`ui-badge ui-badge--${variant} ui-badge--${size}${className ? ` ${className}` : ''}`}
    {...rest}
  >
    {dot && <span className="ui-badge-dot" />}
    {Icon && <Icon size={size === 'sm' ? 11 : 13} />}
    {children}
  </span>
);

export default Badge;
```
(Note: `className` and `...rest` are destructured OUT of props, so the spread cannot override the computed `ui-badge` classes.)

- [ ] **Step 2: Verify existing usage is unchanged + build**

Run (from `frontend/`):
```bash
grep -n "Badge" src/components/scenes/SceneList.jsx
```
Expected: still `import { EmptyState, Badge, Spinner } from '../ui';` and `<Badge variant="danger">OMIT</Badge>` — that call passes no `className`/rest, so it renders `ui-badge ui-badge--danger ui-badge--sm` exactly as before.

Run: `npm run build`
Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/Badge.jsx
git commit -m "feat(ui): forward className + rest props in <Badge>

Append an optional className and spread ...rest (title/aria/onClick) onto the
badge span so attributed/positioned pills can adopt the primitive; computed
ui-badge classes always win. Additive — existing usage unchanged. Part of B4b.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

### Task 2: scenes — status-badge (2 merge modals) + merge-recommended-badge

**Files:**
- Modify: `frontend/src/components/scenes/MultiMergeModal.jsx`
- Modify: `frontend/src/components/scenes/SceneMergeModal.jsx`
- Modify: `frontend/src/components/scenes/ScriptSummary.jsx`
- Modify: `frontend/src/components/scenes/SceneModals.css` (prune `.status-badge`)
- Modify: `frontend/src/components/scenes/ScriptSummary.css` (prune `.merge-recommended-badge`)

**Interfaces:**
- Consumes: `Badge` from `frontend/src/components/ui`.

- [ ] **Step 1: MultiMergeModal.jsx** — extend the ui import to `import { Modal, Button, Badge } from '../ui';`, then replace:
```jsx
                                    {keepSceneId === scene.id ? (
                                        <span className="status-badge kept">KEEP</span>
                                    ) : (
                                        <span className="status-badge omitted">OMIT</span>
                                    )}
```
with:
```jsx
                                    {keepSceneId === scene.id ? (
                                        <Badge variant="success">KEEP</Badge>
                                    ) : (
                                        <Badge variant="danger">OMIT</Badge>
                                    )}
```
(Leave the adjacent `<span className="scene-badge">…</span>` — excluded number label.)

- [ ] **Step 2: SceneMergeModal.jsx** — extend the ui import to `import { Modal, Button, Badge } from '../ui';`. There are TWO identical `status-badge` pairs (first-scene block and second-scene block). Replace each:
```jsx
                                {keepNumber === 'first' ? (
                                    <span className="status-badge kept">KEPT</span>
                                ) : (
                                    <span className="status-badge omitted">OMITTED</span>
                                )}
```
with:
```jsx
                                {keepNumber === 'first' ? (
                                    <Badge variant="success">KEPT</Badge>
                                ) : (
                                    <Badge variant="danger">OMITTED</Badge>
                                )}
```
and the second block:
```jsx
                                {keepNumber === 'second' ? (
                                    <span className="status-badge kept">KEPT</span>
                                ) : (
                                    <span className="status-badge omitted">OMITTED</span>
                                )}
```
with:
```jsx
                                {keepNumber === 'second' ? (
                                    <Badge variant="success">KEPT</Badge>
                                ) : (
                                    <Badge variant="danger">OMITTED</Badge>
                                )}
```
(Leave the `<span className="scene-badge">…</span>` labels.)

- [ ] **Step 3: ScriptSummary.jsx** — add `import { Badge } from '../ui';` (after the lucide import on line 2), then replace:
```jsx
                                    <span className="merge-recommended-badge">Recommended</span>
```
with:
```jsx
                                    <Badge variant="success">Recommended</Badge>
```

- [ ] **Step 4: Prune CSS**

In `SceneModals.css`, delete the `.status-badge`, `.status-badge.kept`, and `.status-badge.omitted` rules (grep-confirm no other JSX uses `status-badge` — only the two modals just converted). Keep `.scene-badge`, `.preview-badge`, and all other rules.

In `ScriptSummary.css`, delete the `.merge-recommended-badge` rule.

- [ ] **Step 5: Verify + commit**

Run (from `frontend/`):
```bash
grep -rn "status-badge\|merge-recommended-badge" src/components/scenes/MultiMergeModal.jsx src/components/scenes/SceneMergeModal.jsx src/components/scenes/ScriptSummary.jsx
```
Expected: no output.
```bash
grep -rn "status-badge\|merge-recommended-badge" src/components/scenes/SceneModals.css src/components/scenes/ScriptSummary.css
```
Expected: no output.

Run: `npm run build` — expected: succeeds.

```bash
git add frontend/src/components/scenes/MultiMergeModal.jsx frontend/src/components/scenes/SceneMergeModal.jsx frontend/src/components/scenes/ScriptSummary.jsx frontend/src/components/scenes/SceneModals.css frontend/src/components/scenes/ScriptSummary.css
git commit -m "refactor(scenes): adopt <Badge> for merge status pills

Convert status-badge (KEEP/OMIT, KEPT/OMITTED) to <Badge variant=success|danger>
and merge-recommended-badge to <Badge variant=success> (copy verbatim). Prune
the bespoke badge CSS. Part of Phase 3 Stream B4b.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

### Task 3: reports + board — shared-badge + strip-scheduled-badge

`strip-scheduled-badge` carries a `title` tooltip and `margin-left:auto` positioning — both preserved via Task 1's `...rest` (title) and `className` (positioning) passthrough.

**Files:**
- Modify: `frontend/src/components/reports/ReportBuilder.jsx` (+ `ReportBuilder.css`)
- Modify: `frontend/src/components/board/StripCard.jsx` (+ `StripCard.css`)

**Interfaces:**
- Consumes: `Badge` (with `className`/`...rest`) from Task 1.

- [ ] **Step 1: ReportBuilder.jsx** — extend the ui import to `import { Spinner, Button, Badge } from '../ui';` (keep the existing `Share2` lucide import). Replace:
```jsx
                                                        {report.is_public && (
                                                            <span className="shared-badge">
                                                                <Share2 size={10} />
                                                                Shared
                                                            </span>
                                                        )}
```
with:
```jsx
                                                        {report.is_public && (
                                                            <Badge variant="success" icon={Share2}>Shared</Badge>
                                                        )}
```

- [ ] **Step 2: StripCard.jsx** — add `import { Badge } from '../ui';` (after the lucide import on line 2; keep the existing `CalendarCheck` import). Replace:
```jsx
                {(isScheduled || strip.isScheduled) && (
                    <span
                        className="strip-scheduled-badge"
                        title={(scheduledDayLabel || strip.scheduledDayLabel) ? `Scheduled: ${scheduledDayLabel || strip.scheduledDayLabel}` : 'Scheduled'}
                    >
                        <CalendarCheck size={9} />
                        {(scheduledDayLabel || strip.scheduledDayLabel) || 'Sched'}
                    </span>
                )}
```
with:
```jsx
                {(isScheduled || strip.isScheduled) && (
                    <Badge
                        variant="success"
                        icon={CalendarCheck}
                        className="strip-scheduled-badge"
                        title={(scheduledDayLabel || strip.scheduledDayLabel) ? `Scheduled: ${scheduledDayLabel || strip.scheduledDayLabel}` : 'Scheduled'}
                    >
                        {(scheduledDayLabel || strip.scheduledDayLabel) || 'Sched'}
                    </Badge>
                )}
```

- [ ] **Step 3: Prune / reduce CSS**

In `ReportBuilder.css`, delete the `.shared-badge` rule (grep-confirm unused).

In `StripCard.css`, **reduce** `.strip-scheduled-badge` to only the positioning it must retain (the primitive now supplies color/padding/radius/font); replace the whole rule with:
```css
.strip-scheduled-badge {
    margin-left: auto;
    flex-shrink: 0;
}
```
(The `className="strip-scheduled-badge"` on the `<Badge>` re-applies this alongside the `ui-badge` classes.)

- [ ] **Step 4: Verify + commit**

Run (from `frontend/`):
```bash
grep -rn "shared-badge" src/components/reports/ReportBuilder.jsx src/components/reports/ReportBuilder.css
```
Expected: no output.
```bash
grep -n "strip-scheduled-badge" src/components/board/StripCard.jsx src/components/board/StripCard.css
```
Expected: `StripCard.jsx` shows the `className="strip-scheduled-badge"` on the `<Badge>`; `StripCard.css` shows only the reduced 2-line rule.

Run: `npm run build` — expected: succeeds.

```bash
git add frontend/src/components/reports/ReportBuilder.jsx frontend/src/components/reports/ReportBuilder.css frontend/src/components/board/StripCard.jsx frontend/src/components/board/StripCard.css
git commit -m "refactor(reports,board): adopt <Badge> for shared + scheduled pills

Convert shared-badge (icon={Share2}) and strip-scheduled-badge (icon +
tooltip via ...rest, margin-left:auto retained via className) to
<Badge variant=success>. Prune/reduce the bespoke CSS. Part of Phase 3 Stream B4b.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

## End-of-stream verification

After all 3 tasks, from `frontend/src`:

- `<Badge>` forwards props: `components/ui/Badge.jsx` destructures `className`/`...rest` and spreads rest onto the span; `SceneList.jsx`'s existing `<Badge>` is unchanged.
- Converted pills gone from JSX:
  ```bash
  grep -rn "className=\"status-badge\|merge-recommended-badge\|shared-badge\|className=\"strip-scheduled-badge" . --include="*.jsx"
  ```
  Returns nothing (the only `strip-scheduled-badge` occurrence is now the `className` prop on `<Badge>`, not a bespoke `<span className="strip-scheduled-badge">`).
- Each converted file imports and uses `Badge`:
  ```bash
  grep -rln "Badge" components/scenes/MultiMergeModal.jsx components/scenes/SceneMergeModal.jsx components/scenes/ScriptSummary.jsx components/reports/ReportBuilder.jsx components/board/StripCard.jsx
  ```
  Returns all five.
- Excluded badges untouched: `timeline-*`, `int-ext`/`ie-badge`, `bd-dept-badge`, count chips, `AnalysisStatusBadge`, etc. still present in their files.
- `npm run build` green.
- No test runner; live-drive login-gated. Correctness rests on build + per-task review + these invariants + before/after that every badge's text is verbatim, its color intent is preserved by the variant, and `strip-scheduled`'s tooltip + right-alignment survive.
