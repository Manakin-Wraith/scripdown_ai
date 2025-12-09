"""
Analysis Queue Service - Handles background processing of AI analysis jobs.

This service manages:
- Job queue for analysis tasks
- Chunked processing for large scripts
- Progress tracking
- Error handling and retries
"""

import json
import time
import threading
from datetime import datetime
from db.db_connection import get_db

# ============================================
# Job Queue Management
# ============================================

def create_analysis_job(script_id, job_type, target_id=None, priority=5):
    """
    Create a new analysis job in the queue.
    
    Args:
        script_id: The script to analyze
        job_type: 'overview', 'story_arc', 'characters', 'character_detail', 'locations'
        target_id: Character name or location for specific analyses
        priority: 1=highest, 10=lowest
    
    Returns:
        job_id of created job
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if job already exists
        cursor.execute("""
            SELECT job_id FROM analysis_jobs 
            WHERE script_id = ? AND job_type = ? AND target_id IS ? AND status IN ('queued', 'processing')
        """, (script_id, job_type, target_id))
        
        existing = cursor.fetchone()
        if existing:
            return existing[0]
        
        cursor.execute("""
            INSERT INTO analysis_jobs (script_id, job_type, target_id, priority, status)
            VALUES (?, ?, ?, ?, 'queued')
        """, (script_id, job_type, target_id, priority))
        
        job_id = cursor.lastrowid
        db.commit()
        cursor.close()
        
        return job_id
        
    except Exception as e:
        print(f"Error creating analysis job: {e}")
        return None


def get_next_job():
    """Get the next job to process (highest priority, oldest first)."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT job_id, script_id, job_type, target_id, retry_count, max_retries
            FROM analysis_jobs 
            WHERE status = 'queued'
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            return {
                'job_id': row[0],
                'script_id': row[1],
                'job_type': row[2],
                'target_id': row[3],
                'retry_count': row[4],
                'max_retries': row[5]
            }
        return None
        
    except Exception as e:
        print(f"Error getting next job: {e}")
        return None


def update_job_status(job_id, status, progress=None, result_summary=None, error_message=None):
    """Update job status and progress."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        updates = ["status = ?"]
        params = [status]
        
        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)
        
        if result_summary is not None:
            updates.append("result_summary = ?")
            params.append(result_summary)
        
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        
        if status == 'processing':
            updates.append("started_at = CURRENT_TIMESTAMP")
        elif status in ('completed', 'failed'):
            updates.append("completed_at = CURRENT_TIMESTAMP")
        
        params.append(job_id)
        
        cursor.execute(f"""
            UPDATE analysis_jobs 
            SET {', '.join(updates)}
            WHERE job_id = ?
        """, params)
        
        db.commit()
        cursor.close()
        
    except Exception as e:
        print(f"Error updating job status: {e}")


def retry_job(job_id):
    """Increment retry count and re-queue job."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE analysis_jobs 
            SET status = 'queued', 
                retry_count = retry_count + 1,
                error_message = NULL,
                started_at = NULL
            WHERE job_id = ?
        """, (job_id,))
        
        db.commit()
        cursor.close()
        
    except Exception as e:
        print(f"Error retrying job: {e}")


# ============================================
# Script Analysis Status
# ============================================

def update_script_analysis_status(script_id, status, progress=None):
    """Update the overall analysis status for a script."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        updates = ["analysis_status = ?"]
        params = [status]
        
        if progress is not None:
            updates.append("analysis_progress = ?")
            params.append(progress)
        
        if status == 'in_progress' and progress == 0:
            updates.append("analysis_started_at = CURRENT_TIMESTAMP")
        elif status == 'complete':
            updates.append("analysis_completed_at = CURRENT_TIMESTAMP")
        
        params.append(script_id)
        
        cursor.execute(f"""
            UPDATE scripts 
            SET {', '.join(updates)}
            WHERE script_id = ?
        """, params)
        
        db.commit()
        cursor.close()
        
    except Exception as e:
        print(f"Error updating script analysis status: {e}")


