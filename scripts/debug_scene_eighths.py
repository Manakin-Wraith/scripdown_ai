#!/usr/bin/env python3
"""
Debug script to examine scene eighths calculation for latest script
"""

import sys
import os
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

def debug_latest_script():
    """Debug the latest uploaded script's scene eighths."""
    db = SupabaseDB()
    
    # Get the most recent script
    scripts_response = db.client.table('scripts').select('*').order('created_at', desc=True).limit(1).execute()
    
    if not scripts_response.data:
        print("❌ No scripts found")
        return
    
    script = scripts_response.data[0]
    script_id = script['id']
    script_title = script.get('title', 'Untitled')
    total_pages = script.get('total_pages', 'Unknown')
    
    print(f"\n{'='*80}")
    print(f"📄 Script: {script_title}")
    print(f"   ID: {script_id}")
    print(f"   Total Pages: {total_pages}")
    print(f"{'='*80}\n")
    
    # Get scenes for this script
    scenes_response = db.client.table('scenes').select('*').eq('script_id', script_id).order('scene_number').execute()
    scenes = scenes_response.data
    
    if not scenes:
        print("❌ No scenes found for this script")
        return
    
    print(f"📊 Found {len(scenes)} scenes\n")
    
    total_eighths = 0
    
    for i, scene in enumerate(scenes, 1):
        scene_num = scene.get('scene_number', i)
        scene_id = scene['id']
        stored_eighths = scene.get('page_length_eighths')
        page_start = scene.get('page_start')
        page_end = scene.get('page_end')
        
        # Gather scene text
        scene_text_parts = []
        if scene.get('description'):
            scene_text_parts.append(scene['description'])
        if scene.get('action_description'):
            scene_text_parts.append(scene['action_description'])
        if scene.get('dialog'):
            scene_text_parts.append(scene['dialog'])
        
        scene_text = '\n'.join(scene_text_parts)
        
        print(f"Scene {scene_num} (ID: {scene_id[:8]}...)")
        print(f"  Pages: {page_start} - {page_end}")
        print(f"  Stored eighths: {stored_eighths} ({format_eighths(stored_eighths) if stored_eighths else 'None'})")
        
        # Calculate using different methods
        if scene_text.strip():
            content_eighths = calculate_eighths_from_content(scene_text)
            lines = len(scene_text.strip().split('\n'))
            print(f"  Content-based: {content_eighths} eighths ({format_eighths(content_eighths)}) - {lines} lines")
        else:
            print(f"  Content-based: No text available")
        
        if page_start and page_end:
            page_eighths = calculate_eighths_from_pages(page_start, page_end, scene_text if scene_text.strip() else None)
            page_span = page_end - page_start + 1 if page_end >= page_start else 1
            print(f"  Page-based: {page_eighths} eighths ({format_eighths(page_eighths)}) - {page_span} page span")
        else:
            print(f"  Page-based: No page data")
        
        if stored_eighths:
            total_eighths += stored_eighths
        
        print()
    
    print(f"{'='*80}")
    print(f"📈 TOTALS:")
    print(f"   Sum of stored eighths: {total_eighths} ({format_eighths(total_eighths)})")
    print(f"   Expected for {total_pages} pages: {int(total_pages) * 8 if isinstance(total_pages, (int, float)) else 'Unknown'} eighths")
    print(f"   Calculated pages from eighths: {total_eighths / 8:.2f} pages")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    try:
        debug_latest_script()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
