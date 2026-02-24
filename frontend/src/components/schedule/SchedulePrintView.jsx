import React, { useMemo } from 'react';
import { formatEighths, getSceneEighths } from '../../utils/sceneUtils';
import './SchedulePrintView.css';

const formatDisplayDate = (dateStr) => {
    if (!dateStr) return null;
    try {
        return new Date(dateStr + 'T00:00:00').toLocaleDateString(undefined, {
            weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
        });
    } catch {
        return dateStr;
    }
};

const getCharacterNames = (characters) => {
    if (!Array.isArray(characters) || characters.length === 0) return '';
    return characters
        .map(c => (typeof c === 'string' ? c : c?.name))
        .filter(Boolean)
        .join(', ');
};

const getList = (arr) => {
    if (!Array.isArray(arr) || arr.length === 0) return '';
    return arr.map(i => (typeof i === 'string' ? i : i?.name || '')).filter(Boolean).join(', ');
};

// ─── One-Liner Row ────────────────────────────────────────────────────────────
const OneLinerRow = ({ scene, index }) => {
    const eighths = getSceneEighths(scene);
    const intExt = scene.int_ext || '';
    const intExtClass = intExt === 'INT' ? 'print-int' : intExt === 'EXT' ? 'print-ext' : '';
    const castNames = getCharacterNames(scene.characters);

    return (
        <tr className={`print-scene-row ${index % 2 === 0 ? 'print-row-even' : ''} ${scene.is_omitted ? 'print-omitted' : ''}`}>
            <td className="print-col-num">{scene.scene_number}{scene.is_omitted && <span className="print-omit-tag"> OMIT</span>}</td>
            <td className={`print-col-ie ${intExtClass}`}>{intExt}</td>
            <td className="print-col-setting">{scene.setting || '—'}</td>
            <td className="print-col-tod">{scene.time_of_day || '—'}</td>
            <td className="print-col-cast">{castNames || '—'}</td>
            <td className="print-col-pages">{eighths > 0 ? formatEighths(eighths) : '—'}</td>
        </tr>
    );
};

// ─── Main Component ───────────────────────────────────────────────────────────
const SchedulePrintView = ({ days, scheduleName, metadata }) => {

    const totals = useMemo(() => {
        let totalEighths = 0;
        let totalScenes = 0;
        days.forEach(day => {
            (day.scenes || []).forEach(ds => {
                const scene = ds.scenes || ds.scene || {};
                totalEighths += getSceneEighths(scene);
                totalScenes++;
            });
        });
        return { totalEighths, totalScenes };
    }, [days]);

    const today = new Date().toLocaleDateString(undefined, {
        month: 'long', day: 'numeric', year: 'numeric',
    });

    return (
        <div id="schedule-print-view" className="schedule-print-view">
            {/* Cover header */}
            <div className="print-cover">
                <div className="print-cover-left">
                    <div className="print-script-title">{metadata?.title || 'Untitled Script'}</div>
                    {metadata?.writer && (
                        <div className="print-script-writer">Written by {metadata.writer}</div>
                    )}
                </div>
                <div className="print-cover-right">
                    <div className="print-schedule-name">{scheduleName || 'Shooting Schedule'}</div>
                    <div className="print-cover-meta">
                        <span>{days.length} Shooting Day{days.length !== 1 ? 's' : ''}</span>
                        <span className="print-meta-sep">·</span>
                        <span>{totals.totalScenes} Scene{totals.totalScenes !== 1 ? 's' : ''}</span>
                        <span className="print-meta-sep">·</span>
                        <span>{formatEighths(totals.totalEighths)} Pages</span>
                    </div>
                    <div className="print-generated-date">Generated {today}</div>
                </div>
            </div>

            <div className="print-cover-rule" />

            {/* Days */}
            {days.map((day) => {
                const scenes = (day.scenes || []).map(ds => ds.scenes || ds.scene || {});
                const dayEighths = scenes.reduce((sum, s) => sum + getSceneEighths(s), 0);
                const displayDate = formatDisplayDate(day.shoot_date);

                const uniqueLocations = [...new Set(scenes.map(s => s.setting).filter(Boolean))];
                const uniqueChars = new Set();
                scenes.forEach(s => {
                    (s.characters || []).forEach(c => {
                        const name = typeof c === 'string' ? c : c?.name;
                        if (name) uniqueChars.add(name);
                    });
                });

                return (
                    <div key={day.id} className="print-day-section">
                        {/* Day header */}
                        <div className="print-day-header">
                            <div className="print-day-header-left">
                                <span className="print-day-label">DAY {day.day_number}</span>
                                {displayDate && (
                                    <span className="print-day-date">{displayDate}</span>
                                )}
                            </div>
                            <div className="print-day-header-right">
                                <span className="print-day-stat">{scenes.length} scene{scenes.length !== 1 ? 's' : ''}</span>
                                <span className="print-day-stat">{formatEighths(dayEighths)} pages</span>
                                <span className="print-day-stat">{uniqueChars.size} cast</span>
                                <span className="print-day-stat">{uniqueLocations.length} location{uniqueLocations.length !== 1 ? 's' : ''}</span>
                            </div>
                        </div>

                        {/* Cast summary line */}
                        {uniqueChars.size > 0 && (
                            <div className="print-day-cast-summary">
                                <span className="print-detail-label">Cast:</span>
                                {[...uniqueChars].join(', ')}
                            </div>
                        )}

                        {/* Scenes */}
                        <table className="print-one-liner-table">
                            <thead>
                                <tr className="print-table-head">
                                    <th className="print-col-num">#</th>
                                    <th className="print-col-ie">I/E</th>
                                    <th className="print-col-setting">Location</th>
                                    <th className="print-col-tod">TOD</th>
                                    <th className="print-col-cast">Cast</th>
                                    <th className="print-col-pages">Pages</th>
                                </tr>
                            </thead>
                            <tbody>
                                {scenes.map((scene, i) => (
                                    <OneLinerRow key={scene.id || i} scene={scene} index={i} />
                                ))}
                            </tbody>
                            <tfoot>
                                <tr className="print-day-total-row">
                                    <td colSpan={5} className="print-day-total-label">Day {day.day_number} Total</td>
                                    <td className="print-col-pages print-day-total-pages">{formatEighths(dayEighths)}</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                );
            })}

            {/* Grand total footer */}
            <div className="print-grand-total">
                <span>Total: {days.length} Days · {totals.totalScenes} Scenes · {formatEighths(totals.totalEighths)} Pages</span>
            </div>
        </div>
    );
};

export default SchedulePrintView;
