import { useState, useEffect } from 'react';
import { listSeries, createSeries, listSeasons, createSeason } from '../../services/apiService';

/**
 * SeriesPicker - three-state picker for assigning a script to a series/season.
 *
 * States: 'none' (default, no assignment), 'existing' (pick a series +
 * season), 'new' (create a series, season defaults to 1).
 *
 * Calls onAssign(seasonId, episodeNumber) when the user has made a
 * complete selection; onAssign(null, null) if they pick 'none'. The
 * caller (ScriptUpload or a reassignment surface) decides what to do with
 * that -- fire it immediately, or wait for a "confirm" action.
 */
export default function SeriesPicker({ onAssign }) {
    const [mode, setMode] = useState('none');
    const [seriesList, setSeriesList] = useState([]);
    const [selectedSeriesId, setSelectedSeriesId] = useState('');
    const [seasons, setSeasons] = useState([]);
    const [selectedSeasonId, setSelectedSeasonId] = useState('');
    const [episodeNumber, setEpisodeNumber] = useState('');
    const [newSeriesTitle, setNewSeriesTitle] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (mode !== 'existing') return;
        listSeries()
            .then((data) => setSeriesList(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'));
    }, [mode]);

    useEffect(() => {
        setSelectedSeasonId('');
        if (!selectedSeriesId) {
            setSeasons([]);
            return;
        }
        listSeasons(selectedSeriesId)
            .then((data) => setSeasons(data.seasons || []))
            .catch((err) => setError(err.message || 'Failed to load seasons'));
    }, [selectedSeriesId]);

    useEffect(() => {
        if (mode === 'none') {
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
