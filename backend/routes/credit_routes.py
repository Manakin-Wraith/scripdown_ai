"""
Credit Routes
API endpoints for script credit management and purchases.
"""

from flask import Blueprint, request, jsonify, g
from services.credit_service import (
    get_credit_balance,
    can_upload_with_credits,
    deduct_credit_for_script,
    create_credit_purchase,
    complete_credit_purchase,
    get_purchase_history,
    get_credit_packages,
    grant_legacy_credits
)
from middleware.auth import require_auth, get_user_id

credit_bp = Blueprint('credits', __name__, url_prefix='/api/credits')


@credit_bp.route('/balance', methods=['GET'])
@require_auth
def get_balance():
    """Get user's current credit balance and stats."""
    user_id = get_user_id()
    
    balance = get_credit_balance(user_id)
    
    return jsonify({
        'success': True,
        'balance': balance
    }), 200


@credit_bp.route('/can-upload', methods=['GET'])
@require_auth
def check_can_upload():
    """Check if user can upload a script with current credits."""
    user_id = get_user_id()
    
    can_upload, message = can_upload_with_credits(user_id)
    
    return jsonify({
        'success': True,
        'can_upload': can_upload,
        'message': message
    }), 200


@credit_bp.route('/deduct', methods=['POST'])
@require_auth
def deduct_credit():
    """
    Deduct 1 credit for a script upload.
    Body: { script_id, script_name }
    """
    user_id = get_user_id()
    data = request.get_json()
    
    script_id = data.get('script_id')
    script_name = data.get('script_name', 'Untitled Script')
    
    if not script_id:
        return jsonify({
            'success': False,
            'error': 'script_id is required'
        }), 400
    
    result = deduct_credit_for_script(user_id, script_id, script_name)
    
    if result['success']:
        return jsonify({
            'success': True,
            'remaining_credits': result['remaining_credits']
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result['error']
        }), 400


@credit_bp.route('/packages', methods=['GET'])
def get_packages():
    """Get available credit packages with pricing."""
    packages = get_credit_packages()
    
    return jsonify({
        'success': True,
        'packages': packages
    }), 200


@credit_bp.route('/purchase/create', methods=['POST'])
@require_auth
def create_purchase():
    """
    Create a credit purchase record.
    Body: { package_type, payment_reference?, yoco_payment_id? }
    """
    user_id = get_user_id()
    data = request.get_json()
    
    package_type = data.get('package_type')
    payment_reference = data.get('payment_reference')
    yoco_payment_id = data.get('yoco_payment_id')
    
    if not package_type:
        return jsonify({
            'success': False,
            'error': 'package_type is required'
        }), 400
    
    # Get user email from g.current_user (set by auth middleware)
    user = getattr(g, 'current_user', None)
    email = user.get('email') if user else None
    if not email:
        return jsonify({
            'success': False,
            'error': 'User email not found'
        }), 400
    
    result = create_credit_purchase(
        user_id,
        email,
        package_type,
        payment_reference,
        yoco_payment_id
    )
    
    if result['success']:
        return jsonify({
            'success': True,
            'purchase_id': result['purchase_id']
        }), 201
    else:
        return jsonify({
            'success': False,
            'error': result['error']
        }), 400


@credit_bp.route('/purchase/<purchase_id>/complete', methods=['POST'])
def complete_purchase(purchase_id):
    """
    Complete a purchase and add credits to user account.
    This endpoint can be called by webhooks (no auth required).
    Body: { yoco_payment_id? }
    """
    data = request.get_json() or {}
    yoco_payment_id = data.get('yoco_payment_id')
    
    result = complete_credit_purchase(purchase_id, yoco_payment_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'credits_added': result['credits_added']
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result['error']
        }), 400


@credit_bp.route('/purchase/history', methods=['GET'])
@require_auth
def get_history():
    """Get user's credit purchase history."""
    user_id = get_user_id()
    limit = request.args.get('limit', 20, type=int)
    
    history = get_purchase_history(user_id, limit)
    
    return jsonify({
        'success': True,
        'purchases': history
    }), 200


@credit_bp.route('/admin/grant-legacy', methods=['POST'])
@require_auth
def grant_legacy():
    """
    Admin endpoint to grant legacy credits to existing users.
    Body: { user_id, credits? }
    """
    # TODO: Add admin role check
    data = request.get_json()
    
    target_user_id = data.get('user_id')
    credits = data.get('credits', 10)
    
    if not target_user_id:
        return jsonify({
            'success': False,
            'error': 'user_id is required'
        }), 400
    
    result = grant_legacy_credits(target_user_id, credits)
    
    if result['success']:
        return jsonify({
            'success': True,
            'credits_granted': result['credits_granted']
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': result['error']
        }), 400
