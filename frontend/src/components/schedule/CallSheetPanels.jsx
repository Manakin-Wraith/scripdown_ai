const MEALS = [['craft', 'Craft'], ['breakfast', 'Breakfast'], ['lunch', 'Lunch'], ['dinner', 'Dinner']];
const GROUPS = [['crew', 'Crew'], ['cast', 'Cast'], ['add_crew', 'Add. crew'], ['extras', 'Extras']];

const toNull = (raw) => (raw === '' ? null : raw);

/** Uncontrolled input that commits on blur, only when the value actually changed. */
export function TypedInput({ type, value, onCommit, disabled, placeholder }) {
    const initial = value ?? '';
    const commit = (e) => {
        if (e.target.value !== String(initial)) onCommit(e.target.value);
    };
    if (type === 'textarea') {
        return <textarea defaultValue={initial} disabled={disabled} placeholder={placeholder} onBlur={commit} />;
    }
    const inputType = type === 'time' ? 'time' : type === 'number' ? 'number' : 'text';
    return <input type={inputType} defaultValue={initial} disabled={disabled} placeholder={placeholder} onBlur={commit} />;
}

/** Day-info fields for one template section (header | day_info | notes). */
export function DayFieldsPanel({ callSheet, section, onPatch }) {
    const canSee = !!callSheet.can_view_sensitive;
    const fields = callSheet.template.day_fields.filter(
        (f) => f.section === section && f.visible && (canSee || !f.sensitive));
    const valueOf = (f) => (f.builtin ? callSheet[f.key] : (callSheet.custom_values || {})[f.key]);
    const commit = (f, raw) => {
        const value = toNull(raw);
        onPatch(f.builtin ? { [f.key]: value } : { custom_values: { [f.key]: value } });
    };
    return fields.map((f) => (
        <label key={`${f.key}:${valueOf(f) ?? ''}`} className="cs-field">
            <span>{f.label}</span>
            <TypedInput type={f.type} value={valueOf(f) ?? f.default ?? ''} onCommit={(raw) => commit(f, raw)} />
        </label>
    ));
}

export function KeyCrewPanel({ callSheet, onPatch }) {
    const overrides = callSheet.header_values || {};
    return (callSheet.template.key_crew || []).map((k) => (
        <label key={`${k.key}:${overrides[k.key] ?? ''}`} className="cs-field">
            <span>{k.label}</span>
            <TypedInput type="text" value={overrides[k.key] ?? k.value}
                        onCommit={(raw) => onPatch({ header_values: { [k.key]: toNull(raw) } })} />
        </label>
    ));
}

/** Template blocks: shown with the template text; editing stores a day-only override. */
export function BlocksPanel({ callSheet, onPatch }) {
    const overrides = callSheet.block_overrides || {};
    return (callSheet.template.blocks || []).map((b) => {
        const overridden = overrides[b.key] !== undefined;
        return (
            <label key={`${b.key}:${overrides[b.key] ?? ''}`} className="cs-field">
                <span>{b.label}{overridden && <em className="cs-overridden"> (edited for this day)</em>}</span>
                <TypedInput type="textarea" value={overrides[b.key] ?? b.body}
                            onCommit={(raw) => onPatch({
                                // Identical to the template text = drop the override.
                                block_overrides: { [b.key]: raw === b.body ? null : raw },
                            })} />
            </label>
        );
    });
}

export function DeptCallsPanel({ callSheet, onPatch }) {
    const overrides = callSheet.dept_overrides || {};
    const depts = callSheet.template.departments || [];
    if (!depts.length) return <p className="cs-note">No departments in the template yet.</p>;
    return (
        <table className="cs-scene-table">
            <thead><tr><th>Department</th><th>Call</th><th>As per</th></tr></thead>
            <tbody>
                {depts.map((d) => {
                    const ov = overrides[d.key] || {};
                    return (
                        <tr key={`${d.key}:${ov.call ?? ''}:${ov.as_per ?? ''}`}>
                            <td>{d.label}</td>
                            <td><TypedInput type="time" value={ov.call ?? d.default_call}
                                            onCommit={(raw) => onPatch({ dept_overrides: { [d.key]: { call: toNull(raw) } } })} /></td>
                            <td><TypedInput type="text" value={ov.as_per ?? d.as_per}
                                            onCommit={(raw) => onPatch({ dept_overrides: { [d.key]: { as_per: toNull(raw) } } })} /></td>
                        </tr>
                    );
                })}
            </tbody>
        </table>
    );
}

/** Per-meal headcount grid, prefilled from roster counts (catering_effective). */
export function CateringPanel({ callSheet, onPatch }) {
    const eff = callSheet.catering_effective || {};
    return (
        <table className="cs-scene-table cs-catering-table">
            <thead><tr><th></th>{MEALS.map(([m, label]) => <th key={m}>{label}</th>)}</tr></thead>
            <tbody>
                {GROUPS.map(([g, glabel]) => (
                    <tr key={g}>
                        <td>{glabel}</td>
                        {MEALS.map(([m]) => (
                            <td key={`${m}:${eff[m]?.[g] ?? 0}`}>
                                <TypedInput type="number" value={eff[m]?.[g] ?? 0}
                                            onCommit={(raw) => onPatch(
                                                { catering: { [m]: { [g]: raw === '' ? null : Number(raw) } } },
                                                { reload: true })} />
                            </td>
                        ))}
                    </tr>
                ))}
            </tbody>
        </table>
    );
}

/** Inline inputs for a table's custom columns. Sensitive columns are hidden from viewers who can't see them. */
export function ColumnInputs({ columns, values, onCommit, canSeeSensitive }) {
    const visible = (columns || []).filter((c) => canSeeSensitive || !c.sensitive);
    if (!visible.length) return null;
    return (
        <span className="cs-inline-cols">
            {visible.map((c) => (
                <label key={`${c.key}:${values?.[c.key] ?? ''}`} className="cs-inline-col">
                    <small>{c.label}</small>
                    <TypedInput type={c.type} value={values?.[c.key] ?? ''}
                                onCommit={(raw) => onCommit(c.key, toNull(raw))} />
                </label>
            ))}
        </span>
    );
}
