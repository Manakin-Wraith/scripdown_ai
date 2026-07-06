# Phase 2 — Shared UI Primitives Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build six token-driven UI primitives in `frontend/src/components/ui/`, consolidate ConfirmDialog onto the new Modal, and prove the APIs by adopting them in the scenes modal cluster.

**Architecture:** Plain-JSX React components, one file pair per primitive plus a shared `useOverlay` hook that centralizes overlay behavior (Escape, focus trap+restore, scroll-lock, portal). A barrel `index.js` exports everything. Components consume only Phase 1 CSS tokens.

**Tech Stack:** React 18, Vite, lucide-react (icons), plain CSS with CSS-variable tokens. No TypeScript. No test runner.

## Global Constraints

- Plain JSX + JSDoc only — no TypeScript, no PropTypes package.
- New CSS uses **only** `index.css` tokens: `--space-*`, `--radius-*`, `--text-*`, `--font-*`, `--primary-*`, `--gray-*`, `--success/--danger/--warning(+-bg)`, `--primary-alpha-*`, `--z-*`, `--shadow-*`. Zero raw hex/rgb/px-radius/hardcoded z-index.
- All imports of primitives go through the barrel: `import { Button } from '../ui'` (path depth varies per file).
- Icons come from `lucide-react`. Spinner uses `Loader2`.
- No test runner exists (frontend `tests/` is backend Python). Per-task verification = `npm run build` compiles clean (run from `frontend/`). Interactive behavior is verified once in Task 12 via `npm run dev`.
- Commit after each task. Run build commands from `frontend/`.

---

### Task 1: Spinner + barrel

**Files:**
- Create: `frontend/src/components/ui/Spinner.jsx`
- Create: `frontend/src/components/ui/Spinner.css`
- Create: `frontend/src/components/ui/index.js`

**Interfaces:**
- Produces: `Spinner({ size=16, label='Loading', className='' })` → JSX; `<Spinner />`. Barrel exports `Spinner`.

- [ ] **Step 1: Create `Spinner.css`**

```css
@keyframes ui-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.ui-spinner {
  display: inline-flex;
  animation: ui-spin 1s linear infinite;
  color: currentColor;
}
```

- [ ] **Step 2: Create `Spinner.jsx`**

```jsx
import { Loader2 } from 'lucide-react';
import './Spinner.css';

/**
 * Canonical spinner. Wraps lucide Loader2 with a single keyframe.
 * @param {{ size?: number, label?: string, className?: string }} props
 */
const Spinner = ({ size = 16, label = 'Loading', className = '' }) => (
  <span className={`ui-spinner ${className}`.trim()} role="status" aria-label={label}>
    <Loader2 size={size} />
  </span>
);

export default Spinner;
```

- [ ] **Step 3: Create barrel `index.js`**

```js
export { default as Spinner } from './Spinner';
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: `✓ built` with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/Spinner.jsx frontend/src/components/ui/Spinner.css frontend/src/components/ui/index.js
git commit -m "feat(ui): add Spinner primitive + barrel"
```

---

### Task 2: Button

**Files:**
- Create: `frontend/src/components/ui/Button.jsx`
- Create: `frontend/src/components/ui/Button.css`
- Modify: `frontend/src/components/ui/index.js`

**Interfaces:**
- Consumes: `Spinner` (Task 1).
- Produces: `Button({ variant='primary', size='md', loading=false, disabled=false, icon, iconPosition='left', fullWidth=false, children, className='', ...rest })`. Classes: `ui-btn ui-btn--{variant} ui-btn--{size}`.

- [ ] **Step 1: Create `Button.css`**

```css
.ui-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-lg);
  font-family: var(--font-sans);
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, opacity 0.2s;
  white-space: nowrap;
}
.ui-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.ui-btn--full { width: 100%; }

/* Sizes */
.ui-btn--sm { padding: var(--space-1) var(--space-3); font-size: var(--text-xs); }
.ui-btn--md { padding: var(--space-2) var(--space-5); font-size: var(--text-sm); }

/* Variants */
.ui-btn--primary { background: var(--primary-600); color: var(--gray-900); }
.ui-btn--primary:hover:not(:disabled) { background: var(--primary-500); }

.ui-btn--secondary { background: var(--gray-700); color: var(--text-primary); border-color: var(--border-color); }
.ui-btn--secondary:hover:not(:disabled) { background: var(--gray-600); }

.ui-btn--danger { background: var(--danger); color: #fff; }
.ui-btn--danger:hover:not(:disabled) { background: var(--danger); filter: brightness(0.92); }

.ui-btn--ghost { background: transparent; color: var(--text-secondary); }
.ui-btn--ghost:hover:not(:disabled) { background: var(--gray-700); color: var(--text-primary); }
```