def get_script_analysis_status(script_id):
    """Get the current analysis status for a script."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get script status
        cursor.execute("""
            SELECT analysis_status, analysis_progress, analysis_started_at, analysis_completed_at
            FROM scripts WHERE script_id = ?
        """, (script_id,))
        
        script_row = cursor.fetchone()
        
        # Get job statuses
        cursor.execute("""
            SELECT job_type, target_id, status, progress, error_message, result_summary
            FROM analysis_jobs 
            WHERE script_id = ?
            ORDER BY created_at DESC
        """, (script_id,))
        
        jobs = cursor.fetchall()
        cursor.close()
        
        if not script_row:
            return None
        
        return {
            'status': script_row[0] or 'pending',
            'progress': script_row[1] or 0,
            'started_at': script_row[2],
            'completed_at': script_row[3],
            'jobs': [
                {
                    'type': job[0],
                    'target': job[1],
                    'status': job[2],
                    'progress': job[3],
                    'error': job[4],
                    'message': job[5]  # result_summary for progress details
                }
                for job in jobs
            ]
        }
        
    except Exception as e:
        print(f"Error getting script analysis status: {e}")
        return None


def get_all_analysis_status():
    """Get analysis status for all scripts."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT script_id, script_name, analysis_status, analysis_progress
            FROM scripts
            ORDER BY upload_date DESC
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        
        return {
            row[0]: {
                'name': row[1],
                'status': row[2] or 'pending',
                'progress': row[3] or 0
            }
            for row in rows
        }
        
    except Exception as e:
        print(f"Error getting all analysis status: {e}")
        return {}


# ============================================
# Queue Full Script Analysis
# ============================================

