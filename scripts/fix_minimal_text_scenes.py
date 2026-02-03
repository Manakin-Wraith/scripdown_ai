#!/usr/bin/env python3
"""
Fix scenes with minimal text by using page-based calculation
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from db.supabase_client import SupabaseDB
from utils.scene_calculations import (
    calculate_eighths_from_pages,
    format_eighths
)

def fix_minimal_text_scenes(script_id=None, min_lines_threshold=10):
    """
    Fix scenes that have minimal text by recalculating using page-based method.
    
    Args:
        script_id: Optional script ID to fix
        min_lines_threshold: Scenes with fewer lines than this will be recalculated
    """
    db = SupabaseDB()
    
    # Build query
    query = db.client.table('scenes').select('*')
    
    if script_id:
        query = query.eq('script_id', script_id)
        print(f"🔧 Fixing scenes for script: {script_id}")
    else:
        print("🔧 Fixing all scenes with minimal text")
    
    # Execute query
    response = query.execute()
    scenes = response.data
    
    if not scenes:
        print("✅ No scenes found")
        return
    
    print(f"📊 Checking {len(scenes)} scenes\n")
    
    fixed_count = 0
    skipped_count = 0
    
    for scene in scenes:
        scene_id = scene['id']
        scene_num = scene.get('scene_number', 'Unknown')
        
        # Gather scene text
        scene_text_parts = []
        if scene.get('description'):
            scene_text_parts.append(scene['description'])
        if scene.get('action_description'):
            scene_text_parts.append(scene['action_description'])
        if scene.get('dialog'):
            scene_text_parts.append(scene['dialog'])
        
        scene_text = '\n'.join(scene_text_parts)
        line_count = len(scene_text.strip().split('\n')) if scene_text.strip() else 0
        
        # Check if scene has minimal text
        if line_count < min_lines_threshold:
            page_start = scene.get('page_start')
            page_end = scene.get('page_end')
            
            if page_start and page_end:
                # Recalculate using page-based method
                new_eighths = calculate_eighths_from_pages(page_start, page_end)
                old_eighths = scene.get('page_length_eighths')
                
                if new_eighths != old_eighths:
                    try:
                        db.client.table('scenes').update({
                            'page_length_eighths': new_eighths
                        }).eq('id', scene_id).execute()
                        
                        print(f"✅ Scene {scene_num} (ID: {scene_id[:8]}...): {line_count} lines")
                        print(f"   Pages {page_start}-{page_end}: {format_eighths(old_eighths)} → {format_eighths(new_eighths)}")
                        fixed_count += 1
                    except Exception as e:
                        print(f"❌ Scene {scene_num}: Error - {str(e)}")
                        skipped_count += 1
                else:
                    print(f"⏭️  Scene {scene_num}: Already correct ({format_eighths(old_eighths)})")
                    skipped_count += 1
            else:
                print(f"⚠️  Scene {scene_num}: No page data available")
                skipped_count += 1
        else:
            skipped_count += 1
    
    print()
    print("=" * 60)
    print(f"✅ FIX COMPLETE")
    print(f"   Fixed: {fixed_count} scenes")
    print(f"   Skipped: {skipped_count} scenes")
    print("=" * 60)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fix scenes with minimal text using page-based calculation'
    )
    parser.add_argument(
        '--script-id',
        type=str,
        help='Specific script ID to fix'
    )
    parser.add_argument(
        '--min-lines',
        type=int,
        default=10,
        help='Minimum line count threshold (default: 10)'
    )
    
    args = parser.parse_args()
    
    try:
        fix_minimal_text_scenes(
            script_id=args.script_id,
            min_lines_threshold=args.min_lines
        )
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
