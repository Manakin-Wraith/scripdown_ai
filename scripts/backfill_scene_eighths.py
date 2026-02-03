#!/usr/bin/env python3
"""
Backfill Script: Calculate Scene Length in Eighths

Calculates and updates page_length_eighths for all existing scenes.
Uses content-based calculation for accuracy.

Usage:
    python scripts/backfill_scene_eighths.py                    # All scenes
    python scripts/backfill_scene_eighths.py --script-id 123    # Specific script
    python scripts/backfill_scene_eighths.py --dry-run          # Preview only
"""

import sys
import os
import argparse
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from db.supabase_client import SupabaseDB
from utils.scene_calculations import (
    calculate_eighths_from_content,
    calculate_eighths_from_pages,
    format_eighths
)


def backfill_scene_eighths(script_id=None, dry_run=False):
    """
    Backfill page_length_eighths for existing scenes.
    
    Args:
        script_id (str, optional): Specific script ID to backfill
        dry_run (bool): If True, only preview changes without updating
    """
    db = SupabaseDB()
    
    # Build query
    query = db.client.table('scenes').select('*')
    
    if script_id:
        query = query.eq('script_id', script_id)
        print(f"🎬 Backfilling scenes for script: {script_id}")
    else:
        print("🎬 Backfilling all scenes")
    
    # Only process scenes without eighths calculated
    query = query.is_('page_length_eighths', 'null')
    
    # Execute query
    response = query.execute()
    scenes = response.data
    
    if not scenes:
        print("✅ No scenes need backfilling. All scenes already have eighths calculated.")
        return
    
    print(f"📊 Found {len(scenes)} scenes to process")
    print()
    
    updated_count = 0
    skipped_count = 0
    
    for scene in scenes:
        scene_id = scene['id']
        scene_num = scene.get('scene_number', 'Unknown')
        
        # Gather scene text from all available fields
        scene_text_parts = []
        
        if scene.get('description'):
            scene_text_parts.append(scene['description'])
        if scene.get('action_description'):
            scene_text_parts.append(scene['action_description'])
        if scene.get('dialog'):
            scene_text_parts.append(scene['dialog'])
        
        scene_text = '\n'.join(scene_text_parts)
        
        # Calculate eighths
        if scene_text.strip():
            # Use content-based calculation (more accurate)
            eighths = calculate_eighths_from_content(scene_text)
            method = "content"
        elif scene.get('page_start') and scene.get('page_end'):
            # Fallback to page range calculation
            eighths = calculate_eighths_from_pages(
                scene['page_start'],
                scene['page_end']
            )
            method = "page-range"
        else:
            # No data available, skip
            print(f"⚠️  Scene {scene_num} (ID: {scene_id}): No content or page data, skipping")
            skipped_count += 1
            continue
        
        formatted = format_eighths(eighths)
        
        if dry_run:
            print(f"🔍 Scene {scene_num} (ID: {scene_id}): Would set to {formatted} ({method})")
        else:
            # Update database
            try:
                db.client.table('scenes').update({
                    'page_length_eighths': eighths
                }).eq('id', scene_id).execute()
                
                print(f"✅ Scene {scene_num} (ID: {scene_id}): Set to {formatted} ({method})")
                updated_count += 1
            except Exception as e:
                print(f"❌ Scene {scene_num} (ID: {scene_id}): Error - {str(e)}")
                skipped_count += 1
    
    print()
    print("=" * 60)
    if dry_run:
        print(f"🔍 DRY RUN COMPLETE")
        print(f"   Would update: {updated_count} scenes")
    else:
        print(f"✅ BACKFILL COMPLETE")
        print(f"   Updated: {updated_count} scenes")
    
    if skipped_count > 0:
        print(f"   Skipped: {skipped_count} scenes (no data)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Backfill scene length in eighths for existing scenes'
    )
    parser.add_argument(
        '--script-id',
        type=str,
        help='Specific script ID to backfill (optional)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without updating database'
    )
    
    args = parser.parse_args()
    
    try:
        backfill_scene_eighths(
            script_id=args.script_id,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
