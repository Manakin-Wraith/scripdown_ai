import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { 
    FileText, Download, Printer, Clock, AlertCircle, 
    Users, MapPin, Package, Film, Loader
} from 'lucide-react';
import { 
    getSharedReport, 
    getSharedReportPdfUrl, 
    getSharedReportPrintUrl 
} from '../../services/apiService';
import './SharedReportView.css';

const SharedReportView = () => {
    const { shareToken } = useParams();
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchReport = async () => {
            try {
                setLoading(true);
                const res = await getSharedReport(shareToken);
                if (res.success) {
                    setReport(res.report);
                } else {
                    setError(res.error || 'Report not found');
                }
            } catch (err) {
                setError('This report link has expired or is invalid');
            } finally {
                setLoading(false);
            }
        };
        
        fetchReport();
    }, [shareToken]);

    const handlePrint = () => {
        window.open(getSharedReportPrintUrl(shareToken), '_blank');
    };

    const handleDownload = () => {
        window.open(getSharedReportPdfUrl(shareToken), '_blank');
    };

    if (loading) {
        return (
            <div className="shared-report-loading">
                <Loader className="spin" size={32} />
                <p>Loading report...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="shared-report-error">
                <AlertCircle size={48} />
                <h2>Report Not Available</h2>
                <p>{error}</p>
            </div>
        );
    }

    const data = report.data_snapshot || {};
    const script = data.script || {};
    const summary = data.summary || {};

    return (
        <div className="shared-report">
            {/* Header */}
            <div className="shared-report-header">
                <div className="header-info">
                    <h1>{report.title}</h1>
                    <div className="script-info">
                        <span>{script.title}</span>
                        {script.writer && <span>by {script.writer}</span>}
                    </div>
                    <div className="report-meta">
                        <Clock size={14} />
                        <span>Generated {new Date(report.generated_at).toLocaleDateString()}</span>
                    </div>
                </div>
                <div className="header-actions">
                    <button className="action-btn" onClick={handlePrint}>
                        <Printer size={16} />
                        Print
                    </button>
                    <button className="action-btn primary" onClick={handleDownload}>
                        <Download size={16} />
                        Download PDF
                    </button>
                </div>
            </div>

            {/* Summary Stats */}
            <div className="report-summary">
                <div className="summary-stat">
                    <Film size={20} />
                    <span className="stat-value">{summary.total_scenes || 0}</span>
                    <span className="stat-label">Scenes</span>
                </div>
                <div className="summary-stat">
                    <Users size={20} />
                    <span className="stat-value">{summary.total_characters || 0}</span>
                    <span className="stat-label">Characters</span>
                </div>
                <div className="summary-stat">
                    <MapPin size={20} />
                    <span className="stat-value">{summary.total_locations || 0}</span>
                    <span className="stat-label">Locations</span>
                </div>
                <div className="summary-stat">
                    <Package size={20} />
                    <span className="stat-value">{summary.total_props || 0}</span>
                    <span className="stat-label">Props</span>
                </div>
            </div>

            {/* Report Content */}
            <div className="report-content">
                {report.report_type === 'scene_breakdown' && (
                    <SceneBreakdownTable scenes={data.scenes || []} />
                )}
                
                {report.report_type === 'day_out_of_days' && (
                    <DayOutOfDaysTable characters={data.characters || {}} />
                )}
                
                {report.report_type === 'location' && (
                    <LocationTable locations={data.locations || {}} />
                )}
                
                {report.report_type === 'props' && (
                    <PropsTable props={data.props || {}} />
                )}
                
                {report.report_type === 'one_liner' && (
                    <OneLinerTable scenes={data.scenes || []} />
                )}
                
                {report.report_type === 'full_breakdown' && (
                    <>
                        <h2>Scene Breakdown</h2>
                        <SceneBreakdownTable scenes={data.scenes || []} />
                        <h2>Day Out of Days</h2>
                        <DayOutOfDaysTable characters={data.characters || {}} />
                        <h2>Locations</h2>
                        <LocationTable locations={data.locations || {}} />
                    </>
                )}
            </div>

            {/* Footer */}
            <div className="shared-report-footer">
                <p>Generated by ScripDown AI</p>
            </div>
        </div>
    );
};

