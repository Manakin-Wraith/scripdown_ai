"""
Feedback Service - Business logic for feedback submission and management
Handles rate limiting, screenshot uploads, and feedback CRUD operations.
"""

from datetime import datetime, timedelta
import uuid
import os
from db.supabase_client import get_supabase_admin


def check_rate_limit(user_id):
    """
    Check if user has exceeded rate limit (5 submissions per day).
    
    Args:
        user_id: User's UUID
    
    Returns:
        bool: True if user can submit, False if rate limit exceeded
    """
    try:
        supabase = get_supabase_admin()
        
        # Get submissions in last 24 hours
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        
        result = supabase.table('feedback_submissions')\
            .select('id', count='exact')\
            .eq('user_id', user_id)\
            .gte('created_at', yesterday)\
            .execute()
        
        count = result.count if hasattr(result, 'count') else len(result.data)
        
        return count < 5
        
    except Exception as e:
        print(f"Error checking rate limit: {e}")
        # Allow submission on error (fail open)
        return True


def upload_screenshot(user_id, screenshot_file):
    """
    Upload screenshot to Supabase Storage.
    
    Args:
        user_id: User's UUID
        screenshot_file: File object from request.files
    
    Returns:
        str: Public URL of uploaded screenshot, or None on error
    """
    try:
        if not screenshot_file:
            return None
        
        # Validate file size (5MB max)
        screenshot_file.seek(0, os.SEEK_END)
        file_size = screenshot_file.tell()
        screenshot_file.seek(0)
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            print("Screenshot file too large")
            return None
        
        # Validate MIME type
        allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
        if screenshot_file.content_type not in allowed_types:
            print(f"Invalid file type: {screenshot_file.content_type}")
            return None
        
        # Generate unique filename
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        ext = screenshot_file.filename.split('.')[-1] if '.' in screenshot_file.filename else 'png'
        filename = f"{user_id}/{uuid.uuid4()}_{timestamp}.{ext}"
        
        # Upload to Supabase Storage
        supabase = get_supabase_admin()
        
        file_bytes = screenshot_file.read()
        
        result = supabase.storage.from_('feedback-screenshots').upload(
            filename,
            file_bytes,
            file_options={
                'content-type': screenshot_file.content_type,
                'cache-control': '3600',
                'upsert': 'false'
            }
        )
        
        # Get public URL
        public_url = supabase.storage.from_('feedback-screenshots').get_public_url(filename)
        
        return public_url
        
    except Exception as e:
        print(f"Error uploading screenshot: {e}")
        return None


def submit_feedback(user_id, category, priority, subject, description, screenshot_file=None, page_context=None):
    """
    Submit new feedback.
    
    Args:
        user_id: User's UUID
        category: 'bug', 'feature', 'ui_ux', or 'general'
        priority: 'low', 'medium', or 'high'
        subject: Feedback subject (max 200 chars)
        description: Feedback description (max 2000 chars)
        screenshot_file: Optional screenshot file
        page_context: Optional dict with page context
    
    Returns:
        dict: {'id': feedback_id, 'screenshot_url': url} or {'error': message}
    """
    try:
        supabase = get_supabase_admin()
        
        # Upload screenshot if provided
        screenshot_url = None
        if screenshot_file:
            screenshot_url = upload_screenshot(user_id, screenshot_file)
        
        # Prepare feedback data
        feedback_data = {
            'user_id': user_id,
            'category': category,
            'priority': priority,
            'subject': subject,
            'description': description,
            'screenshot_url': screenshot_url,
            'page_context': page_context or {},
            'status': 'new'
        }
        
        # Insert feedback
        result = supabase.table('feedback_submissions')\
            .insert(feedback_data)\
            .execute()
        
        if not result.data:
            return {'error': 'Failed to insert feedback'}
        
        feedback_id = result.data[0]['id']
        
        # Get user info for emails and notifications
        user_result = supabase.table('profiles')\
            .select('email, full_name')\
            .eq('id', user_id)\
            .single()\
            .execute()
        
        user_email = user_result.data.get('email') if user_result.data else None
        user_name = user_result.data.get('full_name', '') if user_result.data else ''
        
        # Send confirmation email to user (async, don't block on failure)
        try:
            from services.email_service import send_feedback_confirmation_email
            
            if user_email:
                send_feedback_confirmation_email(
                    user_email=user_email,
                    user_name=user_name,
                    feedback_id=feedback_id,
                    category=category,
                    subject=subject
                )
        except Exception as email_error:
            print(f"Error sending confirmation email: {email_error}")
        
        # Create in-app notifications for all superusers
        try:
            # Get all superuser IDs
            superusers = supabase.table('profiles')\
                .select('id, email')\
                .eq('is_superuser', True)\
                .execute()
            
            if superusers.data:
                # Create notification for each superuser
                for admin in superusers.data:
                    notification_data = {
                        'user_id': admin['id'],
                        'type': 'feedback_submitted',
                        'title': f'New {category.replace("_", "/")} feedback',
                        'message': f'{user_name or "User"} submitted: {subject}',
                        'data': {
                            'feedback_id': feedback_id,
                            'category': category,
                            'priority': priority,
                            'user_email': user_email
                        }
                    }
                    supabase.table('notifications').insert(notification_data).execute()
        except Exception as notif_error:
            print(f"Error creating admin notifications: {notif_error}")
        
        # Send email alert to admins for high-priority or bug feedback
        if priority == 'high' or category == 'bug':
            try:
                from services.email_service import send_admin_feedback_alert_email
                
                # Get superuser emails
                superusers = supabase.table('profiles')\
                    .select('email')\
                    .eq('is_superuser', True)\
                    .execute()
                
                if superusers.data:
                    admin_emails = [admin['email'] for admin in superusers.data if admin.get('email')]
                    
                    if admin_emails:
                        send_admin_feedback_alert_email(
                            feedback_id=feedback_id,
                            user_name=user_name,
                            user_email=user_email or 'Unknown',
                            category=category,
                            priority=priority,
                            subject=subject,
                            description=description,
                            admin_emails=admin_emails
                        )
            except Exception as admin_email_error:
                print(f"Error sending admin alert email: {admin_email_error}")
        
        return {
            'id': feedback_id,
            'screenshot_url': screenshot_url
        }
        
    except Exception as e:
        print(f"Error submitting feedback: {e}")
        return {'error': str(e)}


