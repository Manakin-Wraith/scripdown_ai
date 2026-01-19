import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import DropZone from './DropZone';
import { AlertTriangle, X, CheckCircle, Loader, ArrowRight, Clapperboard, Sparkles, AlertCircle, FileText, Scissors, Lock } from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { supabase } from '../../lib/supabase';
import { useSubscription } from '../../hooks/useSubscription';
import { UpgradeModal } from '../subscription';
import './ScriptUpload.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

/**
 * ScriptUpload - Simplified upload flow
 * 
 * New behavior:
 * - Upload extracts scenes via regex (fast)
 * - No automatic AI analysis
 * - User navigates to scene viewer to analyze on-demand
 * - Handles edge case: scripts without standard scene headers
 */
const ScriptUpload = () => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [uploadResult, setUploadResult] = useState(null);
    const [error, setError] = useState(null);
    const [isAiDetecting, setIsAiDetecting] = useState(false);
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [uploadBlocked, setUploadBlocked] = useState(false);
    const [blockMessage, setBlockMessage] = useState('');
    const navigate = useNavigate();
    const toast = useToast();
    const { canUploadScript, status, daysRemaining, scriptLimit, scriptCount } = useSubscription();

    const [processingStage, setProcessingStage] = useState('');

    // Check upload permission on mount
    useEffect(() => {
        checkUploadPermission();
    }, []);

    const checkUploadPermission = async () => {
        const result = await canUploadScript();
        if (!result.canUpload) {
            setUploadBlocked(true);
            setBlockMessage(result.message);
        } else {
            setUploadBlocked(false);
            setBlockMessage('');
        }
    };
    
    const processFile = async (selectedFile) => {
        setFile(selectedFile);
        setError(null);
        
        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            setUploading(true);
            setUploadProgress(0);
            setProcessingStage('Uploading file...');

            // Get auth token for the request
            const { data: { session } } = await supabase.auth.getSession();
            const authHeaders = session?.access_token 
                ? { 'Authorization': `Bearer ${session.access_token}` }
                : {};

            // Simulate staged progress for better UX
            // Stage 1: Upload (0-40%)
            const uploadResponse = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data', ...authHeaders },
                onUploadProgress: (progressEvent) => {
                    // Upload is 0-40% of total progress
                    const uploadPercent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    const scaledPercent = Math.round(uploadPercent * 0.4);
                    setUploadProgress(scaledPercent);
                    
                    if (uploadPercent === 100) {
                        // File uploaded, now server is processing
                        setProcessingStage('Saving to cloud storage...');
                        setUploadProgress(45);
                        
                        // Simulate processing stages
                        setTimeout(() => {
                            setProcessingStage('Parsing PDF pages...');
                            setUploadProgress(55);
                        }, 300);
                        
                        setTimeout(() => {
                            setProcessingStage('Detecting scenes...');
                            setUploadProgress(70);
                        }, 600);
                        
                        setTimeout(() => {
                            setProcessingStage('Saving to database...');
                            setUploadProgress(85);
                        }, 900);
                    }
                }
            });

            // Processing complete
            setUploadProgress(100);
            setProcessingStage('Complete!');
            
            const result = uploadResponse.data;
            setUploadResult(result);
            setUploading(false);
            
            // Show success message
            toast.success(
                'Script Uploaded!', 
                `Found ${result.scene_candidates || 0} scenes. Ready for analysis.`
            );

        } catch (err) {
            handleError(err.response?.data?.error || err.message);
        }
    };

    const handleError = (msg) => {
        setUploading(false);
        setError(msg);
        toast.error('Upload Failed', msg);
    };

    const resetUpload = () => {
        setFile(null);
        setUploading(false);
        setUploadProgress(0);
        setUploadResult(null);
        setError(null);
    };

    const goToSceneViewer = () => {
        if (uploadResult?.script_id) {
            navigate(`/scenes/${uploadResult.script_id}`);
        }
    };

    // Trigger AI-based scene detection for scripts without standard headers
    const handleAiSceneDetection = async () => {
        if (!uploadResult?.script_id) return;
        
        setIsAiDetecting(true);
        
        try {
            const response = await axios.post(
                `${API_BASE_URL}/scripts/${uploadResult.script_id}/detect-scenes-ai`
            );
            
            const newSceneCount = response.data.scenes_detected || 0;
            
            // Update result with new scene count
            setUploadResult(prev => ({
                ...prev,
                scene_candidates: newSceneCount
            }));
            
            toast.success(
                'AI Detection Complete!',
                `Found ${newSceneCount} scenes using AI analysis.`
            );
        } catch (err) {
            toast.error(
                'AI Detection Failed',
                err.response?.data?.error || 'Could not detect scenes with AI.'
            );
        } finally {
            setIsAiDetecting(false);
        }
    };

    // Check if we have zero scenes (edge case)
    const hasNoScenes = uploadResult && (uploadResult.scene_candidates || 0) === 0;

    return (
        <div className="upload-page">
            <div className="upload-header">
                <h1>Upload New Script</h1>
                <p>Upload your screenplay and we'll detect all scenes. You can then analyze each scene for breakdown details.</p>
            </div>

            {error && (
                <div className="upload-error">
                    <div className="error-content">
                        <AlertTriangle size={24} />
                        <span>{error}</span>
                    </div>
                    <button className="error-close" onClick={resetUpload}>
                        <X size={20} />
                    </button>
                </div>
            )}

            <div className="upload-content">
                {/* Upload blocked - show upgrade prompt */}
                {uploadBlocked ? (
                    <div className="upload-blocked-container">
                        <div className="upload-blocked-card">
                            <div className="upload-blocked-icon">
                                <Lock size={48} />
                            </div>
                            <h3>Script Limit Reached</h3>
                            <p className="blocked-message">{blockMessage}</p>
                            
                            {status === 'trial' && (
                                <div className="blocked-info">
                                    <p>
                                        You've uploaded <strong>{scriptCount}</strong> of <strong>{scriptLimit}</strong> scripts 
                                        allowed on the trial plan.
                                    </p>
                                    <p>
                                        Upgrade to get <strong>unlimited scripts</strong> and full access to all features.
                                    </p>
                                </div>
                            )}
                            
                            <button 
                                className="btn-upgrade"
                                onClick={() => setShowUpgradeModal(true)}
                            >
                                <Sparkles size={18} />
                                Upgrade Now - R249
                            </button>
                            
                            <button 
                                className="btn-secondary"
                                onClick={() => navigate('/scripts')}
                            >
                                View Existing Scripts
                            </button>
                        </div>
                    </div>
                ) : !uploading && !uploadResult ? (
                    <DropZone onFileSelect={processFile} disabled={false} />
                ) : uploading ? (
                    <div className="upload-progress-container">
                        <div className="upload-progress-card">
                            <Loader size={32} className="spin upload-spinner" />
                            <h3>Processing Script...</h3>
                            <p className="file-name">{file?.name}</p>
                            <div className="upload-progress-bar">
                                <div 
                                    className="upload-progress-fill"
                                    style={{ width: `${uploadProgress}%`, transition: 'width 0.3s ease' }}
                                />
                            </div>
                            <span className="upload-percent">{uploadProgress}%</span>
                            {processingStage && (
                                <p className="processing-stage">{processingStage}</p>
                            )}
                        </div>
                    </div>
                ) : hasNoScenes ? (
                    /* Zero Scenes Edge Case */
                    <div className="upload-success-container">
                        <div className="upload-success-card zero-scenes">
                            <AlertCircle size={48} className="warning-icon" />
                            <h3>No Standard Scenes Found</h3>
                            <p className="file-name">{file?.name}</p>
                            
                            <div className="zero-scenes-info">
                                <p>
                                    Your script doesn't appear to use standard scene headers 
                                    (e.g., <code>INT. LOCATION - DAY</code>).
                                </p>
                                <p>
                                    This could be because:
                                </p>
                                <ul>
                                    <li>The script uses a non-standard format</li>
                                    <li>Scene headers are formatted differently</li>
                                    <li>It's a treatment or outline document</li>
                                </ul>
                            </div>
                            
                            <div className="zero-scenes-options">
                                <h4>What would you like to do?</h4>
                                
                                <button 
                                    className="btn-ai-detect"
                                    onClick={handleAiSceneDetection}
                                    disabled={isAiDetecting}
                                >
                                    {isAiDetecting ? (
                                        <>
                                            <Loader size={18} className="spin" />
                                            Detecting Scenes...
                                        </>
                                    ) : (
                                        <>
                                            <Sparkles size={18} />
                                            Use AI to Detect Scenes
                                        </>
                                    )}
                                </button>
                                <p className="option-hint">
                                    Our AI will analyze the document and identify scene breaks
                                </p>
                                
                                <div className="option-divider">
                                    <span>or</span>
                                </div>
                                
                                <button 
                                    className="btn-manual-label"
                                    onClick={() => navigate(`/scripts/${uploadResult.script_id}/edit`)}
                                >
                                    <Scissors size={18} />
                                    Manually Label Scenes
                                </button>
                                <p className="option-hint">
                                    Select text in the script to mark scene boundaries
                                </p>
                                
                                <div className="option-divider">
                                    <span>or</span>
                                </div>
                                
                                <button 
                                    className="btn-secondary"
                                    onClick={goToSceneViewer}
                                >
                                    <FileText size={18} />
                                    View Full Script
                                </button>
                                <p className="option-hint">
                                    View the script without scene breakdown
                                </p>
                                
                                <button 
                                    className="btn-tertiary"
                                    onClick={resetUpload}
                                >
                                    Upload Different File
                                </button>
                            </div>
                        </div>
                    </div>
                ) : (
                    /* Normal Success State */
                    <div className="upload-success-container">
                        <div className="upload-success-card">
                            <CheckCircle size={48} className="success-icon" />
                            <h3>Script Ready!</h3>
                            <p className="file-name">{file?.name}</p>
                            
                            {/* Scene count info */}
                            <div className="upload-stats">
                                <div className="stat-item">
                                    <Clapperboard size={20} />
                                    <span className="stat-value">{uploadResult?.scene_candidates || 0}</span>
                                    <span className="stat-label">Scenes Detected</span>
                                </div>
                            </div>
                            
                            <p className="success-message">
                                Your script has been processed. Click below to view scenes and analyze them for breakdown details.
                            </p>
                            
                            <div className="success-actions">
                                <button 
                                    className="btn-primary"
                                    onClick={goToSceneViewer}
                                >
                                    View Scenes
                                    <ArrowRight size={18} />
                                </button>
                                <button 
                                    className="btn-tertiary"
                                    onClick={resetUpload}
                                >
                                    Upload Another
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <UpgradeModal
                isOpen={showUpgradeModal}
                onClose={() => setShowUpgradeModal(false)}
                feature="unlimited_scripts"
                daysRemaining={daysRemaining}
                isExpired={status === 'expired'}
            />
        </div>
    );
};

export default ScriptUpload;
