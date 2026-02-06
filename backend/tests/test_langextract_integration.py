"""
Integration Tests for LangExtract Implementation
Tests the complete flow from extraction to database storage to API access.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.langextract_service import (
    extract_with_langextract,
    save_extractions_to_supabase,
    generate_visualization,
    get_extractions_by_class,
    get_extraction_stats
)


# Sample screenplay text for testing
SAMPLE_SCRIPT = """INT. COFFEE SHOP - DAY

JANE WILLIAMS (30s, exhausted) enters carrying a worn briefcase. She spots DETECTIVE MORGAN at a corner table.

JANE
(nervously)
You wanted to see me?

DETECTIVE MORGAN
(coldly)
Sit down, Miss Williams.

Jane pulls out a VINTAGE PHOTOGRAPH from her briefcase and slides it across the table.

JANE
This is what you're looking for.

The detective examines the photo - a black and white image of a woman in 1940s clothing.
"""


class TestLangExtractService:
    """Test LangExtract service functions."""
    
    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        mock = MagicMock()
        mock.table.return_value.insert.return_value.execute.return_value.data = [{'id': 'test-id'}]
        mock.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        return mock
    
    @pytest.fixture
    def sample_extractions(self):
        """Sample extraction data."""
        return [
            {
                'extraction_class': 'scene_header',
                'extraction_text': 'INT. COFFEE SHOP - DAY',
                'text_start': 0,
                'text_end': 23,
                'attributes': {
                    'int_ext': 'INT',
                    'setting': 'COFFEE SHOP',
                    'time_of_day': 'DAY'
                },
                'confidence': 1.0
            },
            {
                'extraction_class': 'character',
                'extraction_text': 'JANE WILLIAMS (30s, exhausted)',
                'text_start': 25,
                'text_end': 55,
                'attributes': {
                    'name': 'JANE WILLIAMS',
                    'emotional_state': 'exhausted',
                    'first_appearance': 'true'
                },
                'confidence': 0.95
            },
            {
                'extraction_class': 'prop',
                'extraction_text': 'worn briefcase',
                'text_start': 73,
                'text_end': 87,
                'attributes': {
                    'item_name': 'briefcase',
                    'character_using': 'JANE WILLIAMS',
                    'condition': 'worn',
                    'importance': 'character_defining'
                },
                'confidence': 0.9
            },
            {
                'extraction_class': 'dialogue',
                'extraction_text': 'You wanted to see me?',
                'text_start': 150,
                'text_end': 171,
                'attributes': {
                    'character': 'JANE',
                    'tone': 'nervous',
                    'parenthetical': 'nervously'
                },
                'confidence': 1.0
            }
        ]
    
    def test_extract_with_langextract_requires_api_key(self):
        """Test that extraction fails without GOOGLE_API_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GOOGLE_API_KEY not found"):
                extract_with_langextract("test text")
    
    @patch('services.langextract_service.LangExtract')
    def test_extract_with_langextract_success(self, mock_langextract_class):
        """Test successful extraction."""
        # Mock LangExtract instance
        mock_extractor = MagicMock()
        mock_result = MagicMock()
        mock_result.extraction_class = 'scene_header'
        mock_result.extraction_text = 'INT. TEST - DAY'
        mock_result.text_start = 0
        mock_result.text_end = 15
        mock_result.attributes = {'int_ext': 'INT'}
        mock_result.confidence = 1.0
        
        mock_extractor.extract.return_value = [mock_result]
        mock_langextract_class.return_value = mock_extractor
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            results = extract_with_langextract("INT. TEST - DAY")
        
        assert len(results) == 1
        assert results[0]['extraction_class'] == 'scene_header'
        assert results[0]['extraction_text'] == 'INT. TEST - DAY'
        assert results[0]['text_start'] == 0
        assert results[0]['text_end'] == 15
    
    def test_save_extractions_to_supabase(self, mock_supabase, sample_extractions):
        """Test saving extractions to Supabase."""
        script_id = 'test-script-123'
        
        count = save_extractions_to_supabase(script_id, sample_extractions, mock_supabase)
        
        # Verify insert was called
        mock_supabase.table.assert_called_with('extraction_metadata')
        assert count >= 0  # Should return count of saved records
    
    def test_save_extractions_empty_list(self, mock_supabase):
        """Test saving empty extractions list."""
        count = save_extractions_to_supabase('test-id', [], mock_supabase)
        assert count == 0
    
    def test_get_extractions_by_class(self, mock_supabase, sample_extractions):
        """Test retrieving extractions by class."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            sample_extractions[0]
        ]
        
        results = get_extractions_by_class('test-id', 'scene_header', mock_supabase)
        
        assert len(results) == 1
        assert results[0]['extraction_class'] == 'scene_header'
    
    def test_get_extraction_stats(self, mock_supabase, sample_extractions):
        """Test extraction statistics calculation."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = sample_extractions
        
        stats = get_extraction_stats('test-id', mock_supabase)
        
        assert 'scene_header' in stats
        assert 'character' in stats
        assert 'prop' in stats
        assert 'dialogue' in stats
        
        # Check counts
        assert stats['scene_header']['count'] == 1
        assert stats['character']['count'] == 1
        
        # Check average confidence
        assert 0.0 <= stats['scene_header']['avg_confidence'] <= 1.0
    
    # test_aggregate_extractions_to_scenes removed — function deprecated in SSoT refactor.
    # See docs/rich_update.md for migration details.


