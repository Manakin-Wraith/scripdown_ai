import { Plus } from 'lucide-react';
import PageHeader from '../layout/PageHeader';
import './DirectoryShell.css';

/**
 * Two-column master/detail layout for the account-level directory pages
 * (Contacts, Locations). The left column holds the page header, a "New"
 * link, a toolbar (search / filters) and the list; the right column is the
 * detail pane, driven by nested routes.
 *
 * Props:
 *   title, subtitle   - page header text
 *   newLabel, onNew   - "New" button label + click handler (guarded by the page)
 *   toolbar           - node rendered above the list (search, filters)
 *   list              - the list node
 *   error             - optional error string shown above the list
 *   hasSelection      - true when a detail route is active; on narrow
 *                       viewports the list hides and the pane fills the screen
 *   children          - the detail pane (<Outlet />)
 */
export default function DirectoryShell({
    title, subtitle, newLabel, onNew, toolbar, list, error,
    hasSelection = false, children,
}) {
    return (
        <div className={`directory-shell${hasSelection ? ' has-selection' : ''}`}>
            <aside className="directory-list-col">
                <PageHeader
                    title={title}
                    subtitle={subtitle}
                    actions={onNew ? (
                        <button type="button" className="production-new-btn" onClick={onNew}>
                            <Plus size={16} /> {newLabel}
                        </button>
                    ) : null}
                />
                {toolbar}
                {error && <p className="production-page-error">{error}</p>}
                <div className="directory-list-scroll">{list}</div>
            </aside>
            <section className="directory-detail-col">{children}</section>
        </div>
    );
}
