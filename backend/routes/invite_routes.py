"""
Team Invite Routes

Handles script team invitations:
- Create invite (generate magic link)
- List invites for a script
- Accept invite
- Revoke invite
- List/manage team members
- Email notifications
"""

import os
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from db.supabase_client import get_supabase_client, get_supabase_admin
from middleware.auth import require_auth, optional_auth, get_user_id
from services.email_service import send_invite_accepted_notification, send_test_email, is_configured as email_configured

invite_bp = Blueprint('invite', __name__)

# Use admin client for server-side operations (bypasses RLS)
try:
    supabase = get_supabase_admin()
except ValueError:
    print("Warning: Using anon client for invites - RLS will apply")
    supabase = get_supabase_client()

# Frontend URL for email links
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

# Cache for departments from database
_departments_cache = None

def get_departments_list():
    """Get departments from database with caching."""
    global _departments_cache
    if _departments_cache is None and supabase:
        try:
            result = supabase.table('departments').select('code, name, color').order('sort_order').execute()
            _departments_cache = result.data or []
        except Exception as e:
            print(f"Error fetching departments: {e}")
            _departments_cache = []
    return _departments_cache or []

def get_department_name(code):
    """Get department name by code."""
    depts = get_departments_list()
    for d in depts:
        if d['code'] == code:
            return d['name']
    return code

def generate_invite_token():
    """Generate a secure random token for invite links."""
    return secrets.token_urlsafe(32)


@invite_bp.route('/api/invite/departments', methods=['GET'])
def get_invite_departments():
    """Get list of available departments for invites."""
    return jsonify({'departments': get_departments_list()})


@invite_bp.route('/api/scripts/<script_id>/invites', methods=['POST'])
@require_auth
def create_invite(script_id):
    """
    Create a new invite for a script.
    
    Body:
    {
        "email": "teammate@example.com",
        "department_code": "costume",
        "role": "member"  // optional, defaults to 'member'
    }
    """
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    user_id = get_user_id()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    
    email = data.get('email', '').strip().lower()
    department_code = data.get('department_code')
    role = data.get('role', 'member')
    
    # Validation
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    if not department_code:
        return jsonify({'error': 'Department is required'}), 400
    if department_code not in [d['code'] for d in get_departments_list()]:
        return jsonify({'error': 'Invalid department code'}), 400
    if role not in ['admin', 'member', 'viewer']:
        return jsonify({'error': 'Invalid role'}), 400
    
    try:
        # Verify user owns the script or is admin
        script_result = supabase.table('scripts').select('id, user_id, title').eq('id', script_id).single().execute()
        
        if not script_result.data:
            return jsonify({'error': 'Script not found'}), 404
        
        script = script_result.data
        
        # Check ownership or admin status
        if script['user_id'] != user_id:
            member_check = supabase.table('script_members').select('role').eq('script_id', script_id).eq('user_id', user_id).single().execute()
            if not member_check.data or member_check.data['role'] not in ['owner', 'admin']:
                return jsonify({'error': 'Not authorized to invite members'}), 403
        
        # Check if invite already exists for this email/script
        # Note: We skip the "already a member" check here - it will be handled during accept
        try:
            existing = supabase.table('script_invites').select('id, status').eq('script_id', script_id).eq('email', email).eq('status', 'pending').execute()
            if existing.data:
                return jsonify({'error': 'An invite is already pending for this email'}), 409
        except Exception as e:
            print(f"Warning: Could not check existing invites: {e}")
        
        # Generate invite token
        token = generate_invite_token()
        expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
        
        # Create invite
        invite_data = {
            'script_id': script_id,
            'email': email,
            'department_code': department_code,
            'role': role,
            'token': token,
            'invited_by': user_id,
            'status': 'pending',
            'expires_at': expires_at
        }
        
        result = supabase.table('script_invites').insert(invite_data).execute()
        
        if not result.data:
            return jsonify({'error': 'Failed to create invite'}), 500
        
        invite = result.data[0]
        
        # Build invite URL
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        invite_url = f"{frontend_url}/invite/{token}"
        
        # Get department name
        dept_name = get_department_name(department_code)
        
        return jsonify({
            'invite': {
                'id': invite['id'],
                'email': email,
                'department': dept_name,
                'department_code': department_code,
                'role': role,
                'status': 'pending',
                'invite_url': invite_url,
                'expires_at': expires_at,
                'script_title': script['title']
            }
        }), 201
        
    except Exception as e:
        print(f"Error creating invite: {e}")
        return jsonify({'error': str(e)}), 500


