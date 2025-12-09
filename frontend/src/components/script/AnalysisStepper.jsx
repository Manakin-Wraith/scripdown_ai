import React from 'react';
import { CheckCircle2, Circle, Loader2, FileText } from 'lucide-react';
import './AnalysisStepper.css';

const AnalysisStepper = ({ progress, status, fileName }) => {
    // Determine active step based on status message or progress
    const getStepStatus = (stepIndex) => {
        // Logic to determine if step is 'pending', 'processing', or 'completed'
        // This is a simplified heuristic based on the current backend messages
        
        if (progress === 100) return 'completed';
        
        // Step 1: Upload
        if (stepIndex === 0) {
            return progress > 0 ? 'processing' : 'pending';
        }
        
        // Step 2: Analysis
        if (stepIndex === 1) {
            if (status.includes('Uploading')) return 'pending';
            return progress > 0 ? 'processing' : 'pending';
        }

        // Step 3: Finalizing
        if (stepIndex === 2) {
             return progress > 90 ? 'processing' : 'pending';
        }

        return 'pending';
    };

    const steps = [
        { title: 'Upload Script', description: 'Sending PDF to secure server' },
        { title: 'AI Analysis', description: 'Extracting scenes, characters, and props' },
        { title: 'Finalizing', description: 'Preparing your interactive breakdown' }
    ];

    // Override for demo/MVP smoothness:
    // If progress is moving, assume Step 2 is active. 
    // Real implementation might need more granular backend states.
    const currentStep = status.includes('Uploading') ? 0 : (progress > 90 ? 2 : 1);

    return (
        <div className="analysis-stepper">
            <div className="file-info-card">
                <div className="file-icon-wrapper">
                    <FileText size={24} className="file-icon" />
                </div>
                <div className="file-details">
                    <span className="file-name">{fileName}</span>
                    <span className="file-status">{status || 'Initializing...'}</span>
                </div>
                <div className="progress-ring">
                    {progress}%
                </div>
            </div>

            <div className="steps-container">
                {steps.map((step, index) => {
                    const isActive = index === currentStep;
                    const isCompleted = index < currentStep;
                    
                    return (
                        <div key={index} className={`step-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}>
                            <div className="step-indicator">
                                {isCompleted ? (
                                    <CheckCircle2 className="step-icon completed" />
                                ) : isActive ? (
                                    <Loader2 className="step-icon spinner" />
                                ) : (
                                    <Circle className="step-icon pending" />
                                )}
                                {index < steps.length - 1 && <div className="step-line"></div>}
                            </div>
                            <div className="step-content">
                                <h4 className="step-title">{step.title}</h4>
                                <p className="step-desc">{step.description}</p>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default AnalysisStepper;
