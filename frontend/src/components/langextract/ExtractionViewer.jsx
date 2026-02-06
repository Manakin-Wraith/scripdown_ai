import { useMemo } from 'react';
import { Film } from 'lucide-react';
import { CLASS_METADATA, getClassMetadata } from '../../config/extractionClassConfig';
import './ExtractionViewer.css';

const ExtractionViewer = ({ extractions, selectedScene, onExtractionClick }) => {
  const groupedExtractions = useMemo(() => {
    const groups = {};
    
    extractions.forEach(extraction => {
      const className = extraction.extraction_class || extraction.class;
      if (!groups[className]) {
        groups[className] = [];
      }
      groups[className].push(extraction);
    });

    return Object.entries(groups)
      .sort(([, a], [, b]) => b.length - a.length)
      .map(([className, items]) => ({
        className,
        metadata: getClassMetadata(className),
        items
      }));
  }, [extractions]);

  if (extractions.length === 0) {
    return (
      <div className="extraction-viewer">
        <div className="no-extractions">
          <p>No extractions match your current filters.</p>
          <p className="hint">Try adjusting your filters or search query.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="extraction-viewer">
      <div className="extraction-viewer-content">
        {selectedScene && (
          <div className="scene-context-header">
            <div className="scene-context-title">
              <Film size={20} />
              <h2>Scene {selectedScene.scene_number}</h2>
            </div>
            <div className="scene-context-details">
              <span className="scene-setting">
                {selectedScene.int_ext && <span className="int-ext-badge">{selectedScene.int_ext}</span>}
                {selectedScene.setting}
                {selectedScene.time_of_day && <span className="time-badge">{selectedScene.time_of_day}</span>}
              </span>
            </div>
            <div className="scene-context-stats">
              {extractions.length} extraction{extractions.length !== 1 ? 's' : ''} in this scene
            </div>
          </div>
        )}
        
        <div className="breakdown-grid">
          {groupedExtractions.map(({ className, metadata, items }) => {
            const Icon = metadata.icon;
            
            return (
              <div key={className} className="breakdown-card">
                <div className="card-header" style={{ borderLeftColor: metadata.color, borderLeftWidth: '3px' }}>
                  <Icon className="card-icon" size={20} style={{ color: metadata.color }} />
                  <h3>{metadata.label}</h3>
                  <span className="item-count">{items.length}</span>
                </div>
                <div className="card-content">
                  <div className="extraction-list">
                    {items.map((extraction, idx) => (
                      <div
                        key={extraction.id || idx}
                        className="extraction-item"
                        onClick={() => onExtractionClick(extraction)}
                        style={{ borderLeftColor: metadata.color }}
                      >
                        <div className="extraction-text">{extraction.extraction_text}</div>
                        {extraction.attributes && Object.keys(extraction.attributes).length > 0 && (
                          <div className="extraction-meta">
                            {Object.entries(extraction.attributes).slice(0, 2).map(([key, value]) => (
                              <span key={key} className="meta-tag">
                                {key}: {String(value)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default ExtractionViewer;
