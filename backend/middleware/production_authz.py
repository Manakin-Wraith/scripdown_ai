"""
Production-axis authorization for SlateOne.

Parallel to middleware/authorization.py (the script axis) — deliberately a
separate module because the production axis is independent: a production
member gets zero script access and vice versa.

Answers: may THIS user act on THIS production, at what role, with which
capability flags? Enforcement is app-layer (the backend uses the
service-role key).
"""
import logging
from functools import wraps

from flask import g, jsonify

from db.supabase_client import get_supabase_admin
from middleware.auth import get_user_id

logger = logging.getLogger(__name__)

ROLE_RANK = {'viewer': 1, 'coordinator': 2, 'admin': 3, 'owner': 4}

CAPABILITIES = (
    'can_view_sensitive', 'can_edit_crew', 'can_manage_members', 'can_edit_production',
)

# Sentinel distinguishing "production does not exist" (404) from "no access" (403).
PRODUCTION_NOT_FOUND = object()


def _get_production_owner(production_id):
    if not production_id:
        return PRODUCTION_NOT_FOUND
    res = (get_supabase_admin().table('productions')
           .select('owner_id').eq('id', production_id).limit(1).execute())
    if not res.data:
        return PRODUCTION_NOT_FOUND
    return res.data[0].get('owner_id')


def _get_member_row(production_id, user_id):
    res = (get_supabase_admin().table('production_members')
           .select('*').eq('production_id', production_id)
           .eq('user_id', user_id).limit(1).execute())
    return res.data[0] if res.data else None


def get_production_role(production_id, user_id):
    """'owner' | 'admin' | 'coordinator' | 'viewer' | None | PRODUCTION_NOT_FOUND"""
    if not production_id or not user_id:
        return None
    owner_id = _get_production_owner(production_id)
    if owner_id is PRODUCTION_NOT_FOUND:
        return PRODUCTION_NOT_FOUND
    if owner_id == user_id:
        return 'owner'
    row = _get_member_row(production_id, user_id)
    return row['role'] if row else None


def get_production_access(production_id, user_id):
    """dict(role + 4 capability booleans) | None | PRODUCTION_NOT_FOUND.

    Owner short-circuits to all-true. A member returns its row's stored
    flags. A non-member returns None.
    """
    if not production_id or not user_id:
        return None
    owner_id = _get_production_owner(production_id)
    if owner_id is PRODUCTION_NOT_FOUND:
        return PRODUCTION_NOT_FOUND
    if owner_id == user_id:
        return {'role': 'owner', **{c: True for c in CAPABILITIES}}
    row = _get_member_row(production_id, user_id)
    if not row:
        return None
    return {'role': row['role'], **{c: bool(row.get(c)) for c in CAPABILITIES}}


def _lookup_production_id(table, id_value, id_col='id'):
    if not id_value:
        return None
    res = (get_supabase_admin().table(table)
           .select('production_id').eq(id_col, id_value).limit(1).execute())
    return res.data[0].get('production_id') if res.data else None


def from_production_id(kwargs):
    return kwargs.get('production_id')


def from_crew_id(kwargs):
    return _lookup_production_id('production_crew', kwargs.get('crew_id'))


def from_member_id(kwargs):
    return _lookup_production_id('production_members', kwargs.get('member_id'))


def from_production_invite_id(kwargs):
    return _lookup_production_id('production_invites', kwargs.get('invite_id'))


def require_production_role(min_role=None, capability=None, resolver=from_production_id):
    """Require the caller to hold a production role (and/or a capability flag).

    Stack BELOW @require_auth. Resolves the production via resolver(kwargs).
    404 if the production/resource is absent; 403 if the role rank is below
    `min_role` or the named `capability` flag is not True. On success sets
    g.production_access (the full dict) and g.resolved_production_id.
    """
    if min_role is not None and min_role not in ROLE_RANK:
        raise ValueError(f"Unknown min_role: {min_role}")
    if capability is not None and capability not in CAPABILITIES:
        raise ValueError(f"Unknown capability: {capability}")

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = get_user_id()
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401

            production_id = resolver(kwargs)
            if not production_id:
                return jsonify({'error': 'Not found'}), 404

            access = get_production_access(production_id, user_id)
            if access is PRODUCTION_NOT_FOUND:
                return jsonify({'error': 'Not found'}), 404
            if access is None:
                return jsonify({'error': 'Insufficient permissions'}), 403
            if min_role is not None and ROLE_RANK[access['role']] < ROLE_RANK[min_role]:
                return jsonify({'error': 'Insufficient permissions'}), 403
            if capability is not None and not access.get(capability):
                return jsonify({'error': 'Insufficient permissions'}), 403

            g.production_access = access
            g.resolved_production_id = production_id
            return f(*args, **kwargs)

        if min_role is not None:
            wrapper._authz_min_role = min_role
        if capability is not None:
            wrapper._authz_capability = capability
        return wrapper
    return decorator
