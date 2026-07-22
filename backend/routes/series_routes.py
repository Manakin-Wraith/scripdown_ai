"""
Series / Season / Episode grouping routes (Phase 1 -- grouping and
reporting layer only).

A series groups seasons; a season groups episode scripts. Purely
organizational on top of the existing single-script model -- no changes
to upload, parsing, AI analysis, or entitlement/billing. Access to a
season/episode list is inherited per-episode from the caller's existing
script role (owner or a script_members row) via get_script_role -- there
is no separate series-level permission system for READING episode data.

Series/season STRUCTURE (creating seasons, moving episodes) is gated on
series ownership: only the user who created a series can add seasons to
it or move a script into/out of one of its seasons. This is stricter than
the read path (which any team member with episode access can see) and
mirrors how script structure changes (e.g. deleting a script) are
owner-gated elsewhere in this codebase.
"""
from flask import Blueprint, request, jsonify
from db.supabase_client import get_supabase_admin, fetch_single
from middleware.auth import require_auth, get_user_id
from middleware.authorization import get_script_role, SCRIPT_NOT_FOUND, require_script_role

series_bp = Blueprint('series', __name__)


def _get_series(supabase, series_id):
    return fetch_single(
        supabase.table('series').select('*').eq('id', series_id).single()
    )


def _user_owns_series(supabase, series_id, user_id):
    series = _get_series(supabase, series_id)
    return bool(series and series.get('owner_id') == user_id)


@series_bp.route('/api/series', methods=['POST'])
@require_auth
def create_series():
    """
    Create a series, plus its first season.

    Body: {"title": "Show Name", "season_number": 1, "season_title": null}
    season_number/season_title are optional -- default to 1 / None.
    """
    try:
        supabase = get_supabase_admin()
        user_id = get_user_id()
        data = request.get_json(silent=True) or {}
        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({'error': 'title is required'}), 400

        season_number = data.get('season_number') or 1
        season_title = data.get('season_title')

        series_result = supabase.table('series').insert({
            'owner_id': user_id, 'title': title,
        }).execute()
        if not series_result.data:
            return jsonify({'error': 'Failed to create series'}), 500
        series = series_result.data[0]

        season_result = supabase.table('seasons').insert({
            'series_id': series['id'], 'season_number': season_number,
            'title': season_title,
        }).execute()
        season = season_result.data[0] if season_result.data else None

        return jsonify({'series': series, 'season': season}), 201
    except Exception as e:
        print(f"Error creating series: {e}")
        return jsonify({'error': str(e)}), 500


@series_bp.route('/api/series', methods=['GET'])
@require_auth
def list_series():
    """
    List series the caller owns.

    Note: this is intentionally owner-scoped, not "every series I have an
    accessible episode in" -- discovery of someone else's series isn't a
    surface this phase builds. A team member who has episode access via a
    direct link still gets correctly-filtered season/episode/cast views
    (see list_seasons, list_episodes, get_season_cast below); they just
    won't see that series in their own /api/series listing.
    """
    try:
        supabase = get_supabase_admin()
        user_id = get_user_id()
        result = supabase.table('series').select('*').eq('owner_id', user_id).execute()
        return jsonify({'series': result.data or []})
    except Exception as e:
        print(f"Error listing series: {e}")
        return jsonify({'error': str(e)}), 500


@series_bp.route('/api/series/<series_id>/seasons', methods=['POST'])
@require_auth
def create_season(series_id):
    """Add a season to a series. Series-owner only."""
    try:
        supabase = get_supabase_admin()
        user_id = get_user_id()

        if not _user_owns_series(supabase, series_id, user_id):
            return jsonify({'error': 'Insufficient permissions'}), 403

        data = request.get_json(silent=True) or {}
        season_number = data.get('season_number')
        if not season_number:
            return jsonify({'error': 'season_number is required'}), 400

        result = supabase.table('seasons').insert({
            'series_id': series_id, 'season_number': season_number,
            'title': data.get('title'),
        }).execute()
        if not result.data:
            return jsonify({'error': 'Failed to create season'}), 500

        return jsonify({'season': result.data[0]}), 201
    except Exception as e:
        print(f"Error creating season: {e}")
        return jsonify({'error': str(e)}), 500


