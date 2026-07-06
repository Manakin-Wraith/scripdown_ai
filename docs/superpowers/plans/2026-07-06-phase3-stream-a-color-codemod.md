# Phase 3 · Stream A — Color-Token Codemod Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace in-scope raw color literals with design tokens via an allowlist codemod, unify legacy indigo/blue brand accents → amber, and tokenize the semantic timeline palette — with zero unintended visual change.

**Architecture:** A committed Node script (`scripts/ui/color-codemod.mjs`) holds a mapping table and rewrites only exact-matched literals, reporting everything it leaves behind. It runs per-domain batch with a `npm run build` + unmapped-report review gate on each. Semantic timeline literals are tokenized in a targeted pass *before* the board/schedule batch. Context-sensitive tail (white/black, emerald/teal greens, non-timeline purples, dark ambers) is triaged by a fixed decision tree, not auto-mapped.

**Tech Stack:** Node (ESM script, no deps), CSS custom properties, Vite build.

## Global Constraints

- Touch CSS values and `index.css` only. No JSX, no CSS rule deletion, no selector changes.
- In-scope = `frontend/src/**/*.css` EXCEPT `pages/Admin/**`, `components/admin/**`, `components/campaigns/**`, auth pages (`LoginPage`,`ConfirmEmailPage`,`AuthCallbackPage`,`ResetPasswordPage`,`InvitePage`,`PaymentSuccessPage`), and `components/ui/**`.
- The codemod is an **allowlist**: only literals in the mapping table are replaced; everything else is left byte-identical and printed to the unmapped report.
- Class named for a color must never render a different color: `.blue`/`.indigo`/`.green` modifier classes and their values are OUT of the auto table (manual triage only).
- No test runner exists; per-task gate is `npm run build` (run from `frontend/`) + the script's report. Commit per domain batch. End commit messages with the `Co-Authored-By: Claude Fable 5` and `Claude-Session` trailers.

---

### Task 1: Add semantic timeline tokens to index.css

**Files:**
- Modify: `frontend/src/index.css` (append to `:root`, after the `--scrim` block)

**Interfaces:**
- Produces tokens: `--timeline-dream`, `--timeline-fantasy`, `--timeline-flashback` and their `-bg` variants. `--timeline-montage`/`--timeline-title-card` intentionally NOT added (they equal `--primary-500` / `--gray-400`; timeline CSS will reference those directly).

- [ ] **Step 1: Add the tokens**

Insert into `:root` (after the `--scrim-soft` line):
```css
  /* Semantic timeline codes (montage → --primary-500, title_card → --gray-400) */
  --timeline-dream: #3b82f6;
  --timeline-dream-bg: rgba(59, 130, 246, 0.15);
  --timeline-fantasy: #ec4899;
  --timeline-fantasy-bg: rgba(236, 72, 153, 0.15);
  --timeline-flashback: #a855f7;
  --timeline-flashback-bg: rgba(168, 85, 247, 0.15);
```

- [ ] **Step 2: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 3: Commit**
```bash
git add frontend/src/index.css
git commit -m "feat(ui): add semantic timeline color tokens"
```

---

### Task 2: Write the codemod script

**Files:**
- Create: `scripts/ui/color-codemod.mjs`

**Interfaces:**
- Produces CLI: `node scripts/ui/color-codemod.mjs <file...>` — rewrites files in place, prints per-file `replacements` and `unmapped` literals. Flag `--dry` = report only, no write.

- [ ] **Step 1: Write the script**