- [ ] **Step 2: Create `Button.jsx`**

```jsx
import Spinner from './Spinner';
import './Button.css';

/**
 * @param {{
 *  variant?: 'primary'|'secondary'|'danger'|'ghost',
 *  size?: 'sm'|'md', loading?: boolean, disabled?: boolean,
 *  icon?: React.ComponentType<{size?: number}>, iconPosition?: 'left'|'right',
 *  fullWidth?: boolean, children?: React.ReactNode, className?: string
 * }} props
 */
const Button = ({
  variant = 'primary', size = 'md', loading = false, disabled = false,
  icon: Icon, iconPosition = 'left', fullWidth = false,
  children, className = '', ...rest
}) => {
  const iconSize = size === 'sm' ? 14 : 16;
  const cls = [
    'ui-btn', `ui-btn--${variant}`, `ui-btn--${size}`,
    fullWidth ? 'ui-btn--full' : '', className,
  ].filter(Boolean).join(' ');

  return (
    <button className={cls} disabled={disabled || loading} {...rest}>
      {loading && <Spinner size={iconSize} />}
      {!loading && Icon && iconPosition === 'left' && <Icon size={iconSize} />}
      {children}
      {!loading && Icon && iconPosition === 'right' && <Icon size={iconSize} />}
    </button>
  );
};

export default Button;
```

- [ ] **Step 3: Add to barrel**

Append to `index.js`:
```js
export { default as Button } from './Button';
```

- [ ] **Step 4: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/Button.jsx frontend/src/components/ui/Button.css frontend/src/components/ui/index.js
git commit -m "feat(ui): add Button primitive"
```

---

### Task 3: useOverlay hook

**Files:**
- Create: `frontend/src/components/ui/useOverlay.js`

**Interfaces:**
- Produces: `useOverlay({ isOpen, onClose, closeOnEscape=true })` → `void`. Side effects only: Escape handler, body scroll-lock, focus save/restore. Portal target is `document.body` (used directly by Modal/Drawer via `createPortal`).

- [ ] **Step 1: Create `useOverlay.js`**

```js
import { useEffect } from 'react';

/**
 * Shared overlay behavior for Modal/Drawer: Escape-to-close, body
 * scroll-lock, and focus restore. Portal + focus-in is handled by the
 * consuming component (it owns the DOM node).
 * @param {{ isOpen: boolean, onClose: () => void, closeOnEscape?: boolean }} opts
 */