def queue_full_analysis(script_id, priority=5, fresh_start=True, force=False, include_deep_analysis=False):
    """
    Queue analysis jobs for a script.
    
    Essential jobs (always run):
    1. Scene Extraction/Enhancement - extracts all scenes
    2. Overview (quick stats)
    3. Story Arc (theme analysis)
    
    Deep analysis jobs (on-demand, opt-in):
    4. Characters (all characters) - can be triggered per-character later
    5. Locations (all locations) - can be triggered per-location later
    
    Args:
        script_id: The script to analyze
        priority: Base priority (lower = higher priority)
        fresh_start: If True, clears existing jobs, scenes, and analysis data
        force: If True, queue even if analysis is already in progress
        include_deep_analysis: If True, also queue character/location analysis
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if analysis is already in progress (prevent duplicate runs)
        if not force:
            cursor.execute("""
                SELECT COUNT(*) FROM analysis_jobs 
                WHERE script_id = ? AND status IN ('queued', 'processing')
            """, (script_id,))
            active_jobs = cursor.fetchone()[0]
            
            if active_jobs > 0:
                print(f"[Queue] Script {script_id} already has {active_jobs} active jobs, skipping")
                return {
                    'script_id': script_id,
                    'jobs_created': 0,
                    'message': 'Analysis already in progress',
                    'active_jobs': active_jobs
                }
        
        if fresh_start:
            # Clear existing analysis jobs for this script
            cursor.execute("DELETE FROM analysis_jobs WHERE script_id = ?", (script_id,))
            
            # Clear existing scenes (will be re-extracted)
            cursor.execute("DELETE FROM scenes WHERE script_id = ?", (script_id,))
            
            # Clear cached analysis data
            cursor.execute("DELETE FROM character_analysis WHERE script_id = ?", (script_id,))
            cursor.execute("DELETE FROM story_arc_analysis WHERE script_id = ?", (script_id,))
            cursor.execute("DELETE FROM script_analysis WHERE script_id = ?", (script_id,))
            
            db.commit()
            print(f"[Queue] Cleared existing data for script {script_id}")
        
        cursor.close()
        
        # Update script status
        update_script_analysis_status(script_id, 'queued', 0)
        
        # Create jobs in order of priority
        # Scene extraction MUST run first - other jobs depend on it
        # Essential jobs (always run)
        jobs = [
            ('scene_extraction', None, 0),  # Highest priority - extracts all scenes
            ('overview', None, 1),          # Quick stats
            ('story_arc', None, 2),         # Story context
        ]
        
        # Deep analysis jobs (optional - can be triggered on-demand per character/location)
        if include_deep_analysis:
            jobs.extend([
                ('characters', None, 3),    # All characters - slow, ~35s per character
                ('locations', None, 4),     # All locations
            ])
        
        job_ids = []
        for job_type, target_id, job_priority in jobs:
            job_id = create_analysis_job(
                script_id, 
                job_type, 
                target_id, 
                priority + job_priority
            )
            if job_id:
                job_ids.append(job_id)
        
        return {
            'script_id': script_id,
            'jobs_created': len(job_ids),
            'job_ids': job_ids
        }
        
    except Exception as e:
        print(f"Error queuing full analysis: {e}")
        return None


def queue_scene_enhancement(script_id, priority=5, force=False):
    """
    Queue scene enhancement jobs for the new v2 pipeline.
    
    This creates one job per scene candidate, allowing:
    - Parallel processing
    - Individual retry on failure
    - Resumable from any point
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if analysis is already in progress (prevent duplicate runs)
        if not force:
            cursor.execute("""
                SELECT COUNT(*) FROM analysis_jobs 
                WHERE script_id = ? AND status IN ('queued', 'processing')
            """, (script_id,))
            active_jobs = cursor.fetchone()[0]
            
            if active_jobs > 0:
                print(f"[Queue] Script {script_id} already has {active_jobs} active jobs, skipping")
                return {
                    'script_id': script_id,
                    'jobs_created': 0,
                    'message': 'Analysis already in progress',
                    'active_jobs': active_jobs
                }
        
        # Get pending scene candidates
        cursor.execute("""
            SELECT candidate_id, scene_number_original 
            FROM scene_candidates 
            WHERE script_id = ? AND status = 'pending'
            ORDER BY scene_order
        """, (script_id,))
        
        candidates = cursor.fetchall()
        
        if not candidates:
            print(f"[Queue] No pending candidates for script {script_id}")
            return {'script_id': script_id, 'jobs_created': 0}
        
        # Create one job for scene enhancement (processes all candidates)
        job_id = create_analysis_job(
            script_id,
            'scene_enhancement',  # New job type
            None,
            priority
        )
        
        # Also queue post-processing jobs (depend on scene_enhancement)
        # Note: characters and locations are now on-demand (not auto-queued)
        post_jobs = [
            ('overview', None, priority + 1),
            ('story_arc', None, priority + 2),
            # ('characters', None, priority + 3),  # On-demand via character profile
            # ('locations', None, priority + 4),   # On-demand via location profile
        ]
        
        job_ids = [job_id] if job_id else []
        for job_type, target_id, job_priority in post_jobs:
            jid = create_analysis_job(script_id, job_type, target_id, job_priority)
            if jid:
                job_ids.append(jid)
        
        # Update script status
        update_script_analysis_status(script_id, 'queued', 0)
        
        cursor.close()
        
        return {
            'script_id': script_id,
            'scene_candidates': len(candidates),
            'jobs_created': len(job_ids),
            'job_ids': job_ids
        }
        
    except Exception as e:
        print(f"Error queuing scene enhancement: {e}")
        return None


def cancel_script_analysis(script_id):
    """Cancel all pending/processing jobs for a script."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE analysis_jobs 
            SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
            WHERE script_id = ? AND status IN ('queued', 'processing')
        """, (script_id,))
        
        cancelled_count = cursor.rowcount
        
        # Update script status
        cursor.execute("""
            UPDATE scripts 
            SET analysis_status = 'cancelled'
            WHERE script_id = ?
        """, (script_id,))
        
        db.commit()
        cursor.close()
        
        return {'cancelled_jobs': cancelled_count}
        
    except Exception as e:
        print(f"Error cancelling analysis: {e}")
        return None


# ============================================
# Character Analysis Cache
# ============================================