```js
#!/usr/bin/env node
// Allowlist color→token codemod. Rewrites ONLY exact-matched literals.
// Usage: node scripts/ui/color-codemod.mjs [--dry] <file.css> [more.css ...]
import { readFileSync, writeFileSync } from 'node:fs';

// --- Mapping table: normalized-literal -> replacement -------------------
// Hex keys are lowercase. rgba keys have NO spaces.
const MAP = {
  // neutrals (slate + cool-gray consolidation)
  '#f8fafc': 'var(--gray-50)',
  '#f1f5f9': 'var(--gray-100)', '#f3f4f6': 'var(--gray-100)',
  '#e2e8f0': 'var(--gray-200)', '#e5e7eb': 'var(--gray-200)',
  '#cbd5e1': 'var(--gray-300)', '#d1d5db': 'var(--gray-300)',
  '#94a3b8': 'var(--gray-400)', '#9ca3af': 'var(--gray-400)',
  '#64748b': 'var(--gray-500)', '#6b7280': 'var(--gray-500)',
  '#475569': 'var(--gray-600)', '#4b5563': 'var(--gray-600)',
  '#334155': 'var(--gray-700)', '#374151': 'var(--gray-700)',
  '#1e293b': 'var(--gray-800)', '#1f2937': 'var(--gray-800)',
  '#0f172a': 'var(--gray-900)', '#111827': 'var(--gray-900)',
  '#020617': 'var(--gray-950)',
  // amber scale
  '#fffbeb': 'var(--primary-50)', '#fef3c7': 'var(--primary-100)',
  '#fde68a': 'var(--primary-200)', '#fcd34d': 'var(--primary-300)',
  '#fbbf24': 'var(--primary-400)', '#f59e0b': 'var(--primary-500)',
  '#d97706': 'var(--primary-600)', '#b45309': 'var(--primary-700)',
  // legacy indigo brand -> amber
  '#6366f1': 'var(--primary-500)', '#4f46e5': 'var(--primary-600)',
  '#818cf8': 'var(--primary-400)', '#a5b4fc': 'var(--primary-300)',
  '#4338ca': 'var(--primary-700)',
  // status (danger variants collapse to --danger; slight accepted shift)
  '#22c55e': 'var(--success)',
  '#ef4444': 'var(--danger)', '#dc2626': 'var(--danger)', '#f87171': 'var(--danger)',
  // amber alpha tints
  'rgba(245,158,11,0.05)': 'var(--primary-alpha-05)',
  'rgba(245,158,11,0.1)': 'var(--primary-alpha-10)',
  'rgba(245,158,11,0.15)': 'var(--primary-alpha-15)',
  'rgba(245,158,11,0.2)': 'var(--primary-alpha-20)',
  'rgba(245,158,11,0.3)': 'var(--primary-alpha-30)',
  'rgba(245,158,11,0.4)': 'var(--primary-alpha-40)',
  // status alpha (exact)
  'rgba(34,197,94,0.1)': 'var(--success-bg)',
  'rgba(239,68,68,0.1)': 'var(--danger-bg)',
};

const args = process.argv.slice(2);
const dry = args.includes('--dry');
const files = args.filter((a) => a !== '--dry');

// literal matchers
const HEX = /#[0-9a-fA-F]{3,8}\b/g;
const RGBA = /rgba?\([^)]*\)/g;
const norm = (s) => s.toLowerCase().replace(/\s+/g, '');

for (const file of files) {
  let css = readFileSync(file, 'utf8');
  // pre-pass: drop dead fallbacks  var(--token, #hex) -> var(--token)
  css = css.replace(/var\((--[a-z0-9-]+),\s*#[0-9a-fA-F]{3,8}\)/gi, 'var($1)');
  const replaced = {}; const unmapped = {};
  const apply = (re) => {
    css = css.replace(re, (m) => {
      const key = norm(m);
      if (MAP[key]) { replaced[m] = (replaced[m] || 0) + 1; return MAP[key]; }
      unmapped[m] = (unmapped[m] || 0) + 1; return m;
    });
  };
  apply(HEX); apply(RGBA);
  if (!dry) writeFileSync(file, css);
  const r = Object.entries(replaced).reduce((a, [, n]) => a + n, 0);
  console.log(`\n${file}  (${r} replaced${dry ? ', DRY' : ''})`);
  const um = Object.entries(unmapped).sort((a, b) => b[1] - a[1]);
  if (um.length) console.log('  UNMAPPED:', um.map(([k, n]) => `${k}×${n}`).join('  '));
}
```

- [ ] **Step 2: Sanity-check on a copy (dry run)**

Run: `node scripts/ui/color-codemod.mjs --dry frontend/src/context/Toast.css`
Expected: prints a replaced count and any UNMAPPED literals; the file is NOT modified (`git diff --stat` shows nothing).

- [ ] **Step 3: Commit the script**
```bash
git add scripts/ui/color-codemod.mjs
git commit -m "build(ui): add allowlist color→token codemod script"
```

---

### Task 3: Tokenize the timeline literals (before board/schedule)

**Files:**
- Modify: `frontend/src/components/board/StripCard.css`
- Modify: `frontend/src/components/board/StripDetailDrawer.css`
- Modify: any other file with `.timeline-*` color rules (find in Step 1)

**Interfaces:**
- Consumes: timeline tokens from Task 1.

- [ ] **Step 1: Find all timeline color rules**