@invite_bp.route('/api/scripts/<script_id>/invites', methods=['GET'])
@require_auth
def list_invites(script_id):
    """Get all invites for a script."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    user_id = get_user_id()
    
    try:
        # Verify access
        script_result = supabase.table('scripts').select('user_id').eq('id', script_id).single().execute()
        
        if not script_result.data:
            return jsonify({'error': 'Script not found'}), 404
        
        # Get invites
        result = supabase.table('script_invites').select('*').eq('script_id', script_id).order('created_at', desc=True).execute()
        
        invites = []
        for inv in result.data or []:
            dept_name = get_department_name(inv['department_code'])
            invites.append({
                'id': inv['id'],
                'email': inv['email'],
                'department': dept_name,
                'department_code': inv['department_code'],
                'role': inv['role'],
                'status': inv['status'],
                'created_at': inv['created_at'],
                'expires_at': inv['expires_at']
            })
        
        return jsonify({'invites': invites})
        
    except Exception as e:
        print(f"Error listing invites: {e}")
        return jsonify({'error': str(e)}), 500


@invite_bp.route('/api/invites/<invite_id>', methods=['DELETE'])
@require_auth
def revoke_invite(invite_id):
    """Revoke a pending invite."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    user_id = get_user_id()
    
    try:
        # Get invite and verify ownership
        invite_result = supabase.table('script_invites').select('*, scripts(user_id)').eq('id', invite_id).single().execute()
        
        if not invite_result.data:
            return jsonify({'error': 'Invite not found'}), 404
        
        invite = invite_result.data
        
        # Check authorization
        if invite['scripts']['user_id'] != user_id and invite['invited_by'] != user_id:
            return jsonify({'error': 'Not authorized'}), 403
        
        # Update status to revoked
        supabase.table('script_invites').update({'status': 'revoked'}).eq('id', invite_id).execute()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error revoking invite: {e}")
        return jsonify({'error': str(e)}), 500


@invite_bp.route('/api/invites/token/<token>', methods=['GET'])
def get_invite_by_token(token):
    """
    Get invite details by token (public endpoint for invite landing page).
    """
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        result = supabase.table('script_invites').select('*, scripts(id, title)').eq('token', token).single().execute()
        
        if not result.data:
            return jsonify({'error': 'Invite not found'}), 404
        
        invite = result.data
        
        # Check if expired
        if invite['expires_at']:
            expires = datetime.fromisoformat(invite['expires_at'].replace('Z', '+00:00'))
            if expires < datetime.now(expires.tzinfo):
                return jsonify({'error': 'Invite has expired', 'status': 'expired'}), 410
        
        # Check status
        if invite['status'] != 'pending':
            return jsonify({'error': f'Invite is {invite["status"]}', 'status': invite['status']}), 410
        
        dept_name = get_department_name(invite['department_code'])
        
        return jsonify({
            'invite': {
                'id': invite['id'],
                'email': invite['email'],
                'department': dept_name,
                'department_code': invite['department_code'],
                'role': invite['role'],
                'script_id': invite['script_id'],
                'script_title': invite['scripts']['title'] if invite['scripts'] else 'Unknown Script',
                'status': invite['status']
            }
        })
        
    except Exception as e:
        print(f"Error getting invite: {e}")
        return jsonify({'error': str(e)}), 500


