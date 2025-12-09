/**
 * Analysis Progress Modal - Detailed progress view for script analysis
 * 
 * Shows:
 * - Overall progress
 * - Individual job statuses (scene extraction, characters, etc.)
 * - Estimated time remaining
 * - Cancel button
 */

import React, { useState, useEffect, useRef } from 'react';
import { 
    X, 
    CheckCircle, 
    Clock, 
    Loader, 
    AlertCircle,
    Clapperboard,
    Users,
    MapPin,
    Sparkles,
    BookOpen,
    XCircle
} from 'lucide-react';
import { useAnalysis } from '../../context/AnalysisContext';
import { cancelScriptAnalysis } from '../../services/apiService';
import { useToast } from '../../context/ToastContext';
import './AnalysisProgressModal.css';

// Job type display config
const JOB_CONFIG = {
    scene_extraction: {
        label: 'Extracting Scenes',
        icon: Clapperboard,
        description: 'Analyzing script and extracting all scenes'
    },
    scene_enhancement: {
        label: 'Extracting Scenes',
        icon: Clapperboard,
        description: 'Analyzing script and extracting all scenes'
    },
    overview: {
        label: 'Overview',
        icon: BookOpen,
        description: 'Gathering basic statistics'
    },
    story_arc: {
        label: 'Story Arc',
        icon: Sparkles,
        description: 'Analyzing narrative structure and themes'
    },
    characters: {
        label: 'Characters',
        icon: Users,
        description: 'Deep analysis of all characters'
    },
    locations: {
        label: 'Locations',
        icon: MapPin,
        description: 'Analyzing all locations and settings'
    }
};