Run: `grep -rn "timeline-\(dream\|fantasy\|flashback\|montage\|title_card\)" frontend/src --include="*.css" | grep -iE "color|background"`
Note every file:line.

- [ ] **Step 2: Replace timeline literals with tokens**

In each matched rule, replace values so that:
- `.timeline-dream { background: rgba(59,130,246,0.15); color: #3b82f6; }` → `background: var(--timeline-dream-bg); color: var(--timeline-dream);`
- `.timeline-fantasy` → `var(--timeline-fantasy-bg)` / `var(--timeline-fantasy)`
- `.timeline-flashback` → `var(--timeline-flashback-bg)` / `var(--timeline-flashback)`
- `.timeline-montage` → `var(--primary-alpha-15)` / `var(--primary-500)`
- `.timeline-title_card` → `rgba(148,163,184,0.15)` stays as-is here (no token) → use `var(--gray-400)` for the color; leave the bg (it will be caught later or left as unmapped).

- [ ] **Step 3: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 4: Commit**
```bash
git add frontend/src/components/board/StripCard.css frontend/src/components/board/StripDetailDrawer.css
git commit -m "refactor(board): tokenize timeline color palette"
```
(Add any other timeline files found in Step 1 to the `git add`.)

---

### Tasks 4–8: Run the codemod per domain batch

For EACH batch below, the procedure is identical (shown once, in full, in Task 4; Tasks 5–8 repeat it with their own file globs). Batches are separate tasks so each is independently reviewable.

**Batch → globs:**
- **Task 4 — scenes:** `frontend/src/components/scenes/*.css`
- **Task 5 — board + schedule:** `frontend/src/components/board/*.css frontend/src/components/schedule/*.css`
- **Task 6 — reports + breakdown:** `frontend/src/components/reports/*.css frontend/src/components/breakdown/*.css`
- **Task 7 — team + notes + workspace + characters:** `frontend/src/components/team/*.css frontend/src/components/notes/*.css frontend/src/components/workspace/*.css frontend/src/components/characters/*.css`
- **Task 8 — remainder:** `frontend/src/components/subscription/*.css frontend/src/components/revisions/*.css frontend/src/components/layout/*.css frontend/src/components/common/*.css frontend/src/components/shared/*.css frontend/src/components/metadata/*.css frontend/src/components/script/*.css frontend/src/components/scripts/*.css frontend/src/components/pdf/*.css frontend/src/components/feedback/*.css frontend/src/components/notifications/*.css frontend/src/context/*.css frontend/src/styles/*.css`

