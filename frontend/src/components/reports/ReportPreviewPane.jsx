import React from 'react';
import { RefreshCw, FileText } from 'lucide-react';
import { Spinner, Button } from '../ui';
import './ReportPreviewPane.css';

const ReportPreviewPane = ({ html, matchCount, totalCount, loading, error, onRefresh }) => {
    return (
        <div className="report-preview-pane">
            <div className="preview-toolbar">
                <span className="preview-status">
                    {typeof matchCount === 'number' && typeof totalCount === 'number'
                        ? `${matchCount} of ${totalCount} scenes match`
                        : 'Live preview'}
                </span>
                <Button variant="secondary" onClick={onRefresh} disabled={loading}>
                    <RefreshCw size={16} />
                    Update Preview
                </Button>
            </div>

            <div className="preview-surface">
                {loading && (
                    <div className="preview-overlay">
                        <Spinner size={28} />
                        <p>Rendering preview…</p>
                    </div>
                )}

                {!loading && error && (
                    <div className="preview-message error">
                        <p>Couldn't render preview.</p>
                        <p className="preview-message-detail">{error}</p>
                    </div>
                )}

                {!loading && !error && !html && (
                    <div className="preview-message">
                        <FileText size={32} />
                        <p>Configure on the left, then hit <strong>Update Preview</strong>.</p>
                    </div>
                )}

                {!loading && !error && html && (
                    <iframe
                        className="preview-frame"
                        title="Report preview"
                        sandbox=""
                        srcDoc={html}
                    />
                )}
            </div>
        </div>
    );
};

export default ReportPreviewPane;
