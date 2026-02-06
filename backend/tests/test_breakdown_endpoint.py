"""
Tests for the scene breakdown endpoint and ReportService enrichment.

Tests:
1. _extraction_class_to_category mapping
2. Breakdown endpoint grouping logic
3. ReportService._enrich_with_extraction_metadata
4. New report type renderers handle missing data gracefully
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from collections import defaultdict

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


# ============================================
# 1. Test extraction_class_to_category mapping
# ============================================

def test_extraction_class_to_category():
    """Verify the mapping from extraction_class to SceneDetail category key."""
    from routes.langextract_routes import _extraction_class_to_category
    
    assert _extraction_class_to_category('character') == 'characters'
    assert _extraction_class_to_category('prop') == 'props'
    assert _extraction_class_to_category('wardrobe') == 'wardrobe'
    assert _extraction_class_to_category('makeup_hair') == 'makeup_hair'
    assert _extraction_class_to_category('special_fx') == 'special_fx'
    assert _extraction_class_to_category('vehicle') == 'vehicles'
    assert _extraction_class_to_category('location_detail') == 'locations'
    assert _extraction_class_to_category('sound') == 'sound'
    assert _extraction_class_to_category('scene_header') is None
    # Unknown classes pass through
    assert _extraction_class_to_category('unknown_class') == 'unknown_class'
    
    print("✓ _extraction_class_to_category mapping correct")


# ============================================
# 2. Test breakdown grouping logic
# ============================================

def test_breakdown_grouping():
    """Test that extractions are grouped into breakdown vs enrichment correctly."""
    mock_extractions = [
        {'id': '1', 'extraction_class': 'character', 'extraction_text': 'JOHN', 'attributes': {'name': 'JOHN'}, 'confidence': 0.95, 'text_start': 0, 'text_end': 4},
        {'id': '2', 'extraction_class': 'prop', 'extraction_text': 'Laptop', 'attributes': {'item_name': 'Laptop'}, 'confidence': 0.88, 'text_start': 10, 'text_end': 16},
        {'id': '3', 'extraction_class': 'emotion', 'extraction_text': 'Anxiety', 'attributes': {'intensity': 'high'}, 'confidence': 0.80, 'text_start': 20, 'text_end': 27},
        {'id': '4', 'extraction_class': 'dialogue', 'extraction_text': 'Hello world', 'attributes': {'tone': 'casual'}, 'confidence': 0.92, 'text_start': 30, 'text_end': 41},
        {'id': '5', 'extraction_class': 'relationship', 'extraction_text': 'Father-son', 'attributes': {'dynamic': 'tense'}, 'confidence': 0.85, 'text_start': 50, 'text_end': 60},
        {'id': '6', 'extraction_class': 'vehicle', 'extraction_text': 'Red Mustang', 'attributes': {}, 'confidence': 0.90, 'text_start': 70, 'text_end': 81},
    ]
    
    from routes.langextract_routes import _extraction_class_to_category
    
    breakdown = {}
    enrichment = {}
    
    for ext in mock_extractions:
        cls = ext.get('extraction_class', 'unknown')
        item = {
            'id': ext['id'],
            'text': ext.get('extraction_text', ''),
            'attributes': ext.get('attributes', {}),
            'confidence': ext.get('confidence', 1.0),
        }
        
        if cls in ('emotion', 'relationship', 'transition', 'dialogue', 'action'):
            if cls not in enrichment:
                enrichment[cls] = []
            enrichment[cls].append(item)
        else:
            category_key = _extraction_class_to_category(cls)
            if category_key:
                if category_key not in breakdown:
                    breakdown[category_key] = []
                breakdown[category_key].append(item)
    
    # Verify breakdown categories
    assert 'characters' in breakdown
    assert len(breakdown['characters']) == 1
    assert breakdown['characters'][0]['text'] == 'JOHN'
    
    assert 'props' in breakdown
    assert len(breakdown['props']) == 1
    
    assert 'vehicles' in breakdown
    assert len(breakdown['vehicles']) == 1
    
    # Verify enrichment categories
    assert 'emotion' in enrichment
    assert len(enrichment['emotion']) == 1
    assert enrichment['emotion'][0]['text'] == 'Anxiety'
    
    assert 'dialogue' in enrichment
    assert len(enrichment['dialogue']) == 1
    
    assert 'relationship' in enrichment
    assert len(enrichment['relationship']) == 1
    
    # scene_header mapped to None should NOT appear in breakdown
    assert 'scene_header' not in breakdown
    
    print("✓ Breakdown grouping logic correct")


# ============================================
# 3. Test ReportService enrichment
# ============================================

def test_report_service_enrichment_with_empty_extractions():
    """Test that enrichment gracefully handles empty extraction_metadata."""
    from services.report_service import ReportService
    
    service = ReportService()
    
    # Mock db client
    mock_response = MagicMock()
    mock_response.data = []
    
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.execute.return_value = mock_response
    
    service.db = MagicMock()
    service.db.client.table.return_value = mock_table
    
    data = {
        'characters': {'JOHN': {'count': 2, 'scenes': ['1', '3']}},
        'props': {},
        'wardrobe': {},
        'summary': {}
    }
    
    result = service._enrich_with_extraction_metadata('test-id', [], data)
    
    # Should return data unchanged (no extractions to enrich with)
    assert result['characters']['JOHN']['count'] == 2
    assert 'enrichment' not in result  # no enrichment added when empty
    
    print("✓ Enrichment with empty extractions works correctly")


def test_report_service_enrichment_adds_rich_attributes():
    """Test that enrichment adds rich attributes to existing categories."""
    from services.report_service import ReportService
    
    service = ReportService()
    
    mock_extractions = [
        {'id': '1', 'extraction_class': 'character', 'extraction_text': 'JOHN', 
         'attributes': {'name': 'JOHN', 'role': 'protagonist'}, 'confidence': 0.95, 'scene_id': 's1'},
        {'id': '2', 'extraction_class': 'dialogue', 'extraction_text': 'Hello there', 
         'attributes': {'character': 'JOHN', 'tone': 'friendly'}, 'confidence': 0.90, 'scene_id': 's1'},
        {'id': '3', 'extraction_class': 'emotion', 'extraction_text': 'joy', 
         'attributes': {'intensity': 'high'}, 'confidence': 0.85, 'scene_id': 's1'},
    ]
    
    mock_response = MagicMock()
    mock_response.data = mock_extractions
    
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.execute.return_value = mock_response
    
    service.db = MagicMock()
    service.db.client.table.return_value = mock_table
    
    scenes = [{'id': 's1', 'scene_number': '1'}]
    data = {
        'characters': {'JOHN': {'count': 1, 'scenes': ['1']}},
        'props': {},
        'wardrobe': {},
        'summary': {}
    }
    
    result = service._enrich_with_extraction_metadata('test-id', scenes, data)
    
    # Should have rich_attributes on JOHN
    assert 'rich_attributes' in result['characters']['JOHN']
    assert result['characters']['JOHN']['rich_attributes'][0]['role'] == 'protagonist'
    
    # Should have enrichment section
    assert 'enrichment' in result
    assert len(result['enrichment']['dialogue']) == 1
    assert result['enrichment']['dialogue'][0]['tone'] == 'friendly'
    assert result['enrichment']['emotions']['joy']['count'] == 1
    
    # Summary should be updated
    assert result['summary']['has_rich_data'] is True
    assert result['summary']['total_dialogue_lines'] == 1
    assert result['summary']['total_emotions'] == 1
    
    print("✓ Enrichment adds rich attributes correctly")


# ============================================
# 4. Test new report renderers handle no data
# ============================================

def test_dialogue_report_no_data():
    """Dialogue report shows message when no enrichment data."""
    from services.report_service import ReportService
    
    service = ReportService()
    data = {'enrichment': {}}
    
    html = service._render_dialogue_report(data)
    assert 'No dialogue data available' in html
    
    print("✓ Dialogue report handles no data")


def test_sound_cues_report_no_data():
    """Sound cues report shows message when no enrichment data."""
    from services.report_service import ReportService
    
    service = ReportService()
    data = {'enrichment': {}}
    
    html = service._render_sound_cues_report(data)
    assert 'No sound cue data available' in html
    
    print("✓ Sound cues report handles no data")


def test_emotional_arc_report_no_data():
    """Emotional arc report shows message when no enrichment data."""
    from services.report_service import ReportService
    
    service = ReportService()
    data = {'enrichment': {}}
    
    html = service._render_emotional_arc_report(data)
    assert 'No emotional data available' in html
    
    print("✓ Emotional arc report handles no data")


def test_continuity_report_no_data():
    """Continuity report shows message when no data."""
    from services.report_service import ReportService
    
    service = ReportService()
    data = {'props': {}, 'wardrobe': {}, 'makeup': {}}
    
    html = service._render_continuity_report(data)
    assert 'No continuity data available' in html
    
    print("✓ Continuity report handles no data")


def test_dialogue_report_renders_grouped_by_character():
    """Dialogue report groups lines by character."""
    from services.report_service import ReportService
    
    service = ReportService()
    data = {
        'enrichment': {
            'dialogue': [
                {'text': 'Hello', 'character': 'JOHN', 'tone': 'casual', 'scene': '1', 'confidence': 0.9},
                {'text': 'Goodbye', 'character': 'JOHN', 'tone': 'sad', 'scene': '3', 'confidence': 0.85},
                {'text': 'Welcome', 'character': 'SARAH', 'tone': 'warm', 'scene': '2', 'confidence': 0.92},
            ],
            'total_dialogue_lines': 3
        }
    }
    
    html = service._render_dialogue_report(data)
    assert 'JOHN' in html
    assert 'SARAH' in html
    assert 'casual' in html
    assert '3 dialogue lines across 2 characters' in html
    
    print("✓ Dialogue report renders grouped by character")


# ============================================
# Run all tests
# ============================================

if __name__ == '__main__':
    print("Running breakdown endpoint & ReportService tests...\n")
    
    test_extraction_class_to_category()
    test_breakdown_grouping()
    test_report_service_enrichment_with_empty_extractions()
    test_report_service_enrichment_adds_rich_attributes()
    test_dialogue_report_no_data()
    test_sound_cues_report_no_data()
    test_emotional_arc_report_no_data()
    test_continuity_report_no_data()
    test_dialogue_report_renders_grouped_by_character()
    
    print("\n✅ All tests passed!")
