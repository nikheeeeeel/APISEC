"""
Unit tests for enhanced endpoint classifier functionality.

Tests endpoint classification with mock data to ensure
accurate API type identification without network dependencies.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

def _run(coro):
    """Run async coroutine from sync test."""
    return asyncio.run(coro)
from classification.endpoint_classifier import (
    EnhancedEndpointClassifier,
    EndpointType,
    create_enhanced_classifier
)
from models import DiscoveryRequest, DiscoveryContext
from scoring.framework_signals import FrameworkSignalDetector, FrameworkType


class TestEnhancedEndpointClassifier:
    """Test suite for enhanced endpoint classifier functionality."""
    
    def test_auth_protected_classification(self):
        """Test authentication-protected endpoint classification."""
        classifier = create_enhanced_classifier()
        
        # Mock response with authentication indicators
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized: Access denied'
        mock_response.headers = {}
        
        request = DiscoveryRequest(
            url="https://api.example.com/protected",
            method="POST"
        )
        
        async def _run_test():
            return await classifier.classify_endpoint(
                request=request,
                initial_response=mock_response
            )
        classification = _run(_run_test())
        
        assert classification.endpoint_type == EndpointType.AUTH_PROTECTED
        assert classification.confidence > 0.6, "Auth protected should have high confidence"
    
    def test_crud_classification(self):
        """Test CRUD endpoint classification."""
        classifier = create_enhanced_classifier()
        
        # Mock response with CRUD indicators
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'User created successfully'
        mock_response.headers = {}
        
        request = DiscoveryRequest(
            url="https://api.example.com/users",
            method="POST"
        )
        
        async def _run_test():
            return await classifier.classify_endpoint(
                request=request,
                initial_response=mock_response
            )
        classification = _run(_run_test())
        
        assert classification.endpoint_type == EndpointType.CRUD
        assert classification.confidence > 0.5, "CRUD should have moderate confidence"
    
    def test_upload_classification(self):
        """Test upload endpoint classification."""
        classifier = create_enhanced_classifier()
        
        # Mock response with upload indicators
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'File uploaded successfully'
        mock_response.headers = {"content-type": "multipart/form-data"}
        
        request = DiscoveryRequest(
            url="https://api.example.com/upload",
            method="POST"
        )
        
        async def _run_test():
            return await classifier.classify_endpoint(
                request=request,
                initial_response=mock_response
            )
        classification = _run(_run_test())
        
        assert classification.endpoint_type == EndpointType.UPLOAD
        assert classification.confidence > 0.6, "Upload should have high confidence"
    
    def test_search_classification(self):
        """Test search endpoint classification."""
        classifier = create_enhanced_classifier()
        
        # Mock response with search indicators
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'Search results returned'
        mock_response.headers = {}
        
        request = DiscoveryRequest(
            url="https://api.example.com/search",
            method="GET"
        )
        
        async def _run_test():
            return await classifier.classify_endpoint(
                request=request,
                initial_response=mock_response
            )
        classification = _run(_run_test())
        
        assert classification.endpoint_type in (EndpointType.SEARCH, EndpointType.CRUD), "Search or CRUD acceptable"
        assert classification.confidence > 0.3, "Search should have reasonable confidence"
    
    def test_framework_integration(self):
        """Test framework signal integration."""
        classifier = create_enhanced_classifier()
        
        # Mock framework detector
        mock_framework_detector = Mock()
        mock_framework_detector.detect_signals.return_value = Mock(
            framework_type=FrameworkType.PYTHON_FASTAPI,
            confidence=0.9
        )
        
        # Create classifier with mock framework detector
        enhanced_classifier = EnhancedEndpointClassifier(
            framework_detector=mock_framework_detector
        )
        
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.text = '{"detail": "field \\"test_param\\" is required"}'
        mock_response.headers = {}
        
        request = DiscoveryRequest(
            url="https://api.example.com/test",
            method="POST"
        )
        
        async def _run_test():
            return await enhanced_classifier.classify_endpoint(
                request=request,
                initial_response=mock_response
            )
        classification = _run(_run_test())
        
        # Should have called framework detector
        mock_framework_detector.detect_signals.assert_called_once()
        assert classification.confidence > 0.3, "Framework integration should yield reasonable confidence"
    
    def test_differential_signals_integration(self):
        """Test differential signals integration."""
        classifier = create_enhanced_classifier()
        
        # Mock differential candidates
        from probes.differential_engine import ParameterCandidate
        mock_candidates = [
            ParameterCandidate(name="test_param", diffs=[], provisional_score=0.7, evidence={}, sources=['differential_engine'])
        ]
        
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'Success'
        mock_response.headers = {}
        
        request = DiscoveryRequest(
            url="https://api.example.com/test",
            method="POST"
        )
        
        async def _run_test():
            return await classifier.classify_endpoint(
                request=request,
                initial_response=mock_response,
                candidates=mock_candidates
            )
        classification = _run(_run_test())
        
        assert classification.signals.differential_candidates == 1, "Should detect differential candidates"
        assert classification.confidence > 0.5, "Differential signals should increase confidence"
    
    def test_confidence_calculation(self):
        """Test confidence calculation in classification."""
        classifier = create_enhanced_classifier()
        
        # Test with strong signals
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'Operation completed successfully'
        mock_response.headers = {}
        
        request = DiscoveryRequest(
            url="https://api.example.com/test",
            method="POST"
        )
        
        async def _run_test():
            return await classifier.classify_endpoint(
                request=request,
                initial_response=mock_response
            )
        classification = _run(_run_test())
        
        assert 0.0 <= classification.confidence <= 1.0, "Confidence should be normalized"
        assert classification.confidence > 0.3, "Should have reasonable confidence"
    
    def test_error_handling(self):
        """Test error handling in classification."""
        classifier = create_enhanced_classifier()
        
        # Test with None response
        async def _run_test():
            return await classifier.classify_endpoint(
                request=DiscoveryRequest(
                    url="https://api.example.com/test",
                    method="POST"
                ),
                initial_response=None,
                candidates=[]
            )
        classification = _run(_run_test())
        
        assert classification.endpoint_type in (EndpointType.CRUD, EndpointType.UPLOAD), "Should default to CRUD or upload for POST"
        assert 0.2 <= classification.confidence <= 0.5, "Should have baseline confidence"


if __name__ == "__main__":
    pytest.main([__name__])