@invite_bp.route('/api/invites/token/<token>/accept', methods=['POST'])
@require_auth
def accept_invite(token):
    """
    Accept an invite and join the script team.
    User must be authenticated.
    """
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    user_id = get_user_id()
    current_user = g.current_user
    user_email = current_user.get('email', '').lower()
    
    try:
        # Get invite
        result = supabase.table('script_invites').select('*').eq('token', token).single().execute()
        
        if not result.data:
            return jsonify({'error': 'Invite not found'}), 404
        
        invite = result.data
        
        # Verify email matches (optional - can be removed for flexibility)
        # if invite['email'].lower() != user_email:
        #     return jsonify({'error': 'This invite was sent to a different email address'}), 403
        
        # Check if expired
        if invite['expires_at']:
            expires = datetime.fromisoformat(invite['expires_at'].replace('Z', '+00:00'))
            if expires < datetime.now(expires.tzinfo):
                supabase.table('script_invites').update({'status': 'expired'}).eq('id', invite['id']).execute()
                return jsonify({'error': 'Invite has expired'}), 410
        
        # Check status
        if invite['status'] != 'pending':
            return jsonify({'error': f'Invite is already {invite["status"]}'}), 410
        
        # Check if already a member
        existing = supabase.table('script_members').select('id').eq('script_id', invite['script_id']).eq('user_id', user_id).execute()
        
        if existing.data:
            return jsonify({'error': 'You are already a member of this script'}), 409
        
        # Add as team member
        member_data = {
            'script_id': invite['script_id'],
            'user_id': user_id,
            'department_code': invite['department_code'],
            'role': invite['role'],
            'invited_by': invite['invited_by']
        }
        
        member_result = supabase.table('script_members').insert(member_data).execute()
        
        if not member_result.data:
            return jsonify({'error': 'Failed to join team'}), 500
        
        # Update invite status
        supabase.table('script_invites').update({
            'status': 'accepted',
            'accepted_at': datetime.utcnow().isoformat()
        }).eq('id', invite['id']).execute()
        
        # Get script title for notification
        script_result = supabase.table('scripts').select('title').eq('id', invite['script_id']).single().execute()
        script_title = script_result.data.get('title', 'Unknown Script') if script_result.data else 'Unknown Script'
        
        # Get accepting user's name
        profile_result = supabase.table('profiles').select('full_name, email').eq('id', user_id).single().execute()
        accepter_name = 'Someone'
        if profile_result.data:
            accepter_name = profile_result.data.get('full_name') or profile_result.data.get('email', 'Someone')
        
        # Create notification for the invite sender
        if invite['invited_by']:
            dept_name = get_department_name(invite['department_code'])
            notification_data = {
                'user_id': invite['invited_by'],
                'type': 'invite_accepted',
                'title': 'Invite Accepted!',
                'message': f'{accepter_name} has joined "{script_title}" as {dept_name}',
                'data': {
                    'script_id': invite['script_id'],
                    'script_title': script_title,
                    'accepter_id': user_id,
                    'accepter_name': accepter_name,
                    'department': dept_name,
                    'department_code': invite['department_code']
                }
            }
            try:
                supabase.table('notifications').insert(notification_data).execute()
            except Exception as notif_err:
                print(f"Warning: Failed to create notification: {notif_err}")
            
            # Send email notification to invite sender
            if email_configured():
                try:
                    # Get inviter's profile for email and name
                    inviter_result = supabase.table('profiles').select('email, full_name').eq('id', invite['invited_by']).single().execute()
                    if inviter_result.data and inviter_result.data.get('email'):
                        inviter_email = inviter_result.data['email']
                        inviter_name = inviter_result.data.get('full_name') or inviter_email.split('@')[0]
                        script_url = f"{FRONTEND_URL}/scenes/{invite['script_id']}"
                        
                        send_invite_accepted_notification(
                            to_email=inviter_email,
                            inviter_name=inviter_name,
                            accepter_name=accepter_name,
                            script_title=script_title,
                            department=dept_name,
                            script_url=script_url
                        )
                except Exception as email_err:
                    print(f"Warning: Failed to send email notification: {email_err}")
        
        return jsonify({
            'success': True,
            'script_id': invite['script_id'],
            'department_code': invite['department_code'],
            'message': 'Successfully joined the team!'
        })
        
    except Exception as e:
        print(f"Error accepting invite: {e}")
        return jsonify({'error': str(e)}), 500


