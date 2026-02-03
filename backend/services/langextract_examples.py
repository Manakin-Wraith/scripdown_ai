"""
LangExtract Few-Shot Examples for Screenplay Extraction
High-quality examples demonstrating proper extraction patterns.
"""

import langextract as lx


# Example 1: Action Scene with Multiple Elements
EXAMPLE_1_ACTION_SCENE = lx.data.ExampleData(
    text="""INT. ABANDONED WAREHOUSE - NIGHT

The rusted metal door CREAKS open. DETECTIVE SARAH MORGAN (40s, exhausted) steps inside, her flashlight cutting through the darkness.

SARAH
(whispers)
Anyone here?

A SHADOW moves across the far wall. Sarah's hand instinctively moves to her holstered gun.

She spots a VINTAGE TYPEWRITER on a dusty desk, still loaded with paper. The keys are stained with dried blood.""",
    
    extractions=[
        lx.data.Extraction(
            extraction_class="scene_header",
            extraction_text="INT. ABANDONED WAREHOUSE - NIGHT",
            attributes={
                "int_ext": "INT",
                "setting": "ABANDONED WAREHOUSE",
                "time_of_day": "NIGHT"
            }
        ),
        lx.data.Extraction(
            extraction_class="sound",
            extraction_text="The rusted metal door CREAKS open",
            attributes={
                "type": "diegetic",
                "description": "door creaking",
                "source": "metal door",
                "importance": "atmosphere",
                "volume": "moderate"
            }
        ),
        lx.data.Extraction(
            extraction_class="character",
            extraction_text="DETECTIVE SARAH MORGAN (40s, exhausted)",
            attributes={
                "name": "DETECTIVE SARAH MORGAN",
                "action": "steps inside",
                "emotional_state": "exhausted",
                "first_appearance": "true"
            }
        ),
        lx.data.Extraction(
            extraction_class="prop",
            extraction_text="her flashlight",
            attributes={
                "item_name": "flashlight",
                "character_using": "SARAH MORGAN",
                "importance": "character_defining",
                "condition": "functional",
                "action": "cutting through darkness"
            }
        ),
        lx.data.Extraction(
            extraction_class="dialogue",
            extraction_text="Anyone here?",
            attributes={
                "character": "SARAH",
                "tone": "cautious",
                "parenthetical": "whispers",
                "subtext": "nervous, expecting danger"
            }
        ),
        lx.data.Extraction(
            extraction_class="action",
            extraction_text="A SHADOW moves across the far wall",
            attributes={
                "type": "movement",
                "intensity": "medium",
                "characters": "unknown",
                "importance": "plot_critical"
            }
        ),
        lx.data.Extraction(
            extraction_class="prop",
            extraction_text="holstered gun",
            attributes={
                "item_name": "gun",
                "character_using": "SARAH MORGAN",
                "importance": "plot_critical",
                "condition": "holstered",
                "action": "hand moves to it instinctively"
            }
        ),
        lx.data.Extraction(
            extraction_class="prop",
            extraction_text="VINTAGE TYPEWRITER on a dusty desk",
            attributes={
                "item_name": "vintage typewriter",
                "character_using": "none",
                "importance": "plot_critical",
                "condition": "dusty, blood-stained keys",
                "era": "vintage",
                "action": "still loaded with paper"
            }
        ),
        lx.data.Extraction(
            extraction_class="location_detail",
            extraction_text="ABANDONED WAREHOUSE",
            attributes={
                "setting": "warehouse",
                "atmosphere": "dark, dusty, ominous",
                "time_period": "present",
                "crowd_size": "empty",
                "practical_notes": "needs lighting, dust effects"
            }
        )
    ]
)


