"""
Unit tests for framework signals functionality.

Tests framework detection with mock data to ensure
accurate API technology identification without network dependencies.
"""

import pytest
from unittest.mock import Mock
from scoring.framework_signals import (
    FrameworkSignalDetector,
    FrameworkType,
    create_framework_detector
)
from fingerprint.response_fingerprint import create_fingerprint


class TestFrameworkSignalDetector:
    """Test suite for framework signal detector functionality."""
    
    def test_fastapi_detection(self):
        """Test FastAPI framework detection."""
        detector = create_framework_detector()
        
        # FastAPI response
        fastapi_response = '{"detail": "field \\"test_param\\" is required", "type": "validation_error"}'
        
        signal = detector.detect_signals(
            response_text=fastapi_response,
            response_headers={"content-type": "application/json"},
            status_code=422
        )
        
        assert signal.framework_type == FrameworkType.PYTHON_FASTAPI
        assert signal.confidence > 0.7, "FastAPI should have high confidence"
        assert len(signal.signal_patterns) > 0, "Should detect FastAPI patterns"
    
    def test_express_detection(self):
        """Test Express.js framework detection."""
        detector = create_framework_detector()
        
        # Express response
        express_response = 'Error: Cannot POST /api/test - parameter "test_param" is required'
        
        signal = detector.detect_signals(
            response_text=express_response,
            response_headers={"x-powered-by": "Express"},
            status_code=400
        )
        
        assert signal.framework_type == FrameworkType.NODE_EXPRESS
        assert signal.confidence > 0.6, "Express should have good confidence"
        assert len(signal.signal_patterns) > 0, "Should detect Express patterns"
    
    def test_spring_boot_detection(self):
        """Test Spring Boot framework detection."""
        detector = create_framework_detector()
        
        # Spring Boot response
        spring_response = '{"timestamp": "1672531200000", "status": 400, "error": "parameter \\"test_param\\" is required"}'
        
        signal = detector.detect_signals(
            response_text=spring_response,
            response_headers={"content-type": "application/json"},
            status_code=400
        )
        
        assert signal.framework_type == FrameworkType.JAVA_SPRING_BOOT
        assert signal.confidence > 0.6, "Spring Boot should have good confidence"
        assert len(signal.signal_patterns) > 0, "Should detect Spring Boot patterns"
    
    def test_framework_specific_strategies(self):
        """Test framework-specific strategy recommendations."""
        detector = create_framework_detector()
        
        # Test FastAPI strategies
        fastapi_strategies = detector.get_framework_specific_strategies(FrameworkType.PYTHON_FASTAPI)
        assert 'string_probe' in fastapi_strategies, "FastAPI should include string probe"
        assert 'type_probe' in fastapi_strategies, "FastAPI should include type probe"
        
        # Test Express strategies
        express_strategies = detector.get_framework_specific_strategies(FrameworkType.NODE_EXPRESS)
        assert 'string_probe' in express_strategies, "Express should include string probe"
        assert 'boundary_probe' in express_strategies, "Express should include boundary probe"
    
    def test_unknown_framework_fallback(self):
        """Test fallback to FastAPI when no patterns detected."""
        detector = create_framework_detector()
        
        # Generic response
        generic_response = '{"message": "success"}'
        
        signal = detector.detect_signals(
            response_text=generic_response,
            response_headers={"content-type": "application/json"},
            status_code=200
        )
        
        # Should default to FastAPI when no patterns detected
        assert signal.confidence == 0.1, "Unknown should have low confidence"
        assert signal.framework_type == FrameworkType.PYTHON_FASTAPI, "Should default to FastAPI"
    
    def test_multiple_framework_patterns(self):
        """Test detection of multiple framework patterns."""
        detector = create_framework_detector()
        
        # Response with multiple framework indicators
        mixed_response = '{"detail": "validation_error", "powered-by": "Express"}'
        
        signal = detector.detect_signals(
            response_text=mixed_response,
            response_headers={"x-powered-by": "Express", "content-type": "application/json"},
            status_code=422
        )
        
        # Should detect Express due to header
        assert signal.framework_type == FrameworkType.NODE_EXPRESS
        assert signal.confidence > 0.5, "Mixed signals should have moderate confidence"
    
    def test_confidence_normalization(self):
        """Test confidence score normalization."""
        detector = create_framework_detector()
        
        # Test with high confidence signals
        high_confidence_response = '{"detail": "field \\"test_param\\" is required", "type": "validation_error"}'
        
        signal = detector.detect_signals(
            response_text=high_confidence_response,
            response_headers={"content-type": "application/json"},
            status_code=422
        )
        
        assert 0.0 <= signal.confidence <= 1.0, "Confidence should be normalized to 0-1 range"
        assert signal.confidence > 0.7, "Strong signals should have high confidence"


if __name__ == "__main__":
    pytest.main([__name__])
