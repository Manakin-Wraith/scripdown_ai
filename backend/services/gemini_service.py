import google.generativeai as genai
import os
import json
import re

def analyze_script(script_text):
    """
    Analyze script using Gemini and extract detailed breakdown of first 3 scenes.
    Returns a dictionary with scenes array containing comprehensive details.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key or api_key == 'your_api_key_here':
        raise ValueError("GEMINI_API_KEY not configured. Please add your API key to backend/.env")
    
    genai.configure(api_key=api_key)
    
    # Use Gemini Pro Latest (free tier available)
    model = genai.GenerativeModel('gemini-pro-latest')
    
    # Focus on first 3 scenes with detailed breakdown
    prompt = f"""
Analyze this screenplay and extract DETAILED information for the FIRST 3 SCENES ONLY.

For each scene, provide comprehensive breakdown including:
- Scene number (1, 2, or 3)
- Setting/Location (e.g., "COFFEE SHOP - INT - DAY")
- Characters present (list ALL character names in UPPERCASE)
- Props (list ALL props, objects, items mentioned or needed)
- Special FX (visual effects, practical effects, stunts)
- Wardrobe notes (costume details, specific clothing mentioned)
- Makeup/Hair notes (any specific requirements)
- Vehicles (cars, bikes, etc.)
- Atmosphere (lighting, weather, mood)
- Description (detailed 2-3 sentence summary of what happens)

Return ONLY valid JSON in this exact format:
{{
    "scenes": [
        {{
            "scene_number": 1,
            "setting": "COFFEE SHOP - INT - DAY",
            "characters": ["JOHN", "MARY", "BARISTA"],
            "props": ["coffee cup", "laptop", "newspaper", "cell phone"],
            "special_fx": ["steam from coffee", "rain visible through window"],
            "wardrobe": ["John: business suit", "Mary: casual dress"],
            "makeup_hair": ["Mary: professional updo"],
            "vehicles": [],
            "atmosphere": "Warm, cozy lighting. Rainy day outside.",
            "description": "John meets Mary at a busy coffee shop to discuss the project. The atmosphere is tense as they debate their next move while rain pours outside."
        }}
    ]
}}

IMPORTANT: 
- Extract ONLY the first 3 scenes
- Be thorough and detailed for each category
- If a category doesn't apply, use an empty array [] or empty string ""
- Look for implied needs (e.g., if someone drinks coffee, include "coffee cup" in props)

Script:
{script_text[:15000]}

Return only the JSON, no markdown formatting or additional text.
"""
    
    try:
        # Generate content with Gemini
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,  # Lower temperature for more consistent output
            )
        )
        
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        
        # Parse JSON from response
        result = json.loads(response_text)
        
        # Validate structure
        if 'scenes' not in result:
            result = {"scenes": []}
        
        # Ensure we only have max 3 scenes
        if len(result['scenes']) > 3:
            result['scenes'] = result['scenes'][:3]
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response text: {response_text[:500]}")
        # Return empty scenes if parsing fails
        return {"scenes": [], "error": "Failed to parse AI response"}
    except Exception as e:
        print(f"Gemini API error: {e}")
        return {"scenes": [], "error": str(e)}