# Example 2: Emotional Dialogue Scene
EXAMPLE_2_EMOTIONAL_SCENE = lx.data.ExampleData(
    text="""INT. HOSPITAL ROOM - DAY

JANE WILLIAMS (30s) sits beside her father's bed, holding his frail hand. Her eyes are red from crying. She wears a rumpled business suit, clearly slept in.

JANE
(voice breaking)
I'm so sorry I wasn't here sooner.

Her father, ROBERT (70s, pale), manages a weak smile.

ROBERT
You're here now. That's what matters.

Jane's phone BUZZES on the bedside table. She glances at it - "BOSS" flashing on screen - then silences it without hesitation.""",
    
    extractions=[
        lx.data.Extraction(
            extraction_class="scene_header",
            extraction_text="INT. HOSPITAL ROOM - DAY",
            attributes={
                "int_ext": "INT",
                "setting": "HOSPITAL ROOM",
                "time_of_day": "DAY"
            }
        ),
        lx.data.Extraction(
            extraction_class="character",
            extraction_text="JANE WILLIAMS (30s)",
            attributes={
                "name": "JANE WILLIAMS",
                "action": "sits beside bed, holding hand",
                "emotional_state": "grief, guilt",
                "first_appearance": "true"
            }
        ),
        lx.data.Extraction(
            extraction_class="makeup_hair",
            extraction_text="Her eyes are red from crying",
            attributes={
                "character": "JANE WILLIAMS",
                "type": "makeup",
                "description": "red, puffy eyes",
                "emotional_context": "has been crying",
                "continuity_note": "maintain throughout scene"
            }
        ),
        lx.data.Extraction(
            extraction_class="wardrobe",
            extraction_text="rumpled business suit, clearly slept in",
            attributes={
                "character": "JANE WILLIAMS",
                "description": "business suit",
                "condition": "rumpled, slept in",
                "formality": "business",
                "significance": "character_defining - rushed from work"
            }
        ),
        lx.data.Extraction(
            extraction_class="dialogue",
            extraction_text="I'm so sorry I wasn't here sooner.",
            attributes={
                "character": "JANE",
                "tone": "grief, guilt",
                "parenthetical": "voice breaking",
                "subtext": "deep regret, seeking forgiveness"
            }
        ),
        lx.data.Extraction(
            extraction_class="character",
            extraction_text="ROBERT (70s, pale)",
            attributes={
                "name": "ROBERT",
                "action": "manages weak smile",
                "emotional_state": "weak but comforting",
                "first_appearance": "true"
            }
        ),
        lx.data.Extraction(
            extraction_class="makeup_hair",
            extraction_text="pale",
            attributes={
                "character": "ROBERT",
                "type": "makeup",
                "description": "pale complexion",
                "emotional_context": "ill, dying",
                "continuity_note": "sickly appearance"
            }
        ),
        lx.data.Extraction(
            extraction_class="dialogue",
            extraction_text="You're here now. That's what matters.",
            attributes={
                "character": "ROBERT",
                "tone": "gentle, forgiving",
                "parenthetical": "none",
                "subtext": "offering comfort, absolution"
            }
        ),
        lx.data.Extraction(
            extraction_class="prop",
            extraction_text="phone",
            attributes={
                "item_name": "phone",
                "character_using": "JANE WILLIAMS",
                "importance": "character_development",
                "condition": "functional",
                "action": "buzzes, shows BOSS calling, silenced"
            }
        ),
        lx.data.Extraction(
            extraction_class="relationship",
            extraction_text="JANE WILLIAMS (30s) sits beside her father's bed",
            attributes={
                "characters": "JANE & ROBERT",
                "type": "familial",
                "dynamic": "daughter caring for dying father",
                "development": "reconciliation, forgiveness"
            }
        ),
        lx.data.Extraction(
            extraction_class="emotion",
            extraction_text="Her eyes are red from crying",
            attributes={
                "character": "JANE WILLIAMS",
                "emotion_type": "grief",
                "intensity": "intense",
                "trigger": "father's illness",
                "manifestation": "red eyes, voice breaking"
            }
        )
    ]
)


