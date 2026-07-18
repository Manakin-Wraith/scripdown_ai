// Carries an in-progress team invite across the PayFast checkout redirect,
// which leaves and re-enters the SPA (so React state alone can't survive it).
const STORAGE_KEY = 'slateone_pending_seat_invite_draft';

export function stashPendingSeatInviteDraft({ scriptId, email, departmentCode, role }) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ scriptId, email, departmentCode, role }));
}

export function readPendingSeatInviteDraft() {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

export function clearPendingSeatInviteDraft() {
    sessionStorage.removeItem(STORAGE_KEY);
}
