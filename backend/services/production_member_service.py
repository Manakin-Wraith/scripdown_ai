"""
Production membership + invite lifecycle (build-sequence step 2b).

A production_members row grants production-level access only (crew now;
locations / schedule / call sheets / DPR later). It grants ZERO script
access. Enforcement is app-layer via middleware/production_authz.py; this
module is the data logic the routes call.
"""
from datetime import datetime, timedelta, timezone

from db.supabase_client import get_supabase_admin
from middleware.production_authz import ROLE_RANK, CAPABILITIES

ROLE_PRESETS = {
    'admin':       {c: True for c in CAPABILITIES},
    'coordinator': {'can_view_sensitive': False, 'can_edit_crew': True,
                    'can_manage_members': False, 'can_edit_production': False},
    'viewer':      {c: False for c in CAPABILITIES},
}


def apply_role_preset(role, overrides):
    flags = dict(ROLE_PRESETS[role])
    for c in CAPABILITIES:
        if overrides and c in overrides and overrides[c] is not None:
            flags[c] = bool(overrides[c])
    return flags


def rank_ok(actor_access, target_role, new_flags):
    """The actor may assign `target_role` + `new_flags` only if:
    - actor is owner (unrestricted), OR
    - target_role ranks strictly below the actor's role, AND
    - every flag being granted is one the actor themselves holds.
    """
    if actor_access['role'] == 'owner':
        return True
    if ROLE_RANK[target_role] >= ROLE_RANK[actor_access['role']]:
        return False
    for c in CAPABILITIES:
        if new_flags.get(c) and not actor_access.get(c):
            return False
    return True


def _profiles_by_id(supabase, ids):
    if not ids:
        return {}
    rows = (supabase.table('profiles').select('id, full_name, email')
            .in_('id', list(ids)).execute().data or [])
    return {r['id']: r for r in rows}


def _member_view(row, profile):
    profile = profile or {}
    return {
        'id': row['id'],
        'user_id': row['user_id'],
        'name': profile.get('full_name') or profile.get('email') or 'Unknown',
        'email': profile.get('email'),
        'role': row['role'],
        **{c: bool(row.get(c)) for c in CAPABILITIES},
        'created_at': row.get('created_at'),
    }


def _invite_view(row):
    return {
        'id': row['id'],
        'email': row['email'],
        'role': row['role'],
        **{c: bool(row.get(c)) for c in CAPABILITIES},
        'expires_at': row.get('expires_at'),
        'created_at': row.get('created_at'),
    }


def list_members_and_invites(production_id):
    supabase = get_supabase_admin()
    members = (supabase.table('production_members').select('*')
               .eq('production_id', production_id).execute().data or [])
    profiles = _profiles_by_id(supabase, {m['user_id'] for m in members})
    invites = (supabase.table('production_invites').select('*')
               .eq('production_id', production_id).eq('status', 'pending')
               .execute().data or [])
    return {
        'members': [_member_view(m, profiles.get(m['user_id'])) for m in members],
        'invites': [_invite_view(i) for i in invites],
    }
