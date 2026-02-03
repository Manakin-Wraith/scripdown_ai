# Report Preview UX Improvements

## Current State Analysis

From the screenshots, the Preview section shows:
- **Basic counts**: 3 Scenes, 6 Characters, 3 Locations, 8 Props
- **Minimal visual design**: Just numbers and labels
- **No actionable information**: User can't see what's actually in the report
- **No context**: Doesn't help user decide if report is ready

**Problem**: Preview adds minimal value - user must generate report to see actual content.

---

## UX Issues Identified

### 1. **Lack of Visual Hierarchy**
- All stats have equal weight
- No indication of what's important
- No visual interest or engagement

### 2. **No Actionable Insights**
- Can't see actual character names
- Can't see location list
- Can't verify data completeness
- No indication of missing data

### 3. **No Report-Specific Preview**
- Same preview for all report types
- Doesn't show what will be in the selected report
- Misses opportunity to build confidence

### 4. **No Data Quality Indicators**
- Can't tell if analysis is complete
- No warning for missing critical data
- No indication of data richness

---

## Proposed UX Improvements

### Option A: Enhanced Stats with Mini Lists (Recommended)

**Visual Design**:
```
┌─────────────────────────────────────────────────────────┐
│ Preview                                                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📊 Script Summary                                       │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │    3     │    6     │    3     │    8     │         │
│  │  Scenes  │ Chars    │ Locations│  Props   │         │
│  └──────────┴──────────┴──────────┴──────────┘         │
│                                                          │
│  👥 Top Characters (in this report)                     │
│  • John (3 scenes) ────────────────────────── 100%      │
│  • Sarah (2 scenes) ───────────────────────── 67%       │
│  • Mike (1 scene) ────────────────────────── 33%        │
│  + 3 more characters                                    │
│                                                          │
│  📍 Key Locations                                        │
│  • INT. COFFEE SHOP - DAY (2 scenes)                    │
│  • EXT. CITY STREET - NIGHT (1 scene)                   │
│                                                          │
│  ⚠️ Data Quality                                         │
│  ✓ All scenes analyzed                                  │
│  ⚠ 2 scenes missing wardrobe details                    │
│  ✓ Character breakdown complete                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Benefits**:
- Shows actual data, not just counts
- Builds confidence before generation
- Helps user verify completeness
- Report-specific preview

---

### Option B: Visual Data Cards

**Visual Design**:
```
┌─────────────────────────────────────────────────────────┐
│ Preview - Wardrobe Report                                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────┐  ┌────────────────┐                │
│  │ 👕 Wardrobe    │  │ 👥 Characters  │                │
│  │                │  │                │                │
│  │      12        │  │       6        │                │
│  │    items       │  │   featured     │                │
│  │                │  │                │                │
│  │ • Leather jacket│  │ • John         │                │
│  │ • Red dress    │  │ • Sarah        │                │
│  │ • Police uniform│  │ • Mike         │                │
│  │ + 9 more       │  │ + 3 more       │                │
│  └────────────────┘  └────────────────┘                │
│                                                          │
│  ┌────────────────────────────────────────┐            │
│  │ 📊 Coverage                             │            │
│  │ ████████████████░░░░ 80% Complete       │            │
│  │                                         │            │
│  │ ✓ 8 scenes with wardrobe details       │            │
│  │ ⚠ 2 scenes need review                 │            │
│  └────────────────────────────────────────┘            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Benefits**:
- Visually engaging cards
- Progress indicators
- Clear data quality metrics
- Actionable warnings

---

### Option C: Interactive Preview Table

