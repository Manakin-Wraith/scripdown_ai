import React, { useState, useMemo, useCallback } from 'react';
import { Users, MapPin, CheckCircle, Clock, AlertTriangle, Merge, X, Check, Edit3 } from 'lucide-react';
import './ScriptSummary.css';

/**
 * Lightweight Levenshtein distance for client-side duplicate detection.
 */
function levenshtein(a, b) {
    const m = a.length, n = b.length;
    if (m === 0) return n;
    if (n === 0) return m;
    const d = Array.from({ length: m + 1 }, (_, i) => [i]);
    for (let j = 1; j <= n; j++) d[0][j] = j;
    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            d[i][j] = a[i - 1] === b[j - 1]
                ? d[i - 1][j - 1]
                : 1 + Math.min(d[i - 1][j], d[i][j - 1], d[i - 1][j - 1]);
        }
    }
    return d[m][n];
}

/**
 * Detect suspected duplicate character names.
 * Returns a Map of name → Set of names it might be a duplicate of.
 */
function detectDuplicates(names) {
    const suspects = new Map();
    for (let i = 0; i < names.length; i++) {
        for (let j = i + 1; j < names.length; j++) {
            const a = names[i].toUpperCase();
            const b = names[j].toUpperCase();
            const maxLen = Math.max(a.length, b.length);
            if (maxLen === 0) continue;
            const dist = levenshtein(a, b);
            const similarity = 1 - dist / maxLen;
            if (similarity >= 0.7 && dist <= 3) {
                if (!suspects.has(names[i])) suspects.set(names[i], new Set());
                if (!suspects.has(names[j])) suspects.set(names[j], new Set());
                suspects.get(names[i]).add(names[j]);
                suspects.get(names[j]).add(names[i]);
            }
        }
    }
    return suspects;
}

/**
 * ScriptSummary - Collapsible panel showing aggregated script data
 * with character duplicate detection and merge capability.
 */
