"""
Credit Service
Handles script credit management, purchases, and usage tracking.
"""

from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from db.supabase_client import get_supabase_client

# Credit package configurations — Breakdown Packs
CREDIT_PACKAGES = {
    'single': {
        'credits': 1,
        'price': 500.00,
        'per_breakdown': 500.00,
        'name': '1 Breakdown',
        'description': 'Break down 1 screenplay',
        'validity': '6 months'
    },
    'pack_5': {
        'credits': 5,
        'price': 2000.00,
        'per_breakdown': 400.00,
        'savings': '20%',
        'name': '5 Breakdowns',
        'description': 'Break down 5 screenplays — Save 20%',
        'validity': '12 months'
    },
    'pack_10': {
        'credits': 10,
        'price': 3500.00,
        'per_breakdown': 350.00,
        'savings': '30%',
        'name': '10 Breakdowns',
        'description': 'Break down 10 screenplays — Save 30%',
        'validity': '12 months'
    },
    'pack_25': {
        'credits': 25,
        'price': 7500.00,
        'per_breakdown': 300.00,
        'savings': '40%',
        'name': '25 Breakdowns',
        'description': 'Break down 25 screenplays — Save 40%',
        'validity': '12 months'
    }
}


def get_credit_balance(user_id: str) -> Dict[str, Any]:
    """
    Get user's current credit balance and usage stats.
    
    Returns:
        {
            'credits': int,
            'total_purchased': int,
            'scripts_uploaded': int,
            'is_legacy_beta': bool,
            'usage_history': list
        }
    """
    try:
        supabase = get_supabase_client()
        
        # Get profile with credit info
        profile_result = supabase.table('profiles') \
            .select('script_credits, total_scripts_purchased, is_legacy_beta') \
            .eq('id', user_id) \
            .execute()
        
        # If profile doesn't exist, create it
        if not profile_result.data or len(profile_result.data) == 0:
            print(f"Profile not found for user {user_id}, creating default profile...")
            
            # Create profile with default values
            create_result = supabase.table('profiles') \
                .insert({
                    'id': user_id,
                    'script_credits': 0,
                    'total_scripts_purchased': 0,
                    'is_legacy_beta': False
                }) \
                .execute()
            
            if create_result.data and len(create_result.data) > 0:
                profile_result.data = create_result.data
            else:
                print(f"Failed to create profile for user {user_id}")
                return {
                    'credits': 0,
                    'total_purchased': 0,
                    'scripts_uploaded': 0,
                    'is_legacy_beta': False,
                    'usage_history': []
                }
        
        # Get first profile from results
        profile = profile_result.data[0] if isinstance(profile_result.data, list) else profile_result.data
        
        # Debug: Log the raw profile data
        print(f"DEBUG - Raw profile data for user {user_id}:")
        print(f"  script_credits: {profile.get('script_credits')}")
        print(f"  total_scripts_purchased: {profile.get('total_scripts_purchased')}")
        print(f"  is_legacy_beta: {profile.get('is_legacy_beta')} (type: {type(profile.get('is_legacy_beta'))})")
        
        # Get usage count
        usage_result = supabase.table('script_credit_usage') \
            .select('id', count='exact') \
            .eq('user_id', user_id) \
            .execute()
        
        scripts_uploaded = usage_result.count or 0
        
        # Get recent usage history (last 10)
        history_result = supabase.table('script_credit_usage') \
            .select('id, script_name, credits_used, created_at') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .limit(10) \
            .execute()
        
        return {
            'credits': profile.get('script_credits', 0),
            'total_purchased': profile.get('total_scripts_purchased', 0),
            'scripts_uploaded': scripts_uploaded,
            'is_legacy_beta': profile.get('is_legacy_beta', False),
            'usage_history': history_result.data or []
        }
        
    except Exception as e:
        print(f"Error getting credit balance: {e}")
        return {
            'credits': 0,
            'total_purchased': 0,
            'scripts_uploaded': 0,
            'is_legacy_beta': False,
            'usage_history': []
        }