// Sub-components for different report types
const SceneBreakdownTable = ({ scenes }) => (
    <table className="report-table">
        <thead>
            <tr>
                <th>#</th>
                <th>I/E</th>
                <th>Setting</th>
                <th>D/N</th>
                <th>Characters</th>
                <th>Props</th>
                <th>Page</th>
            </tr>
        </thead>
        <tbody>
            {scenes.map(scene => (
                <tr key={scene.id || scene.scene_id}>
                    <td>{scene.scene_number}</td>
                    <td>{scene.int_ext}</td>
                    <td>{scene.setting}</td>
                    <td>{scene.time_of_day}</td>
                    <td>{(scene.characters || []).slice(0, 5).join(', ')}</td>
                    <td>{(scene.props || []).slice(0, 3).join(', ')}</td>
                    <td>{scene.page_start || '-'}</td>
                </tr>
            ))}
        </tbody>
    </table>
);

const DayOutOfDaysTable = ({ characters }) => (
    <table className="report-table">
        <thead>
            <tr>
                <th>Character</th>
                <th>Scenes</th>
                <th>Scene Numbers</th>
            </tr>
        </thead>
        <tbody>
            {Object.entries(characters)
                .sort((a, b) => b[1].count - a[1].count)
                .map(([name, info]) => (
                    <tr key={name}>
                        <td><strong>{name}</strong></td>
                        <td>{info.count}</td>
                        <td>{info.scenes.slice(0, 10).join(', ')}{info.scenes.length > 10 ? '...' : ''}</td>
                    </tr>
                ))
            }
        </tbody>
    </table>
);

const LocationTable = ({ locations }) => (
    <table className="report-table">
        <thead>
            <tr>
                <th>Location</th>
                <th>INT/EXT</th>
                <th>D/N</th>
                <th>Scenes</th>
            </tr>
        </thead>
        <tbody>
            {Object.entries(locations)
                .sort((a, b) => b[1].count - a[1].count)
                .map(([name, info]) => (
                    <tr key={name}>
                        <td><strong>{name}</strong></td>
                        <td>{(info.int_ext || []).join('/')}</td>
                        <td>{(info.time_of_day || []).join('/')}</td>
                        <td>{info.count}</td>
                    </tr>
                ))
            }
        </tbody>
    </table>
);

const PropsTable = ({ props }) => (
    <table className="report-table">
        <thead>
            <tr>
                <th>Prop</th>
                <th>Appearances</th>
                <th>Scenes</th>
            </tr>
        </thead>
        <tbody>
            {Object.entries(props)
                .sort((a, b) => b[1].count - a[1].count)
                .map(([name, info]) => (
                    <tr key={name}>
                        <td><strong>{name}</strong></td>
                        <td>{info.count}</td>
                        <td>{info.scenes.join(', ')}</td>
                    </tr>
                ))
            }
        </tbody>
    </table>
);

const OneLinerTable = ({ scenes }) => (
    <table className="report-table one-liner">
        <thead>
            <tr>
                <th>#</th>
                <th>I/E</th>
                <th>Setting</th>
                <th>D/N</th>
                <th>Cast</th>
                <th>Pg</th>
            </tr>
        </thead>
        <tbody>
            {scenes.map(scene => {
                const chars = scene.characters || [];
                const charDisplay = chars.slice(0, 3).join(', ');
                const more = chars.length > 3 ? ` +${chars.length - 3}` : '';
                
                return (
                    <tr key={scene.id || scene.scene_id}>
                        <td>{scene.scene_number}</td>
                        <td>{scene.int_ext}</td>
                        <td>{scene.setting}</td>
                        <td>{scene.time_of_day}</td>
                        <td>{charDisplay}{more}</td>
                        <td>{scene.page_start || '-'}</td>
                    </tr>
                );
            })}
        </tbody>
    </table>
);

export default SharedReportView;
