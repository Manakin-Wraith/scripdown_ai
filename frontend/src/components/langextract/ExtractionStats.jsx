import { useMemo } from 'react';
import { FileText, Users, MapPin, Home, Package, Car, Sparkles, Clock } from 'lucide-react';
import './ExtractionStats.css';

const ExtractionStats = ({ script, scenes, totalExtractions, filteredExtractions, extractions, onMetricClick }) => {
  // Compute metrics: prefer extraction_metadata, fall back to scenes JSONB
  const metrics = useMemo(() => {
    const hasExtractions = extractions && extractions.length > 0;

    // Total pages always from script metadata
    const totalPages = script?.total_pages || 0;

    // Eighths from scenes (not in extraction_metadata)
    const totalEighths = scenes?.reduce((sum, s) => sum + (s.page_length_eighths || 0), 0) || 0;
    const eighthsPages = Math.floor(totalEighths / 8);
    const eighthsRemainder = totalEighths % 8;
    const formattedEighths = eighthsRemainder > 0
      ? `${eighthsPages} ${eighthsRemainder}/8`
      : `${eighthsPages}`;

    // INT/EXT from scenes (scene-level metadata)
    const intCount = scenes?.filter(s => s.int_ext === 'INT').length || 0;
    const extCount = scenes?.filter(s => s.int_ext === 'EXT').length || 0;
    const intExtTotal = intCount + extCount;
    const intPercent = intExtTotal > 0 ? Math.round((intCount / intExtTotal) * 100) : 0;
    const extPercent = 100 - intPercent;

    let characterCount, locationCount, propsCount, vehiclesCount, specialFxCount;

    if (hasExtractions) {
      // Primary source: extraction_metadata
      const uniqueChars = new Set();
      const uniqueProps = new Set();
      const uniqueVehicles = new Set();
      const uniqueFx = new Set();

      extractions.forEach(ext => {
        const cls = ext.extraction_class || ext.class;
        const text = ext.extraction_text || ext.text || '';
        if (cls === 'character') uniqueChars.add(text);
        else if (cls === 'prop') uniqueProps.add(text);
        else if (cls === 'vehicle') uniqueVehicles.add(text);
        else if (cls === 'special_fx') uniqueFx.add(text);
      });

      characterCount = uniqueChars.size;
      propsCount = uniqueProps.size;
      vehiclesCount = uniqueVehicles.size;
      specialFxCount = uniqueFx.size;

      // Locations still from scenes (scene_header attributes)
      const uniqueLocs = new Set();
      scenes?.forEach(s => { if (s.setting) uniqueLocs.add(s.setting); });
      locationCount = uniqueLocs.size;
    } else {
      // Fallback: scenes JSONB arrays
      const uniqueChars = new Set();
      const uniqueLocs = new Set();
      const uniqueProps = new Set();
      const uniqueVehicles = new Set();
      const uniqueFx = new Set();

      scenes?.forEach(scene => {
        (scene.characters || []).forEach(c => uniqueChars.add(c));
        if (scene.setting) uniqueLocs.add(scene.setting);
        (scene.props || []).forEach(p => uniqueProps.add(p));
        (scene.vehicles || []).forEach(v => uniqueVehicles.add(v));
        (scene.special_fx || []).forEach(fx => uniqueFx.add(fx));
      });

      characterCount = uniqueChars.size;
      locationCount = uniqueLocs.size;
      propsCount = uniqueProps.size;
      vehiclesCount = uniqueVehicles.size;
      specialFxCount = uniqueFx.size;
    }

    return {
      totalPages, totalEighths, formattedEighths, eighthsPages, eighthsRemainder,
      characterCount, locationCount,
      intPercent, extPercent,
      propsCount, vehiclesCount, specialFxCount,
      fromExtractions: hasExtractions
    };
  }, [script, scenes, extractions]);
  
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      });
    } catch {
      return 'N/A';
    }
  };
  
  const handleMetricClick = (metricType) => {
    if (onMetricClick) {
      onMetricClick(metricType);
    }
  };

  return (
    <div className="extraction-stats-container">
      {/* Section 1: Script Header Card */}
      <div className="script-header-card">
        <div className="header-icon">
          <FileText size={32} />
        </div>
        <div className="header-content">
          <h1 className="script-title">{script?.title || 'Untitled Script'}</h1>
          <div className="script-meta">
            {script?.writer_name && (
              <span className="meta-item">
                Written by: <strong>{script.writer_name}</strong>
              </span>
            )}
            {script?.draft_version && (
              <span className="meta-item">
                Draft: <strong>{script.draft_version}</strong>
              </span>
            )}
            {metrics.totalPages > 0 && (
              <span className="meta-item">
                Pages: <strong>{metrics.totalPages}</strong>
              </span>
            )}
            {script?.created_at && (
              <span className="meta-item">
                Uploaded: <strong>{formatDate(script.created_at)}</strong>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Section 2: Production Metrics Grid */}
      <div className="production-metrics-grid">
        <div 
          className="metric-card clickable" 
          onClick={() => handleMetricClick('pages')}
          title="Click to view page breakdown"
        >
          <div className="metric-icon">
            <FileText size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{metrics.totalPages}</div>
            <div className="metric-label">Total Pages</div>
          </div>
        </div>

        <div 
          className="metric-card clickable" 
          onClick={() => handleMetricClick('eighths')}
          title="Click to view scene timing breakdown"
        >
          <div className="metric-icon">
            <Clock size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-value">
              {metrics.eighthsPages}
              {metrics.eighthsRemainder > 0 && (
                <span className="metric-fraction">{metrics.eighthsRemainder}/8</span>
              )}
            </div>
            <div className="metric-label">Total Eighths</div>
          </div>
        </div>

        <div 
          className="metric-card clickable" 
          onClick={() => handleMetricClick('characters')}
          title="Click to view character breakdown"
        >
          <div className="metric-icon">
            <Users size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{metrics.characterCount}</div>
            <div className="metric-label">Characters</div>
          </div>
        </div>

        <div 
          className="metric-card clickable" 
          onClick={() => handleMetricClick('locations')}
          title="Click to view location breakdown"
        >
          <div className="metric-icon">
            <MapPin size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{metrics.locationCount}</div>
            <div className="metric-label">Locations</div>
          </div>
        </div>

        <div 
          className="metric-card clickable" 
          onClick={() => handleMetricClick('int-ext')}
          title="Click to view INT/EXT breakdown"
        >
          <div className="metric-icon">
            <Home size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-value">
              {metrics.intPercent}% <span className="metric-subvalue">INT</span>
            </div>
            <div className="metric-sublabel">{metrics.extPercent}% EXT</div>
          </div>
        </div>

        <div 
          className="metric-card clickable" 
          onClick={() => handleMetricClick('props')}
          title="Click to view props list"
        >
          <div className="metric-icon">
            <Package size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{metrics.propsCount}</div>
            <div className="metric-label">Props</div>
          </div>
        </div>

        <div 
          className="metric-card clickable" 
          onClick={() => handleMetricClick('vehicles')}
          title="Click to view vehicles list"
        >
          <div className="metric-icon">
            <Car size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{metrics.vehiclesCount}</div>
            <div className="metric-label">Vehicles</div>
          </div>
        </div>

        <div 
          className="metric-card clickable" 
          onClick={() => handleMetricClick('special-fx')}
          title="Click to view special FX list"
        >
          <div className="metric-icon">
            <Sparkles size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-value">{metrics.specialFxCount}</div>
            <div className="metric-label">Special FX</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExtractionStats;
