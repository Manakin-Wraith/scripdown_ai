"""
Supabase Client for SlateOne (ScripDown AI)

This module provides the Supabase client connection and helper functions
for database operations.
"""

import os
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: supabase-py not installed. Run: pip install supabase")


# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')


@lru_cache(maxsize=1)
def get_supabase_client() -> 'Client':
    """
    Get a cached Supabase client instance.
    Uses the anon key for client-side operations.
    """
    if not SUPABASE_AVAILABLE:
        raise ImportError("supabase-py is not installed")
    
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment")
    
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


@lru_cache(maxsize=1)
def get_supabase_admin() -> 'Client':
    """
    Get a cached Supabase admin client instance.
    Uses the service role key for server-side operations (bypasses RLS).
    """
    if not SUPABASE_AVAILABLE:
        raise ImportError("supabase-py is not installed")
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for admin operations")
    
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_db():
    """
    Compatibility function - returns Supabase client.
    This allows gradual migration from SQLite.
    """
    return get_supabase_client()


# ============================================
# Helper Functions for Common Operations
# ============================================

class SupabaseDB:
    """
    Database abstraction layer for Supabase operations.
    Provides a cleaner API for common database tasks.
    """
    
    def __init__(self, use_admin: bool = False):
        """
        Initialize with either anon or admin client.
        
        Args:
            use_admin: If True, use service role key (bypasses RLS)
        """
        self.client = get_supabase_admin() if use_admin else get_supabase_client()
    
    # ============================================
    # Scripts
    # ============================================
    
    def create_script(self, user_id: str, title: str, **kwargs) -> dict:
        """Create a new script record."""
        data = {
            'user_id': user_id,
            'title': title,
            **kwargs
        }
        result = self.client.table('scripts').insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_script(self, script_id: str) -> dict:
        """Get a script by ID."""
        result = self.client.table('scripts').select('*').eq('id', script_id).single().execute()
        return result.data
    
    def get_user_scripts(self, user_id: str) -> list:
        """Get all scripts for a user."""
        result = self.client.table('scripts').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        return result.data or []
    
    def update_script(self, script_id: str, **kwargs) -> dict:
        """Update a script."""
        result = self.client.table('scripts').update(kwargs).eq('id', script_id).execute()
        return result.data[0] if result.data else None
    
    def delete_script(self, script_id: str) -> bool:
        """Delete a script."""
        result = self.client.table('scripts').delete().eq('id', script_id).execute()
        return True
    
    # ============================================
    # Script Pages
    # ============================================
    
    def add_script_pages(self, script_id: str, pages: list) -> list:
        """Add multiple pages to a script."""
        data = [
            {'script_id': script_id, 'page_number': p['page_number'], 'page_text': p['text']}
            for p in pages
        ]
        result = self.client.table('script_pages').insert(data).execute()
        return result.data or []
    
    def get_script_pages(self, script_id: str) -> list:
        """Get all pages for a script."""
        result = self.client.table('script_pages').select('*').eq('script_id', script_id).order('page_number').execute()
        return result.data or []
    
    # ============================================
    # Scenes
    # ============================================
    
    def create_scene(self, script_id: str, scene_number: str, scene_order: int, **kwargs) -> dict:
        """Create a new scene."""
        data = {
            'script_id': script_id,
            'scene_number': scene_number,
            'scene_order': scene_order,
            **kwargs
        }
        result = self.client.table('scenes').insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_scenes(self, script_id: str) -> list:
        """Get all scenes for a script."""
        result = self.client.table('scenes').select('*').eq('script_id', script_id).order('scene_order').execute()
        return result.data or []
    
    def get_scene(self, scene_id: str) -> dict:
        """Get a scene by ID."""
        result = self.client.table('scenes').select('*').eq('id', scene_id).single().execute()
        return result.data
    
    def update_scene(self, scene_id: str, **kwargs) -> dict:
        """Update a scene."""
        result = self.client.table('scenes').update(kwargs).eq('id', scene_id).execute()
        return result.data[0] if result.data else None
    
    def delete_scene(self, scene_id: str) -> bool:
        """Delete a scene."""
        result = self.client.table('scenes').delete().eq('id', scene_id).execute()
        return True
    
    def create_scenes_batch(self, scenes: list) -> list:
        """Create multiple scenes at once."""
        result = self.client.table('scenes').insert(scenes).execute()
        return result.data or []
    
    # ============================================
    # Analysis Jobs
    # ============================================
    
    def create_analysis_job(self, script_id: str, job_type: str, scene_id: str = None, priority: int = 5) -> dict:
        """Create an analysis job."""
        data = {
            'script_id': script_id,
            'job_type': job_type,
            'scene_id': scene_id,
            'priority': priority,
            'status': 'queued'
        }
        result = self.client.table('analysis_jobs').insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_pending_jobs(self, limit: int = 10) -> list:
        """Get pending analysis jobs ordered by priority."""
        result = self.client.table('analysis_jobs').select('*').eq('status', 'queued').order('priority').order('created_at').limit(limit).execute()
        return result.data or []
    
    def update_job_status(self, job_id: str, status: str, **kwargs) -> dict:
        """Update job status."""
        data = {'status': status, **kwargs}
        result = self.client.table('analysis_jobs').update(data).eq('id', job_id).execute()
        return result.data[0] if result.data else None
    
    # ============================================
    # Scene Management (Phase 1)
    # ============================================
    
    def reorder_scenes(self, script_id: str, scene_ids: list) -> bool:
        """
        Reorder scenes by updating their scene_order based on array position.
        
        Args:
            script_id: The script ID
            scene_ids: Ordered list of scene UUIDs in desired order
            
        Returns:
            True if successful
        """
        for i, scene_id in enumerate(scene_ids, start=1):
            self.client.table('scenes').update({
                'scene_order': i
            }).eq('id', scene_id).eq('script_id', script_id).execute()
        
        return True
    
    def omit_scene(self, scene_id: str, is_omitted: bool = True) -> dict:
        """
        Mark a scene as omitted (or un-omit).
        
        Args:
            scene_id: The scene ID
            is_omitted: True to omit, False to restore
            
        Returns:
            Updated scene data
        """
        from datetime import datetime
        
        data = {
            'is_omitted': is_omitted,
            'omitted_at': datetime.utcnow().isoformat() if is_omitted else None
        }
        
        result = self.client.table('scenes').update(data).eq('id', scene_id).execute()
        return result.data[0] if result.data else None
    
    def get_scenes_for_management(self, script_id: str) -> list:
        """
        Get all scenes for a script with management-related fields.
        Includes omitted scenes and orders by scene_order.
        
        Returns:
            List of scenes with all fields needed for scene manager
        """
        result = self.client.table('scenes').select(
            'id, script_id, scene_number, scene_number_original, scene_order, '
            'int_ext, setting, time_of_day, page_start, page_end, '
            'is_omitted, omitted_at, locked_scene_number, revision_number, '
            'analysis_status, characters, props, created_at'
        ).eq('script_id', script_id).order('scene_order').execute()
        
        return result.data or []
    
    def record_scene_history(self, scene_id: str, change_type: str, 
                            previous_data: dict = None, user_id: str = None,
                            version_id: str = None) -> dict:
        """
        Record a change to scene history for audit trail.
        
        Args:
            scene_id: The scene that was changed
            change_type: Type of change (created, modified, omitted, split, merged, reordered)
            previous_data: Snapshot of scene data before change
            user_id: User who made the change
            version_id: Script version ID if applicable
            
        Returns:
            Created history record
        """
        import json
        
        data = {
            'scene_id': scene_id,
            'change_type': change_type,
            'previous_data': json.dumps(previous_data) if previous_data else None,
            'changed_by': user_id,
            'version_id': version_id
        }
        
        result = self.client.table('scene_history').insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_scene_history(self, scene_id: str) -> list:
        """Get change history for a scene."""
        result = self.client.table('scene_history').select('*').eq(
            'scene_id', scene_id
        ).order('changed_at', desc=True).execute()
        
        return result.data or []
    
    # ============================================
    # Script Versions (Phase 1 - Basic)
    # ============================================
    
    def create_script_version(self, script_id: str, version_number: int, 
                              revision_color: str = 'white', **kwargs) -> dict:
        """Create a new script version record."""
        data = {
            'script_id': script_id,
            'version_number': version_number,
            'revision_color': revision_color,
            **kwargs
        }
        result = self.client.table('script_versions').insert(data).execute()
        return result.data[0] if result.data else None
    
    def get_script_versions(self, script_id: str) -> list:
        """Get all versions for a script."""
        result = self.client.table('script_versions').select('*').eq(
            'script_id', script_id
        ).order('version_number', desc=True).execute()
        
        return result.data or []
    
    def get_latest_version(self, script_id: str) -> dict:
        """Get the latest version for a script."""
        result = self.client.table('script_versions').select('*').eq(
            'script_id', script_id
        ).order('version_number', desc=True).limit(1).execute()
        
        return result.data[0] if result.data else None
    
    # ============================================
    # Story Days (Phase 1)
    # ============================================
    
    def get_scene_by_order(self, script_id: str, scene_order: int) -> dict:
        """
        Get a scene by its scene_order position within a script.
        Used to fetch Scene X-1 for previous-scene context injection.
        
        Returns:
            Scene dict with header fields + story day fields, or None.
        """
        result = self.client.table('scenes').select(
            'id, script_id, scene_number, scene_number_original, scene_order, '
            'int_ext, setting, time_of_day, description, '
            'story_day, is_new_story_day, story_day_label, time_transition, timeline_code'
        ).eq('script_id', script_id).eq('scene_order', scene_order).limit(1).execute()
        
        return result.data[0] if result.data else None
    
    def get_scenes_ordered(self, script_id: str) -> list:
        """
        Get all scenes for a script ordered by scene_order, with story day fields.
        Used by recalculate_story_days() and story day summary.
        
        Returns:
            List of scene dicts ordered by scene_order.
        """
        result = self.client.table('scenes').select(
            'id, script_id, scene_number, scene_number_original, scene_order, '
            'int_ext, setting, time_of_day, description, '
            'story_day, story_day_label, time_transition, '
            'is_new_story_day, story_day_confidence, '
            'story_day_is_manual, story_day_is_locked, timeline_code'
        ).eq('script_id', script_id).order('scene_order').execute()
        
        return result.data or []
    
    def bulk_update_story_days(self, scenes: list) -> bool:
        """
        Batch update story_day, story_day_label for a list of scenes.
        Each scene dict must have 'id', 'story_day', 'story_day_label'.
        
        Returns:
            True if successful.
        """
        for scene in scenes:
            self.client.table('scenes').update({
                'story_day': scene.get('story_day'),
                'story_day_label': scene.get('story_day_label'),
            }).eq('id', scene['id']).execute()
        
        return True
    
    def update_script_total_story_days(self, script_id: str, total_days: int) -> dict:
        """Update total_story_days on the scripts table."""
        result = self.client.table('scripts').update({
            'total_story_days': total_days
        }).eq('id', script_id).execute()
        return result.data[0] if result.data else None


# Singleton instance for easy import
# Try admin first, fall back to anon if service key not set
try:
    db = SupabaseDB(use_admin=True)  # Use admin for server-side operations
except ValueError:
    print("Warning: SUPABASE_SERVICE_KEY not set, using anon client (RLS applies)")
    db = SupabaseDB(use_admin=False)
