import React, { useState, useMemo, useCallback } from 'react';
import { Users, MapPin, CheckCircle, Clock, AlertTriangle, Merge, X, Check, Edit3 } from 'lucide-react';
import { Badge } from '../ui';
import { useToast } from '../../context/ToastContext';
import { mergeCharacters, mergeLocations, retryFailedScenes } from '../../services/apiService';
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
 * Detect suspected duplicate names (characters or locations).
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
 * Client-side mirror of the backend merge matching, used to detect when
 * selected items already reduce to the same value (so a merge would be a no-op).
 * Characters match case-insensitively (backend upcases). Locations now merge on
 * raw setting text like character names, where a case-only difference IS a real
 * merge (villa -> VILLA) — so only trim + collapse whitespace, preserving case.
 */
function normalizeForMerge(type, name) {
    if (type === 'locations') {
        return (name || '').trim().replace(/\s+/g, ' ');
    }
    return (name || '').trim().toUpperCase().replace(/\s+/g, ' ');
}

/** Count the number of distinct duplicate groups from a suspects map. */
function countDuplicateGroups(suspects) {
    const groups = new Set();
    suspects.forEach((partners, name) => {
        groups.add([name, ...Array.from(partners)].sort().join('|'));
    });
    return groups.size;
}

/**
 * Per-entity-type config. Characters and locations share the exact same
 * selection + merge-bar interaction; only the data source, labels, and
 * merge API call differ.
 */
const ENTITY_TYPES = {
    characters: { label: 'character', labelPlural: 'characters', mergeFn: mergeCharacters },
    locations: { label: 'location', labelPlural: 'locations', mergeFn: mergeLocations },
};

/**
 * ScriptSummary - Collapsible panel showing aggregated script data with
 * duplicate detection and merge capability for BOTH characters and locations.
 * A single selection/merge flow is active at a time (`mergeType`).
 */