**Visual Design**:
```
┌─────────────────────────────────────────────────────────┐
│ Preview - Scene Breakdown                                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Showing first 5 of 12 scenes                           │
│                                                          │
│  ┌──────┬─────┬──────────────┬─────┬──────────┐        │
│  │ Sc # │ I/E │ Setting      │ D/N │ Length   │        │
│  ├──────┼─────┼──────────────┼─────┼──────────┤        │
│  │  1   │ INT │ Coffee Shop  │ DAY │ 2 3/8    │        │
│  │  2   │ EXT │ City Street  │ NIGHT│ 1/8     │        │
│  │  3   │ INT │ Apartment    │ DAY │ 1 2/8    │        │
│  │  4   │ EXT │ Parking Lot  │ DAY │ 3/8      │        │
│  │  5   │ INT │ Office       │ DAY │ 2/8      │        │
│  └──────┴─────┴──────────────┴─────┴──────────┘        │
│                                                          │
│  [View Full Preview →]                                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Benefits**:
- Shows actual report structure
- User can verify data accuracy
- Expandable for full preview
- Builds confidence

---

## Recommended Implementation: Hybrid Approach

Combine the best elements from all options:

### 1. **Summary Stats Bar** (Always visible)
```jsx
<div className="preview-stats-bar">
  <StatCard icon={Film} value={3} label="Scenes" />
  <StatCard icon={Users} value={6} label="Characters" />
  <StatCard icon={MapPin} value={3} label="Locations" />
  <StatCard icon={Package} value={8} label="Props" />
</div>
```

### 2. **Report-Specific Preview** (Dynamic based on selected type)

**For Wardrobe Report**:
```jsx
<div className="preview-details">
  <PreviewSection title="Wardrobe Items" icon={Shirt}>
    <ItemList items={topWardrobe} max={5} />
  </PreviewSection>
  
  <PreviewSection title="Characters" icon={Users}>
    <ItemList items={topCharacters} max={5} />
  </PreviewSection>
  
  <DataQuality 
    complete={80} 
    warnings={["2 scenes missing wardrobe details"]}
  />
</div>
```

**For Scene Breakdown**:
```jsx
<div className="preview-details">
  <PreviewTable 
    scenes={scenes.slice(0, 5)}
    columns={['Scene', 'I/E', 'Setting', 'D/N', 'Length']}
  />
  <button onClick={expandPreview}>View All {scenes.length} Scenes</button>
</div>
```

**For Day Out of Days**:
```jsx
<div className="preview-details">
  <CharacterSchedule 
    characters={topCharacters}
    showSceneCounts={true}
  />
  <EstimatedShootDays days={calculateShootDays()} />
</div>
```

### 3. **Data Quality Indicator** (Always visible)
```jsx
<div className="data-quality-card">
  <ProgressBar value={analysisComplete} />
  <QualityChecks>
    <Check status="success">All scenes analyzed</Check>
    <Check status="warning">2 scenes missing props</Check>
    <Check status="success">Character breakdown complete</Check>
  </QualityChecks>
</div>
```

---

## Detailed Component Specifications

### Component 1: Enhanced Stats Bar

**File**: `frontend/src/components/reports/PreviewStatsBar.jsx`

```jsx
import React from 'react';
import { Film, Users, MapPin, Package, TrendingUp } from 'lucide-react';
import './PreviewStatsBar.css';

