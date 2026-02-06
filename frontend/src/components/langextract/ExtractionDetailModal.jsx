import { X, TrendingUp, Link2, FileJson } from 'lucide-react';
import './ExtractionDetailModal.css';

const ExtractionDetailModal = ({ extraction, relatedExtractions, onClose }) => {
  const confidence = Math.round((extraction.confidence || 0) * 100);
  
  const getConfidenceColor = (conf) => {
    if (conf >= 80) return 'var(--green-600)';
    if (conf >= 60) return 'var(--yellow-600)';
    return 'var(--red-600)';
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="extraction-modal-backdrop" onClick={handleBackdropClick}>
      <div className="extraction-modal">
        <div className="modal-header">
          <div className="modal-title-section">
            <h2>{extraction.class}</h2>
            <span className="extraction-id">ID: {extraction.id}</span>
          </div>
          <button className="close-button" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          <div className="extraction-text-section">
            <h3>Extracted Text</h3>
            <div className="extraction-text-display">
              "{extraction.text}"
            </div>
          </div>

          <div className="confidence-section">
            <div className="confidence-header">
              <TrendingUp size={18} />
              <span>Confidence Score</span>
            </div>
            <div className="confidence-bar-container">
              <div 
                className="confidence-bar"
                style={{
                  width: `${confidence}%`,
                  backgroundColor: getConfidenceColor(confidence)
                }}
              />
            </div>
            <div className="confidence-value" style={{ color: getConfidenceColor(confidence) }}>
              {confidence}%
            </div>
          </div>

          {extraction.attributes && Object.keys(extraction.attributes).length > 0 && (
            <div className="attributes-section">
              <div className="section-header">
                <FileJson size={18} />
                <span>Attributes</span>
              </div>
              <div className="attributes-grid">
                {Object.entries(extraction.attributes).map(([key, value]) => (
                  <div key={key} className="attribute-item">
                    <span className="attribute-key">{key}:</span>
                    <span className="attribute-value">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {relatedExtractions.length > 0 && (
            <div className="related-section">
              <div className="section-header">
                <Link2 size={18} />
                <span>Related Extractions ({relatedExtractions.length})</span>
              </div>
              <div className="related-list">
                {relatedExtractions.slice(0, 5).map((related) => (
                  <div key={related.id} className="related-item">
                    <span className="related-class">{related.class}</span>
                    <span className="related-text">"{related.text.slice(0, 50)}..."</span>
                    <span className="related-confidence">
                      {Math.round((related.confidence || 0) * 100)}%
                    </span>
                  </div>
                ))}
                {relatedExtractions.length > 5 && (
                  <div className="related-more">
                    +{relatedExtractions.length - 5} more
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="metadata-section">
            <div className="metadata-grid">
              {extraction.scene_id && (
                <div className="metadata-item">
                  <span className="metadata-label">Scene ID:</span>
                  <span className="metadata-value">{extraction.scene_id}</span>
                </div>
              )}
              <div className="metadata-item">
                <span className="metadata-label">Text Position:</span>
                <span className="metadata-value">
                  {extraction.text_start} - {extraction.text_end}
                </span>
              </div>
              {extraction.created_at && (
                <div className="metadata-item">
                  <span className="metadata-label">Extracted:</span>
                  <span className="metadata-value">
                    {new Date(extraction.created_at).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="modal-close-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExtractionDetailModal;