@series_bp.route('/api/series/<series_id>/seasons', methods=['GET'])
@require_auth
def list_seasons(series_id):
    """
    List a series' seasons, ordered by season_number.

    Visible to the series owner, or to anyone with viewer-or-above access
    to at least one script inside any of this series' seasons -- so a team
    member following a shared season link can still see season structure.
    """
    try:
        supabase = get_supabase_admin()
        user_id = get_user_id()

        series = _get_series(supabase, series_id)
        if not series:
            return jsonify({'error': 'Series not found'}), 404

        is_owner = series.get('owner_id') == user_id
        seasons_result = supabase.table('seasons').select('*').eq(
            'series_id', series_id
        ).order('season_number').execute()
        seasons = seasons_result.data or []

        if not is_owner:
            visible = False
            for season in seasons:
                scripts_result = supabase.table('scripts').select('id').eq(
                    'season_id', season['id']
                ).execute()
                for script in (scripts_result.data or []):
                    role = get_script_role(script['id'], user_id)
                    if role not in (None, SCRIPT_NOT_FOUND):
                        visible = True
                        break
                if visible:
                    break
            if not visible:
                return jsonify({'error': 'Insufficient permissions'}), 403

        return jsonify({'seasons': seasons})
    except Exception as e:
        print(f"Error listing seasons: {e}")
        return jsonify({'error': str(e)}), 500


def _visible_episode_scripts(supabase, season_id, user_id):
    """Scripts in this season, filtered to ones the caller can access,
    ordered by episode_number. Shared by list_episodes and (Task 4's)
    get_season_cast."""
    scripts_result = supabase.table('scripts').select('*').eq(
        'season_id', season_id
    ).order('episode_number').execute()

    visible = []
    for script in (scripts_result.data or []):
        role = get_script_role(script['id'], user_id)
        if role not in (None, SCRIPT_NOT_FOUND):
            visible.append(script)
    return visible


@series_bp.route('/api/seasons/<season_id>/episodes', methods=['GET'])
@require_auth
def list_episodes(season_id):
    """Episodes in a season, filtered to the caller's accessible scripts."""
    try:
        supabase = get_supabase_admin()
        user_id = get_user_id()
        episodes = _visible_episode_scripts(supabase, season_id, user_id)
        return jsonify({'episodes': episodes})
    except Exception as e:
        print(f"Error listing episodes: {e}")
        return jsonify({'error': str(e)}), 500


@series_bp.route('/api/scripts/<script_id>/season', methods=['PATCH'])
@require_auth
@require_script_role('member')
def update_script_season(script_id):
    """
    Assign, reassign, or clear a script's season/episode-number.

    Body: {"season_id": "<uuid>" | null, "episode_number": 3}
    season_id: null clears the assignment (episode_number is cleared too,
    regardless of what's in the body, since an episode number without a
    season is meaningless).

    Requires @require_script_role('member') on the script (the caller must
    already have at least edit access to it) AND ownership of the target
    season's series -- you can't move your own script into someone else's
    series just because you can edit the script.
    """
    try:
        supabase = get_supabase_admin()
        user_id = get_user_id()
        data = request.get_json(silent=True) or {}

        season_id = data.get('season_id')
        if season_id is None:
            supabase.table('scripts').update({
                'season_id': None, 'episode_number': None,
            }).eq('id', script_id).execute()
            return jsonify({'success': True, 'season_id': None, 'episode_number': None})

        season = fetch_single(supabase.table('seasons').select('*').eq('id', season_id).single())
        if not season:
            return jsonify({'error': 'Season not found'}), 404

        if not _user_owns_series(supabase, season['series_id'], user_id):
            return jsonify({'error': 'Insufficient permissions'}), 403

        episode_number = data.get('episode_number')
        supabase.table('scripts').update({
            'season_id': season_id, 'episode_number': episode_number,
        }).eq('id', script_id).execute()

        return jsonify({'success': True, 'season_id': season_id, 'episode_number': episode_number})
    except Exception as e:
        print(f"Error updating script season: {e}")
        return jsonify({'error': str(e)}), 500