const PreviewStatsBar = ({ summary }) => {
  const stats = [
    { 
      icon: Film, 
      value: summary?.total_scenes || 0, 
      label: 'Scenes',
      color: 'blue',
      trend: null
    },
    { 
      icon: Users, 
      value: summary?.total_characters || 0, 
      label: 'Characters',
      color: 'purple',
      subtext: `${summary?.analyzed_characters || 0} analyzed`
    },
    { 
      icon: MapPin, 
      value: summary?.total_locations || 0, 
      label: 'Locations',
      color: 'green',
      subtext: `${summary?.int_locations || 0} INT / ${summary?.ext_locations || 0} EXT`
    },
    { 
      icon: Package, 
      value: summary?.total_props || 0, 
      label: 'Props',
      color: 'orange',
      trend: summary?.props_trend
    }
  ];

  return (
    <div className="preview-stats-bar">
      {stats.map((stat, idx) => (
        <div key={idx} className={`stat-card stat-${stat.color}`}>
          <div className="stat-icon">
            <stat.icon size={20} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{stat.value}</div>
            <div className="stat-label">{stat.label}</div>
            {stat.subtext && (
              <div className="stat-subtext">{stat.subtext}</div>
            )}
          </div>
          {stat.trend && (
            <div className="stat-trend">
              <TrendingUp size={14} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default PreviewStatsBar;
```

**CSS**:
```css
.preview-stats-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--surface-2);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-blue .stat-icon { background: rgba(99, 102, 241, 0.1); color: #6366f1; }
.stat-purple .stat-icon { background: rgba(168, 85, 247, 0.1); color: #a855f7; }
.stat-green .stat-icon { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
.stat-orange .stat-icon { background: rgba(249, 115, 22, 0.1); color: #f97316; }

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 4px;
}

.stat-subtext {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}
```

---

### Component 2: Report-Specific Preview

**File**: `frontend/src/components/reports/ReportPreviewDetails.jsx`

```jsx
import React from 'react';
import { Users, Shirt, Package, MapPin, Zap, Flame } from 'lucide-react';
import './ReportPreviewDetails.css';

const ReportPreviewDetails = ({ reportType, previewData }) => {
  const renderWardrobe Preview = () => {
    const wardrobe = Object.entries(previewData.wardrobe || {})
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 5);
    
    const characters = Object.entries(previewData.characters || {})
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 5);

    return (
      <div className="preview-grid">
        <PreviewCard title="Wardrobe Items" icon={Shirt} count={Object.keys(previewData.wardrobe || {}).length}>
          <ItemList>
            {wardrobe.map(([item, info]) => (
              <Item key={item} name={item} count={info.count} scenes={info.scenes} />
            ))}
          </ItemList>
        </PreviewCard>

        <PreviewCard title="Characters" icon={Users} count={Object.keys(previewData.characters || {}).length}>
          <ItemList>
            {characters.map(([char, info]) => (
              <Item key={char} name={char} count={info.count} />
            ))}
          </ItemList>
        </PreviewCard>
      </div>
    );
  };

  const renderSceneBreakdown = () => {
    const scenes = (previewData.scenes || []).slice(0, 5);
    
    return (
      <div className="preview-table-container">
        <table className="preview-table">
          <thead>
            <tr>
              <th>Scene</th>
              <th>I/E</th>
              <th>Setting</th>
              <th>D/N</th>
              <th>Length</th>
            </tr>
          </thead>
          <tbody>
            {scenes.map((scene) => (
              <tr key={scene.id}>
                <td><strong>{scene.scene_number}</strong></td>
                <td>{scene.int_ext}</td>
                <td>{scene.setting}</td>
                <td>{scene.time_of_day}</td>
                <td>{formatEighths(scene.page_length_eighths)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {previewData.scenes?.length > 5 && (
          <div className="preview-more">
            + {previewData.scenes.length - 5} more scenes
          </div>
        )}
      </div>
    );
  };

  const renderDayOutOfDays = () => {
    const characters = Object.entries(previewData.characters || {})
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 8);

    return (
      <div className="character-schedule">
        <h4>Character Appearance Schedule</h4>
        {characters.map(([char, info]) => (
          <div key={char} className="character-bar">
            <div className="character-name">{char}</div>
            <div className="character-progress">
              <div 
                className="progress-fill" 
                style={{ width: `${(info.count / previewData.summary.total_scenes) * 100}%` }}
              />
            </div>
            <div className="character-count">{info.count} scenes</div>
          </div>
        ))}
      </div>
    );
  };

  // Route to appropriate preview
  switch (reportType) {
    case 'wardrobe':
      return renderWardrobePreview();
    case 'scene_breakdown':
      return renderSceneBreakdown();
    case 'day_out_of_days':
      return renderDayOutOfDays();
    case 'props':
      return renderPropsPreview();
    case 'stunts':
      return renderStuntsPreview();
    default:
      return <div className="preview-generic">Preview available after generation</div>;
  }
};

// Helper Components
const PreviewCard = ({ title, icon: Icon, count, children }) => (
  <div className="preview-card">
    <div className="preview-card-header">
      <Icon size={18} />
      <h4>{title}</h4>
      <span className="count-badge">{count}</span>
    </div>
    <div className="preview-card-body">
      {children}
    </div>
  </div>
);

const ItemList = ({ children }) => (
  <ul className="preview-item-list">
    {children}
  </ul>
);

const Item = ({ name, count, scenes }) => (
  <li className="preview-item">
    <span className="item-name">{name}</span>
    <span className="item-meta">
      {count} scene{count !== 1 ? 's' : ''}
      {scenes && ` (${scenes.slice(0, 3).join(', ')}${scenes.length > 3 ? '...' : ''})`}
    </span>
  </li>
);

const formatEighths = (eighths) => {
  if (!eighths) return '—';
  const full = Math.floor(eighths / 8);
  const remaining = eighths % 8;
  if (remaining === 0) return full > 0 ? `${full}` : '—';
  if (full === 0) return `${remaining}/8`;
  return `${full} ${remaining}/8`;
};

export default ReportPreviewDetails;
```

---

### Component 3: Data Quality Indicator

**File**: `frontend/src/components/reports/DataQualityIndicator.jsx`

```jsx
import React from 'react';
import { CheckCircle, AlertCircle, Info } from 'lucide-react';
import './DataQualityIndicator.css';

const DataQualityIndicator = ({ previewData }) => {
  const checks = [
    {
      status: previewData.summary?.analyzed_scenes === previewData.summary?.total_scenes ? 'success' : 'warning',
      message: `${previewData.summary?.analyzed_scenes || 0} of ${previewData.summary?.total_scenes || 0} scenes analyzed`,
      icon: CheckCircle
    },
    {
      status: previewData.summary?.total_characters > 0 ? 'success' : 'warning',
      message: previewData.summary?.total_characters > 0 
        ? 'Character breakdown complete' 
        : 'No characters detected',
      icon: previewData.summary?.total_characters > 0 ? CheckCircle : AlertCircle
    },
    {
      status: 'info',
      message: `Script length: ${(previewData.summary?.total_eighths / 8).toFixed(1)} pages`,
      icon: Info
    }
  ];

  const completionPercent = previewData.summary?.analyzed_scenes 
    ? Math.round((previewData.summary.analyzed_scenes / previewData.summary.total_scenes) * 100)
    : 0;

  return (
    <div className="data-quality-indicator">
      <div className="quality-header">
        <h4>Data Quality</h4>
        <span className={`quality-badge quality-${getQualityLevel(completionPercent)}`}>
          {completionPercent}% Complete
        </span>
      </div>

      <div className="quality-progress">
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${completionPercent}%` }}
          />
        </div>
      </div>

      <div className="quality-checks">
        {checks.map((check, idx) => (
          <div key={idx} className={`quality-check check-${check.status}`}>
            <check.icon size={16} />
            <span>{check.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const getQualityLevel = (percent) => {
  if (percent >= 90) return 'excellent';
  if (percent >= 70) return 'good';
  if (percent >= 50) return 'fair';
  return 'poor';
};

export default DataQualityIndicator;
```

---

## Implementation Roadmap

### Phase 1: Enhanced Stats (1-2 days)
- [x] Create PreviewStatsBar component
- [ ] Add visual styling with colors and icons
- [ ] Add hover effects and animations
- [ ] Integrate into ReportBuilder

### Phase 2: Report-Specific Previews (3-4 days)
- [ ] Create ReportPreviewDetails component
- [ ] Implement wardrobe preview
- [ ] Implement scene breakdown preview
- [ ] Implement day-out-of-days preview
- [ ] Implement props/stunts/extras previews
- [ ] Add "View More" expansion

### Phase 3: Data Quality (1-2 days)
- [ ] Create DataQualityIndicator component
- [ ] Add progress bar visualization
- [ ] Add quality checks with icons
- [ ] Add completion percentage

### Phase 4: Polish & Testing (1-2 days)
- [ ] Responsive design for mobile
- [ ] Loading states and animations
- [ ] Error handling
- [ ] User testing and feedback

**Total Estimated Time**: 6-10 days

---

## Success Metrics

### User Engagement
- **Before**: Preview viewed but not used (passive)
- **After**: Preview actively used to verify data (active)

### Confidence Building
- **Before**: User unsure if report is ready
- **After**: User confident in report quality before generation

### Error Prevention
- **Before**: User generates report, finds missing data, regenerates
- **After**: User sees missing data in preview, fixes before generation

### Time Savings
- **Before**: Generate → Review → Fix → Regenerate (5-10 min)
- **After**: Preview → Fix → Generate once (2-3 min)

---

## Conclusion

The current preview is a missed opportunity to:
1. ✅ Build user confidence
2. ✅ Show actual report content
3. ✅ Prevent wasted generation attempts
4. ✅ Provide actionable insights

**Recommended**: Implement **Hybrid Approach** with:
- Enhanced stats bar (visual engagement)
- Report-specific previews (actual content)
- Data quality indicator (confidence building)

This transforms the preview from a passive display to an **active decision-making tool**.
