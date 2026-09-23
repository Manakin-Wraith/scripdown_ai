// Script-axis roles, mirroring backend middleware/authorization.ROLE_RANK.
// UX only — the backend's require_script_role is the real enforcement.
export const SCRIPT_ROLE_RANK = { viewer: 1, member: 2, admin: 3, owner: 4 };

/** True when the role may edit script content (member and above). */
export const canEditScript = (role) =>
    (SCRIPT_ROLE_RANK[role] || 0) >= SCRIPT_ROLE_RANK.member;
