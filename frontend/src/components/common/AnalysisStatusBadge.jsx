/**
 * AnalysisStatusBadge - Visual indicator for AI analysis status
 * 
 * Shows:
 * - Status icon and label
 * - Progress bar when analyzing
 * - Click to start/retry analysis
 */

import React from 'react';
import { 
    CheckCircle, 
    Loader, 
    Clock, 
    AlertCircle, 
    Sparkles,
    Play,
    RefreshCw
} from 'lucide-react';
import { useAnalysis } from '../../context/AnalysisContext';
import './AnalysisStatusBadge.css';

const AnalysisStatusBadge = ({ 
    scriptId, 
    showProgress = true,
    showLabel = true,
    size = 'medium',  // 'small', 'medium', 'large'
    onClick = null    // Custom click handler
}) => {
    const { getStatus, startAnalysis, retryAnalysis, isLoading } = useAnalysis();
    const status = getStatus(scriptId);

    const handleClick = async (e) => {
        e.stopPropagation();
        
        if (onClick) {
            onClick(e);
            return;
        }
        
        if (status.status === 'pending') {
            await startAnalysis(scriptId);
        } else if (status.status === 'failed' || status.status === 'partial') {
            await retryAnalysis(scriptId);
        }
    };

    const statusConfig = {
        pending: {
            icon: <Clock size={size === 'small' ? 12 : size === 'large' ? 18 : 14} />,
            label: 'Not Analyzed',
            color: 'gray',
            actionIcon: <Play size={size === 'small' ? 10 : 12} />,
            actionLabel: 'Start',
            clickable: true
        },
        queued: {
            icon: <Clock size={size === 'small' ? 12 : size === 'large' ? 18 : 14} className="pulse" />,
            label: 'Queued',
            color: 'yellow',
            clickable: false
        },
        in_progress: {
            icon: <Loader size={size === 'small' ? 12 : size === 'large' ? 18 : 14} className="spin" />,
            label: `Analyzing${status.progress ? ` ${status.progress}%` : '...'}`,
            color: 'blue',
            clickable: false
        },
        partial: {
            icon: <Sparkles size={size === 'small' ? 12 : size === 'large' ? 18 : 14} />,
            label: 'Partial',
            color: 'purple',
            actionIcon: <RefreshCw size={size === 'small' ? 10 : 12} />,
            actionLabel: 'Complete',
            clickable: true
        },
        complete: {
            icon: <CheckCircle size={size === 'small' ? 12 : size === 'large' ? 18 : 14} />,
            label: 'Complete',
            color: 'green',
            clickable: false
        },
        failed: {
            icon: <AlertCircle size={size === 'small' ? 12 : size === 'large' ? 18 : 14} />,
            label: 'Failed',
            color: 'red',
            actionIcon: <RefreshCw size={size === 'small' ? 10 : 12} />,
            actionLabel: 'Retry',
            clickable: true
        }
    };

    const config = statusConfig[status.status] || statusConfig.pending;
    const isClickable = config.clickable && !isLoading;

    return (
        <div 
            className={`analysis-status-badge ${config.color} ${size} ${isClickable ? 'clickable' : ''}`}
            onClick={isClickable ? handleClick : undefined}
            title={config.clickable ? config.actionLabel : config.label}
        >
            <span className="status-icon">
                {isLoading ? <Loader size={size === 'small' ? 12 : 14} className="spin" /> : config.icon}
            </span>
            
            {showLabel && (
                <span className="status-label">{config.label}</span>
            )}
            
            {config.actionIcon && isClickable && (
                <span className="action-icon">{config.actionIcon}</span>
            )}
            
            {showProgress && status.status === 'in_progress' && status.progress > 0 && (
                <div className="progress-bar-mini">
                    <div 
                        className="progress-fill" 
                        style={{ width: `${status.progress}%` }} 
                    />
                </div>
            )}
        </div>
    );
};

export default AnalysisStatusBadge;
