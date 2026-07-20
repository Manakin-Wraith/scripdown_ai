"""
Script authorization for SlateOne.

Authentication (who the user is) lives in middleware/auth.py.
This module answers: may THIS user act on THIS script, at what role?
Enforcement is app-layer because the backend uses the service-role key.
"""
import logging
from db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

ROLE_RANK = {'viewer': 1, 'member': 2, 'admin': 3, 'owner': 4}

# Sentinel distinguishing "script does not exist" (404) from "no access" (403).
SCRIPT_NOT_FOUND = object()


def get_script_role(script_id, user_id):
    """Return the caller's effective role on a script.

    Returns:
        'owner'                 if scripts.user_id == user_id
        a script_members.role   if the user is a member
        None                    if the script exists but the user has no access
        SCRIPT_NOT_FOUND        if the script does not exist
    """
    if not script_id or not user_id:
        return None

    supabase = get_supabase_client()
    script = (supabase.table('scripts')
              .select('user_id').eq('id', script_id).limit(1).execute())
    if not script.data:
        return SCRIPT_NOT_FOUND

    owner_id = script.data[0].get('user_id')
    if owner_id == user_id:
        return 'owner'

    member = (supabase.table('script_members')
              .select('role').eq('script_id', script_id)
              .eq('user_id', user_id).limit(1).execute())
    if member.data:
        return member.data[0].get('role')

    return None


def _lookup_script_id(table, id_value, id_col='id', script_col='script_id'):
    """Fetch a single row by id and return its script_id (or None)."""
    if not id_value:
        return None
    supabase = get_supabase_client()
    res = (supabase.table(table)
           .select(script_col).eq(id_col, id_value).limit(1).execute())
    return res.data[0].get(script_col) if res.data else None


def from_script(kwargs):
    return kwargs.get('script_id')


def from_scene(kwargs):
    return _lookup_script_id('scenes', kwargs.get('scene_id'))


def from_note(kwargs):
    return _lookup_script_id('department_notes', kwargs.get('note_id'))


def from_item(kwargs):
    return _lookup_script_id('department_items', kwargs.get('item_id'))


def from_schedule(kwargs):
    return _lookup_script_id('shooting_schedules', kwargs.get('schedule_id'))


def from_report(kwargs):
    return _lookup_script_id('reports', kwargs.get('report_id'))


def from_preset(kwargs):
    return _lookup_script_id('report_filter_presets', kwargs.get('preset_id'))


def from_day(kwargs):
    """Two-hop: shooting_days.schedule_id -> shooting_schedules.script_id."""
    schedule_id = _lookup_script_id('shooting_days', kwargs.get('day_id'),
                                    script_col='schedule_id')
    if not schedule_id:
        return None
    return _lookup_script_id('shooting_schedules', schedule_id)


from functools import wraps
from flask import g, jsonify
from middleware.auth import get_user_id


def require_script_role(min_role, resolver=from_script):
    """Require the caller to hold at least `min_role` on the target script.

    Stack BELOW @require_auth. Resolves the script via `resolver(kwargs)`,
    then compares the caller's effective role against `min_role`.
    404 if the script/resource is absent; 403 if the role is insufficient.
    """
    if min_role not in ROLE_RANK:
        raise ValueError(f"Unknown min_role: {min_role}")

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = get_user_id()
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401

            script_id = resolver(kwargs)
            if not script_id:
                return jsonify({'error': 'Not found'}), 404

            role = get_script_role(script_id, user_id)
            if role is SCRIPT_NOT_FOUND:
                return jsonify({'error': 'Not found'}), 404
            if role is None or ROLE_RANK[role] < ROLE_RANK[min_role]:
                return jsonify({'error': 'Insufficient permissions'}), 403

            g.script_role = role
            g.resolved_script_id = script_id
            return f(*args, **kwargs)
        return wrapper
    return decorator
