import { Search, X } from 'lucide-react';
import { CLASS_METADATA } from '../../config/extractionClassConfig';
import './FilterPanel.css';

const FilterPanel = ({ 
  extractions, 
  scenes = [],
  activeFilters, 
  searchQuery,
  selectedScene,
  onToggleFilter, 
  onSearchChange,
  onSceneChange,
  onClearFilters 
}) => {
  const classCounts = extractions.reduce((acc, ext) => {
    const className = ext.extraction_class || ext.class;
    acc[className] = (acc[className] || 0) + 1;
    return acc;
  }, {});

  const sortedClasses = Object.keys(CLASS_METADATA).sort((a, b) => {
    const countA = classCounts[a] || 0;
    const countB = classCounts[b] || 0;
    return countB - countA;
  });

  // Count extractions per scene
  const sceneExtractionCounts = extractions.reduce((acc, ext) => {
    if (ext.scene_id) {
      acc[ext.scene_id] = (acc[ext.scene_id] || 0) + 1;
    }
    return acc;
  }, {});

  const hasActiveFilters = activeFilters.size > 0 || searchQuery.length > 0 || selectedScene;

  return (
    <aside className="filter-panel">
      <div className="filter-panel-header">
        <h2>Filters</h2>
        {hasActiveFilters && (
          <button 
            className="clear-filters-btn"
            onClick={onClearFilters}
            title="Clear all filters"
          >
            <X size={16} />
            Clear
          </button>
        )}
      </div>

      <div className="search-box">
        <Search size={18} className="search-icon" />
        <input
          type="text"
          placeholder="Search extractions..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="search-input"
        />
        {searchQuery && (
          <button 
            className="clear-search-btn"
            onClick={() => onSearchChange('')}
            aria-label="Clear search"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {scenes.length > 0 && (
        <div className="filter-section scene-filter-section">
          <h3>Filter by Scene</h3>
          <select 
            className="scene-select"
            value={selectedScene || ''}
            onChange={(e) => onSceneChange(e.target.value || null)}
          >
            <option value="">All Scenes</option>
            {scenes.map(scene => {
              const count = sceneExtractionCounts[scene.id] || 0;
              const sceneLabel = `Scene ${scene.scene_number}: ${scene.int_ext || ''} ${scene.setting || ''}`.trim();
              return (
                <option key={scene.id} value={scene.id}>
                  {sceneLabel} ({count})
                </option>
              );
            })}
          </select>
        </div>
      )}

      <div className="filter-section">
        <h3>Extraction Classes</h3>
        <div className="filter-list">
          {sortedClasses.map(className => {
            const metadata = CLASS_METADATA[className];
            const count = classCounts[className] || 0;
            const isActive = activeFilters.has(className);
            const Icon = metadata.icon;

            if (count === 0) return null;

            return (
              <button
                key={className}
                className={`filter-item ${isActive ? 'active' : ''}`}
                onClick={() => onToggleFilter(className)}
                style={{
                  '--filter-color': metadata.color,
                  '--filter-border': isActive ? metadata.color : 'transparent'
                }}
              >
                <div className="filter-item-left">
                  <Icon 
                    size={18} 
                    className="filter-icon"
                    style={{ color: metadata.color }}
                  />
                  <span className="filter-label">{metadata.label}</span>
                </div>
                <span className="filter-count">{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      {activeFilters.size > 0 && (
        <div className="active-filters-summary">
          <p>{activeFilters.size} filter{activeFilters.size !== 1 ? 's' : ''} active</p>
        </div>
      )}
    </aside>
  );
};

export default FilterPanel;
