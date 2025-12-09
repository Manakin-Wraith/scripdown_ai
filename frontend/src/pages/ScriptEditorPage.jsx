import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Loader, AlertCircle, Check, Clapperboard } from 'lucide-react';
import SceneEditor from '../components/scenes/SceneEditor';
import { getScriptMetadata, getScriptFullText } from '../services/apiService';
import { useToast } from '../context/ToastContext';
import './ScriptEditorPage.css';

/**
 * ScriptEditorPage - Manual Scene Labeling Page
 * 
 * Displays the full script text and allows users to manually
 * select and label scenes.
 */
const ScriptEditorPage = () => {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const toast = useToast();
    
    const [script, setScript] = useState(null);
    const [fullText, setFullText] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [sceneCount, setSceneCount] = useState(0);

    useEffect(() => {
        loadScriptData();
    }, [scriptId]);

    const loadScriptData = async () => {
        try {
            setLoading(true);
            
            // Get script metadata from backend API
            const scriptData = await getScriptMetadata(scriptId);
            setScript(scriptData);
            
            // Get full text from backend API
            const textData = await getScriptFullText(scriptId);
            if (textData?.full_text) {
                setFullText(textData.full_text);
            } else {
                setError('No script content found. Please re-upload the script.');
            }
            
        } catch (err) {
            console.error('Error loading script:', err);
            setError(err.message || 'Failed to load script');
        } finally {
            setLoading(false);
        }
    };

    const handleScenesUpdated = (scenes) => {
        setSceneCount(scenes.length);
    };

    const handleFinish = () => {
        if (sceneCount > 0) {
            navigate(`/scenes/${scriptId}`);
        } else {
            toast.warning('No Scenes', 'Please create at least one scene before continuing.');
        }
    };

    if (loading) {
        return (
            <div className="editor-page loading">
                <Loader size={32} className="spin" />
                <p>Loading script...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="editor-page error">
                <AlertCircle size={48} />
                <h2>Error Loading Script</h2>
                <p>{error}</p>
                <Link to="/upload" className="btn-primary">
                    Upload New Script
                </Link>
            </div>
        );
    }

    return (
        <div className="editor-page">
            {/* Header */}
            <div className="editor-header">
                <div className="header-left">
                    <button 
                        className="back-btn"
                        onClick={() => navigate(-1)}
                    >
                        <ArrowLeft size={18} />
                    </button>
                    <div className="header-info">
                        <h1>{script?.title || 'Untitled Script'}</h1>
                        <span className="subtitle">Manual Scene Labeling</span>
                    </div>
                </div>
                
                <div className="header-right">
                    <div className="scene-counter">
                        <Clapperboard size={18} />
                        <span>{sceneCount} scenes</span>
                    </div>
                    <button 
                        className="btn-finish"
                        onClick={handleFinish}
                        disabled={sceneCount === 0}
                    >
                        <Check size={18} />
                        Done Labeling
                    </button>
                </div>
            </div>

            {/* Scene Editor */}
            <SceneEditor 
                scriptId={scriptId}
                fullText={fullText}
                onScenesUpdated={handleScenesUpdated}
            />
        </div>
    );
};

export default ScriptEditorPage;