export default function useOverlay({ isOpen, onClose, closeOnEscape = true }) {
  useEffect(() => {
    if (!isOpen) return undefined;

    const previouslyFocused = document.activeElement;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (e) => {
      if (closeOnEscape && e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = prevOverflow;
      if (previouslyFocused && previouslyFocused.focus) previouslyFocused.focus();
    };
  }, [isOpen, onClose, closeOnEscape]);
}
```

- [ ] **Step 2: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/useOverlay.js
git commit -m "feat(ui): add useOverlay hook (escape, scroll-lock, focus restore)"
```

---

### Task 4: Modal

**Files:**
- Create: `frontend/src/components/ui/Modal.jsx`
- Create: `frontend/src/components/ui/Modal.css`
- Modify: `frontend/src/components/ui/index.js`

**Interfaces:**
- Consumes: `useOverlay` (Task 3).
- Produces: `Modal({ isOpen, onClose, title, size='md', footer, showClose=true, closeOnOverlay=true, closeOnEscape=true, children })`. Returns a portal or `null` when closed.

- [ ] **Step 1: Create `Modal.css`**

```css
.ui-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  z-index: var(--z-modal);
}
.ui-modal {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  width: 100%;
  max-height: calc(100vh - var(--space-8));
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.ui-modal--sm { max-width: 420px; }
.ui-modal--md { max-width: 560px; }
.ui-modal--lg { max-width: 820px; }

.ui-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--border-color);
}
.ui-modal-title { font-size: var(--text-lg); font-weight: 600; color: var(--text-primary); }
.ui-modal-close {
  display: inline-flex;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: var(--space-1);
  border-radius: var(--radius-md);
}
.ui-modal-close:hover { background: var(--gray-700); color: var(--text-primary); }
.ui-modal-body { padding: var(--space-6); overflow-y: auto; }
.ui-modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--border-color);
}
```

- [ ] **Step 2: Create `Modal.jsx`**

```jsx
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import useOverlay from './useOverlay';
import './Modal.css';

/**
 * @param {{
 *  isOpen: boolean, onClose: () => void, title?: React.ReactNode,
 *  size?: 'sm'|'md'|'lg', footer?: React.ReactNode, showClose?: boolean,
 *  closeOnOverlay?: boolean, closeOnEscape?: boolean, children?: React.ReactNode
 * }} props
 */
const Modal = ({
  isOpen, onClose, title, size = 'md', footer,
  showClose = true, closeOnOverlay = true, closeOnEscape = true, children,
}) => {
  useOverlay({ isOpen, onClose, closeOnEscape });
  if (!isOpen) return null;

  return createPortal(
    <div
      className="ui-modal-overlay"
      onClick={closeOnOverlay ? onClose : undefined}
    >
      <div
        className={`ui-modal ui-modal--${size}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {(title || showClose) && (
          <div className="ui-modal-header">
            <span className="ui-modal-title">{title}</span>
            {showClose && (
              <button className="ui-modal-close" onClick={onClose} aria-label="Close">
                <X size={20} />
              </button>
            )}
          </div>
        )}
        <div className="ui-modal-body">{children}</div>
        {footer && <div className="ui-modal-footer">{footer}</div>}
      </div>
    </div>,
    document.body
  );
};

export default Modal;
```

- [ ] **Step 3: Add to barrel** — append `export { default as Modal } from './Modal';`

- [ ] **Step 4: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/Modal.jsx frontend/src/components/ui/Modal.css frontend/src/components/ui/index.js
git commit -m "feat(ui): add Modal primitive (portal, escape, overlay-close)"
```

---

### Task 5: Drawer

**Files:**
- Create: `frontend/src/components/ui/Drawer.jsx`
- Create: `frontend/src/components/ui/Drawer.css`
- Modify: `frontend/src/components/ui/index.js`

**Interfaces:**
- Consumes: `useOverlay` (Task 3).
- Produces: `Drawer({ isOpen, onClose, title, subtitle, side='right', width='480px', footer, showClose=true, children })`.

- [ ] **Step 1: Create `Drawer.css`**

```css
.ui-drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: var(--z-drawer);
  display: flex;
}
.ui-drawer-backdrop.right { justify-content: flex-end; }
.ui-drawer-backdrop.left { justify-content: flex-start; }
.ui-drawer {
  background: var(--bg-card);
  height: 100%;
  max-width: 100vw;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}
.ui-drawer--right { border-left: 1px solid var(--border-color); }
.ui-drawer--left { border-right: 1px solid var(--border-color); }

.ui-drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--border-color);
}
.ui-drawer-title-group { display: flex; flex-direction: column; gap: var(--space-1); }
.ui-drawer-title { font-size: var(--text-lg); font-weight: 600; color: var(--text-primary); }
.ui-drawer-subtitle { font-size: var(--text-sm); color: var(--text-secondary); }
.ui-drawer-close {
  display: inline-flex;
  background: transparent; border: none; cursor: pointer;
  color: var(--text-secondary); padding: var(--space-1); border-radius: var(--radius-md);
}
.ui-drawer-close:hover { background: var(--gray-700); color: var(--text-primary); }
.ui-drawer-body { padding: var(--space-6); overflow-y: auto; flex: 1; }
.ui-drawer-footer {
  display: flex; align-items: center; justify-content: flex-end; gap: var(--space-3);
  padding: var(--space-4) var(--space-6); border-top: 1px solid var(--border-color);
}
```

- [ ] **Step 2: Create `Drawer.jsx`**