def save_character_analysis(script_id, character_name, analysis_data, is_complete=True):
    """Save character analysis to the dedicated cache table."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO character_analysis 
            (script_id, character_name, role_type, description, traits, backstory, 
             motivation, arc_summary, scene_breakdown, relationships, is_complete, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            script_id,
            character_name,
            analysis_data.get('role_type'),
            analysis_data.get('description'),
            json.dumps(analysis_data.get('traits', [])),
            analysis_data.get('backstory'),
            analysis_data.get('motivation'),
            analysis_data.get('arc_summary'),
            json.dumps(analysis_data.get('scene_breakdown', {})),
            json.dumps(analysis_data.get('relationships', [])),
            1 if is_complete else 0
        ))
        
        db.commit()
        cursor.close()
        
    except Exception as e:
        print(f"Error saving character analysis: {e}")


def get_character_analysis(script_id, character_name):
    """Get character analysis from cache."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT role_type, description, traits, backstory, motivation, 
                   arc_summary, scene_breakdown, relationships, is_complete
            FROM character_analysis 
            WHERE script_id = ? AND character_name = ?
        """, (script_id, character_name))
        
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            return {
                'role_type': row[0],
                'description': row[1],
                'traits': json.loads(row[2]) if row[2] else [],
                'backstory': row[3],
                'motivation': row[4],
                'arc_summary': row[5],
                'scene_breakdown': json.loads(row[6]) if row[6] else {},
                'relationships': json.loads(row[7]) if row[7] else [],
                'is_complete': bool(row[8])
            }
        return None
        
    except Exception as e:
        print(f"Error getting character analysis: {e}")
        return None


def get_all_character_analyses(script_id):
    """Get all character analyses for a script."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT character_name, role_type, description, traits, backstory, 
                   motivation, arc_summary, scene_breakdown, relationships, is_complete
            FROM character_analysis 
            WHERE script_id = ?
        """, (script_id,))
        
        rows = cursor.fetchall()
        cursor.close()
        
        characters = {}
        for row in rows:
            characters[row[0]] = {
                'role_type': row[1],
                'description': row[2],
                'traits': json.loads(row[3]) if row[3] else [],
                'backstory': row[4],
                'motivation': row[5],
                'arc_summary': row[6],
                'scene_breakdown': json.loads(row[7]) if row[7] else {},
                'relationships': json.loads(row[8]) if row[8] else [],
                'is_complete': bool(row[9])
            }
        
        return characters
        
    except Exception as e:
        print(f"Error getting all character analyses: {e}")
        return {}


# ============================================
# Story Arc Cache
# ============================================

def save_story_arc_analysis(script_id, analysis_data):
    """Save story arc analysis to cache."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO story_arc_analysis 
            (script_id, theme, tone, conflict_type, setting_mood, protagonist, 
             antagonist, is_ensemble, narrative_style, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            script_id,
            analysis_data.get('theme'),
            analysis_data.get('tone'),
            analysis_data.get('conflict_type'),
            analysis_data.get('setting_mood'),
            analysis_data.get('protagonist'),
            analysis_data.get('antagonist'),
            1 if analysis_data.get('is_ensemble') else 0,
            analysis_data.get('narrative_style')
        ))
        
        db.commit()
        cursor.close()
        
    except Exception as e:
        print(f"Error saving story arc analysis: {e}")


def get_story_arc_analysis(script_id):
    """Get story arc analysis from cache."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT theme, tone, conflict_type, setting_mood, protagonist, 
                   antagonist, is_ensemble, narrative_style
            FROM story_arc_analysis 
            WHERE script_id = ?
        """, (script_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            return {
                'theme': row[0],
                'tone': row[1],
                'conflict_type': row[2],
                'setting_mood': row[3],
                'protagonist': row[4],
                'antagonist': row[5],
                'is_ensemble': bool(row[6]),
                'narrative_style': row[7]
            }
        return None
        
    except Exception as e:
        print(f"Error getting story arc analysis: {e}")
        return None


# ============================================
# Analysis Metrics
# ============================================

def update_analysis_metrics(script_id, **kwargs):
    """Update analysis metrics for a script."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if metrics exist
        cursor.execute("SELECT id FROM analysis_metrics WHERE script_id = ?", (script_id,))
        exists = cursor.fetchone()
        
        if exists:
            updates = [f"{k} = ?" for k in kwargs.keys()]
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params = list(kwargs.values()) + [script_id]
            
            cursor.execute(f"""
                UPDATE analysis_metrics 
                SET {', '.join(updates)}
                WHERE script_id = ?
            """, params)
        else:
            columns = ['script_id'] + list(kwargs.keys())
            placeholders = ['?'] * len(columns)
            params = [script_id] + list(kwargs.values())
            
            cursor.execute(f"""
                INSERT INTO analysis_metrics ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """, params)
        
        db.commit()
        cursor.close()
        
    except Exception as e:
        print(f"Error updating analysis metrics: {e}")
