# Component Architecture & Separation of Concerns

## Current State (December 2025)

### Issues Identified
1. **Global CSS Class Names** - Classes like `.scene-item`, `.col-scene` can conflict
2. **Large Monolithic Components** - `Stripboard.jsx` (811 lines), `Stripboard.css` (858 lines)
3. **No CSS Scoping** - Styles can leak between components
4. **Flat File Structure** - Related sub-components not grouped

### Immediate Fix Applied
- Added inline style `style={{ display: 'table-cell' }}` to `Stripboard.jsx:577` to fix row alignment
- Cleaned up redundant CSS overrides in `Stripboard.css`

### Decision: Phased Migration
**Phase 1 (Current):** Keep existing structure with inline style fix
**Phase 2 (Future):** Migrate to CSS Modules when time permits

---

## Proposed Architecture: CSS Modules + Component Folders

### File Structure Pattern

```
components/
├── reports/
│   ├── Stripboard/
│   │   ├── index.js                    # Barrel export
│   │   ├── Stripboard.jsx              # Main component (container)
│   │   ├── Stripboard.module.css       # Scoped styles
│   │   ├── components/
│   │   │   ├── StripboardHeader.jsx    # Header with stats
│   │   │   ├── StripboardFilters.jsx   # Filter controls
│   │   │   ├── StripboardRow.jsx       # Single row component
│   │   │   ├── StripboardRow.module.css
│   │   │   ├── BreakdownCard.jsx       # Expandable breakdown
│   │   │   └── BreakdownCard.module.css
│   │   └── hooks/
│   │       └── useStripboardData.js    # Data fetching logic
│   │
│   ├── ReportBuilder/
│   │   ├── index.js
│   │   ├── ReportBuilder.jsx
│   │   └── ReportBuilder.module.css
│   │
│   └── SharedReportView/
│       ├── index.js
│       ├── SharedReportView.jsx
│       └── SharedReportView.module.css
```

### CSS Modules Usage

**Before (Global CSS):**
```css
/* Stripboard.css */
.col-scene {
    width: 70px;
    display: flex;  /* This could leak! */
}
```

```jsx
// Stripboard.jsx
import './Stripboard.css';

<td className="col-scene">...</td>
```

**After (CSS Modules):**
```css
/* Stripboard.module.css */
.colScene {
    width: 70px;
}
```

```jsx
// Stripboard.jsx
import styles from './Stripboard.module.css';

<td className={styles.colScene}>...</td>
```

The class name becomes something like `Stripboard_colScene__x7Ks2` - completely unique and scoped.

---

## Migration Strategy

### Phase 1: Critical Components (Week 1)
1. **Stripboard** - Currently has CSS conflicts
2. **SceneDetail** - Shares styles with Stripboard breakdown cards

### Phase 2: Scene Components (Week 2)
1. SceneViewer
2. SceneList
3. SceneManager

### Phase 3: Remaining Components (Week 3-4)
1. Reports
2. Auth
3. Layout

### Migration Steps Per Component

1. **Create folder structure**
   ```bash
   mkdir -p components/reports/Stripboard/components
   ```

2. **Rename CSS file**
   ```bash
   mv Stripboard.css Stripboard.module.css
   ```

3. **Update imports**
   ```jsx
   // Before
   import './Stripboard.css';
   
   // After
   import styles from './Stripboard.module.css';
   ```

4. **Update class names**
   ```jsx
   // Before
   <div className="stripboard-header">
   
   // After
   <div className={styles.stripboardHeader}>
   ```

5. **Extract sub-components**
   - Move related JSX into separate files
   - Create corresponding `.module.css` files

6. **Create barrel export**
   ```js
   // index.js
   export { default } from './Stripboard';
   ```

---

## Naming Conventions

### CSS Modules
- Use **camelCase** for class names: `.stripboardHeader`, `.colScene`
- Use **BEM-like** for variants: `.rowExpanded`, `.statusAnalyzed`

### Components
- Use **PascalCase** for component names: `StripboardRow.jsx`
- Use **camelCase** for hooks: `useStripboardData.js`

### Files
- Component: `ComponentName.jsx`
- Styles: `ComponentName.module.css`
- Types: `ComponentName.types.ts` (if using TypeScript)
- Tests: `ComponentName.test.jsx`

---

## Benefits

| Benefit | Description |
|---------|-------------|
| **No CSS Conflicts** | Class names are automatically scoped |
| **Smaller Files** | Sub-components are easier to maintain |
| **Better DX** | IDE autocomplete for class names |
| **Tree Shaking** | Unused styles are removed in production |
| **Gradual Migration** | Can migrate one component at a time |

---

## Quick Reference: Vite CSS Modules

Vite supports CSS Modules out of the box. Just rename `.css` to `.module.css`.

```jsx
// Import as object
import styles from './Component.module.css';

// Use with className
<div className={styles.myClass}>

// Multiple classes
<div className={`${styles.base} ${styles.active}`}>

// Conditional classes
<div className={isActive ? styles.active : styles.inactive}>

// With clsx/classnames library (optional)
import clsx from 'clsx';
<div className={clsx(styles.base, { [styles.active]: isActive })}>
```

---

## Immediate Action Items

1. [ ] Fix Stripboard CSS conflict (display: flex issue)
2. [ ] Create Stripboard folder structure
3. [ ] Convert Stripboard.css to Stripboard.module.css
4. [ ] Extract StripboardRow as sub-component
5. [ ] Test and verify no regressions
