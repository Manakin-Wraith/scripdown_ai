"""
Subscription Service
Handles subscription status checks, limits, and access control.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from functools import wraps
from flask import request, jsonify, g
from db.supabase_client import get_supabase_client

# Trial configuration
TRIAL_DURATION_DAYS = 14
TRIAL_SCRIPT_LIMIT = 1

# Extended trial for early access users
EARLY_ACCESS_TRIAL_DAYS = 30

# Beta configuration (6 months)
BETA_DURATION_DAYS = 180

# Feature access mapping
TRIAL_FEATURES = [
    'view_scripts',
    'view_scenes',
    'basic_analysis',
]

ACTIVE_FEATURES = [
    'view_scripts',
    'view_scenes',
    'basic_analysis',
    'upload_scripts',
    'unlimited_scripts',
    'full_analysis',
    'team_collaboration',
    'invite_members',
    'reports',
    'export_pdf',
    'stripboard_edit',
    'department_notes',
]


def get_subscription_status(user_id: str) -> Dict[str, Any]:
    """
    Get detailed subscription status for a user.
    
    Returns:
        {
            'status': 'trial' | 'active' | 'expired' | 'cancelled',
            'is_active': bool,
            'days_remaining': int | None,
            'expires_at': str | None,
            'trial_ends_at': str | None,
            'can_upload_script': bool,
            'script_count': int,
            'script_limit': int | None,
            'features': list
        }
    """
    try:
        supabase = get_supabase_client()
        
        # Get profile with subscription info
        profile_result = supabase.table('profiles') \
            .select('subscription_status, subscription_expires_at, created_at') \
            .eq('id', user_id) \
            .single() \
            .execute()
        
        if not profile_result.data:
            return _default_trial_status()
        
        profile = profile_result.data
        status = profile.get('subscription_status', 'trial')
        expires_at = profile.get('subscription_expires_at')
        created_at = profile.get('created_at')
        
        # Get script count for limit checking
        script_result = supabase.table('scripts') \
            .select('id', count='exact') \
            .eq('user_id', user_id) \
            .execute()
        
        script_count = script_result.count or 0
        
        # Calculate trial end date
        # Use subscription_expires_at if set (for early access users with extended trial)
        # Otherwise fall back to created_at + default trial days
        trial_ends_at = None
        if expires_at:
            # Early access or custom trial - use the explicit expiry date
            trial_ends_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        elif created_at:
            # Default trial - calculate from account creation
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            trial_ends_at = created_date + timedelta(days=TRIAL_DURATION_DAYS)
        
        now = datetime.now(trial_ends_at.tzinfo if trial_ends_at else None)
        
        # Determine effective status
        if status == 'trial':
            if trial_ends_at and now > trial_ends_at:
                # Trial expired
                return {
                    'status': 'expired',
                    'is_active': False,
                    'days_remaining': 0,
                    'expires_at': None,
                    'trial_ends_at': trial_ends_at.isoformat() if trial_ends_at else None,
                    'can_upload_script': False,
                    'script_count': script_count,
                    'script_limit': TRIAL_SCRIPT_LIMIT,
                    'features': [],
                    'message': 'Your trial has expired. Upgrade to continue using SlateOne.'
                }
            else:
                # Active trial
                days_remaining = (trial_ends_at - now).days if trial_ends_at else TRIAL_DURATION_DAYS
                can_upload = script_count < TRIAL_SCRIPT_LIMIT
                
                return {
                    'status': 'trial',
                    'is_active': True,
                    'days_remaining': max(0, days_remaining),
                    'expires_at': None,
                    'trial_ends_at': trial_ends_at.isoformat() if trial_ends_at else None,
                    'can_upload_script': can_upload,
                    'script_count': script_count,
                    'script_limit': TRIAL_SCRIPT_LIMIT,
                    'features': TRIAL_FEATURES,
                    'message': f'{days_remaining} days left in your trial' if days_remaining <= 7 else None
                }
        
        elif status == 'active':
            # Check if beta subscription has expired
            if expires_at:
                expires_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if now > expires_date:
                    return {
                        'status': 'expired',
                        'is_active': False,
                        'days_remaining': 0,
                        'expires_at': expires_at,
                        'trial_ends_at': None,
                        'can_upload_script': False,
                        'script_count': script_count,
                        'script_limit': None,
                        'features': [],
                        'message': 'Your subscription has expired. Renew to continue using SlateOne.'
                    }
                else:
                    days_remaining = (expires_date - now).days
                    return {
                        'status': 'active',
                        'is_active': True,
                        'days_remaining': max(0, days_remaining),
                        'expires_at': expires_at,
                        'trial_ends_at': None,
                        'can_upload_script': True,
                        'script_count': script_count,
                        'script_limit': None,  # Unlimited
                        'features': ACTIVE_FEATURES,
                        'message': f'{days_remaining} days until renewal' if days_remaining <= 14 else None
                    }
            else:
                # Active with no expiry (lifetime beta)
                return {
                    'status': 'active',
                    'is_active': True,
                    'days_remaining': None,
                    'expires_at': None,
                    'trial_ends_at': None,
                    'can_upload_script': True,
                    'script_count': script_count,
                    'script_limit': None,
                    'features': ACTIVE_FEATURES,
                    'message': None
                }
        
        elif status in ['expired', 'cancelled']:
            return {
                'status': status,
                'is_active': False,
                'days_remaining': 0,
                'expires_at': expires_at,
                'trial_ends_at': None,
                'can_upload_script': False,
                'script_count': script_count,
                'script_limit': None,
                'features': [],
                'message': 'Your subscription is inactive. Upgrade to continue using SlateOne.'
            }
        
        return _default_trial_status()
        
    except Exception as e:
        print(f"Error getting subscription status: {e}")
        return _default_trial_status()


def _default_trial_status() -> Dict[str, Any]:
    """Return default trial status for new/unknown users."""
    return {
        'status': 'trial',
        'is_active': True,
        'days_remaining': TRIAL_DURATION_DAYS,
        'expires_at': None,
        'trial_ends_at': None,
        'can_upload_script': True,
        'script_count': 0,
        'script_limit': TRIAL_SCRIPT_LIMIT,
        'features': TRIAL_FEATURES,
        'message': None
    }


def can_access_feature(user_id: str, feature: str) -> Tuple[bool, Optional[str]]:
    """
    Check if user can access a specific feature.
    
    Returns:
        (can_access: bool, message: str | None)
    """
    sub_status = get_subscription_status(user_id)
    
    if feature in sub_status.get('features', []):
        return True, None
    
    # Feature not available
    if sub_status['status'] == 'trial':
        return False, f"Upgrade to access {feature.replace('_', ' ')}. Trial users have limited access."
    elif sub_status['status'] == 'expired':
        return False, "Your subscription has expired. Renew to access this feature."
    else:
        return False, "This feature requires an active subscription."


def can_upload_script(user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Check if user can upload a new script.
    
    Returns:
        (can_upload: bool, message: str | None)
    """
    sub_status = get_subscription_status(user_id)
    
    if not sub_status['is_active']:
        return False, "Your subscription is inactive. Upgrade to upload scripts."
    
    if sub_status['can_upload_script']:
        return True, None
    
    # Trial user at limit
    return False, f"Trial users can only upload {TRIAL_SCRIPT_LIMIT} script. Upgrade for unlimited scripts."