@invite_bp.route('/api/invites/auto-accept', methods=['POST'])
@require_auth
def auto_accept_pending_invites():
    """
    Automatically accept all pending invites for the authenticated user's email.
    Called after signup/login to seamlessly add user to teams they were invited to.
    """
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    user_id = get_user_id()
    current_user = g.current_user
    user_email = current_user.get('email', '').lower()
    
    if not user_email:
        return jsonify({'error': 'User email not found'}), 400
    
    try:
        # Find all pending invites for this email
        result = supabase.table('script_invites').select('*').eq('email', user_email).eq('status', 'pending').execute()
        
        if not result.data:
            return jsonify({'accepted': [], 'message': 'No pending invites found'})
        
        accepted = []
        
        for invite in result.data:
            try:
                # Check if expired
                if invite['expires_at']:
                    expires = datetime.fromisoformat(invite['expires_at'].replace('Z', '+00:00'))
                    if expires < datetime.now(expires.tzinfo):
                        supabase.table('script_invites').update({'status': 'expired'}).eq('id', invite['id']).execute()
                        continue
                
                # Check if already a member
                existing = supabase.table('script_members').select('id').eq('script_id', invite['script_id']).eq('user_id', user_id).execute()
                
                if existing.data:
                    # Already a member, just mark invite as accepted
                    supabase.table('script_invites').update({
                        'status': 'accepted',
                        'accepted_at': datetime.utcnow().isoformat()
                    }).eq('id', invite['id']).execute()
                    continue
                
                # Add as team member
                member_data = {
                    'script_id': invite['script_id'],
                    'user_id': user_id,
                    'department_code': invite['department_code'],
                    'role': invite['role'],
                    'invited_by': invite['invited_by']
                }
                
                member_result = supabase.table('script_members').insert(member_data).execute()
                
                if member_result.data:
                    # Update invite status
                    supabase.table('script_invites').update({
                        'status': 'accepted',
                        'accepted_at': datetime.utcnow().isoformat()
                    }).eq('id', invite['id']).execute()
                    
                    # Get script title
                    script_result = supabase.table('scripts').select('title').eq('id', invite['script_id']).single().execute()
                    script_title = script_result.data.get('title', 'Unknown Script') if script_result.data else 'Unknown Script'
                    
                    dept_name = get_department_name(invite['department_code'])
                    
                    accepted.append({
                        'script_id': invite['script_id'],
                        'script_title': script_title,
                        'department': dept_name,
                        'department_code': invite['department_code']
                    })
                    
                    # Create notification for invite sender
                    if invite['invited_by']:
                        profile_result = supabase.table('profiles').select('full_name, email').eq('id', user_id).single().execute()
                        accepter_name = 'Someone'
                        if profile_result.data:
                            accepter_name = profile_result.data.get('full_name') or profile_result.data.get('email', 'Someone')
                        
                        notification_data = {
                            'user_id': invite['invited_by'],
                            'type': 'invite_accepted',
                            'title': 'Invite Accepted!',
                            'message': f'{accepter_name} has joined "{script_title}" as {dept_name}',
                            'data': {
                                'script_id': invite['script_id'],
                                'script_title': script_title,
                                'accepter_id': user_id,
                                'accepter_name': accepter_name,
                                'department': dept_name,
                                'department_code': invite['department_code']
                            }
                        }
                        try:
                            supabase.table('notifications').insert(notification_data).execute()
                        except Exception as notif_err:
                            print(f"Warning: Failed to create notification: {notif_err}")
                        
                        # Send email notification
                        if email_configured():
                            try:
                                inviter_result = supabase.table('profiles').select('email, full_name').eq('id', invite['invited_by']).single().execute()
                                if inviter_result.data and inviter_result.data.get('email'):
                                    inviter_email = inviter_result.data['email']
                                    inviter_name = inviter_result.data.get('full_name') or inviter_email.split('@')[0]
                                    script_url = f"{FRONTEND_URL}/scenes/{invite['script_id']}"
                                    
                                    send_invite_accepted_notification(
                                        to_email=inviter_email,
                                        inviter_name=inviter_name,
                                        accepter_name=accepter_name,
                                        script_title=script_title,
                                        department=dept_name,
                                        script_url=script_url
                                    )
                            except Exception as email_err:
                                print(f"Warning: Failed to send email notification: {email_err}")
                
            except Exception as invite_err:
                print(f"Error processing invite {invite['id']}: {invite_err}")
                continue
        
        return jsonify({
            'accepted': accepted,
            'count': len(accepted),
            'message': f'Successfully joined {len(accepted)} team(s)' if accepted else 'No new teams joined'
        })
        
    except Exception as e:
        print(f"Error auto-accepting invites: {e}")
        return jsonify({'error': str(e)}), 500


