import { useState } from 'react';
import { importProductionCrew } from '../../services/apiService';

/**
 * Bulk-import crew from a CSV file.
 * Props: { productionId, onDone, onClose }
 */
export default function CrewImportModal({ productionId, onDone, onClose }) {
    const [file, setFile] = useState(null);
    const [importing, setImporting] = useState(false);
    const [error, setError] = useState(null);
    const [summary, setSummary] = useState(null);

    const handleImport = async () => {
        if (!file || importing) return;
        setError(null);
        setImporting(true);
        try {
            const r = await importProductionCrew(productionId, file);
            setSummary(r);
        } catch (err) {
            if (err.response?.status === 400) {
                setError(err.response.data?.error || 'That file could not be imported.');
            } else {
                setError(err.message || 'Import failed.');
            }
        } finally {
            setImporting(false);
        }
    };

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>Import crew from CSV</h3>

                {!summary && (
                    <>
                        <p className="crew-import-help">
                            Columns: name, email, phone, company_name, role, department, rate, rate_unit, notes.
                            {' '}
                            <a href="/crew-import-template.csv" download>Download template</a>
                        </p>
                        <input
                            type="file"
                            accept=".csv"
                            onChange={(e) => { setFile(e.target.files?.[0] || null); setError(null); }}
                        />
                        {error && <p className="production-page-error">{error}</p>}
                        <div className="contact-form-actions">
                            <button type="button" className="production-modal-close" onClick={onClose}>
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="production-new-btn"
                                onClick={handleImport}
                                disabled={!file || importing}
                            >
                                {importing ? 'Importing…' : 'Import'}
                            </button>
                        </div>
                    </>
                )}

                {summary && (
                    <>
                        <p className="crew-import-summary">
                            {summary.created_contacts} added, {summary.matched_contacts} matched existing,
                            {' '}{summary.assignments_created} assigned
                        </p>
                        {summary.skipped?.length > 0 && (
                            <ul className="crew-import-skipped">
                                {summary.skipped.map((s, i) => (
                                    <li key={i}>
                                        {s.line ? `line ${s.line}: ` : ''}{s.reason}
                                    </li>
                                ))}
                            </ul>
                        )}
                        <div className="contact-form-actions">
                            <button type="button" className="production-new-btn" onClick={onDone}>
                                Done
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
