# Report Configuration Schema

## Overview
Flexible configuration system for controlling PDF report content, enabling department-specific reports and customizable exports.

**Date**: 2026-02-02  
**Phase**: 3 - Department Views & Configuration

---

## Configuration Object Structure

```python
{
    # Report Type
    "report_type": "full_breakdown|scene_breakdown|wardrobe|props|makeup|sfx|stunts|vehicles|animals|extras|custom",
    
    # Included Breakdown Categories (array of strings)
    "include_categories": [
        "characters",
        "props", 
        "wardrobe",
        "makeup",
        "special_effects",
        "stunts",
        "vehicles",
        "animals",
        "extras",
        "locations",
        "sound"
    ],
    
    # Excluded Categories (takes precedence over include)
    "exclude_categories": [],
    
    # Metadata Fields to Include
    "include_metadata": {
        "script_title": true,
        "writer_name": true,
        "draft_version": true,
        "production_company": true,
        "contact_info": true,
        "copyright_info": true,
        "additional_credits": true,
        "total_pages": true
    },
    
    # Scene Description Fields
    "include_descriptions": {
        "description": true,
        "action_description": true,
        "emotional_tone": true,
        "technical_notes": true,
        "sound_notes": true,
        "atmosphere": true
    },
    
    # Summary Statistics
    "include_summary": true,
    
    # Cross-References (show which scenes each item appears in)
    "show_cross_references": true,
    
    # Grouping Options
    "group_by": null,  # null|"department"|"scene"|"character"|"location"
    
    # Sorting Options
    "sort_by": "scene_number",  # "scene_number"|"alphabetical"|"frequency"
    
    # Filter Options
    "filter": {
        "scene_numbers": [],  # Empty = all scenes, or specific scene numbers
        "characters": [],     # Empty = all, or specific character names
        "locations": []       # Empty = all, or specific locations
    },
    
    # Department-Specific Options
    "department_options": {
        "wardrobe": {
            "group_by_character": true,
            "show_continuity_notes": true
        },
        "props": {
            "categorize": true,  # Group by prop type (weapon, food, etc.)
            "show_hero_props": true
        },
        "makeup": {
            "group_by_character": true,
            "show_continuity": true
        },
        "stunts": {
            "show_safety_notes": true,
            "group_by_type": true
        }
    },
    
    # Visual Options
    "visual_options": {
        "color_code_int_ext": true,
        "color_code_day_night": true,
        "show_page_numbers": true,
        "compact_mode": false
    }
}
```

---

## Preset Configurations

### 1. Full Breakdown (Default)
```python
PRESET_FULL_BREAKDOWN = {
    "report_type": "full_breakdown",
    "include_categories": ["all"],
    "include_metadata": {"all": true},
    "include_descriptions": {"all": true},
    "include_summary": true,
    "show_cross_references": false
}
```

### 2. Wardrobe Department
```python
PRESET_WARDROBE = {
    "report_type": "wardrobe",
    "include_categories": ["characters", "wardrobe"],
    "include_metadata": {
        "script_title": true,
        "writer_name": true,
        "production_company": true
    },
    "include_descriptions": {
        "description": true,
        "atmosphere": false
    },
    "include_summary": true,
    "show_cross_references": true,
    "group_by": "character",
    "department_options": {
        "wardrobe": {
            "group_by_character": true,
            "show_continuity_notes": true
        }
    }
}
```

### 3. Props Department
```python
PRESET_PROPS = {
    "report_type": "props",
    "include_categories": ["characters", "props"],
    "include_metadata": {
        "script_title": true,
        "production_company": true
    },
    "include_descriptions": {
        "description": true
    },
    "include_summary": true,
    "show_cross_references": true,
    "group_by": "department",
    "department_options": {
        "props": {
            "categorize": true,
            "show_hero_props": true
        }
    }
}
```

### 4. Makeup & Hair Department
```python
PRESET_MAKEUP = {
    "report_type": "makeup",
    "include_categories": ["characters", "makeup"],
    "include_metadata": {
        "script_title": true,
        "production_company": true
    },
    "include_descriptions": {
        "description": true,
        "emotional_tone": true
    },
    "include_summary": true,
    "show_cross_references": true,
    "group_by": "character",
    "department_options": {
        "makeup": {
            "group_by_character": true,
            "show_continuity": true
        }
    }
}
```

### 5. Special Effects Department
```python
PRESET_SFX = {
    "report_type": "sfx",
    "include_categories": ["special_effects", "technical_notes"],
    "include_metadata": {
        "script_title": true,
        "production_company": true
    },
    "include_descriptions": {
        "description": true,
        "technical_notes": true
    },
    "include_summary": true,
    "show_cross_references": true
}
```

### 6. Stunts Department
```python
PRESET_STUNTS = {
    "report_type": "stunts",
    "include_categories": ["characters", "stunts"],
    "include_metadata": {
        "script_title": true,
        "production_company": true
    },
    "include_descriptions": {
        "description": true,
        "action_description": true,
        "technical_notes": true
    },
    "include_summary": true,
    "show_cross_references": true,
    "department_options": {
        "stunts": {
            "show_safety_notes": true,
            "group_by_type": true
        }
    }
}
```

