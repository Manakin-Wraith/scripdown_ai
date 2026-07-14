"""
Timeline Segment Routes for SlateOne (ScripDown AI)

CRUD for off-timeline flashback/montage segments plus scene attach/detach.
Every mutation ends with a story-day recalc so the numeric timeline and
total_story_days stay correct.

The backend uses the Supabase service-role client (RLS bypassed), so every
endpoint authorizes the caller against the target script at the app layer via
script_access() — the same owner-or-member gate the report blueprint uses.
Segment-scoped routes resolve the script server-side from the segment row
rather than trusting a client-supplied script_id. See
docs/superpowers/specs/2026-07-14-timeline-segments-design.md
"""

from flask import Blueprint, request, jsonify
from middleware.auth import require_auth, get_user_id
from db.supabase_client import db
from services.story_day_service import recalculate_story_days
from utils.report_access import script_access

segment_bp = Blueprint('segments', __name__)

VALID_TYPES = {'FLASHBACK', 'DREAM', 'FANTASY', 'MONTAGE', 'TITLE_CARD'}


def _check_script(script_id):
    """Guard: None if the current user may access script_id, else an error response."""
    status = script_access(db.client, script_id, get_user_id())
    if status == 'not_found':
        return jsonify({'error': 'Script not found'}), 404
    if status == 'forbidden':
        return jsonify({'error': 'Not authorized'}), 403
    return None


def _load_segment_or_error(segment_id):
    """Return (segment, None) if it exists and the user may access its script,
    else (None, error_response)."""
    segment = db.get_timeline_segment(segment_id)
    if not segment:
        return None, (jsonify({'error': 'Segment not found'}), 404)
    denied = _check_script(segment['script_id'])
    if denied:
        return None, denied
    return segment, None


@segment_bp.route('/api/scripts/<script_id>/segments', methods=['GET'])
@require_auth
def list_segments(script_id):
    denied = _check_script(script_id)
    if denied:
        return denied
    segments = db.get_timeline_segments(script_id)
    return jsonify({'segments': segments}), 200


@segment_bp.route('/api/scripts/<script_id>/segments', methods=['POST'])
@require_auth
def create_segment(script_id):
    denied = _check_script(script_id)
    if denied:
        return denied
    body = request.get_json() or {}
    name = (body.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    segment_type = body.get('segment_type', 'FLASHBACK')
    if segment_type not in VALID_TYPES:
        return jsonify({'error': f'invalid segment_type: {segment_type}'}), 400
    segment = db.create_timeline_segment(
        script_id=script_id,
        name=name,
        segment_type=segment_type,
        color=body.get('color'),
        display_order=body.get('display_order', 0),
    )
    return jsonify({'segment': segment}), 201


@segment_bp.route('/api/segments/<segment_id>', methods=['PATCH'])
@require_auth
def update_segment(segment_id):
    _segment, denied = _load_segment_or_error(segment_id)
    if denied:
        return denied
    body = request.get_json() or {}
    allowed = {k: body[k] for k in ('name', 'segment_type', 'color', 'display_order')
               if k in body}
    if 'segment_type' in allowed and allowed['segment_type'] not in VALID_TYPES:
        return jsonify({'error': 'invalid segment_type'}), 400
    if not allowed:
        return jsonify({'error': 'no updatable fields provided'}), 400
    segment = db.update_timeline_segment(segment_id, **allowed)
    return jsonify({'segment': segment}), 200


@segment_bp.route('/api/segments/<segment_id>', methods=['DELETE'])
@require_auth
def delete_segment(segment_id):
    segment, denied = _load_segment_or_error(segment_id)
    if denied:
        return denied
    script_id = segment['script_id']
    db.delete_timeline_segment(segment_id)
    # Member scenes fell back to the timeline via ON DELETE SET NULL.
    recalculate_story_days(script_id, start_from_order=0)
    return jsonify({'success': True}), 200


@segment_bp.route('/api/segments/<segment_id>/scenes', methods=['POST'])
@require_auth
def attach_scenes(segment_id):
    segment, denied = _load_segment_or_error(segment_id)
    if denied:
        return denied
    script_id = segment['script_id']
    body = request.get_json() or {}
    scene_ids = body.get('scene_ids') or []
    if not scene_ids:
        return jsonify({'error': 'scene_ids is required'}), 400
    # Validate every scene belongs to this segment's script BEFORE mutating any.
    for scene_id in scene_ids:
        if db.get_scene_script_id(scene_id) != script_id:
            return jsonify({'error': f'scene {scene_id} does not belong to this script'}), 400
    for scene_id in scene_ids:
        # Joining a segment clears manual day flags and the numeric day.
        db.update_scene(
            scene_id,
            segment_id=segment_id,
            story_day=None,
            is_new_story_day=False,
            story_day_is_locked=False,
        )
    recalculate_story_days(script_id, start_from_order=0)
    return jsonify({'success': True}), 200


@segment_bp.route('/api/segments/<segment_id>/scenes/<scene_id>', methods=['DELETE'])
@require_auth
def detach_scene(segment_id, scene_id):
    segment, denied = _load_segment_or_error(segment_id)
    if denied:
        return denied
    script_id = segment['script_id']
    if db.get_scene_script_id(scene_id) != script_id:
        return jsonify({'error': 'scene does not belong to this script'}), 400
    db.update_scene(scene_id, segment_id=None)
    recalculate_story_days(script_id, start_from_order=0)
    return jsonify({'success': True}), 200
