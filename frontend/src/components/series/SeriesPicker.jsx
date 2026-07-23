import { useState, useEffect, useRef } from 'react';
import { listSeries, createSeries, listSeasons, createSeason, listEpisodes } from '../../services/apiService';
import './SeriesPicker.css';

/**
 * SeriesPicker - three-state picker for assigning a script to a series/season,
 * plus a compact "known series" view used when arriving via a deep link.
 *
 * States: 'none' (default, no assignment), 'existing' (pick a series +
 * season), 'new' (create a series, season defaults to 1).
 *
 * Calls onAssign(seasonId, episodeNumber) when the user has made a
 * complete selection; onAssign(null, null) for the 'none' state. The
 * caller (ScriptUpload or a reassignment surface) decides what to do with
 * that -- fire it immediately, or wait for a "confirm" action.
 *
 * autoFireNone (default true): in the upload flow, landing on 'none' means
 * "the script simply isn't part of a series" and should report that the
 * instant the user picks it (or on initial mount, since 'none' is the
 * default). In a reassignment context (SeriesAssignmentModal), 'none' means
 * "remove this script's existing assignment" -- a destructive action that
 * must NOT fire just because the modal opened with 'none' as the initial
 * mode. Pass autoFireNone={false} there; the 'none' panel then renders an
 * explicit "Remove from series" button instead of firing automatically.
 *
 * initialSeriesId/initialSeasonId/initialEpisodeNumber: optional deep-link
 * prefill (used by the "+ Add episode" action on a season's group header in
 * ScriptTable, which navigates to /upload?seriesId=..&seasonId=..). When
 * both initialSeriesId and initialSeasonId are set, isKnownSeries is true
 * and the picker renders a compact "known series" view (series shown as
 * fixed context, season + episode number as live editable controls) instead
 * of the classic 3-tab picker -- unless the user clicks "Not this series?",
 * which sets overridden=true and reveals the classic tabs from a clean
 * 'none' state. initialEpisodeNumber is accepted but unused on the
 * known-series path -- the suggested episode number is now computed here
 * from listEpisodes() whenever the selected season changes, since numbering
 * is per-season and the season is a live dropdown in this view.
 */
