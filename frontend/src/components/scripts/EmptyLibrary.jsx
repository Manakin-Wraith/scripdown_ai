import React from 'react';
import { FileText, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './EmptyLibrary.css';

const EmptyLibrary = () => {
    const navigate = useNavigate();

    return (
        <div className="empty-library">
            <div className="empty-content">
                <div className="empty-icon-wrapper">
                    <FileText size={48} className="empty-icon" />
                </div>
                <h2>No scripts uploaded yet</h2>
                <p>Upload your first screenplay to get an AI-powered breakdown of scenes, characters, and props.</p>
                <button
                    className="empty-upload-btn"
                    onClick={() => navigate('/upload')}
                >
                    <Plus size={18} />
                    Upload Script
                </button>
            </div>
        </div>
    );
};

export default EmptyLibrary;