def get_user_feedback(user_id, page=1, limit=20):
    """
    Get feedback submissions for a specific user.
    
    Args:
        user_id: User's UUID
        page: Page number (1-indexed)
        limit: Items per page
    
    Returns:
        dict: {'feedback': [...], 'total': count, 'page': page, 'pages': total_pages}
    """
    try:
        supabase = get_supabase_admin()
        
        offset = (page - 1) * limit
        
        # Get total count
        count_result = supabase.table('feedback_submissions')\
            .select('id', count='exact')\
            .eq('user_id', user_id)\
            .execute()
        
        total = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
        
        # Get feedback
        result = supabase.table('feedback_submissions')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        total_pages = (total + limit - 1) // limit
        
        return {
            'feedback': result.data,
            'total': total,
            'page': page,
            'pages': total_pages
        }
        
    except Exception as e:
        print(f"Error fetching user feedback: {e}")
        return {'error': str(e)}


def get_all_feedback(page=1, limit=20, category=None, status=None, priority=None, search=None):
    """
    Get all feedback submissions with filters (superuser only).
    
    Args:
        page: Page number
        limit: Items per page
        category: Filter by category
        status: Filter by status
        priority: Filter by priority
        search: Search in subject/description
    
    Returns:
        dict: {'feedback': [...], 'total': count, 'page': page, 'pages': total_pages}
    """
    try:
        supabase = get_supabase_admin()
        
        offset = (page - 1) * limit
        
        # Build query - fetch feedback without join first
        query = supabase.table('feedback_submissions').select('*', count='exact')
        
        if category:
            query = query.eq('category', category)
        if status:
            query = query.eq('status', status)
        if priority:
            query = query.eq('priority', priority)
        if search:
            # Full-text search on subject and description
            query = query.or_(f'subject.ilike.%{search}%,description.ilike.%{search}%')
        
        # Get total count
        count_result = query.execute()
        total = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
        
        # Get feedback with pagination
        result = query.order('created_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        total_pages = (total + limit - 1) // limit
        
        # Fetch user profiles separately for each feedback item
        feedback_list = []
        for item in result.data:
            feedback_item = {**item}
            
            # Fetch user profile data
            try:
                profile_result = supabase.table('profiles')\
                    .select('email, full_name')\
                    .eq('id', item['user_id'])\
                    .single()\
                    .execute()
                
                if profile_result.data:
                    feedback_item['user_email'] = profile_result.data.get('email')
                    feedback_item['user_name'] = profile_result.data.get('full_name')
            except Exception as profile_error:
                print(f"Error fetching profile for user {item['user_id']}: {profile_error}")
                feedback_item['user_email'] = None
                feedback_item['user_name'] = None
            
            feedback_list.append(feedback_item)
        
        return {
            'feedback': feedback_list,
            'total': total,
            'page': page,
            'pages': total_pages
        }
        
    except Exception as e:
        print(f"Error fetching all feedback: {e}")
        return {'error': str(e)}


def get_feedback_by_id(feedback_id, user_id):
    """
    Get single feedback submission by ID.
    
    Args:
        feedback_id: Feedback UUID
        user_id: Requesting user's UUID
    
    Returns:
        dict: Feedback data or {'error': message}
    """
    try:
        supabase = get_supabase_admin()
        
        # Check if user is superuser
        profile = supabase.table('profiles')\
            .select('is_superuser')\
            .eq('id', user_id)\
            .single()\
            .execute()
        
        is_superuser = profile.data.get('is_superuser', False) if profile.data else False
        
        # Get feedback
        result = supabase.table('feedback_submissions')\
            .select('*')\
            .eq('id', feedback_id)\
            .single()\
            .execute()
        
        if not result.data:
            return {'error': 'Feedback not found'}
        
        # Check access
        if not is_superuser and result.data['user_id'] != user_id:
            return {'error': 'Forbidden'}
        
        # Fetch user profile data separately
        feedback_item = {**result.data}
        try:
            profile_result = supabase.table('profiles')\
                .select('email, full_name')\
                .eq('id', result.data['user_id'])\
                .single()\
                .execute()
            
            if profile_result.data:
                feedback_item['user_email'] = profile_result.data.get('email')
                feedback_item['user_name'] = profile_result.data.get('full_name')
        except Exception as profile_error:
            print(f"Error fetching profile: {profile_error}")
            feedback_item['user_email'] = None
            feedback_item['user_name'] = None
        
        return feedback_item
        
    except Exception as e:
        print(f"Error fetching feedback by ID: {e}")
        return {'error': str(e)}


def update_feedback_status(feedback_id, status, admin_notes=None, resolved_by=None):
    """
    Update feedback status.
    
    Args:
        feedback_id: Feedback UUID
        status: New status
        admin_notes: Optional admin notes
        resolved_by: User ID of resolver (for resolved status)
    
    Returns:
        dict: Updated feedback or {'error': message}
    """
    try:
        supabase = get_supabase_admin()
        
        update_data = {'status': status}
        
        if admin_notes:
            update_data['admin_notes'] = admin_notes
        
        if resolved_by and status == 'resolved':
            update_data['resolved_by'] = resolved_by
            update_data['resolved_at'] = datetime.utcnow().isoformat()
        
        result = supabase.table('feedback_submissions')\
            .update(update_data)\
            .eq('id', feedback_id)\
            .execute()
        
        if not result.data:
            return {'error': 'Feedback not found'}
        
        return result.data[0]
        
    except Exception as e:
        print(f"Error updating feedback status: {e}")
        return {'error': str(e)}


def delete_feedback(feedback_id, user_id):
    """
    Delete feedback submission (superuser only).
    
    Args:
        feedback_id: Feedback UUID
        user_id: Requesting user's UUID
    
    Returns:
        dict: {'success': True} or {'error': message}
    """
    try:
        supabase = get_supabase_admin()
        
        # Check if user is superuser
        profile = supabase.table('profiles')\
            .select('is_superuser')\
            .eq('id', user_id)\
            .single()\
            .execute()
        
        is_superuser = profile.data.get('is_superuser', False) if profile.data else False
        
        if not is_superuser:
            return {'error': 'Forbidden: Only superusers can delete feedback'}
        
        # Delete the feedback
        result = supabase.table('feedback_submissions')\
            .delete()\
            .eq('id', feedback_id)\
            .execute()
        
        if not result.data:
            return {'error': 'Feedback not found'}
        
        return {'success': True, 'message': 'Feedback deleted successfully'}
        
    except Exception as e:
        print(f"Error deleting feedback: {e}")
        return {'error': str(e)}


def send_feedback_reply(feedback_id, reply_message, admin_user_id):
    """
    Send email reply to feedback submitter.
    
    Args:
        feedback_id: Feedback UUID
        reply_message: Admin's reply message
        admin_user_id: Admin user ID
    
    Returns:
        dict: {'success': True} or {'error': message}
    """
    try:
        supabase = get_supabase_admin()
        
        # Get feedback and user info
        feedback = supabase.table('feedback_submissions')\
            .select('*')\
            .eq('id', feedback_id)\
            .single()\
            .execute()
        
        if not feedback.data:
            return {'error': 'Feedback not found'}
        
        # Get user profile data
        user_profile = supabase.table('profiles')\
            .select('email, full_name')\
            .eq('id', feedback.data['user_id'])\
            .single()\
            .execute()
        
        if not user_profile.data:
            return {'error': 'User profile not found'}
        
        # Send reply email
        from services.email_service import send_feedback_reply_email
        
        send_feedback_reply_email(
            user_email=user_profile.data['email'],
            user_name=user_profile.data['full_name'],
            feedback_id=feedback_id,
            subject=feedback.data['subject'],
            category=feedback.data['category'],
            reply_message=reply_message
        )
        
        # Update last_reply_sent timestamp
        supabase.table('feedback_submissions')\
            .update({'last_reply_sent': datetime.utcnow().isoformat()})\
            .eq('id', feedback_id)\
            .execute()
        
        return {'success': True}
        
    except Exception as e:
        print(f"Error sending feedback reply: {e}")
        return {'error': str(e)}


def get_feedback_stats():
    """
    Get feedback statistics from the feedback_stats view.
    
    Returns:
        dict: Feedback statistics
    """
    try:
        supabase = get_supabase_admin()
        
        result = supabase.table('feedback_stats')\
            .select('*')\
            .single()\
            .execute()
        
        return result.data if result.data else {}
        
    except Exception as e:
        print(f"Error fetching feedback stats: {e}")
        return {'error': str(e)}