const AnalysisProgressModal = ({ scriptId, scriptName, isOpen, onClose }) => {
    const { detailedStatus, fetchScriptStatus } = useAnalysis();
    const toast = useToast();
    const [isCancelling, setIsCancelling] = useState(false);
    
    const status = detailedStatus[scriptId] || {};
    const jobs = status.jobs || [];
    
    // Use ref to track completion toast (avoids re-render loops)
    const hasShownCompleteRef = useRef(false);
    
    // Poll for status updates when modal is open
    useEffect(() => {
        if (!isOpen || !scriptId) return;
        
        // Reset completion flag when modal opens
        hasShownCompleteRef.current = false;
        
        // Initial fetch
        fetchScriptStatus(scriptId);
        
        // Poll every 2 seconds
        const interval = setInterval(() => {
            fetchScriptStatus(scriptId);
        }, 2000);
        
        return () => clearInterval(interval);
    }, [isOpen, scriptId]); // fetchScriptStatus is stable from context
    
    // Show completion toast (using ref to prevent loops)
    useEffect(() => {
        if (status.status === 'complete' && !hasShownCompleteRef.current) {
            hasShownCompleteRef.current = true;
            toast.success('Analysis Complete!', `${scriptName} is ready to view.`);
        }
    }, [status.status, scriptName, toast]);
    
    const handleCancel = async () => {
        setIsCancelling(true);
        try {
            await cancelScriptAnalysis(scriptId);
            toast.info('Analysis Cancelled', 'The analysis has been stopped.');
            onClose();
        } catch (error) {
            toast.error('Cancel Failed', error.message || 'Could not cancel analysis.');
        } finally {
            setIsCancelling(false);
        }
    };
    
    // Calculate estimated time
    const getEstimatedTime = () => {
        const pendingJobs = jobs.filter(j => j.status === 'queued' || j.status === 'processing');
        // Support both legacy (scene_extraction) and v2 (scene_enhancement) job types
        const sceneJob = jobs.find(j => j.type === 'scene_extraction' || j.type === 'scene_enhancement');
        
        if (sceneJob?.status === 'processing') {
            // Scene extraction in progress - estimate based on progress
            const remaining = 100 - (sceneJob.progress || 0);
            const scenesRemaining = Math.ceil(remaining / 5); // ~5% per scene
            return `~${scenesRemaining * 4} seconds`; // 4s per scene with new pipeline
        }
        
        // Other jobs
        const otherPending = pendingJobs.filter(j => j.type !== 'scene_extraction' && j.type !== 'scene_enhancement').length;
        if (otherPending > 0) {
            return `~${otherPending * 35} seconds`;
        }
        
        return 'Almost done...';
    };
    
    const getStatusIcon = (jobStatus) => {
        switch (jobStatus) {
            case 'completed':
                return <CheckCircle size={18} className="status-icon completed" />;
            case 'processing':
                return <Loader size={18} className="status-icon processing spin" />;
            case 'failed':
                return <AlertCircle size={18} className="status-icon failed" />;
            case 'cancelled':
                return <XCircle size={18} className="status-icon cancelled" />;
            default:
                return <Clock size={18} className="status-icon pending" />;
        }
    };
    
    if (!isOpen) return null;
    
    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="analysis-progress-modal" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <div className="header-content">
                        <Sparkles size={24} className="header-icon" />
                        <div>
                            <h2>AI Analysis in Progress</h2>
                            <p className="script-name">{scriptName}</p>
                        </div>
                    </div>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>
                
                {/* Overall Progress */}
                <div className="overall-progress">
                    <div className="progress-header">
                        <span className="progress-label">Overall Progress</span>
                        <span className="progress-percent">{status.progress || 0}%</span>
                    </div>
                    <div className="progress-bar-container">
                        <div 
                            className="progress-bar-fill"
                            style={{ width: `${status.progress || 0}%` }}
                        />
                    </div>
                    <div className="progress-meta">
                        <span className="estimated-time">
                            <Clock size={14} />
                            {getEstimatedTime()}
                        </span>
                        <span className={`status-badge ${status.status || 'pending'}`}>
                            {status.status === 'in_progress' ? 'Analyzing...' : status.status}
                        </span>
                    </div>
                </div>
                
                {/* Job List */}
                <div className="jobs-list">
                    {Object.entries(JOB_CONFIG).map(([jobType, config]) => {
                        const job = jobs.find(j => j.type === jobType);
                        const Icon = config.icon;
                        
                        return (
                            <div 
                                key={jobType} 
                                className={`job-item ${job?.status || 'pending'}`}
                            >
                                <div className="job-icon">
                                    <Icon size={20} />
                                </div>
                                <div className="job-info">
                                    <div className="job-header">
                                        <span className="job-label">{config.label}</span>
                                        {getStatusIcon(job?.status)}
                                    </div>
                                    <p className="job-description">
                                        {job?.status === 'processing' && job?.message 
                                            ? job.message 
                                            : config.description}
                                    </p>
                                    {job?.status === 'processing' && job?.progress > 0 && (
                                        <div className="job-progress">
                                            <div 
                                                className="job-progress-fill"
                                                style={{ width: `${job.progress}%` }}
                                            />
                                        </div>
                                    )}
                                    {job?.status === 'completed' && job?.message && (
                                        <p className="job-result">{job.message}</p>
                                    )}
                                    {job?.error && (
                                        <p className="job-error">{job.error}</p>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
                
                {/* Footer */}
                <div className="modal-footer">
                    <p className="footer-note">
                        You can close this modal - analysis will continue in the background.
                    </p>
                    <div className="footer-actions">
                        <button 
                            className="cancel-btn"
                            onClick={handleCancel}
                            disabled={isCancelling || status.status === 'complete'}
                        >
                            {isCancelling ? (
                                <>
                                    <Loader size={16} className="spin" />
                                    Cancelling...
                                </>
                            ) : (
                                <>
                                    <XCircle size={16} />
                                    Cancel Analysis
                                </>
                            )}
                        </button>
                        <button className="close-modal-btn" onClick={onClose}>
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AnalysisProgressModal;
