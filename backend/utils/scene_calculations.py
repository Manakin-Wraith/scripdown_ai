"""
Scene Length Calculation Utilities

Provides industry-standard scene length calculations in eighths.
1 screenplay page = 8 eighths
1/8 page ≈ 1 minute of screen time
"""

def calculate_eighths_from_content(scene_text):
    """
    Calculate scene length in eighths from actual content.
    More accurate than page range method.
    
    Industry standard:
    - 1 page ≈ 55 lines (standard screenplay formatting)
    - 1 page = 8 eighths
    
    Args:
        scene_text (str): The scene content (description + action + dialogue)
    
    Returns:
        int: Scene length in eighths (minimum 1, maximum 80)
    
    Examples:
        >>> calculate_eighths_from_content("INT. OFFICE - DAY\\n\\nJohn enters.")
        2  # Very short scene ≈ 2/8 page
        >>> calculate_eighths_from_content("..." * 300)  # Long scene
        24  # 3 pages = 24/8
    """
    if not scene_text or not scene_text.strip():
        return 8  # Default to 1 page
    
    # Count lines
    lines = len(scene_text.strip().split('\n'))
    
    # Calculate eighths (55 lines = 8 eighths)
    # Round to nearest eighth
    eighths = round((lines / 55) * 8)
    
    # Minimum 1/8, maximum 80 eighths (10 pages)
    return max(1, min(eighths, 80))


def calculate_eighths_from_pages(page_start, page_end, scene_text=None):
    """
    Calculate scene length in eighths from page range.
    Less accurate than content-based method. Use as fallback.
    
    Args:
        page_start (int): Starting page number
        page_end (int): Ending page number
        scene_text (str, optional): Scene text for more accurate calculation
    
    Returns:
        int: Scene length in eighths
    
    Examples:
        >>> calculate_eighths_from_pages(1, 1)
        8  # 1 full page
        >>> calculate_eighths_from_pages(5, 7)
        24  # 3 pages
    """
    if not page_start or not page_end:
        return 8  # Default to 1 page
    
    # If we have scene text, use line-based calculation (most accurate)
    if scene_text and scene_text.strip():
        return calculate_eighths_from_content(scene_text)
    
    # Otherwise, estimate based on page span
    # page_end - page_start + 1 gives the number of pages (e.g., pages 4-6 = 3 pages)
    page_span = page_end - page_start + 1
    
    # Simple estimation: each page = 8 eighths
    # This assumes full pages, which is reasonable without actual content
    total_eighths = page_span * 8
    
    # Cap at maximum 80 eighths (10 pages)
    return max(1, min(total_eighths, 80))


def format_eighths(eighths):
    """
    Format eighths as readable string for display in reports.
    
    Args:
        eighths (int): Scene length in eighths
    
    Returns:
        str: Formatted string (e.g., "2 3/8", "1", "4/8")
    
    Examples:
        >>> format_eighths(8)
        '1'
        >>> format_eighths(12)
        '1 4/8'
        >>> format_eighths(3)
        '3/8'
        >>> format_eighths(16)
        '2'
        >>> format_eighths(None)
        '—'
    """
    if not eighths:
        return "—"
    
    full_pages = eighths // 8
    remaining_eighths = eighths % 8
    
    if remaining_eighths == 0:
        # Whole pages only
        return str(full_pages) if full_pages > 0 else "—"
    elif full_pages == 0:
        # Fractional page only
        return f"{remaining_eighths}/8"
    else:
        # Mixed: whole pages + fraction
        return f"{full_pages} {remaining_eighths}/8"


def calculate_total_script_length(scenes):
    """
    Calculate total script length from list of scenes.
    
    Args:
        scenes (list): List of scene dictionaries with 'page_length_eighths' key
    
    Returns:
        tuple: (total_eighths, total_pages_decimal)
    
    Examples:
        >>> scenes = [{'page_length_eighths': 8}, {'page_length_eighths': 12}]
        >>> calculate_total_script_length(scenes)
        (20, 2.5)
    """
    total_eighths = sum(s.get('page_length_eighths', 8) for s in scenes)
    total_pages = total_eighths / 8
    return total_eighths, total_pages


def get_scene_length_category(eighths):
    """
    Categorize scene length for analysis and color-coding.
    
    Args:
        eighths (int): Scene length in eighths
    
    Returns:
        str: Category ('very_short', 'short', 'medium', 'long', 'very_long')
    
    Examples:
        >>> get_scene_length_category(2)
        'very_short'
        >>> get_scene_length_category(8)
        'medium'
        >>> get_scene_length_category(24)
        'long'
    """
    if not eighths:
        return 'unknown'
    
    if eighths <= 2:  # <= 1/4 page
        return 'very_short'
    elif eighths <= 4:  # <= 1/2 page
        return 'short'
    elif eighths <= 12:  # <= 1.5 pages
        return 'medium'
    elif eighths <= 24:  # <= 3 pages
        return 'long'
    else:  # > 3 pages
        return 'very_long'
