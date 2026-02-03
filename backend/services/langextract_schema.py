"""
LangExtract Screenplay Extraction Schema
Defines extraction classes and attributes for screenplay analysis.
"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class ExtractionClass:
    """Defines an extraction class with its expected attributes."""
    name: str
    description: str
    attributes: List[str]
    examples: List[str]


# Screenplay Extraction Schema
SCREENPLAY_EXTRACTION_SCHEMA = {
    "scene_header": ExtractionClass(
        name="scene_header",
        description="Scene heading with INT/EXT, setting, and time of day",
        attributes=[
            "int_ext",        # INT or EXT
            "setting",        # Location name
            "time_of_day",    # DAY, NIGHT, DAWN, DUSK, etc.
            "scene_number"    # Optional scene number
        ],
        examples=[
            "INT. COFFEE SHOP - DAY",
            "EXT. CITY STREET - NIGHT",
            "INT./EXT. CAR - CONTINUOUS"
        ]
    ),
    
    "character": ExtractionClass(
        name="character",
        description="Character name with contextual information",
        attributes=[
            "name",              # Character name
            "action",            # What they're doing
            "emotional_state",   # Current emotion
            "first_appearance"   # Boolean if first time in script
        ],
        examples=[
            "JANE enters, looking nervous",
            "DETECTIVE MORGAN slams the door",
            "SARAH (20s, anxious) paces"
        ]
    ),
    
    "dialogue": ExtractionClass(
        name="dialogue",
        description="Character dialogue with tone and context",
        attributes=[
            "character",      # Who's speaking
            "tone",          # Angry, sad, sarcastic, etc.
            "parenthetical", # (beat), (sotto), etc.
            "subtext"        # What's really being said
        ],
        examples=[
            "JOHN: (angry) I told you not to come here!",
            "MARY: (whispers) We need to leave. Now.",
            "BOSS: (sarcastically) Great work, as always."
        ]
    ),
    
    "action": ExtractionClass(
        name="action",
        description="Action lines describing what happens",
        attributes=[
            "type",           # movement, violence, emotional, technical
            "intensity",      # low, medium, high
            "characters",     # Who's involved
            "importance"      # plot_critical, character_development, atmosphere
        ],
        examples=[
            "The building EXPLODES in a ball of fire",
            "She gently touches his face, tears streaming",
            "A shadow moves across the wall"
        ]
    ),
    
    "prop": ExtractionClass(
        name="prop",
        description="Props and objects mentioned in the scene",
        attributes=[
            "item_name",      # Name of the prop
            "character_using", # Who uses it
            "importance",     # plot_critical, background, character_defining
            "condition",      # new, worn, broken, vintage
            "era",           # time period if relevant
            "action"         # how it's used
        ],
        examples=[
            "vintage typewriter - John types furiously",
            "bloodied knife on the table",
            "her grandmother's locket"
        ]
    ),
    
    "wardrobe": ExtractionClass(
        name="wardrobe",
        description="Clothing and costume details",
        attributes=[
            "character",      # Who's wearing it
            "description",    # What they're wearing
            "condition",      # pristine, rumpled, torn, etc.
            "formality",      # casual, business, formal, costume
            "significance"    # character_defining, plot_relevant, atmospheric
        ],
        examples=[
            "JANE - elegant black dress, slightly torn",
            "DETECTIVE - rumpled suit, coffee stains",
            "SOLDIER - full combat gear, mud-covered"
        ]
    ),
    
    "makeup_hair": ExtractionClass(
        name="makeup_hair",
        description="Makeup, hair, and physical appearance details",
        attributes=[
            "character",      # Who
            "type",          # makeup, hair, injury, aging
            "description",    # Specific details
            "emotional_context", # Why it matters
            "continuity_note"    # Important for tracking
        ],
        examples=[
            "MARY - smeared mascara from crying",
            "JOHN - fresh scar across cheek",
            "ELDERLY WOMAN - silver hair in tight bun"
        ]
    ),
    
    "special_fx": ExtractionClass(
        name="special_fx",
        description="Special effects, VFX, and technical requirements",
        attributes=[
            "type",          # practical, vfx, sfx, stunt
            "description",    # What happens
            "complexity",     # simple, moderate, complex
            "safety_concern"  # Boolean
        ],
        examples=[
            "Car flips and explodes (stunt + VFX)",
            "Ghost appears in mirror (VFX)",
            "Rain effect throughout scene (practical)"
        ]
    ),
    
    "vehicle": ExtractionClass(
        name="vehicle",
        description="Vehicles and transportation",
        attributes=[
            "type",          # car, motorcycle, helicopter, etc.
            "description",    # Make, model, condition
            "era",           # time period
            "usage",         # background, featured, stunt
            "condition"      # pristine, worn, damaged
        ],
        examples=[
            "1967 Mustang - cherry red, pristine",
            "Police cruiser - lights flashing",
            "Rusted pickup truck"
        ]
    ),
    
    "location_detail": ExtractionClass(
        name="location_detail",
        description="Specific location details and atmosphere",
        attributes=[
            "setting",        # Where
            "atmosphere",     # mood, lighting, weather
            "time_period",    # era if relevant
            "crowd_size",     # empty, sparse, crowded
            "practical_notes" # Access, permissions, etc.
        ],
        examples=[
            "Abandoned warehouse - dark, dusty, echoing",
            "Busy restaurant - lunch rush, noisy",
            "Mountain peak - dawn light, fog rolling in"
        ]
    ),
    
    "emotion": ExtractionClass(
        name="emotion",
        description="Emotional beats and character feelings",
        attributes=[
            "character",      # Who feels it
            "emotion_type",   # joy, anger, fear, sadness, etc.
            "intensity",      # subtle, moderate, intense
            "trigger",        # What caused it
            "manifestation"   # How it shows
        ],
        examples=[
            "JANE - overwhelming grief (tears, collapse)",
            "JOHN - simmering rage (clenched fists)",
            "MARY - quiet relief (exhales, shoulders drop)"
        ]
    ),
    
    "relationship": ExtractionClass(
        name="relationship",
        description="Character relationships and dynamics",
        attributes=[
            "characters",     # Who's involved
            "type",          # romantic, familial, professional, adversarial
            "dynamic",       # power balance, tension level
            "development"    # forming, strengthening, fracturing
        ],
        examples=[
            "JANE & JOHN - romantic tension building",
            "BOSS & EMPLOYEE - power imbalance, fear",
            "SIBLINGS - old resentment surfacing"
        ]
    ),
    
    "sound": ExtractionClass(
        name="sound",
        description="Sound effects and audio cues",
        attributes=[
            "type",          # diegetic, non-diegetic
            "description",    # What we hear
            "source",        # Where it comes from
            "importance",     # atmosphere, plot_critical, character_cue
            "volume"         # subtle, moderate, loud
        ],
        examples=[
            "Distant SIRENS approaching",
            "PHONE RINGS - shrill, insistent",
            "Soft JAZZ MUSIC from the radio"
        ]
    ),
    
    "transition": ExtractionClass(
        name="transition",
        description="Scene transitions and time jumps",
        attributes=[
            "type",          # CUT TO, DISSOLVE TO, FADE TO, MATCH CUT
            "timing",        # immediate, gradual
            "time_jump",     # how much time passes
            "purpose"        # pacing, contrast, parallel action
        ],
        examples=[
            "CUT TO: Same location, 3 hours later",
            "DISSOLVE TO: Flashback - 10 years ago",
            "MATCH CUT: Her face to her daughter's face"
        ]
    )
}


def get_extraction_classes() -> List[str]:
    """Return list of all extraction class names."""
    return list(SCREENPLAY_EXTRACTION_SCHEMA.keys())


def get_class_attributes(class_name: str) -> List[str]:
    """Get attributes for a specific extraction class."""
    if class_name in SCREENPLAY_EXTRACTION_SCHEMA:
        return SCREENPLAY_EXTRACTION_SCHEMA[class_name].attributes
    return []


def get_class_description(class_name: str) -> str:
    """Get description for a specific extraction class."""
    if class_name in SCREENPLAY_EXTRACTION_SCHEMA:
        return SCREENPLAY_EXTRACTION_SCHEMA[class_name].description
    return ""


# Prompt description for LangExtract
SCREENPLAY_EXTRACTION_PROMPT = """
Extract screenplay elements in order of appearance from the script text.

CRITICAL RULES:
1. Use EXACT text from the script - do not paraphrase or summarize
2. Extract entities in the order they appear
3. Do not overlap entity spans (each word should belong to only one extraction)
4. Provide meaningful attributes for context and department use
5. Focus on production-relevant details (props, wardrobe, locations, etc.)
6. Capture emotional context for casting and performance
7. Note continuity-critical details (injuries, wardrobe changes, etc.)

EXTRACTION PRIORITIES:
- Scene headers (always extract)
- Characters (first appearance and significant actions)
- Props and wardrobe (production departments need these)
- Locations and atmosphere (for scouting and design)
- Special effects and stunts (for budgeting and safety)
- Emotional beats (for casting and direction)

ATTRIBUTE GUIDELINES:
- Be specific but concise
- Use industry-standard terminology
- Flag plot-critical vs. background elements
- Note safety concerns for stunts/effects
- Indicate era/period for props and wardrobe
"""
