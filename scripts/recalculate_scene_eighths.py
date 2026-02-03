#!/usr/bin/env python3
"""
Migration Script: Recalculate Scene Length Eighths

This script recalculates page_length_eighths for all existing scenes using the
corrected calculation logic. Run this after fixing the calculation methods to
ensure all historical data is accurate.

Usage:
    python scripts/recalculate_scene_eighths.py [--dry-run] [--script-id SCRIPT_ID]

Options:
    --dry-run       Show what would be updated without making changes
    --script-id     Only recalculate scenes for a specific script
"""

import sys
import os
import argparse
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from db.supabase_client import get_supabase_client
from utils.scene_calculations import calculate_eighths_from_content, calculate_eighths_from_pages


def recalculate_scene_eighths(dry_run=False, script_id=None):
    """
    Recalculate page_length_eighths for all scenes.
    
    Args:
        dry_run (bool): If True, show changes without applying them
        script_id (str): If provided, only process scenes from this script
    """
    print(f"\n{'='*60}")
    print(f"Scene Length Recalculation - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    if script_id:
        print(f"Script Filter: {script_id}")
    print(f"{'='*60}\n")
    
    client = get_supabase_client()
    
    # Build query
    query = client.table('scenes').select('*')
    if script_id:
        query = query.eq('script_id', script_id)
    
    # Fetch all scenes
    response = query.execute()
    scenes = response.data
    
    if not scenes:
        print("No scenes found.")
        return
    
    print(f"Found {len(scenes)} scenes to process.\n")
    
    updated_count = 0
    unchanged_count = 0
    errors = []
    
    for scene in scenes:
        scene_id = scene['id']
        scene_number = scene.get('scene_number', 'Unknown')
        old_eighths = scene.get('page_length_eighths')
        
        try:
            # Recalculate using corrected logic
            scene_text = scene.get('scene_text')
            page_start = scene.get('page_start')
            page_end = scene.get('page_end')
            
            if scene_text and len(scene_text.strip()) > 50:
                new_eighths = calculate_eighths_from_content(scene_text)
            elif page_start and page_end:
                new_eighths = calculate_eighths_from_pages(page_start, page_end, scene_text)
            else:
                new_eighths = 8  # Default to 1 page
            
            # Check if update needed
            if old_eighths != new_eighths:
                print(f"Scene {scene_number} (ID: {scene_id[:8]}...)")
                print(f"  Old: {old_eighths} eighths → New: {new_eighths} eighths")
                
                if not dry_run:
                    # Update database
                    client.table('scenes').update({
                        'page_length_eighths': new_eighths
                    }).eq('id', scene_id).execute()
                    print(f"  ✓ Updated")
                else:
                    print(f"  [Would update]")
                
                updated_count += 1
            else:
                unchanged_count += 1
                
        except Exception as e:
            error_msg = f"Scene {scene_number} (ID: {scene_id[:8]}...): {str(e)}"
            errors.append(error_msg)
            print(f"✗ Error: {error_msg}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total scenes processed: {len(scenes)}")
    print(f"Scenes updated: {updated_count}")
    print(f"Scenes unchanged: {unchanged_count}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"  - {error}")
    
    if dry_run and updated_count > 0:
        print(f"\n⚠️  This was a DRY RUN. Run without --dry-run to apply changes.")
    elif updated_count > 0:
        print(f"\n✓ Successfully updated {updated_count} scenes.")
    else:
        print(f"\n✓ All scenes already have correct values.")
    
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Recalculate scene length eighths for all scenes'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    parser.add_argument(
        '--script-id',
        type=str,
        help='Only recalculate scenes for a specific script'
    )
    
    args = parser.parse_args()
    
    try:
        recalculate_scene_eighths(
            dry_run=args.dry_run,
            script_id=args.script_id
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