**Procedure (Task 4 shown; identical for 5–8 with the batch's globs):**

- [ ] **Step 1: Dry-run to preview**

Run: `node scripts/ui/color-codemod.mjs --dry frontend/src/components/scenes/*.css`
Read the UNMAPPED lists. They should contain only: blues (`#3b82f6`/`#60a5fa`), greens/teals (`#10b981`/`#34d399`/`#4ade80`/`#2dd4bf`), non-timeline purples (`#c084fc`), white/black (`#fff`/`#ffffff`/`#000`/`#000000`/`#333`/`#555`/`#1a1a1a`), dark amber (`#92400e`), light status tints (`#fecaca`/`#d1fae5`), and non-`0.1/0.15` rgba scrims. If any plain slate/amber/status literal from the Task 2 MAP appears as unmapped, the script has a bug — stop and fix Task 2.

- [ ] **Step 2: Apply**

Run: `node scripts/ui/color-codemod.mjs frontend/src/components/scenes/*.css`

- [ ] **Step 3: Manual triage of the unmapped tail (decision tree)**

For each UNMAPPED literal the report listed, edit by hand per this fixed tree:
- **Accent blue** `#3b82f6`/`#60a5fa` (NOT inside a `.timeline-*` or `.blue`/`.indigo`-named rule) → `var(--primary-500)` / `var(--primary-400)`.
- **Inside a color-named modifier class** (`.blue`, `.indigo`, `.green`, `.purple` selector) → LEAVE unchanged; note in report (Stream-follow-up, not this stream).
- **White text on a colored background** (`color: #fff`/`#ffffff` where the rule's background is a `--primary`/`--danger`/`--success`) → `var(--gray-50)`.
- **White/black as a print/page background** (`.print`, `@media print`, page/sheet backgrounds) → LEAVE unchanged.
- **Black** `#000`/`#000000`/`#1a1a1a`/`#333`/`#555` as UI text/border → nearest `var(--gray-900)`/`var(--gray-800)`/`var(--gray-700)` by darkness; if it's a shadow color, LEAVE.
- **Emerald/teal green** `#10b981`/`#34d399`/`#4ade80`/`#2dd4bf` → if the rule clearly means success/positive, `var(--success)`; if it's a distinct semantic accent (e.g. a chart series), LEAVE and note.
- **Dark amber** `#92400e` → `var(--primary-700)`.
- **Light status tints** `#fecaca`/`#d1fae5` → `var(--danger-bg)` / `var(--success-bg)` only if used as a subtle fill; else LEAVE.
- **Anything else** → LEAVE unchanged and list it in the commit body under "left as-is".

- [ ] **Step 4: Verify build** — `cd frontend && npm run build` → `✓ built`.

- [ ] **Step 5: Commit**
```bash
git add frontend/src/components/scenes/
git commit -m "refactor(scenes): migrate color literals to tokens

Auto-mapped via color-codemod; manually triaged remaining accent/white/green
literals. Left as-is: <list any semantic/ambiguous literals kept>."
```

- [ ] **Tasks 5–8:** repeat Steps 1–5 with the batch's globs and a `refactor(<batch>): migrate color literals to tokens` message. For Task 5, note timeline literals were already tokenized in Task 3 (their files will show fewer replacements).

---

### Task 9: Final verification

**Files:** none.

- [ ] **Step 1: Full build** — `cd frontend && npm run build` → `✓ built`, no errors.

- [ ] **Step 2: Residual-literal audit**

Run:
```bash
cd frontend/src
find . -name "*.css" | grep -vE "pages/Admin/|components/admin/|components/campaigns/|LoginPage|ConfirmEmailPage|AuthCallbackPage|ResetPasswordPage|InvitePage|PaymentSuccessPage|/ui/" \
  | xargs grep -hoE "#[0-9a-fA-F]{3,6}\b|rgba?\([^)]*\)" 2>/dev/null | tr 'A-F' 'a-f' | sort | uniq -c | sort -rn
```
Expected: the only remaining literals are the intentionally-preserved set (color-named-modifier values, distinct semantic greens/teals, print white/black, shadow rgba). NO plain slate/amber/status/indigo literal from the Task 2 MAP should remain. If one does, find its file and convert it.

- [ ] **Step 3: Report**

Summarize: total replacements, per-batch commit hashes, and the full list of deliberately-preserved literals with their one-line reason (this list is the input to a later semantic-token follow-up). Note build is green and that live visual verification was not possible (localhost/login), so confidence rests on token-equivalence (cases 1–2 identical; case 3 indigo→amber and timeline tokenization are the only intended deltas) + per-batch review.

---

## Self-Review

**Spec coverage:**
- Allowlist codemod (only mapped literals touched, rest reported) → Task 2 script. ✔
- Four categories: dead-fallback → (see note below); neutral/status/amber → MAP; indigo→amber → MAP; semantic timeline → Tasks 1+3. ✔
- Ambiguity guard (color-named modifier classes left alone) → Global Constraints + Task 4 Step 3 tree. ✔
- Per-domain commits + build/review gate → Tasks 4–8. ✔
- Semantic tokens defined once in index.css → Task 1. ✔
- Residual audit → Task 9. ✔

**Gap found & fixed:** the spec's category 1 (dead token-fallbacks `var(--token, #legacy)` → `var(--token)`) would otherwise be corrupted by the HEX regex rewriting the `#legacy` inside the fallback (producing invalid `var(--primary-500, var(--primary-500))`). Fixed inline in Task 2's script via a pre-pass (`css.replace(/var\((--[a-z0-9-]+),\s*#hex\)/…, 'var($1)')`) that runs before `apply(HEX)`. This also means category-1 dead fallbacks are handled automatically by every domain batch — no separate task needed.

**Placeholder scan:** Task 3 Step 1 and Task 4 Step 3 use grep/decision-tree procedures rather than fixed line numbers — deliberate, because literal locations vary and the tree is an exhaustive branch set, not an open TODO.

**Type consistency:** `MAP` keys are normalized (lowercase hex, spaceless rgba) and `norm()` normalizes match text the same way — consistent. Token names (`--timeline-dream(-bg)`, `--primary-*`, `--gray-*`, `--success/-bg`, `--danger/-bg`, `--primary-alpha-*`) all exist in `index.css` after Task 1.