def activate_beta_subscription(user_id: str, email: str) -> Dict[str, Any]:
    """
    Activate beta subscription for a user after payment.
    Sets subscription_status to 'active' and expiry to 6 months from now.
    """
    try:
        supabase = get_supabase_client()
        
        expires_at = datetime.now() + timedelta(days=BETA_DURATION_DAYS)
        
        # Update profile
        result = supabase.table('profiles') \
            .update({
                'subscription_status': 'active',
                'subscription_expires_at': expires_at.isoformat()
            }) \
            .eq('id', user_id) \
            .execute()
        
        # Link payment to user if exists
        supabase.table('beta_payments') \
            .update({'user_id': user_id}) \
            .eq('email', email.lower().strip()) \
            .execute()
        
        return {
            'success': True,
            'status': 'active',
            'expires_at': expires_at.isoformat()
        }
        
    except Exception as e:
        print(f"Error activating subscription: {e}")
        return {'success': False, 'error': str(e)}


def get_users_expiring_soon(days: int = 7) -> list:
    """
    Get list of users whose subscriptions expire within the specified days.
    Used for sending reminder emails.
    """
    try:
        supabase = get_supabase_client()
        
        now = datetime.now()
        threshold = now + timedelta(days=days)
        
        # Get active users expiring soon
        result = supabase.table('profiles') \
            .select('id, email, full_name, subscription_status, subscription_expires_at') \
            .eq('subscription_status', 'active') \
            .lte('subscription_expires_at', threshold.isoformat()) \
            .gte('subscription_expires_at', now.isoformat()) \
            .execute()
        
        return result.data or []
        
    except Exception as e:
        print(f"Error getting expiring users: {e}")
        return []


