"""
AI-based Scene Detection for Non-Standard Scripts

This module provides AI-powered scene detection for scripts that don't use
standard screenplay formatting (INT./EXT. headers).

It uses OpenAI to analyze the text and identify logical scene breaks.
"""

import os
import json
import re
from database import get_db

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def detect_scenes_with_ai(script_id: int, full_text: str) -> int:
    """
    Use AI to detect scene breaks in non-standard scripts.
    
    Args:
        script_id: The script ID in the database
        full_text: The full text content of the script
        
    Returns:
        Number of scenes detected and created
    """
    if not OPENAI_AVAILABLE:
        raise ImportError("OpenAI not available")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    client = OpenAI(api_key=api_key)
    
    # Truncate text if too long (keep first ~15000 chars for analysis)
    analysis_text = full_text[:15000] if len(full_text) > 15000 else full_text
    
    # Ask AI to identify scene breaks
    prompt = f"""Analyze this script/document and identify distinct scenes or sections.
A scene change typically occurs when:
- The location changes
- Time passes significantly
- There's a clear narrative break
- New characters enter a different setting

For each scene you identify, provide:
1. A brief title/setting description (max 50 chars)
2. The approximate starting line or paragraph
3. Whether it's interior (INT) or exterior (EXT) if determinable

Return your response as a JSON array like this:
[
  {{"title": "Scene description", "int_ext": "INT", "start_marker": "First few words of scene"}},
  ...
]

If you cannot identify clear scenes, return an empty array [].

SCRIPT TEXT:
---
{analysis_text}
---

Respond ONLY with the JSON array, no other text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a screenplay analyst. Identify scene breaks in scripts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        # Handle markdown code blocks if present
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n?', '', result_text)
            result_text = re.sub(r'\n?```$', '', result_text)
        
        scenes_data = json.loads(result_text)
        
        if not scenes_data or not isinstance(scenes_data, list):
            return 0
        
        # Create scenes in database
        return create_scenes_from_ai_detection(script_id, full_text, scenes_data)
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response: {e}")
        raise
    except Exception as e:
        print(f"AI scene detection failed: {e}")
        raise


def create_scenes_from_ai_detection(script_id: int, full_text: str, scenes_data: list) -> int:
    """
    Create scene records from AI detection results.
    
    Args:
        script_id: The script ID
        full_text: Full script text
        scenes_data: List of scene dicts from AI
        
    Returns:
        Number of scenes created
    """
    db = get_db()
    cursor = db.cursor()
    
    scenes_created = 0
    lines = full_text.split('\n')
    
    for i, scene in enumerate(scenes_data):
        title = scene.get('title', f'Scene {i + 1}')[:100]
        int_ext = scene.get('int_ext', 'INT').upper()
        if int_ext not in ['INT', 'EXT', 'INT/EXT']:
            int_ext = 'INT'
        
        start_marker = scene.get('start_marker', '')
        
        # Try to find the start position in text
        text_start = 0
        if start_marker:
            pos = full_text.find(start_marker[:50])
            if pos > 0:
                text_start = pos
        
        # Calculate approximate page (assuming ~3000 chars per page)
        page_start = max(1, text_start // 3000 + 1)
        
        # Get scene text (from this marker to next scene or end)
        if i + 1 < len(scenes_data):
            next_marker = scenes_data[i + 1].get('start_marker', '')
            if next_marker:
                next_pos = full_text.find(next_marker[:50], text_start + 100)
                if next_pos > text_start:
                    scene_text = full_text[text_start:next_pos]
                else:
                    scene_text = full_text[text_start:text_start + 3000]
            else:
                scene_text = full_text[text_start:text_start + 3000]
        else:
            scene_text = full_text[text_start:]
        
        # Limit scene text length
        scene_text = scene_text[:5000]
        
        try:
            cursor.execute("""
                INSERT INTO scenes (
                    script_id, scene_number, int_ext, setting, 
                    time_of_day, page_start, page_end, scene_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                script_id,
                str(i + 1),
                int_ext,
                title,
                'DAY',  # Default
                page_start,
                page_start,
                scene_text
            ))
            scenes_created += 1
        except Exception as e:
            print(f"Failed to create scene {i + 1}: {e}")
            continue
    
    db.commit()
    return scenes_created


def detect_scenes_heuristic(script_id: int, full_text: str) -> int:
    """
    Heuristic-based scene detection as fallback.
    
    Looks for patterns like:
    - All-caps lines (potential scene headers)
    - Blank line followed by location-like text
    - Time indicators (LATER, CONTINUOUS, etc.)
    """
    db = get_db()
    cursor = db.cursor()
    
    # Patterns that might indicate scene breaks
    scene_indicators = [
        r'^[A-Z][A-Z\s\-\.]+$',  # All caps line
        r'^\s*(LATER|CONTINUOUS|MOMENTS? LATER|SAME TIME)',
        r'^\s*\d+\s*$',  # Just a number (scene number)
        r'^[A-Z]+\s*[-–—]\s*[A-Z]+',  # LOCATION - TIME pattern
    ]
    
    lines = full_text.split('\n')
    potential_breaks = []
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        for pattern in scene_indicators:
            if re.match(pattern, line_stripped):
                potential_breaks.append({
                    'line_num': i,
                    'text': line_stripped,
                    'position': full_text.find(line)
                })
                break
    
    # Filter to reasonable number of scenes (max 100, min 1)
    if len(potential_breaks) > 100:
        # Take every Nth break
        step = len(potential_breaks) // 50
        potential_breaks = potential_breaks[::step]
    
    if not potential_breaks:
        # Create at least one scene with full text
        cursor.execute("""
            INSERT INTO scenes (
                script_id, scene_number, int_ext, setting, 
                time_of_day, page_start, page_end, scene_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            script_id,
            '1',
            'INT',
            'Full Document',
            'DAY',
            1,
            1,
            full_text[:5000]
        ))
        db.commit()
        return 1
    
    scenes_created = 0
    for i, break_info in enumerate(potential_breaks):
        # Get text from this break to next
        start_pos = break_info['position']
        if i + 1 < len(potential_breaks):
            end_pos = potential_breaks[i + 1]['position']
        else:
            end_pos = len(full_text)
        
        scene_text = full_text[start_pos:end_pos][:5000]
        setting = break_info['text'][:100]
        
        try:
            cursor.execute("""
                INSERT INTO scenes (
                    script_id, scene_number, int_ext, setting, 
                    time_of_day, page_start, page_end, scene_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                script_id,
                str(i + 1),
                'INT',
                setting,
                'DAY',
                max(1, start_pos // 3000 + 1),
                max(1, end_pos // 3000 + 1),
                scene_text
            ))
            scenes_created += 1
        except Exception as e:
            print(f"Failed to create heuristic scene {i + 1}: {e}")
            continue
    
    db.commit()
    return scenes_created
