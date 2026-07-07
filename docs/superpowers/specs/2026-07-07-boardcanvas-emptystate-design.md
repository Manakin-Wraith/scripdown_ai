# BoardCanvas Empty States → `<EmptyState>` — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (C5 — empty states). Deferred B4a leftover: BoardCanvas's two placeholder blocks were skipped in B4a because they used emoji glyphs (📋/🔍) rather than a lucide icon component. This closes that gap.
**Goal:** Convert BoardCanvas's two ad-hoc emoji-icon empty states to the shared `<EmptyState>` primitive, keeping copy verbatim and layout intact.

## Scope

**In — `frontend/src/components/board/BoardCanvas.jsx` + `BoardCanvas.css`.** Two early-return placeholder blocks:

| Condition | Current | Target |
| --- | --- | --- |
| `viewModel.totalScenes === 0` | `<div className="board-empty-state">` with `<div className="board-empty-icon">📋</div>`, `<h3>No scenes found</h3>`, `<p>Upload and analyze a script to see the board view.</p>` | `<EmptyState icon={FileText} title="No scenes found" message="Upload and analyze a script to see the board view." />` inside the reduced wrapper |
| `viewModel.totalScenes > 0 && viewModel.totalVisible === 0` | same wrapper with `🔍`, `<h3>No scenes match filters</h3>`, `<p>Try adjusting or clearing your filters.</p>`, and a `<button className="board-clear-filters-btn">Clear All Filters</button>` | `<EmptyState icon={SearchX} title="No scenes match filters" message="Try adjusting or clearing your filters." action={<button className="board-clear-filters-btn" onClick={() => dispatch({ type: 'CLEAR_FILTERS' })}>Clear All Filters</button>} />` inside the reduced wrapper |

- **Icons:** `FileText` for the empty-board state (matches `SceneList.jsx`'s identical "No scenes found" `<EmptyState>` from B4a); `SearchX` for the filtered-out state (preserves the 🔍 magnifier intent). Both are lucide-react components, confirmed present. Import both plus `EmptyState`.
- **Copy:** verbatim — titles and messages unchanged.
- **Clear-filters action:** keep the existing bespoke `<button className="board-clear-filters-btn">` (with its `onClick={() => dispatch({ type: 'CLEAR_FILTERS' })}`) passed as the `action` prop; **retain** `.board-clear-filters-btn` CSS. Board components do not import the shared `<Button>`; introducing it here is out of scope.

**Layout — keep a reduced positioning wrapper.** `.board-empty-state` currently does double duty: `flex: 1` to fill and vertically center the board area, plus content styling (icon size, `h3`, `p`). `ui-empty` centers its own content but has no fill behavior, and BoardCanvas returns each block as its entire render output (the parent, `ZoomableStripboard`, expects it to fill). So keep `<div className="board-empty-state">` as the wrapper, **reduced** to layout only:
```css
.board-empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    padding: 3rem;
}
```
and **prune** the now-dead content rules: `.board-empty-icon`, `.board-empty-state h3`, `.board-empty-state p` (the primitive supplies icon/title/message styling).

**Out:**
- No `<Button>` adoption (keep the bespoke clear-filters button).
- No copy changes.
- No changes to other board components or the deferred title-nesting item.

## Verification

- `npm run build` from `frontend/` succeeds.
- Invariants (from `frontend/src`): `BoardCanvas.jsx` imports `EmptyState` from `../ui` and `FileText`/`SearchX` from `lucide-react`; renders `<EmptyState` twice; no `board-empty-icon` in the JSX; `grep -n "board-empty-icon\|board-empty-state h3\|board-empty-state p" components/board/BoardCanvas.css` returns nothing; `.board-empty-state` (reduced) and `.board-clear-filters-btn` remain. No emoji glyphs (📋/🔍) remain in `BoardCanvas.jsx`.
- No test runner; live-drive login-gated. Correctness rests on build + review + before/after that both placeholders render with verbatim copy, the board area still fills/centers, and the clear-filters button still dispatches `CLEAR_FILTERS`.

## Execution

Lightweight — a single build-verified, reviewed commit on a short branch (`chore/boardcanvas-emptystate`). No multi-task SDD.

## Success criteria

- Both BoardCanvas empty states render via `<EmptyState>` with lucide icons and verbatim copy; no emoji glyphs remain.
- The dead `.board-empty-icon`/`.board-empty-state h3`/`.board-empty-state p` rules are removed; `.board-empty-state` (reduced) and `.board-clear-filters-btn` remain.
- Board area still fills and centers; clear-filters still works.
- Build green.