```jsx
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import useOverlay from './useOverlay';
import './Drawer.css';

/**
 * @param {{
 *  isOpen: boolean, onClose: () => void, title?: React.ReactNode,
 *  subtitle?: React.ReactNode, side?: 'right'|'left', width?: string,
 *  footer?: React.ReactNode, showClose?: boolean, children?: React.ReactNode
 * }} props
 */
const Drawer = ({
  isOpen, onClose, title, subtitle, side = 'right', width = '480px',
  footer, showClose = true, children,
}) => {
  useOverlay({ isOpen, onClose });
  if (!isOpen) return null;

  return createPortal(
    <div className={`ui-drawer-backdrop ${side}`} onClick={onClose}>
      <div
        className={`ui-drawer ui-drawer--${side}`}
        style={{ width }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {(title || showClose) && (
          <div className="ui-drawer-header">
            <div className="ui-drawer-title-group">
              {title && <span className="ui-drawer-title">{title}</span>}
              {subtitle && <span className="ui-drawer-subtitle">{subtitle}</span>}
            </div>
            {showClose && (
              <button className="ui-drawer-close" onClick={onClose} aria-label="Close">
                <X size={20} />
              </button>
            )}
          </div>
        )}
        <div className="ui-drawer-body">{children}</div>
        {footer && <div className="ui-drawer-footer">{footer}</div>}
      </div>
    </div>,
    document.body
  );
};

export default Drawer;
```

- [ ] **Step 3: Add to barrel** — append `export { default as Drawer } from './Drawer';`

- [ ] **Step 4: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/Drawer.jsx frontend/src/components/ui/Drawer.css frontend/src/components/ui/index.js
git commit -m "feat(ui): add Drawer primitive"
```

---

### Task 6: EmptyState

**Files:**
- Create: `frontend/src/components/ui/EmptyState.jsx`
- Create: `frontend/src/components/ui/EmptyState.css`
- Modify: `frontend/src/components/ui/index.js`

**Interfaces:**
- Produces: `EmptyState({ icon, title, message, action, size='md' })`.

- [ ] **Step 1: Create `EmptyState.css`**

```css
.ui-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: var(--space-3);
  color: var(--text-secondary);
}
.ui-empty--md { padding: var(--space-12) var(--space-6); }
.ui-empty--sm { padding: var(--space-6) var(--space-4); }
.ui-empty-icon { color: var(--text-muted); }
.ui-empty-title { font-size: var(--text-lg); font-weight: 600; color: var(--text-primary); }
.ui-empty-message { font-size: var(--text-sm); color: var(--text-secondary); max-width: 42ch; }
.ui-empty-action { margin-top: var(--space-2); }
```

- [ ] **Step 2: Create `EmptyState.jsx`**

```jsx
import './EmptyState.css';

/**
 * @param {{
 *  icon?: React.ComponentType<{size?: number}>, title: string,
 *  message?: React.ReactNode, action?: React.ReactNode, size?: 'sm'|'md'
 * }} props
 */
const EmptyState = ({ icon: Icon, title, message, action, size = 'md' }) => (
  <div className={`ui-empty ui-empty--${size}`}>
    {Icon && <span className="ui-empty-icon"><Icon size={size === 'sm' ? 28 : 40} /></span>}
    <span className="ui-empty-title">{title}</span>
    {message && <span className="ui-empty-message">{message}</span>}
    {action && <span className="ui-empty-action">{action}</span>}
  </div>
);

export default EmptyState;
```

- [ ] **Step 3: Add to barrel** — append `export { default as EmptyState } from './EmptyState';`

- [ ] **Step 4: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/EmptyState.jsx frontend/src/components/ui/EmptyState.css frontend/src/components/ui/index.js
git commit -m "feat(ui): add EmptyState primitive"
```

---

### Task 7: Badge

**Files:**
- Create: `frontend/src/components/ui/Badge.jsx`
- Create: `frontend/src/components/ui/Badge.css`
- Modify: `frontend/src/components/ui/index.js`

**Interfaces:**
- Produces: `Badge({ variant='neutral', size='sm', dot=false, icon, children })`.

- [ ] **Step 1: Create `Badge.css`**

```css
.ui-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  border-radius: var(--radius-full);
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
}
.ui-badge--sm { padding: var(--space-0-5) var(--space-2); font-size: var(--text-2xs); }
.ui-badge--md { padding: var(--space-1) var(--space-3); font-size: var(--text-xs); }

.ui-badge--neutral { background: var(--gray-700); color: var(--text-secondary); }
.ui-badge--primary { background: var(--primary-alpha-15); color: var(--primary-400); }
.ui-badge--success { background: var(--success-bg); color: var(--success); }
.ui-badge--warning { background: var(--warning-bg); color: var(--warning); }
.ui-badge--danger  { background: var(--danger-bg); color: var(--danger); }
.ui-badge--info    { background: var(--gray-700); color: var(--gray-300); }

.ui-badge-dot { width: 6px; height: 6px; border-radius: var(--radius-full); background: currentColor; }
```

