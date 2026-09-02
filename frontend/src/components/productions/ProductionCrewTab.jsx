import { useState, useEffect, useCallback } from 'react';
import {
    listProductionCrew,
    removeProductionCrew,
    getDepartments,
} from '../../services/apiService';
import { Spinner } from '../ui';
import CrewAssignmentModal from './CrewAssignmentModal';
import CrewImportModal from './CrewImportModal';

const UNASSIGNED_KEY = '__unassigned__';

const formatRate = (row) => {
    if (row.job_rate === null || row.job_rate === undefined || row.job_rate === '') return '';
    return row.job_rate_unit ? `${row.job_rate} / ${row.job_rate_unit}` : String(row.job_rate);
};

const formatDates = (row) => {
    if (row.start_date && row.end_date) return `${row.start_date} → ${row.end_date}`;
    return row.start_date || row.end_date || '';
};

export default function ProductionCrewTab({ productionId, access }) {
    const [crew, setCrew] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [editing, setEditing] = useState(null);
    const [adding, setAdding] = useState(false);
    const [importing, setImporting] = useState(false);

    const canEdit = access?.can_edit_crew;
    const canViewSensitive = access?.can_view_sensitive;

    const loadCrew = useCallback(() => {
        return listProductionCrew(productionId)
            .then((data) => setCrew(data.crew || []))
            .catch((err) => setError(err.response?.data?.error || err.message || 'Failed to load crew'));
    }, [productionId]);

    useEffect(() => {
        let active = true;
        Promise.all([
            listProductionCrew(productionId),
            getDepartments().catch(() => ({ departments: [] })),
        ])
            .then(([crewData, deptData]) => {
                if (!active) return;
                setCrew(crewData.crew || []);
                setDepartments(deptData.departments || []);
            })
            .catch((err) => {
                if (active) setError(err.response?.data?.error || err.message || 'Failed to load crew');
            })
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [productionId]);

    const deptName = (code) => {
        const d = departments.find((x) => x.code === code);
        return d ? d.name : code;
    };

    const handleRemove = async (row) => {
        const who = row.contact?.name || row.contact?.company_name || 'this person';
        if (!window.confirm(`Remove ${who} from the crew?`)) return;
        try {
            await removeProductionCrew(productionId, row.id);
            await loadCrew();
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Could not remove that assignment');
        }
    };

    const closeAndRefresh = () => {
        setAdding(false);
        setEditing(null);
        setImporting(false);
        loadCrew();
    };

    if (loading) {
        return <div className="production-page-loading"><Spinner size={32} /></div>;
    }

    // Group by department_code (null → unassigned bucket)
    const groups = new Map();
    for (const row of crew) {
        const key = row.department_code || UNASSIGNED_KEY;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(row);
    }
    const knownKeys = departments.map((d) => d.code).filter((c) => groups.has(c));
    // Any grouped department code not in the fetched departments list (renamed,
    // removed, or getDepartments() failed) — keep its rows visible.
    const orphanKeys = [...groups.keys()].filter(
        (k) => k !== UNASSIGNED_KEY && !knownKeys.includes(k));
    const orderedKeys = [
        ...knownKeys,
        ...orphanKeys,
        ...(groups.has(UNASSIGNED_KEY) ? [UNASSIGNED_KEY] : []),
    ];

    return (
        <div className="production-crew">
            <div className="production-scripts-head">
                <h3>Crew</h3>
                {canEdit && (
                    <div className="production-crew-actions">
                        <button onClick={() => setAdding(true)}>Add crew</button>
                        <button onClick={() => setImporting(true)}>Import CSV</button>
                    </div>
                )}
            </div>

            {error && <p className="production-page-error">{error}</p>}

            {crew.length === 0 ? (
                <p className="production-scripts-empty">
                    {canEdit ? 'No crew yet. Add people or import a CSV.' : 'No crew yet.'}
                </p>
            ) : (
                orderedKeys.map((key) => (
                    <section key={key} className="production-crew-group">
                        <h4>{key === UNASSIGNED_KEY ? 'Unassigned / Vendors' : deptName(key)}</h4>
                        <ul className="production-crew-list">
                            {groups.get(key).map((row) => (
                                <li key={row.id}>
                                    <div className="production-crew-row-main">
                                        <span className="production-crew-name">
                                            {row.contact?.name || row.contact?.company_name || 'Unknown'}
                                        </span>
                                        {row.role && <span className="production-crew-role">{row.role}</span>}
                                        {!canViewSensitive ? (
                                            <span className="production-crew-rate production-crew-rate-hidden">rate hidden</span>
                                        ) : formatRate(row) && (
                                            <span className="production-crew-rate">{formatRate(row)}</span>
                                        )}
                                        {formatDates(row) && (
                                            <span className="production-crew-dates">{formatDates(row)}</span>
                                        )}
                                    </div>
                                    {canEdit && (
                                        <div className="production-crew-row-actions">
                                            <button onClick={() => setEditing(row)}>Edit</button>
                                            <button onClick={() => handleRemove(row)}>Remove</button>
                                        </div>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </section>
                ))
            )}

            {adding && (
                <CrewAssignmentModal
                    productionId={productionId}
                    departments={departments}
                    onSaved={closeAndRefresh}
                    onClose={() => setAdding(false)}
                />
            )}
            {editing && (
                <CrewAssignmentModal
                    productionId={productionId}
                    initial={editing}
                    departments={departments}
                    onSaved={closeAndRefresh}
                    onClose={() => setEditing(null)}
                />
            )}
            {importing && (
                <CrewImportModal
                    productionId={productionId}
                    onDone={closeAndRefresh}
                    onClose={() => setImporting(false)}
                />
            )}
        </div>
    );
}
