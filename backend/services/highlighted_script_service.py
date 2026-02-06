"""
Highlighted Script PDF Service

Generates a PDF version of the script with color-coded highlights
for each extraction class (characters, props, wardrobe, etc.).

Uses extraction_metadata character positions to overlay highlights
on the script text, then renders to PDF via WeasyPrint.
"""

import html
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from db.supabase_client import get_supabase_client, get_supabase_admin


# ============================================
# Extraction Class → Highlight Color Mapping
# Matches frontend extractionClassConfig.js
# ============================================

HIGHLIGHT_COLORS = {
    'scene_header':    {'bg': 'rgba(99, 102, 241, 0.20)',  'border': '#6366f1', 'label': 'Scene Header'},
    'character':       {'bg': 'rgba(59, 130, 246, 0.22)',   'border': '#3b82f6', 'label': 'Character'},
    'dialogue':        {'bg': 'rgba(20, 184, 166, 0.15)',   'border': '#14b8a6', 'label': 'Dialogue'},
    'action':          {'bg': 'rgba(220, 38, 38, 0.12)',    'border': '#dc2626', 'label': 'Action'},
    'prop':            {'bg': 'rgba(6, 182, 212, 0.22)',    'border': '#06b6d4', 'label': 'Prop'},
    'wardrobe':        {'bg': 'rgba(139, 92, 246, 0.20)',   'border': '#8b5cf6', 'label': 'Wardrobe'},
    'location_detail': {'bg': 'rgba(16, 185, 129, 0.20)',   'border': '#10b981', 'label': 'Location'},
    'emotion':         {'bg': 'rgba(219, 39, 119, 0.15)',   'border': '#db2777', 'label': 'Emotion'},
    'relationship':    {'bg': 'rgba(236, 72, 153, 0.15)',   'border': '#ec4899', 'label': 'Relationship'},
    'special_fx':      {'bg': 'rgba(234, 179, 8, 0.22)',    'border': '#eab308', 'label': 'Special FX'},
    'vehicle':         {'bg': 'rgba(239, 68, 68, 0.18)',    'border': '#ef4444', 'label': 'Vehicle'},
    'sound':           {'bg': 'rgba(168, 85, 247, 0.18)',   'border': '#a855f7', 'label': 'Sound'},
    'transition':      {'bg': 'rgba(245, 158, 11, 0.15)',   'border': '#f59e0b', 'label': 'Transition'},
    'makeup_hair':     {'bg': 'rgba(249, 115, 22, 0.18)',   'border': '#f97316', 'label': 'Makeup & Hair'},
}

DEFAULT_HIGHLIGHT = {'bg': 'rgba(107, 114, 128, 0.15)', 'border': '#6b7280', 'label': 'Other'}


# ============================================
# Screenplay CSS (Industry Standard)
# ============================================