# Example 3: Action Sequence with VFX
EXAMPLE_3_ACTION_VFX = lx.data.ExampleData(
    text="""EXT. CITY STREET - DUSK

A BLACK MERCEDES speeds through the intersection, tires SCREECHING. AGENT CROSS (30s, determined) grips the wheel, his tactical vest visible under his jacket.

Suddenly, a HELICOPTER appears overhead, searchlight sweeping the street.

AGENT CROSS
(into radio)
I need backup. Now!

The car SWERVES to avoid a fruit stand. Oranges EXPLODE across the pavement. The Mercedes CRASHES through a chain-link fence and flips three times before landing on its roof.

SLOW MOTION: Cross hangs upside down, blood dripping from a gash on his forehead.""",
    
    extractions=[
        lx.data.Extraction(
            extraction_class="scene_header",
            extraction_text="EXT. CITY STREET - DUSK",
            attributes={
                "int_ext": "EXT",
                "setting": "CITY STREET",
                "time_of_day": "DUSK"
            }
        ),
        lx.data.Extraction(
            extraction_class="vehicle",
            extraction_text="BLACK MERCEDES",
            attributes={
                "type": "car",
                "description": "black Mercedes",
                "era": "modern",
                "usage": "featured",
                "condition": "pristine then damaged"
            }
        ),
        lx.data.Extraction(
            extraction_class="sound",
            extraction_text="tires SCREECHING",
            attributes={
                "type": "diegetic",
                "description": "tire screech",
                "source": "Mercedes tires",
                "importance": "atmosphere",
                "volume": "loud"
            }
        ),
        lx.data.Extraction(
            extraction_class="character",
            extraction_text="AGENT CROSS (30s, determined)",
            attributes={
                "name": "AGENT CROSS",
                "action": "grips wheel, driving",
                "emotional_state": "determined",
                "first_appearance": "true"
            }
        ),
        lx.data.Extraction(
            extraction_class="wardrobe",
            extraction_text="tactical vest visible under his jacket",
            attributes={
                "character": "AGENT CROSS",
                "description": "tactical vest under jacket",
                "condition": "functional",
                "formality": "tactical",
                "significance": "character_defining - law enforcement"
            }
        ),
        lx.data.Extraction(
            extraction_class="vehicle",
            extraction_text="HELICOPTER",
            attributes={
                "type": "helicopter",
                "description": "helicopter with searchlight",
                "era": "modern",
                "usage": "featured",
                "condition": "operational"
            }
        ),
        lx.data.Extraction(
            extraction_class="special_fx",
            extraction_text="searchlight sweeping the street",
            attributes={
                "type": "practical",
                "description": "helicopter searchlight",
                "complexity": "moderate",
                "safety_concern": "false"
            }
        ),
        lx.data.Extraction(
            extraction_class="dialogue",
            extraction_text="I need backup. Now!",
            attributes={
                "character": "AGENT CROSS",
                "tone": "urgent, desperate",
                "parenthetical": "into radio",
                "subtext": "in serious danger"
            }
        ),
        lx.data.Extraction(
            extraction_class="prop",
            extraction_text="radio",
            attributes={
                "item_name": "radio",
                "character_using": "AGENT CROSS",
                "importance": "plot_critical",
                "condition": "functional",
                "action": "speaking into it"
            }
        ),
        lx.data.Extraction(
            extraction_class="special_fx",
            extraction_text="Oranges EXPLODE across the pavement",
            attributes={
                "type": "practical",
                "description": "fruit stand collision, oranges scatter",
                "complexity": "simple",
                "safety_concern": "false"
            }
        ),
        lx.data.Extraction(
            extraction_class="special_fx",
            extraction_text="Mercedes CRASHES through a chain-link fence and flips three times",
            attributes={
                "type": "stunt",
                "description": "car crash and flip",
                "complexity": "complex",
                "safety_concern": "true"
            }
        ),
        lx.data.Extraction(
            extraction_class="makeup_hair",
            extraction_text="blood dripping from a gash on his forehead",
            attributes={
                "character": "AGENT CROSS",
                "type": "injury",
                "description": "bleeding forehead gash",
                "emotional_context": "crash injury",
                "continuity_note": "maintain throughout remaining scenes"
            }
        ),
        lx.data.Extraction(
            extraction_class="transition",
            extraction_text="SLOW MOTION:",
            attributes={
                "type": "technical",
                "timing": "gradual",
                "time_jump": "none",
                "purpose": "emphasize impact moment"
            }
        )
    ]
)


