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
            now = datetime.now()
            thirty_days_ago = (now - timedelta(days=30)).isoformat()
            first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

            # Total users + new this month in one query
            users_result = self.supabase.table('profiles')\
                .select('id, created_at')\
                .execute()
            total_users = len(users_result.data or [])
            new_users_this_month = sum(
                1 for u in (users_result.data or [])
                if (u.get('created_at') or '') >= first_of_month
            )

            # Active users = unique uploaders in last 30 days
            active_scripts = self.supabase.table('scripts')\
                .select('user_id')\
                .gte('created_at', thirty_days_ago)\
                .execute()
            active_users = len(set(
                s['user_id'] for s in (active_scripts.data or []) if s.get('user_id')
            ))

            # Total scripts + this month
            scripts_result = self.supabase.table('scripts')\
                .select('id, created_at')\
                .execute()
            total_scripts = len(scripts_result.data or [])
            scripts_this_month = sum(
                1 for s in (scripts_result.data or [])
                if (s.get('created_at') or '') >= first_of_month
            )

            # Total scenes
            scenes_result = self.supabase.table('scenes')\
                .select('id', count='exact')\
                .execute()
            total_scenes = scenes_result.count or 0

            # Analysis jobs — table may not exist
            total_jobs = 0
            completed_jobs = 0
            failed_jobs = 0
            try:
                jobs_result = self.supabase.table('analysis_jobs')\
                    .select('id, status')\
                    .execute()
                total_jobs = len(jobs_result.data or [])
                for job in (jobs_result.data or []):
                    if job.get('status') == 'completed':
                        completed_jobs += 1
                    elif job.get('status') == 'failed':
                        failed_jobs += 1
            except Exception:
                pass

            # Success rate: if no jobs table, derive from scripts analysis_status
            if total_jobs == 0:
                complete_scripts = sum(
                    1 for s in (scripts_result.data or [])
                    if s.get('analysis_status') == 'complete'
                )
                success_rate = round(complete_scripts / total_scripts * 100, 2) if total_scripts > 0 else 100.0
                failed_jobs = sum(
                    1 for s in (scripts_result.data or [])
                    if s.get('analysis_status') == 'failed'
                )
            else:
                success_rate = round(completed_jobs / total_jobs * 100, 2) if total_jobs > 0 else 0.0

            return {
                'total_users': total_users,
                'active_users': active_users,
                'new_users_this_month': new_users_this_month,
                'total_scripts': total_scripts,
                'scripts_this_month': scripts_this_month,
                'total_scenes': total_scenes,
                'total_analysis_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'success_rate': success_rate,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error getting global stats: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total_users': 0,
                'active_users': 0,
                'new_users_this_month': 0,
                'total_scripts': 0,
                'scripts_this_month': 0,
                'total_scenes': 0,
                'total_analysis_jobs': 0,
                'completed_jobs': 0,
                'failed_jobs': 0,
                'success_rate': 0,
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
        Get recent platform activity events.
        Uses batch queries to avoid N+1 problems.

        Args:
            limit: Maximum number of events to return

        Returns:
            list: Recent activity events with timestamps and details
        """
        try:
            activities = []

            # ── 1. Recent user signups ──
            recent_users = self.supabase.table('profiles')\
                .select('id, full_name, email, created_at')\
                .order('created_at', desc=True)\
                .limit(20)\
                .execute()

            for user in (recent_users.data or []):
                activities.append({
                    'type': 'user_signup',
                    'user_name': user.get('full_name') or 'Unknown',
                    'user_email': user.get('email'),
                    'timestamp': user['created_at'],
                    'description': f"{user.get('full_name') or 'New user'} signed up"
                })

            # ── 2. Recent script uploads — batch-fetch user profiles ──
            recent_scripts = self.supabase.table('scripts')\
                .select('id, title, user_id, created_at')\
                .order('created_at', desc=True)\
                .limit(20)\
                .execute()

            # Batch-fetch all user profiles needed for scripts
            script_user_ids = list(set(
                s['user_id'] for s in (recent_scripts.data or []) if s.get('user_id')
            ))
            users_map: Dict[str, str] = {}
            if script_user_ids:
                users_result = self.supabase.table('profiles')\
                    .select('id, full_name')\
                    .in_('id', script_user_ids)\
                    .execute()
                users_map = {
                    u['id']: (u.get('full_name') or 'Unknown')
                    for u in (users_result.data or [])
                }

            for script in (recent_scripts.data or []):
                user_name = users_map.get(script.get('user_id', ''), 'Unknown')
                activities.append({
                    'type': 'script_upload',
                    'user_name': user_name,
                    'script_title': script.get('title', 'Untitled'),
                    'script_id': script['id'],
                    'timestamp': script['created_at'],
                    'description': f"{user_name} uploaded '{script.get('title', 'Untitled')}'"
                })

            # ── 3. Recent payment approvals ──
            try:
                recent_payments = self.supabase.table('script_credit_purchases')\
                    .select('id, user_id, email, credits_purchased, amount, status, paid_at, created_at')\
                    .eq('status', 'completed')\
                    .order('paid_at', desc=True)\
                    .limit(10)\
                    .execute()

                for payment in (recent_payments.data or []):
                    ts = payment.get('paid_at') or payment.get('created_at', '')
                    activities.append({
                        'type': 'payment_approved',
                        'user_name': payment.get('email', 'Unknown'),
                        'user_email': payment.get('email'),
                        'amount': float(payment.get('amount') or 0),
                        'credits': payment.get('credits_purchased', 0),
                        'timestamp': ts,
                        'description': f"Payment of R{payment.get('amount', 0)} approved ({payment.get('credits_purchased', 0)} credits)"
                    })
            except Exception:
                pass

            # ── 4. Sort all activities by timestamp (most recent first) ──
            activities.sort(key=lambda x: x.get('timestamp') or '', reverse=True)

            return activities[:limit]

        except Exception as e:
            print(f"Error getting recent activity: {e}")
            import traceback
            traceback.print_exc()
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
            # Generate date range — use at least 14 days for meaningful charts
            effective_days = max(days, 14)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=effective_days)

            # Get scripts within the window
            all_scripts = self.supabase.table('scripts')\
                .select('id, created_at')\
                .gte('created_at', start_date.isoformat())\
                .execute()

            # Get ALL users for cumulative growth chart (not just window)
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
        Get script analysis statistics.

        Args:
            days: Number of days to look back

        Returns:
            dict: Script analysis metrics
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            # Scripts uploaded in period — use correct column names
            scripts_result = self.supabase.table('scripts')\
                .select('id, title, created_at, analysis_status, total_pages')\
                .gte('created_at', cutoff_date)\
                .order('created_at', desc=True)\
                .execute()

            total_scripts = len(scripts_result.data or [])

            # Analysis status breakdown
            status_counts = {
                'pending': 0,
                'in_progress': 0,
                'complete': 0,
                'failed': 0
            }
            for script in (scripts_result.data or []):
                status = script.get('analysis_status', 'pending')
                if status in status_counts:
                    status_counts[status] += 1

            # Scene count for scripts in this period
            script_ids = [s['id'] for s in (scripts_result.data or [])]
            total_scenes = 0
            if script_ids:
                scenes_result = self.supabase.table('scenes')\
                    .select('id', count='exact')\
                    .in_('script_id', script_ids)\
                    .execute()
                total_scenes = scenes_result.count or 0

            avg_scenes = round(total_scenes / total_scripts, 1) if total_scripts > 0 else 0

            # Analysis jobs — guard against missing table
            total_jobs = 0
            avg_duration = 0.0
            try:
                jobs_result = self.supabase.table('analysis_jobs')\
                    .select('id, status, created_at, started_at, completed_at')\
                    .gte('created_at', cutoff_date)\
                    .execute()
                total_jobs = len(jobs_result.data or [])
                total_duration = 0
                completed_count = 0
                for job in (jobs_result.data or []):
                    if job.get('status') == 'completed' and job.get('started_at') and job.get('completed_at'):
                        started = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
                        completed_dt = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
                        total_duration += (completed_dt - started).total_seconds()
                        completed_count += 1
                avg_duration = round(total_duration / completed_count, 2) if completed_count > 0 else 0.0
            except Exception:
                pass

            return {
                'period_days': days,
                'total_scripts': total_scripts,
                'total_scenes': total_scenes,
                'avg_scenes_per_script': avg_scenes,
                'status_breakdown': status_counts,
                'total_jobs': total_jobs,
                'avg_analysis_time_seconds': avg_duration,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error getting script stats: {e}")
            import traceback
            traceback.print_exc()
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
        Get subscription and conversion metrics.

        Returns:
            dict: Subscription stats including trial conversions, churn, revenue.
        """
        try:
            now = datetime.now()
            seven_days_from_now = (now + timedelta(days=7)).isoformat()

            # Single query — get all subscription fields at once
            users_result = self.supabase.table('profiles')\
                .select('id, subscription_status, subscription_expires_at')\
                .execute()

            total_users = len(users_result.data or [])
            trial_users = 0
            active_subscribers = 0
            expired_users = 0
            trial_expiring_soon = 0

            for user in (users_result.data or []):
                status = user.get('subscription_status') or 'trial'
                if status == 'trial':
                    trial_users += 1
                    # Expiring soon = expires_at is set and within 7 days
                    expires_at = user.get('subscription_expires_at')
                    if expires_at and expires_at <= seven_days_from_now:
                        trial_expiring_soon += 1
                elif status == 'active':
                    active_subscribers += 1
                elif status == 'expired':
                    expired_users += 1

            # Conversion rate (trial to paid)
            total_addressable = active_subscribers + trial_users
            conversion_rate = round(
                active_subscribers / total_addressable * 100, 2
            ) if total_addressable > 0 else 0.0

            # Revenue from completed credit purchases
            total_revenue = 0.0
            successful_payments = 0
            try:
                payments_result = self.supabase.table('script_credit_purchases')\
                    .select('id, amount, status')\
                    .eq('status', 'completed')\
                    .execute()
                # amount is numeric in DB — cast to float to avoid Decimal serialisation issues
                total_revenue = round(
                    sum(float(p.get('amount') or 0) for p in (payments_result.data or [])), 2
                )
                successful_payments = len(payments_result.data or [])
            except Exception as e:
                print(f"Error fetching credit purchase revenue: {e}")

            return {
                'total_users': total_users,
                'trial_users': trial_users,
                'active_subscribers': active_subscribers,
                'expired_users': expired_users,
                'trial_expiring_soon': trial_expiring_soon,
                'conversion_rate': conversion_rate,
                'total_revenue': total_revenue,
                'successful_payments': successful_payments,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error getting subscription metrics: {e}")
            import traceback
            traceback.print_exc()
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
            
            # Normalise amount to float for all payments (Postgres numeric → Decimal)
            for p in payments:
                p['amount'] = float(p.get('amount') or 0)

            # Calculate summary stats
            total_revenue = sum(p['amount'] for p in payments)
            payment_count = len(payments)
            average_payment = total_revenue / payment_count if payment_count > 0 else 0.0

            # Package type breakdown
            package_breakdown = {}
            for payment in payments:
                pkg_type = payment.get('package_type', 'unknown')
                if pkg_type not in package_breakdown:
                    package_breakdown[pkg_type] = {'count': 0, 'revenue': 0.0}
                package_breakdown[pkg_type]['count'] += 1
                package_breakdown[pkg_type]['revenue'] += payment['amount']

            return {
                'success': True,
                'summary': {
                    'total_revenue': round(total_revenue, 2),
                    'payment_count': payment_count,
                    'average_payment': round(average_payment, 2),
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
