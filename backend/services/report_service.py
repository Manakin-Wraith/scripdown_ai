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
from utils.scene_calculations import format_eighths, calculate_total_script_length


# ============================================
# Report Configuration Presets
# ============================================

PRESET_FULL_BREAKDOWN = {
    "report_type": "full_breakdown",
    "include_categories": ["all"],
    "exclude_categories": [],
    "include_metadata": {"all": True},
    "include_descriptions": {"all": True},
    "include_summary": True,
    "show_cross_references": False
}

PRESET_WARDROBE = {
    "report_type": "wardrobe",
    "include_categories": ["characters", "wardrobe"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "writer_name": True,
        "production_company": True
    },
    "include_descriptions": {
        "description": True
    },
    "include_summary": True,
    "show_cross_references": True,
    "group_by": "character"
}

PRESET_PROPS = {
    "report_type": "props",
    "include_categories": ["characters", "props"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "production_company": True
    },
    "include_descriptions": {
        "description": True
    },
    "include_summary": True,
    "show_cross_references": True
}

PRESET_MAKEUP = {
    "report_type": "makeup",
    "include_categories": ["characters", "makeup"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "production_company": True
    },
    "include_descriptions": {
        "description": True,
        "emotional_tone": True
    },
    "include_summary": True,
    "show_cross_references": True,
    "group_by": "character"
}

PRESET_SFX = {
    "report_type": "sfx",
    "include_categories": ["special_effects"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "production_company": True
    },
    "include_descriptions": {
        "description": True,
        "technical_notes": True
    },
    "include_summary": True,
    "show_cross_references": True
}

PRESET_STUNTS = {
    "report_type": "stunts",
    "include_categories": ["characters", "stunts"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "production_company": True
    },
    "include_descriptions": {
        "description": True,
        "action_description": True,
        "technical_notes": True
    },
    "include_summary": True,
    "show_cross_references": True
}

PRESET_VEHICLES = {
    "report_type": "vehicles",
    "include_categories": ["vehicles", "characters"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "production_company": True
    },
    "include_descriptions": {
        "description": True
    },
    "include_summary": True,
    "show_cross_references": True
}

PRESET_ANIMALS = {
    "report_type": "animals",
    "include_categories": ["animals", "characters"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "production_company": True
    },
    "include_descriptions": {
        "description": True
    },
    "include_summary": True,
    "show_cross_references": True
}

PRESET_EXTRAS = {
    "report_type": "extras",
    "include_categories": ["extras", "locations"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "production_company": True
    },
    "include_descriptions": {
        "description": True,
        "atmosphere": True
    },
    "include_summary": True,
    "show_cross_references": True
}

PRESET_DIALOGUE = {
    "report_type": "dialogue",
    "include_categories": ["characters"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "writer_name": True
    },
    "include_descriptions": {"all": True},
    "include_summary": True,
    "show_cross_references": False,
    "group_by": "character"
}

PRESET_SOUND_CUES = {
    "report_type": "sound_cues",
    "include_categories": ["sound"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "production_company": True
    },
    "include_descriptions": {
        "description": True,
        "technical_notes": True
    },
    "include_summary": True,
    "show_cross_references": True
}

PRESET_EMOTIONAL_ARC = {
    "report_type": "emotional_arc",
    "include_categories": ["characters"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "writer_name": True
    },
    "include_descriptions": {"all": True},
    "include_summary": True,
    "show_cross_references": False
}

PRESET_CONTINUITY = {
    "report_type": "continuity",
    "include_categories": ["all"],
    "exclude_categories": [],
    "include_metadata": {"all": True},
    "include_descriptions": {"all": True},
    "include_summary": True,
    "show_cross_references": True
}


