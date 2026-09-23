"""
Moving a script's own team (script_members / script_invites) into a
production when the script is attached, and back out on detach.

Spec: docs/superpowers/specs/2026-09-23-production-script-access-design.md

Every write is idempotent (select-then-insert, raise-only updates,
pending-only revokes) and script_members rows are deleted LAST, so a retry
after a partial failure converges. A leftover direct row is harmless:
get_script_role takes the higher of direct and production-derived roles.

Moving deliberately bypasses the seat and Team-tier gates in
production_member_service.add_member: it relocates people who are already
counted (spec decision D3).
"""
from datetime import datetime, timedelta, timezone

from db.supabase_client import get_supabase_admin
from middleware.production_authz import (
    SCRIPT_ACCESS_RANK, SCRIPT_ACCESS_TO_ROLE, SCRIPT_ROLE_TO_ACCESS,
)
import services.production_member_service as pms

# script_members.department_code for members kept on detach; production
# members carry no department (spec decision D2).
KEPT_DEPARTMENT_CODE = 'production'


def _is_live(invite):
    exp = invite.get('expires_at')
    if not exp:
        return True
    try:
        return datetime.fromisoformat(exp.replace('Z', '+00:00')) > datetime.now(timezone.utc)
    except ValueError:
        return True


def _raise_access(current, mapped):
    current = current or 'none'
    return mapped if SCRIPT_ACCESS_RANK[mapped] > SCRIPT_ACCESS_RANK.get(current, 0) else current


def load_script_team(script_id):
    supabase = get_supabase_admin()
    members = (supabase.table('script_members').select('*')
               .eq('script_id', script_id).execute().data or [])
    pending = (supabase.table('script_invites').select('*')
               .eq('script_id', script_id).eq('status', 'pending').execute().data or [])
    live = [i for i in pending if _is_live(i)]
    expired = [i for i in pending if not _is_live(i)]
    return members, live, expired


def describe_script_team(members, invites):
    profiles = pms._profiles_by_id(get_supabase_admin(), {m['user_id'] for m in members})
    out_members = []
    for m in members:
        p = profiles.get(m['user_id']) or {}
        out_members.append({
            'user_id': m['user_id'],
            'name': p.get('full_name') or p.get('email') or 'Unknown',
            'email': p.get('email'),
            'role': m.get('role'),
        })
    return {
        'members': out_members,
        'invites': [{'email': i.get('email'), 'role': i.get('role')} for i in invites],
    }


def _revoke_script_invite(supabase, invite_id):
    (supabase.table('script_invites').update({'status': 'revoked'})
     .eq('id', invite_id).eq('status', 'pending').execute())


