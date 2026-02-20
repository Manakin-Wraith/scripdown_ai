"""
Campaign Webhook Routes
Handles webhooks from Resend for email tracking events.

Resend sends a svix-style signature in the `Resend-Signature` header:
  v1,<timestamp>.<hmac-sha256-hex>
We verify against RESEND_WEBHOOK_SECRET env var when set.
"""

import os
import hmac
import hashlib
from flask import Blueprint, request, jsonify
from db.supabase_client import get_supabase_admin
from datetime import datetime

webhook_bp = Blueprint('campaign_webhooks', __name__, url_prefix='/api/campaigns/webhooks')


def verify_resend_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """
    Verify Resend webhook signature.
    Header format: "v1,<timestamp>.<hex-digest>"
    We verify: HMAC-SHA256(secret, timestamp + "." + payload)
    """
    if not secret:
        return True
    try:
        # Header: "v1,<ts>.<sig>"
        parts = signature_header.split(',')
        if len(parts) < 2:
            return False
        ts_sig = parts[1]  # "<ts>.<sig>"
        ts, sig = ts_sig.rsplit('.', 1)
        signed_content = f"{ts}.{payload.decode('utf-8')}"
        expected = hmac.new(
            secret.encode('utf-8'),
            signed_content.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


def _increment_campaign_counter(supabase, campaign_id: str, field: str, amount: int = 1):
    """
    Safely increment a numeric counter on email_campaigns.
    Reads current value then writes current+amount.
    """
    try:
        row = supabase.table('email_campaigns')\
            .select(field)\
            .eq('id', campaign_id)\
            .single()\
            .execute()
        if row.data:
            current = row.data.get(field) or 0
            supabase.table('email_campaigns')\
                .update({field: current + amount, 'updated_at': datetime.utcnow().isoformat()})\
                .eq('id', campaign_id)\
                .execute()
    except Exception as e:
        print(f"Warning: could not increment {field} on campaign {campaign_id}: {e}")


def _sync_email_tracking(supabase, email_id: str, event_type: str, now: str, event_data: dict):
    """
    Mirror webhook events into the email_tracking table so transactional
    email stats stay accurate alongside campaign stats.
    """
    try:
        status_map = {
            'email.sent':      'sent',
            'email.delivered': 'delivered',
            'email.bounced':   'bounced',
            'email.complained':'bounced',
            'email.opened':    'delivered',
            'email.clicked':   'delivered',
        }
        delivery_status = status_map.get(event_type)
        if not delivery_status or not email_id:
            return

        update_data = {
            'delivery_status': delivery_status,
            'updated_at': now,
        }
        if event_type == 'email.opened':
            update_data['opened_at'] = now
        if event_type == 'email.clicked':
            update_data['clicked_at'] = now

        supabase.table('email_tracking')\
            .update(update_data)\
            .eq('resend_email_id', email_id)\
            .execute()
    except Exception as e:
        print(f"Warning: could not sync email_tracking for {email_id}: {e}")


@webhook_bp.route('/resend', methods=['POST'])
def resend_webhook():
    """
    Handle Resend webhook events for email tracking.

    Tracked events and their datapoints:
    - email.sent       → recipient.status=sent, resend_message_id, campaign.emails_sent++
    - email.delivered  → recipient.status=delivered, delivered_at, campaign.emails_delivered++
    - email.bounced    → recipient.status=bounced, bounced_at, error_message, campaign.emails_bounced++
    - email.opened     → recipient.status=opened, opened_at, open_count++, campaign.emails_opened++
    - email.clicked    → recipient.status=clicked, clicked_at, click_count++, campaign.emails_clicked++
    - email.complained → recipient.status=bounced, error_message=spam, campaign.emails_bounced++
    - email.delivery_delayed → logged only, no status change

    All events also mirror into email_tracking table via resend_email_id.
    Signature verified against RESEND_WEBHOOK_SECRET env var when set.
    """
    try:
        payload = request.get_data()
        signature = request.headers.get('Resend-Signature', '')

        webhook_secret = os.getenv('RESEND_WEBHOOK_SECRET', '')
        if webhook_secret and not verify_resend_signature(payload, signature, webhook_secret):
            print(f"Resend webhook: invalid signature")
            return jsonify({'error': 'Invalid signature'}), 401

        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'Empty payload'}), 400

        event_type = data.get('type', '')
        event_data = data.get('data', {})

        print(f"[Resend webhook] {event_type}")

        # ── Extract tracking tags ──────────────────────────────────────────────
        # Resend tags come as list [{name, value}] or dict depending on SDK version
        raw_tags = event_data.get('tags', {})
        if isinstance(raw_tags, list):
            tags = {t['name']: t['value'] for t in raw_tags if 'name' in t}
        else:
            tags = raw_tags

        email_id    = event_data.get('email_id') or event_data.get('id')
        campaign_id = tags.get('campaign_id')
        recipient_id = tags.get('recipient_id')

        supabase = get_supabase_admin()
        now = datetime.utcnow().isoformat()

        # ── Mirror into email_tracking (transactional emails) ─────────────────
        _sync_email_tracking(supabase, email_id, event_type, now, event_data)

        # ── Campaign-specific tracking ─────────────────────────────────────────
        if not campaign_id or not recipient_id:
            print(f"[Resend webhook] No campaign/recipient tags — transactional only")
            return jsonify({'status': 'ok', 'tracked': 'transactional_only'}), 200

        recipient_update = {'updated_at': now}
        campaign_counter = None  # field name to increment on email_campaigns

        if event_type == 'email.sent':
            recipient_update['status'] = 'sent'
            recipient_update['sent_at'] = now
            if email_id:
                recipient_update['resend_message_id'] = email_id
            campaign_counter = 'emails_sent'

        elif event_type == 'email.delivered':
            recipient_update['status'] = 'delivered'
            recipient_update['delivered_at'] = now
            campaign_counter = 'emails_delivered'

        elif event_type == 'email.bounced':
            recipient_update['status'] = 'bounced'
            recipient_update['bounced_at'] = now
            bounce_type = event_data.get('bounce', {}).get('type', 'unknown')
            recipient_update['error_message'] = f"Bounced ({bounce_type})"
            campaign_counter = 'emails_bounced'

        elif event_type == 'email.opened':
            recipient_update['status'] = 'opened'
            recipient_update['opened_at'] = event_data.get('opened_at') or now
            # Increment per-recipient open count
            r = supabase.table('email_campaign_recipients')\
                .select('open_count').eq('id', recipient_id).single().execute()
            recipient_update['open_count'] = (r.data.get('open_count') or 0) + 1 if r.data else 1
            campaign_counter = 'emails_opened'

        elif event_type == 'email.clicked':
            recipient_update['status'] = 'clicked'
            recipient_update['clicked_at'] = event_data.get('clicked_at') or now
            # Increment per-recipient click count
            r = supabase.table('email_campaign_recipients')\
                .select('click_count').eq('id', recipient_id).single().execute()
            recipient_update['click_count'] = (r.data.get('click_count') or 0) + 1 if r.data else 1
            campaign_counter = 'emails_clicked'

        elif event_type == 'email.complained':
            recipient_update['status'] = 'bounced'
            recipient_update['error_message'] = 'Marked as spam'
            campaign_counter = 'emails_bounced'

        elif event_type == 'email.delivery_delayed':
            print(f"[Resend webhook] Delivery delayed for recipient {recipient_id}")
            # No status change — just log

        # ── Persist recipient update ───────────────────────────────────────────
        supabase.table('email_campaign_recipients')\
            .update(recipient_update)\
            .eq('id', recipient_id)\
            .execute()

        # ── Increment campaign aggregate counter ───────────────────────────────
        if campaign_counter:
            _increment_campaign_counter(supabase, campaign_id, campaign_counter)

        print(f"[Resend webhook] {event_type} → recipient={recipient_id} campaign={campaign_id}")

        return jsonify({
            'status': 'success',
            'event': event_type,
            'campaign_id': campaign_id,
            'recipient_id': recipient_id,
            'counter_updated': campaign_counter,
        }), 200

    except Exception as e:
        print(f"[Resend webhook] Error: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_bp.route('/resend/test', methods=['GET'])
def test_webhook():
    """Test endpoint to verify webhook is accessible"""
    return jsonify({
        'status': 'ok',
        'message': 'Resend webhook endpoint is active',
        'url': request.url_root + 'api/campaigns/webhooks/resend'
    }), 200
