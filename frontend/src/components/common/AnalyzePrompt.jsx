/**
 * AnalyzePrompt - Reusable component for on-demand AI analysis
 * 
 * Shows a prompt to analyze a character or location when AI data is not available.
 * Provides a button to trigger analysis and shows progress.
 */

import React, { useState, useEffect } from 'react';
import { Sparkles, Loader, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { queueCharacterAnalysis, queueLocationAnalysis } from '../../services/apiService';
import { useToast } from '../../context/ToastContext';
import './AnalyzePrompt.css';

const AnalyzePrompt = ({ 
    type, // 'character' or 'location'
    name, 
    scriptId, 
    sceneCount,
    onAnalysisComplete,
    onAnalysisStarted
}) => {
    const [status, setStatus] = useState('idle'); // idle, analyzing, complete, error
    const [error, setError] = useState(null);
    const toast = useToast();

    const handleAnalyze = async () => {
        setStatus('analyzing');
        setError(null);
        
        try {
            if (type === 'character') {
                await queueCharacterAnalysis(scriptId, name);
            } else if (type === 'location') {
                await queueLocationAnalysis(scriptId, name);
            }
            
            toast.info('Analysis Started', `Analyzing ${name}... This may take a moment.`);
            
            if (onAnalysisStarted) {
                onAnalysisStarted();
            }
            
            // Poll for completion (simple approach - could use WebSocket for real-time)
            // For now, we'll let the parent component handle refreshing
            
        } catch (err) {
            setStatus('error');
            setError(err.message || 'Failed to start analysis');
            toast.error('Analysis Failed', err.message || 'Could not start analysis');
        }
    };

    const getEstimatedTime = () => {
        if (type === 'character') {
            // Roughly 35 seconds per character with rate limiting
            return '~30-45 seconds';
        }
        return '~15-30 seconds';
    };

    const getDescription = () => {
        if (type === 'character') {
            return `Get detailed AI insights about ${name}'s personality, motivations, relationships, and emotional arc across ${sceneCount || 'all'} scenes.`;
        }
        return `Get AI analysis of ${name}'s atmosphere, significance, and key events.`;
    };

    return (
        <div className="analyze-prompt">
            <div className="analyze-prompt-icon">
                <Sparkles size={32} />
            </div>
            
            <h3 className="analyze-prompt-title">
                AI Analysis Available
            </h3>
            
            <p className="analyze-prompt-description">
                {getDescription()}
            </p>

            {status === 'idle' && (
                <>
                    <button 
                        className="analyze-prompt-btn"
                        onClick={handleAnalyze}
                    >
                        <Sparkles size={18} />
                        Analyze {type === 'character' ? 'Character' : 'Location'}
                    </button>
                    
                    <div className="analyze-prompt-meta">
                        <Clock size={14} />
                        <span>Estimated time: {getEstimatedTime()}</span>
                    </div>
                </>
            )}

            {status === 'analyzing' && (
                <div className="analyze-prompt-status analyzing">
                    <Loader size={20} className="spin" />
                    <span>Analyzing {name}...</span>
                    <p className="status-hint">This page will update automatically when complete.</p>
                </div>
            )}

            {status === 'complete' && (
                <div className="analyze-prompt-status complete">
                    <CheckCircle size={20} />
                    <span>Analysis complete!</span>
                </div>
            )}

            {status === 'error' && (
                <div className="analyze-prompt-status error">
                    <AlertCircle size={20} />
                    <span>{error}</span>
                    <button 
                        className="retry-btn"
                        onClick={handleAnalyze}
                    >
                        Try Again
                    </button>
                </div>
            )}
        </div>
    );
};

export default AnalyzePrompt;
