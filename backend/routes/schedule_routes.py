"""
Shooting Schedule Routes for SlateOne (ScripDown AI)

CRUD endpoints for shooting schedules, shooting days, and scene assignments.
Supports the "Add to Schedule" workflow from the Zoomable Stripboard.
"""

import os
from flask import Blueprint, request, jsonify
from middleware.auth import require_auth, optional_auth, get_user_id
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '').strip()
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '').strip()

supabase_key = SUPABASE_SERVICE_KEY if SUPABASE_SERVICE_KEY else SUPABASE_ANON_KEY
supabase = None
if SUPABASE_URL and supabase_key:
    try:
        supabase = create_client(SUPABASE_URL, supabase_key)
    except Exception as e:
        print(f"Schedule routes: Supabase connection failed: {e}")

schedule_bp = Blueprint('schedule', __name__)


# ============================================
# Schedules
# ============================================

@schedule_bp.route('/api/scripts/<script_id>/schedules', methods=['GET'])
@optional_auth
def get_schedules(script_id):
    """List all shooting schedules for a script."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        result = supabase.table('shooting_schedules') \
            .select('*') \
            .eq('script_id', script_id) \
            .order('created_at', desc=False) \
            .execute()
        return jsonify({'schedules': result.data or []}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/scripts/<script_id>/schedules', methods=['POST'])
@optional_auth
def create_schedule(script_id):
    """Create a new shooting schedule for a script."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        body = request.get_json() or {}
        user_id = get_user_id()

        data = {
            'script_id': script_id,
            'created_by': user_id,
            'name': body.get('name', 'Schedule 1'),
            'status': 'draft',
        }
        if body.get('start_date'):
            data['start_date'] = body['start_date']

        result = supabase.table('shooting_schedules').insert(data).execute()
        schedule = result.data[0] if result.data else None
        return jsonify({'schedule': schedule}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/schedules/<schedule_id>', methods=['PATCH'])
@optional_auth
def update_schedule(schedule_id):
    """Update a schedule (name, status, start_date, notes)."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        body = request.get_json() or {}
        allowed = {'name', 'status', 'start_date', 'notes'}
        updates = {k: v for k, v in body.items() if k in allowed}
        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400

        result = supabase.table('shooting_schedules') \
            .update(updates).eq('id', schedule_id).execute()
        return jsonify({'schedule': result.data[0] if result.data else None}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/schedules/<schedule_id>', methods=['DELETE'])
@optional_auth
def delete_schedule(schedule_id):
    """Delete a schedule and all its days/scenes (CASCADE)."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        supabase.table('shooting_schedules').delete().eq('id', schedule_id).execute()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# Shooting Days
# ============================================

@schedule_bp.route('/api/schedules/<schedule_id>/days', methods=['GET'])
@optional_auth
def get_shooting_days(schedule_id):
    """List all shooting days for a schedule, with their scenes."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        days_result = supabase.table('shooting_days') \
            .select('*') \
            .eq('schedule_id', schedule_id) \
            .order('day_number', desc=False) \
            .execute()

        days = days_result.data or []

        # Fetch scenes for each day
        for day in days:
            scenes_result = supabase.table('shooting_day_scenes') \
                .select('*, scenes(id, scene_number, setting, int_ext, time_of_day, story_day, characters, page_length_eighths, scene_text, page_start, page_end)') \
                .eq('shooting_day_id', day['id']) \
                .order('sort_order', desc=False) \
                .execute()
            day['scenes'] = scenes_result.data or []

        return jsonify({'days': days}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/schedules/<schedule_id>/days', methods=['POST'])
@optional_auth
def create_shooting_day(schedule_id):
    """Create a new shooting day, optionally with initial scenes."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        body = request.get_json() or {}

        # Auto-increment day_number
        existing = supabase.table('shooting_days') \
            .select('day_number') \
            .eq('schedule_id', schedule_id) \
            .order('day_number', desc=True) \
            .limit(1) \
            .execute()
        next_num = (existing.data[0]['day_number'] + 1) if existing.data else 1

        day_data = {
            'schedule_id': schedule_id,
            'day_number': body.get('day_number', next_num),
            'notes': body.get('notes', ''),
            'color_label': body.get('color_label', 'default'),
            'status': 'draft',
        }
        if body.get('shoot_date'):
            day_data['shoot_date'] = body['shoot_date']

        day_result = supabase.table('shooting_days').insert(day_data).execute()
        day = day_result.data[0] if day_result.data else None

        if not day:
            return jsonify({'error': 'Failed to create shooting day'}), 500

        # Add initial scenes if provided
        scene_ids = body.get('scene_ids', [])
        added_scenes = []
        if scene_ids and day:
            rows = [
                {
                    'shooting_day_id': day['id'],
                    'scene_id': sid,
                    'sort_order': i,
                }
                for i, sid in enumerate(scene_ids)
            ]
            scenes_result = supabase.table('shooting_day_scenes').insert(rows).execute()
            added_scenes = scenes_result.data or []

        day['scenes'] = added_scenes
        return jsonify({'day': day}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/shooting-days/<day_id>', methods=['PATCH'])
@optional_auth
def update_shooting_day(day_id):
    """Update a shooting day (notes, date, status, color)."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        body = request.get_json() or {}
        allowed = {'day_number', 'shoot_date', 'notes', 'color_label', 'status'}
        updates = {k: v for k, v in body.items() if k in allowed}
        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400

        result = supabase.table('shooting_days') \
            .update(updates).eq('id', day_id).execute()
        return jsonify({'day': result.data[0] if result.data else None}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/shooting-days/<day_id>', methods=['DELETE'])
@optional_auth
def delete_shooting_day(day_id):
    """Delete a shooting day (scenes are cascade-deleted from the join table)."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        supabase.table('shooting_days').delete().eq('id', day_id).execute()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# Add / Remove Scenes from Days
# ============================================

@schedule_bp.route('/api/shooting-days/<day_id>/scenes', methods=['POST'])
@optional_auth
def add_scenes_to_day(day_id):
    """Add one or more scenes to a shooting day."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        body = request.get_json() or {}
        scene_ids = body.get('scene_ids', [])
        if not scene_ids:
            return jsonify({'error': 'scene_ids required'}), 400

        # Get current max sort_order
        existing = supabase.table('shooting_day_scenes') \
            .select('sort_order') \
            .eq('shooting_day_id', day_id) \
            .order('sort_order', desc=True) \
            .limit(1) \
            .execute()
        next_order = (existing.data[0]['sort_order'] + 1) if existing.data else 0

        rows = [
            {
                'shooting_day_id': day_id,
                'scene_id': sid,
                'sort_order': next_order + i,
            }
            for i, sid in enumerate(scene_ids)
        ]

        result = supabase.table('shooting_day_scenes').insert(rows).execute()
        return jsonify({'scenes': result.data or []}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/shooting-days/<day_id>/scenes/<scene_id>', methods=['DELETE'])
@optional_auth
def remove_scene_from_day(day_id, scene_id):
    """Remove a scene from a shooting day."""
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        supabase.table('shooting_day_scenes') \
            .delete() \
            .eq('shooting_day_id', day_id) \
            .eq('scene_id', scene_id) \
            .execute()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# Reorder & Move Scenes
# ============================================

@schedule_bp.route('/api/shooting-days/<day_id>/scenes/reorder', methods=['PATCH'])
@optional_auth
def reorder_day_scenes(day_id):
    """
    Reorder scenes within a shooting day.
    Body: { scene_ids: ["id1", "id2", ...] }  — new order
    """
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        body = request.get_json() or {}
        scene_ids = body.get('scene_ids', [])
        if not scene_ids:
            return jsonify({'error': 'scene_ids required'}), 400

        for i, sid in enumerate(scene_ids):
            supabase.table('shooting_day_scenes') \
                .update({'sort_order': i}) \
                .eq('shooting_day_id', day_id) \
                .eq('scene_id', sid) \
                .execute()

        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/api/shooting-days/<from_day_id>/scenes/<scene_id>/move', methods=['POST'])
@optional_auth
def move_scene_to_day(from_day_id, scene_id):
    """
    Move a scene from one day to another (and optionally set its position).
    Body: { target_day_id: "...", target_index: 0 }
    """
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        body = request.get_json() or {}
        target_day_id = body.get('target_day_id')
        target_index = body.get('target_index')
        if not target_day_id:
            return jsonify({'error': 'target_day_id required'}), 400

        # Remove from source day
        supabase.table('shooting_day_scenes') \
            .delete() \
            .eq('shooting_day_id', from_day_id) \
            .eq('scene_id', scene_id) \
            .execute()

        # Get current scenes in target day
        target_scenes = supabase.table('shooting_day_scenes') \
            .select('scene_id, sort_order') \
            .eq('shooting_day_id', target_day_id) \
            .order('sort_order', desc=False) \
            .execute()
        existing_ids = [s['scene_id'] for s in (target_scenes.data or [])]

        # Determine insert position
        if target_index is None or target_index >= len(existing_ids):
            new_order = len(existing_ids)
        else:
            new_order = max(0, target_index)

        # Insert at position
        existing_ids.insert(new_order, scene_id)

        # Re-number all sort_orders in target day
        for i, sid in enumerate(existing_ids):
            if sid == scene_id:
                supabase.table('shooting_day_scenes') \
                    .insert({
                        'shooting_day_id': target_day_id,
                        'scene_id': scene_id,
                        'sort_order': i,
                    }).execute()
            else:
                supabase.table('shooting_day_scenes') \
                    .update({'sort_order': i}) \
                    .eq('shooting_day_id', target_day_id) \
                    .eq('scene_id', sid) \
                    .execute()

        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# Quick Action: Add selected scenes to schedule
# (creates schedule + day if needed)
# ============================================

@schedule_bp.route('/api/scripts/<script_id>/schedule/quick-add', methods=['POST'])
@optional_auth
def quick_add_to_schedule(script_id):
    """
    Quick-add selected scenes to a schedule.
    
    Body: {
        scene_ids: [...],
        schedule_id: "..." | null,      // null = create new schedule
        shooting_day_id: "..." | null,  // null = create new day
        day_label: "Day 1"              // optional label for new day
    }
    """
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 500
    try:
        body = request.get_json() or {}
        scene_ids = body.get('scene_ids', [])
        if not scene_ids:
            return jsonify({'error': 'scene_ids required'}), 400

        user_id = get_user_id()
        schedule_id = body.get('schedule_id')
        day_id = body.get('shooting_day_id')

        # Create schedule if needed
        if not schedule_id:
            # Count existing schedules for naming
            count_result = supabase.table('shooting_schedules') \
                .select('id', count='exact') \
                .eq('script_id', script_id) \
                .execute()
            count = count_result.count if hasattr(count_result, 'count') and count_result.count else len(count_result.data or [])

            schedule_data = {
                'script_id': script_id,
                'created_by': user_id,
                'name': f'Schedule {count + 1}',
                'status': 'draft',
            }
            sched_result = supabase.table('shooting_schedules').insert(schedule_data).execute()
            schedule_id = sched_result.data[0]['id'] if sched_result.data else None
            if not schedule_id:
                return jsonify({'error': 'Failed to create schedule'}), 500

        # Create shooting day if needed
        if not day_id:
            existing_days = supabase.table('shooting_days') \
                .select('day_number') \
                .eq('schedule_id', schedule_id) \
                .order('day_number', desc=True) \
                .limit(1) \
                .execute()
            next_num = (existing_days.data[0]['day_number'] + 1) if existing_days.data else 1

            day_data = {
                'schedule_id': schedule_id,
                'day_number': next_num,
                'notes': body.get('day_label', ''),
                'status': 'draft',
            }
            day_result = supabase.table('shooting_days').insert(day_data).execute()
            day_id = day_result.data[0]['id'] if day_result.data else None
            if not day_id:
                return jsonify({'error': 'Failed to create shooting day'}), 500

        # Add scenes to the day
        existing_scenes = supabase.table('shooting_day_scenes') \
            .select('sort_order, scene_id') \
            .eq('shooting_day_id', day_id) \
            .order('sort_order', desc=True) \
            .execute()
        next_order = (existing_scenes.data[0]['sort_order'] + 1) if existing_scenes.data else 0

        # Filter out scenes already in this day
        existing_scene_ids = {s['scene_id'] for s in (existing_scenes.data or [])}
        new_scene_ids = [sid for sid in scene_ids if sid not in existing_scene_ids]

        added = []
        if new_scene_ids:
            rows = [
                {
                    'shooting_day_id': day_id,
                    'scene_id': sid,
                    'sort_order': next_order + i,
                }
                for i, sid in enumerate(new_scene_ids)
            ]
            add_result = supabase.table('shooting_day_scenes').insert(rows).execute()
            added = add_result.data or []

        return jsonify({
            'schedule_id': schedule_id,
            'shooting_day_id': day_id,
            'added_count': len(added),
            'skipped_count': len(scene_ids) - len(new_scene_ids),
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
