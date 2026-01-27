"""
Analytics Service - Data aggregation for superuser dashboard

Provides analytics on:
- User activity and engagement
- Script analysis performance
- System health metrics
- Subscription and conversion stats
"""

from datetime import datetime, timedelta
from db.supabase_client import get_supabase_client, get_supabase_admin
from typing import Dict, List, Any, Optional


class AnalyticsService:
    """Service for aggregating analytics data"""
    
    def __init__(self):
        # Use admin client for analytics to bypass RLS
        self.supabase = get_supabase_admin()
    
    def get_global_stats(self) -> Dict[str, Any]:
        """
        Get high-level global statistics
        
        Returns:
            dict: Global metrics including user counts, script counts, etc.
        """
        try:
            # Total users
            users_result = self.supabase.table('profiles').select('id', count='exact').execute()
            total_users = users_result.count or 0
            
            # Total scripts
            scripts_result = self.supabase.table('scripts').select('id', count='exact').execute()
            total_scripts = scripts_result.count or 0
            
            # Total scenes analyzed
            scenes_result = self.supabase.table('scenes').select('id', count='exact').execute()
            total_scenes = scenes_result.count or 0
            
            # Active users (last 30 days)
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            active_users_result = self.supabase.table('scripts')\
                .select('user_id', count='exact')\
                .gte('created_at', thirty_days_ago)\
                .execute()
            
            # Get unique active users
            active_user_ids = set()
            if active_users_result.data:
                for script in active_users_result.data:
                    if script.get('user_id'):
                        active_user_ids.add(script['user_id'])
            active_users = len(active_user_ids)
            
            # Scripts analyzed this month
            first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0).isoformat()
            scripts_this_month = self.supabase.table('scripts')\
                .select('id', count='exact')\
                .gte('created_at', first_of_month)\
                .execute()
            
            # Analysis jobs stats - Note: analysis_jobs table may not exist in Supabase
            try:
                jobs_result = self.supabase.table('analysis_jobs')\
                    .select('id, status', count='exact')\
                    .execute()
            except Exception:
                # Table doesn't exist, use defaults
                jobs_result = type('obj', (object,), {'count': 0, 'data': []})()

            
            total_jobs = jobs_result.count or 0
            completed_jobs = 0
            failed_jobs = 0
            
            if jobs_result.data:
                for job in jobs_result.data:
                    if job.get('status') == 'completed':
                        completed_jobs += 1
                    elif job.get('status') == 'failed':
                        failed_jobs += 1
            
            success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            
            # Subscription stats - Note: subscription_status column may not exist
            try:
                trial_users = self.supabase.table('profiles')\
                    .select('id', count='exact')\
                    .eq('subscription_status', 'trial')\
                    .execute()
                
                active_subscribers = self.supabase.table('profiles')\
                    .select('id', count='exact')\
                    .eq('subscription_status', 'active')\
                    .execute()
            except Exception:
                # Column doesn't exist, use defaults
                trial_users = type('obj', (object,), {'count': 0})()
                active_subscribers = type('obj', (object,), {'count': 0})()

            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'total_scripts': total_scripts,
                'scripts_this_month': scripts_this_month.count or 0,
                'total_scenes': total_scenes,
                'total_analysis_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'success_rate': round(success_rate, 2),
                'trial_users': trial_users.count or 0,
                'active_subscribers': active_subscribers.count or 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting global stats: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_user_activity(self, days: int = 30, limit: int = 100, offset: int = 0, 
                          status_filter: str = None, search: str = None) -> Dict[str, Any]:
        """
        Get user activity with filtering and pagination
        
        Args:
            days: Number of days to look back
            limit: Maximum number of records to return
            offset: Number of records to skip (pagination)
            status_filter: Filter by subscription status (trial, active, expired)
            search: Search by name or email
            
        Returns:
            dict: User activity records with engagement metrics and total count
        """
        try:
            # Build query for users
            query = self.supabase.table('profiles')\
                .select('id, full_name, email, created_at', count='exact')
            
            # Try to add subscription_status if column exists
            try:
                if status_filter:
                    query = query.eq('subscription_status', status_filter)
            except Exception:
                pass
            
            # Add search filter
            if search:
                # Search in name or email
                query = query.or_(f'full_name.ilike.%{search}%,email.ilike.%{search}%')
            
            # Execute with pagination
            users_result = query\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            total_count = users_result.count or 0
            users = []
            
            for user in users_result.data or []:
                user_id = user['id']
                
                # Get script count
                scripts_result = self.supabase.table('scripts')\
                    .select('id', count='exact')\
                    .eq('user_id', user_id)\
                    .execute()
                
                # Get last activity (most recent script)
                last_script = self.supabase.table('scripts')\
                    .select('created_at')\
                    .eq('user_id', user_id)\
                    .order('created_at', desc=True)\
                    .limit(1)\
                    .execute()
                
                last_active = None
                if last_script.data:
                    last_active = last_script.data[0].get('created_at')
                
                # Calculate days since signup
                created_at = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
                days_since_signup = (datetime.now(created_at.tzinfo) - created_at).days
                
                users.append({
                    'user_id': user_id,
                    'name': user.get('full_name', 'Unknown'),
                    'email': user.get('email'),
                    'subscription_status': 'trial',  # Default since column may not exist
                    'script_count': scripts_result.count or 0,
                    'last_active': last_active,
                    'days_since_signup': days_since_signup,
                    'created_at': user['created_at']
                })
            
            return {
                'users': users,
                'total': total_count,
                'limit': limit,
                'offset': offset
            }
            
        except Exception as e:
            print(f"Error getting user activity: {e}")
            return {
                'users': [],
                'total': 0,
                'limit': limit,
                'offset': offset,
                'error': str(e)
            }
    
    def get_recent_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent platform activity events
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            list: Recent activity events with timestamps and details
        """
        try:
            activities = []
            
            # Get recent user signups
            recent_users = self.supabase.table('profiles')\
                .select('id, full_name, email, created_at')\
                .order('created_at', desc=True)\
                .limit(20)\
                .execute()
            
            for user in recent_users.data or []:
                activities.append({
                    'type': 'user_signup',
                    'user_name': user.get('full_name', 'Unknown'),
                    'user_email': user.get('email'),
                    'timestamp': user['created_at'],
                    'description': f"{user.get('full_name', 'New user')} signed up"
                })
            
            # Get recent script uploads
            recent_scripts = self.supabase.table('scripts')\
                .select('id, title, user_id, created_at')\
                .order('created_at', desc=True)\
                .limit(20)\
                .execute()
            
            for script in recent_scripts.data or []:
                # Get user info
                user_result = self.supabase.table('profiles')\
                    .select('full_name')\
                    .eq('id', script['user_id'])\
                    .limit(1)\
                    .execute()
                
                user_name = 'Unknown'
                if user_result.data:
                    user_name = user_result.data[0].get('full_name', 'Unknown')
                
                activities.append({
                    'type': 'script_upload',
                    'user_name': user_name,
                    'script_title': script.get('title', 'Untitled'),
                    'script_id': script['id'],
                    'timestamp': script['created_at'],
                    'description': f"{user_name} uploaded '{script.get('title', 'Untitled')}'"
                })
            
            # Get recent scene analysis completions (if scenes table has status)
            try:
                recent_scenes = self.supabase.table('scenes')\
                    .select('id, scene_number, script_id, created_at')\
                    .order('created_at', desc=True)\
                    .limit(10)\
                    .execute()
                
                for scene in recent_scenes.data or []:
                    # Get script info
                    script_result = self.supabase.table('scripts')\
                        .select('title, user_id')\
                        .eq('id', scene['script_id'])\
                        .limit(1)\
                        .execute()
                    
                    if script_result.data:
                        script_data = script_result.data[0]
                        
                        # Get user info
                        user_result = self.supabase.table('profiles')\
                            .select('full_name')\
                            .eq('id', script_data['user_id'])\
                            .limit(1)\
                            .execute()
                        
                        user_name = 'Unknown'
                        if user_result.data:
                            user_name = user_result.data[0].get('full_name', 'Unknown')
                        
                        activities.append({
                            'type': 'scene_analyzed',
                            'user_name': user_name,
                            'script_title': script_data.get('title', 'Untitled'),
                            'scene_number': scene.get('scene_number'),
                            'timestamp': scene['created_at'],
                            'description': f"Scene {scene.get('scene_number', '?')} analyzed in '{script_data.get('title', 'Untitled')}'"
                        })
            except Exception:
                # Scenes table might not have the data we need
                pass
            
            # Sort all activities by timestamp (most recent first)
            activities.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Return limited results
            return activities[:limit]
            
        except Exception as e:
            print(f"Error getting recent activity: {e}")
            return []
    
    def get_chart_data(self, days: int = 30) -> Dict[str, Any]:
        """
        Get chart data for visualizations
        
        Args:
            days: Number of days to look back
            
        Returns:
            dict: Chart data for scripts and users over time
        """
        try:
            from datetime import timedelta
            
            # Use 7 days for better visualization with limited data
            days = 7
            
            # Generate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get all scripts
            all_scripts = self.supabase.table('scripts')\
                .select('id, created_at')\
                .gte('created_at', start_date.isoformat())\
                .execute()
            
            # Get all users
            all_users = self.supabase.table('profiles')\
                .select('id, created_at')\
                .execute()
            
            # Scripts over time - count by day
            scripts_data = []
            current_date = start_date
            while current_date <= end_date:
                date_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
                date_end = date_start + timedelta(days=1)
                
                # Count scripts created on this day
                count = 0
                for script in (all_scripts.data or []):
                    script_date = datetime.fromisoformat(script['created_at'].replace('Z', '+00:00'))
                    if date_start.replace(tzinfo=script_date.tzinfo) <= script_date < date_end.replace(tzinfo=script_date.tzinfo):
                        count += 1
                
                scripts_data.append({
                    'date': current_date.strftime('%b %d'),
                    'count': count
                })
                
                current_date += timedelta(days=1)
            
            # User growth (cumulative) - count total users up to each day
            users_data = []
            current_date = start_date
            while current_date <= end_date:
                date_end = current_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # Count total users up to this date
                count = 0
                for user in (all_users.data or []):
                    user_date = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
                    if user_date <= date_end.replace(tzinfo=user_date.tzinfo):
                        count += 1
                
                users_data.append({
                    'date': current_date.strftime('%b %d'),
                    'total': count
                })
                
                current_date += timedelta(days=1)
            
            print(f"Chart data generated: {len(scripts_data)} script points, {len(users_data)} user points")
            print(f"Scripts data sample: {scripts_data[:3]}")
            print(f"Users data sample: {users_data[:3]}")
            
            return {
                'scripts_over_time': scripts_data,
                'user_growth': users_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting chart data: {e}")
            import traceback
            traceback.print_exc()
            return {
                'scripts_over_time': [],
                'user_growth': [],
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_script_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive script analytics and performance metrics
        
        Returns:
            dict: Script analytics including overview, top scripts, and distributions
        """
        try:
            # Get all scripts with user info
            scripts_result = self.supabase.table('scripts')\
                .select('id, title, user_id, created_at')\
                .execute()
            
            scripts_data = scripts_result.data or []
            total_scripts = len(scripts_data)
            
            # Get all scenes
            scenes_result = self.supabase.table('scenes')\
                .select('id, script_id, scene_number, setting, time_of_day, int_ext, characters')\
                .execute()
            
            scenes_data = scenes_result.data or []
            total_scenes = len(scenes_data)
            
            # Calculate metrics per script
            script_metrics = {}
            for script in scripts_data:
                script_id = script['id']
                script_scenes = [s for s in scenes_data if s.get('script_id') == script_id]
                
                # Count unique characters across all scenes
                all_characters = set()
                all_locations = set()
                int_scenes = 0
                ext_scenes = 0
                day_scenes = 0
                night_scenes = 0
                
                for scene in script_scenes:
                    # Characters
                    chars = scene.get('characters', []) or []
                    if isinstance(chars, list):
                        for char in chars:
                            if isinstance(char, dict) and 'name' in char:
                                all_characters.add(char['name'])
                            elif isinstance(char, str):
                                all_characters.add(char)
                    
                    # Locations
                    setting = scene.get('setting', '')
                    if setting:
                        all_locations.add(setting)
                    
                    # INT/EXT - use the int_ext column
                    int_ext = (scene.get('int_ext') or '').upper()
                    if int_ext == 'INT' or int_ext == 'INTERIOR':
                        int_scenes += 1
                    elif int_ext == 'EXT' or int_ext == 'EXTERIOR':
                        ext_scenes += 1
                    
                    # DAY/NIGHT - use the time_of_day column
                    time_of_day = (scene.get('time_of_day') or '').upper()
                    if 'DAY' in time_of_day:
                        day_scenes += 1
                    elif 'NIGHT' in time_of_day:
                        night_scenes += 1
                
                # Get user info
                user_result = self.supabase.table('profiles')\
                    .select('full_name')\
                    .eq('id', script['user_id'])\
                    .limit(1)\
                    .execute()
                
                user_name = 'Unknown'
                if user_result.data:
                    user_name = user_result.data[0].get('full_name', 'Unknown')
                
                script_metrics[script_id] = {
                    'id': script_id,
                    'title': script.get('title', 'Untitled'),
                    'user_name': user_name,
                    'scene_count': len(script_scenes),
                    'character_count': len(all_characters),
                    'location_count': len(all_locations),
                    'int_scenes': int_scenes,
                    'ext_scenes': ext_scenes,
                    'day_scenes': day_scenes,
                    'night_scenes': night_scenes,
                    'uploaded_at': script['created_at']
                }
            
            # Calculate overview metrics
            total_characters = sum(m['character_count'] for m in script_metrics.values())
            total_locations = sum(m['location_count'] for m in script_metrics.values())
            avg_scenes = total_scenes / total_scripts if total_scripts > 0 else 0
            avg_characters = total_characters / total_scripts if total_scripts > 0 else 0
            
            # Get top scripts by scene count
            top_scripts = sorted(script_metrics.values(), key=lambda x: x['scene_count'], reverse=True)[:10]
            
            # Calculate scene distribution across all scripts
            total_int = sum(m['int_scenes'] for m in script_metrics.values())
            total_ext = sum(m['ext_scenes'] for m in script_metrics.values())
            total_day = sum(m['day_scenes'] for m in script_metrics.values())
            total_night = sum(m['night_scenes'] for m in script_metrics.values())
            
            # Calculate performance metrics
            performance = self.get_performance_metrics()
            
            # Add analysis duration to each script
            for script_id, metrics in script_metrics.items():
                script = next((s for s in scripts_data if s['id'] == script_id), None)
                if script and script.get('created_at') and script.get('updated_at'):
                    try:
                        created = datetime.fromisoformat(script['created_at'].replace('Z', '+00:00'))
                        updated = datetime.fromisoformat(script['updated_at'].replace('Z', '+00:00'))
                        duration = (updated - created).total_seconds()
                        if duration > 0 and duration < 3600:
                            metrics['analysis_duration'] = round(duration, 1)
                        else:
                            metrics['analysis_duration'] = None
                    except:
                        metrics['analysis_duration'] = None
                else:
                    metrics['analysis_duration'] = None
            
            return {
                'overview': {
                    'total_scripts': total_scripts,
                    'total_scenes': total_scenes,
                    'avg_scenes_per_script': round(avg_scenes, 1),
                    'avg_characters_per_script': round(avg_characters, 1),
                    'total_characters': total_characters,
                    'total_locations': total_locations
                },
                'performance': performance,
                'top_scripts': top_scripts,
                'scene_distribution': {
                    'int_scenes': total_int,
                    'ext_scenes': total_ext,
                    'day_scenes': total_day,
                    'night_scenes': total_night
                },
                'all_scripts': list(script_metrics.values()),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting script analytics: {e}")
            import traceback
            traceback.print_exc()
            return {
                'overview': {
                    'total_scripts': 0,
                    'total_scenes': 0,
                    'avg_scenes_per_script': 0,
                    'avg_characters_per_script': 0,
                    'total_characters': 0,
                    'total_locations': 0
                },
                'top_scripts': [],
                'scene_distribution': {
                    'int_scenes': 0,
                    'ext_scenes': 0,
                    'day_scenes': 0,
                    'night_scenes': 0
                },
                'all_scripts': [],
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get analysis performance metrics from analysis_jobs table
        
        Returns:
            dict: Performance metrics including avg time, success rate, etc.
        """
        try:
            # Query analysis_jobs table for completed jobs
            # Schema: id (UUID), script_id, scene_id, job_type, status, started_at, completed_at
            jobs_result = self.supabase.table('analysis_jobs')\
                .select('id, started_at, completed_at, status')\
                .eq('status', 'completed')\
                .execute()
            
            jobs_data = jobs_result.data or []
            
            # Calculate durations from completed jobs
            durations = []
            for job in jobs_data:
                started = job.get('started_at')
                completed = job.get('completed_at')
                
                if started and completed:
                    try:
                        start_time = datetime.fromisoformat(started.replace('Z', '+00:00'))
                        end_time = datetime.fromisoformat(completed.replace('Z', '+00:00'))
                        duration = (end_time - start_time).total_seconds()
                        if duration > 0 and duration < 3600:  # Only count if < 1 hour (reasonable)
                            durations.append(duration)
                    except Exception as e:
                        print(f"Error parsing job timestamps: {e}")
                        pass
            
            # Get total job counts
            all_jobs_result = self.supabase.table('analysis_jobs')\
                .select('id', count='exact')\
                .execute()
            
            total_jobs = all_jobs_result.count or 0
            successful_jobs = len(jobs_data)
            
            # Calculate metrics
            avg_duration = sum(durations) / len(durations) if durations else 0
            fastest = min(durations) if durations else 0
            slowest = max(durations) if durations else 0
            success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
            
            print(f"Performance metrics calculated: {len(durations)} jobs with timing, avg={avg_duration}s")
            
            return {
                'avg_analysis_time': round(avg_duration, 1),
                'fastest_analysis': round(fastest, 1),
                'slowest_analysis': round(slowest, 1),
                'total_analyses': total_jobs,
                'successful_analyses': successful_jobs,
                'success_rate': round(success_rate, 1),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting performance metrics: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to script-based calculation
            try:
                scripts_result = self.supabase.table('scripts')\
                    .select('id, created_at, updated_at')\
                    .execute()
                
                scripts_data = scripts_result.data or []
                total_scripts = len(scripts_data)
                
                durations = []
                for script in scripts_data:
                    if script.get('created_at') and script.get('updated_at'):
                        try:
                            created = datetime.fromisoformat(script['created_at'].replace('Z', '+00:00'))
                            updated = datetime.fromisoformat(script['updated_at'].replace('Z', '+00:00'))
                            duration = (updated - created).total_seconds()
                            if duration > 0 and duration < 3600:
                                durations.append(duration)
                        except:
                            pass
                
                avg_duration = sum(durations) / len(durations) if durations else 0
                fastest = min(durations) if durations else 0
                slowest = max(durations) if durations else 0
                
                scenes_result = self.supabase.table('scenes')\
                    .select('script_id', count='exact')\
                    .execute()
                
                scripts_with_scenes = len(set(s['script_id'] for s in (scenes_result.data or [])))
                success_rate = (scripts_with_scenes / total_scripts * 100) if total_scripts > 0 else 0
                
                return {
                    'avg_analysis_time': round(avg_duration, 1),
                    'fastest_analysis': round(fastest, 1),
                    'slowest_analysis': round(slowest, 1),
                    'total_analyses': total_scripts,
                    'successful_analyses': scripts_with_scenes,
                    'success_rate': round(success_rate, 1),
                    'timestamp': datetime.now().isoformat()
                }
            except:
                return {
                    'avg_analysis_time': 0,
                    'fastest_analysis': 0,
                    'slowest_analysis': 0,
                    'total_analyses': 0,
                    'successful_analyses': 0,
                    'success_rate': 0,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
    
    def get_script_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get script analysis statistics
        
        Args:
            days: Number of days to look back
            
        Returns:
            dict: Script analysis metrics
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Scripts uploaded in period
            scripts_result = self.supabase.table('scripts')\
                .select('script_id, script_name, upload_date, analysis_status, scene_count')\
                .gte('upload_date', cutoff_date)\
                .order('upload_date', desc=True)\
                .execute()
            
            total_scripts = len(scripts_result.data or [])
            total_scenes = sum(s.get('scene_count', 0) for s in scripts_result.data or [])
            
            # Analysis status breakdown
            status_counts = {
                'pending': 0,
                'in_progress': 0,
                'complete': 0,
                'failed': 0
            }
            
            for script in scripts_result.data or []:
                status = script.get('analysis_status', 'pending')
                if status in status_counts:
                    status_counts[status] += 1
            
            # Average scenes per script
            avg_scenes = total_scenes / total_scripts if total_scripts > 0 else 0
            
            # Get analysis jobs for this period
            jobs_result = self.supabase.table('analysis_jobs')\
                .select('job_id, job_type, status, created_at, started_at, completed_at')\
                .gte('created_at', cutoff_date)\
                .execute()
            
            # Calculate average analysis time
            total_duration = 0
            completed_count = 0
            
            for job in jobs_result.data or []:
                if job.get('status') == 'completed' and job.get('started_at') and job.get('completed_at'):
                    started = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
                    completed = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
                    duration = (completed - started).total_seconds()
                    total_duration += duration
                    completed_count += 1
            
            avg_duration = total_duration / completed_count if completed_count > 0 else 0
            
            return {
                'period_days': days,
                'total_scripts': total_scripts,
                'total_scenes': total_scenes,
                'avg_scenes_per_script': round(avg_scenes, 1),
                'status_breakdown': status_counts,
                'total_jobs': len(jobs_result.data or []),
                'avg_analysis_time_seconds': round(avg_duration, 2),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting script stats: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get system performance metrics
        
        Returns:
            dict: Performance metrics including job stats, error rates, etc.
        """
        try:
            # Get all analysis jobs
            jobs_result = self.supabase.table('analysis_jobs')\
                .select('job_id, job_type, status, created_at, started_at, completed_at, error_message')\
                .order('created_at', desc=True)\
                .limit(1000)\
                .execute()
            
            # Job type breakdown
            job_types = {}
            total_jobs = 0
            failed_jobs = 0
            
            for job in jobs_result.data or []:
                job_type = job.get('job_type', 'unknown')
                if job_type not in job_types:
                    job_types[job_type] = {
                        'total': 0,
                        'completed': 0,
                        'failed': 0,
                        'avg_duration': 0,
                        'durations': []
                    }
                
                job_types[job_type]['total'] += 1
                total_jobs += 1
                
                if job.get('status') == 'completed':
                    job_types[job_type]['completed'] += 1
                    
                    # Calculate duration
                    if job.get('started_at') and job.get('completed_at'):
                        started = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
                        completed = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
                        duration = (completed - started).total_seconds()
                        job_types[job_type]['durations'].append(duration)
                
                elif job.get('status') == 'failed':
                    job_types[job_type]['failed'] += 1
                    failed_jobs += 1
            
            # Calculate averages
            for job_type in job_types:
                durations = job_types[job_type]['durations']
                if durations:
                    job_types[job_type]['avg_duration'] = round(sum(durations) / len(durations), 2)
                del job_types[job_type]['durations']  # Remove raw data
            
            # Error rate
            error_rate = (failed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            
            # Get recent errors
            recent_errors = []
            for job in jobs_result.data or []:
                if job.get('status') == 'failed' and job.get('error_message'):
                    recent_errors.append({
                        'job_type': job.get('job_type'),
                        'error': job.get('error_message'),
                        'timestamp': job.get('completed_at') or job.get('created_at')
                    })
                    if len(recent_errors) >= 10:
                        break
            
            return {
                'total_jobs': total_jobs,
                'failed_jobs': failed_jobs,
                'error_rate': round(error_rate, 2),
                'job_types': job_types,
                'recent_errors': recent_errors,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting performance metrics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_subscription_metrics(self) -> Dict[str, Any]:
        """
        Get subscription and conversion metrics
        
        Returns:
            dict: Subscription stats including trial conversions, churn, etc.
        """
        try:
            # Get all users - simplified to work with current schema
            users_result = self.supabase.table('profiles')\
                .select('id, created_at')\
                .execute()
            
            total_users = len(users_result.data or [])
            
            # Try to get subscription data if columns exist
            trial_users = 0
            active_subscribers = 0
            expired_users = 0
            trial_expiring_soon = 0
            
            try:
                # Attempt to query subscription_status if it exists
                status_result = self.supabase.table('profiles')\
                    .select('id, subscription_status')\
                    .execute()
                
                for user in status_result.data or []:
                    status = user.get('subscription_status', 'trial')
                    if status == 'trial':
                        trial_users += 1
                    elif status == 'active':
                        active_subscribers += 1
                    elif status == 'expired':
                        expired_users += 1
            except Exception:
                # subscription_status column doesn't exist, use defaults
                pass
            
            # Conversion rate (trial to paid)
            conversion_rate = (active_subscribers / (active_subscribers + trial_users) * 100) if (active_subscribers + trial_users) > 0 else 0
            
            # Get payment data from script_credit_purchases table
            total_revenue = 0
            successful_payments = 0
            try:
                # Get completed credit purchases (approved payments)
                payments_result = self.supabase.table('script_credit_purchases')\
                    .select('id, amount, status')\
                    .eq('status', 'completed')\
                    .execute()
                
                total_revenue = sum(p.get('amount', 0) for p in payments_result.data or [])
                successful_payments = len(payments_result.data or [])
            except Exception as e:
                # Table doesn't exist or error occurred
                print(f"Error fetching credit purchase revenue: {e}")
                pass
            
            return {
                'total_users': total_users,
                'trial_users': trial_users,
                'active_subscribers': active_subscribers,
                'expired_users': expired_users,
                'trial_expiring_soon': trial_expiring_soon,
                'conversion_rate': round(conversion_rate, 2),
                'total_revenue': total_revenue,
                'successful_payments': successful_payments,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting subscription metrics: {e}")
            return {
                'total_users': 0,
                'trial_users': 0,
                'active_subscribers': 0,
                'expired_users': 0,
                'trial_expiring_soon': 0,
                'conversion_rate': 0,
                'total_revenue': 0,
                'successful_payments': 0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_revenue_details(
        self, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = 'created_at',
        sort_order: str = 'desc'
    ) -> Dict[str, Any]:
        """
        Get detailed revenue breakdown with filters
        
        Args:
            start_date: Start date filter (ISO format)
            end_date: End date filter (ISO format)
            search: Search by email
            sort_by: Column to sort by
            sort_order: Sort direction (asc/desc)
        
        Returns:
            dict: Revenue details with summary and payment list
        """
        try:
            # Build query
            query = self.supabase.table('script_credit_purchases')\
                .select('id, user_id, email, package_type, credits_purchased, amount, currency, status, created_at, verified_at, verified_by, payment_reference, yoco_payment_id')\
                .eq('status', 'completed')
            
            # Apply date filters
            if start_date:
                query = query.gte('created_at', start_date)
            if end_date:
                query = query.lte('created_at', end_date)
            
            # Apply search filter
            if search:
                query = query.ilike('email', f'%{search}%')
            
            # Apply sorting
            ascending = sort_order.lower() == 'asc'
            query = query.order(sort_by, desc=not ascending)
            
            # Execute query
            result = query.execute()
            payments = result.data or []
            
            # Calculate summary stats
            total_revenue = sum(p.get('amount', 0) for p in payments)
            payment_count = len(payments)
            average_payment = total_revenue / payment_count if payment_count > 0 else 0
            
            # Package type breakdown
            package_breakdown = {}
            for payment in payments:
                pkg_type = payment.get('package_type', 'unknown')
                if pkg_type not in package_breakdown:
                    package_breakdown[pkg_type] = {'count': 0, 'revenue': 0}
                package_breakdown[pkg_type]['count'] += 1
                package_breakdown[pkg_type]['revenue'] += payment.get('amount', 0)
            
            return {
                'success': True,
                'summary': {
                    'total_revenue': float(total_revenue),
                    'payment_count': payment_count,
                    'average_payment': float(average_payment),
                    'period': self._get_period_label(start_date, end_date)
                },
                'payments': payments,
                'package_breakdown': package_breakdown,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting revenue details: {e}")
            return {
                'success': False,
                'error': str(e),
                'summary': {
                    'total_revenue': 0,
                    'payment_count': 0,
                    'average_payment': 0,
                    'period': 'Error'
                },
                'payments': [],
                'package_breakdown': {}
            }
    
    def _get_period_label(self, start_date: Optional[str], end_date: Optional[str]) -> str:
        """Generate human-readable period label"""
        if not start_date and not end_date:
            return 'All time'
        elif start_date and not end_date:
            return f'Since {start_date[:10]}'
        elif not start_date and end_date:
            return f'Until {end_date[:10]}'
        else:
            return f'{start_date[:10]} to {end_date[:10]}'
