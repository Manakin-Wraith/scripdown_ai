import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, FileText, AlertCircle } from 'lucide-react';
import './DropZone.css';

const DropZone = ({ onFileSelect, disabled }) => {
    const onDrop = useCallback((acceptedFiles) => {
        if (acceptedFiles?.length > 0) {
            onFileSelect(acceptedFiles[0]);
        }
    }, [onFileSelect]);

    const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
        onDrop,
        accept: {
            'application/pdf': ['.pdf']
        },
        maxFiles: 1,
        disabled
    });

    return (
        <div 
            {...getRootProps()} 
            className={`dropzone ${isDragActive ? 'active' : ''} ${isDragReject ? 'reject' : ''} ${disabled ? 'disabled' : ''}`}
        >
            <input {...getInputProps()} />
            
            <div className="dropzone-content">
                {isDragReject ? (
                    <>
                        <AlertCircle size={48} className="dropzone-icon error" />
                        <p className="dropzone-text error">PDF files only, please</p>
                    </>
                ) : (
                    <>
                        <div className={`icon-wrapper ${isDragActive ? 'bounce' : ''}`}>
                            {isDragActive ? (
                                <FileText size={48} className="dropzone-icon active" />
                            ) : (
                                <UploadCloud size={48} className="dropzone-icon" />
                            )}
                        </div>
                        <h3 className="dropzone-title">
                            {isDragActive ? "Drop script here" : "Upload your script"}
                        </h3>
                        <p className="dropzone-subtitle">
                            Drag and drop a PDF file here, or click to browse
                        </p>
                        <div className="dropzone-hint">
                            Supports standard Screenplay PDFs (max 10MB)
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default DropZone;
