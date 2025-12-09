/**
 * DepartmentSelector - Onboarding component for selecting departments
 * 
 * Shown after signup to let users choose their department(s)
 */

import React, { useState, useEffect } from 'react';
import { 
    Check, 
    Loader,
    Clapperboard,
    Briefcase,
    Camera,
    Palette,
    Shirt,
    Users,
    MapPin,
    Sparkles,
    Volume2,
    Scissors,
    PenTool,
    User,
    ArrowRight
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { getDepartments } from '../../lib/supabase';
import './DepartmentSelector.css';

// Icon mapping
const DEPARTMENT_ICONS = {
    'clapperboard': Clapperboard,
    'briefcase': Briefcase,
    'camera': Camera,
    'palette': Palette,
    'shirt': Shirt,
    'users': Users,
    'map-pin': MapPin,
    'sparkles': Sparkles,
    'volume-2': Volume2,
    'scissors': Scissors,
    'pen-tool': PenTool,
    'user': User
};

const DepartmentSelector = ({ isOpen, onComplete }) => {
    const [departments, setDepartments] = useState([]);
    const [selectedDepts, setSelectedDepts] = useState([]);
    const [primaryDept, setPrimaryDept] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);

    const { joinUserDepartment, user } = useAuth();

    // Fetch departments
    useEffect(() => {
        const fetchDepts = async () => {
            setLoading(true);
            const { data, error } = await getDepartments();
            if (error) {
                setError('Failed to load departments');
            } else {
                setDepartments(data || []);
            }
            setLoading(false);
        };
        
        if (isOpen) {
            fetchDepts();
        }
    }, [isOpen]);

    const toggleDepartment = (dept) => {
        setSelectedDepts(prev => {
            const isSelected = prev.some(d => d.id === dept.id);
            if (isSelected) {
                // Remove
                const newSelection = prev.filter(d => d.id !== dept.id);
                // If removing primary, clear it
                if (primaryDept?.id === dept.id) {
                    setPrimaryDept(newSelection[0] || null);
                }
                return newSelection;
            } else {
                // Add
                const newSelection = [...prev, dept];
                // If first selection, make it primary
                if (!primaryDept) {
                    setPrimaryDept(dept);
                }
                return newSelection;
            }
        });
    };

    const handleComplete = async () => {
        if (selectedDepts.length === 0) {
            setError('Please select at least one department');
            return;
        }

        setSaving(true);
        setError(null);

        try {
            // Join all selected departments
            for (const dept of selectedDepts) {
                const isPrimary = primaryDept?.id === dept.id;
                await joinUserDepartment(dept.id, 'member', isPrimary);
            }
            
            onComplete();
        } catch (err) {
            setError('Failed to save departments');
        } finally {
            setSaving(false);
        }
    };

    const getIcon = (iconName) => {
        return DEPARTMENT_ICONS[iconName] || Briefcase;
    };

    if (!isOpen) return null;

    return (
        <div className="dept-selector-overlay">
            <div className="dept-selector-modal">
                {/* Header */}
                <div className="dept-selector-header">
                    <h2>Select Your Department(s)</h2>
                    <p>Choose the departments you work in. You can change this later.</p>
                </div>

                {/* Content */}
                <div className="dept-selector-content">
                    {loading ? (
                        <div className="dept-loading">
                            <Loader size={32} className="spin" />
                            <span>Loading departments...</span>
                        </div>
                    ) : (
                        <>
                            {/* Department Grid */}
                            <div className="dept-grid">
                                {departments.map(dept => {
                                    const Icon = getIcon(dept.icon);
                                    const isSelected = selectedDepts.some(d => d.id === dept.id);
                                    const isPrimary = primaryDept?.id === dept.id;
                                    
                                    return (
                                        <button
                                            key={dept.id}
                                            className={`dept-card ${isSelected ? 'selected' : ''} ${isPrimary ? 'primary' : ''}`}
                                            onClick={() => toggleDepartment(dept)}
                                            style={{
                                                '--dept-color': dept.color
                                            }}
                                        >
                                            <div className="dept-icon">
                                                <Icon size={24} />
                                            </div>
                                            <span className="dept-name">{dept.name}</span>
                                            {isSelected && (
                                                <div className="dept-check">
                                                    <Check size={16} />
                                                </div>
                                            )}
                                            {isPrimary && (
                                                <span className="primary-badge">Primary</span>
                                            )}
                                        </button>
                                    );
                                })}
                            </div>

                            {/* Primary selector */}
                            {selectedDepts.length > 1 && (
                                <div className="primary-selector">
                                    <label>Primary Department:</label>
                                    <select 
                                        value={primaryDept?.id || ''} 
                                        onChange={(e) => {
                                            const dept = selectedDepts.find(d => d.id === e.target.value);
                                            setPrimaryDept(dept);
                                        }}
                                    >
                                        {selectedDepts.map(dept => (
                                            <option key={dept.id} value={dept.id}>
                                                {dept.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            {/* Error */}
                            {error && (
                                <div className="dept-error">{error}</div>
                            )}
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="dept-selector-footer">
                    <div className="selected-count">
                        {selectedDepts.length} department{selectedDepts.length !== 1 ? 's' : ''} selected
                    </div>
                    <button 
                        className="continue-btn"
                        onClick={handleComplete}
                        disabled={saving || selectedDepts.length === 0}
                    >
                        {saving ? (
                            <>
                                <Loader size={18} className="spin" />
                                Saving...
                            </>
                        ) : (
                            <>
                                Continue
                                <ArrowRight size={18} />
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default DepartmentSelector;
