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
