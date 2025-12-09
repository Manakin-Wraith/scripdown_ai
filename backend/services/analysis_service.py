import google.generativeai as genai
import os
import json
import re
import time
from db.db_connection import get_db

# Rate limiting for Gemini API (free tier: 2 requests/minute)
_last_request_time = 0
_min_request_interval = 35  # seconds between requests

def get_gemini_model():
    """Get configured Gemini model."""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key or api_key == 'your_api_key_here':
        raise ValueError("GEMINI_API_KEY not configured")
    
    genai.configure(api_key=api_key)
    # Use gemini-2.5-flash - latest model with good quota
    return genai.GenerativeModel('gemini-2.5-flash')


def rate_limit_wait():
    """Wait if needed to respect rate limits."""
    global _last_request_time
    current_time = time.time()
    elapsed = current_time - _last_request_time
    
    if elapsed < _min_request_interval:
        wait_time = _min_request_interval - elapsed
        print(f"Rate limiting: waiting {wait_time:.1f}s before next API call")
        time.sleep(wait_time)
    
    _last_request_time = time.time()


def analyze_characters(script_id, characters, scenes):
    """
    Analyze characters using Gemini AI with emotional arc per scene.
    
    Args:
        script_id: The script ID
        characters: Dict of character names to their scene appearances
        scenes: List of scene objects with descriptions
    
    Returns:
        Dict with character analysis results including emotional arc
    """
    # Check cache first
    cached = get_cached_analysis(script_id, 'characters')
    if cached:
        return cached
    
    # Rate limit before API call
    rate_limit_wait()
    
    model = get_gemini_model()
    
    # Build detailed scene context with character info
    scene_details = []
    for s in scenes[:10]:
        scene_chars = s.get('characters', [])
        scene_details.append(
            f"Scene {s.get('scene_number', '?')} ({s.get('setting', 'Unknown')}): "
            f"{s.get('description', 'No description')} "
            f"[Characters: {', '.join(scene_chars) if scene_chars else 'None'}]"
        )
    scene_context = "\n".join(scene_details)
    
    # Build character list with their specific scenes
    char_details = []
    for name, char_scenes in characters.items():
        scene_nums = [str(s.get('scene_number', '?')) for s in char_scenes]
        char_details.append(f"- {name}: appears in scene(s) {', '.join(scene_nums)}")
    char_list = "\n".join(char_details)
    
    prompt = f"""
Analyze these characters from a screenplay. Provide comprehensive character analysis including their emotional journey, scene-by-scene breakdown, and story arc.

CHARACTERS:
{char_list}

SCENE CONTEXT:
{scene_context}

For each character, provide a DETAILED analysis including:
1. Description (2-3 sentences about who they are)
2. Role type: "Lead", "Supporting", or "Minor"
3. Personality traits (3-5 key traits)
4. Backstory (what we can infer about their past, history, background)
5. Motivation (what drives this character, their goals and desires)
6. Character arc summary (how they transform through the story)
7. DETAILED scene-by-scene breakdown with:
   - Emotional state and intensity (1-10)
   - Character's objective in that scene
   - Key actions they take
   - Dialogue notes (nature of their speech)
   - Arc position (beginning/rising/climax/falling/resolution)
8. Relationships with other characters

Return ONLY valid JSON in this exact format:
{{
    "characters": {{
        "CHARACTER_NAME": {{
            "description": "Detailed description of the character",
            "role_type": "Lead|Supporting|Minor",
            "traits": ["trait1", "trait2", "trait3"],
            "backstory": "What we can infer about their past, their history and background",
            "motivation": "What drives this character, their goals and desires",
            "arc_summary": "How the character transforms through the story",
            "scene_breakdown": {{
                "1": {{
                    "emotion": "despair",
                    "intensity": 9,
                    "emotional_description": "Character is in deep emotional pain",
                    "objective": "What the character wants to achieve in this scene",
                    "key_actions": ["action1", "action2", "action3"],
                    "dialogue_notes": "Nature of their dialogue (e.g., prayer-like, aggressive, silent)",
                    "arc_position": "beginning|rising|climax|falling|resolution"
                }}
            }},
            "relationships": [
                {{
                    "character": "OTHER_NAME",
                    "type": "antagonist|ally|love_interest|family|friend|enemy",
                    "description": "Nature of their relationship",
                    "dynamic": "Brief insight about the relationship dynamic"
                }}
            ]
        }}
    }},
    "story_arc": {{
        "theme": "Main theme of the story",
        "tone": "Overall tone (dark, hopeful, tragic, etc.)",
        "conflict_type": "man_vs_self|man_vs_man|man_vs_society|man_vs_nature",
        "setting_mood": "Overall mood established by the settings"
    }},
    "insights": {{
        "protagonist": "Name of likely protagonist",
        "antagonist": "Name of likely antagonist (if any)",
        "ensemble": true/false,
        "narrative_style": "Brief description of the narrative approach"
    }}
}}

Return only the JSON, no markdown formatting.
"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.7)
        )
        
        response_text = response.text.strip()
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        
        result = json.loads(response_text)
        
        # Cache the result
        cache_analysis(script_id, 'characters', result)
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error in character analysis: {e}")
        return {"characters": {}, "error": "Failed to parse AI response"}
    except Exception as e:
        print(f"Gemini API error in character analysis: {e}")
        return {"characters": {}, "error": str(e)}


def analyze_locations(script_id, locations, scenes):
    """
    Analyze locations using Gemini AI.
    
    Args:
        script_id: The script ID
        locations: Dict of location names to their scene appearances
        scenes: List of scene objects with descriptions
    
    Returns:
        Dict with location analysis results
    """
    # Check cache first
    cached = get_cached_analysis(script_id, 'locations')
    if cached:
        return cached
    
    # Rate limit before API call
    rate_limit_wait()
    
    model = get_gemini_model()
    
    # Build context from scenes
    scene_context = "\n".join([
        f"Scene {s.get('scene_number', '?')} at {s.get('setting', 'Unknown')}: {s.get('description', 'No description')}"
        for s in scenes[:10]
    ])
    
    # Build location list
    loc_list = "\n".join([
        f"- {name}: {len(loc_scenes)} scene(s)"
        for name, loc_scenes in locations.items()
    ])
    
    prompt = f"""