@invite_bp.route('/api/scripts/<script_id>/members', methods=['GET'])
@optional_auth
def list_members(script_id):
    """Get all team members for a script."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    try:
        # Get members with profile info (specify the user_id foreign key relationship)
        result = supabase.table('script_members').select('*, profiles!script_members_user_id_fkey(id, email, full_name, avatar_url, job_title)').eq('script_id', script_id).order('joined_at').execute()
        
        members = []
        for m in result.data or []:
            profile = m.get('profiles', {}) or {}
            dept_name = get_department_name(m['department_code'])
            
            members.append({
                'id': m['id'],
                'user_id': m['user_id'],
                'name': profile.get('full_name') or profile.get('email', 'Unknown'),
                'email': profile.get('email'),
                'avatar_url': profile.get('avatar_url'),
                'job_title': profile.get('job_title'),
                'department': dept_name,
                'department_code': m['department_code'],
                'role': m['role'],
                'joined_at': m['joined_at']
            })
        
        # Get script to find owner user_id
        script_result = supabase.table('scripts').select('user_id').eq('id', script_id).single().execute()
        
        owner = None
        if script_result.data:
            owner_user_id = script_result.data['user_id']
            # Fetch owner's profile separately
            owner_profile_result = supabase.table('profiles').select('id, email, full_name, avatar_url').eq('id', owner_user_id).single().execute()
            owner_profile = owner_profile_result.data or {}
            owner = {
                'user_id': owner_user_id,
                'name': owner_profile.get('full_name') or owner_profile.get('email', 'Owner'),
                'email': owner_profile.get('email'),
                'avatar_url': owner_profile.get('avatar_url'),
                'role': 'owner'
            }
        
        return jsonify({
            'owner': owner,
            'members': members
        })
        
    except Exception as e:
        print(f"Error listing members: {e}")
        return jsonify({'error': str(e)}), 500


@invite_bp.route('/api/scripts/<script_id>/my-membership', methods=['GET'])
@require_auth
def get_my_membership(script_id):
    """Get the current user's membership info for a script."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    user_id = get_user_id()
    
    try:
        # Check if user is the owner
        script_result = supabase.table('scripts').select('user_id, title').eq('id', script_id).single().execute()
        
        if not script_result.data:
            return jsonify({'error': 'Script not found'}), 404
        
        if script_result.data['user_id'] == user_id:
            # User is the owner
            return jsonify({
                'membership': {
                    'role': 'owner',
                    'department': None,
                    'department_code': None,
                    'is_owner': True
                }
            })
        
        # Check if user is a team member
        member_result = supabase.table('script_members').select('*').eq('script_id', script_id).eq('user_id', user_id).single().execute()
        
        if not member_result.data:
            return jsonify({'membership': None})
        
        member = member_result.data
        dept_name = get_department_name(member['department_code'])
        
        # Get department color
        depts = get_departments_list()
        dept_color = next((d.get('color', '#6366F1') for d in depts if d['code'] == member['department_code']), '#6366F1')
        
        return jsonify({
            'membership': {
                'id': member['id'],
                'role': member['role'],
                'department': dept_name,
                'department_code': member['department_code'],
                'department_color': dept_color,
                'joined_at': member['joined_at'],
                'is_owner': False
            }
        })
        
    except Exception as e:
        print(f"Error getting membership: {e}")
        return jsonify({'error': str(e)}), 500


