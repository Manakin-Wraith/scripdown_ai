"""
Story Day Service — Phase 1: Timeline Calculator

Provides sequential story day assignment and recalculation logic.
Triggered after AI enhancement, manual edits, scene reorder/split/merge.

Key design decisions:
- Sequential pass: iterates scenes in scene_order, incrementing day counter
- Respects locked days: if user locked "Day 3" on Scene 10, counter resets
- Handles timeline_code: FLASHBACK/DREAM scenes get labeled differently
- Idempotent: safe to re-run at any time
"""

from typing import Dict, Optional
from db.supabase_client import db


def recalculate_story_days(script_id: str, start_from_order: int = 0) -> Dict:
    """
    Sequential pass to assign story_day numbers based on is_new_story_day flags.
    
    Fetches all scenes from start_from_order onward.
    Respects manually locked days.
    Updates DB in batch.
    
    Triggers:
      1. After AI enhancement batch completes
      2. After user manually toggles "New Day" on a scene
      3. After user manually sets a story_day value
      4. After scene reorder / split / merge / add / delete
    
    Args:
        script_id: The script to recalculate
        start_from_order: Optimization — only recalculate from this scene_order onward.
                         Pass 0 to recalculate entire script.
    
    Returns:
        Summary dict with total_days, scenes_updated count.
    """
    scenes = db.get_scenes_ordered(script_id)
    
    if not scenes:
        print(f"[StoryDays] No scenes found for script {script_id}")
        return {'total_days': 0, 'scenes_updated': 0}
    
    # Determine starting day counter
    if start_from_order > 0:
        # Find the scene just before start_from_order to get its story_day
        for s in scenes:
            if s.get('scene_order', 0) == start_from_order - 1:
                current_day = s.get('story_day') or 1
                break
        else:
            current_day = 1
    else:
        current_day = 1
    
    scenes_to_update = []
    
    for i, scene in enumerate(scenes):
        scene_order = scene.get('scene_order', i + 1)
        
        # Skip scenes before start_from_order (they keep their existing values)
        if start_from_order > 0 and scene_order < start_from_order:
            continue
        
        # Respect locked days — if user locked this scene's story_day, reset counter
        if scene.get('story_day_is_locked') and scene.get('story_day') is not None:
            current_day = scene['story_day']
            # Still need to update the label in case timeline_code changed
            label = _build_label(current_day, scene.get('time_transition', ''), scene.get('timeline_code', 'PRESENT'))
            if scene.get('story_day_label') != label:
                scenes_to_update.append({
                    'id': scene['id'],
                    'story_day': current_day,
                    'story_day_label': label,
                })
            continue
        
        # First scene of the script is always Day 1
        if i == 0 and start_from_order == 0:
            current_day = 1
        elif scene.get('is_new_story_day'):
            current_day += 1
        
        # Build label
        label = _build_label(
            current_day,
            scene.get('time_transition', ''),
            scene.get('timeline_code', 'PRESENT'),
        )
        
        # Only update if values changed
        if scene.get('story_day') != current_day or scene.get('story_day_label') != label:
            scenes_to_update.append({
                'id': scene['id'],
                'story_day': current_day,
                'story_day_label': label,
            })
        
        # Update in-memory too for subsequent iterations
        scene['story_day'] = current_day
        scene['story_day_label'] = label
    
    # Batch update changed scenes
    if scenes_to_update:
        db.bulk_update_story_days(scenes_to_update)
        print(f"[StoryDays] Updated {len(scenes_to_update)} scenes for script {script_id}")
    
    # Calculate total unique story days
    all_days = set()
    for s in scenes:
        sd = s.get('story_day')
        if sd is not None:
            all_days.add(sd)
    total_days = len(all_days)
    
    # Update script-level total
    db.update_script_total_story_days(script_id, total_days)
    
    print(f"[StoryDays] Script {script_id}: {total_days} total story days")
    
    return {
        'total_days': total_days,
        'scenes_updated': len(scenes_to_update),
    }


def _build_label(day_number: int, time_transition: str, timeline_code: str) -> str:
    """
    Build a human-readable story day label.
    
    Examples:
        "Day 1"
        "Day 4 (THREE MONTHS LATER)"
        "Flashback — Day 2"
        "Dream Sequence"
    """
    base = f"Day {day_number}"
    
    # Adjust label for time gaps
    if time_transition:
        upper = time_transition.upper()
        if any(kw in upper for kw in ['WEEK', 'MONTH', 'YEAR', 'LATER']):
            # Only add transition note if it's a significant time gap
            if any(kw in upper for kw in ['WEEK', 'MONTH', 'YEAR']):
                base = f"Day {day_number} ({time_transition.strip()})"
    
    # Handle non-present timelines
    if timeline_code and timeline_code != 'PRESENT':
        label_map = {
            'FLASHBACK': 'Flashback',
            'DREAM': 'Dream',
            'FANTASY': 'Fantasy',
            'MONTAGE': 'Montage',
            'TITLE_CARD': 'Title Card',
        }
        prefix = label_map.get(timeline_code, timeline_code.title())
        base = f"{prefix} — {base}"
    
    return base


def get_story_day_summary(script_id: str) -> Dict:
    """
    Get story day statistics for a script.
    
    Returns:
        {
            'total_days': int,
            'scenes_per_day': {day_number: count},
            'timeline_breakdown': {timeline_code: count},
            'unassigned_count': int,
        }
    """
    scenes = db.get_scenes_ordered(script_id)
    
    if not scenes:
        return {
            'total_days': 0,
            'scenes_per_day': {},
            'timeline_breakdown': {},
            'unassigned_count': 0,
        }
    
    scenes_per_day = {}
    timeline_breakdown = {}
    unassigned = 0
    
    for scene in scenes:
        sd = scene.get('story_day')
        tc = scene.get('timeline_code', 'PRESENT')
        
        if sd is not None:
            scenes_per_day[sd] = scenes_per_day.get(sd, 0) + 1
        else:
            unassigned += 1
        
        timeline_breakdown[tc] = timeline_breakdown.get(tc, 0) + 1
    
    return {
        'total_days': len(scenes_per_day),
        'scenes_per_day': scenes_per_day,
        'timeline_breakdown': timeline_breakdown,
        'unassigned_count': unassigned,
    }