class TestLangExtractIntegration:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def mock_supabase_full(self):
        """Create a full mock Supabase client for integration testing."""
        mock = MagicMock()
        
        # Mock script query
        mock.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'test-script-123',
            'full_text': SAMPLE_SCRIPT
        }
        
        # Mock insert operations
        mock.table.return_value.insert.return_value.execute.return_value.data = [{'id': 'inserted-id'}]
        
        # Mock update operations
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        return mock
    
    @patch('services.langextract_service.LangExtract')
    def test_full_extraction_pipeline(self, mock_langextract_class, mock_supabase_full):
        """Test the complete extraction pipeline."""
        from services.script_service import process_script_with_langextract
        
        # Mock LangExtract to return sample extractions
        mock_extractor = MagicMock()
        mock_results = []
        
        for i in range(5):
            mock_result = MagicMock()
            mock_result.extraction_class = 'dialogue'
            mock_result.extraction_text = f'Test line {i}'
            mock_result.text_start = i * 10
            mock_result.text_end = i * 10 + 10
            mock_result.attributes = {'character': 'TEST'}
            mock_result.confidence = 0.9
            mock_results.append(mock_result)
        
        mock_extractor.extract.return_value = mock_results
        mock_langextract_class.return_value = mock_extractor
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('services.langextract_service.create_html_visualization', return_value='<html>test</html>'):
                result = process_script_with_langextract(
                    'test-script-123',
                    SAMPLE_SCRIPT,
                    mock_supabase_full
                )
        
        assert result['success'] is True
        assert result['extractions_count'] == 5
        assert 'visualization_size' in result


class TestLangExtractAPI:
    """Test API endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create Flask test app."""
        from app import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @patch('routes.langextract_routes.get_supabase_client')
    def test_get_extractions_endpoint(self, mock_get_client, client):
        """Test GET /api/scripts/:id/extractions endpoint."""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {
                'id': '1',
                'extraction_class': 'dialogue',
                'extraction_text': 'Test',
                'text_start': 0,
                'text_end': 4
            }
        ]
        mock_get_client.return_value = mock_supabase
        
        response = client.get('/api/scripts/test-id/extractions')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'extractions' in data
        assert data['script_id'] == 'test-id'
    
    @patch('routes.langextract_routes.get_supabase_client')
    def test_get_extraction_stats_endpoint(self, mock_get_client, client):
        """Test GET /api/scripts/:id/extractions/stats endpoint."""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {'extraction_class': 'dialogue', 'confidence': 0.9},
            {'extraction_class': 'dialogue', 'confidence': 0.95}
        ]
        mock_get_client.return_value = mock_supabase
        
        response = client.get('/api/scripts/test-id/extractions/stats')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_extractions' in data
        assert 'by_class' in data