class ReportConfig:
    """Report configuration with validation and defaults."""
    
    VALID_REPORT_TYPES = [
        "full_breakdown", "scene_breakdown", "wardrobe", "props",
        "makeup", "sfx", "special_effects", "stunts", "vehicles", 
        "animals", "extras", "custom", "day_out_of_days", 
        "location", "one_liner", "dialogue", "sound_cues",
        "emotional_arc", "continuity"
    ]
    
    VALID_CATEGORIES = [
        "characters", "props", "wardrobe", "makeup", "special_effects",
        "stunts", "vehicles", "animals", "extras", "locations", "sound"
    ]
    
    def __init__(self, config_dict: Optional[Dict] = None):
        """Initialize configuration with optional custom config."""
        self.config = self._merge_with_defaults(config_dict or {})
        self._validate()
    
    def _merge_with_defaults(self, config: Dict) -> Dict:
        """Merge user config with defaults."""
        defaults = {
            "report_type": "full_breakdown",
            "include_categories": ["all"],
            "exclude_categories": [],
            "include_metadata": {"all": True},
            "include_descriptions": {"all": True},
            "include_summary": True,
            "show_cross_references": False,
            "group_by": None,
            "sort_by": "scene_number",
            "filter": {
                "scene_numbers": [],
                "characters": [],
                "locations": []
            },
            "department_options": {},
            "visual_options": {
                "color_code_int_ext": False,
                "color_code_day_night": False,
                "show_page_numbers": True,
                "compact_mode": False
            }
        }
        
        # Deep merge for nested dicts
        merged = defaults.copy()
        for key, value in config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        
        return merged
    
    def _validate(self):
        """Validate configuration values."""
        if self.config["report_type"] not in self.VALID_REPORT_TYPES:
            raise ValueError(f"Invalid report_type: {self.config['report_type']}")
        
        # Validate categories
        for category in self.config["include_categories"]:
            if category != "all" and category not in self.VALID_CATEGORIES:
                raise ValueError(f"Invalid category: {category}")
        
        for category in self.config["exclude_categories"]:
            if category not in self.VALID_CATEGORIES:
                raise ValueError(f"Invalid exclude category: {category}")
    
    def should_include_category(self, category: str) -> bool:
        """Check if a category should be included."""
        if "all" in self.config["include_categories"]:
            return category not in self.config["exclude_categories"]
        return category in self.config["include_categories"]
    
    def should_include_metadata(self, field: str) -> bool:
        """Check if a metadata field should be included."""
        metadata = self.config["include_metadata"]
        if metadata.get("all"):
            return True
        return metadata.get(field, False)
    
    def should_include_description(self, field: str) -> bool:
        """Check if a description field should be included."""
        descriptions = self.config["include_descriptions"]
        if descriptions.get("all"):
            return True
        return descriptions.get(field, False)
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary for storage."""
        return self.config.copy()
    
    @staticmethod
    def from_preset(preset_name: str) -> 'ReportConfig':
        """Create config from preset name."""
        presets = {
            "full_breakdown": PRESET_FULL_BREAKDOWN,
            "wardrobe": PRESET_WARDROBE,
            "props": PRESET_PROPS,
            "makeup": PRESET_MAKEUP,
            "sfx": PRESET_SFX,
            "stunts": PRESET_STUNTS,
            "vehicles": PRESET_VEHICLES,
            "animals": PRESET_ANIMALS,
            "extras": PRESET_EXTRAS,
            "dialogue": PRESET_DIALOGUE,
            "sound_cues": PRESET_SOUND_CUES,
            "emotional_arc": PRESET_EMOTIONAL_ARC,
            "continuity": PRESET_CONTINUITY
        }
        
        if preset_name not in presets:
            raise ValueError(f"Unknown preset: {preset_name}")
        
        return ReportConfig(presets[preset_name])
    
    @staticmethod
    def get_available_presets() -> List[Dict[str, str]]:
        """Get list of available presets with metadata."""
        return [
            {"name": "full_breakdown", "title": "Full Breakdown", "description": "Complete script breakdown with all categories"},
            {"name": "wardrobe", "title": "Wardrobe Department", "description": "Wardrobe items grouped by character"},
            {"name": "props", "title": "Props Department", "description": "Props list with scene cross-references"},
            {"name": "makeup", "title": "Makeup & Hair", "description": "Makeup requirements by character"},
            {"name": "sfx", "title": "Special Effects", "description": "VFX and practical effects breakdown"},
            {"name": "stunts", "title": "Stunts Department", "description": "Stunt requirements with safety notes"},
            {"name": "vehicles", "title": "Vehicles & Transportation", "description": "Vehicle requirements by scene"},
            {"name": "animals", "title": "Animals & Wranglers", "description": "Animal requirements by scene"},
            {"name": "extras", "title": "Extras & Background", "description": "Background actor requirements"},
            {"name": "dialogue", "title": "Dialogue & Tone", "description": "Dialogue lines with tone and character analysis"},
            {"name": "sound_cues", "title": "Sound Design Cue Sheet", "description": "Sound effects and audio cues by scene"},
            {"name": "emotional_arc", "title": "Emotional Arc", "description": "Emotional progression across scenes"},
            {"name": "continuity", "title": "Continuity Report", "description": "Props, wardrobe, and makeup continuity tracking"}
        ]


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
        },
        'dialogue': {
            'name': 'Dialogue & Tone Report',
            'description': 'Dialogue lines with tone analysis grouped by character'
        },
        'sound_cues': {
            'name': 'Sound Design Cue Sheet',
            'description': 'Sound effects and audio cues by scene'
        },
        'emotional_arc': {
            'name': 'Emotional Arc Report',
            'description': 'Emotional progression and intensity across scenes'
        },
        'continuity': {
            'name': 'Continuity Report',
            'description': 'Props, wardrobe, and makeup continuity tracking across scenes'
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
        Collects ALL breakdown categories without truncation.
        """
        # Get script metadata
        script = self.db.get_script(script_id)
        if not script:
            raise ValueError(f"Script not found: {script_id}")
        
        # Get all scenes
        scenes = self.db.get_scenes(script_id)
        
        # Aggregate data - NO TRUNCATION
        characters = defaultdict(lambda: {'count': 0, 'scenes': [], 'eighths': 0})
        locations = defaultdict(lambda: {'count': 0, 'scenes': [], 'int_ext': set(), 'time_of_day': set()})
        props = defaultdict(lambda: {'count': 0, 'scenes': []})
        wardrobe_items = defaultdict(lambda: {'count': 0, 'scenes': [], 'characters': set()})
        makeup_items = defaultdict(lambda: {'count': 0, 'scenes': [], 'characters': set()})
        special_effects = defaultdict(lambda: {'count': 0, 'scenes': [], 'type': set()})
        vehicles = defaultdict(lambda: {'count': 0, 'scenes': []})
        animals = defaultdict(lambda: {'count': 0, 'scenes': []})
        extras = defaultdict(lambda: {'count': 0, 'scenes': []})
        stunts = defaultdict(lambda: {'count': 0, 'scenes': []})
        
        total_eighths = 0
        analyzed_scenes = 0
        
        for scene in scenes:
            scene_num = scene.get('scene_number', '')
            eighths = scene.get('page_length_eighths', 8)  # Default to 1 page
            total_eighths += eighths
            
            if scene.get('analysis_status') == 'complete':
                analyzed_scenes += 1
            
            # Characters
            for char in (scene.get('characters') or []):
                char_name = char if isinstance(char, str) else char.get('name', str(char))
                characters[char_name]['count'] += 1
                characters[char_name]['scenes'].append(scene_num)
                characters[char_name]['eighths'] += eighths
            
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
                char_ref = item.get('character', '') if isinstance(item, dict) else ''
                wardrobe_items[item_name]['count'] += 1
                wardrobe_items[item_name]['scenes'].append(scene_num)
                if char_ref:
                    wardrobe_items[item_name]['characters'].add(char_ref)
            
            # Makeup & Hair
            for item in (scene.get('makeup') or []):
                item_name = item if isinstance(item, str) else item.get('requirements', str(item))
                if isinstance(item_name, list):
                    item_name = ', '.join(item_name)
                char_ref = item.get('character', '') if isinstance(item, dict) else ''
                makeup_items[item_name]['count'] += 1
                makeup_items[item_name]['scenes'].append(scene_num)
                if char_ref:
                    makeup_items[item_name]['characters'].add(char_ref)
            
            # Special Effects (SFX/VFX)
            for item in (scene.get('special_effects') or []):
                item_name = item if isinstance(item, str) else item.get('effect', str(item))
                item_type = item.get('type', 'unknown') if isinstance(item, dict) else 'unknown'
                special_effects[item_name]['count'] += 1
                special_effects[item_name]['scenes'].append(scene_num)
                special_effects[item_name]['type'].add(item_type)
            
            # Vehicles
            for item in (scene.get('vehicles') or []):
                item_name = item if isinstance(item, str) else item.get('type', str(item))
                vehicles[item_name]['count'] += 1
                vehicles[item_name]['scenes'].append(scene_num)
            
            # Animals
            for item in (scene.get('animals') or []):
                item_name = item if isinstance(item, str) else item.get('type', str(item))
                animals[item_name]['count'] += 1
                animals[item_name]['scenes'].append(scene_num)
            
            # Extras
            for item in (scene.get('extras') or []):
                item_name = item if isinstance(item, str) else item.get('type', str(item))
                extras[item_name]['count'] += 1
                extras[item_name]['scenes'].append(scene_num)
            
            # Stunts
            for item in (scene.get('stunts') or []):
                item_name = item if isinstance(item, str) else item.get('type', str(item))
                stunts[item_name]['count'] += 1
                stunts[item_name]['scenes'].append(scene_num)
        
        # Calculate total pages from eighths
        total_pages = total_eighths / 8
        
        result = {
            'script': {
                'id': script_id,
                'title': script.get('title', 'Untitled'),
                'writer': script.get('writer_name', 'Unknown'),
                'draft': script.get('draft_version', ''),
                'total_pages': script.get('total_pages', total_pages),
                'production_company': script.get('production_company', ''),
                'contact_email': script.get('contact_email', ''),
                'contact_phone': script.get('contact_phone', ''),
                'copyright_info': script.get('copyright_info', ''),
                'additional_credits': script.get('additional_credits', '')
            },
            'summary': {
                'total_scenes': len(scenes),
                'analyzed_scenes': analyzed_scenes,
                'total_characters': len(characters),
                'total_locations': len(locations),
                'total_props': len(props),
                'total_wardrobe': len(wardrobe_items),
                'total_makeup': len(makeup_items),
                'total_special_effects': len(special_effects),
                'total_vehicles': len(vehicles),
                'total_animals': len(animals),
                'total_extras': len(extras),
                'total_stunts': len(stunts),
                'total_eighths': total_eighths,
                'total_pages': total_pages
            },
            'scenes': scenes,
            'characters': dict(characters),
            'locations': {k: {**v, 'int_ext': list(v['int_ext']), 'time_of_day': list(v['time_of_day'])} 
                         for k, v in locations.items()},
            'props': dict(props),
            'wardrobe': {k: {**v, 'characters': list(v['characters'])} for k, v in wardrobe_items.items()},
            'makeup': {k: {**v, 'characters': list(v['characters'])} for k, v in makeup_items.items()},
            'special_effects': {k: {**v, 'type': list(v['type'])} for k, v in special_effects.items()},
            'vehicles': dict(vehicles),
            'animals': dict(animals),
            'extras': dict(extras),
            'stunts': dict(stunts),
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Enrich with extraction_metadata (rich attributes + new categories)
        result = self._enrich_with_extraction_metadata(script_id, scenes, result)
        
        return result
    
    def _enrich_with_extraction_metadata(
        self,
        script_id: str,
        scenes: List[Dict],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Augment aggregated report data with rich attributes from extraction_metadata.
        Adds detailed attributes (tone, condition, importance) to existing categories
        and populates new enrichment categories (dialogue, emotions, relationships, sound).
        """
        try:
            response = self.db.client.table('extraction_metadata')\
                .select('id, extraction_class, extraction_text, attributes, confidence, scene_id')\
                .eq('script_id', script_id)\
                .order('text_start')\
                .execute()
            
            extractions = response.data if response.data else []
            if not extractions:
                return data
            
            # Build scene_id -> scene_number lookup
            scene_num_map = {}
            for s in scenes:
                sid = s.get('id') or s.get('scene_id')
                if sid:
                    scene_num_map[sid] = s.get('scene_number', '')
            
            # Enrich existing categories with rich attributes
            rich_characters = defaultdict(lambda: {'attributes': [], 'avg_confidence': 0})
            rich_props = defaultdict(lambda: {'attributes': [], 'avg_confidence': 0})
            rich_wardrobe = defaultdict(lambda: {'attributes': [], 'avg_confidence': 0})
            
            # New enrichment categories
            dialogue_items = []
            emotions = defaultdict(lambda: {'count': 0, 'scenes': [], 'intensity': []})
            relationships = []
            sound_cues = defaultdict(lambda: {'count': 0, 'scenes': [], 'type': set()})
            
            for ext in extractions:
                cls = ext.get('extraction_class', '')
                text = ext.get('extraction_text', '')
                attrs = ext.get('attributes', {}) or {}
                confidence = ext.get('confidence', 1.0)
                scene_id = ext.get('scene_id')
                scene_num = scene_num_map.get(scene_id, '')
                
                if cls == 'character' and text:
                    char_name = attrs.get('name', text)
                    rich_characters[char_name]['attributes'].append(attrs)
                    rich_characters[char_name]['avg_confidence'] = confidence
                
                elif cls == 'prop' and text:
                    prop_name = attrs.get('item_name', text)
                    rich_props[prop_name]['attributes'].append(attrs)
                    rich_props[prop_name]['avg_confidence'] = confidence
                
                elif cls == 'wardrobe' and text:
                    rich_wardrobe[text]['attributes'].append(attrs)
                    rich_wardrobe[text]['avg_confidence'] = confidence
                
                elif cls == 'dialogue' and text:
                    dialogue_items.append({
                        'text': text[:200],
                        'character': attrs.get('character', ''),
                        'tone': attrs.get('tone', ''),
                        'scene': scene_num,
                        'confidence': confidence
                    })
                
                elif cls == 'emotion' and text:
                    emotions[text]['count'] += 1
                    if scene_num and scene_num not in emotions[text]['scenes']:
                        emotions[text]['scenes'].append(scene_num)
                    if attrs.get('intensity'):
                        emotions[text]['intensity'].append(attrs['intensity'])
                
                elif cls == 'relationship' and text:
                    relationships.append({
                        'text': text,
                        'characters': [attrs.get('character_a', ''), attrs.get('character_b', '')],
                        'dynamic': attrs.get('dynamic', ''),
                        'scene': scene_num
                    })
                
                elif cls == 'sound' and text:
                    sound_cues[text]['count'] += 1
                    if scene_num and scene_num not in sound_cues[text]['scenes']:
                        sound_cues[text]['scenes'].append(scene_num)
                    if attrs.get('type'):
                        sound_cues[text]['type'].add(attrs['type'])
            
            # Merge rich attributes into existing character data
            for char_name, rich in rich_characters.items():
                if char_name in data['characters']:
                    data['characters'][char_name]['rich_attributes'] = rich['attributes']
                    data['characters'][char_name]['avg_confidence'] = rich['avg_confidence']
            
            for prop_name, rich in rich_props.items():
                if prop_name in data['props']:
                    data['props'][prop_name]['rich_attributes'] = rich['attributes']
                    data['props'][prop_name]['avg_confidence'] = rich['avg_confidence']
            
            for item_name, rich in rich_wardrobe.items():
                if item_name in data['wardrobe']:
                    data['wardrobe'][item_name]['rich_attributes'] = rich['attributes']
                    data['wardrobe'][item_name]['avg_confidence'] = rich['avg_confidence']
            
            # Add new enrichment sections
            data['enrichment'] = {
                'dialogue': dialogue_items[:100],
                'emotions': dict(emotions),
                'relationships': relationships,
                'sound_cues': {k: {**v, 'type': list(v['type'])} for k, v in sound_cues.items()},
                'total_dialogue_lines': len(dialogue_items),
                'total_emotions': len(emotions),
                'total_relationships': len(relationships),
                'total_sound_cues': len(sound_cues)
            }
            
            # Update summary counts
            data['summary']['total_dialogue_lines'] = len(dialogue_items)
            data['summary']['total_emotions'] = len(emotions)
            data['summary']['total_relationships'] = len(relationships)
            data['summary']['total_sound_cues'] = len(sound_cues)
            data['summary']['has_rich_data'] = True
            
        except Exception as e:
            print(f"[ReportService] Enrichment from extraction_metadata failed: {str(e)}")
            # Non-fatal: reports still work with flat scene data
            data['summary']['has_rich_data'] = False
        
        return data
    
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
        """Render report data as HTML with enhanced metadata."""
        report_type = report.get('report_type')
        data = report.get('data_snapshot', {})
        script = data.get('script', {})
        
        # Build metadata sections
        metadata_items = [
            f"<p><strong>Script:</strong> {script.get('title', 'Untitled')}</p>",
            f"<p><strong>Writer:</strong> {script.get('writer', 'Unknown')}</p>"
        ]
        
        if script.get('draft'):
            metadata_items.append(f"<p><strong>Draft:</strong> {script.get('draft')}</p>")
        
        if script.get('production_company'):
            metadata_items.append(f"<p><strong>Production:</strong> {script.get('production_company')}</p>")
        
        if script.get('total_pages'):
            metadata_items.append(f"<p><strong>Pages:</strong> {script.get('total_pages')}</p>")
        
        if script.get('contact_email'):
            metadata_items.append(f"<p><strong>Contact:</strong> {script.get('contact_email')}</p>")
        
        if script.get('contact_phone'):
            metadata_items.append(f"<p><strong>Phone:</strong> {script.get('contact_phone')}</p>")
        
        if script.get('copyright_info'):
            metadata_items.append(f"<p><strong>Copyright:</strong> {script.get('copyright_info')}</p>")
        
        if script.get('additional_credits'):
            metadata_items.append(f"<p><strong>Credits:</strong> {script.get('additional_credits')}</p>")
        
        metadata_items.append(f"<p><strong>Generated:</strong> {report.get('generated_at', '')[:10]}</p>")
        
        # Common header with enhanced metadata
        header = f"""
        <div class="report-header">
            <h1>{report.get('title', 'Script Report')}</h1>
            <div class="script-info">
                {''.join(metadata_items)}
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
        # Department-specific reports
        elif report_type == 'wardrobe':
            body = self._render_wardrobe_department(data)
        elif report_type == 'makeup':
            body = self._render_makeup_department(data)
        elif report_type == 'sfx' or report_type == 'special_effects':
            body = self._render_sfx_department(data)
        elif report_type == 'stunts':
            body = self._render_stunts_department(data)
        elif report_type == 'vehicles':
            body = self._render_vehicles_department(data)
        elif report_type == 'animals':
            body = self._render_animals_department(data)
        elif report_type == 'extras':
            body = self._render_extras_department(data)
        # Enrichment-based reports (langextract)
        elif report_type == 'dialogue':
            body = self._render_dialogue_report(data)
        elif report_type == 'sound_cues':
            body = self._render_sound_cues_report(data)
        elif report_type == 'emotional_arc':
            body = self._render_emotional_arc_report(data)
        elif report_type == 'continuity':
            body = self._render_continuity_report(data)
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
        """Render scene breakdown HTML with complete data (no truncation)."""
        scenes = data.get('scenes', [])
        rows = []
        
        for scene in scenes:
            # Helper function to format arrays
            def format_list(items, key=None):
                if not items:
                    return '—'
                if isinstance(items, list):
                    if key and isinstance(items[0], dict):
                        return ', '.join([item.get(key, str(item)) for item in items])
                    return ', '.join([str(item) if isinstance(item, str) else item.get('name', str(item)) for item in items])
                return str(items)
            
            # Get all breakdown data - NO TRUNCATION
            chars = format_list(scene.get('characters'))
            props = format_list(scene.get('props'))
            wardrobe = format_list(scene.get('wardrobe'))
            makeup = format_list(scene.get('makeup'))
            sfx = format_list(scene.get('special_effects'))
            vehicles = format_list(scene.get('vehicles'))
            animals = format_list(scene.get('animals'))
            extras = format_list(scene.get('extras'))
            stunts = format_list(scene.get('stunts'))
            
            # Scene description and notes
            description = scene.get('description', '') or scene.get('action_description', '')
            emotional_tone = scene.get('emotional_tone', '')
            technical_notes = scene.get('technical_notes', '')
            
            # Scene length in eighths
            eighths = scene.get('page_length_eighths', 8)
            length_display = format_eighths(eighths)
            
            rows.append(f"""
            <tr>
                <td class="scene-num"><strong>{scene.get('scene_number', '')}</strong></td>
                <td class="int-ext">{scene.get('int_ext', '')}</td>
                <td class="setting"><strong>{scene.get('setting', '')}</strong></td>
                <td class="time">{scene.get('time_of_day', '')}</td>
                <td class="length-cell">{length_display}</td>
            </tr>
            <tr class="breakdown-details">
                <td colspan="5">
                    <div class="breakdown-grid">
                        {f'<div class="breakdown-item"><span class="label">Description:</span> <span class="value">{description[:200]}...</span></div>' if description and len(description) > 200 else f'<div class="breakdown-item"><span class="label">Description:</span> <span class="value">{description}</span></div>' if description else ''}
                        {f'<div class="breakdown-item"><span class="label">Tone:</span> <span class="value">{emotional_tone}</span></div>' if emotional_tone else ''}
                        <div class="breakdown-item"><span class="label">Characters:</span> <span class="value">{chars}</span></div>
                        <div class="breakdown-item"><span class="label">Props:</span> <span class="value">{props}</span></div>
                        {f'<div class="breakdown-item"><span class="label">Wardrobe:</span> <span class="value">{wardrobe}</span></div>' if wardrobe != '—' else ''}
                        {f'<div class="breakdown-item"><span class="label">Makeup/Hair:</span> <span class="value">{makeup}</span></div>' if makeup != '—' else ''}
                        {f'<div class="breakdown-item"><span class="label">Special FX:</span> <span class="value">{sfx}</span></div>' if sfx != '—' else ''}
                        {f'<div class="breakdown-item"><span class="label">Vehicles:</span> <span class="value">{vehicles}</span></div>' if vehicles != '—' else ''}
                        {f'<div class="breakdown-item"><span class="label">Animals:</span> <span class="value">{animals}</span></div>' if animals != '—' else ''}
                        {f'<div class="breakdown-item"><span class="label">Extras:</span> <span class="value">{extras}</span></div>' if extras != '—' else ''}
                        {f'<div class="breakdown-item"><span class="label">Stunts:</span> <span class="value">{stunts}</span></div>' if stunts != '—' else ''}
                        {f'<div class="breakdown-item"><span class="label">Technical:</span> <span class="value">{technical_notes}</span></div>' if technical_notes else ''}
                    </div>
                </td>
            </tr>
            """)
        
        return f"""
        <h2>Scene Breakdown</h2>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Scene</th>
                    <th>I/E</th>
                    <th>Setting</th>
                    <th>D/N</th>
                    <th>Length</th>
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
            
            # Scene length in eighths
            eighths = scene.get('page_length_eighths', 8)
            length_display = format_eighths(eighths)
            
            rows.append(f"""
            <tr class="one-liner-row">
                <td class="scene-num">{scene.get('scene_number', '')}</td>
                <td class="int-ext">{scene.get('int_ext', '')}</td>
                <td class="setting">{scene.get('setting', '')}</td>
                <td class="time">{scene.get('time_of_day', '')}</td>
                <td class="chars">{chars}</td>
                <td class="length">{length_display}</td>
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
                    <th>Len</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_full_breakdown(self, data: Dict) -> str:
        """Render full breakdown HTML with comprehensive statistics."""
        summary = data.get('summary', {})
        
        # Calculate analysis completion percentage
        total_scenes = summary.get('total_scenes', 0)
        analyzed_scenes = summary.get('analyzed_scenes', 0)
        completion_pct = int((analyzed_scenes / total_scenes * 100)) if total_scenes > 0 else 0
        
        # Calculate script length from eighths
        total_eighths = summary.get('total_eighths', 0)
        total_pages = total_eighths / 8 if total_eighths else summary.get('total_pages', 0)
        avg_scene_eighths = total_eighths // max(total_scenes, 1) if total_eighths else 8
        
        summary_html = f"""
        <div class="summary-section">
            <h2>Script Summary</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <span class="label">Total Scenes</span>
                    <span class="value">{summary.get('total_scenes', 0)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Script Length</span>
                    <span class="value">{total_pages:.1f} pgs</span>
                </div>
                <div class="summary-item">
                    <span class="label">Avg Scene</span>
                    <span class="value">{format_eighths(avg_scene_eighths)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Analysis</span>
                    <span class="value">{completion_pct}%</span>
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
                <div class="summary-item">
                    <span class="label">Wardrobe</span>
                    <span class="value">{summary.get('total_wardrobe', 0)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Makeup/Hair</span>
                    <span class="value">{summary.get('total_makeup', 0)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Special FX</span>
                    <span class="value">{summary.get('total_special_effects', 0)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Vehicles</span>
                    <span class="value">{summary.get('total_vehicles', 0)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Animals</span>
                    <span class="value">{summary.get('total_animals', 0)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Extras</span>
                    <span class="value">{summary.get('total_extras', 0)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Stunts</span>
                    <span class="value">{summary.get('total_stunts', 0)}</span>
                </div>
            </div>
            <p style="margin-top: 1rem; font-size: 8pt; color: #666; text-align: center;">
                Report generated: {data.get('generated_at', '')[:19].replace('T', ' ')} UTC
            </p>
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
        """Get CSS for PDF reports with enhanced breakdown layout."""
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
            flex-wrap: wrap;
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
            page-break-after: avoid;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 9pt;
            page-break-inside: auto;
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
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        
        tr {
            page-break-inside: avoid;
        }
        
        tr:nth-child(4n+1) {
            background: #fafafa;
        }
        
        /* Scene breakdown specific styles */
        .breakdown-table .scene-num {
            font-weight: 600;
            width: 50px;
        }
        
        .breakdown-table .int-ext {
            width: 40px;
            text-align: center;
        }
        
        .breakdown-table .setting {
            min-width: 120px;
        }
        
        .breakdown-table .time {
            width: 50px;
            text-align: center;
        }
        
        .breakdown-table .length-cell {
            width: 80px;
            text-align: center;
            font-weight: 600;
            font-family: 'Courier New', monospace;
            white-space: nowrap;
            font-size: 9pt;
        }
        
        .breakdown-details {
            background: #f9f9f9 !important;
        }
        
        .breakdown-details td {
            padding: 12px;
        }
        
        .breakdown-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
            font-size: 8.5pt;
        }
        
        .breakdown-item {
            display: flex;
            gap: 8px;
            line-height: 1.3;
        }
        
        .breakdown-item .label {
            font-weight: 600;
            color: #555;
            min-width: 90px;
            flex-shrink: 0;
        }
        
        .breakdown-item .value {
            color: #1a1a1a;
            flex: 1;
            word-wrap: break-word;
        }
        
        .scenes-cell {
            font-size: 8pt;
            color: #666;
            max-width: 200px;
            word-wrap: break-word;
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
        
        .one-liner-table .length {
            width: 60px;
            text-align: center;
            font-family: 'Courier New', monospace;
            font-weight: 600;
        }
        
        /* Summary section */
        .summary-section {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1.5rem;
            page-break-inside: avoid;
        }
        
        .summary-grid {
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
        }
        
        .summary-item {
            text-align: center;
            min-width: 80px;
        }
        
        .summary-item .label {
            display: block;
            font-size: 8pt;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .summary-item .value {
            display: block;
            font-size: 18pt;
            font-weight: 700;
            color: #333;
            margin-top: 4px;
        }
        
        .page-break {
            page-break-after: always;
        }
        
        /* Print optimizations */
        @media print {
            .page-break {
                page-break-after: always;
            }
            
            h2 {
                page-break-after: avoid;
            }
            
            tr {
                page-break-inside: avoid;
            }
            
            table {
                page-break-inside: auto;
            }
        }
        
        /* Department-specific report styles */
        .department-header {
            background: #e8f4f8;
            padding: 12px;
            margin: 1rem 0;
            border-left: 4px solid #0066cc;
        }
        
        .department-header h3 {
            margin: 0;
            font-size: 12pt;
            color: #0066cc;
        }
        """
    
    # ============================================
    # Department-Specific Report Renderers
    # ============================================
    
    def _render_wardrobe_department(self, data: Dict) -> str:
        """Render wardrobe department report with character grouping."""
        wardrobe = data.get('wardrobe', {})
        characters = data.get('characters', {})
        
        if not wardrobe:
            return '<h2>Wardrobe Department</h2><p>No wardrobe items found.</p>'
        
        rows = []
        sorted_items = sorted(wardrobe.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for item_name, info in sorted_items:
            scenes_str = ', '.join(info['scenes'][:15])
            if len(info['scenes']) > 15:
                scenes_str += f" (+{len(info['scenes']) - 15} more)"
            
            # Get associated characters
            chars = ', '.join(info.get('characters', [])) or '—'
            
            rows.append(f"""
            <tr>
                <td><strong>{item_name}</strong></td>
                <td>{chars}</td>
                <td>{info['count']}</td>
                <td class="scenes-cell">{scenes_str}</td>
            </tr>
            """)
        
        return f"""
        <div class="department-header">
            <h3>Wardrobe Department Report</h3>
        </div>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Item</th>
                    <th>Character(s)</th>
                    <th>Scenes</th>
                    <th>Scene Numbers</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_props_department(self, data: Dict) -> str:
        """Render props department report."""
        props = data.get('props', {})
        
        if not props:
            return '<h2>Props Department</h2><p>No props found.</p>'
        
        rows = []
        sorted_props = sorted(props.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for prop_name, info in sorted_props:
            scenes_str = ', '.join(info['scenes'][:15])
            if len(info['scenes']) > 15:
                scenes_str += f" (+{len(info['scenes']) - 15} more)"
            
            rows.append(f"""
            <tr>
                <td><strong>{prop_name}</strong></td>
                <td>{info['count']}</td>
                <td class="scenes-cell">{scenes_str}</td>
            </tr>
            """)
        
        return f"""
        <div class="department-header">
            <h3>Props Department Report</h3>
        </div>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Prop</th>
                    <th>Scenes</th>
                    <th>Scene Numbers</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_makeup_department(self, data: Dict) -> str:
        """Render makeup & hair department report with character grouping."""
        makeup = data.get('makeup', {})
        
        if not makeup:
            return '<h2>Makeup & Hair Department</h2><p>No makeup requirements found.</p>'
        
        rows = []
        sorted_items = sorted(makeup.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for item_name, info in sorted_items:
            scenes_str = ', '.join(info['scenes'][:15])
            if len(info['scenes']) > 15:
                scenes_str += f" (+{len(info['scenes']) - 15} more)"
            
            # Get associated characters
            chars = ', '.join(info.get('characters', [])) or '—'
            
            rows.append(f"""
            <tr>
                <td><strong>{item_name}</strong></td>
                <td>{chars}</td>
                <td>{info['count']}</td>
                <td class="scenes-cell">{scenes_str}</td>
            </tr>
            """)
        
        return f"""
        <div class="department-header">
            <h3>Makeup & Hair Department Report</h3>
        </div>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Requirement</th>
                    <th>Character(s)</th>
                    <th>Scenes</th>
                    <th>Scene Numbers</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_sfx_department(self, data: Dict) -> str:
        """Render special effects department report."""
        sfx = data.get('special_effects', {})
        
        if not sfx:
            return '<h2>Special Effects Department</h2><p>No special effects found.</p>'
        
        rows = []
        sorted_sfx = sorted(sfx.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for effect_name, info in sorted_sfx:
            scenes_str = ', '.join(info['scenes'][:15])
            if len(info['scenes']) > 15:
                scenes_str += f" (+{len(info['scenes']) - 15} more)"
            
            # Get effect types
            types = ', '.join(info.get('type', [])) or 'unknown'
            
            rows.append(f"""
            <tr>
                <td><strong>{effect_name}</strong></td>
                <td>{types}</td>
                <td>{info['count']}</td>
                <td class="scenes-cell">{scenes_str}</td>
            </tr>
            """)
        
        return f"""
        <div class="department-header">
            <h3>Special Effects Department Report</h3>
        </div>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Effect</th>
                    <th>Type</th>
                    <th>Scenes</th>
                    <th>Scene Numbers</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_stunts_department(self, data: Dict) -> str:
        """Render stunts department report."""
        stunts = data.get('stunts', {})
        
        if not stunts:
            return '<h2>Stunts Department</h2><p>No stunts found.</p>'
        
        rows = []
        sorted_stunts = sorted(stunts.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for stunt_name, info in sorted_stunts:
            scenes_str = ', '.join(info['scenes'][:15])
            if len(info['scenes']) > 15:
                scenes_str += f" (+{len(info['scenes']) - 15} more)"
            
            rows.append(f"""
            <tr>
                <td><strong>{stunt_name}</strong></td>
                <td>{info['count']}</td>
                <td class="scenes-cell">{scenes_str}</td>
            </tr>
            """)
        
        return f"""
        <div class="department-header">
            <h3>Stunts Department Report</h3>
        </div>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Stunt</th>
                    <th>Scenes</th>
                    <th>Scene Numbers</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_vehicles_department(self, data: Dict) -> str:
        """Render vehicles department report."""
        vehicles = data.get('vehicles', {})
        
        if not vehicles:
            return '<h2>Vehicles Department</h2><p>No vehicles found.</p>'
        
        rows = []
        sorted_vehicles = sorted(vehicles.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for vehicle_name, info in sorted_vehicles:
            scenes_str = ', '.join(info['scenes'][:15])
            if len(info['scenes']) > 15:
                scenes_str += f" (+{len(info['scenes']) - 15} more)"
            
            rows.append(f"""
            <tr>
                <td><strong>{vehicle_name}</strong></td>
                <td>{info['count']}</td>
                <td class="scenes-cell">{scenes_str}</td>
            </tr>
            """)
        
        return f"""
        <div class="department-header">
            <h3>Vehicles & Transportation Report</h3>
        </div>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Vehicle</th>
                    <th>Scenes</th>
                    <th>Scene Numbers</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_animals_department(self, data: Dict) -> str:
        """Render animals department report."""
        animals = data.get('animals', {})
        
        if not animals:
            return '<h2>Animals Department</h2><p>No animals found.</p>'
        
        rows = []
        sorted_animals = sorted(animals.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for animal_name, info in sorted_animals:
            scenes_str = ', '.join(info['scenes'][:15])
            if len(info['scenes']) > 15:
                scenes_str += f" (+{len(info['scenes']) - 15} more)"
            
            rows.append(f"""
            <tr>
                <td><strong>{animal_name}</strong></td>
                <td>{info['count']}</td>
                <td class="scenes-cell">{scenes_str}</td>
            </tr>
            """)
        
        return f"""
        <div class="department-header">
            <h3>Animals & Wranglers Report</h3>
        </div>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Animal</th>
                    <th>Scenes</th>
                    <th>Scene Numbers</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_extras_department(self, data: Dict) -> str:
        """Render extras department report."""
        extras = data.get('extras', {})
        
        if not extras:
            return '<h2>Extras Department</h2><p>No extras found.</p>'
        
        rows = []
        sorted_extras = sorted(extras.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for extra_name, info in sorted_extras:
            scenes_str = ', '.join(info['scenes'][:15])
            if len(info['scenes']) > 15:
                scenes_str += f" (+{len(info['scenes']) - 15} more)"
            
            rows.append(f"""
            <tr>
                <td><strong>{extra_name}</strong></td>
                <td>{info['count']}</td>
                <td class="scenes-cell">{scenes_str}</td>
            </tr>
            """)
        
        return f"""
        <div class="department-header">
            <h3>Extras & Background Report</h3>
        </div>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Extras</th>
                    <th>Scenes</th>
                    <th>Scene Numbers</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """

    # ============================================
    # Enrichment-Based Report Renderers (LangExtract)
    # ============================================
    
    def _render_dialogue_report(self, data: Dict) -> str:
        """Render dialogue & tone report grouped by character."""
        enrichment = data.get('enrichment', {})
        dialogue = enrichment.get('dialogue', [])
        
        if not dialogue:
            return '<p class="no-data">No dialogue data available. Run LangExtract analysis first.</p>'
        
        # Group by character
        by_character = defaultdict(list)
        for line in dialogue:
            char = line.get('character', 'Unknown')
            by_character[char].append(line)
        
        rows = []
        for char_name in sorted(by_character.keys()):
            lines = by_character[char_name]
            rows.append(f'<tr class="character-header"><td colspan="4"><strong>{char_name}</strong> ({len(lines)} lines)</td></tr>')
            for line in lines:
                tone = line.get('tone', '')
                tone_badge = f'<span class="tone-badge">{tone}</span>' if tone else '—'
                rows.append(f"""
                <tr>
                    <td class="dialogue-text">"{line.get('text', '')}"</td>
                    <td>{tone_badge}</td>
                    <td>Sc. {line.get('scene', '—')}</td>
                    <td>{line.get('confidence', 0):.0%}</td>
                </tr>
                """)
        
        total = enrichment.get('total_dialogue_lines', len(dialogue))
        
        return f"""
        <div class="department-header">
            <h3>Dialogue & Tone Report</h3>
            <p>{total} dialogue lines across {len(by_character)} characters</p>
        </div>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Dialogue</th>
                    <th>Tone</th>
                    <th>Scene</th>
                    <th>Confidence</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_sound_cues_report(self, data: Dict) -> str:
        """Render sound design cue sheet."""
        enrichment = data.get('enrichment', {})
        sound_cues = enrichment.get('sound_cues', {})
        
        if not sound_cues:
            return '<p class="no-data">No sound cue data available. Run LangExtract analysis first.</p>'
        
        rows = []
        for cue_name, cue_data in sorted(sound_cues.items(), key=lambda x: -x[1].get('count', 0)):
            cue_type = ', '.join(cue_data.get('type', [])) or '—'
            scenes = ', '.join(str(s) for s in cue_data.get('scenes', []))
            rows.append(f"""
            <tr>
                <td>{cue_name}</td>
                <td>{cue_type}</td>
                <td>{cue_data.get('count', 0)}</td>
                <td>{scenes or '—'}</td>
            </tr>
            """)
        
        return f"""
        <div class="department-header">
            <h3>Sound Design Cue Sheet</h3>
            <p>{len(sound_cues)} unique sound cues</p>
        </div>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Sound Cue</th>
                    <th>Type</th>
                    <th>Occurrences</th>
                    <th>Scenes</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _render_emotional_arc_report(self, data: Dict) -> str:
        """Render emotional arc report showing emotional progression."""
        enrichment = data.get('enrichment', {})
        emotions = enrichment.get('emotions', {})
        relationships = enrichment.get('relationships', [])
        
        if not emotions and not relationships:
            return '<p class="no-data">No emotional data available. Run LangExtract analysis first.</p>'
        
        # Emotions table
        emotion_rows = []
        for emotion_name, emo_data in sorted(emotions.items(), key=lambda x: -x[1].get('count', 0)):
            scenes = ', '.join(str(s) for s in emo_data.get('scenes', []))
            intensities = emo_data.get('intensity', [])
            avg_intensity = intensities[0] if intensities else '—'
            emotion_rows.append(f"""
            <tr>
                <td>{emotion_name}</td>
                <td>{emo_data.get('count', 0)}</td>
                <td>{avg_intensity}</td>
                <td>{scenes or '—'}</td>
            </tr>
            """)
        
        # Relationships table
        rel_rows = []
        for rel in relationships:
            chars = ' & '.join(c for c in rel.get('characters', []) if c)
            rel_rows.append(f"""
            <tr>
                <td>{rel.get('text', '')}</td>
                <td>{chars or '—'}</td>
                <td>{rel.get('dynamic', '—')}</td>
                <td>Sc. {rel.get('scene', '—')}</td>
            </tr>
            """)
        
        emotions_html = f"""
        <div class="department-header">
            <h3>Emotional Arc</h3>
            <p>{len(emotions)} unique emotions detected</p>
        </div>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Emotion</th>
                    <th>Occurrences</th>
                    <th>Intensity</th>
                    <th>Scenes</th>
                </tr>
            </thead>
            <tbody>
                {''.join(emotion_rows)}
            </tbody>
        </table>
        """
        
        relationships_html = ''
        if rel_rows:
            relationships_html = f"""
            <div class="department-header" style="margin-top: 2rem;">
                <h3>Character Relationships</h3>
                <p>{len(relationships)} relationship dynamics</p>
            </div>
            <table class="breakdown-table">
                <thead>
                    <tr>
                        <th>Relationship</th>
                        <th>Characters</th>
                        <th>Dynamic</th>
                        <th>Scene</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rel_rows)}
                </tbody>
            </table>
            """
        
        return emotions_html + relationships_html
    
    def _render_continuity_report(self, data: Dict) -> str:
        """Render continuity report tracking props, wardrobe, and makeup across scenes."""
        props = data.get('props', {})
        wardrobe = data.get('wardrobe', {})
        makeup = data.get('makeup', {})
        
        sections = []
        
        # Props continuity
        if props:
            prop_rows = []
            for name, info in sorted(props.items(), key=lambda x: -x[1].get('count', 0)):
                scenes = ', '.join(str(s) for s in info.get('scenes', []))
                rich = info.get('rich_attributes', [{}])
                condition = rich[0].get('condition', '') if rich else ''
                importance = rich[0].get('importance', '') if rich else ''
                prop_rows.append(f"""
                <tr>
                    <td>{name}</td>
                    <td>{info.get('count', 0)}</td>
                    <td>{scenes}</td>
                    <td>{condition or '—'}</td>
                    <td>{importance or '—'}</td>
                </tr>
                """)
            
            sections.append(f"""
            <div class="department-header">
                <h3>Props Continuity</h3>
            </div>
            <table class="breakdown-table">
                <thead>
                    <tr><th>Prop</th><th>Appearances</th><th>Scenes</th><th>Condition</th><th>Importance</th></tr>
                </thead>
                <tbody>{''.join(prop_rows)}</tbody>
            </table>
            """)
        
        # Wardrobe continuity
        if wardrobe:
            ward_rows = []
            for name, info in sorted(wardrobe.items(), key=lambda x: -x[1].get('count', 0)):
                scenes = ', '.join(str(s) for s in info.get('scenes', []))
                chars = ', '.join(info.get('characters', [])) or '—'
                ward_rows.append(f"""
                <tr>
                    <td>{name}</td>
                    <td>{chars}</td>
                    <td>{info.get('count', 0)}</td>
                    <td>{scenes}</td>
                </tr>
                """)
            
            sections.append(f"""
            <div class="department-header" style="margin-top: 2rem;">
                <h3>Wardrobe Continuity</h3>
            </div>
            <table class="breakdown-table">
                <thead>
                    <tr><th>Item</th><th>Character</th><th>Appearances</th><th>Scenes</th></tr>
                </thead>
                <tbody>{''.join(ward_rows)}</tbody>
            </table>
            """)
        
        # Makeup continuity
        if makeup:
            makeup_rows = []
            for name, info in sorted(makeup.items(), key=lambda x: -x[1].get('count', 0)):
                scenes = ', '.join(str(s) for s in info.get('scenes', []))
                chars = ', '.join(info.get('characters', [])) or '—'
                makeup_rows.append(f"""
                <tr>
                    <td>{name}</td>
                    <td>{chars}</td>
                    <td>{info.get('count', 0)}</td>
                    <td>{scenes}</td>
                </tr>
                """)
            
            sections.append(f"""
            <div class="department-header" style="margin-top: 2rem;">
                <h3>Makeup & Hair Continuity</h3>
            </div>
            <table class="breakdown-table">
                <thead>
                    <tr><th>Look</th><th>Character</th><th>Appearances</th><th>Scenes</th></tr>
                </thead>
                <tbody>{''.join(makeup_rows)}</tbody>
            </table>
            """)
        
        if not sections:
            return '<p class="no-data">No continuity data available.</p>'
        
        return '\n'.join(sections)


# Singleton instance
report_service = ReportService()
