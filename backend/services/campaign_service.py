"""
Campaign Service - Business logic for email campaigns
Handles campaign creation, user segmentation, and campaign execution
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from db.supabase_client import get_supabase_admin
from services.campaign_email_service import send_campaign_batch
import re


class CampaignService:
    """Service for managing email campaigns"""
    
    def __init__(self):
        # Use admin client to bypass RLS for campaign management
        self.supabase = get_supabase_admin()
    
    def create_campaign(
        self, 
        name: str, 
        template_id: str, 
        audience_filter: Dict[str, Any],
        created_by: str,
        description: str = None,
        scheduled_at: str = None,
        manual_recipients: str = None,
        template_variables: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Create a new email campaign
        
        Args:
            name: Campaign name
            template_id: Email template UUID
            audience_filter: Filters to segment users
            created_by: User ID creating the campaign
            description: Optional campaign description
            scheduled_at: Optional scheduled send time
            manual_recipients: Optional comma/newline-separated email addresses
            
        Returns:
            Campaign data with recipient count
        """
        try:
            # Validate template exists
            template_result = self.supabase.table('email_templates')\
                .select('id, name')\
                .eq('id', template_id)\
                .eq('is_active', True)\
                .single()\
                .execute()
            
            if not template_result.data:
                return {
                    'success': False,
                    'error': 'Template not found or inactive'
                }
            
            # Get recipients - either from manual list or filters
            if manual_recipients and manual_recipients.strip():
                recipients = self._parse_manual_recipients(manual_recipients)
            else:
                recipients = self._get_audience(audience_filter)
            
            total_recipients = len(recipients)
            
            # Create campaign
            campaign_data = {
                'name': name,
                'description': description,
                'template_id': template_id,
                'audience_filter': audience_filter,
                'template_variables': template_variables or {},
                'created_by': created_by,
                'status': 'scheduled' if scheduled_at else 'draft',
                'scheduled_at': scheduled_at,
                'total_recipients': total_recipients
            }
            
            campaign_result = self.supabase.table('email_campaigns')\
                .insert(campaign_data)\
                .execute()
            
            if not campaign_result.data:
                return {
                    'success': False,
                    'error': 'Failed to create campaign'
                }
            
            campaign = campaign_result.data[0]
            
            # Create recipient records
            if recipients:
                recipient_records = [
                    {
                        'campaign_id': campaign['id'],
                        'user_id': recipient['id'],
                        'email': recipient['email'],
                        'status': 'pending'
                    }
                    for recipient in recipients
                ]
                
                self.supabase.table('email_campaign_recipients')\
                    .insert(recipient_records)\
                    .execute()
            
            return {
                'success': True,
                'campaign': campaign,
                'recipients_count': total_recipients
            }
            
        except Exception as e:
            print(f"Error creating campaign: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_audience(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get list of users matching audience filters
        
        Supported filters:
        - subscription_status: List of statuses ['trial', 'active', 'expired']
        - min_scripts: Minimum number of scripts uploaded
        - max_scripts: Maximum number of scripts uploaded
        - days_since_signup_min: Minimum days since signup
        - days_since_signup_max: Maximum days since signup
        - days_inactive_min: Minimum days since last activity
        - trial_expiring_days: Users with trial expiring in N days
        
        Args:
            filters: Dictionary of filter criteria
        
        Returns:
            List of user profiles matching filters
        """
        try:
            # Start with base query
            query = self.supabase.table('profiles')\
                .select('id, email, full_name, subscription_status, trial_ends_at, created_at')
            
            # Apply subscription status filter
            if 'subscription_status' in filters and filters['subscription_status']:
                statuses = filters['subscription_status']
                if isinstance(statuses, list) and len(statuses) > 0:
                    query = query.in_('subscription_status', statuses)
            
            # Execute query to get base users
            result = query.execute()
            users = result.data or []
            
            # Apply script count filters (requires additional query)
            if 'min_scripts' in filters or 'max_scripts' in filters:
                users = self._filter_by_script_count(
                    users,
                    filters.get('min_scripts'),
                    filters.get('max_scripts')
                )
            
            # Apply days since signup filters
            if 'days_since_signup_min' in filters or 'days_since_signup_max' in filters:
                users = self._filter_by_signup_date(
                    users,
                    filters.get('days_since_signup_min'),
                    filters.get('days_since_signup_max')
                )
            
            # Apply inactivity filter
            if 'days_inactive_min' in filters:
                users = self._filter_by_inactivity(
                    users,
                    filters['days_inactive_min']
                )
            
            # Apply trial expiring filter
            if 'trial_expiring_days' in filters:
                users = self._filter_by_trial_expiring(
                    users,
                    filters['trial_expiring_days']
                )
            
            return users
            
        except Exception as e:
            print(f"Error getting audience: {e}")
            return []
    
    def _filter_by_script_count(
        self,
        users: List[Dict],
        min_scripts: Optional[int],
        max_scripts: Optional[int]
    ) -> List[Dict]:
        """Filter users by number of scripts uploaded"""
        filtered = []
        
        for user in users:
            script_count_result = self.supabase.table('scripts')\
                .select('script_id', count='exact')\
                .eq('user_id', user['id'])\
                .execute()
            
            script_count = script_count_result.count or 0
            
            if min_scripts is not None and script_count < min_scripts:
                continue
            if max_scripts is not None and script_count > max_scripts:
                continue
            
            filtered.append(user)
        
        return filtered
    
    def _filter_by_signup_date(
        self,
        users: List[Dict],
        min_days: Optional[int],
        max_days: Optional[int]
    ) -> List[Dict]:
        """Filter users by days since signup"""
        filtered = []
        now = datetime.now()
        
        for user in users:
            created_at = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
            days_since_signup = (now - created_at.replace(tzinfo=None)).days
            
            if min_days is not None and days_since_signup < min_days:
                continue
            if max_days is not None and days_since_signup > max_days:
                continue
            
            filtered.append(user)
        
        return filtered
    
    def _parse_manual_recipients(self, manual_recipients: str) -> List[Dict[str, Any]]:
        """
        Parse manual recipient email addresses and look up users
        
        Args:
            manual_recipients: Comma or newline-separated email addresses
            
        Returns:
            List of user dictionaries with id and email
        """
        import re
        
        # Split by commas and newlines, clean up whitespace
        emails = re.split(r'[,\n]+', manual_recipients)
        emails = [email.strip().lower() for email in emails if email.strip()]
        
        if not emails:
            return []
        
        # Look up users by email
        users_result = self.supabase.table('profiles')\
            .select('id, email')\
            .in_('email', emails)\
            .execute()
        
        return users_result.data or []
    
    def _filter_by_inactivity(
        self,
        users: List[Dict],
        min_days_inactive: int
    ) -> List[Dict]:
        """Filter users by days since last activity"""
        filtered = []
        cutoff_date = (datetime.now() - timedelta(days=min_days_inactive)).isoformat()
        
        for user in users:
            # Check last script upload
            last_script = self.supabase.table('scripts')\
                .select('upload_date')\
                .eq('user_id', user['id'])\
                .order('upload_date', desc=True)\
                .limit(1)\
                .execute()
            
            if not last_script.data:
                # No scripts = inactive user
                filtered.append(user)
            else:
                last_activity = last_script.data[0]['upload_date']
                if last_activity < cutoff_date:
                    filtered.append(user)
        
        return filtered
    
    def _filter_by_trial_expiring(
        self,
        users: List[Dict],
        days: int
    ) -> List[Dict]:
        """Filter users with trial expiring in N days"""
        filtered = []
        now = datetime.now()
        target_date = now + timedelta(days=days)
        
        for user in users:
            if user.get('subscription_status') != 'trial':
                continue
            
            if not user.get('trial_ends_at'):
                continue
            
            trial_ends = datetime.fromisoformat(user['trial_ends_at'].replace('Z', '+00:00'))
            days_until_expiry = (trial_ends.replace(tzinfo=None) - now).days
            
            # Match users expiring within ±1 day of target
            if abs(days_until_expiry - days) <= 1:
                filtered.append(user)
        
        return filtered
    
    def get_campaign_preview(self, audience_filter: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preview audience for campaign without creating it
        
        Args:
            audience_filter: Filter criteria
        
        Returns:
            Audience statistics and sample users
        """
        try:
            recipients = self._get_audience(audience_filter)
            
            return {
                'success': True,
                'total_recipients': len(recipients),
                'sample_recipients': recipients[:10],  # First 10 for preview
                'filters_applied': audience_filter
            }
            
        except Exception as e:
            print(f"Error previewing campaign: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """
        Send campaign immediately via Resend with tracking
        
        Args:
            campaign_id: UUID of campaign to send
        
        Returns:
            Send results with success/failure counts
        """
        try:
            # Get campaign details
            campaign_result = self.supabase.table('email_campaigns')\
                .select('*, email_templates(*)')\
                .eq('id', campaign_id)\
                .single()\
                .execute()
            
            if not campaign_result.data:
                return {
                    'success': False,
                    'error': 'Campaign not found'
                }
            
            campaign = campaign_result.data
            template = campaign['email_templates']
            
            # Get recipients with user names
            recipients_result = self.supabase.table('email_campaign_recipients')\
                .select('id, user_id, email')\
                .eq('campaign_id', campaign_id)\
                .eq('status', 'pending')\
                .execute()
            
            recipients_data = recipients_result.data or []
            
            # Enrich recipients with user names from auth.users
            recipients = []
            for recipient in recipients_data:
                user_name = None
                
                # Try to get user's name from auth.users
                if recipient.get('user_id'):
                    try:
                        user_result = self.supabase.table('users')\
                            .select('full_name')\
                            .eq('id', recipient['user_id'])\
                            .single()\
                            .execute()
                        
                        if user_result.data and user_result.data.get('full_name'):
                            user_name = user_result.data['full_name']
                    except:
                        pass  # User not found or no name, use fallback
                
                # Use "there" as fallback instead of email
                recipients.append({
                    'id': recipient['id'],
                    'user_id': recipient.get('user_id'),
                    'email': recipient['email'],
                    'name': user_name if user_name else 'there'
                })
            
            if not recipients:
                return {
                    'success': False,
                    'error': 'No recipients found for this campaign'
                }
            
            # Update campaign status to sending
            self.supabase.table('email_campaigns')\
                .update({
                    'status': 'sending',
                    'sent_at': datetime.now().isoformat()
                })\
                .eq('id', campaign_id)\
                .execute()
            
            # Get template variables from campaign
            template_variables = campaign.get('template_variables', {})
            
            # Send emails via Resend
            send_results = send_campaign_batch(
                campaign_id=campaign_id,
                template_id=template['id'],
                recipients=recipients,
                template_variables=template_variables,
                subject=template_variables.get('subject', template['subject']),
                html_body=template['body_html'],
                text_body=template['body_text']
            )
            
            # Update campaign status based on results
            final_status = 'sent' if send_results['failed'] == 0 else 'partial'
            
            self.supabase.table('email_campaigns')\
                .update({
                    'status': final_status,
                    'emails_sent': send_results['sent']
                })\
                .eq('id', campaign_id)\
                .execute()
            
            return {
                'success': True,
                'campaign_id': campaign_id,
                'total': send_results['total'],
                'sent': send_results['sent'],
                'failed': send_results['failed'],
                'errors': send_results['errors']
            }
            
        except Exception as e:
            print(f"Error sending campaign: {e}")
            # Update campaign status to failed
            self.supabase.table('email_campaigns')\
                .update({'status': 'failed'})\
                .eq('id', campaign_id)\
                .execute()
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_campaign_analytics(self, campaign_id: str) -> Dict[str, Any]:
        """
        Get analytics for a campaign
        
        Args:
            campaign_id: UUID of campaign
        
        Returns:
            Campaign analytics including open rates, click rates, etc.
        """
        try:
            # Get campaign data
            campaign_result = self.supabase.table('email_campaigns')\
                .select('*')\
                .eq('id', campaign_id)\
                .single()\
                .execute()
            
            if not campaign_result.data:
                return {
                    'success': False,
                    'error': 'Campaign not found'
                }
            
            campaign = campaign_result.data
            
            # Calculate rates
            total = campaign['total_recipients'] or 0
            sent = campaign['emails_sent'] or 0
            delivered = campaign['emails_delivered'] or 0
            opened = campaign['emails_opened'] or 0
            clicked = campaign['emails_clicked'] or 0
            
            analytics = {
                'campaign_id': campaign_id,
                'campaign_name': campaign['name'],
                'status': campaign['status'],
                'total_recipients': total,
                'emails_sent': sent,
                'emails_delivered': delivered,
                'emails_opened': opened,
                'emails_clicked': clicked,
                'emails_bounced': campaign['emails_bounced'] or 0,
                'emails_failed': campaign['emails_failed'] or 0,
                'delivery_rate': round((delivered / sent * 100) if sent > 0 else 0, 2),
                'open_rate': round((opened / delivered * 100) if delivered > 0 else 0, 2),
                'click_rate': round((clicked / delivered * 100) if delivered > 0 else 0, 2),
                'click_to_open_rate': round((clicked / opened * 100) if opened > 0 else 0, 2),
                'sent_at': campaign.get('sent_at'),
                'created_at': campaign['created_at']
            }
            
            return {
                'success': True,
                'analytics': analytics
            }
            
        except Exception as e:
            print(f"Error getting campaign analytics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_campaigns(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List campaigns with optional status filter
        
        Args:
            status: Filter by status (draft, scheduled, sending, sent, paused, cancelled)
            limit: Maximum records to return
            offset: Pagination offset
        
        Returns:
            List of campaigns with metadata
        """
        try:
            query = self.supabase.table('email_campaigns')\
                .select('*, email_templates(name)', count='exact')\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)
            
            if status:
                query = query.eq('status', status)
            
            result = query.execute()
            
            return {
                'success': True,
                'campaigns': result.data or [],
                'total': result.count or 0,
                'limit': limit,
                'offset': offset
            }
            
        except Exception as e:
            print(f"Error listing campaigns: {e}")
            return {
                'success': False,
                'error': str(e),
                'campaigns': [],
                'total': 0
            }
    
    def update_recipient_status(
        self,
        recipient_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update recipient status (called by email service after sending)
        
        Args:
            recipient_id: UUID of recipient record
            status: New status (sent, delivered, opened, clicked, bounced, failed)
            error_message: Error message if failed
        
        Returns:
            Updated recipient data
        """
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            # Set timestamp based on status
            if status == 'sent':
                update_data['sent_at'] = datetime.now().isoformat()
            elif status == 'delivered':
                update_data['delivered_at'] = datetime.now().isoformat()
            elif status == 'opened':
                update_data['opened_at'] = datetime.now().isoformat()
                update_data['open_count'] = self.supabase.rpc(
                    'increment',
                    {'row_id': recipient_id, 'column': 'open_count'}
                ).execute()
            elif status == 'clicked':
                update_data['clicked_at'] = datetime.now().isoformat()
                update_data['click_count'] = self.supabase.rpc(
                    'increment',
                    {'row_id': recipient_id, 'column': 'click_count'}
                ).execute()
            elif status == 'bounced':
                update_data['bounced_at'] = datetime.now().isoformat()
            
            if error_message:
                update_data['error_message'] = error_message
            
            result = self.supabase.table('email_campaign_recipients')\
                .update(update_data)\
                .eq('id', recipient_id)\
                .execute()
            
            return {
                'success': True,
                'recipient': result.data[0] if result.data else None
            }
            
        except Exception as e:
            print(f"Error updating recipient status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