def register_early_access_user(email: str) -> Dict[str, Any]:
    """
    Register an email as an early access user.
    Creates an entry in early_access_users table so when they sign up,
    they get the extended 30-day trial instead of 14 days.
    
    Args:
        email: User's email address
    
    Returns:
        {'success': True} or {'success': False, 'error': str}
    """
    try:
        supabase = get_supabase_client()
        
        # Insert or update early access record
        result = supabase.table('early_access_users') \
            .upsert({
                'email': email.lower().strip(),
                'trial_days': EARLY_ACCESS_TRIAL_DAYS,
                'invited_at': datetime.now().isoformat(),
                'status': 'invited'
            }, on_conflict='email') \
            .execute()
        
        return {'success': True, 'email': email}
        
    except Exception as e:
        print(f"Error registering early access user: {e}")
        return {'success': False, 'error': str(e)}


def get_early_access_trial_days(email: str) -> int:
    """
    Check if an email is registered for early access and return their trial days.
    Returns EARLY_ACCESS_TRIAL_DAYS if found, otherwise TRIAL_DURATION_DAYS.
    
    Args:
        email: User's email address
    
    Returns:
        Number of trial days for this user
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('early_access_users') \
            .select('trial_days') \
            .eq('email', email.lower().strip()) \
            .eq('status', 'invited') \
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0].get('trial_days', EARLY_ACCESS_TRIAL_DAYS)
        
        return TRIAL_DURATION_DAYS
        
    except Exception as e:
        print(f"Error checking early access status: {e}")
        return TRIAL_DURATION_DAYS


def mark_early_access_user_signed_up(email: str, user_id: str) -> None:
    """
    Mark an early access user as signed up.
    Called when a user completes registration.
    
    Args:
        email: User's email address
        user_id: The user's UUID after signup
    """
    try:
        supabase = get_supabase_client()
        
        supabase.table('early_access_users') \
            .update({
                'status': 'signed_up',
                'user_id': user_id,
                'signed_up_at': datetime.now().isoformat()
            }) \
            .eq('email', email.lower().strip()) \
            .execute()
            
    except Exception as e:
        print(f"Error marking early access user as signed up: {e}")


def get_trial_users_expiring_soon(days: int = 3) -> list:
    """
    Get list of trial users whose trials expire within the specified days.
    """
    try:
        supabase = get_supabase_client()
        
        now = datetime.now()
        # Trial users created (TRIAL_DURATION_DAYS - days) ago
        threshold_start = now - timedelta(days=TRIAL_DURATION_DAYS)
        threshold_end = now - timedelta(days=TRIAL_DURATION_DAYS - days)
        
        result = supabase.table('profiles') \
            .select('id, email, full_name, subscription_status, created_at') \
            .eq('subscription_status', 'trial') \
            .gte('created_at', threshold_start.isoformat()) \
            .lte('created_at', threshold_end.isoformat()) \
            .execute()
        
        return result.data or []
        
    except Exception as e:
        print(f"Error getting expiring trial users: {e}")
        return []


# Decorator for protecting routes
def require_active_subscription(f):
    """
    Decorator to require an active subscription for a route.
    Returns 403 if subscription is not active.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get user_id from request (assumes auth middleware sets this)
        user_id = getattr(g, 'user_id', None)
        
        if not user_id:
            # Try to get from request headers or body
            auth_header = request.headers.get('Authorization', '')
            if not auth_header:
                return jsonify({'error': 'Authentication required'}), 401
            # For now, pass through - actual auth check happens elsewhere
            return f(*args, **kwargs)
        
        sub_status = get_subscription_status(user_id)
        
        if not sub_status['is_active']:
            return jsonify({
                'error': 'Subscription required',
                'subscription_status': sub_status['status'],
                'message': sub_status.get('message', 'Please upgrade to access this feature.'),
                'upgrade_url': 'https://pay.yoco.com/r/2JB0rQ'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated


def require_feature(feature: str):
    """
    Decorator factory to require a specific feature.
    Usage: @require_feature('team_collaboration')
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(g, 'user_id', None)
            
            if not user_id:
                return f(*args, **kwargs)
            
            can_access, message = can_access_feature(user_id, feature)
            
            if not can_access:
                return jsonify({
                    'error': 'Feature not available',
                    'feature': feature,
                    'message': message,
                    'upgrade_url': 'https://pay.yoco.com/r/2JB0rQ'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator
