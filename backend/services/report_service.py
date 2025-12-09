"""
Report Service for ScripDown AI

Handles report generation, data aggregation, and PDF creation.
Supports multiple report types: scene breakdown, day-out-of-days, 
location reports, props lists, and one-liner/stripboard views.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

# PDF generation - using HTML templates for flexibility
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("Warning: weasyprint not installed. PDF generation disabled.")

from db.supabase_client import db


class ReportService:
    """Service for generating and managing script reports."""
    
    # Report type configurations
    REPORT_TYPES = {
        'scene_breakdown': {
            'name': 'Scene Breakdown',
            'description': 'Detailed breakdown of each scene'
        },
        'day_out_of_days': {
            'name': 'Day Out of Days',
            'description': 'Character appearance schedule'
        },
        'location': {
            'name': 'Location Report',
            'description': 'All locations with scene counts'
        },
        'props': {
            'name': 'Props List',
            'description': 'All props organized by scene'
        },
        'wardrobe': {
            'name': 'Wardrobe Report',
            'description': 'Wardrobe items by character'
        },
        'one_liner': {
            'name': 'One-Liner / Stripboard',
            'description': 'Compact scene list for scheduling'
        },
        'full_breakdown': {
            'name': 'Full Script Breakdown',
            'description': 'Complete breakdown document'
        }
    }
    
    def __init__(self):
        self.db = db
    
    # ============================================
    # Template Management
    # ============================================
    
    def get_templates(self, report_type: Optional[str] = None) -> List[Dict]:
        """Get available report templates."""
        query = self.db.client.table('report_templates').select('*')
        
        if report_type:
            query = query.eq('report_type', report_type)
        
        result = query.order('report_type').execute()
        return result.data or []
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        """Get a specific template by ID."""
        result = self.db.client.table('report_templates').select('*').eq('id', template_id).single().execute()
        return result.data
    
    # ============================================
    # Data Aggregation
    # ============================================
    
    def aggregate_scene_data(self, script_id: str) -> Dict[str, Any]:
        """
        Aggregate all scene data for a script.
        Returns structured data for report generation.
        """
        # Get script metadata
        script = self.db.get_script(script_id)
        if not script:
            raise ValueError(f"Script not found: {script_id}")
        
        # Get all scenes
        scenes = self.db.get_scenes(script_id)
        
        # Aggregate data
        characters = defaultdict(lambda: {'count': 0, 'scenes': [], 'pages': 0})
        locations = defaultdict(lambda: {'count': 0, 'scenes': [], 'int_ext': set(), 'time_of_day': set()})
        props = defaultdict(lambda: {'count': 0, 'scenes': []})
        wardrobe_items = defaultdict(lambda: {'count': 0, 'scenes': [], 'characters': set()})
        
        total_pages = 0
        analyzed_scenes = 0
        
        for scene in scenes:
            scene_num = scene.get('scene_number', '')
            page_start = scene.get('page_start', 0) or 0
            page_end = scene.get('page_end', page_start) or page_start
            page_count = max(1, page_end - page_start + 1) if page_start else 1
            total_pages += page_count
            
            if scene.get('analysis_status') == 'complete':
                analyzed_scenes += 1
            
            # Characters
            for char in (scene.get('characters') or []):
                char_name = char if isinstance(char, str) else char.get('name', str(char))
                characters[char_name]['count'] += 1
                characters[char_name]['scenes'].append(scene_num)
                characters[char_name]['pages'] += page_count
            
            # Locations
            setting = scene.get('setting', 'UNKNOWN')
            locations[setting]['count'] += 1
            locations[setting]['scenes'].append(scene_num)
            locations[setting]['int_ext'].add(scene.get('int_ext', 'INT'))
            locations[setting]['time_of_day'].add(scene.get('time_of_day', 'DAY'))
            
            # Props
            for prop in (scene.get('props') or []):
                prop_name = prop if isinstance(prop, str) else prop.get('name', str(prop))
                props[prop_name]['count'] += 1
                props[prop_name]['scenes'].append(scene_num)
            
            # Wardrobe
            for item in (scene.get('wardrobe') or []):
                item_name = item if isinstance(item, str) else item.get('name', str(item))
                wardrobe_items[item_name]['count'] += 1
                wardrobe_items[item_name]['scenes'].append(scene_num)
        
        return {
            'script': {
                'id': script_id,
                'title': script.get('title', 'Untitled'),
                'writer': script.get('writer_name', 'Unknown'),
                'draft': script.get('draft_version', ''),
                'total_pages': script.get('total_pages', total_pages),
                'production_company': script.get('production_company', ''),
                'contact_email': script.get('contact_email', ''),
                'contact_phone': script.get('contact_phone', '')
            },
            'summary': {
                'total_scenes': len(scenes),
                'analyzed_scenes': analyzed_scenes,
                'total_characters': len(characters),
                'total_locations': len(locations),
                'total_props': len(props),
                'total_pages': total_pages
            },
            'scenes': scenes,
            'characters': dict(characters),
            'locations': {k: {**v, 'int_ext': list(v['int_ext']), 'time_of_day': list(v['time_of_day'])} 
                         for k, v in locations.items()},
            'props': dict(props),
            'wardrobe': dict(wardrobe_items),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    # ============================================
    # Report Generation
    # ============================================
    
    def generate_report(
        self,
        script_id: str,
        report_type: str,
        config: Optional[Dict] = None,
        title: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Generate a report and store it in the database.
        Returns the report record with data snapshot.
        """
        if report_type not in self.REPORT_TYPES:
            raise ValueError(f"Invalid report type: {report_type}")
        
        # Aggregate data
        data = self.aggregate_scene_data(script_id)
        
        # Generate title if not provided
        if not title:
            title = f"{data['script']['title']} - {self.REPORT_TYPES[report_type]['name']}"
        
        # Create report record
        report_data = {
            'script_id': script_id,
            'report_type': report_type,
            'title': title,
            'config': config or {},
            'data_snapshot': data,
            'generated_by': user_id,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        result = self.db.client.table('reports').insert(report_data).execute()
        return result.data[0] if result.data else None
    
    def get_report(self, report_id: str) -> Optional[Dict]:
        """Get a report by ID."""
        result = self.db.client.table('reports').select('*').eq('id', report_id).single().execute()
        return result.data
    
    def get_script_reports(self, script_id: str) -> List[Dict]:
        """Get all reports for a script."""
        result = self.db.client.table('reports').select('*').eq('script_id', script_id).order('generated_at', desc=True).execute()
        return result.data or []
    
    def delete_report(self, report_id: str) -> bool:
        """Delete a report."""
        self.db.client.table('reports').delete().eq('id', report_id).execute()
        return True
    
    # ============================================
    # Sharing
    # ============================================
    
    def create_share_link(
        self,
        report_id: str,
        expires_in_days: int = 7
    ) -> Dict:
        """
        Create a shareable link for a report.
        Returns the share token and expiry date.
        """
        # Generate unique token
        share_token = secrets.token_urlsafe(16)
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Update report with share info
        result = self.db.client.table('reports').update({
            'share_token': share_token,
            'is_public': True,
            'expires_at': expires_at.isoformat()
        }).eq('id', report_id).execute()
        
        if result.data:
            return {
                'share_token': share_token,
                'expires_at': expires_at.isoformat(),
                'share_url': f"/shared/{share_token}"
            }
        return None
    
    def get_report_by_token(self, share_token: str) -> Optional[Dict]:
        """Get a report by its share token (for public access)."""
        result = self.db.client.table('reports').select('*').eq('share_token', share_token).eq('is_public', True).single().execute()
        
        if result.data:
            # Check expiry
            expires_at = result.data.get('expires_at')
            if expires_at:
                expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if expiry < datetime.now(expiry.tzinfo):
                    return None  # Expired
        
        return result.data
    
    def revoke_share_link(self, report_id: str) -> bool:
        """Revoke a share link."""
        self.db.client.table('reports').update({
            'share_token': None,
            'is_public': False,
            'expires_at': None
        }).eq('id', report_id).execute()
        return True
    
    # ============================================
    # PDF Generation
    # ============================================
    
    def generate_pdf(self, report_id: str) -> bytes:
        """
        Generate a PDF from a report.
        Returns PDF as bytes.
        """
        if not WEASYPRINT_AVAILABLE:
            raise ImportError("weasyprint is not installed")
        
        report = self.get_report(report_id)
        if not report:
            raise ValueError(f"Report not found: {report_id}")
        
        # Get HTML based on report type
        html_content = self._render_report_html(report)
        
        # Generate PDF
        html = HTML(string=html_content)
        css = CSS(string=self._get_report_css())
        
        return html.write_pdf(stylesheets=[css])
    
    def _render_report_html(self, report: Dict) -> str:
        """Render report data as HTML."""
        report_type = report.get('report_type')
        data = report.get('data_snapshot', {})
        script = data.get('script', {})
        
        # Common header
        header = f"""
        <div class="report-header">
            <h1>{report.get('title', 'Script Report')}</h1>
            <div class="script-info">
                <p><strong>Script:</strong> {script.get('title', 'Untitled')}</p>
                <p><strong>Writer:</strong> {script.get('writer', 'Unknown')}</p>
                <p><strong>Generated:</strong> {report.get('generated_at', '')[:10]}</p>
            </div>
        </div>
        """
        
        # Render based on type
        if report_type == 'scene_breakdown':
            body = self._render_scene_breakdown(data)
        elif report_type == 'day_out_of_days':
            body = self._render_day_out_of_days(data)
        elif report_type == 'location':
            body = self._render_location_report(data)
        elif report_type == 'props':
            body = self._render_props_report(data)
        elif report_type == 'one_liner':
            body = self._render_one_liner(data)
        else:
            body = self._render_full_breakdown(data)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{report.get('title', 'Report')}</title>
        </head>
        <body>
            {header}
            {body}
        </body>
        </html>
        """
    
    def _render_scene_breakdown(self, data: Dict) -> str:
        """Render scene breakdown HTML."""
        scenes = data.get('scenes', [])
        rows = []
        
        for scene in scenes:
            chars = ', '.join(scene.get('characters', [])[:5])
            if len(scene.get('characters', [])) > 5:
                chars += '...'
            
            props = ', '.join(scene.get('props', [])[:3])
            if len(scene.get('props', [])) > 3:
                props += '...'
            
            rows.append(f"""
            <tr>
                <td>{scene.get('scene_number', '')}</td>
                <td>{scene.get('int_ext', '')}</td>
                <td>{scene.get('setting', '')}</td>
                <td>{scene.get('time_of_day', '')}</td>
                <td>{chars}</td>
                <td>{props}</td>
                <td>{scene.get('page_start', '')}</td>
            </tr>
            """)
        
        return f"""
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Scene</th>
                    <th>I/E</th>
                    <th>Setting</th>
                    <th>D/N</th>
                    <th>Characters</th>
                    <th>Props</th>
                    <th>Page</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_day_out_of_days(self, data: Dict) -> str:
        """Render day-out-of-days HTML."""
        characters = data.get('characters', {})
        rows = []
        
        # Sort by scene count descending
        sorted_chars = sorted(characters.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for name, info in sorted_chars:
            scenes_str = ', '.join(info['scenes'][:10])
            if len(info['scenes']) > 10:
                scenes_str += '...'
            
            rows.append(f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{info['count']}</td>
                <td>{info.get('pages', info['count'])}</td>
                <td class="scenes-cell">{scenes_str}</td>
            </tr>
            """)
        
        return f"""
        <h2>Day Out of Days - Character Schedule</h2>
        <table class="dood-table">
            <thead>
                <tr>
                    <th>Character</th>
                    <th>Scenes</th>
                    <th>Pages</th>
                    <th>Scene Numbers</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_location_report(self, data: Dict) -> str:
        """Render location report HTML."""
        locations = data.get('locations', {})
        rows = []
        
        sorted_locs = sorted(locations.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for name, info in sorted_locs:
            int_ext = '/'.join(info.get('int_ext', []))
            time = '/'.join(info.get('time_of_day', []))
            scenes_str = ', '.join(info['scenes'][:8])
            if len(info['scenes']) > 8:
                scenes_str += '...'
            
            rows.append(f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{int_ext}</td>
                <td>{time}</td>
                <td>{info['count']}</td>
                <td class="scenes-cell">{scenes_str}</td>
            </tr>
            """)
        
        return f"""
        <h2>Location Report</h2>
        <table class="location-table">
            <thead>
                <tr>
                    <th>Location</th>
                    <th>INT/EXT</th>
                    <th>D/N</th>
                    <th>Scenes</th>
                    <th>Scene Numbers</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_props_report(self, data: Dict) -> str:
        """Render props report HTML."""
        props = data.get('props', {})
        rows = []
        
        sorted_props = sorted(props.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for name, info in sorted_props:
            scenes_str = ', '.join(info['scenes'])
            
            rows.append(f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{info['count']}</td>
                <td class="scenes-cell">{scenes_str}</td>
            </tr>
            """)
        
        return f"""
        <h2>Props List</h2>
        <table class="props-table">
            <thead>
                <tr>
                    <th>Prop</th>
                    <th>Appearances</th>
                    <th>Scenes</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_one_liner(self, data: Dict) -> str:
        """Render one-liner/stripboard HTML."""
        scenes = data.get('scenes', [])
        rows = []
        
        for scene in scenes:
            chars = ', '.join(scene.get('characters', [])[:3])
            if len(scene.get('characters', [])) > 3:
                chars += f" +{len(scene.get('characters', [])) - 3}"
            
            page_info = scene.get('page_start', '')
            if scene.get('page_end') and scene.get('page_end') != scene.get('page_start'):
                page_info = f"{scene.get('page_start')}-{scene.get('page_end')}"
            
            rows.append(f"""
            <tr class="one-liner-row">
                <td class="scene-num">{scene.get('scene_number', '')}</td>
                <td class="int-ext">{scene.get('int_ext', '')}</td>
                <td class="setting">{scene.get('setting', '')}</td>
                <td class="time">{scene.get('time_of_day', '')}</td>
                <td class="chars">{chars}</td>
                <td class="pages">{page_info}</td>
            </tr>
            """)
        
        return f"""
        <h2>One-Liner / Stripboard</h2>
        <table class="one-liner-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>I/E</th>
                    <th>Setting</th>
                    <th>D/N</th>
                    <th>Cast</th>
                    <th>Pg</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_full_breakdown(self, data: Dict) -> str:
        """Render full breakdown HTML."""
        summary = data.get('summary', {})
        
        summary_html = f"""
        <div class="summary-section">
            <h2>Script Summary</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <span class="label">Total Scenes</span>
                    <span class="value">{summary.get('total_scenes', 0)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Total Pages</span>
                    <span class="value">{summary.get('total_pages', 0)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Characters</span>
                    <span class="value">{summary.get('total_characters', 0)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Locations</span>
                    <span class="value">{summary.get('total_locations', 0)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Props</span>
                    <span class="value">{summary.get('total_props', 0)}</span>
                </div>
            </div>
        </div>
        """
        
        return f"""
        {summary_html}
        <div class="page-break"></div>
        {self._render_scene_breakdown(data)}
        <div class="page-break"></div>
        {self._render_day_out_of_days(data)}
        <div class="page-break"></div>
        {self._render_location_report(data)}
        """
    
    def _get_report_css(self) -> str:
        """Get CSS for PDF reports."""
        return """
        @page {
            size: A4;
            margin: 1.5cm;
        }
        
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #1a1a1a;
        }
        
        .report-header {
            border-bottom: 2px solid #333;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .report-header h1 {
            font-size: 18pt;
            margin: 0 0 0.5rem 0;
            color: #111;
        }
        
        .script-info {
            display: flex;
            gap: 2rem;
            font-size: 9pt;
            color: #666;
        }
        
        .script-info p {
            margin: 0;
        }
        
        h2 {
            font-size: 14pt;
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 0.5rem;
            margin-top: 1.5rem;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 9pt;
        }
        
        th {
            background: #f5f5f5;
            border: 1px solid #ddd;
            padding: 8px 6px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 8pt;
            letter-spacing: 0.5px;
        }
        
        td {
            border: 1px solid #ddd;
            padding: 6px;
            vertical-align: top;
        }
        
        tr:nth-child(even) {
            background: #fafafa;
        }
        
        .scenes-cell {
            font-size: 8pt;
            color: #666;
            max-width: 200px;
        }
        
        /* One-liner specific */
        .one-liner-table {
            font-size: 8pt;
        }
        
        .one-liner-table .scene-num {
            font-weight: 600;
            width: 40px;
        }
        
        .one-liner-table .int-ext {
            width: 40px;
        }
        
        .one-liner-table .time {
            width: 50px;
        }
        
        .one-liner-table .pages {
            width: 40px;
            text-align: center;
        }
        
        /* Summary section */
        .summary-section {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1.5rem;
        }
        
        .summary-grid {
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
        }
        
        .summary-item {
            text-align: center;
        }
        
        .summary-item .label {
            display: block;
            font-size: 8pt;
            color: #666;
            text-transform: uppercase;
        }
        
        .summary-item .value {
            display: block;
            font-size: 18pt;
            font-weight: 700;
            color: #333;
        }
        
        .page-break {
            page-break-after: always;
        }
        
        /* Print optimizations */
        @media print {
            .page-break {
                page-break-after: always;
            }
        }
        """


# Singleton instance
report_service = ReportService()
