export const FIELD_TYPES = ['text', 'textarea', 'time', 'link', 'number'];
export const DAY_FIELD_SECTIONS = [['header', 'Header'], ['day_info', 'Day info'], ['notes', 'Notes']];

/** Keys are immutable and generated once: lowercase slug, unique within the list (max 40 chars). */
export function slugKey(label, existingKeys = []) {
    let base = String(label || '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    if (!base) base = 'field';
    if (!/^[a-z]/.test(base)) base = `f_${base}`;
    base = base.slice(0, 36);
    let key = base;
    let n = 2;
    while (existingKeys.includes(key)) {
        key = `${base}_${n}`;
        n += 1;
    }
    return key;
}

export function moveItem(list, index, delta) {
    const target = index + delta;
    if (target < 0 || target >= list.length) return list;
    const next = [...list];
    [next[index], next[target]] = [next[target], next[index]];
    return next;
}

export const updateAt = (list, index, patch) =>
    list.map((item, i) => (i === index ? { ...item, ...patch } : item));

export const removeAt = (list, index) => list.filter((_, i) => i !== index);

/** Messages for errors at or under `prefix` (e.g. `day_fields[3]` matches `day_fields[3].key`). */
export function errorsFor(errors, prefix) {
    return (errors || [])
        .filter((e) => e.path === prefix || e.path.startsWith(`${prefix}.`) || e.path.startsWith(`${prefix}[`))
        .map((e) => e.message);
}

/** Messages attached exactly to `path` (list-level errors such as "built-in fields cannot be removed"). */
export const panelErrors = (errors, path) =>
    (errors || []).filter((e) => e.path === path).map((e) => e.message);

const keysOf = (items) => items.map((i) => i.key);

export const blankDayField = (items) => ({
    key: slugKey('New field', keysOf(items)), label: 'New field', type: 'text',
    section: 'day_info', default: '', sensitive: false, visible: true, builtin: false,
});

export const blankColumn = (items) => ({
    key: slugKey('New column', keysOf(items)), label: 'New column', type: 'text', sensitive: false,
});

export const blankDepartment = (items) => ({
    key: slugKey('New department', keysOf(items)), label: 'New department', default_call: '', as_per: '',
});

export const blankLabelled = (items, valueField) => ({
    key: slugKey('New entry', keysOf(items)), label: 'New entry', [valueField]: '',
});