### 7. Vehicles & Transportation
```python
PRESET_VEHICLES = {
    "report_type": "vehicles",
    "include_categories": ["vehicles", "characters"],
    "include_metadata": {
        "script_title": true,
        "production_company": true
    },
    "include_descriptions": {
        "description": true
    },
    "include_summary": true,
    "show_cross_references": true
}
```

### 8. Animals & Wranglers
```python
PRESET_ANIMALS = {
    "report_type": "animals",
    "include_categories": ["animals", "characters"],
    "include_metadata": {
        "script_title": true,
        "production_company": true
    },
    "include_descriptions": {
        "description": true
    },
    "include_summary": true,
    "show_cross_references": true
}
```

### 9. Extras & Background
```python
PRESET_EXTRAS = {
    "report_type": "extras",
    "include_categories": ["extras", "locations"],
    "include_metadata": {
        "script_title": true,
        "production_company": true
    },
    "include_descriptions": {
        "description": true,
        "atmosphere": true
    },
    "include_summary": true,
    "show_cross_references": true
}
```

---

## Implementation

### Python Class Structure

```python
class ReportConfig:
    """Report configuration with validation and defaults."""
    
    def __init__(self, config_dict=None):
        self.config = self._merge_with_defaults(config_dict or {})
        self._validate()
    
    def _merge_with_defaults(self, config):
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
        return {**defaults, **config}
    
    def _validate(self):
        """Validate configuration values."""
        valid_report_types = [
            "full_breakdown", "scene_breakdown", "wardrobe", "props",
            "makeup", "sfx", "stunts", "vehicles", "animals", "extras", "custom"
        ]
        if self.config["report_type"] not in valid_report_types:
            raise ValueError(f"Invalid report_type: {self.config['report_type']}")
    
    def should_include_category(self, category):
        """Check if a category should be included."""
        if "all" in self.config["include_categories"]:
            return category not in self.config["exclude_categories"]
        return category in self.config["include_categories"]
    
    def should_include_metadata(self, field):
        """Check if a metadata field should be included."""
        metadata = self.config["include_metadata"]
        if metadata.get("all"):
            return True
        return metadata.get(field, False)
    
    def should_include_description(self, field):
        """Check if a description field should be included."""
        descriptions = self.config["include_descriptions"]
        if descriptions.get("all"):
            return True
        return descriptions.get(field, False)
    
    @staticmethod
    def from_preset(preset_name):
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
```

---

## Usage Examples

### 1. Generate Full Breakdown
```python
config = ReportConfig.from_preset("full_breakdown")
report = report_service.generate_report(script_id, config=config)
```

### 2. Generate Wardrobe Report
```python
config = ReportConfig.from_preset("wardrobe")
report = report_service.generate_report(script_id, config=config)
```

### 3. Custom Configuration
```python
config = ReportConfig({
    "report_type": "custom",
    "include_categories": ["props", "vehicles", "special_effects"],
    "include_metadata": {
        "script_title": True,
        "production_company": True
    },
    "show_cross_references": True
})
report = report_service.generate_report(script_id, config=config)
```

### 4. Filtered Report (Specific Scenes)
```python
config = ReportConfig({
    "report_type": "full_breakdown",
    "filter": {
        "scene_numbers": ["1", "2", "5", "10A"]
    }
})
report = report_service.generate_report(script_id, config=config)
```

---

## API Integration

### Generate Report Endpoint
```python
POST /api/scripts/{script_id}/reports/generate
Content-Type: application/json

{
    "report_type": "wardrobe",
    "title": "Wardrobe Breakdown",
    "config": {
        "include_categories": ["characters", "wardrobe"],
        "show_cross_references": true,
        "group_by": "character"
    }
}
```

### Response
```python
{
    "report_id": "uuid",
    "title": "Wardrobe Breakdown",
    "report_type": "wardrobe",
    "status": "completed",
    "pdf_url": "/api/reports/{report_id}/pdf",
    "generated_at": "2026-02-02T19:45:00Z"
}
```

---

## Database Storage

### reports Table Extension
```sql
ALTER TABLE reports ADD COLUMN config JSONB DEFAULT '{}'::jsonb;
CREATE INDEX idx_reports_config_gin ON reports USING GIN (config);

-- Query reports by configuration
SELECT * FROM reports 
WHERE config->>'report_type' = 'wardrobe'
AND script_id = 'uuid';
```

---

## Benefits

1. **Flexibility**: Users can create custom reports with exactly the data they need
2. **Department Focus**: Each department gets relevant data without clutter
3. **Reusability**: Save and reuse configurations as templates
4. **Performance**: Smaller reports with filtered data generate faster
5. **Scalability**: Easy to add new configuration options without breaking changes

---

## Future Enhancements

1. **User Templates**: Allow users to save custom configurations
2. **Team Sharing**: Share report configurations across team members
3. **Version Control**: Track configuration changes over time
4. **Conditional Logic**: Advanced rules (e.g., "include wardrobe only if character count > 5")
5. **Export Formats**: Support multiple formats (PDF, Excel, CSV) with same config