class TestWeek2Features:
    """Test Week 2 enhancements: SSE, error recovery, retry, cancellation."""
    
    @patch('services.langextract_service.LangExtract')
    def test_extract_with_progress_callback(self, mock_langextract_class):
        """Test extraction with progress callback."""
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = []
        mock_langextract_class.return_value = mock_extractor
        
        progress_updates = []
        def progress_callback(percentage, message):
            progress_updates.append({'percentage': percentage, 'message': message})
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            result = extract_with_langextract(
                "test text",
                progress_callback=progress_callback
            )
        
        # Verify progress callbacks were called
        assert len(progress_updates) > 0
        assert any(u['percentage'] == 5 for u in progress_updates)  # Initialization
        assert any(u['percentage'] == 100 for u in progress_updates)  # Completion
    
    @patch('services.langextract_service.LangExtract')
    def test_extract_with_retry_on_failure(self, mock_langextract_class):
        """Test retry logic with exponential backoff."""
        mock_extractor = MagicMock()
        
        # Fail twice, then succeed
        mock_extractor.extract.side_effect = [
            Exception("API rate limit"),
            Exception("Temporary error"),
            [MagicMock(extraction_class='test', extraction_text='test', text_start=0, text_end=4, attributes={}, confidence=1.0)]
        ]
        mock_langextract_class.return_value = mock_extractor
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = extract_with_langextract("test text", max_retries=3)
        
        # Should succeed after retries
        assert result['stats']['total_extractions'] == 1
        assert mock_extractor.extract.call_count == 3
    
    @patch('services.langextract_service.LangExtract')
    def test_extract_with_partial_failure(self, mock_langextract_class):
        """Test error recovery with partial extraction failures."""
        mock_extractor = MagicMock()
        
        # Return some valid results
        mock_result = MagicMock()
        mock_result.extraction_class = 'dialogue'
        mock_result.extraction_text = 'Test'
        mock_result.text_start = 0
        mock_result.text_end = 4
        mock_result.attributes = {}
        mock_result.confidence = 1.0
        
        mock_extractor.extract.return_value = [mock_result]
        mock_langextract_class.return_value = mock_extractor
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            result = extract_with_langextract("test text")
        
        # Should have extractions and stats
        assert 'extractions' in result
        assert 'stats' in result
        assert 'errors' in result
        assert result['stats']['total_extractions'] == 1
        assert result['stats']['success_rate'] > 0
    
    @patch('services.langextract_service.LangExtract')
    def test_extract_with_scene_linking(self, mock_langextract_class):
        """Test automatic scene_id linking during save."""
        mock_extractor = MagicMock()
        mock_result = MagicMock()
        mock_result.extraction_class = 'dialogue'
        mock_result.extraction_text = 'Test'
        mock_result.text_start = 100
        mock_result.text_end = 104
        mock_result.attributes = {}
        mock_result.confidence = 1.0
        
        mock_extractor.extract.return_value = [mock_result]
        mock_langextract_class.return_value = mock_extractor
        
        # Mock Supabase with scene boundaries
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {'id': 'scene-1', 'text_start': 0, 'text_end': 200}
        ]
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{'id': 'extraction-1'}]
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            result = extract_with_langextract("test text")
            count = save_extractions_to_supabase(
                'test-script',
                result['extractions'],
                mock_supabase,
                link_to_scenes=True
            )
        
        assert count == 1
    
    def test_sse_stream_endpoint(self, client):
        """Test SSE streaming endpoint for real-time progress."""
        with patch('routes.langextract_routes.get_supabase_client'):
            with patch('routes.langextract_routes.SupabaseDB'):
                with patch('routes.langextract_routes.extract_with_langextract'):
                    response = client.post('/api/scripts/test-id/process-langextract-stream')
                    
                    # Should return SSE stream
                    assert response.status_code == 200
                    assert response.mimetype == 'text/event-stream'
    
    def test_cancellation_endpoint(self, client):
        """Test extraction cancellation endpoint."""
        from routes.langextract_routes import _active_extractions
        
        # Add active extraction
        _active_extractions['test-id'] = {'cancelled': False}
        
        with patch('routes.langextract_routes.get_supabase_client'):
            with patch('routes.langextract_routes.SupabaseDB'):
                response = client.post('/api/scripts/test-id/extractions/cancel')
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['status'] == 'cancelled'
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        return app.test_client()
    
    def test_configuration_loading(self):
        """Test configuration loading from environment."""
        from config.langextract_config import get_config, reload_config
        
        with patch.dict(os.environ, {
            'LANGEXTRACT_CHUNK_SIZE': '3000',
            'LANGEXTRACT_MAX_WORKERS': '15',
            'LANGEXTRACT_MAX_RETRIES': '5'
        }):
            config = reload_config()
            
            assert config.chunk_size == 3000
            assert config.max_workers == 15
            assert config.max_retries == 5
    
    def test_performance_metrics_collection(self):
        """Test performance metrics are collected and stored."""
        from services.langextract_service import save_performance_metrics
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            'id': 'job-1',
            'status': 'completed',
            'result_data': {}
        }
        
        metrics = {
            'total_extractions': 100,
            'elapsed_time': 45.2,
            'success_rate': 98.5
        }
        
        with patch('services.langextract_service.SupabaseDB'):
            result = save_performance_metrics(
                'script-1',
                'job-1',
                metrics,
                mock_supabase
            )
        
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