Analyze these locations from a screenplay and provide detailed insights.

LOCATIONS:
{loc_list}

SCENE CONTEXT:
{scene_context}

For each location, provide:
1. A brief atmosphere description (1-2 sentences about the mood/feel)
2. Type: "Interior" or "Exterior"
3. Time of day typically used: "Day", "Night", "Dawn/Dusk", or "Various"
4. Key set pieces or props typically needed
5. Mood/tone of scenes at this location

Return ONLY valid JSON in this exact format:
{{
    "locations": {{
        "LOCATION_NAME": {{
            "atmosphere": "Description of the atmosphere and mood",
            "type": "Interior|Exterior",
            "time_of_day": "Day|Night|Dawn/Dusk|Various",
            "set_pieces": ["item1", "item2"],
            "mood": "tense|calm|romantic|action|dramatic|etc"
        }}
    }},
    "insights": {{
        "primary_location": "Most frequently used location",
        "location_variety": "low|medium|high",
        "production_notes": "Brief note about location requirements"
    }}
}}

Return only the JSON, no markdown formatting.
"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.7)
        )
        
        response_text = response.text.strip()
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        
        result = json.loads(response_text)
        
        # Cache the result
        cache_analysis(script_id, 'locations', result)
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error in location analysis: {e}")
        return {"locations": {}, "error": "Failed to parse AI response"}
    except Exception as e:
        print(f"Gemini API error in location analysis: {e}")
        return {"locations": {}, "error": str(e)}


def get_cached_analysis(script_id, analysis_type):
    """Get cached analysis from database."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT analysis_data FROM script_analysis 
            WHERE script_id = ? AND analysis_type = ?
        """, (script_id, analysis_type))
        
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            return json.loads(row[0])
        return None
        
    except Exception as e:
        print(f"Error getting cached analysis: {e}")
        return None


def cache_analysis(script_id, analysis_type, data):
    """Cache analysis results to database."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Delete existing cache
        cursor.execute("""
            DELETE FROM script_analysis 
            WHERE script_id = ? AND analysis_type = ?
        """, (script_id, analysis_type))
        
        # Insert new cache
        cursor.execute("""
            INSERT INTO script_analysis (script_id, analysis_type, analysis_data)
            VALUES (?, ?, ?)
        """, (script_id, analysis_type, json.dumps(data)))
        
        db.commit()
        cursor.close()
        
    except Exception as e:
        print(f"Error caching analysis: {e}")


def clear_analysis_cache(script_id):
    """Clear all cached analysis for a script."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            DELETE FROM script_analysis WHERE script_id = ?
        """, (script_id,))
        
        db.commit()
        cursor.close()
        
    except Exception as e:
        print(f"Error clearing analysis cache: {e}")
