#!/usr/bin/env python3
"""
Force page-based calculation for scenes with minimal text
This will store the page-based eighths in the database
"""

import sys
import os
from pathlib import Path

backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from db.supabase_client import SupabaseDB
from utils.scene_calculations import calculate_eighths_from_pages, format_eighths

def force_page_based_calculation(script_id):
    """Force page-based calculation for all scenes in a script."""
    db = SupabaseDB()
    
    # Get scenes
    response = db.client.table('scenes').select('*').eq('script_id', script_id).order('scene_number').execute()
    scenes = response.data
    
    if not scenes:
        print(f"❌ No scenes found for script {script_id}")
        return
    
    print(f"📊 Processing {len(scenes)} scenes\n")
    
    for scene in scenes:
        scene_id = scene['id']
        scene_num = scene.get('scene_number', 'Unknown')
        page_start = scene.get('page_start')
        page_end = scene.get('page_end')
        
        if page_start and page_end:
            # Calculate using page-based method
            eighths = calculate_eighths_from_pages(page_start, page_end)
            
            # Update database
            db.client.table('scenes').update({
                'page_length_eighths': eighths
            }).eq('id', scene_id).execute()
            
            print(f"✅ Scene {scene_num}: Pages {page_start}-{page_end} = {format_eighths(eighths)}")
        else:
            print(f"⚠️  Scene {scene_num}: No page data")
    
    print("\n✅ Done!")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('script_id', help='Script ID')
    args = parser.parse_args()
    
    force_page_based_calculation(args.script_id)