const ScriptSummary = ({ characters, locations, stats, scriptId, onMergeComplete }) => {
    const [mergeType, setMergeType] = useState(null); // 'characters' | 'locations' | null
    const [selected, setSelected] = useState(new Set());
    const [showMergeBar, setShowMergeBar] = useState(false);
    const [merging, setMerging] = useState(false);
    const [canonicalChoice, setCanonicalChoice] = useState(null);
    const [customName, setCustomName] = useState('');
    const [showCustomInput, setShowCustomInput] = useState(false);
    const [mergeSuccess, setMergeSuccess] = useState(null);
    const [retryingFailed, setRetryingFailed] = useState(false);
    const toast = useToast();

    const handleRetryFailed = useCallback(async () => {
        if (!scriptId) return;
        setRetryingFailed(true);
        try {
            const res = await retryFailedScenes(scriptId);
            const count = res?.retrying;
            toast.info(
                'Retrying failed scenes',
                count != null ? `Retrying ${count} scene${count === 1 ? '' : 's'}.` : 'Retrying failed scenes in the background.'
            );
            await onMergeComplete?.();
        } catch (err) {
            toast.error('Retry failed', err.response?.data?.error || err.message);
        } finally {
            setRetryingFailed(false);
        }
    }, [scriptId, onMergeComplete, toast]);

    const dataFor = useCallback(
        (type) => (type === 'locations' ? locations : characters),
        [characters, locations]
    );

    const sortedCharacters = useMemo(() =>
        Object.entries(characters).sort((a, b) => b[1].count - a[1].count),
        [characters]
    );

    const sortedLocations = useMemo(() =>
        Object.entries(locations).sort((a, b) => b[1].count - a[1].count),
        [locations]
    );

    const characterSuspects = useMemo(() =>
        detectDuplicates(sortedCharacters.map(([name]) => name)),
        [sortedCharacters]
    );

    const locationSuspects = useMemo(() =>
        detectDuplicates(sortedLocations.map(([name]) => name)),
        [sortedLocations]
    );

    const characterDupCount = useMemo(() => countDuplicateGroups(characterSuspects), [characterSuspects]);
    const locationDupCount = useMemo(() => countDuplicateGroups(locationSuspects), [locationSuspects]);

    const resetMerge = useCallback(() => {
        setSelected(new Set());
        setShowMergeBar(false);
        setCanonicalChoice(null);
        setShowCustomInput(false);
        setCustomName('');
    }, []);

    const toggleSelect = useCallback((name, type) => {
        // Switching entity type starts a fresh selection.
        const switching = mergeType !== type;
        const next = new Set(switching ? [] : selected);
        if (next.has(name)) {
            next.delete(name);
        } else {
            next.add(name);
        }

        const dataMap = dataFor(type);
        setMergeType(next.size > 0 ? type : null);
        setSelected(next);
        setMergeSuccess(null);
        setShowCustomInput(false);
        setCustomName('');

        if (next.size >= 2) {
            // Auto-recommend the name with the highest scene count.
            const best = Array.from(next)
                .map(n => ({ name: n, count: dataMap[n]?.count || 0 }))
                .sort((a, b) => b.count - a.count)[0];
            setCanonicalChoice(best.name);
            setShowMergeBar(true);
        } else {
            setCanonicalChoice(null);
            setShowMergeBar(false);
        }
    }, [mergeType, selected, dataFor]);

    const handleMerge = useCallback(async () => {
        if (!mergeType || !scriptId) return;

        const finalCanonical = showCustomInput && customName.trim()
            ? customName.trim().toUpperCase()
            : canonicalChoice;
        if (!finalCanonical) return;

        const aliases = Array.from(selected).filter(n => n !== finalCanonical);
        if (aliases.length === 0) return;

        // Guard: if every selected alias already reduces to the canonical name
        // (e.g. case/punctuation variants of the same place), the backend would
        // reject with "No valid aliases to merge". Surface a clear message
        // instead of firing a doomed request.
        const canonNorm = normalizeForMerge(mergeType, finalCanonical);
        const effectiveAliases = aliases.filter(a => {
            const an = normalizeForMerge(mergeType, a);
            return an && an !== canonNorm;
        });
        if (effectiveAliases.length === 0) {
            toast.info(
                'Already the same',
                `These ${ENTITY_TYPES[mergeType].labelPlural} already share the same name — nothing to merge. If they look different, refresh the page and try again.`
            );
            return;
        }

        setMerging(true);
        try {
            const result = await ENTITY_TYPES[mergeType].mergeFn(scriptId, finalCanonical, aliases);
            setMergeSuccess({
                type: mergeType,
                // characters return canonical_name, locations return canonical_place
                canonical: result.canonical_name || result.canonical_place || finalCanonical,
                scenesUpdated: result.scenes_updated,
            });
            resetMerge();
            setMergeType(null);
            if (onMergeComplete) onMergeComplete();
        } catch (err) {
            console.error('Merge failed:', err);
            toast.error('Merge Failed', err.response?.data?.error || err.message);
        } finally {
            setMerging(false);
        }
    }, [mergeType, selected, canonicalChoice, customName, showCustomInput, scriptId, onMergeComplete, resetMerge, toast]);

    const cancelMerge = useCallback(() => {
        resetMerge();
        setMergeType(null);
    }, [resetMerge]);

    const selectedArr = useMemo(() => {
        if (!mergeType) return [];
        const dataMap = dataFor(mergeType);
        return Array.from(selected)
            .map(n => ({ name: n, count: dataMap[n]?.count || 0 }))
            .sort((a, b) => b.count - a.count);
    }, [selected, mergeType, dataFor]);

    const renderColumn = (type, icon, title, sortedItems, suspects, dupCount) => {
        const isActive = mergeType === type;
        return (
            <div className="summary-column">
                <h4 className="column-title">
                    {icon}
                    {title}
                    {dupCount > 0 && (
                        <span
                            className="duplicate-alert"
                            title={`${dupCount} possible duplicate${dupCount > 1 ? 's' : ''} detected`}
                        >
                            <AlertTriangle size={12} />
                            {dupCount}
                        </span>
                    )}
                </h4>
                {dupCount > 0 && !(isActive && selected.size > 0) && (
                    <p className="duplicate-hint">Select {ENTITY_TYPES[type].labelPlural} to merge duplicates</p>
                )}
                <div className="summary-list">
                    {sortedItems.length === 0 ? (
                        <p className="empty-text">No {title.toLowerCase()} detected yet</p>
                    ) : (
                        sortedItems.map(([name, data]) => {
                            const isSuspect = suspects.has(name);
                            const isSelected = isActive && selected.has(name);
                            const display = name.length > 40 ? name.substring(0, 40) + '...' : name;
                            return (
                                <div
                                    key={name}
                                    className={`summary-item ${isSuspect ? 'suspect' : ''} ${isSelected ? 'selected' : ''}`}
                                    onClick={() => toggleSelect(name, type)}
                                    title={isSuspect ? 'Possible duplicate — click to select for merge' : 'Click to select for merge'}
                                >
                                    <div className="item-left">
                                        <span className={`item-checkbox ${isSelected ? 'checked' : ''}`}>
                                            {isSelected && <Check size={10} />}
                                        </span>
                                        <span className="item-name">{display}</span>
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
        );
    };

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
                {stats.failed > 0 && (
                    <button
                        type="button"
                        className="retry-all-failed-btn"
                        onClick={handleRetryFailed}
                        disabled={retryingFailed}
                    >
                        {retryingFailed ? 'Retrying…' : `Retry all failed (${stats.failed})`}
                    </button>
                )}
            </div>

            {/* Merge Success Banner */}
            {mergeSuccess && (
                <div className="merge-success-banner">
                    <Check size={14} />
                    <span>
                        Merged into <strong>{mergeSuccess.canonical}</strong> — {mergeSuccess.scenesUpdated} scenes updated
                    </span>
                    <button onClick={() => setMergeSuccess(null)}><X size={12} /></button>
                </div>
            )}

            <div className="summary-columns">
                {renderColumn('characters', <Users size={14} />, 'Characters', sortedCharacters, characterSuspects, characterDupCount)}
                {renderColumn('locations', <MapPin size={14} />, 'Locations', sortedLocations, locationSuspects, locationDupCount)}
            </div>

            {/* Merge Bar */}
            {showMergeBar && mergeType && selected.size >= 2 && (
                <div className="merge-bar">
                    <div className="merge-bar-header">
                        <Merge size={16} />
                        <span>Merge {selected.size} {ENTITY_TYPES[mergeType].labelPlural} into:</span>
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
                                    <Badge variant="success">Recommended</Badge>
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