SCREENPLAY_CSS = """
@page {
    size: letter;
    margin: 1in 1.25in 0.75in 1.25in;

    @bottom-center {
        content: counter(page);
        font-family: 'Courier New', Courier, monospace;
        font-size: 10pt;
        color: #666;
    }
}

@page :first {
    @bottom-center { content: none; }
}

* { box-sizing: border-box; }

body {
    font-family: 'Courier New', Courier, monospace;
    font-size: 12pt;
    line-height: 1.0;
    color: #1a1a1a;
    margin: 0;
    padding: 0;
}

/* Cover / title page */
.cover-page {
    text-align: center;
    padding-top: 3in;
    page-break-after: always;
}
.cover-page h1 {
    font-size: 18pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5in;
}
.cover-page .subtitle {
    font-size: 12pt;
    color: #444;
    margin-bottom: 0.3in;
}
.cover-page .meta-line {
    font-size: 10pt;
    color: #666;
    margin: 4pt 0;
}

/* Legend box */
.legend {
    border: 1pt solid #ccc;
    border-radius: 4pt;
    padding: 10pt 14pt;
    margin-bottom: 16pt;
    page-break-inside: avoid;
    background: #fafafa;
    max-width: 6in;
    margin-left: auto;
    margin-right: auto;
}
.legend h3 {
    font-size: 10pt;
    margin: 0 0 8pt 0;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #555;
}
.legend-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 6pt;
}
.legend-item {
    display: inline-flex;
    align-items: center;
    gap: 4pt;
    font-size: 9pt;
    padding: 2pt 6pt;
    border-radius: 3pt;
    border-left: 3pt solid transparent;
}

/* ============================================
   Screenplay Structure Elements
   Industry-standard formatting (Courier 12pt)
   ============================================ */

.script-body {
    line-height: 1.0;
    max-width: 6in;
    margin-left: auto;
    margin-right: auto;
}

/* Scene heading: left-aligned, bold, uppercase, 2-line gap above */
.sp-scene-heading {
    font-weight: bold;
    text-transform: uppercase;
    margin-top: 24pt;
    margin-bottom: 12pt;
}

/* Character cue: centered, uppercase */
.sp-character-cue {
    text-transform: uppercase;
    margin-left: 2.2in;
    margin-top: 12pt;
    margin-bottom: 0;
}

/* Dialogue: indented block, narrower than action */
.sp-dialogue {
    margin-left: 1in;
    margin-right: 1.5in;
    margin-top: 0;
    margin-bottom: 0;
}

/* Parenthetical: slightly more indented, italic */
.sp-parenthetical {
    margin-left: 1.6in;
    margin-right: 2in;
    margin-top: 0;
    margin-bottom: 0;
}

/* Action: full-width, normal weight */
.sp-action {
    margin-top: 12pt;
    margin-bottom: 0;
}

/* Transition: right-aligned, uppercase */
.sp-transition {
    text-align: right;
    text-transform: uppercase;
    margin-top: 12pt;
    margin-bottom: 12pt;
}

/* Blank line (spacing) */
.sp-blank {
    height: 12pt;
}

/* Extraction highlights */
.hl {
    border-radius: 2pt;
    padding: 0 1pt;
    border-bottom: 1.5pt solid transparent;
}

/* Per-class highlight styles (generated dynamically) */

/* Page break markers */
.page-break {
    page-break-before: always;
}

/* Stats footer */
.stats-summary {
    margin-top: 24pt;
    padding-top: 12pt;
    border-top: 1pt solid #ccc;
    font-size: 9pt;
    color: #666;
}
.stats-summary table {
    width: 100%;
    border-collapse: collapse;
}
.stats-summary td {
    padding: 3pt 8pt;
    border-bottom: 0.5pt solid #eee;
}
.stats-summary td:first-child {
    font-weight: bold;
    width: 40%;
}
"""


def _generate_class_css(active_classes: set) -> str:
    """Generate CSS rules for each active extraction class."""
    rules = []
    for cls in sorted(active_classes):
        colors = HIGHLIGHT_COLORS.get(cls, DEFAULT_HIGHLIGHT)
        rules.append(
            f".hl-{cls} {{ background: {colors['bg']}; "
            f"border-bottom-color: {colors['border']}; }}"
        )
    return "\n".join(rules)


# ============================================
# HTML Builder
# ============================================