def move_script_team_to_production(production_id, script_id, actor_uid):
    supabase = get_supabase_admin()
    members, live, expired = load_script_team(script_id)
    owner_id = pms._owner_id(supabase, production_id)
    viewer_flags = pms.apply_role_preset('viewer', None)

    moved_members = 0
    for m in members:
        uid = m['user_id']
        if uid == owner_id:
            continue
        mapped = SCRIPT_ROLE_TO_ACCESS.get(m.get('role'), 'view')
        existing = (supabase.table('production_members').select('*')
                    .eq('production_id', production_id).eq('user_id', uid)
                    .limit(1).execute().data or [])
        if existing:
            row = existing[0]
            new = _raise_access(row.get('script_access'), mapped)
            if new != (row.get('script_access') or 'none'):
                (supabase.table('production_members').update({'script_access': new})
                 .eq('id', row['id']).execute())
        else:
            try:
                supabase.table('production_members').insert({
                    'production_id': production_id, 'user_id': uid, 'role': 'viewer',
                    'invited_by': actor_uid, 'script_access': mapped, **viewer_flags,
                }).execute()
            except Exception:
                # Concurrent insert raced the UNIQUE (production_id, user_id).
                again = (supabase.table('production_members').select('id')
                         .eq('production_id', production_id).eq('user_id', uid)
                         .limit(1).execute().data or [])
                if not again:
                    raise
            else:
                pms._notify_member_added(supabase, production_id, uid, 'viewer')
        moved_members += 1

    prod_pending = (supabase.table('production_invites').select('*')
                    .eq('production_id', production_id).eq('status', 'pending')
                    .execute().data or [])
    by_email = {(p.get('email') or '').strip().lower(): p for p in prod_pending}
    expires = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()

    moved_invites = 0
    for inv in live:
        email = (inv.get('email') or '').strip().lower()
        mapped = SCRIPT_ROLE_TO_ACCESS.get(inv.get('role'), 'view')

        prof = (supabase.table('profiles').select('id')
                .ilike('email', email).limit(1).execute().data or [])
        existing_member = None
        if prof:
            existing_member = (supabase.table('production_members').select('*')
                                .eq('production_id', production_id)
                                .eq('user_id', prof[0]['id'])
                                .limit(1).execute().data or [])
        if existing_member:
            # Already a production member — raise their access, no invite/email.
            row = existing_member[0]
            new = _raise_access(row.get('script_access'), mapped)
            if new != (row.get('script_access') or 'none'):
                (supabase.table('production_members').update({'script_access': new})
                 .eq('id', row['id']).execute())
        elif email in by_email:
            p = by_email[email]
            new = _raise_access(p.get('script_access'), mapped)
            if new != (p.get('script_access') or 'none'):
                (supabase.table('production_invites').update({'script_access': new})
                 .eq('id', p['id']).execute())
                p['script_access'] = new
        else:
            new_inv = supabase.table('production_invites').insert({
                'production_id': production_id, 'email': email, 'role': 'viewer',
                'token': pms._generate_token(), 'status': 'pending',
                'invited_by': actor_uid, 'expires_at': expires,
                'script_access': mapped, **viewer_flags,
            }).execute().data[0]
            by_email[email] = new_inv
            pms._send_invite_email(supabase, production_id, new_inv)
        # Silent revoke: the person just got a production invite instead.
        _revoke_script_invite(supabase, inv['id'])
        moved_invites += 1

    for inv in expired:
        _revoke_script_invite(supabase, inv['id'])

    supabase.table('script_members').delete().eq('script_id', script_id).execute()
    return {'moved_members': moved_members, 'moved_invites': moved_invites}


def _email_invite_withdrawn(supabase, invite, actor_uid):
    from services import email_service
    if not email_service.is_configured() or not invite.get('email'):
        return
    try:
        script = (supabase.table('scripts').select('title')
                  .eq('id', invite['script_id']).limit(1).execute().data or [])
        prof = (supabase.table('profiles').select('full_name, email')
                .eq('id', actor_uid).limit(1).execute().data or [])
        name = 'The script owner'
        if prof:
            name = (prof[0].get('full_name')
                    or (prof[0].get('email') or '').split('@')[0]
                    or name)
        email_service.send_invite_revoked(
            to_email=invite['email'],
            script_title=(script[0].get('title') if script else None) or 'Unknown Script',
            inviter_name=name)
    except Exception as e:
        print(f"Warning: invite-withdrawn email failed: {e}")


def drop_script_team(script_id, actor_uid):
    supabase = get_supabase_admin()
    _members, live, expired = load_script_team(script_id)
    for inv in live:
        _revoke_script_invite(supabase, inv['id'])
        _email_invite_withdrawn(supabase, inv, actor_uid)
    for inv in expired:
        _revoke_script_invite(supabase, inv['id'])
    supabase.table('script_members').delete().eq('script_id', script_id).execute()
    return {'moved_members': 0, 'moved_invites': 0}


def keep_members_on_script(production_id, script_id, user_ids, actor_uid):
    """On detach: give chosen production members a direct script_members row.

    Only members with script_access view/edit qualify. `invited_by` is the
    owner (actor) so entitlement_service keeps counting them as one seat.
    """
    supabase = get_supabase_admin()
    kept = 0
    for uid in dict.fromkeys(user_ids or []):
        rows = (supabase.table('production_members').select('script_access')
                .eq('production_id', production_id).eq('user_id', uid)
                .limit(1).execute().data or [])
        role = SCRIPT_ACCESS_TO_ROLE.get(rows[0].get('script_access')) if rows else None
        if not role:
            continue
        existing = (supabase.table('script_members').select('id')
                    .eq('script_id', script_id).eq('user_id', uid)
                    .limit(1).execute().data or [])
        if existing:
            continue
        supabase.table('script_members').insert({
            'script_id': script_id, 'user_id': uid, 'role': role,
            'department_code': KEPT_DEPARTMENT_CODE, 'invited_by': actor_uid,
        }).execute()
        kept += 1
    return kept
