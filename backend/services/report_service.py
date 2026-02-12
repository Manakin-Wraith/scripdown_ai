"""
Report Service for ScripDown AI

Handles report generation, data aggregation, and PDF creation.
Supports multiple report types: scene breakdown, day-out-of-days, 
location reports, props lists, and one-liner/stripboard views.
"""

import os
import re
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
# Scene Number Helpers (for range filtering)
# ============================================

def _parse_scene_number(scene_num: str) -> tuple:
    """
    Parse a scene number into (numeric_prefix, alpha_suffix) for comparison.
    Examples: '5' -> (5, ''), '5A' -> (5, 'A'), '12B' -> (12, 'B'), 'A1' -> (0, 'A1')
    """
    if not scene_num:
        return (0, '')
    match = re.match(r'^(\d+)(.*)', str(scene_num).strip())
    if match:
        return (int(match.group(1)), match.group(2).upper())
    return (0, str(scene_num).upper())


def _in_scene_range(scene_num: str, scene_range: Dict) -> bool:
    """
    Check if scene_num falls within scene_range {'from': '1', 'to': '20'}.
    Compares numeric prefix; alpha suffixes are included (e.g., '5A' is within 1-20).
    """
    if not scene_range:
        return True
    parsed = _parse_scene_number(scene_num)
    range_from = scene_range.get('from')
    range_to = scene_range.get('to')
    if range_from:
        from_parsed = _parse_scene_number(range_from)
        if parsed < from_parsed:
            return False
    if range_to:
        to_parsed = _parse_scene_number(range_to)
        # Include the 'to' number and all its suffixes (e.g., 20, 20A, 20B)
        if parsed[0] > to_parsed[0]:
            return False
        if parsed[0] == to_parsed[0] and to_parsed[1] and parsed[1] > to_parsed[1]:
            return False
    return True


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


