/**
 * A label / value pair in a directory detail pane, matching the spacing of
 * the edit form's fields. Renders nothing when `value` is empty.
 */
export function DetailRow({ label, value, capitalize }) {
    if (value === null || value === undefined || value === '') return null;
    return (
        <div className="directory-detail-row">
            <span className="directory-detail-label">{label}</span>
            <span className={`directory-detail-value${capitalize ? ' is-capitalize' : ''}`}>{value}</span>
        </div>
    );
}

/** A titled section (Used on, Reference photos, …) below the field list. */
export function DetailSection({ title, children }) {
    return (
        <section className="directory-detail-section">
            <h4 className="directory-detail-heading">{title}</h4>
            {children}
        </section>
    );
}