@invite_bp.route('/api/scripts/<script_id>/members/<member_id>', methods=['DELETE'])
@require_auth
def remove_member(script_id, member_id):
    """Remove a team member from a script."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    user_id = get_user_id()
    
    try:
        # Verify ownership
        script_result = supabase.table('scripts').select('user_id').eq('id', script_id).single().execute()
        
        if not script_result.data:
            return jsonify({'error': 'Script not found'}), 404
        
        if script_result.data['user_id'] != user_id:
            return jsonify({'error': 'Only script owner can remove members'}), 403
        
        # Remove member
        supabase.table('script_members').delete().eq('id', member_id).eq('script_id', script_id).execute()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error removing member: {e}")
        return jsonify({'error': str(e)}), 500


# ============ Notification Routes ============

@invite_bp.route('/api/notifications', methods=['GET'])
@require_auth
def get_notifications():
    """Get notifications for the current user."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    user_id = get_user_id()
    limit = request.args.get('limit', 20, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    try:
        query = supabase.table('notifications').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit)
        
        if unread_only:
            query = query.eq('read', False)
        
        result = query.execute()
        
        # Count unread
        unread_result = supabase.table('notifications').select('id', count='exact').eq('user_id', user_id).eq('read', False).execute()
        unread_count = unread_result.count if hasattr(unread_result, 'count') else len(unread_result.data or [])
        
        return jsonify({
            'notifications': result.data or [],
            'unread_count': unread_count
        })
        
    except Exception as e:
        print(f"Error getting notifications: {e}")
        return jsonify({'error': str(e)}), 500


@invite_bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
@require_auth
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    user_id = get_user_id()
    
    try:
        supabase.table('notifications').update({'read': True}).eq('id', notification_id).eq('user_id', user_id).execute()
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error marking notification read: {e}")
        return jsonify({'error': str(e)}), 500


@invite_bp.route('/api/notifications/read-all', methods=['POST'])
@require_auth
def mark_all_notifications_read():
    """Mark all notifications as read for the current user."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    
    user_id = get_user_id()
    
    try:
        supabase.table('notifications').update({'read': True}).eq('user_id', user_id).eq('read', False).execute()
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error marking all notifications read: {e}")
        return jsonify({'error': str(e)}), 500


# ============ Email Test Routes ============

@invite_bp.route('/api/email/test', methods=['POST'])
def test_email():
    """
    Send a test email to verify email service is working.
    
    Request body:
    {
        "email": "your-email@example.com"
    }
    """
    data = request.get_json() or {}
    to_email = data.get('email')
    
    if not to_email:
        return jsonify({'error': 'Email address is required'}), 400
    
    if not email_configured():
        return jsonify({
            'error': 'Email service not configured',
            'hint': 'Add RESEND_API_KEY to your .env file'
        }), 503
    
    result = send_test_email(to_email)
    
    if 'error' in result:
        return jsonify({
            'success': False,
            'error': result['error']
        }), 500
    
    return jsonify({
        'success': True,
        'message': f'Test email sent to {to_email}',
        'result': result
    })


@invite_bp.route('/api/email/status', methods=['GET'])
def email_status():
    """Check if email service is configured."""
    return jsonify({
        'configured': email_configured(),
        'from_email': os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')
    })