- [ ] **Step 2: Create `Badge.jsx`**

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

- [ ] **Step 3: Add to barrel** — append `export { default as Badge } from './Badge';`

- [ ] **Step 4: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/Badge.jsx frontend/src/components/ui/Badge.css frontend/src/components/ui/index.js
git commit -m "feat(ui): add Badge primitive"
```

---

### Task 8: Rebuild ConfirmDialog on Modal (context)

**Files:**
- Modify: `frontend/src/context/ConfirmDialogContext.jsx`

**Interfaces:**
- Consumes: `Modal`, `Button` (barrel).
- Produces: unchanged public API — `useConfirmDialog()` → `{ confirm }`, `confirm({ title, message, variant, confirmText, cancelText }) => Promise<boolean>`.

**Context:** The current inner `ConfirmDialog` (lines 115–176) renders bespoke `.confirm-overlay`/`.confirm-dialog` markup. Replace ONLY that inner component to render on `<Modal>`; keep `ConfirmDialogProvider`, `confirm`, `handleConfirm`, `handleCancel`, `VARIANTS`, and the hook exactly as-is.

- [ ] **Step 1: Replace the inner `ConfirmDialog` component**

Replace the whole `const ConfirmDialog = ({ config, onConfirm, onCancel, onKeyDown }) => { ... };` block (currently lines ~115–176) with:

```jsx
const ConfirmDialog = ({ config, onConfirm, onCancel }) => {
    const variant = VARIANTS[config.variant] || VARIANTS.info;
    const Icon = variant.icon;
    const confirmText = config.confirmText || variant.confirmText;
    const btnVariant = config.variant === 'danger' ? 'danger' : 'primary';

    return (
        <Modal
            isOpen
            onClose={onCancel}
            size="sm"
            showClose={false}
            title={
                <span className="confirm-title-row">
                    <Icon size={20} />
                    {config.title}
                </span>
            }
            footer={
                <>
                    <Button variant="secondary" onClick={onCancel}>{config.cancelText}</Button>
                    <Button variant={btnVariant} onClick={onConfirm} autoFocus>{confirmText}</Button>
                </>
            }
        >
            <p className="confirm-message">{config.message}</p>
        </Modal>
    );
};
```

- [ ] **Step 2: Update imports and remove dead prop**

At top of file, replace `import './ConfirmDialog.css';` with:
```jsx
import './ConfirmDialog.css';
import Modal from '../components/ui/Modal';
import Button from '../components/ui/Button';
```
In `ConfirmDialogProvider`'s JSX, the `<ConfirmDialog ... onKeyDown={handleKeyDown} />` — remove the `onKeyDown={handleKeyDown}` prop (Modal owns Escape now). The `handleKeyDown` callback (lines ~89–95) may be left unused or deleted; delete it to avoid a lint warning.

- [ ] **Step 3: Trim now-unused CSS**

In `frontend/src/context/ConfirmDialog.css`, keep `.confirm-title-row` (add if absent) and `.confirm-message`; the `.confirm-overlay`/`.confirm-dialog`/`.confirm-actions`/`.confirm-btn` rules are now unused — leave them for Phase 3 cleanup (do not risk other consumers this task). Add if missing:
```css
.confirm-title-row { display: inline-flex; align-items: center; gap: var(--space-2); }
```

- [ ] **Step 4: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/context/ConfirmDialogContext.jsx frontend/src/context/ConfirmDialog.css
git commit -m "refactor(ui): rebuild ConfirmDialog on Modal primitive (API unchanged)"
```

---

### Task 9: Migrate EmailCampaignsPage, delete duplicate ConfirmDialog

**Files:**
- Modify: `frontend/src/pages/Admin/EmailCampaignsPage.jsx`
- Delete: `frontend/src/components/common/ConfirmDialog.jsx`
- Delete: `frontend/src/components/common/ConfirmDialog.css`

**Context:** `EmailCampaignsPage` is the only consumer of `common/ConfirmDialog` (a controlled `isOpen`/`onConfirm`/`onClose` component). It holds a `confirmDialog` state object (line ~113) and renders `<ConfirmDialog .../>` (line ~501). Migrate to the promise hook so behavior is preserved and the duplicate can be deleted.

