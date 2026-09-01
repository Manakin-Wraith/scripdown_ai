"""
Production membership + invite lifecycle (build-sequence step 2b).

A production_members row grants production-level access only (crew now;
locations / schedule / call sheets / DPR later). It grants ZERO script
access. Enforcement is app-layer via middleware/production_authz.py; this
module is the data logic the routes call.
"""
import secrets
from datetime import datetime, timedelta, timezone

from db.supabase_client import get_supabase_admin
from middleware.production_authz import ROLE_RANK, CAPABILITIES
from services.production_service import _get_production
from services.entitlement_service import get_entitlement

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


def _generate_token():
    return secrets.token_urlsafe(32)


def _owner_id(supabase, production_id):
    prod = _get_production(supabase, production_id)
    return prod.get('owner_id') if prod else None


def _production_title(supabase, production_id):
    prod = _get_production(supabase, production_id)
    return (prod or {}).get('title') or 'a production'


def add_member(production_id, actor_uid, actor_access, fields):
    supabase = get_supabase_admin()
    email = (fields.get('email') or '').strip().lower()
    role = fields.get('role')
    if not email:
        return ('error', 'bad_email', 400)
    if role not in ROLE_PRESETS:
        return ('error', 'bad_role', 400)

    flags = apply_role_preset(role, fields)
    if not rank_ok(actor_access, role, flags):
        return ('error', 'rank_denied', 403)

    # Entitlement gate — keyed to the PRODUCTION OWNER, never the acting caller.
    ent = get_entitlement(_owner_id(supabase, production_id))
    if not ent.get('can_use_teams'):
        return ('error', 'tier_2_required', 403)
    if ent.get('seats_used', 0) >= ent.get('seats_paid', 0):
        return ('error', 'no_seats_available', 402)

    # Existing account?
    prof = (supabase.table('profiles').select('id, email')
            .ilike('email', email).limit(1).execute().data or [])
    if prof:
        target_uid = prof[0]['id']
        dupe = (supabase.table('production_members').select('id')
                .eq('production_id', production_id).eq('user_id', target_uid)
                .limit(1).execute().data or [])
        if dupe:
            return ('error', 'duplicate_member', 409)
        row = supabase.table('production_members').insert({
            'production_id': production_id, 'user_id': target_uid, 'role': role,
            'invited_by': actor_uid, **flags,
        }).execute().data[0]
        _notify_member_added(supabase, production_id, target_uid, role)
        profiles = _profiles_by_id(supabase, {target_uid})
        return {'member': _member_view(row, profiles.get(target_uid))}

    # Unknown email → pending invite
    pending = (supabase.table('production_invites').select('id')
               .eq('production_id', production_id).eq('status', 'pending')
               .ilike('email', email).limit(1).execute().data or [])
    if pending:
        return ('error', 'duplicate_invite', 409)
    expires = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    inv = supabase.table('production_invites').insert({
        'production_id': production_id, 'email': email, 'role': role,
        'token': _generate_token(), 'status': 'pending', 'invited_by': actor_uid,
        'expires_at': expires, **flags,
    }).execute().data[0]
    _send_invite_email(supabase, production_id, inv)
    return {'invite': _invite_view(inv)}


def update_member(production_id, member_id, actor_uid, actor_access, fields):
    supabase = get_supabase_admin()
    row = (supabase.table('production_members').select('*')
           .eq('id', member_id).eq('production_id', production_id)
           .limit(1).execute().data or [])
    if not row:
        return ('error', 'not_found', 404)
    current = row[0]
    new_role = fields.get('role', current['role'])
    if new_role not in ROLE_PRESETS:
        return ('error', 'bad_role', 400)
    # Start from the member's current flags, apply any explicit overrides.
    merged = {c: bool(fields[c]) if c in fields and fields[c] is not None
              else bool(current.get(c)) for c in CAPABILITIES}
    # Guard against the current role AND the new role (+ resulting flags).
    if (not rank_ok(actor_access, current['role'], {})
            or not rank_ok(actor_access, new_role, merged)):
        return ('error', 'rank_denied', 403)
    supabase.table('production_members').update(
        {'role': new_role, **merged}).eq('id', member_id).execute()
    updated = (supabase.table('production_members').select('*')
               .eq('id', member_id).limit(1).execute().data[0])
    profiles = _profiles_by_id(supabase, {updated['user_id']})
    return {'member': _member_view(updated, profiles.get(updated['user_id']))}


def remove_member(production_id, member_id, actor_uid, actor_access):
    supabase = get_supabase_admin()
    row = (supabase.table('production_members').select('*')
           .eq('id', member_id).eq('production_id', production_id)
           .limit(1).execute().data or [])
    if not row:
        return 'ok'  # no-op, mirrors remove_script
    if not rank_ok(actor_access, row[0]['role'], {}):
        return ('error', 'rank_denied', 403)
    supabase.table('production_members').delete().eq('id', member_id).execute()
    return 'ok'


