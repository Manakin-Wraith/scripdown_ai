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