def _build_highlighted_html(
    script_text: str,
    extractions: List[Dict],
    script_meta: Dict,
    filter_classes: Optional[List[str]] = None,
    page_boundaries: Optional[List[int]] = None
) -> str:
    """
    Build a screenplay-formatted HTML document with extraction highlights.

    Uses line-by-line classification to produce proper screenplay structure:
    scene headings, character cues, dialogue, parentheticals, action, transitions.

    Args:
        script_text: Full script text
        extractions: List of extraction dicts with text_start, text_end,
                     extraction_class, extraction_text, attributes
        script_meta: Script metadata (title, writer, etc.)
        filter_classes: Optional list of classes to include (None = all)
        page_boundaries: Optional list of character positions for page breaks

    Returns:
        Complete HTML string ready for WeasyPrint
    """
    # Filter extractions if requested
    if filter_classes:
        extractions = [e for e in extractions if e.get('extraction_class') in filter_classes]

    # Sort by text_start, then by span length descending (longer spans first)
    extractions = sorted(
        extractions,
        key=lambda e: (e.get('text_start', 0), -(e.get('text_end', 0) - e.get('text_start', 0)))
    )

    # Remove overlapping extractions (first-wins strategy)
    clean_extractions = _remove_overlaps(extractions)

    # Collect active classes for CSS + legend
    active_classes = set(e.get('extraction_class', '') for e in clean_extractions)

    # Build the highlighted script body (line-by-line screenplay formatting)
    body_html = _build_screenplay_body(script_text, clean_extractions, page_boundaries)

    # Build legend
    legend_html = _build_legend(active_classes)

    # Build stats
    stats_html = _build_stats(clean_extractions, active_classes, len(script_text))

    # Build cover page
    title = script_meta.get('title', 'Untitled Script')
    writer = script_meta.get('writer_name', script_meta.get('writer', ''))
    cover_html = _build_cover_page(title, writer, script_meta, filter_classes)

    # Assemble class-specific CSS
    class_css = _generate_class_css(active_classes)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(title)} — Highlighted Breakdown</title>
    <style>
    {SCREENPLAY_CSS}
    {class_css}
    </style>
</head>
<body>
    {cover_html}
    {legend_html}
    <div class="script-body">{body_html}</div>
    {stats_html}
