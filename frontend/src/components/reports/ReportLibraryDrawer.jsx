import React, { useState } from 'react';
import { X, Search, Download, Share2, Trash2 } from 'lucide-react';
import { Badge } from '../ui';
import { reportIcon } from './reportIcons';
import './ReportLibraryDrawer.css';

const ReportLibraryDrawer = ({ open, reports, onClose, onReopen, onDownload, onShare, onDelete }) => {
    const [query, setQuery] = useState('');

    const filtered = (reports || []).filter((r) => {
        const q = query.trim().toLowerCase();
        if (!q) return true;
        return (r.title || '').toLowerCase().includes(q) || (r.report_type || '').toLowerCase().includes(q);
    });

    return (
        <>
            {open && <div className="library-backdrop" onClick={onClose} />}
            <aside className={`library-drawer ${open ? 'open' : ''}`} aria-hidden={!open} {...(!open ? { inert: '' } : {})}>
                <div className="library-header">
                    <strong>Library · past reports</strong>
                    <button className="library-close" onClick={onClose} title="Close"><X size={18} /></button>
                </div>

                <div className="library-search">
                    <Search size={14} />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search reports…"
                    />
                </div>

                <div className="library-list">
                    {filtered.length === 0 ? (
                        <p className="library-empty">No reports yet.</p>
                    ) : filtered.map((report) => {
                        const Icon = reportIcon(report.report_type);
                        const date = report.generated_at ? new Date(report.generated_at).toLocaleDateString() : '';
                        return (
                            <div key={report.id} className="library-item">
                                <button className="library-item-main" onClick={() => onReopen(report)} title="Reopen to edit">
                                    <Icon size={18} />
                                    <span className="library-item-text">
                                        <span className="library-item-title">
                                            {report.title}
                                            {report.is_public && <Badge variant="success" icon={Share2}>Shared</Badge>}
                                        </span>
                                        <span className="library-item-meta">{date} · click to reopen &amp; edit</span>
                                    </span>
                                </button>
                                <div className="library-item-actions">
                                    <button className="lib-action" onClick={() => onDownload(report)} title="Download"><Download size={15} /></button>
                                    <button className="lib-action" onClick={() => onShare(report)} title="Share"><Share2 size={15} /></button>
                                    <button className="lib-action danger" onClick={() => onDelete(report)} title="Delete"><Trash2 size={15} /></button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </aside>
        </>
    );
};

export default ReportLibraryDrawer;
