"""
Authentication Middleware for SlateOne Backend

Provides JWT verification using Supabase Auth.
"""

import os
import logging
from functools import wraps
from flask import request, jsonify, g
import jwt
from jwt import PyJWKClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Supabase JWT configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET')  # Legacy HS256 fallback
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')

# JWKS endpoint for ECC P-256 (ES256) key verification
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else None
_jwks_client = None

# For development - allow bypassing auth
DEV_MODE = os.getenv('FLASK_ENV') == 'development'
DEV_USER_ID = os.getenv('DEV_USER_ID', '00000000-0000-0000-0000-000000000001')


def get_jwks_client():
    """
    Get or create the cached JWKS client for Supabase token verification.
    Fetches public keys from Supabase's JWKS endpoint.
    """
    global _jwks_client
    if _jwks_client is None and JWKS_URL:
        _jwks_client = PyJWKClient(JWKS_URL, cache_keys=True, lifespan=300)
    return _jwks_client


def verify_supabase_token(token: str) -> dict:
    """
    Verify a Supabase JWT token and return the payload.
    
    Supports both:
    - ECC P-256 (ES256) — new Supabase JWT signing keys (verified via JWKS)
    - HS256 — legacy shared secret fallback
    
    Args:
        token: The JWT token from Authorization header
        
    Returns:
        dict: The decoded token payload containing user info
        
    Raises:
        jwt.InvalidTokenError: If token is invalid or expired
    """
    # Strategy 1: JWKS-based verification (ECC P-256 / ES256)
    jwks_client = get_jwks_client()
    if jwks_client:
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "HS256"],
                audience="authenticated"
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.warning(f"JWKS verification failed, trying fallback: {e}")
    
    # Strategy 2: Legacy HS256 shared secret fallback
    if SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated"
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    # Strategy 3: Dev mode — decode without verification
    if DEV_MODE:
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception:
            pass
    
    raise ValueError("JWT verification failed. Ensure SUPABASE_URL is set for JWKS verification.")


def get_current_user():
    """
    Get the current authenticated user from the request context.
    
    Returns:
        dict: User info with 'id', 'email', 'role' etc.
        None: If no user is authenticated
    """
    return getattr(g, 'current_user', None)


def get_user_id():
    """
    Get the current user's ID.
    
    Returns:
        str: User ID or DEV_USER_ID in development mode
    """
    user = get_current_user()
    if user:
        return user.get('sub') or user.get('id')
    
    # Fallback for development
    if DEV_MODE:
        return DEV_USER_ID
    
    return None


def require_auth(f):
    """
    Decorator to require authentication for a route.
    
    Usage:
        @app.route('/api/protected')
        @require_auth
        def protected_route():
            user = get_current_user()
            return jsonify({'user_id': user['sub']})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            # In dev mode, allow requests without auth
            if DEV_MODE:
                g.current_user = {
                    'sub': DEV_USER_ID,
                    'email': 'dev@example.com',
                    'role': 'authenticated'
                }
                return f(*args, **kwargs)
            
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            # Verify the token
            payload = verify_supabase_token(token)
            
            # Store user info in Flask's g object
            g.current_user = payload
            
            return f(*args, **kwargs)
            
        except ValueError as e:
            # In dev mode, allow fallback
            if DEV_MODE:
                g.current_user = {
                    'sub': DEV_USER_ID,
                    'email': 'dev@example.com',
                    'role': 'authenticated'
                }
                return f(*args, **kwargs)
            
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            return jsonify({'error': f'Authentication failed: {str(e)}'}), 401
    
    return decorated_function


def optional_auth(f):
    """
    Decorator for routes where auth is optional.
    Sets g.current_user if token is valid, otherwise None.
    
    Usage:
        @app.route('/api/public')
        @optional_auth
        def public_route():
            user = get_current_user()
            if user:
                return jsonify({'message': f'Hello {user["email"]}'})
            return jsonify({'message': 'Hello anonymous'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = verify_supabase_token(token)
                g.current_user = payload
            except Exception:
                g.current_user = None
        else:
            g.current_user = None
            
            # In dev mode, set dev user
            if DEV_MODE:
                g.current_user = {
                    'sub': DEV_USER_ID,
                    'email': 'dev@example.com',
                    'role': 'authenticated'
                }
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_superuser(f):
    """
    Decorator to require superuser privileges for a route.
    Must be used with @require_auth.
    
    Usage:
        @app.route('/api/admin/analytics')
        @require_auth
        @require_superuser
        def admin_route():
            return jsonify({'message': 'Admin access granted'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from db.supabase_client import get_supabase_client
        
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        user_id = user.get('sub') or user.get('id')
        
        # In dev mode, allow superuser access
        if DEV_MODE:
            return f(*args, **kwargs)
        
        try:
            # Check if user has superuser flag
            supabase = get_supabase_client()
            result = supabase.table('profiles').select('is_superuser').eq('id', user_id).single().execute()
            
            if not result.data or not result.data.get('is_superuser'):
                return jsonify({'error': 'Superuser access required'}), 403
            
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({'error': f'Authorization check failed: {str(e)}'}), 500
    
    return decorated_function