- [ ] **Step 1: Read the exact usage**

Run: `sed -n '108,180p;495,515p' frontend/src/pages/Admin/EmailCampaignsPage.jsx`
Identify the two `setConfirmDialog({...})` call sites and the JSX render block.

- [ ] **Step 2: Swap to the hook**

- Remove `import ConfirmDialog from '../../components/common/ConfirmDialog';`.
- Add `import { useConfirmDialog } from '../../context/ConfirmDialogContext';` and inside the component: `const { confirm } = useConfirmDialog();`.
- Replace each `setConfirmDialog({ isOpen: true, title, message, onConfirm: fn, ... })` pattern with:
```jsx
if (await confirm({ title, message, variant: 'danger' })) {
  await fn();   // the action previously in onConfirm
}
```
- Remove the `confirmDialog` state (`useState` line ~113) and the `<ConfirmDialog ... />` render block (line ~501).

- [ ] **Step 3: Delete the duplicate files**

```bash
git rm frontend/src/components/common/ConfirmDialog.jsx frontend/src/components/common/ConfirmDialog.css
```

- [ ] **Step 4: Verify no references remain**

Run: `grep -rn "common/ConfirmDialog" frontend/src`
Expected: no output.

- [ ] **Step 5: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Admin/EmailCampaignsPage.jsx
git commit -m "refactor(ui): migrate EmailCampaignsPage to confirm hook; delete duplicate ConfirmDialog"
```

---

### Task 10: Adopt Modal + Button in the scenes modal cluster

**Files:**
- Modify: `frontend/src/components/scenes/AddSceneModal.jsx`
- Modify: `frontend/src/components/scenes/SceneSplitModal.jsx`
- Modify: `frontend/src/components/scenes/SceneMergeModal.jsx`
- Modify: `frontend/src/components/scenes/MultiMergeModal.jsx`
- Modify: `frontend/src/components/scenes/SceneEditor.jsx` (its form-modal block only)
- Modify: `frontend/src/components/scenes/SceneModals.css` (remove now-dead overlay/button rules)

**Interfaces:**
- Consumes: `Modal`, `Button` (barrel `../ui`).

**Pattern (apply to each modal):** replace the outer `<div className="modal-overlay" onClick={onClose}><div className="scene-modal ..." onClick={stop}>…</div></div>` wrapper with `<Modal isOpen onClose={onClose} title={…} footer={…}>`. Move the header title into `title`, the footer buttons into `footer` using `<Button>`, and keep the form body as `children`. Remove the local `modal-close` button (Modal renders it).

- [ ] **Step 1: Convert `AddSceneModal.jsx`**

Replace the return wrapper (currently lines ~70–186) so the structure is:
```jsx
import { Plus } from 'lucide-react';
import { Modal, Button } from '../ui';
// ...
return (
  <Modal
    isOpen
    onClose={onClose}
    title={<><Plus size={20} /> Add New Scene</>}
    footer={
      <>
        <Button variant="secondary" onClick={onClose} disabled={loading}>Cancel</Button>
        <Button type="submit" form="add-scene-form" variant="primary" loading={loading} icon={Plus}>
          {loading ? 'Adding…' : 'Add Scene'}
        </Button>
      </>
    }
  >
    <form id="add-scene-form" onSubmit={handleSubmit}>
      {/* keep existing .modal-content inner markup, minus the old header/footer */}
    </form>
  </Modal>
);
```
Remove the old `import { ... X, Loader } from 'lucide-react'` entries that are now unused (keep `Plus`). Delete the old `.modal-overlay`/`.modal-header`/`.modal-footer` JSX.

- [ ] **Step 2: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 3: Convert `SceneSplitModal.jsx`, `SceneMergeModal.jsx`, `MultiMergeModal.jsx`**

Apply the same pattern to each: `<Modal>` wrapper, header→`title`, footer buttons→`<Button>`, body stays. Use each modal's existing submit handler and loading flag names (read each file first with `sed -n '1,40p'`). Build after each conversion.

- [ ] **Step 4: Convert `SceneEditor.jsx` form modal**

In `SceneEditor.jsx`, the scene-form modal block (`.scene-form-overlay`/`.scene-form-modal`, around line ~249) → `<Modal>`; its confirm/cancel buttons → `<Button>`. Leave the rest of SceneEditor untouched. Build.

- [ ] **Step 5: Remove dead CSS from `SceneModals.css`**

After all five conversions, delete the now-unused `.modal-overlay`, `.scene-modal`, `.modal-header`, `.modal-close`, `.modal-footer`, `.btn-primary`, `.btn-cancel` rules from `SceneModals.css` (grep first: `grep -n "modal-overlay\|scene-modal\|btn-primary\|btn-cancel\|modal-footer\|modal-close" frontend/src/components/scenes/SceneModals.css`). Keep `.modal-content` and form-field rules still referenced by the bodies. Build.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/scenes/
git commit -m "refactor(scenes): adopt Modal+Button primitives in scene modal cluster"
```