def _notify_member_added(supabase, production_id, target_uid, role):
    title = _production_title(supabase, production_id)
    try:
        supabase.table('notifications').insert({
            'user_id': target_uid,
            'type': 'production_member_added',
            'title': 'Added to a production',
            'message': f'You were added to "{title}" as {role}',
            'data': {'production_id': production_id, 'role': role},
        }).execute()
    except Exception as e:
        print(f"Warning: production member-added notification failed: {e}")
    _maybe_email_member_added(supabase, production_id, target_uid, role, title)


def _maybe_email_member_added(supabase, production_id, target_uid, role, title):
    from services import email_service
    if not email_service.is_configured():
        return
    prof = (supabase.table('profiles').select('email')
            .eq('id', target_uid).limit(1).execute().data or [])
    if not prof or not prof[0].get('email'):
        return
    try:
        email_service.send_production_member_added(
            to_email=prof[0]['email'], inviter_name='A teammate',
            production_title=title, role=role,
            production_url=f"{email_service.APP_URL}/productions/{production_id}")
    except Exception as e:
        print(f"Warning: production member-added email failed: {e}")


def revoke_invite(invite_id):
    get_supabase_admin().table('production_invites').update(
        {'status': 'revoked'}).eq('id', invite_id).execute()
    return 'ok'


def get_invite_by_token(token):
    supabase = get_supabase_admin()
    rows = (supabase.table('production_invites').select('*')
            .eq('token', token).limit(1).execute().data or [])
    if not rows:
        return None
    inv = rows[0]
    prod = _get_production(supabase, inv['production_id'])
    inviter = None
    if inv.get('invited_by'):
        p = (supabase.table('profiles').select('full_name, email')
             .eq('id', inv['invited_by']).limit(1).execute().data or [])
        if p:
            inviter = p[0].get('full_name') or p[0].get('email')
    expired = False
    if inv.get('expires_at'):
        try:
            exp = datetime.fromisoformat(inv['expires_at'].replace('Z', '+00:00'))
            expired = exp < datetime.now(exp.tzinfo)
        except ValueError:
            pass
    return {
        'production_id': inv['production_id'],
        'production_title': (prod or {}).get('title', 'a production'),
        'inviter_name': inviter or 'A teammate',
        'role': inv['role'], 'email': inv['email'],
        'status': inv['status'], 'expired': expired,
    }


def accept_invite(token, user_id, user_email):
    supabase = get_supabase_admin()
    rows = (supabase.table('production_invites').select('*')
            .eq('token', token).limit(1).execute().data or [])
    if not rows:
        return ('error', 'not_found', 404)
    inv = rows[0]
    if (inv['email'] or '').lower() != (user_email or '').lower():
        return ('error', 'email_mismatch', 403)
    if inv['status'] == 'revoked':
        return ('error', 'invite_revoked', 403)
    if inv.get('expires_at'):
        try:
            exp = datetime.fromisoformat(inv['expires_at'].replace('Z', '+00:00'))
            if exp < datetime.now(exp.tzinfo):
                return ('error', 'invite_expired', 403)
        except ValueError:
            pass

    existing = (supabase.table('production_members').select('id')
                .eq('production_id', inv['production_id']).eq('user_id', user_id)
                .limit(1).execute().data or [])
    if existing:
        supabase.table('production_invites').update(
            {'status': 'accepted'}).eq('id', inv['id']).execute()
        return {'production_id': inv['production_id'], 'already_member': True}

    supabase.table('production_members').insert({
        'production_id': inv['production_id'], 'user_id': user_id, 'role': inv['role'],
        'invited_by': inv.get('invited_by'),
        **{c: bool(inv.get(c)) for c in CAPABILITIES},
    }).execute()
    supabase.table('production_invites').update(
        {'status': 'accepted'}).eq('id', inv['id']).execute()
    _notify_invite_accepted(supabase, inv, user_id)
    return {'production_id': inv['production_id'], 'already_member': False}


def _notify_invite_accepted(supabase, inv, user_id):
    if not inv.get('invited_by'):
        return
    prod = _get_production(supabase, inv['production_id'])
    title = (prod or {}).get('title', 'a production')
    try:
        supabase.table('notifications').insert({
            'user_id': inv['invited_by'],
            'type': 'production_invite_accepted',
            'title': 'Invite accepted',
            'message': f'Someone joined "{title}" as {inv["role"]}',
            'data': {'production_id': inv['production_id']},
        }).execute()
    except Exception as e:
        print(f"Warning: production invite-accepted notification failed: {e}")


def _send_invite_email(supabase, production_id, inv):
    from services import email_service
    if not email_service.is_configured():
        return
    title = _production_title(supabase, production_id)
    try:
        email_service.send_production_invite(
            to_email=inv['email'], inviter_name='A teammate',
            production_title=title, role=inv['role'],
            invite_url=f"{email_service.APP_URL}/production-invites/{inv['token']}")
    except Exception as e:
        print(f"Warning: production invite email failed: {e}")