# Example 4: Period Drama Scene
EXAMPLE_4_PERIOD_DRAMA = lx.data.ExampleData(
    text="""INT. VICTORIAN DRAWING ROOM - EVENING

LADY CATHERINE (50s, imperious) sits in a high-backed chair, her elaborate gown rustling as she adjusts her position. A SERVANT in period livery pours tea from a silver service.

LADY CATHERINE
(coldly)
Tell me, Miss Bennett, what are your
intentions regarding my nephew?

ELIZABETH BENNETT (20s, defiant) stands by the fireplace, her simple muslin dress a stark contrast to the opulent surroundings.

ELIZABETH
My intentions, madam, are my own concern.""",
    
    extractions=[
        lx.data.Extraction(
            extraction_class="scene_header",
            extraction_text="INT. VICTORIAN DRAWING ROOM - EVENING",
            attributes={
                "int_ext": "INT",
                "setting": "VICTORIAN DRAWING ROOM",
                "time_of_day": "EVENING"
            }
        ),
        lx.data.Extraction(
            extraction_class="character",
            extraction_text="LADY CATHERINE (50s, imperious)",
            attributes={
                "name": "LADY CATHERINE",
                "action": "sits, adjusts position",
                "emotional_state": "imperious, commanding",
                "first_appearance": "true"
            }
        ),
        lx.data.Extraction(
            extraction_class="wardrobe",
            extraction_text="elaborate gown",
            attributes={
                "character": "LADY CATHERINE",
                "description": "elaborate Victorian gown",
                "condition": "pristine",
                "formality": "formal",
                "significance": "character_defining - wealth, status"
            }
        ),
        lx.data.Extraction(
            extraction_class="prop",
            extraction_text="high-backed chair",
            attributes={
                "item_name": "high-backed chair",
                "character_using": "LADY CATHERINE",
                "importance": "character_defining",
                "condition": "ornate",
                "era": "Victorian",
                "action": "sitting in it"
            }
        ),
        lx.data.Extraction(
            extraction_class="character",
            extraction_text="SERVANT in period livery",
            attributes={
                "name": "SERVANT",
                "action": "pours tea",
                "emotional_state": "neutral, dutiful",
                "first_appearance": "true"
            }
        ),
        lx.data.Extraction(
            extraction_class="wardrobe",
            extraction_text="period livery",
            attributes={
                "character": "SERVANT",
                "description": "Victorian servant livery",
                "condition": "pristine",
                "formality": "formal",
                "significance": "atmospheric - period accuracy"
            }
        ),
        lx.data.Extraction(
            extraction_class="prop",
            extraction_text="silver service",
            attributes={
                "item_name": "silver tea service",
                "character_using": "SERVANT",
                "importance": "atmospheric",
                "condition": "polished",
                "era": "Victorian",
                "action": "pouring tea from it"
            }
        ),
        lx.data.Extraction(
            extraction_class="dialogue",
            extraction_text="Tell me, Miss Bennett, what are your intentions regarding my nephew?",
            attributes={
                "character": "LADY CATHERINE",
                "tone": "cold, interrogative",
                "parenthetical": "coldly",
                "subtext": "threatening, asserting dominance"
            }
        ),
        lx.data.Extraction(
            extraction_class="character",
            extraction_text="ELIZABETH BENNETT (20s, defiant)",
            attributes={
                "name": "ELIZABETH BENNETT",
                "action": "stands by fireplace",
                "emotional_state": "defiant",
                "first_appearance": "true"
            }
        ),
        lx.data.Extraction(
            extraction_class="wardrobe",
            extraction_text="simple muslin dress",
            attributes={
                "character": "ELIZABETH BENNETT",
                "description": "simple muslin dress",
                "condition": "modest",
                "formality": "casual",
                "significance": "character_defining - class contrast"
            }
        ),
        lx.data.Extraction(
            extraction_class="location_detail",
            extraction_text="VICTORIAN DRAWING ROOM",
            attributes={
                "setting": "drawing room",
                "atmosphere": "opulent, formal, intimidating",
                "time_period": "Victorian era",
                "crowd_size": "sparse",
                "practical_notes": "period-accurate furniture, decor"
            }
        ),
        lx.data.Extraction(
            extraction_class="dialogue",
            extraction_text="My intentions, madam, are my own concern.",
            attributes={
                "character": "ELIZABETH",
                "tone": "defiant, firm",
                "parenthetical": "none",
                "subtext": "refusing to be intimidated"
            }
        ),
        lx.data.Extraction(
            extraction_class="relationship",
            extraction_text="LADY CATHERINE (50s, imperious) sits in a high-backed chair",
            attributes={
                "characters": "LADY CATHERINE & ELIZABETH BENNETT",
                "type": "adversarial",
                "dynamic": "power struggle, class conflict",
                "development": "confrontation building"
            }
        )
    ]
)


