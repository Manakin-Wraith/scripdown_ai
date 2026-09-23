"""
Script authorization for SlateOne.

Authentication (who the user is) lives in middleware/auth.py.
This module answers: may THIS user act on THIS script, at what role?
Enforcement is app-layer because the backend uses the service-role key.
"""
import logging
from db.supabase_client import get_supabase_admin
from middleware.production_authz import SCRIPT_ACCESS_TO_ROLE

logger = logging.getLogger(__name__)

ROLE_RANK = {'viewer': 1, 'member': 2, 'admin': 3, 'owner': 4}

# Sentinel distinguishing "script does not exist" (404) from "no access" (403).
SCRIPT_NOT_FOUND = object()


def get_script_role(script_id, user_id):
    """Return the caller's effective role on a script.

    Sources, highest role wins:
      - scripts.user_id == user_id                      → 'owner'
      - a script_members row                            → its role
      - scripts.production_id → production_members.script_access
                                                        → 'member' (edit) / 'viewer' (view)

    Returns a role string, None (exists, no access), or SCRIPT_NOT_FOUND.
    """
    if not script_id or not user_id:
        return None

    supabase = get_supabase_admin()
    script = (supabase.table('scripts')
              .select('user_id, production_id').eq('id', script_id).limit(1).execute())
    if not script.data:
        return SCRIPT_NOT_FOUND

    row = script.data[0]
    if row.get('user_id') == user_id:
        return 'owner'

    member = (supabase.table('script_members')
              .select('role').eq('script_id', script_id)
              .eq('user_id', user_id).limit(1).execute())
    direct = member.data[0].get('role') if member.data else None
    derived = production_derived_role(supabase, row.get('production_id'), user_id)
    return _higher_role(direct, derived)


def _higher_role(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return a if ROLE_RANK.get(a, 0) >= ROLE_RANK.get(b, 0) else b


def production_derived_role(client, production_id, user_id):
    """Script role granted by production membership, or None."""
    if not production_id or not user_id:
        return None
    rows = (client.table('production_members').select('script_access')
            .eq('production_id', production_id).eq('user_id', user_id)
            .limit(1).execute().data or [])
    if not rows:
        return None
    return SCRIPT_ACCESS_TO_ROLE.get(rows[0].get('script_access'))


def production_script_roles(client, user_id):
    """{script_id: role} for scripts the user reaches only through production
    membership (script_access view/edit). Excludes scripts they own.

    `client` is passed in so route modules with their own module-level
    Supabase client (supabase_routes.supabase) can reuse it.
    """
    if not user_id:
        return {}
    rows = (client.table('production_members').select('production_id, script_access')
            .eq('user_id', user_id).execute().data or [])
    access_by_prod = {r['production_id']: r.get('script_access') for r in rows
                      if SCRIPT_ACCESS_TO_ROLE.get(r.get('script_access'))}
    if not access_by_prod:
        return {}
    scripts = (client.table('scripts').select('id, user_id, production_id')
               .in_('production_id', list(access_by_prod)).execute().data or [])
    return {s['id']: SCRIPT_ACCESS_TO_ROLE[access_by_prod[s['production_id']]]
            for s in scripts if s.get('user_id') != user_id}


def _lookup_script_id(table, id_value, id_col='id', script_col='script_id'):
    """Fetch a single row by id and return its script_id (or None)."""
    if not id_value:
        return None
    supabase = get_supabase_admin()
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


def from_move_day(kwargs):
    """Two-hop resolver for the move route, which uses `from_day_id` instead of `day_id`."""
    schedule_id = _lookup_script_id('shooting_days', kwargs.get('from_day_id'),
                                    script_col='schedule_id')
    if not schedule_id:
        return None
    return _lookup_script_id('shooting_schedules', schedule_id)


def from_casting(kwargs):
    return _lookup_script_id('casting', kwargs.get('casting_id'))


def from_casting_group(kwargs):
    return _lookup_script_id('casting_groups', kwargs.get('group_id'))


def from_casting_unavailability(kwargs):
    """Two-hop: casting_unavailability.casting_id -> casting.script_id."""
    casting_id = _lookup_script_id('casting_unavailability', kwargs.get('unavail_id'),
                                   script_col='casting_id')
    if not casting_id:
        return None
    return _lookup_script_id('casting', casting_id)


def from_casting_photo(kwargs):
    """Two-hop: casting_photos.casting_id -> casting.script_id."""
    casting_id = _lookup_script_id('casting_photos', kwargs.get('photo_id'),
                                   script_col='casting_id')
    if not casting_id:
        return None
    return _lookup_script_id('casting', casting_id)


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
        wrapper._authz_min_role = min_role  # introspection marker for tests
        return wrapper
    return decorator
