import React from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { 
    ArrowLeft, 
    User, 
    Clock,
    Sparkles
} from 'lucide-react';
import './CharacterProfile.css';

/**
 * CharacterProfile - Coming Soon placeholder
 * 
 * This feature is temporarily disabled as part of the platform simplification.
 * Deep character analysis will be available in a future update.
 */
const CharacterProfile = () => {
    const { scriptId, characterName } = useParams();
    const navigate = useNavigate();
    const decodedName = decodeURIComponent(characterName);

    return (
        <div className="character-profile coming-soon-page">
            {/* Back Navigation */}
            <div className="profile-nav">
                <button 
                    className="back-btn"
                    onClick={() => navigate(`/scenes/${scriptId}`)}
                >
                    <ArrowLeft size={18} />
                    Back to Scenes
                </button>
            </div>

            {/* Coming Soon Content */}
            <div className="coming-soon-container">
                <div className="coming-soon-icon">
                    <User size={64} />
                    <div className="icon-badge">
                        <Clock size={24} />
                    </div>
                </div>
                
                <h1>Character Profiles</h1>
                <h2 className="character-name-preview">{decodedName}</h2>
                
                <div className="coming-soon-badge">
                    <Sparkles size={16} />
                    Coming Soon
                </div>
                
                <p className="coming-soon-description">
                    Deep character analysis with AI-powered insights, emotional arcs, 
                    and relationship mapping is coming in a future update.
                </p>
                
                <div className="coming-soon-features">
                    <h3>Planned Features:</h3>
                    <ul>
                        <li>Character backstory and motivation analysis</li>
                        <li>Emotional arc visualization across scenes</li>
                        <li>Relationship mapping with other characters</li>
                        <li>Scene-by-scene character breakdown</li>
                        <li>Costume and appearance tracking</li>
                    </ul>
                </div>
                
                <div className="coming-soon-actions">
                    <Link to={`/scenes/${scriptId}`} className="btn-primary">
                        Return to Scene Breakdown
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default CharacterProfile;
