"""
Report Routes for ScripDown AI

API endpoints for report generation, management, and sharing.
"""

from flask import Blueprint, request, jsonify, Response
from services.report_service import report_service
from middleware.auth import optional_auth, get_user_id

report_bp = Blueprint('reports', __name__)


# ============================================
# Template Endpoints
# ============================================

@report_bp.route('/templates', methods=['GET'])
def get_templates():
    """Get all available report templates."""
    try:
        report_type = request.args.get('type')
        templates = report_service.get_templates(report_type)
        return jsonify({
            'success': True,
            'templates': templates
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@report_bp.route('/templates/<template_id>', methods=['GET'])
def get_template(template_id):
    """Get a specific template."""
    try:
        template = report_service.get_template(template_id)
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        return jsonify({
            'success': True,
            'template': template
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Filter Options Endpoint
# ============================================

@report_bp.route('/scripts/<script_id>/filter-options', methods=['GET'])
def get_filter_options(script_id):
    """
    Get unique values for each filter dimension.
    Used by frontend to populate filter dropdowns.
    """
    try:
        options = report_service.get_filter_options(script_id)
        return jsonify({
            'success': True,
            'options': options
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Filter Preset Endpoints
# ============================================

@report_bp.route('/scripts/<script_id>/filter-presets', methods=['GET'])
@optional_auth
def get_filter_presets(script_id):
    """Get filter presets (default + user's own) for a script."""
    try:
        user_id = get_user_id()
        presets = report_service.get_filter_presets(script_id, user_id=user_id)
        return jsonify({
            'success': True,
            'presets': presets
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@report_bp.route('/scripts/<script_id>/filter-presets', methods=['POST'])
@optional_auth
def save_filter_preset(script_id):
    """
    Save a new filter preset.
    
    Request body:
    {
        "name": "My Preset",
        "filters": { ... },
        "categories": ["props", "wardrobe"],
        "group_by": "location"
    }
    """
    try:
        data = request.get_json() or {}
        name = data.get('name')
        user_id = get_user_id()
        filters = data.get('filters', {})
        categories = data.get('categories', [])
        group_by = data.get('group_by', 'scene_number')
        
        if not name:
            return jsonify({'success': False, 'error': 'Preset name is required'}), 400
        if not user_id:
            return jsonify({'success': False, 'error': 'Authentication required to save presets'}), 401
        
        preset = report_service.save_filter_preset(
            script_id=script_id,
            user_id=user_id,
            name=name,
            filters=filters,
            categories=categories,
            group_by=group_by
        )
        
        if not preset:
            return jsonify({'success': False, 'error': 'Failed to save preset'}), 500
        
        return jsonify({
            'success': True,
            'preset': preset
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@report_bp.route('/filter-presets/<preset_id>', methods=['DELETE'])
@optional_auth
def delete_filter_preset(preset_id):
    """Delete a user's filter preset."""
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Authentication required to delete presets'}), 401
        
        report_service.delete_filter_preset(preset_id, user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Report Generation Endpoints
# ============================================

@report_bp.route('/scripts/<script_id>/reports', methods=['GET'])
def get_script_reports(script_id):
    """Get all reports for a script."""
    try:
        reports = report_service.get_script_reports(script_id)
        return jsonify({
            'success': True,
            'reports': reports
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@report_bp.route('/scripts/<script_id>/reports/generate', methods=['POST'])
def generate_report(script_id):
    """
    Generate a new report for a script.
    
    Request body:
    {
        "report_type": "scene_breakdown" | "day_out_of_days" | "location" | "props" | "one_liner" | "full_breakdown",
        "title": "Optional custom title",
        "config": { optional configuration overrides }
    }
    """
    try:
        data = request.get_json() or {}
        report_type = data.get('report_type', 'scene_breakdown')
        title = data.get('title')
        config = data.get('config') or {}
        filters = data.get('filters')
        group_by = data.get('group_by')
        categories = data.get('categories')
        
        # Merge group_by and categories into config for rendering
        if group_by:
            config['group_by'] = group_by
        if categories:
            config['categories'] = categories
        
        # Validate report type
        if report_type not in report_service.REPORT_TYPES:
            return jsonify({
                'success': False,
                'error': f'Invalid report type. Valid types: {list(report_service.REPORT_TYPES.keys())}'
            }), 400
        
        report = report_service.generate_report(
            script_id=script_id,
            report_type=report_type,
            config=config,
            title=title,
            filters=filters
        )
        
        if not report:
            return jsonify({'success': False, 'error': 'Failed to generate report'}), 500
        
        return jsonify({
            'success': True,
            'report': report
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@report_bp.route('/scripts/<script_id>/reports/preview', methods=['POST'])
def preview_report(script_id):
    """
    Preview report data without saving.
    Returns aggregated data for the specified report type.
    """
    try:
        data = request.get_json() or {}
        report_type = data.get('report_type', 'scene_breakdown')
        filters = data.get('filters')
        
        # Get aggregated data with optional filters
        aggregated_data = report_service.aggregate_scene_data(script_id, filters=filters)
        
        return jsonify({
            'success': True,
            'report_type': report_type,
            'data': aggregated_data
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Report Management Endpoints
# ============================================

@report_bp.route('/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    """Get a specific report."""
    try:
        report = report_service.get_report(report_id)
        if not report:
            return jsonify({'success': False, 'error': 'Report not found'}), 404
        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@report_bp.route('/reports/<report_id>', methods=['DELETE'])
def delete_report(report_id):
    """Delete a report."""
    try:
        report_service.delete_report(report_id)
        return jsonify({
            'success': True,
            'message': 'Report deleted'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# PDF Download Endpoints
# ============================================

@report_bp.route('/reports/<report_id>/pdf', methods=['GET'])
def download_pdf(report_id):
    """Download report as PDF."""
    try:
        report = report_service.get_report(report_id)
        if not report:
            return jsonify({'success': False, 'error': 'Report not found'}), 404
        
        pdf_bytes = report_service.generate_pdf(report_id)
        
        # Create filename
        title = report.get('title', 'report').replace(' ', '_')
        filename = f"{title}.pdf"
        
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/pdf'
            }
        )
    except ImportError as e:
        return jsonify({
            'success': False,
            'error': 'PDF generation not available. Install weasyprint.'
        }), 501
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@report_bp.route('/reports/<report_id>/print', methods=['GET'])
def get_printable_html(report_id):
    """Get printable HTML version of report."""
    try:
        report = report_service.get_report(report_id)
        if not report:
            return jsonify({'success': False, 'error': 'Report not found'}), 404
        
        # Generate HTML
        html_content = report_service._render_report_html(report)
        css_content = report_service._get_report_css()
        
        # Combine into full printable page
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{report.get('title', 'Report')}</title>
            <style>{css_content}</style>
        </head>
        <body>
            {html_content.split('<body>')[1].split('</body>')[0] if '<body>' in html_content else html_content}
            <script>
                // Auto-print on load (optional)
                // window.onload = function() {{ window.print(); }}
            </script>
        </body>
        </html>
        """
        
        return Response(full_html, mimetype='text/html')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Sharing Endpoints
# ============================================

@report_bp.route('/reports/<report_id>/share', methods=['POST'])
def create_share_link(report_id):
    """
    Create a shareable link for a report.
    
    Request body:
    {
        "expires_in_days": 7  // optional, default 7
    }
    """
    try:
        data = request.get_json() or {}
        expires_in_days = data.get('expires_in_days', 7)
        
        share_info = report_service.create_share_link(report_id, expires_in_days)
        
        if not share_info:
            return jsonify({'success': False, 'error': 'Failed to create share link'}), 500
        
        return jsonify({
            'success': True,
            **share_info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@report_bp.route('/reports/<report_id>/share', methods=['DELETE'])
def revoke_share_link(report_id):
    """Revoke a share link."""
    try:
        report_service.revoke_share_link(report_id)
        return jsonify({
            'success': True,
            'message': 'Share link revoked'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@report_bp.route('/shared/<share_token>', methods=['GET'])
def get_shared_report(share_token):
    """
    Access a shared report via token.
    This is a public endpoint - no auth required.
    """
    try:
        report = report_service.get_report_by_token(share_token)
        
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report not found or link has expired'
            }), 404
        
        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@report_bp.route('/shared/<share_token>/pdf', methods=['GET'])
def download_shared_pdf(share_token):
    """Download shared report as PDF."""
    try:
        report = report_service.get_report_by_token(share_token)
        
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report not found or link has expired'
            }), 404
        
        pdf_bytes = report_service.generate_pdf(report['id'])
        
        title = report.get('title', 'report').replace(' ', '_')
        filename = f"{title}.pdf"
        
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/pdf'
            }
        )
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'PDF generation not available'
        }), 501
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@report_bp.route('/shared/<share_token>/print', methods=['GET'])
def get_shared_printable(share_token):
    """Get printable HTML for shared report."""
    try:
        report = report_service.get_report_by_token(share_token)
        
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report not found or link has expired'
            }), 404
        
        html_content = report_service._render_report_html(report)
        css_content = report_service._get_report_css()
        
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{report.get('title', 'Report')}</title>
            <style>{css_content}</style>
        </head>
        <body>
            {html_content.split('<body>')[1].split('</body>')[0] if '<body>' in html_content else html_content}
        </body>
        </html>
        """
        
        return Response(full_html, mimetype='text/html')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Report Types Info Endpoint
# ============================================

@report_bp.route('/report-types', methods=['GET'])
def get_report_types():
    """Get available report types and their descriptions."""
    return jsonify({
        'success': True,
        'report_types': report_service.REPORT_TYPES
    })


@report_bp.route('/report-presets', methods=['GET'])
def get_report_presets():
    """
    Get available report configuration presets.
    Returns list of presets with name, title, and description.
    """
    try:
        from services.report_service import ReportConfig
        presets = ReportConfig.get_available_presets()
        return jsonify({
            'success': True,
            'presets': presets
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
