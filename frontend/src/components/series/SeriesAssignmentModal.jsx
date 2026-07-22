import { useState } from 'react';
import { Modal } from '../ui';
import { updateScriptSeason } from '../../services/apiService';
import SeriesPicker from './SeriesPicker';

/**
 * SeriesAssignmentModal - lets a user assign, reassign, or clear a script's
 * series/season/episode after upload, via the "Series" action in
 * ScriptTable. Reuses SeriesPicker for the actual pick/create UI, but with
 * autoFireNone={false} so opening the modal (which defaults to the 'none'
 * tab) never silently clears an existing assignment -- the user must
 * explicitly click "Remove from series" to do that.
 *
 * This fills the gap in the original design: the upload flow could assign a
 * script to a series, but there was no way to fix a missed or wrong
 * assignment afterward.
 */
export default function SeriesAssignmentModal({ isOpen, onClose, script, onSaved }) {
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);

    if (!script) return null;

    const handleAssign = async (seasonId, episodeNumber) => {
        setSaving(true);
        setError(null);
        try {
            await updateScriptSeason(script.script_id, seasonId, episodeNumber);
            onSaved();
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to update series assignment');
        } finally {
            setSaving(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={`Series: ${script.script_name}`}
            size="md"
        >
            <p className="series-assignment-current">
                {script.episode_number
                    ? `Currently assigned as Episode ${script.episode_number} of a season.`
                    : 'Not currently part of a series.'}
            </p>

            <SeriesPicker
                onAssign={handleAssign}
                autoFireNone={false}
            />

            {saving && <p className="series-assignment-status">Saving...</p>}
            {error && <p className="series-picker-error">{error}</p>}
        </Modal>
    );
}