def can_upload_with_credits(user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Check if user has credits to upload a script.
    
    Returns:
        (can_upload: bool, message: str | None)
    """
    balance = get_credit_balance(user_id)
    
    if balance['credits'] > 0:
        return True, None
    
    # No credits available
    if balance['is_legacy_beta']:
        return False, "You've used all your legacy beta credits. Purchase more to continue uploading."
    else:
        return False, "You need credits to upload scripts. Purchase a credit pack to get started."


def deduct_credit_for_script(user_id: str, script_id: str, script_name: str) -> Dict[str, Any]:
    """
    Deduct 1 credit from user's balance and log usage.
    Uses database function for atomic operation.
    
    Returns:
        {'success': bool, 'remaining_credits': int | None, 'error': str | None}
    """
    try:
        # Use admin client for server-side operations
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        # Call database function for atomic deduction
        result = supabase.rpc('deduct_script_credit', {
            'p_user_id': user_id,
            'p_script_id': script_id,
            'p_script_name': script_name
        }).execute()
        
        if result.data:
            # Get updated balance
            balance = get_credit_balance(user_id)
            return {
                'success': True,
                'remaining_credits': balance['credits'],
                'error': None
            }
        else:
            return {
                'success': False,
                'remaining_credits': None,
                'error': 'Insufficient credits'
            }
            
    except Exception as e:
        print(f"Error deducting credit: {e}")
        return {
            'success': False,
            'remaining_credits': None,
            'error': str(e)
        }


def add_credits_after_purchase(user_id: str, credits: int, purchase_id: str) -> Dict[str, Any]:
    """
    Add credits to user's account after successful payment.
    Uses database function for atomic operation.
    
    Returns:
        {'success': bool, 'new_balance': int | None, 'error': str | None}
    """
    try:
        # Use admin client for server-side operations
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        # Call database function for atomic credit addition
        result = supabase.rpc('add_script_credits', {
            'p_user_id': user_id,
            'p_credits': credits,
            'p_purchase_id': purchase_id
        }).execute()
        
        if result.data:
            # Get updated balance
            balance = get_credit_balance(user_id)
            return {
                'success': True,
                'new_balance': balance['credits'],
                'error': None
            }
        else:
            return {
                'success': False,
                'new_balance': None,
                'error': 'Failed to add credits'
            }
            
    except Exception as e:
        print(f"Error adding credits: {e}")
        return {
            'success': False,
            'new_balance': None,
            'error': str(e)
        }


def track_breakdown_usage(user_id: str, script_id: str, script_name: str) -> Dict[str, Any]:
    """
    Track that a script breakdown was performed.
    Called when AI analysis is first triggered for a script.
    
    Pricing model: $49/month unlimited breakdowns.
    - Active subscribers: log usage only (no credit deduction)
    - Legacy credit users: deduct 1 credit + log usage
    - Idempotent: UNIQUE constraint on script_id prevents double-counting
    - Non-blocking: analysis proceeds even if tracking fails
    
    Returns:
        {'tracked': bool, 'credit_deducted': bool, 'remaining_credits': int | None, 'error': str | None}
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        # Check if this script has already been tracked (avoid duplicate work)
        existing = supabase.table('script_credit_usage') \
            .select('id') \
            .eq('script_id', script_id) \
            .execute()
        
        if existing.data and len(existing.data) > 0:
            print(f"[Credits] Script {script_id} already tracked for user {user_id}")
            return {
                'tracked': True,
                'credit_deducted': False,
                'remaining_credits': None,
                'error': None
            }
        
        # Check if user is an active subscriber ($49/mo unlimited model)
        from services.subscription_service import get_subscription_status
        sub_status = get_subscription_status(user_id)
        is_active_subscriber = sub_status.get('status') == 'active'
        
        credit_deducted = False
        
        if not is_active_subscriber:
            # Legacy credit user — try to deduct via atomic DB function
            try:
                result = supabase.rpc('deduct_script_credit', {
                    'p_user_id': user_id,
                    'p_script_id': script_id,
                    'p_script_name': script_name
                }).execute()
                
                credit_deducted = bool(result.data)
                if credit_deducted:
                    print(f"[Credits] Deducted 1 credit for script '{script_name}' (legacy user: {user_id})")
            except Exception as rpc_err:
                print(f"[Credits] RPC deduct failed (may be duplicate): {rpc_err}")
        
        # Log usage for all users (subscribers and legacy) if not already done by RPC
        if not credit_deducted:
            try:
                supabase.table('script_credit_usage').insert({
                    'user_id': user_id,
                    'script_id': script_id,
                    'script_name': script_name,
                    'credits_used': 1  # 1 breakdown used (tracking only for subscribers)
                }).execute()
                print(f"[Credits] Tracked breakdown for script '{script_name}' (user: {user_id}, subscriber: {is_active_subscriber})")
            except Exception as insert_err:
                if 'unique_credit_per_script' in str(insert_err).lower() or 'duplicate' in str(insert_err).lower():
                    print(f"[Credits] Script {script_id} usage already logged (concurrent insert)")
                else:
                    print(f"[Credits] Error logging usage: {insert_err}")
        
        # Get updated balance for response
        remaining = None
        try:
            balance = get_credit_balance(user_id)
            remaining = balance.get('credits', 0)
        except Exception:
            pass
        
        return {
            'tracked': True,
            'credit_deducted': credit_deducted,
            'remaining_credits': remaining,
            'error': None
        }
        
    except Exception as e:
        print(f"[Credits] Error tracking breakdown usage: {e}")
        return {
            'tracked': False,
            'credit_deducted': False,
            'remaining_credits': None,
            'error': str(e)
        }


def create_credit_purchase(
    user_id: str,
    email: str,
    package_type: str,
    payment_reference: Optional[str] = None,
    yoco_payment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a credit purchase record.
    
    Args:
        user_id: User's UUID
        email: User's email
        package_type: One of 'single', 'pack_5', 'pack_10', 'pack_25'
        payment_reference: Optional payment reference
        yoco_payment_id: Optional Yoco payment ID
    
    Returns:
        {'success': bool, 'purchase_id': str | None, 'error': str | None}
    """
    if package_type not in CREDIT_PACKAGES:
        return {
            'success': False,
            'purchase_id': None,
            'error': f'Invalid package type: {package_type}'
        }
    
    try:
        # Use admin client to bypass RLS - user is already authenticated via JWT middleware
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        package = CREDIT_PACKAGES[package_type]
        
        # Create purchase record
        result = supabase.table('script_credit_purchases').insert({
            'user_id': user_id,
            'email': email.lower().strip(),
            'credits_purchased': package['credits'],
            'package_type': package_type,
            'amount': package['price'],
            'currency': 'ZAR',
            'payment_reference': payment_reference,
            'yoco_payment_id': yoco_payment_id,
            'status': 'pending'
        }).execute()
        
        if result.data and len(result.data) > 0:
            return {
                'success': True,
                'purchase_id': result.data[0]['id'],
                'error': None
            }
        else:
            return {
                'success': False,
                'purchase_id': None,
                'error': 'Failed to create purchase record'
            }
            
    except Exception as e:
        print(f"Error creating credit purchase: {e}")
        return {
            'success': False,
            'purchase_id': None,
            'error': str(e)
        }


def complete_credit_purchase(purchase_id: str, yoco_payment_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Mark a purchase as completed and add credits to user's account.
    Called by webhooks, so uses admin client.
    
    Returns:
        {'success': bool, 'credits_added': int | None, 'error': str | None}
    """
    try:
        # Use admin client for webhook operations
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        # Get purchase details
        purchase_result = supabase.table('script_credit_purchases') \
            .select('user_id, credits_purchased, status') \
            .eq('id', purchase_id) \
            .single() \
            .execute()
        
        if not purchase_result.data:
            return {
                'success': False,
                'credits_added': None,
                'error': 'Purchase not found'
            }
        
        purchase = purchase_result.data
        
        if purchase['status'] == 'completed':
            return {
                'success': False,
                'credits_added': None,
                'error': 'Purchase already completed'
            }
        
        # Add credits using database function
        result = add_credits_after_purchase(
            purchase['user_id'],
            purchase['credits_purchased'],
            purchase_id
        )
        
        if result['success']:
            # Update payment ID if provided
            if yoco_payment_id:
                supabase.table('script_credit_purchases') \
                    .update({
                        'yoco_payment_id': yoco_payment_id,
                        'paid_at': datetime.now().isoformat()
                    }) \
                    .eq('id', purchase_id) \
                    .execute()
            
            return {
                'success': True,
                'credits_added': purchase['credits_purchased'],
                'error': None
            }
        else:
            return result
            
    except Exception as e:
        print(f"Error completing credit purchase: {e}")
        return {
            'success': False,
            'credits_added': None,
            'error': str(e)
        }


def get_purchase_history(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get user's credit purchase history.
    
    Returns:
        List of purchase records
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('script_credit_purchases') \
            .select('id, package_type, credits_purchased, amount, status, created_at, paid_at') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .limit(limit) \
            .execute()
        
        return result.data or []
        
    except Exception as e:
        print(f"Error getting purchase history: {e}")
        return []


def get_credit_packages() -> Dict[str, Dict[str, Any]]:
    """
    Get all available credit packages with pricing.
    
    Returns:
        Dictionary of package configurations
    """
    return CREDIT_PACKAGES


def grant_legacy_credits(user_id: str, credits: int = 10) -> Dict[str, Any]:
    """
    Grant credits to legacy beta users (existing users before credit system).
    Admin operation - uses service role key.
    
    Args:
        user_id: User's UUID
        credits: Number of credits to grant (default: 10)
    
    Returns:
        {'success': bool, 'credits_granted': int | None, 'error': str | None}
    """
    try:
        # Use admin client for admin operations
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        # Update profile with legacy credits
        result = supabase.table('profiles') \
            .update({
                'script_credits': credits,
                'total_scripts_purchased': credits,
                'is_legacy_beta': True
            }) \
            .eq('id', user_id) \
            .execute()
        
        if result.data:
            return {
                'success': True,
                'credits_granted': credits,
                'error': None
            }
        else:
            return {
                'success': False,
                'credits_granted': None,
                'error': 'Failed to grant credits'
            }
            
    except Exception as e:
        print(f"Error granting legacy credits: {e}")
        return {
            'success': False,
            'credits_granted': None,
            'error': str(e)
        }