# Example 5: Horror Scene
EXAMPLE_5_HORROR = lx.data.ExampleData(
    text="""INT. BASEMENT - NIGHT

The single LIGHTBULB flickers, casting dancing shadows on the concrete walls. MIKE (20s, terrified) descends the creaking wooden stairs, his breath visible in the cold air.

A CHILD'S MUSIC BOX plays somewhere in the darkness - a haunting, off-key melody.

MIKE
(trembling)
Hello?

The music stops abruptly. Silence. Then, a WHISPER - too quiet to make out words - seems to come from everywhere at once.

Mike's flashlight dies. Complete darkness.""",
    
    extractions=[
        lx.data.Extraction(
            extraction_class="scene_header",
            extraction_text="INT. BASEMENT - NIGHT",
            attributes={
                "int_ext": "INT",
                "setting": "BASEMENT",
                "time_of_day": "NIGHT"
            }
        ),
        lx.data.Extraction(
            extraction_class="prop",
            extraction_text="single LIGHTBULB",
            attributes={
                "item_name": "lightbulb",
                "character_using": "none",
                "importance": "atmosphere",
                "condition": "flickering",
                "action": "casting dancing shadows"
            }
        ),
        lx.data.Extraction(
            extraction_class="special_fx",
            extraction_text="flickering, casting dancing shadows",
            attributes={
                "type": "practical",
                "description": "flickering light effect",
                "complexity": "simple",
                "safety_concern": "false"
            }
        ),
        lx.data.Extraction(
            extraction_class="character",
            extraction_text="MIKE (20s, terrified)",
            attributes={
                "name": "MIKE",
                "action": "descends stairs",
                "emotional_state": "terrified",
                "first_appearance": "true"
            }
        ),
        lx.data.Extraction(
            extraction_class="sound",
            extraction_text="creaking wooden stairs",
            attributes={
                "type": "diegetic",
                "description": "stairs creaking",
                "source": "wooden stairs",
                "importance": "atmosphere",
                "volume": "moderate"
            }
        ),
        lx.data.Extraction(
            extraction_class="special_fx",
            extraction_text="breath visible in the cold air",
            attributes={
                "type": "practical",
                "description": "visible breath vapor",
                "complexity": "simple",
                "safety_concern": "false"
            }
        ),
        lx.data.Extraction(
            extraction_class="prop",
            extraction_text="CHILD'S MUSIC BOX",
            attributes={
                "item_name": "child's music box",
                "character_using": "unknown",
                "importance": "plot_critical",
                "condition": "functional",
                "action": "playing haunting melody"
            }
        ),
        lx.data.Extraction(
            extraction_class="sound",
            extraction_text="haunting, off-key melody",
            attributes={
                "type": "diegetic",
                "description": "music box melody",
                "source": "child's music box",
                "importance": "plot_critical",
                "volume": "moderate"
            }
        ),
        lx.data.Extraction(
            extraction_class="dialogue",
            extraction_text="Hello?",
            attributes={
                "character": "MIKE",
                "tone": "fearful, questioning",
                "parenthetical": "trembling",
                "subtext": "seeking reassurance, terrified"
            }
        ),
        lx.data.Extraction(
            extraction_class="sound",
            extraction_text="WHISPER - too quiet to make out words",
            attributes={
                "type": "diegetic",
                "description": "unintelligible whisper",
                "source": "unknown, omnidirectional",
                "importance": "plot_critical",
                "volume": "subtle"
            }
        ),
        lx.data.Extraction(
            extraction_class="prop",
            extraction_text="flashlight",
            attributes={
                "item_name": "flashlight",
                "character_using": "MIKE",
                "importance": "plot_critical",
                "condition": "dies/fails",
                "action": "providing light then dying"
            }
        ),
        lx.data.Extraction(
            extraction_class="location_detail",
            extraction_text="BASEMENT",
            attributes={
                "setting": "basement",
                "atmosphere": "dark, cold, ominous, claustrophobic",
                "time_period": "present",
                "crowd_size": "empty",
                "practical_notes": "needs fog/vapor effect, flickering lights"
            }
        ),
        lx.data.Extraction(
            extraction_class="emotion",
            extraction_text="MIKE (20s, terrified)",
            attributes={
                "character": "MIKE",
                "emotion_type": "terror",
                "intensity": "intense",
                "trigger": "supernatural presence",
                "manifestation": "trembling, visible breath, fear in voice"
            }
        )
    ]
)


# Collect all examples
SCREENPLAY_EXAMPLES = [
    EXAMPLE_1_ACTION_SCENE,
    EXAMPLE_2_EMOTIONAL_SCENE,
    EXAMPLE_3_ACTION_VFX,
    EXAMPLE_4_PERIOD_DRAMA,
    EXAMPLE_5_HORROR
]


def get_examples() -> list:
    """Return all screenplay extraction examples."""
    return SCREENPLAY_EXAMPLES


def get_example_by_type(scene_type: str) -> lx.data.ExampleData:
    """Get a specific example by scene type."""
    examples_map = {
        "action": EXAMPLE_1_ACTION_SCENE,
        "emotional": EXAMPLE_2_EMOTIONAL_SCENE,
        "vfx": EXAMPLE_3_ACTION_VFX,
        "period": EXAMPLE_4_PERIOD_DRAMA,
        "horror": EXAMPLE_5_HORROR
    }
    return examples_map.get(scene_type.lower(), EXAMPLE_1_ACTION_SCENE)
