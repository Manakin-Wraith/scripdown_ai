"""Access control for report endpoints: owner-or-member script access.

The report blueprint uses the Supabase service-role client (RLS bypassed), so
these functions are the app-layer authorization for report data.
"""


def script_access(client, script_id, user_id):
    """Return 'ok' | 'forbidden' | 'not_found' for (script_id, user_id).

    'ok' if the user owns the script (scripts.user_id) or is a member
    (script_members row). 'not_found' if the script does not exist.
    """
    res = client.table('scripts').select('user_id').eq('id', script_id).limit(1).execute()
    if not res.data:
        return 'not_found'
    if res.data[0].get('user_id') == user_id:
        return 'ok'
    member = (
        client.table('script_members').select('id')
        .eq('script_id', script_id).eq('user_id', user_id).limit(1).execute()
    )
    return 'ok' if member.data else 'forbidden'


def report_script_id(client, report_id):
    """Return the report's script_id, or None if the report does not exist."""
    res = client.table('reports').select('script_id').eq('id', report_id).limit(1).execute()
    return res.data[0]['script_id'] if res.data else None