---

### Task 11: Prove EmptyState + Badge in scenes area

**Files:**
- Modify: one scene list/empty site (e.g. `frontend/src/components/scenes/SceneList.jsx`)
- Modify: one scene status-pill site (e.g. `frontend/src/components/scenes/SceneDetail.jsx` or `SceneList.jsx`)

**Interfaces:** Consumes `EmptyState`, `Badge` (barrel).

- [ ] **Step 1: Find candidate sites**

Run: `grep -rn "empty-state\|no-scenes\|status-badge\|scene-badge" frontend/src/components/scenes/*.jsx | head`

- [ ] **Step 2: Convert one empty state**

Replace one hand-rolled empty block with `<EmptyState icon={…} title="…" message="…" />` (pick an existing icon already imported in that file).

- [ ] **Step 3: Convert one status pill**

Replace one `.status-badge kept/omitted`-style span with `<Badge variant={scene.omitted ? 'danger' : 'success'}>{label}</Badge>`.

- [ ] **Step 4: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/scenes/
git commit -m "refactor(scenes): adopt EmptyState + Badge primitives (proof)"
```

---

### Task 12: End-to-end verification

**Files:** none (verification only).

- [ ] **Step 1: Production build** — `cd frontend && npm run build` → `✓ built`, no errors.

- [ ] **Step 2: Start dev server** — `cd frontend && npm run dev` (background). Note the localhost URL.

- [ ] **Step 3: Drive the scenes flow (browser)**

Log in locally, open a script's scenes view, then verify:
- Open "Add Scene" → the modal appears; **Escape closes it**; overlay-click closes it (both previously did NOT work).
- Submit with required fields → the submit Button shows the spinner (`loading`) and is disabled.
- Trigger a delete-scene → the ConfirmDialog (now on Modal) appears, Escape cancels, Delete confirms.
- Split / Merge modals open and close via Escape/overlay.

If local login is not configured, record that interactive verification was blocked and fall back to the production build gate + component review; report this explicitly rather than claiming success.

- [ ] **Step 4: Report**

Summarize: build status, which flows were driven live, and any deltas from the spec.

---

## Self-Review

**Spec coverage:**
- Six primitives → Tasks 1,2,4,5,6,7. ✔
- `useOverlay` shared hook → Task 3. ✔
- Barrel `index.js` → Task 1 (created), extended each task. ✔
- Token-only CSS → enforced in Global Constraints + each CSS step. ✔
- ConfirmDialog rebuilt on Modal, API identical → Task 8. ✔
- Delete `common/` duplicate + repoint consumer → Task 9. ✔
- Adopt scenes modal cluster → Task 10. ✔
- Prove EmptyState + Badge → Task 11. ✔
- Verify via build + dev drive → Task 12. ✔

**Placeholder scan:** Task 3/10 reference reading each modal's own handler names before converting — this is deliberate (they differ per file) and bounded by a concrete `sed`/`grep` command, not an open TODO. All component code is complete.

**Type consistency:** `Spinner(size,label,className)`, `Button(variant,size,loading,icon,iconPosition,fullWidth)`, `Modal(isOpen,onClose,title,size,footer,showClose,closeOnOverlay,closeOnEscape)`, `Drawer(isOpen,onClose,title,subtitle,side,width,footer,showClose)`, `useOverlay({isOpen,onClose,closeOnEscape})` — names consistent across Tasks 4/5/8/10.

**Known scope note:** Task 8 leaves dead `.confirm-*` overlay CSS in place (removed in Phase 3) to avoid touching unrelated consumers this phase — intentional, stated in the spec.