class ReportConfig:
    """Report configuration with validation and defaults."""
    
    VALID_REPORT_TYPES = [
        "full_breakdown", "scene_breakdown", "wardrobe", "props",
        "makeup", "sfx", "special_effects", "stunts", "vehicles", 
        "animals", "extras", "custom", "day_out_of_days", 
        "location", "one_liner"
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
            "extras": PRESET_EXTRAS
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
            {"name": "extras", "title": "Extras & Background", "description": "Background actor requirements"}
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
    # Scene Filtering
    # ============================================
    
    def _filter_scenes(self, scenes: List[Dict], filters: Dict) -> List[Dict]:
        """
        Filter scenes based on criteria. All filters AND-combined.
        Multiple values within a single filter are OR-combined.
        Returns subset of scenes matching all active filters.
        """
        if not filters:
            return scenes
        
        filtered = list(scenes)
        
        # Location filter (exact match on setting)
        if filters.get('locations'):
            locs = [l.upper() for l in filters['locations']]
            filtered = [s for s in filtered if (s.get('setting') or '').upper() in locs]
        
        # Location parent filter (matches if location_hierarchy contains parent)
        if filters.get('location_parents'):
            parents = [p.upper() for p in filters['location_parents']]
            def _matches_parent(scene):
                hierarchy = scene.get('location_hierarchy') or []
                if isinstance(hierarchy, list) and hierarchy:
                    return any(h.upper() in parents for h in hierarchy)
                setting = (scene.get('setting') or '').upper()
                return any(setting.startswith(p) for p in parents)
            filtered = [s for s in filtered if _matches_parent(s)]
        
        # Character filter (scene must contain at least one of the characters)
        if filters.get('characters'):
            chars = [c.upper() for c in filters['characters']]
            def _has_character(scene):
                scene_chars = scene.get('characters') or []
                for c in scene_chars:
                    name = c.upper() if isinstance(c, str) else (c.get('name', '') or '').upper()
                    if name in chars:
                        return True
                return False
            filtered = [s for s in filtered if _has_character(s)]
        
        # INT/EXT filter
        if filters.get('int_ext'):
            vals = [v.upper() for v in filters['int_ext']]
            filtered = [s for s in filtered if (s.get('int_ext') or '').upper() in vals]
        
        # Time of day filter
        if filters.get('time_of_day'):
            vals = [v.upper() for v in filters['time_of_day']]
            filtered = [s for s in filtered if (s.get('time_of_day') or '').upper() in vals]
        
        # Story day filter
        if filters.get('story_days'):
            days = filters['story_days']
            filtered = [s for s in filtered if s.get('story_day') in days]
        
        # Scene numbers filter (specific scenes)
        if filters.get('scene_numbers'):
            nums = [str(n) for n in filters['scene_numbers']]
            filtered = [s for s in filtered if str(s.get('scene_number', '')) in nums]
        
        # Scene range filter
        if filters.get('scene_range'):
            sr = filters['scene_range']
            if sr.get('from') or sr.get('to'):
                filtered = [s for s in filtered if _in_scene_range(s.get('scene_number', ''), sr)]
        
        # Timeline code filter
        if filters.get('timeline_codes'):
            codes = [c.upper() for c in filters['timeline_codes']]
            filtered = [s for s in filtered 
                        if (s.get('timeline_code') or 'PRESENT').upper() in codes]
        
        # Exclude omitted scenes (default True)
        if filters.get('exclude_omitted', True):
            filtered = [s for s in filtered if not s.get('is_omitted')]
        
        return filtered
    
    def get_filter_options(self, script_id: str) -> Dict[str, Any]:
        """
        Return unique values for each filter dimension.
        Used by frontend to populate filter dropdowns.
        """
        scenes = self.db.get_scenes(script_id)
        
        locations = set()
        location_parents = set()
        characters = set()
        int_ext_values = set()
        time_of_day_values = set()
        story_days = set()
        timeline_codes = set()
        scene_numbers = []
        
        for scene in scenes:
            # Locations
            setting = scene.get('setting')
            if setting:
                locations.add(setting)
            
            # Location parents (from hierarchy)
            hierarchy = scene.get('location_hierarchy')
            if isinstance(hierarchy, list) and len(hierarchy) > 1:
                location_parents.add(hierarchy[0])
            
            # Characters
            for c in (scene.get('characters') or []):
                name = c if isinstance(c, str) else c.get('name', '')
                if name:
                    characters.add(name)
            
            # INT/EXT
            ie = scene.get('int_ext')
            if ie:
                int_ext_values.add(ie)
            
            # Time of day
            tod = scene.get('time_of_day')
            if tod:
                time_of_day_values.add(tod)
            
            # Story days
            sd = scene.get('story_day')
            if sd is not None:
                story_days.add(sd)
            
            # Timeline codes
            tc = scene.get('timeline_code')
            if tc:
                timeline_codes.add(tc)
            
            # Scene numbers (preserve order)
            sn = scene.get('scene_number')
            if sn is not None:
                scene_numbers.append(str(sn))
        
        return {
            'locations': sorted(locations),
            'location_parents': sorted(location_parents),
            'characters': sorted(characters),
            'int_ext_values': sorted(int_ext_values),
            'time_of_day_values': sorted(time_of_day_values),
            'story_days': sorted(story_days),
            'timeline_codes': sorted(timeline_codes),
            'scene_numbers': scene_numbers,
            'total_scenes': len(scenes)
        }
    
    # ============================================
    # Data Aggregation
    # ============================================
    
    def aggregate_scene_data(self, script_id: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Aggregate all scene data for a script.
        Returns structured data for report generation.
        Collects ALL breakdown categories without truncation.
        When filters are provided, only matching scenes are aggregated.
        """
        # Get script metadata
        script = self.db.get_script(script_id)
        if not script:
            raise ValueError(f"Script not found: {script_id}")
        
        # Get all scenes
        all_scenes = self.db.get_scenes(script_id)
        
        # Apply filters if provided
        scenes = self._filter_scenes(all_scenes, filters) if filters else all_scenes
        
        # Get user-added items from department_items (exclude removed)
        user_items_by_scene = {}
        try:
            items_result = self.db.client.table('department_items').select(
                'scene_id, item_type, item_name'
            ).eq('script_id', script_id).neq('status', 'removed').execute()
            for item in (items_result.data or []):
                sid = item.get('scene_id')
                itype = item.get('item_type')
                iname = item.get('item_name')
                if sid and itype and iname:
                    if sid not in user_items_by_scene:
                        user_items_by_scene[sid] = {}
                    if itype not in user_items_by_scene[sid]:
                        user_items_by_scene[sid][itype] = []
                    user_items_by_scene[sid][itype].append(iname)
        except Exception as e:
            print(f"Warning: Could not fetch department_items for report: {e}")
        
        # Aggregate data - NO TRUNCATION
        characters = defaultdict(lambda: {'count': 0, 'scenes': [], 'eighths': 0, 'story_days': set()})
        locations = defaultdict(lambda: {'count': 0, 'scenes': [], 'int_ext': set(), 'time_of_day': set(), 'story_days': set()})
        props = defaultdict(lambda: {'count': 0, 'scenes': [], 'story_days': set()})
        wardrobe_items = defaultdict(lambda: {'count': 0, 'scenes': [], 'characters': set()})
        makeup_items = defaultdict(lambda: {'count': 0, 'scenes': [], 'characters': set()})
        special_effects = defaultdict(lambda: {'count': 0, 'scenes': [], 'type': set()})
        vehicles = defaultdict(lambda: {'count': 0, 'scenes': []})
        animals = defaultdict(lambda: {'count': 0, 'scenes': []})
        extras = defaultdict(lambda: {'count': 0, 'scenes': []})
        stunts = defaultdict(lambda: {'count': 0, 'scenes': []})
        
        total_eighths = 0
        analyzed_scenes = 0
        all_story_days = set()
        
        for scene in scenes:
            scene_num = scene.get('scene_number', '')
            eighths = scene.get('page_length_eighths', 8)  # Default to 1 page
            total_eighths += eighths
            
            if scene.get('analysis_status') == 'complete':
                analyzed_scenes += 1
            
            # Track story day
            scene_story_day = scene.get('story_day')
            if scene_story_day:
                all_story_days.add(scene_story_day)
            
            # Characters
            for char in (scene.get('characters') or []):
                char_name = char if isinstance(char, str) else char.get('name', str(char))
                characters[char_name]['count'] += 1
                characters[char_name]['scenes'].append(scene_num)
                characters[char_name]['eighths'] += eighths
                if scene_story_day:
                    characters[char_name]['story_days'].add(scene_story_day)
            
            # Locations
            setting = scene.get('setting', 'UNKNOWN')
            locations[setting]['count'] += 1
            locations[setting]['scenes'].append(scene_num)
            locations[setting]['int_ext'].add(scene.get('int_ext', 'INT'))
            locations[setting]['time_of_day'].add(scene.get('time_of_day', 'DAY'))
            if scene_story_day:
                locations[setting]['story_days'].add(scene_story_day)
            
            # Props
            for prop in (scene.get('props') or []):
                prop_name = prop if isinstance(prop, str) else prop.get('name', str(prop))
                props[prop_name]['count'] += 1
                props[prop_name]['scenes'].append(scene_num)
                if scene_story_day:
                    props[prop_name]['story_days'].add(scene_story_day)
            
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
            
            # Merge user-added items from department_items for this scene
            scene_id = scene.get('id') or scene.get('scene_id')
            scene_user_items = user_items_by_scene.get(scene_id, {})
            category_map = {
                'characters': characters,
                'props': props,
                'wardrobe': wardrobe_items,
                'makeup': makeup_items,
                'special_fx': special_effects,
                'special_effects': special_effects,
                'vehicles': vehicles,
                'animals': animals,
                'extras': extras,
                'stunts': stunts,
                'sound': None,  # sound is handled differently (not aggregated)
            }
            for itype, names in scene_user_items.items():
                target = category_map.get(itype)
                if target is not None:
                    for name in names:
                        target[name]['count'] += 1
                        target[name]['scenes'].append(scene_num)
                        if itype == 'characters':
                            target[name]['eighths'] += eighths
        
        # Calculate total pages from eighths
        total_pages = total_eighths / 8
        
        return {
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
                'total_pages': total_pages,
                'total_story_days': len(all_story_days)
            },
            'scenes': scenes,
            'user_items_by_scene': user_items_by_scene,
            'characters': {k: {**v, 'story_days': sorted(v['story_days'])} for k, v in characters.items()},
            'locations': {k: {**v, 'int_ext': list(v['int_ext']), 'time_of_day': list(v['time_of_day']), 'story_days': sorted(v['story_days'])} 
                         for k, v in locations.items()},
            'props': {k: {**v, 'story_days': sorted(v['story_days'])} for k, v in props.items()},
            'wardrobe': {k: {**v, 'characters': list(v['characters'])} for k, v in wardrobe_items.items()},
            'makeup': {k: {**v, 'characters': list(v['characters'])} for k, v in makeup_items.items()},
            'special_effects': {k: {**v, 'type': list(v['type'])} for k, v in special_effects.items()},
            'vehicles': dict(vehicles),
            'animals': dict(animals),
            'extras': dict(extras),
            'stunts': dict(stunts),
            'filter_summary': {
                'total_scenes_unfiltered': len(all_scenes),
                'total_scenes_filtered': len(scenes),
                'is_filtered': filters is not None and len(scenes) != len(all_scenes),
                'active_filters': [k for k, v in (filters or {}).items() if v] if filters else []
            },
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
        user_id: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        Generate a report and store it in the database.
        Returns the report record with data snapshot.
        Accepts optional filters to restrict which scenes are included.
        """
        if report_type not in self.REPORT_TYPES:
            raise ValueError(f"Invalid report type: {report_type}")
        
        # Aggregate data with optional filters
        data = self.aggregate_scene_data(script_id, filters=filters)
        
        # Generate title if not provided
        if not title:
            title = f"{data['script']['title']} - {self.REPORT_TYPES[report_type]['name']}"
        
        # Merge filters into config for persistence
        merged_config = config or {}
        if filters:
            merged_config['filters'] = filters
        
        # Create report record
        report_data = {
            'script_id': script_id,
            'report_type': report_type,
            'title': title,
            'config': merged_config,
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
    # Filter Presets
    # ============================================
    
    def get_filter_presets(self, script_id: str, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get filter presets: default (global) + user's own for this script.
        """
        presets = []
        
        # Get default presets (no script_id, is_default=True)
        default_result = self.db.client.table('report_filter_presets').select('*').eq('is_default', True).order('name').execute()
        presets.extend(default_result.data or [])
        
        # Get user's custom presets for this script
        if user_id:
            user_result = (
                self.db.client.table('report_filter_presets')
                .select('*')
                .eq('user_id', user_id)
                .eq('script_id', script_id)
                .eq('is_default', False)
                .order('name')
                .execute()
            )
            presets.extend(user_result.data or [])
        
        return presets
    
    def save_filter_preset(
        self,
        script_id: str,
        user_id: str,
        name: str,
        filters: Dict,
        categories: Optional[List[str]] = None,
        group_by: str = 'scene_number'
    ) -> Dict:
        """Save a new filter preset for a user."""
        preset_data = {
            'user_id': user_id,
            'script_id': script_id,
            'name': name,
            'filters': filters or {},
            'categories': categories or [],
            'group_by': group_by,
            'is_default': False
        }
        
        result = self.db.client.table('report_filter_presets').insert(preset_data).execute()
        return result.data[0] if result.data else None
    
    def delete_filter_preset(self, preset_id: str, user_id: str) -> bool:
        """Delete a user's filter preset. Cannot delete default presets."""
        self.db.client.table('report_filter_presets').delete().eq('id', preset_id).eq('user_id', user_id).eq('is_default', False).execute()
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
        
        # Check for grouped rendering via config
        config = report.get('config', {})
        group_by = config.get('group_by')
        categories = config.get('categories')
        
        # If group_by is set to a non-default value, use grouped renderer
        if group_by and group_by != 'scene_number':
            body = self._render_grouped_report(data, group_by, categories if categories else None)
        # Otherwise render based on type
        elif report_type == 'scene_breakdown':
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
        user_items_map = data.get('user_items_by_scene', {})
        rows = []
        
        for scene in scenes:
            scene_id = scene.get('id') or scene.get('scene_id')
            scene_user = user_items_map.get(scene_id, {})
            
            # Helper to merge AI + user items, then format
            def merge_and_format(ai_items, user_list):
                combined = list(ai_items or []) + list(user_list or [])
                if not combined:
                    return '—'
                return ', '.join([
                    (item if isinstance(item, str) else item.get('name', str(item)))
                    for item in combined
                ])
            
            # Get all breakdown data - NO TRUNCATION (merged AI + user)
            chars = merge_and_format(scene.get('characters'), scene_user.get('characters'))
            props = merge_and_format(scene.get('props'), scene_user.get('props'))
            wardrobe = merge_and_format(scene.get('wardrobe'), scene_user.get('wardrobe'))
            makeup = merge_and_format(scene.get('makeup'), scene_user.get('makeup'))
            sfx = merge_and_format(scene.get('special_effects'), scene_user.get('special_effects', scene_user.get('special_fx')))
            vehicles = merge_and_format(scene.get('vehicles'), scene_user.get('vehicles'))
            animals = merge_and_format(scene.get('animals'), scene_user.get('animals'))
            extras = merge_and_format(scene.get('extras'), scene_user.get('extras'))
            stunts = merge_and_format(scene.get('stunts'), scene_user.get('stunts'))
            
            # Scene description and notes
            description = scene.get('description', '') or scene.get('action_description', '')
            emotional_tone = scene.get('emotional_tone', '')
            technical_notes = scene.get('technical_notes', '')
            
            # Scene length in eighths
            eighths = scene.get('page_length_eighths', 8)
            length_display = format_eighths(eighths)
            
            story_day_display = f"D{scene.get('story_day')}" if scene.get('story_day') else '—'
            
            rows.append(f"""
            <tr>
                <td class="scene-num"><strong>{scene.get('scene_number', '')}</strong></td>
                <td class="int-ext">{scene.get('int_ext', '')}</td>
                <td class="setting"><strong>{scene.get('setting', '')}</strong></td>
                <td class="time">{scene.get('time_of_day', '')}</td>
                <td class="day-cell">{story_day_display}</td>
                <td class="length-cell">{length_display}</td>
            </tr>
            <tr class="breakdown-details">
                <td colspan="6">
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
                    <th>Day</th>
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
            scenes_str = ', '.join(info['scenes'])
            
            story_days = info.get('story_days', [])
            days_str = ', '.join([f'D{d}' for d in sorted(story_days)]) if story_days else '—'
            
            rows.append(f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{info['count']}</td>
                <td>{info.get('pages', info['count'])}</td>
                <td>{days_str}</td>
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
                    <th>Story Days</th>
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
            scenes_str = ', '.join(info['scenes'])
            
            story_days = info.get('story_days', [])
            days_str = ', '.join([f'D{d}' for d in sorted(story_days)]) if story_days else '—'
            
            rows.append(f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{int_ext}</td>
                <td>{time}</td>
                <td>{info['count']}</td>
                <td>{days_str}</td>
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
                    <th>Story Days</th>
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
            
            story_days = info.get('story_days', [])
            days_str = ', '.join([f'D{d}' for d in sorted(story_days)]) if story_days else '—'
            
            rows.append(f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{info['count']}</td>
                <td>{days_str}</td>
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
                    <th>Story Days</th>
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
        user_items_map = data.get('user_items_by_scene', {})
        rows = []
        prev_story_day = None
        
        for scene in scenes:
            scene_id = scene.get('id') or scene.get('scene_id')
            scene_user = user_items_map.get(scene_id, {})
            all_chars = list(scene.get('characters') or []) + list(scene_user.get('characters') or [])
            chars = ', '.join(all_chars[:3])
            if len(all_chars) > 3:
                chars += f" +{len(all_chars) - 3}"
            
            # Scene length in eighths
            eighths = scene.get('page_length_eighths', 8)
            length_display = format_eighths(eighths)
            
            # Story day separator
            scene_story_day = scene.get('story_day')
            story_day_display = f"D{scene_story_day}" if scene_story_day else '—'
            if scene_story_day and scene_story_day != prev_story_day:
                day_label = scene.get('story_day_label') or f'Day {scene_story_day}'
                rows.append(f"""
                <tr class="day-separator-row">
                    <td colspan="7" class="day-separator-cell">
                        <strong>{day_label}</strong>
                    </td>
                </tr>
                """)
            prev_story_day = scene_story_day
            
            rows.append(f"""
            <tr class="one-liner-row">
                <td class="scene-num">{scene.get('scene_number', '')}</td>
                <td class="int-ext">{scene.get('int_ext', '')}</td>
                <td class="setting">{scene.get('setting', '')}</td>
                <td class="time">{scene.get('time_of_day', '')}</td>
                <td class="day-cell">{story_day_display}</td>
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
                    <th>Day</th>
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
                    <span class="label">Story Days</span>
                    <span class="value">{summary.get('total_story_days', 0)}</span>
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
        
        /* Story Day cells */
        .day-cell {
            width: 45px;
            text-align: center;
            font-weight: 700;
            font-size: 8pt;
            color: #0d9488;
        }
        
        .day-separator-row td {
            background: #e8f5f3 !important;
            padding: 4px 8px;
            border-left: 3px solid #14b8a6;
            font-size: 8pt;
            font-weight: 700;
            color: #0d9488;
            text-transform: uppercase;
            letter-spacing: 0.5px;
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
        
        /* Grouped report styles */
        .report-group {
            margin-bottom: 2rem;
            page-break-inside: avoid;
        }
        
        .report-group + .page-break + .report-group {
            page-break-before: always;
        }
        
        .group-header {
            font-size: 13pt;
            font-weight: 700;
            color: #1a1a1a;
            background: #f0f4f8;
            padding: 10px 14px;
            margin: 0 0 4px 0;
            border-left: 4px solid #4f46e5;
            page-break-after: avoid;
        }
        
        .group-meta {
            font-size: 8.5pt;
            color: #666;
            margin: 0 0 0.75rem 0;
            padding: 0 0 0 18px;
        }
        
        .grouped-breakdown {
            font-size: 8.5pt;
            line-height: 1.5;
        }
        
        .grouped-breakdown strong {
            color: #555;
        }
        
        .grouped-table {
            margin-top: 0;
        }
        
        .filter-note {
            font-size: 9pt;
            color: #b45309;
            font-style: italic;
            margin: 0.25rem 0 0.75rem 0;
        }
        
        .category-note {
            font-size: 8.5pt;
            color: #666;
            margin: 0 0 1rem 0;
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
    # Grouped Report Renderer
    # ============================================
    
    def _render_grouped_report(self, data: Dict, group_by: str, categories: Optional[List[str]] = None) -> str:
        """
        Render a report grouped by a dimension (location, character, story_day).
        Only selected categories are shown in each group's breakdown table.
        """
        scenes = data.get('scenes', [])
        user_items_map = data.get('user_items_by_scene', {})
        
        # Default categories if none specified
        all_categories = ['characters', 'props', 'wardrobe', 'makeup', 'special_effects', 'vehicles', 'animals', 'extras', 'stunts']
        active_cats = categories if categories else all_categories
        
        # Category display labels
        cat_labels = {
            'characters': 'Characters', 'props': 'Props', 'wardrobe': 'Wardrobe',
            'makeup': 'Makeup/Hair', 'special_effects': 'Special FX',
            'vehicles': 'Vehicles', 'animals': 'Animals', 'extras': 'Extras', 'stunts': 'Stunts'
        }
        
        def merge_items(scene, scene_user, category):
            """Merge AI + user items for a given category."""
            ai_key = category
            user_key = category if category != 'special_effects' else 'special_fx'
            ai_items = scene.get(ai_key) or []
            user_items = scene_user.get(category, scene_user.get(user_key, [])) or []
            combined = list(ai_items) + list(user_items)
            return [item if isinstance(item, str) else item.get('name', str(item)) for item in combined]
        
        # Build groups based on dimension
        groups = {}  # key -> { 'label': str, 'meta': str, 'scenes': [scene_dicts] }
        
        if group_by == 'location':
            for scene in scenes:
                setting = scene.get('setting', 'UNKNOWN')
                if setting not in groups:
                    groups[setting] = {
                        'scenes': [],
                        'int_ext': set(),
                        'time_of_day': set(),
                        'story_days': set()
                    }
                groups[setting]['scenes'].append(scene)
                groups[setting]['int_ext'].add(scene.get('int_ext', ''))
                groups[setting]['time_of_day'].add(scene.get('time_of_day', ''))
                if scene.get('story_day'):
                    groups[setting]['story_days'].add(scene['story_day'])
            
            # Sort by scene count descending
            sorted_keys = sorted(groups.keys(), key=lambda k: len(groups[k]['scenes']), reverse=True)
        
        elif group_by == 'character':
            # Build character -> scenes mapping
            char_scenes = {}
            for scene in scenes:
                scene_id = scene.get('id') or scene.get('scene_id')
                scene_user = user_items_map.get(scene_id, {})
                all_chars = merge_items(scene, scene_user, 'characters')
                for char_name in all_chars:
                    if char_name not in char_scenes:
                        char_scenes[char_name] = {
                            'scenes': [],
                            'int_ext': set(),
                            'time_of_day': set(),
                            'story_days': set()
                        }
                    # Avoid duplicate scenes for same character
                    scene_nums = [s.get('scene_number') for s in char_scenes[char_name]['scenes']]
                    if scene.get('scene_number') not in scene_nums:
                        char_scenes[char_name]['scenes'].append(scene)
                        char_scenes[char_name]['int_ext'].add(scene.get('int_ext', ''))
                        char_scenes[char_name]['time_of_day'].add(scene.get('time_of_day', ''))
                        if scene.get('story_day'):
                            char_scenes[char_name]['story_days'].add(scene['story_day'])
            
            groups = char_scenes
            sorted_keys = sorted(groups.keys(), key=lambda k: len(groups[k]['scenes']), reverse=True)
        
        elif group_by == 'story_day':
            for scene in scenes:
                day = scene.get('story_day') or 0
                day_key = f"Day {day}" if day else "Unassigned"
                if day_key not in groups:
                    groups[day_key] = {
                        'scenes': [],
                        'int_ext': set(),
                        'time_of_day': set(),
                        'story_days': {day} if day else set(),
                        'sort_key': day
                    }
                groups[day_key]['scenes'].append(scene)
                groups[day_key]['int_ext'].add(scene.get('int_ext', ''))
                groups[day_key]['time_of_day'].add(scene.get('time_of_day', ''))
            
            sorted_keys = sorted(groups.keys(), key=lambda k: groups[k].get('sort_key', 0))
        
        else:
            # Default: scene_number — just render the standard breakdown
            return self._render_scene_breakdown(data)
        
        # Render each group
        group_sections = []
        for key in sorted_keys:
            group = groups[key]
            group_scenes = group['scenes']
            scene_count = len(group_scenes)
            
            # Build meta line
            meta_parts = [f"{scene_count} scene{'s' if scene_count != 1 else ''}"]
            int_ext_vals = sorted([v for v in group.get('int_ext', set()) if v])
            if int_ext_vals:
                meta_parts.append('/'.join(int_ext_vals))
            tod_vals = sorted([v for v in group.get('time_of_day', set()) if v])
            if tod_vals:
                meta_parts.append('/'.join(tod_vals))
            story_days = sorted(group.get('story_days', set()))
            if story_days:
                meta_parts.append('Story Days: ' + ', '.join(f'D{d}' for d in story_days))
            
            meta_str = ' · '.join(meta_parts)
            
            # Build breakdown rows for scenes in this group
            rows = []
            for scene in group_scenes:
                scene_id = scene.get('id') or scene.get('scene_id')
                scene_user = user_items_map.get(scene_id, {})
                
                # Collect items per active category
                cat_cells = []
                for cat in active_cats:
                    items = merge_items(scene, scene_user, cat)
                    if items:
                        cat_cells.append(f"<strong>{cat_labels.get(cat, cat)}:</strong> {', '.join(items)}")
                
                breakdown_str = '<br>'.join(cat_cells) if cat_cells else '—'
                
                eighths = scene.get('page_length_eighths', 8)
                length_display = format_eighths(eighths)
                story_day_display = f"D{scene.get('story_day')}" if scene.get('story_day') else '—'
                
                rows.append(f"""
                <tr>
                    <td class="scene-num"><strong>{scene.get('scene_number', '')}</strong></td>
                    <td class="int-ext">{scene.get('int_ext', '')}</td>
                    <td class="setting">{scene.get('setting', '')}</td>
                    <td class="time">{scene.get('time_of_day', '')}</td>
                    <td class="day-cell">{story_day_display}</td>
                    <td class="length-cell">{length_display}</td>
                </tr>
                <tr class="breakdown-details">
                    <td colspan="6">
                        <div class="grouped-breakdown">{breakdown_str}</div>
                    </td>
                </tr>
                """)
            
            group_sections.append(f"""
            <div class="report-group">
                <h3 class="group-header">{key}</h3>
                <p class="group-meta">{meta_str}</p>
                <table class="breakdown-table grouped-table">
                    <thead>
                        <tr>
                            <th>Scene</th>
                            <th>I/E</th>
                            <th>Setting</th>
                            <th>D/N</th>
                            <th>Day</th>
                            <th>Length</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
            """)
        
        group_label = {'location': 'Location', 'character': 'Character', 'story_day': 'Story Day'}.get(group_by, group_by)
        filter_note = ''
        filter_summary = data.get('filter_summary', {})
        if filter_summary.get('is_filtered'):
            filter_note = f'<p class="filter-note">Filtered: showing {filter_summary["total_scenes_filtered"]} of {filter_summary["total_scenes_unfiltered"]} scenes</p>'
        
        cat_note = ''
        if categories and len(categories) < len(all_categories):
            cat_note = f'<p class="category-note">Categories: {", ".join(cat_labels.get(c, c) for c in active_cats)}</p>'
        
        return f"""
        <h2>Grouped by {group_label}</h2>
        {filter_note}
        {cat_note}
        {'<div class="page-break"></div>'.join(group_sections)}
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


# Singleton instance
report_service = ReportService()
