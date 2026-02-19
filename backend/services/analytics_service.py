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
        Get user activity with filtering and pagination.
        Returns full profile data including credits, signup source, and purchase history.
        
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
            # Build query — select ALL useful profile columns
            select_cols = (
                'id, full_name, email, created_at, '
                'subscription_status, subscription_expires_at, '
                'script_credits, total_scripts_purchased, '
                'is_legacy_beta, script_upload_limit, scripts_uploaded, '
                'signup_source, signup_plan, is_superuser, phone, job_title'
            )
            query = self.supabase.table('profiles')\
                .select(select_cols, count='exact')
            
            # Filter by subscription status
            if status_filter:
                query = query.eq('subscription_status', status_filter)
            
            # Add search filter
            if search:
                query = query.or_(f'full_name.ilike.%{search}%,email.ilike.%{search}%')
            
            # Execute with pagination
            users_result = query\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            total_count = users_result.count or 0
            
            # Batch-fetch script counts and last-active for all users in this page
            user_ids = [u['id'] for u in (users_result.data or [])]
            
            # Get all scripts for these users in one query
            scripts_by_user = {}
            if user_ids:
                all_scripts = self.supabase.table('scripts')\
                    .select('id, user_id, created_at')\
                    .in_('user_id', user_ids)\
                    .order('created_at', desc=True)\
                    .execute()
                
                for script in (all_scripts.data or []):
                    uid = script['user_id']
                    if uid not in scripts_by_user:
                        scripts_by_user[uid] = []
                    scripts_by_user[uid].append(script)
            
            # Get credit purchase summary per user
            purchases_by_user = {}
            if user_ids:
                all_purchases = self.supabase.table('script_credit_purchases')\
                    .select('id, user_id, credits_purchased, amount, status, created_at')\
                    .in_('user_id', user_ids)\
                    .execute()
                
                for purchase in (all_purchases.data or []):
                    uid = purchase['user_id']
                    if uid not in purchases_by_user:
                        purchases_by_user[uid] = []
                    purchases_by_user[uid].append(purchase)
            
            # Get credit usage summary per user
            usage_by_user = {}
            if user_ids:
                all_usage = self.supabase.table('script_credit_usage')\
                    .select('id, user_id, created_at')\
                    .in_('user_id', user_ids)\
                    .execute()
                
                for usage in (all_usage.data or []):
                    uid = usage['user_id']
                    usage_by_user[uid] = usage_by_user.get(uid, 0) + 1
            
            users = []
            for user in users_result.data or []:
                user_id = user['id']
                user_scripts = scripts_by_user.get(user_id, [])
                user_purchases = purchases_by_user.get(user_id, [])
                
                # Last active = most recent script upload
                last_active = user_scripts[0]['created_at'] if user_scripts else None
                
                # Days since signup
                created_at = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
                days_since_signup = (datetime.now(created_at.tzinfo) - created_at).days
                
                # Purchase summary
                completed_purchases = [p for p in user_purchases if p.get('status') == 'completed']
                pending_purchases = [p for p in user_purchases if p.get('status') == 'pending']
                total_spent = sum(p.get('amount', 0) for p in completed_purchases)
                total_credits_bought = sum(p.get('credits_purchased', 0) for p in completed_purchases)
                
                users.append({
                    'user_id': user_id,
                    'name': user.get('full_name', 'Unknown'),
                    'email': user.get('email'),
                    'phone': user.get('phone'),
                    'job_title': user.get('job_title'),
                    'subscription_status': user.get('subscription_status', 'trial'),
                    'subscription_expires_at': user.get('subscription_expires_at'),
                    'script_credits': user.get('script_credits', 0),
                    'total_scripts_purchased': user.get('total_scripts_purchased', 0),
                    'is_legacy_beta': user.get('is_legacy_beta', False),
                    'is_superuser': user.get('is_superuser', False),
                    'script_upload_limit': user.get('script_upload_limit'),
                    'scripts_uploaded': user.get('scripts_uploaded', 0),
                    'signup_source': user.get('signup_source', 'direct'),
                    'signup_plan': user.get('signup_plan'),
                    'script_count': len(user_scripts),
                    'last_active': last_active,
                    'days_since_signup': days_since_signup,
                    'created_at': user['created_at'],
                    # Credit economy
                    'credits_remaining': user.get('script_credits', 0),
                    'credits_used': usage_by_user.get(user_id, 0),
                    'total_spent': total_spent,
                    'total_credits_bought': total_credits_bought,
                    'purchase_count': len(completed_purchases),
                    'pending_purchases': len(pending_purchases),
                })
            
            return {
                'users': users,
                'total': total_count,
                'limit': limit,
                'offset': offset
            }
            
        except Exception as e:
            print(f"Error getting user activity: {e}")
            import traceback
            traceback.print_exc()
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
        Get comprehensive script analytics for admin dashboard.
        
        Returns rich data for:
        - Hero metrics (at-a-glance KPIs)
        - Upload activity timeline
        - Scene composition (INT/EXT, Day/Night)
        - Parser quality (ScreenPy grammar vs regex)
        - Feature adoption across scripts
        - Per-script detail rows with drill-down metadata
        """
        try:
            # ── 1. Fetch all scripts with extended columns ──
            scripts_result = self.supabase.table('scripts')\
                .select('id, title, user_id, total_pages, analysis_status, created_at, '
                        'writer_name, total_story_days, is_locked, genre, current_revision_color')\
                .order('created_at', desc=True)\
                .execute()
            scripts_data = scripts_result.data or []
            total_scripts = len(scripts_data)
            
            # ── 2. Fetch all scenes with parser + composition columns ──
            scenes_result = self.supabase.table('scenes')\
                .select('id, script_id, scene_number, setting, time_of_day, int_ext, '
                        'characters, parse_method, shot_type, is_omitted, is_manual, story_day')\
                .execute()
            scenes_data = scenes_result.data or []
            total_scenes = len(scenes_data)
            
            # Index scenes by script_id for O(1) lookup
            scenes_by_script = {}
            for scene in scenes_data:
                sid = scene.get('script_id')
                if sid not in scenes_by_script:
                    scenes_by_script[sid] = []
                scenes_by_script[sid].append(scene)
            
            # ── 3. Batch-fetch user profiles ──
            user_ids = list(set(s['user_id'] for s in scripts_data if s.get('user_id')))
            users_map = {}
            if user_ids:
                users_result = self.supabase.table('profiles')\
                    .select('id, full_name, email, subscription_status')\
                    .in_('id', user_ids)\
                    .execute()
                for u in (users_result.data or []):
                    users_map[u['id']] = u
            
            # ── 4. Batch-fetch feature adoption counts ──
            script_ids = [s['id'] for s in scripts_data]
            
            feature_counts = {}  # { script_id: { feature: count } }
            feature_tables = [
                ('reports', 'reports', 'script_id'),
                ('dept_items', 'department_items', 'script_id'),
                ('dept_notes', 'department_notes', 'script_id'),
                ('schedules', 'shooting_schedules', 'script_id'),
                ('team_members', 'script_members', 'script_id'),
                ('extractions', 'extraction_metadata', 'script_id'),
                ('threads', 'threads', 'script_id'),
            ]
            
            for feature_key, table_name, fk_col in feature_tables:
                try:
                    result = self.supabase.table(table_name)\
                        .select(fk_col)\
                        .in_(fk_col, script_ids)\
                        .execute()
                    for row in (result.data or []):
                        sid = row[fk_col]
                        if sid not in feature_counts:
                            feature_counts[sid] = {}
                        feature_counts[sid][feature_key] = feature_counts[sid].get(feature_key, 0) + 1
                except Exception:
                    pass
            
            # ── 5. Build per-script metrics ──
            all_scripts_detail = []
            total_pages = 0
            total_grammar = 0
            total_regex = 0
            total_int = 0
            total_ext = 0
            total_int_ext = 0
            total_day = 0
            total_night = 0
            total_other_time = 0
            total_characters = 0
            total_locations = 0
            
            for script in scripts_data:
                script_id = script['id']
                script_scenes = scenes_by_script.get(script_id, [])
                pages = script.get('total_pages') or 0
                total_pages += pages
                
                # Characters & locations
                chars = set()
                locs = set()
                grammar_count = 0
                regex_count = 0
                int_count = 0
                ext_count = 0
                int_ext_count = 0
                day_count = 0
                night_count = 0
                other_time_count = 0
                shot_types_found = 0
                
                for scene in script_scenes:
                    # Characters
                    scene_chars = scene.get('characters', []) or []
                    if isinstance(scene_chars, list):
                        for c in scene_chars:
                            if isinstance(c, dict) and 'name' in c:
                                chars.add(c['name'])
                            elif isinstance(c, str):
                                chars.add(c)
                    
                    # Locations
                    setting = scene.get('setting', '')
                    if setting:
                        locs.add(setting)
                    
                    # Parser
                    pm = scene.get('parse_method', '')
                    if pm == 'grammar':
                        grammar_count += 1
                    else:
                        regex_count += 1
                    
                    # INT/EXT
                    ie = (scene.get('int_ext') or '').upper()
                    if ie in ('INT', 'INTERIOR'):
                        int_count += 1
                    elif ie in ('EXT', 'EXTERIOR'):
                        ext_count += 1
                    elif 'INT' in ie and 'EXT' in ie:
                        int_ext_count += 1
                    
                    # Time of day
                    tod = (scene.get('time_of_day') or '').upper()
                    if 'DAY' in tod:
                        day_count += 1
                    elif 'NIGHT' in tod:
                        night_count += 1
                    elif tod:
                        other_time_count += 1
                    
                    # Shot type
                    if scene.get('shot_type'):
                        shot_types_found += 1
                
                total_grammar += grammar_count
                total_regex += regex_count
                total_int += int_count
                total_ext += ext_count
                total_int_ext += int_ext_count
                total_day += day_count
                total_night += night_count
                total_other_time += other_time_count
                total_characters += len(chars)
                total_locations += len(locs)
                
                # User info
                user = users_map.get(script.get('user_id'), {})
                
                # Feature adoption for this script
                features = feature_counts.get(script_id, {})
                features_used = sum(1 for v in features.values() if v > 0)
                
                all_scripts_detail.append({
                    'id': script_id,
                    'title': script.get('title', 'Untitled'),
                    'writer_name': script.get('writer_name'),
                    'genre': script.get('genre'),
                    'total_pages': pages,
                    'scene_count': len(script_scenes),
                    'character_count': len(chars),
                    'location_count': len(locs),
                    'story_days': script.get('total_story_days', 0),
                    'is_locked': script.get('is_locked', False),
                    'revision_color': script.get('current_revision_color', 'white'),
                    'analysis_status': script.get('analysis_status', 'pending'),
                    'uploaded_at': script['created_at'],
                    # Owner
                    'owner_name': user.get('full_name', 'Unknown'),
                    'owner_email': user.get('email', ''),
                    'subscription_status': user.get('subscription_status', 'trial'),
                    # Scene composition
                    'int_scenes': int_count,
                    'ext_scenes': ext_count,
                    'int_ext_scenes': int_ext_count,
                    'day_scenes': day_count,
                    'night_scenes': night_count,
                    'other_time_scenes': other_time_count,
                    # Parser quality
                    'grammar_scenes': grammar_count,
                    'regex_scenes': regex_count,
                    'grammar_rate': round(grammar_count / len(script_scenes) * 100, 1) if script_scenes else 0,
                    # Shot types
                    'shot_type_count': shot_types_found,
                    # Feature adoption
                    'features': features,
                    'features_used': features_used,
                })
            
            # ── 6. Upload activity timeline (by date) ──
            upload_timeline = {}
            for script in scripts_data:
                date_key = script['created_at'][:10]  # YYYY-MM-DD
                if date_key not in upload_timeline:
                    upload_timeline[date_key] = {'date': date_key, 'count': 0, 'pages': 0, 'users': set()}
                upload_timeline[date_key]['count'] += 1
                upload_timeline[date_key]['pages'] += script.get('total_pages') or 0
                if script.get('user_id'):
                    upload_timeline[date_key]['users'].add(script['user_id'])
            
            # Convert sets to counts for JSON serialization
            timeline_list = []
            for entry in sorted(upload_timeline.values(), key=lambda x: x['date']):
                timeline_list.append({
                    'date': entry['date'],
                    'count': entry['count'],
                    'pages': entry['pages'],
                    'unique_users': len(entry['users'])
                })
            
            # ── 7. Global feature adoption summary ──
            feature_adoption_summary = {}
            for feature_key, _, _ in feature_tables:
                total_usage = sum(
                    feature_counts.get(sid, {}).get(feature_key, 0) 
                    for sid in script_ids
                )
                scripts_using = sum(
                    1 for sid in script_ids 
                    if feature_counts.get(sid, {}).get(feature_key, 0) > 0
                )
                feature_adoption_summary[feature_key] = {
                    'total_usage': total_usage,
                    'scripts_using': scripts_using,
                    'adoption_rate': round(scripts_using / total_scripts * 100, 1) if total_scripts > 0 else 0
                }
            
            # ── 8. Unique uploaders ──
            unique_uploaders = len(set(s.get('user_id') for s in scripts_data if s.get('user_id')))
            
            # ── 9. This month's scripts ──
            first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0).isoformat()[:10]
            scripts_this_month = sum(1 for s in scripts_data if (s.get('created_at') or '')[:10] >= first_of_month)
            
            # ── 10. Avg pages ──
            avg_pages = round(total_pages / total_scripts, 1) if total_scripts > 0 else 0
            avg_scenes = round(total_scenes / total_scripts, 1) if total_scripts > 0 else 0
            
            # ── 11. ScreenPy parse rate ──
            grammar_rate = round(total_grammar / total_scenes * 100, 1) if total_scenes > 0 else 0
            
            return {
                'overview': {
                    'total_scripts': total_scripts,
                    'total_scenes': total_scenes,
                    'total_pages': total_pages,
                    'unique_uploaders': unique_uploaders,
                    'scripts_this_month': scripts_this_month,
                    'avg_pages_per_script': avg_pages,
                    'avg_scenes_per_script': avg_scenes,
                    'total_characters': total_characters,
                    'total_locations': total_locations,
                    'grammar_parse_rate': grammar_rate,
                },
                'scene_distribution': {
                    'int_scenes': total_int,
                    'ext_scenes': total_ext,
                    'int_ext_scenes': total_int_ext,
                    'day_scenes': total_day,
                    'night_scenes': total_night,
                    'other_time_scenes': total_other_time,
                },
                'parser_quality': {
                    'total_grammar': total_grammar,
                    'total_regex': total_regex,
                    'grammar_rate': grammar_rate,
                },
                'upload_timeline': timeline_list,
                'feature_adoption': feature_adoption_summary,
                'all_scripts': all_scripts_detail,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting script analytics: {e}")
            import traceback
            traceback.print_exc()
            return {
                'overview': {},
                'scene_distribution': {},
                'parser_quality': {},
                'upload_timeline': [],
                'feature_adoption': {},
                'all_scripts': [],
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