</body>
</html>"""


def _remove_overlaps(extractions: List[Dict]) -> List[Dict]:
    """Remove overlapping extractions using first-wins strategy."""
    result = []
    last_end = -1

    for ext in extractions:
        start = ext.get('text_start', 0)
        end = ext.get('text_end', 0)

        if start is None or end is None:
            continue
        if start < 0 or end <= start:
            continue
        if start < last_end:
            continue

        result.append(ext)
        last_end = end

    return result


# ============================================
# Line Classification
# ============================================

# Regex for scene headings
_SCENE_HEADING_RE = re.compile(
    r'^\s*(INT\.|EXT\.|INT/EXT\.|INT\s*/\s*EXT\.|I/E\.|INTERIOR|EXTERIOR)',
    re.IGNORECASE
)

# Regex for character cues: ALL-CAPS name, optionally with (CONT'D), (V.O.), (O.S.)
_CHARACTER_CUE_RE = re.compile(
    r"^[A-Z][A-Z\s'\.\-]+(\s*\((?:CONT'?D?|V\.?O\.?|O\.?S\.?|O\.?C\.?|CONT'D|FILTERED)\))?$"
)

# Transitions
_TRANSITION_RE = re.compile(
    r'^(FADE\s+(IN|OUT|TO\s+BLACK)|CUT\s+TO|SMASH\s+CUT|MATCH\s+CUT|DISSOLVE\s+TO|'
    r'WIPE\s+TO|JUMP\s+CUT|IRIS\s+(IN|OUT)|.*\s+TO:)\s*\.?$',
    re.IGNORECASE
)


def _classify_line(line: str, prev_class: str) -> str:
    """
    Classify a script line into a screenplay element type.

    Args:
        line: The text line (stripped)
        prev_class: The class of the previous non-blank line

    Returns:
        One of: 'scene_heading', 'character_cue', 'dialogue',
                'parenthetical', 'transition', 'action', 'blank'
    """
    stripped = line.strip()

    if not stripped:
        return 'blank'

    # Scene heading: INT./EXT. etc.
    if _SCENE_HEADING_RE.match(stripped):
        return 'scene_heading'

    # Transition: CUT TO:, FADE OUT., etc.
    if _TRANSITION_RE.match(stripped):
        return 'transition'
    if stripped.endswith(':') and stripped == stripped.upper() and len(stripped) < 25:
        return 'transition'

    # Parenthetical: starts with ( and ends with )
    if stripped.startswith('(') and stripped.endswith(')'):
        if prev_class in ('character_cue', 'dialogue', 'parenthetical'):
            return 'parenthetical'

    # Character cue: ALL CAPS, short, not a scene heading
    if (_CHARACTER_CUE_RE.match(stripped)
            and len(stripped) < 45
            and stripped == stripped.upper()
            and len(stripped.split()) <= 5):
        return 'character_cue'

    # Dialogue: follows character cue, parenthetical, or previous dialogue
    if prev_class in ('character_cue', 'parenthetical', 'dialogue'):
        return 'dialogue'

    # Action: everything else
    return 'action'


# ============================================
# Line-by-line Screenplay Body Builder
# ============================================

def _build_screenplay_body(
    text: str,
    extractions: List[Dict],
    page_boundaries: Optional[List[int]] = None
) -> str:
    """
    Build the script body HTML with proper screenplay formatting.

    Splits text into lines, classifies each line as a screenplay element,
    applies extraction highlights within each line, and wraps in styled divs.
    """
    lines = text.split('\n')

    # Build character-position-to-line-index mapping
    line_starts = []
    pos = 0
    for line in lines:
        line_starts.append(pos)
        pos += len(line) + 1  # +1 for the \n

    # Build page-break positions set
    break_positions = set(page_boundaries) if page_boundaries else set()

    # Classify each line
    line_classes = []
    prev_class = 'blank'
    for line in lines:
        cls = _classify_line(line, prev_class)
        line_classes.append(cls)
        if cls != 'blank':
            prev_class = cls

    # CSS class mapping for each line type
    css_class_map = {
        'scene_heading': 'sp-scene-heading',
        'character_cue': 'sp-character-cue',
        'dialogue': 'sp-dialogue',
        'parenthetical': 'sp-parenthetical',
        'action': 'sp-action',
        'transition': 'sp-transition',
        'blank': 'sp-blank',
    }

    # Build HTML line by line
    html_parts = []

    for i, (line, line_cls) in enumerate(zip(lines, line_classes)):
        line_start = line_starts[i]
        line_end = line_start + len(line)

        # Insert page break if this line starts at a page boundary
        if line_start in break_positions:
            html_parts.append('<div class="page-break"></div>')

        # Blank lines → spacing div
        if line_cls == 'blank':
            html_parts.append('<div class="sp-blank"></div>')
            continue

        # Find extractions that overlap this line
        line_extractions = [
            e for e in extractions
            if (e.get('text_start', 0) < line_end
                and e.get('text_end', 0) > line_start)
        ]

        # Build highlighted line content
        inner_html = _highlight_line(line, line_start, line_extractions)

        # Wrap in styled div
        css_cls = css_class_map.get(line_cls, 'sp-action')
        html_parts.append(f'<div class="{css_cls}">{inner_html}</div>')

    return '\n'.join(html_parts)


def _highlight_line(line: str, line_start: int, extractions: List[Dict]) -> str:
    """
    Apply extraction highlight <span>s within a single line of text.

    Args:
        line: The line text
        line_start: Character position of this line within the full script text
        extractions: Extractions that overlap this line (pre-filtered)

    Returns:
        HTML string with highlight spans applied, text escaped
    """
    if not extractions:
        return html.escape(line)

    segments = []
    local_pos = 0  # position within the line

    for ext in extractions:
        ext_start = ext.get('text_start', 0)
        ext_end = ext.get('text_end', 0)
        cls = ext.get('extraction_class', 'unknown')
        attrs = ext.get('attributes', {})

        # Clamp to line boundaries
        span_start = max(ext_start - line_start, 0)
        span_end = min(ext_end - line_start, len(line))

        if span_start >= span_end or span_start < local_pos:
            continue

        # Text before this extraction span
        if span_start > local_pos:
            segments.append(html.escape(line[local_pos:span_start]))

        # Build tooltip
        tooltip_parts = [HIGHLIGHT_COLORS.get(cls, DEFAULT_HIGHLIGHT)['label']]
        if attrs:
            for k, v in attrs.items():
                if v and str(v).lower() not in ('none', 'null', ''):
                    tooltip_parts.append(f"{k}: {v}")
        tooltip = " | ".join(tooltip_parts)

        # Highlighted span
        span_text = line[span_start:span_end]
        segments.append(
            f'<span class="hl hl-{html.escape(cls)}" title="{html.escape(tooltip)}">'
            f'{html.escape(span_text)}'
            f'</span>'
        )

        local_pos = span_end

    # Remaining text after last extraction
    if local_pos < len(line):
        segments.append(html.escape(line[local_pos:]))

    return ''.join(segments)


def _build_cover_page(
    title: str,
    writer: str,
    meta: Dict,
    filter_classes: Optional[List[str]] = None
) -> str:
    """Build a cover page for the highlighted PDF."""
    lines = [
        '<div class="cover-page">',
        f'<h1>{html.escape(title)}</h1>',
    ]

    if writer:
        lines.append(f'<div class="subtitle">by {html.escape(writer)}</div>')

    if meta.get('draft_version'):
        lines.append(f'<div class="meta-line">{html.escape(meta["draft_version"])}</div>')

    if meta.get('contact_email'):
        lines.append(f'<div class="meta-line">{html.escape(meta["contact_email"])}</div>')

    if meta.get('contact_phone'):
        lines.append(f'<div class="meta-line">{html.escape(meta["contact_phone"])}</div>')

    lines.append(f'<div class="meta-line" style="margin-top: 0.5in;">'
                 f'HIGHLIGHTED SCRIPT BREAKDOWN</div>')

    if filter_classes:
        class_labels = [HIGHLIGHT_COLORS.get(c, DEFAULT_HIGHLIGHT)['label'] for c in filter_classes]
        lines.append(f'<div class="meta-line">Showing: {", ".join(class_labels)}</div>')

    lines.append(f'<div class="meta-line">Generated {datetime.now().strftime("%B %d, %Y")}</div>')
    lines.append('</div>')

    return "\n".join(lines)


def _build_legend(active_classes: set) -> str:
    """Build the color legend box."""
    if not active_classes:
        return ''

    items = []
    for cls in sorted(active_classes):
        colors = HIGHLIGHT_COLORS.get(cls, DEFAULT_HIGHLIGHT)
        items.append(
            f'<span class="legend-item" style="background:{colors["bg"]}; '
            f'border-left-color:{colors["border"]};">'
            f'{html.escape(colors["label"])}</span>'
        )

    return f"""
    <div class="legend">
        <h3>Extraction Legend</h3>
        <div class="legend-grid">
            {"".join(items)}
        </div>
    </div>"""


def _build_stats(extractions: List[Dict], active_classes: set, text_length: int) -> str:
    """Build a summary statistics section at the end."""
    if not extractions:
        return ''

    class_counts = {}
    for ext in extractions:
        cls = ext.get('extraction_class', 'unknown')
        class_counts[cls] = class_counts.get(cls, 0) + 1

    rows = []
    for cls in sorted(class_counts.keys()):
        colors = HIGHLIGHT_COLORS.get(cls, DEFAULT_HIGHLIGHT)
        rows.append(
            f'<tr><td style="color:{colors["border"]};">'
            f'{html.escape(colors["label"])}</td>'
            f'<td>{class_counts[cls]}</td></tr>'
        )

    total = len(extractions)
    coverage_chars = sum(
        (e.get('text_end', 0) - e.get('text_start', 0)) for e in extractions
    )
    coverage_pct = round(coverage_chars / max(text_length, 1) * 100, 1)

    return f"""
    <div class="stats-summary">
        <table>
            <tr><td>Total Extractions</td><td>{total}</td></tr>
            <tr><td>Text Coverage</td><td>{coverage_pct}%</td></tr>
            {" ".join(rows)}
        </table>
    </div>"""


# ============================================
# Public API
# ============================================

def generate_highlighted_pdf(
    script_id: str,
    filter_classes: Optional[List[str]] = None,
    supabase_client=None
) -> Tuple[bytes, str]:
    """
    Generate a highlighted script PDF.

    Args:
        script_id: UUID of the script
        filter_classes: Optional list of extraction_class values to include
        supabase_client: Optional Supabase client (uses admin if not provided)

    Returns:
        Tuple of (pdf_bytes, filename)

    Raises:
        ImportError: If WeasyPrint is not available
        ValueError: If script or extractions not found
    """
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("weasyprint is not installed. PDF generation is disabled.")

    if supabase_client is None:
        supabase_client = get_supabase_admin()

    # 1. Fetch script metadata + full text
    script_resp = supabase_client.table('scripts')\
        .select('id, title, full_text, writer_name, draft_version, '
                'contact_email, contact_phone, user_id')\
        .eq('id', script_id)\
        .single()\
        .execute()

    if not script_resp.data:
        raise ValueError(f"Script not found: {script_id}")

    script = script_resp.data
    full_text = script.get('full_text', '')

    if not full_text:
        raise ValueError(f"Script has no text content: {script_id}")

    # 2. Fetch extraction_metadata
    query = supabase_client.table('extraction_metadata')\
        .select('extraction_class, extraction_text, text_start, text_end, '
                'attributes, confidence')\
        .eq('script_id', script_id)\
        .order('text_start')

    if filter_classes:
        query = query.in_('extraction_class', filter_classes)

    ext_resp = query.execute()
    extractions = ext_resp.data if ext_resp.data else []

    if not extractions:
        raise ValueError(f"No extractions found for script: {script_id}")

    # 3. Fetch page boundaries (character positions where pages start)
    page_boundaries = _get_page_boundaries(script_id, supabase_client)

    # 4. Build HTML
    html_content = _build_highlighted_html(
        script_text=full_text,
        extractions=extractions,
        script_meta=script,
        filter_classes=filter_classes,
        page_boundaries=page_boundaries
    )

    # 5. Render PDF
    pdf_bytes = HTML(string=html_content).write_pdf()

    # 6. Build filename
    safe_title = (script.get('title') or 'script').replace(' ', '_')[:40]
    suffix = ''
    if filter_classes:
        suffix = '_' + '_'.join(filter_classes[:3])
    filename = f"{safe_title}_highlighted{suffix}.pdf"

    print(f"[HighlightedPDF] Generated {len(pdf_bytes)} bytes for script {script_id}")

    return pdf_bytes, filename


def generate_highlighted_html(
    script_id: str,
    filter_classes: Optional[List[str]] = None,
    supabase_client=None
) -> str:
    """
    Generate highlighted script as printable HTML (no PDF conversion).

    Same logic as generate_highlighted_pdf but returns raw HTML string
    for browser-side printing.
    """
    if supabase_client is None:
        supabase_client = get_supabase_admin()

    script_resp = supabase_client.table('scripts')\
        .select('id, title, full_text, writer_name, draft_version, '
                'contact_email, contact_phone, user_id')\
        .eq('id', script_id)\
        .single()\
        .execute()

    if not script_resp.data:
        raise ValueError(f"Script not found: {script_id}")

    script = script_resp.data
    full_text = script.get('full_text', '')

    if not full_text:
        raise ValueError(f"Script has no text content: {script_id}")

    query = supabase_client.table('extraction_metadata')\
        .select('extraction_class, extraction_text, text_start, text_end, '
                'attributes, confidence')\
        .eq('script_id', script_id)\
        .order('text_start')

    if filter_classes:
        query = query.in_('extraction_class', filter_classes)

    ext_resp = query.execute()
    extractions = ext_resp.data if ext_resp.data else []

    page_boundaries = _get_page_boundaries(script_id, supabase_client)

    return _build_highlighted_html(
        script_text=full_text,
        extractions=extractions,
        script_meta=script,
        filter_classes=filter_classes,
        page_boundaries=page_boundaries
    )


def _get_page_boundaries(script_id: str, supabase_client) -> Optional[List[int]]:
    """
    Get character positions where each page starts.
    Uses script_pages table if available.
    """
    try:
        pages_resp = supabase_client.table('script_pages')\
            .select('page_number, page_text')\
            .eq('script_id', script_id)\
            .order('page_number')\
            .execute()

        if not pages_resp.data or len(pages_resp.data) < 2:
            return None

        boundaries = []
        offset = 0
        for page in pages_resp.data:
            if page['page_number'] > 1:
                boundaries.append(offset)
            page_text = page.get('page_text', '') or ''
            offset += len(page_text) + 1  # +1 for newline separator

        return boundaries if boundaries else None

    except Exception as e:
        print(f"[HighlightedPDF] Could not load page boundaries: {e}")
        return None
