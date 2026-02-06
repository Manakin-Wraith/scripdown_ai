import { useMemo } from 'react';
import useVirtualScroll from '../../hooks/useVirtualScroll';
import './ExtractionViewer.css';

const CLASS_COLORS = {
  'character': '#3b82f6',
  'location': '#10b981',
  'time': '#f59e0b',
  'color': '#ec4899',
  'wardrobe': '#8b5cf6',
  'props': '#06b6d4',
  'vehicle': '#ef4444',
  'makeup': '#f97316',
  'dialogue': '#14b8a6',
  'sound': '#a855f7',
  'camera': '#6366f1',
  'vfx': '#eab308',
  'action': '#dc2626',
  'emotion': '#db2777'
};

const VirtualizedViewer = ({ scriptText, extractions, onExtractionClick }) => {
  const ITEM_HEIGHT = 20;
  const CONTAINER_HEIGHT = 600;

  const { containerRef, visibleLines, offsetY, totalHeight, startIndex } = useVirtualScroll(
    scriptText,
    ITEM_HEIGHT,
    CONTAINER_HEIGHT,
    20
  );

  const extractionsByLine = useMemo(() => {
    const lineMap = new Map();
    const lines = scriptText.split('\n');
    
    let charCount = 0;
    lines.forEach((line, lineIndex) => {
      const lineStart = charCount;
      const lineEnd = charCount + line.length;
      
      const lineExtractions = extractions.filter(ext => 
        (ext.text_start >= lineStart && ext.text_start < lineEnd) ||
        (ext.text_end > lineStart && ext.text_end <= lineEnd) ||
        (ext.text_start <= lineStart && ext.text_end >= lineEnd)
      );

      if (lineExtractions.length > 0) {
        lineMap.set(lineIndex, lineExtractions);
      }

      charCount += line.length + 1;
    });

    return lineMap;
  }, [scriptText, extractions]);

  const renderLine = (line, lineIndex) => {
    const actualLineIndex = startIndex + lineIndex;
    const lineExtractions = extractionsByLine.get(actualLineIndex) || [];

    if (lineExtractions.length === 0) {
      return <div key={actualLineIndex} style={{ height: ITEM_HEIGHT }}>{line}</div>;
    }

    return (
      <div key={actualLineIndex} style={{ height: ITEM_HEIGHT }}>
        {line}
      </div>
    );
  };

  return (
    <div className="extraction-viewer">
      <div 
        ref={containerRef}
        className="extraction-viewer-content"
        style={{ 
          height: CONTAINER_HEIGHT,
          overflow: 'auto'
        }}
      >
        <div style={{ height: totalHeight, position: 'relative' }}>
          <div style={{ transform: `translateY(${offsetY}px)` }}>
            <pre className="script-text">
              {visibleLines.map((line, index) => renderLine(line, index))}
            </pre>
          </div>
        </div>
      </div>

      {extractions.length === 0 && (
        <div className="no-extractions">
          <p>No extractions match your current filters.</p>
          <p className="hint">Try adjusting your filters or search query.</p>
        </div>
      )}
    </div>
  );
};

export default VirtualizedViewer;