const ScriptSummary = ({ characters, locations, stats, scriptId, onMergeComplete }) => {
    const [selected, setSelected] = useState(new Set());
    const [showMergeBar, setShowMergeBar] = useState(false);
    const [merging, setMerging] = useState(false);
    const [canonicalChoice, setCanonicalChoice] = useState(null);
    const [customName, setCustomName] = useState('');
    const [showCustomInput, setShowCustomInput] = useState(false);
    const [mergeSuccess, setMergeSuccess] = useState(null);

    const sortedCharacters = useMemo(() =>
        Object.entries(characters).sort((a, b) => b[1].count - a[1].count),
        [characters]
    );

    const sortedLocations = useMemo(() =>
        Object.entries(locations).sort((a, b) => b[1].count - a[1].count),
        [locations]
    );

    const duplicateSuspects = useMemo(() =>
        detectDuplicates(sortedCharacters.map(([name]) => name)),
        [sortedCharacters]
    );

    const duplicateCount = useMemo(() => {
        const groups = new Set();
        duplicateSuspects.forEach((partners, name) => {
            const key = [name, ...Array.from(partners)].sort().join('|');
            groups.add(key);
        });
        return groups.size;
    }, [duplicateSuspects]);

    const toggleSelect = useCallback((name) => {
        setSelected(prev => {
            const next = new Set(prev);
            if (next.has(name)) {
                next.delete(name);
            } else {
                next.add(name);
            }
            if (next.size >= 2) {
                setShowMergeBar(true);
                // Auto-recommend: highest scene count among selected
                const best = Array.from(next)
                    .map(n => ({ name: n, count: characters[n]?.count || 0 }))
                    .sort((a, b) => b.count - a.count)[0];
                setCanonicalChoice(best.name);
            } else {
                setShowMergeBar(false);
                setCanonicalChoice(null);
            }
            setShowCustomInput(false);
            setCustomName('');
            setMergeSuccess(null);
            return next;
        });
    }, [characters]);

    const handleMerge = useCallback(async () => {
        const finalCanonical = showCustomInput && customName.trim()
            ? customName.trim().toUpperCase()
            : canonicalChoice;

        if (!finalCanonical || !scriptId) return;

        const aliases = Array.from(selected).filter(n => n !== finalCanonical);
        if (aliases.length === 0) return;

        setMerging(true);
        try {
            const { mergeCharacters } = await import('../../services/apiService');
            const result = await mergeCharacters(scriptId, finalCanonical, aliases);
            setMergeSuccess(result);
            setSelected(new Set());
            setShowMergeBar(false);
            setCanonicalChoice(null);
            setShowCustomInput(false);
            setCustomName('');
            if (onMergeComplete) onMergeComplete();
        } catch (err) {
            console.error('Merge failed:', err);
            alert('Merge failed: ' + (err.response?.data?.error || err.message));
        } finally {
            setMerging(false);
        }
    }, [selected, canonicalChoice, customName, showCustomInput, scriptId, onMergeComplete]);

    const cancelMerge = useCallback(() => {
        setSelected(new Set());
        setShowMergeBar(false);
        setCanonicalChoice(null);
        setShowCustomInput(false);
        setCustomName('');
    }, []);

    const selectedArr = useMemo(() =>
        Array.from(selected)
            .map(n => ({ name: n, count: characters[n]?.count || 0 }))
            .sort((a, b) => b.count - a.count),
        [selected, characters]
    );

    return (
        <div className="script-summary">
            {/* Stats Row */}
            <div className="summary-stats-row">
                <div className="stat-item">
                    <CheckCircle size={16} className="stat-icon complete" />
                    <span className="stat-value">{stats.analyzed}</span>
                    <span className="stat-label">Analyzed</span>
                </div>
                <div className="stat-item">
                    <Clock size={16} className="stat-icon pending" />
                    <span className="stat-value">{stats.pending}</span>
                    <span className="stat-label">Pending</span>
                </div>
                <div className="stat-item">
                    <Users size={16} className="stat-icon" />
                    <span className="stat-value">{sortedCharacters.length}</span>
                    <span className="stat-label">Characters</span>
                </div>
                <div className="stat-item">
                    <MapPin size={16} className="stat-icon" />
                    <span className="stat-value">{sortedLocations.length}</span>
                    <span className="stat-label">Locations</span>
                </div>
            </div>

            {/* Merge Success Banner */}
            {mergeSuccess && (
                <div className="merge-success-banner">
                    <Check size={14} />
                    <span>
                        Merged into <strong>{mergeSuccess.canonical_name}</strong> — {mergeSuccess.scenes_updated} scenes updated
                    </span>
                    <button onClick={() => setMergeSuccess(null)}><X size={12} /></button>
                </div>
            )}

            <div className="summary-columns">
                {/* Characters Column */}
                <div className="summary-column">
                    <h4 className="column-title">
                        <Users size={14} />
                        Characters
                        {duplicateCount > 0 && (
                            <span className="duplicate-alert" title={`${duplicateCount} possible duplicate${duplicateCount > 1 ? 's' : ''} detected`}>
                                <AlertTriangle size={12} />
                                {duplicateCount}
                            </span>
                        )}
                    </h4>
                    {duplicateCount > 0 && selected.size === 0 && (
                        <p className="duplicate-hint">Select characters to merge duplicates</p>
                    )}
                    <div className="summary-list">
                        {sortedCharacters.length === 0 ? (
                            <p className="empty-text">No characters detected yet</p>
                        ) : (
                            sortedCharacters.map(([name, data]) => {
                                const isSuspect = duplicateSuspects.has(name);
                                const isSelected = selected.has(name);
                                return (
                                    <div
                                        key={name}
                                        className={`summary-item ${isSuspect ? 'suspect' : ''} ${isSelected ? 'selected' : ''}`}
                                        onClick={() => toggleSelect(name)}
                                        title={isSuspect ? `Possible duplicate — click to select for merge` : 'Click to select for merge'}
                                    >
                                        <div className="item-left">
                                            <span className={`item-checkbox ${isSelected ? 'checked' : ''}`}>
                                                {isSelected && <Check size={10} />}
                                            </span>
                                            <span className="item-name">{name}</span>
                                            {isSuspect && !isSelected && (
                                                <AlertTriangle size={12} className="suspect-icon" />
                                            )}
                                        </div>
                                        <span className="item-count">{data.count} scenes</span>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>

                {/* Locations Column */}
                <div className="summary-column">
                    <h4 className="column-title">
                        <MapPin size={14} />
                        Locations
                    </h4>
                    <div className="summary-list">
                        {sortedLocations.length === 0 ? (
                            <p className="empty-text">No locations detected yet</p>
                        ) : (
                            sortedLocations.map(([name, data]) => (
                                <div key={name} className="summary-item">
                                    <span className="item-name" title={name}>
                                        {name.length > 40 ? name.substring(0, 40) + '...' : name}
                                    </span>
                                    <span className="item-count">{data.count} scenes</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* Merge Bar */}
            {showMergeBar && selected.size >= 2 && (
                <div className="merge-bar">
                    <div className="merge-bar-header">
                        <Merge size={16} />
                        <span>Merge {selected.size} characters into:</span>
                    </div>
                    <div className="merge-options">
                        {selectedArr.map(({ name, count }) => (
                            <label key={name} className={`merge-option ${canonicalChoice === name && !showCustomInput ? 'recommended' : ''}`}>
                                <input
                                    type="radio"
                                    name="canonical"
                                    checked={canonicalChoice === name && !showCustomInput}
                                    onChange={() => { setCanonicalChoice(name); setShowCustomInput(false); }}
                                />
                                <span className="merge-option-name">{name}</span>
                                <span className="merge-option-count">{count} scenes</span>
                                {canonicalChoice === name && !showCustomInput && selectedArr[0].name === name && (
                                    <span className="merge-recommended-badge">Recommended</span>
                                )}
                            </label>
                        ))}
                        <label className={`merge-option ${showCustomInput ? 'recommended' : ''}`}>
                            <input
                                type="radio"
                                name="canonical"
                                checked={showCustomInput}
                                onChange={() => setShowCustomInput(true)}
                            />
                            <Edit3 size={12} />
                            <span className="merge-option-name">Custom name</span>
                        </label>
                        {showCustomInput && (
                            <input
                                type="text"
                                className="merge-custom-input"
                                placeholder="Type correct name..."
                                value={customName}
                                onChange={(e) => setCustomName(e.target.value)}
                                autoFocus
                            />
                        )}
                    </div>
                    <div className="merge-bar-info">
                        {(() => {
                            const aliases = selectedArr.filter(s =>
                                showCustomInput ? true : s.name !== canonicalChoice
                            );
                            const total = aliases.reduce((sum, s) => sum + s.count, 0);
                            return `${total} scene${total !== 1 ? 's' : ''} will be updated`;
                        })()}
                    </div>
                    <div className="merge-bar-actions">
                        <button className="merge-cancel-btn" onClick={cancelMerge} disabled={merging}>
                            Cancel
                        </button>
                        <button
                            className="merge-confirm-btn"
                            onClick={handleMerge}
                            disabled={merging || (showCustomInput && !customName.trim())}
                        >
                            {merging ? 'Merging...' : 'Merge'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ScriptSummary;
