"""
Revision Service - Script Version Comparison and Import

This module handles:
1. Importing new script revisions (PDF upload)
2. Comparing scenes between versions (diff)
3. Tracking changes and creating version history
"""

import os
import hashlib
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from services.extraction_pipeline import parse_pdf_with_pages, detect_scene_headers, generate_content_hash


class ChangeType(Enum):
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    REMOVED = "removed"


@dataclass
class SceneDiff:
    """Represents a difference between two scene versions."""
    change_type: ChangeType
    scene_number: str
    old_scene: Optional[Dict] = None
    new_scene: Optional[Dict] = None
    similarity_score: float = 0.0
    changes: List[str] = None
    
    def __post_init__(self):
        if self.changes is None:
            self.changes = []
    
    def to_dict(self):
        return {
            'change_type': self.change_type.value,
            'scene_number': self.scene_number,
            'old_scene': self.old_scene,
            'new_scene': self.new_scene,
            'similarity_score': self.similarity_score,
            'changes': self.changes
        }


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two text strings using Jaccard similarity.
    Returns a value between 0 (completely different) and 1 (identical).
    """
    if not text1 or not text2:
        return 0.0
    
    # Normalize texts
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0


def match_scenes_by_header(old_scenes: List[Dict], new_scenes: List[Dict]) -> Dict[str, Dict]:
    """
    Match scenes between old and new versions by scene header.
    Returns a mapping of new_scene_id -> old_scene (or None if new).
    """
    # Build lookup by scene number
    old_by_number = {s.get('scene_number', str(i)): s for i, s in enumerate(old_scenes)}
    
    matches = {}
    for new_scene in new_scenes:
        new_number = new_scene.get('scene_number', '')
        
        # Try exact match first
        if new_number in old_by_number:
            matches[new_scene.get('id', new_number)] = old_by_number[new_number]
        else:
            # Try fuzzy match by header similarity
            best_match = None
            best_score = 0.0
            
            new_header = f"{new_scene.get('int_ext', '')} {new_scene.get('setting', '')} {new_scene.get('time_of_day', '')}"
            
            for old_scene in old_scenes:
                old_header = f"{old_scene.get('int_ext', '')} {old_scene.get('setting', '')} {old_scene.get('time_of_day', '')}"
                score = calculate_text_similarity(new_header, old_header)
                
                if score > best_score and score > 0.7:  # 70% threshold
                    best_score = score
                    best_match = old_scene
            
            matches[new_scene.get('id', new_number)] = best_match
    
    return matches


def compare_scene_content(old_scene: Dict, new_scene: Dict) -> Tuple[bool, List[str]]:
    """
    Compare two scenes and return whether they differ and what changed.
    """
    changes = []
    
    # Compare header fields
    if old_scene.get('int_ext') != new_scene.get('int_ext'):
        changes.append(f"INT/EXT changed: {old_scene.get('int_ext')} → {new_scene.get('int_ext')}")
    
    if old_scene.get('setting') != new_scene.get('setting'):
        changes.append(f"Setting changed: {old_scene.get('setting')} → {new_scene.get('setting')}")
    
    if old_scene.get('time_of_day') != new_scene.get('time_of_day'):
        changes.append(f"Time changed: {old_scene.get('time_of_day')} → {new_scene.get('time_of_day')}")
    
    # Compare content hash if available
    old_hash = old_scene.get('content_hash') or generate_content_hash(old_scene.get('full_text', ''))
    new_hash = new_scene.get('content_hash') or generate_content_hash(new_scene.get('full_text', ''))
    
    if old_hash != new_hash:
        changes.append("Scene content modified")
    
    return len(changes) > 0, changes


def diff_script_versions(old_scenes: List[Dict], new_scenes: List[Dict]) -> List[SceneDiff]:
    """
    Compare two versions of a script and return a list of differences.
    
    Args:
        old_scenes: List of scene dicts from the previous version
        new_scenes: List of scene dicts from the new version
    
    Returns:
        List of SceneDiff objects describing all changes
    """
    diffs = []
    
    # Match new scenes to old scenes
    matches = match_scenes_by_header(old_scenes, new_scenes)
    
    # Track which old scenes were matched
    matched_old_ids = set()
    
    for new_scene in new_scenes:
        new_id = new_scene.get('id', new_scene.get('scene_number', ''))
        old_scene = matches.get(new_id)
        
        if old_scene is None:
            # New scene added
            diffs.append(SceneDiff(
                change_type=ChangeType.ADDED,
                scene_number=new_scene.get('scene_number', '?'),
                new_scene=new_scene,
                similarity_score=0.0,
                changes=['New scene added']
            ))
        else:
            matched_old_ids.add(old_scene.get('id', old_scene.get('scene_number', '')))
            
            # Compare content
            has_changes, changes = compare_scene_content(old_scene, new_scene)
            
            # Calculate similarity
            old_text = old_scene.get('full_text', '')
            new_text = new_scene.get('full_text', '')
            similarity = calculate_text_similarity(old_text, new_text)
            
            if has_changes or similarity < 0.95:
                diffs.append(SceneDiff(
                    change_type=ChangeType.MODIFIED,
                    scene_number=new_scene.get('scene_number', '?'),
                    old_scene=old_scene,
                    new_scene=new_scene,
                    similarity_score=similarity,
                    changes=changes if changes else ['Content modified']
                ))
            else:
                diffs.append(SceneDiff(
                    change_type=ChangeType.UNCHANGED,
                    scene_number=new_scene.get('scene_number', '?'),
                    old_scene=old_scene,
                    new_scene=new_scene,
                    similarity_score=similarity,
                    changes=[]
                ))
    
    # Find removed scenes (in old but not matched)
    for old_scene in old_scenes:
        old_id = old_scene.get('id', old_scene.get('scene_number', ''))
        if old_id not in matched_old_ids:
            diffs.append(SceneDiff(
                change_type=ChangeType.REMOVED,
                scene_number=old_scene.get('scene_number', '?'),
                old_scene=old_scene,
                similarity_score=0.0,
                changes=['Scene removed']
            ))
    
    # Sort by scene number
    def scene_sort_key(diff):
        num = diff.scene_number
        # Handle alphanumeric scene numbers like "12A"
        match = __import__('re').match(r'(\d+)([A-Z]*)', str(num))
        if match:
            return (int(match.group(1)), match.group(2))
        return (0, str(num))
    
    diffs.sort(key=scene_sort_key)
    
    return diffs


def extract_scenes_from_pdf(file_path: str) -> List[Dict]:
    """
    Extract scenes from a PDF file using the extraction pipeline.
    Returns a list of scene dictionaries.
    """
    pages, full_text = parse_pdf_with_pages(file_path)
    
    scenes = []
    current_scene = None
    
    for page in pages:
        if page.scene_headers:
            for header in page.scene_headers:
                # Save previous scene
                if current_scene:
                    current_scene['page_end'] = page.page_number - 1
                    scenes.append(current_scene)
                
                # Start new scene
                current_scene = {
                    'scene_number': header.get('scene_number', str(len(scenes) + 1)),
                    'int_ext': header.get('int_ext', 'INT'),
                    'setting': header.get('setting', 'UNKNOWN'),
                    'time_of_day': header.get('time_of_day', 'DAY'),
                    'page_start': page.page_number,
                    'full_text': '',
                    'content_hash': ''
                }
        
        # Accumulate text for current scene
        if current_scene:
            current_scene['full_text'] += page.text + '\n'
    
    # Don't forget the last scene
    if current_scene:
        current_scene['page_end'] = pages[-1].page_number if pages else 1
        current_scene['content_hash'] = generate_content_hash(current_scene['full_text'])
        scenes.append(current_scene)
    
    return scenes


def create_version_record(supabase, script_id: str, revision_color: str, 
                          pdf_path: str = None, notes: str = None) -> Dict:
    """
    Create a new script version record in the database.
    """
    # Get the next version number
    result = supabase.table('script_versions').select('version_number').eq(
        'script_id', script_id
    ).order('version_number', desc=True).limit(1).execute()
    
    next_version = 1
    if result.data:
        next_version = result.data[0]['version_number'] + 1
    
    # Create version record
    version_data = {
        'script_id': script_id,
        'version_number': next_version,
        'revision_color': revision_color,
        'pdf_path': pdf_path,
        'notes': notes,
        'imported_at': datetime.utcnow().isoformat()
    }
    
    result = supabase.table('script_versions').insert(version_data).execute()
    
    return result.data[0] if result.data else None


def apply_revision_changes(supabase, script_id: str, version_id: str, 
                           diffs: List[SceneDiff], new_scenes: List[Dict]) -> Dict:
    """
    Apply the changes from a revision import to the database.
    
    This will:
    1. Update existing scenes that were modified
    2. Add new scenes
    3. Mark removed scenes as omitted
    4. Create scene_history records for all changes
    """
    stats = {
        'added': 0,
        'modified': 0,
        'removed': 0,
        'unchanged': 0
    }
    
    for diff in diffs:
        if diff.change_type == ChangeType.ADDED:
            # Insert new scene
            scene_data = {
                'script_id': script_id,
                'scene_number': diff.new_scene.get('scene_number'),
                'int_ext': diff.new_scene.get('int_ext'),
                'setting': diff.new_scene.get('setting'),
                'time_of_day': diff.new_scene.get('time_of_day'),
                'full_text': diff.new_scene.get('full_text', ''),
                'page_start': diff.new_scene.get('page_start'),
                'page_end': diff.new_scene.get('page_end'),
                'content_hash': diff.new_scene.get('content_hash'),
                'revision_number': 1
            }
            result = supabase.table('scenes').insert(scene_data).execute()
            
            if result.data:
                # Create history record
                supabase.table('scene_history').insert({
                    'scene_id': result.data[0]['id'],
                    'version_id': version_id,
                    'change_type': 'created',
                    'previous_data': None
                }).execute()
            
            stats['added'] += 1
            
        elif diff.change_type == ChangeType.MODIFIED:
            # Update existing scene
            old_id = diff.old_scene.get('id')
            if old_id:
                # Store previous data for history
                previous_data = {
                    'int_ext': diff.old_scene.get('int_ext'),
                    'setting': diff.old_scene.get('setting'),
                    'time_of_day': diff.old_scene.get('time_of_day'),
                    'full_text': diff.old_scene.get('full_text'),
                    'content_hash': diff.old_scene.get('content_hash')
                }
                
                # Update scene
                update_data = {
                    'int_ext': diff.new_scene.get('int_ext'),
                    'setting': diff.new_scene.get('setting'),
                    'time_of_day': diff.new_scene.get('time_of_day'),
                    'full_text': diff.new_scene.get('full_text', ''),
                    'page_start': diff.new_scene.get('page_start'),
                    'page_end': diff.new_scene.get('page_end'),
                    'content_hash': diff.new_scene.get('content_hash'),
                    'revision_number': (diff.old_scene.get('revision_number', 0) or 0) + 1
                }
                
                supabase.table('scenes').update(update_data).eq('id', old_id).execute()
                
                # Create history record
                supabase.table('scene_history').insert({
                    'scene_id': old_id,
                    'version_id': version_id,
                    'change_type': 'modified',
                    'previous_data': previous_data
                }).execute()
            
            stats['modified'] += 1
            
        elif diff.change_type == ChangeType.REMOVED:
            # Mark scene as omitted
            old_id = diff.old_scene.get('id')
            if old_id:
                supabase.table('scenes').update({
                    'is_omitted': True,
                    'omitted_at': datetime.utcnow().isoformat()
                }).eq('id', old_id).execute()
                
                # Create history record
                supabase.table('scene_history').insert({
                    'scene_id': old_id,
                    'version_id': version_id,
                    'change_type': 'omitted',
                    'previous_data': {'is_omitted': False}
                }).execute()
            
            stats['removed'] += 1
            
        else:  # UNCHANGED
            stats['unchanged'] += 1
    
    return stats


def get_version_history(supabase, script_id: str) -> List[Dict]:
    """
    Get the version history for a script.
    """
    result = supabase.table('script_versions').select('*').eq(
        'script_id', script_id
    ).order('version_number', desc=True).execute()
    
    return result.data if result.data else []


def get_version_diff(supabase, script_id: str, version_id: str, 
                     compare_to_version_id: str = None) -> List[Dict]:
    """
    Get the diff for a specific version compared to another version.
    If compare_to_version_id is not provided, compares to the previous version.
    """
    # Get the version
    version_result = supabase.table('script_versions').select('*').eq(
        'id', version_id
    ).single().execute()
    
    if not version_result.data:
        return []
    
    version = version_result.data
    
    # Get comparison version
    if compare_to_version_id:
        compare_result = supabase.table('script_versions').select('*').eq(
            'id', compare_to_version_id
        ).single().execute()
        compare_version = compare_result.data
    else:
        # Get previous version
        compare_result = supabase.table('script_versions').select('*').eq(
            'script_id', script_id
        ).lt('version_number', version['version_number']).order(
            'version_number', desc=True
        ).limit(1).execute()
        compare_version = compare_result.data[0] if compare_result.data else None
    
    if not compare_version:
        return []
    
    # Get scene history for this version
    history_result = supabase.table('scene_history').select(
        '*, scenes!scene_history_scene_id_fkey(*)'
    ).eq('version_id', version_id).execute()
    
    return history_result.data if history_result.data else []