export default function SeriesPicker({
    onAssign,
    autoFireNone = true,
    initialSeriesId = null,
    initialSeasonId = null,
    initialEpisodeNumber = null,
}) {
    const isKnownSeries = !!(initialSeriesId && initialSeasonId);
    const [overridden, setOverridden] = useState(false);
    const showKnownView = isKnownSeries && !overridden;

    const [mode, setMode] = useState(initialSeasonId && !isKnownSeries ? 'existing' : 'none');
    const [seriesList, setSeriesList] = useState([]);
    const [selectedSeriesId, setSelectedSeriesId] = useState(isKnownSeries ? initialSeriesId : '');
    const [seasons, setSeasons] = useState([]);
    const [selectedSeasonId, setSelectedSeasonId] = useState('');
    const [episodeNumber, setEpisodeNumber] = useState(
        initialEpisodeNumber != null ? String(initialEpisodeNumber) : ''
    );
    const [newSeriesTitle, setNewSeriesTitle] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const appliedInitialSeason = useRef(false);

    // Known-series view: fetch the series list once (to resolve the badge
    // name) and the season list for the known series -- unconditionally,
    // not gated behind mode === 'existing' like the classic view, since
    // there's no tab click to gate it on here.
    useEffect(() => {
        if (!showKnownView) return;
        listSeries()
            .then((data) => setSeriesList(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'));
        listSeasons(initialSeriesId)
            .then((data) => setSeasons(data.seasons || []))
            .catch((err) => setError(err.message || 'Failed to load seasons'));
        setSelectedSeasonId(initialSeasonId);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [showKnownView]);

    // Known-series view: whenever the selected season changes, recompute the
    // suggested next episode number (numbering is per-season) and fire
    // onAssign so pendingSeasonAssignment in ScriptUpload stays in sync
    // without the user touching anything.
    useEffect(() => {
        if (!showKnownView || !selectedSeasonId) return;
        let cancelled = false;
        listEpisodes(selectedSeasonId)
            .then((data) => {
                if (cancelled) return;
                const episodes = data.episodes || [];
                const nextNumber = episodes.reduce(
                    (max, ep) => Math.max(max, ep.episode_number || 0),
                    0
                ) + 1;
                setEpisodeNumber(String(nextNumber));
                onAssign(selectedSeasonId, nextNumber);
            })
            .catch((err) => {
                if (!cancelled) setError(err.message || 'Failed to load episodes');
            });
        return () => {
            cancelled = true;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [showKnownView, selectedSeasonId]);

    useEffect(() => {
        if (showKnownView) return;
        if (mode !== 'existing') return;
        listSeries()
            .then((data) => setSeriesList(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'));
    }, [mode, showKnownView]);

    useEffect(() => {
        if (showKnownView) return;
        let cancelled = false;
        const isFirstRunWithPrefill = !appliedInitialSeason.current && !!initialSeasonId;
        if (isFirstRunWithPrefill) {
            // Flip synchronously (not inside the .then() below) so a series
            // change that fires a second effect run before this promise
            // resolves sees the ref already set, and correctly treats
            // itself as a normal (non-prefill) run instead of racing to
            // apply the original prefill onto the newly selected series.
            appliedInitialSeason.current = true;
        } else {
            setSelectedSeasonId('');
        }
        if (!selectedSeriesId) {
            setSeasons([]);
            return;
        }
        listSeasons(selectedSeriesId)
            .then((data) => {
                if (cancelled) return;
                setSeasons(data.seasons || []);
                if (isFirstRunWithPrefill) {
                    setSelectedSeasonId(initialSeasonId);
                }
            })
            .catch((err) => {
                if (!cancelled) setError(err.message || 'Failed to load seasons');
            });
        return () => {
            cancelled = true;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedSeriesId, showKnownView]);

    useEffect(() => {
        if (showKnownView) return;
        if (mode === 'none' && autoFireNone) {
            onAssign(null, null);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [mode, showKnownView]);

    const handleExistingConfirm = () => {
        if (!selectedSeasonId || !episodeNumber) {
            setError('Pick a season and enter an episode number');
            return;
        }
        onAssign(selectedSeasonId, Number(episodeNumber));
    };

    const handleNewConfirm = async () => {
        if (!newSeriesTitle.trim() || !episodeNumber) {
            setError('Enter a series title and episode number');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const { season } = await createSeries(newSeriesTitle.trim());
            onAssign(season.id, Number(episodeNumber));
        } catch (err) {
            setError(err.message || 'Failed to create series');
        } finally {
            setLoading(false);
        }
    };

    const handleOverride = () => {
        setOverridden(true);
        setMode('none');
        setSelectedSeriesId('');
        setSelectedSeasonId('');
        setEpisodeNumber('');
        setError(null);
    };

    const handleKnownSeasonChange = (e) => {
        setSelectedSeasonId(e.target.value);
    };

    const handleKnownEpisodeNumberChange = (e) => {
        const value = e.target.value;
        setEpisodeNumber(value);
        if (selectedSeasonId && value) {
            onAssign(selectedSeasonId, Number(value));
        }
    };

    if (showKnownView) {
        const knownSeries = seriesList.find((s) => s.id === initialSeriesId);
        const seriesLabel = knownSeries?.title || 'Series';

        return (
            <div className="series-picker">
                {error && <p className="series-picker-error">{error}</p>}
                <div className="series-picker-known">
                    <div className="series-picker-known-badge">{seriesLabel}</div>
                    <div className="series-picker-known-fields">
                        <div className="series-picker-known-field">
                            <label>Season</label>
                            <select value={selectedSeasonId} onChange={handleKnownSeasonChange}>
                                {seasons.map((s) => (
                                    <option key={s.id} value={s.id}>{s.title || `Season ${s.season_number}`}</option>
                                ))}
                            </select>
                        </div>
                        <div className="series-picker-known-field">
                            <label>Episode #</label>
                            <input
                                type="number"
                                min="1"
                                value={episodeNumber}
                                onChange={handleKnownEpisodeNumberChange}
                            />
                        </div>
                    </div>
                    <p className="series-picker-known-hint">
                        Suggested next — change to upload out of sequence
                    </p>
                    <button type="button" className="series-picker-override-btn" onClick={handleOverride}>
                        Not this series?
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="series-picker">
            <div className="series-picker-modes">
                <button type="button" className={mode === 'none' ? 'active' : ''} onClick={() => setMode('none')}>
                    Not part of a series
                </button>
                <button type="button" className={mode === 'existing' ? 'active' : ''} onClick={() => setMode('existing')}>
                    Add to existing series
                </button>
                <button type="button" className={mode === 'new' ? 'active' : ''} onClick={() => setMode('new')}>
                    Create new series
                </button>
            </div>

            {error && <p className="series-picker-error">{error}</p>}

            {mode === 'none' && !autoFireNone && (
                <div className="series-picker-none">
                    <button type="button" onClick={() => onAssign(null, null)}>
                        Remove from series
                    </button>
                </div>
            )}

            {mode === 'existing' && (
                <div className="series-picker-existing">
                    <select value={selectedSeriesId} onChange={(e) => setSelectedSeriesId(e.target.value)}>
                        <option value="">Select a series...</option>
                        {seriesList.map((s) => (
                            <option key={s.id} value={s.id}>{s.title}</option>
                        ))}
                    </select>
                    <select
                        value={selectedSeasonId}
                        onChange={(e) => setSelectedSeasonId(e.target.value)}
                        disabled={!selectedSeriesId}
                    >
                        <option value="">Select a season...</option>
                        {seasons.map((s) => (
                            <option key={s.id} value={s.id}>{s.title || `Season ${s.season_number}`}</option>
                        ))}
                    </select>
                    <input
                        type="number"
                        min="1"
                        placeholder="Episode #"
                        value={episodeNumber}
                        onChange={(e) => setEpisodeNumber(e.target.value)}
                    />
                    <button type="button" onClick={handleExistingConfirm}>Assign</button>
                </div>
            )}

            {mode === 'new' && (
                <div className="series-picker-new">
                    <input
                        type="text"
                        placeholder="Series title"
                        value={newSeriesTitle}
                        onChange={(e) => setNewSeriesTitle(e.target.value)}
                    />
                    <input
                        type="number"
                        min="1"
                        placeholder="Episode #"
                        value={episodeNumber}
                        onChange={(e) => setEpisodeNumber(e.target.value)}
                    />
                    <button type="button" onClick={handleNewConfirm} disabled={loading}>
                        {loading ? 'Creating...' : 'Create & Assign'}
                    </button>
                </div>
            )}
        </div>
    );
}
