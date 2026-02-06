import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Play, X } from 'lucide-react';
import { triggerLangExtract, cancelLangExtract, getLangExtractStatus } from '../../services/apiService';
import FilterPanel from './FilterPanel';
import ExtractionViewer from './ExtractionViewer';
import ExtractionStats from './ExtractionStats';
import ExtractionDetailModal from './ExtractionDetailModal';
import ExportMenu from './ExportMenu';
import './InteractiveViewer.css';

const InteractiveViewer = () => {
  const { scriptId } = useParams();
  const navigate = useNavigate();

  const [script, setScript] = useState(null);
  const [extractions, setExtractions] = useState([]);
  const [scenes, setScenes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [activeFilters, setActiveFilters] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedScene, setSelectedScene] = useState(null);
  const [selectedExtraction, setSelectedExtraction] = useState(null);

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingMessage, setProcessingMessage] = useState('');
  const pollingIntervalRef = useRef(null);

  useEffect(() => {
    fetchData();
    return () => {
      // Cleanup polling on unmount
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [scriptId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get Supabase session from localStorage
      const authData = localStorage.getItem('sb-twzfaizeyqwevmhjyicz-auth-token');
      let token = null;
      if (authData) {
        try {
          const parsed = JSON.parse(authData);
          token = parsed?.access_token;
        } catch (e) {
          console.warn('Failed to parse auth token:', e);
        }
      }

      const headers = token ? {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      } : {
        'Content-Type': 'application/json'
      };

      const [scriptRes, extractionsRes, scenesRes] = await Promise.all([
        fetch(`/api/scripts/${scriptId}/metadata`, { headers }),
        fetch(`/api/scripts/${scriptId}/extractions`, { headers }),
        fetch(`/api/scripts/${scriptId}/scenes`, { headers })
      ]);

      // Check script metadata response
      if (!scriptRes.ok) {
        throw new Error(`Failed to fetch script metadata: ${scriptRes.status}`);
      }

      const scriptContentType = scriptRes.headers.get('content-type');
      if (!scriptContentType || !scriptContentType.includes('application/json')) {
        throw new Error(`Script metadata endpoint returned non-JSON response (${scriptRes.status})`);
      }

      const scriptData = await scriptRes.json();
      setScript(scriptData);

      // Handle extractions response - may not exist yet
      if (extractionsRes.ok) {
        const contentType = extractionsRes.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const extractionsData = await extractionsRes.json();
          setExtractions(extractionsData.extractions || extractionsData || []);
        } else {
          console.warn('Extractions endpoint returned non-JSON response');
          setExtractions([]);
        }
      } else {
        console.warn(`Extractions not available: ${extractionsRes.status}`);
        setExtractions([]);
      }

      // Handle scenes response
      if (scenesRes.ok) {
        const contentType = scenesRes.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const scenesData = await scenesRes.json();
          setScenes(scenesData.scenes || scenesData || []);
        } else {
          console.warn('Scenes endpoint returned non-JSON response');
          setScenes([]);
        }
      } else {
        console.warn(`Scenes not available: ${scenesRes.status}`);
        setScenes([]);
      }
    } catch (err) {
      console.error('Error fetching data:', err);
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const filteredExtractions = extractions.filter(ext => {
    const className = ext.extraction_class || ext.class;
    const extractionText = ext.extraction_text || ext.text || '';
    
    const matchesFilter = activeFilters.size === 0 || activeFilters.has(className);
    const matchesSearch = !searchQuery || 
      extractionText.toLowerCase().includes(searchQuery.toLowerCase()) ||
      className.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesScene = !selectedScene || ext.scene_id === selectedScene;
    
    return matchesFilter && matchesSearch && matchesScene;
  });

  const toggleFilter = (className) => {
    setActiveFilters(prev => {
      const next = new Set(prev);
      if (next.has(className)) {
        next.delete(className);
      } else {
        next.add(className);
      }
      return next;
    });
  };

  const clearFilters = () => {
    setActiveFilters(new Set());
    setSearchQuery('');
    setSelectedScene(null);
  };

  const handleRunExtraction = async () => {
    try {
      setIsProcessing(true);
      setProcessingProgress(0);
      setProcessingMessage('Initializing extraction...');
      setError(null);

      // Trigger extraction
      const result = await triggerLangExtract(scriptId);
      
      setProcessingMessage('Processing script...');
      
      // Poll for completion — check both extractions AND job status
      pollingIntervalRef.current = setInterval(async () => {
        try {
          // Check job status first to detect failure
          const jobStatus = await getLangExtractStatus(scriptId);
          
          if (jobStatus.status === 'failed' || jobStatus.status === 'cancelled') {
            clearInterval(pollingIntervalRef.current);
            setIsProcessing(false);
            setProcessingProgress(0);
            setProcessingMessage('');
            setError(`Extraction ${jobStatus.status}: ${jobStatus.error_message || 'Unknown error'}`);
            return;
          }
          
          if (jobStatus.status === 'completed' || jobStatus.status === 'partial') {
            // Job finished — refresh data to get extractions
            await fetchData();
            clearInterval(pollingIntervalRef.current);
            setIsProcessing(false);
            setProcessingProgress(100);
            setProcessingMessage('Extraction complete!');
            return;
          }
          
          // Still processing — slow increment (large scripts take 3-5 minutes)
          setProcessingProgress(prev => Math.min(prev + 1, 90));
        } catch (err) {
          console.error('Polling error:', err);
        }
      }, 5000); // Poll every 5 seconds

    } catch (err) {
      console.error('Error triggering extraction:', err);
      const errorMessage = err.response?.data?.error || err.response?.data?.message || err.message || 'Failed to start extraction';
      setError(`Failed to start extraction: ${errorMessage}`);
      setIsProcessing(false);
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    }
  };

  const handleCancelExtraction = async () => {
    try {
      await cancelLangExtract(scriptId);
      setIsProcessing(false);
      setProcessingMessage('Extraction cancelled');
      
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    } catch (err) {
      console.error('Error cancelling extraction:', err);
    }
  };

  if (loading) {
    return (
      <div className="interactive-viewer-loading">
        <Loader2 className="spinner" />
        <p>Loading extractions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="interactive-viewer-error">
        <h2>Error Loading Extractions</h2>
        <p>{error}</p>
        <button onClick={() => navigate(`/scenes/${scriptId}`)}>
          <ArrowLeft size={16} />
          Back to Script
        </button>
      </div>
    );
  }

  // Show empty state if no extractions exist
  if (!loading && extractions.length === 0 && !isProcessing) {
    return (
      <div className="interactive-viewer">
        <header className="interactive-viewer-header">
          <div className="header-left">
            <button 
              className="back-button"
              onClick={() => navigate(`/scenes/${scriptId}`)}
              title="Back to Script"
            >
              <ArrowLeft size={20} />
            </button>
            <h1>{script?.title || 'Script'} - Interactive Extractions</h1>
          </div>
        </header>
        <div className="interactive-viewer-empty">
          <div className="empty-state">
            <h2>No Extractions Available</h2>
            <p>LangExtract analysis has not been run for this script yet.</p>
            <p className="empty-note">
              Click the button below to start the extraction process. This will analyze your script 
              and extract 14 different element types including characters, locations, props, dialogue, 
              emotions, and more.
            </p>
            <div className="empty-actions">
              <button 
                className="btn-primary run-extraction-btn"
                onClick={handleRunExtraction}
                disabled={isProcessing}
              >
                <Play size={18} />
                Run LangExtract Analysis
              </button>
              <button 
                className="btn-secondary"
                onClick={() => navigate(`/scenes/${scriptId}`)}
              >
                <ArrowLeft size={16} />
                Back to Script
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Show processing state
  if (isProcessing) {
    return (
      <div className="interactive-viewer">
        <header className="interactive-viewer-header">
          <div className="header-left">
            <button 
              className="back-button"
              onClick={() => navigate(`/scenes/${scriptId}`)}
              title="Back to Script"
            >
              <ArrowLeft size={20} />
            </button>
            <h1>{script?.title || 'Script'} - Interactive Extractions</h1>
          </div>
        </header>
        <div className="interactive-viewer-processing">
          <div className="processing-state">
            <Loader2 className="spinner" size={48} />
            <h2>Processing Script...</h2>
            <p className="processing-message">{processingMessage}</p>
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${processingProgress}%` }}
              />
            </div>
            <p className="progress-text">{processingProgress}%</p>
            <button 
              className="btn-secondary cancel-btn"
              onClick={handleCancelExtraction}
            >
              <X size={16} />
              Cancel Extraction
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="interactive-viewer">
      <header className="interactive-viewer-header">
        <div className="header-left">
          <button 
            className="back-button"
            onClick={() => navigate(`/scenes/${scriptId}`)}
            title="Back to Script"
          >
            <ArrowLeft size={20} />
          </button>
          <h1>{script?.title || 'Script'} - Interactive Extractions</h1>
        </div>
        <div className="header-right">
          <ExportMenu 
            extractions={filteredExtractions}
            scriptTitle={script?.title}
          />
        </div>
      </header>

      <ExtractionStats 
        script={script}
        scenes={scenes}
        totalExtractions={extractions.length}
        filteredExtractions={filteredExtractions.length}
        extractions={extractions}
        onMetricClick={(metricType) => {
          console.log('Metric clicked:', metricType);
          // TODO: Implement drill-down navigation based on metricType
          // e.g., filter extractions by character, location, etc.
        }}
      />

      <div className="interactive-viewer-content">
        <FilterPanel
          extractions={extractions}
          scenes={scenes}
          activeFilters={activeFilters}
          searchQuery={searchQuery}
          selectedScene={selectedScene}
          onToggleFilter={toggleFilter}
          onSearchChange={setSearchQuery}
          onSceneChange={setSelectedScene}
          onClearFilters={clearFilters}
        />

        <ExtractionViewer
          extractions={filteredExtractions}
          selectedScene={scenes.find(s => s.id === selectedScene)}
          onExtractionClick={setSelectedExtraction}
        />
      </div>

      {selectedExtraction && (
        <ExtractionDetailModal
          extraction={selectedExtraction}
          relatedExtractions={extractions.filter(
            ext => ext.id !== selectedExtraction.id &&
                   (ext.scene_id === selectedExtraction.scene_id ||
                    ext.attributes?.character === selectedExtraction.attributes?.character)
          )}
          onClose={() => setSelectedExtraction(null)}
        />
      )}
    </div>
  );
};

export default InteractiveViewer;
