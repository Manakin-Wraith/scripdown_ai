import { useState, useEffect, useRef } from 'react';
import { listSeries, createSeries, listSeasons, createSeason } from '../../services/apiService';

/**
 * SeriesPicker - three-state picker for assigning a script to a series/season.
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
 * initialSeasonId is set, the picker starts in 'existing' mode with that
 * series/season/episode-number pre-selected -- fully editable, not locked
 * in, matching the "assignment is always overridable" principle used
 * elsewhere in this component.
 */
export default function SeriesPicker({
    onAssign,
    autoFireNone = true,
    initialSeriesId = null,
    initialSeasonId = null,
    initialEpisodeNumber = null,
}) {
    const [mode, setMode] = useState(initialSeasonId ? 'existing' : 'none');
    const [seriesList, setSeriesList] = useState([]);
    const [selectedSeriesId, setSelectedSeriesId] = useState(initialSeriesId || '');
    const [seasons, setSeasons] = useState([]);
    const [selectedSeasonId, setSelectedSeasonId] = useState('');
    const [episodeNumber, setEpisodeNumber] = useState(
        initialEpisodeNumber != null ? String(initialEpisodeNumber) : ''
    );
    const [newSeriesTitle, setNewSeriesTitle] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const appliedInitialSeason = useRef(false);

    useEffect(() => {
        if (mode !== 'existing') return;
        listSeries()
            .then((data) => setSeriesList(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'));
    }, [mode]);

    useEffect(() => {
        const isFirstRunWithPrefill = !appliedInitialSeason.current && !!initialSeasonId;
        if (!isFirstRunWithPrefill) {
            setSelectedSeasonId('');
        }
        if (!selectedSeriesId) {
            setSeasons([]);
            return;
        }
        listSeasons(selectedSeriesId)
            .then((data) => {
                setSeasons(data.seasons || []);
                if (isFirstRunWithPrefill) {
                    setSelectedSeasonId(initialSeasonId);
                    appliedInitialSeason.current = true;
                }
            })
            .catch((err) => setError(err.message || 'Failed to load seasons'));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedSeriesId]);

    useEffect(() => {
        if (mode === 'none' && autoFireNone) {
            onAssign(null, null);
        }
    }, [mode]); // eslint-disable-line react-hooks/exhaustive-deps

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
