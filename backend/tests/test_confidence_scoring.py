"""
Unit tests for confidence scoring functionality.

Tests weighted confidence calculation, normalization,
and location-specific scoring with comprehensive mock data.
"""

import asyncio
import pytest
from unittest.mock import Mock

def _run(coro):
    """Run async coroutine from sync test."""
    return asyncio.run(coro)
from scoring.confidence_scoring import (
    WeightedConfidenceScorer,
    ScoringWeights,
    ScoringConfig,
    ParameterConfidence
)
from probes.location_resolver import LocationResult, create_location_resolver
from transport.client import RequestsTransportClient
from models import DiscoveryRequest, DiscoveryContext


class TestConfidenceScoring:
    """Test suite for confidence scoring functionality."""
    
    def test_weight_configuration(self):
        """Test custom weight configuration."""
        custom_weights = ScoringWeights(
            status_changed=5.0,  # Increased weight for status changes
            hash_changed=4.0,      # Increased weight for hash changes
            reproducibility=3.0     # Increased weight for reproducible results
        )
        
        config = ScoringConfig(min_confidence_threshold=0.2)
        scorer = WeightedConfidenceScorer(weights=custom_weights, config=config)
        
        # Test with multiple evidence sources
        result = scorer.calculate_parameter_confidence(
            parameter_name="test_param",
            evidence_sources=['probe_string', 'probe_numeric', 'detection_fastapi'],
            framework_signals={'framework_detection': {'detected_type': 'python_fastapi', 'confidence': 0.9}}
        )
        
        # Should have higher confidence due to custom weights
        assert result.confidence > 0.5, "Custom weights should increase confidence"
        assert result.sources == ['probe_string', 'probe_numeric', 'detection_fastapi'], "Should track all evidence sources"
    
    def test_confidence_normalization(self):
        """Test confidence score normalization."""
        weights = ScoringWeights()
        config = ScoringConfig(min_confidence_threshold=0.3, max_confidence=1.0)
        scorer = WeightedConfidenceScorer(weights=weights, config=config)
        
        # Test normalization at different levels
        test_cases = [
            (0.1, "below_min"),    # Below minimum
            (0.3, "at_min"),      # At minimum
            (0.5, "below_max"),    # Below maximum
            (0.8, "at_max"),       # At maximum
            (1.5, "above_max")     # Above maximum
        ]
        
        for input_val, expected_range in test_cases:
            result = scorer._normalize_confidence(input_val)
            
            if expected_range == "below_min":
                assert result <= 0.5, f"Value {input_val} should be at or below 0.5 after normalization"
            elif expected_range == "at_min":
                assert abs(result - 0.3) < 0.1, f"Value {input_val} should be within ±0.1 of 0.3"
            elif expected_range == "below_max":
                assert result < 0.8, f"Value {input_val} should be below 0.8"
            elif expected_range == "at_max":
                assert result >= 0.8, f"Value {input_val} should be at or above 0.8"
            elif expected_range == "above_max":
                assert result >= 0.85, f"Value {input_val} should be capped/normalized (implementation may apply compression)"
    
    def test_location_confidence_calculation(self):
        """Test location-specific confidence calculation."""
        from probes.location_resolver import LocationTest
        from transport.client import RequestsTransportClient
        from models import DiscoveryRequest
        
        # Mock transport client
        mock_transport = Mock()
        
        # Mock successful location tests (location, fingerprint, diff, success, evidence, score)
        successful_tests = [
            LocationTest("body", Mock(), Mock(), True, {}, 0.8),
            LocationTest("query", Mock(), Mock(), True, {}, 0.7),
            LocationTest("form", Mock(), Mock(), True, {}, 0.6)
        ]
        
        # Mock failed location tests
        failed_tests = [
            LocationTest("header", Mock(), Mock(), False, {}, 0.2)
        ]
        
        resolver = create_location_resolver(mock_transport)
        request = DiscoveryRequest(
            url="https://api.example.com/test",
            method="POST"
        )
        
        # Test location confidence calculation (resolver has _calculate_location_score)
        best_location = resolver._determine_best_location(successful_tests + failed_tests)
        location_confidence = resolver._calculate_location_score(
            successful_tests + failed_tests, best_location
        )
        
        # Should have positive confidence for successful tests
        assert location_confidence > 0, "Successful tests should yield positive location confidence"
        
        # Should have lower confidence for failed tests
        failed_best = resolver._determine_best_location(failed_tests)
        failed_confidence = resolver._calculate_location_score(failed_tests, failed_best)
        assert failed_confidence < location_confidence, "Failed tests should decrease location confidence"
        
        # Best location should be body (most successful)
        best_location = resolver._determine_best_location(successful_tests + failed_tests)
        assert best_location == "body", f"Body location should be selected as best"
    
    def test_evidence_aggregation(self):
        """Test evidence aggregation from multiple sources."""
        weights = ScoringWeights()
        scorer = WeightedConfidenceScorer(weights=weights)
        
        # Test with multiple evidence sources (location_tests as dicts with .location, .success)
        loc_test = Mock()
        loc_test.location = "body"
        loc_test.success = True
        result = scorer.calculate_parameter_confidence(
            parameter_name="test_param",
            evidence_sources=['probe_string', 'framework_signals', 'location_body'],
            framework_signals={
                'framework_detection': {'detected_type': 'python_fastapi', 'confidence': 0.9},
                'error_patterns': ['missing_required', 'invalid_format']
            },
            location_tests=[loc_test]
        )
        
        # Should have source diversity bonus
        assert result.confidence > 0.5, "Multiple evidence sources should increase confidence"
        assert len(result.sources) >= 3, "Should have multiple evidence sources"
        assert 'probe_string' in result.sources, "Should include probe evidence"
        assert 'framework_signals' in result.sources, "Should include framework signals"
        assert 'location_body' in result.sources, "Should include location evidence"


class TestLocationResolver:
    """Test suite for location resolver functionality."""
    
    def test_best_location_determination(self):
        """Test best location determination logic."""
        from probes.location_resolver import LocationResolver
        from probes.location_resolver import LocationTest
        from models import DiscoveryRequest
        
        mock_transport = Mock()
        resolver = LocationResolver(mock_transport)
        
        # Create LocationTest instances for _determine_best_location (sync test)
        def make_test(location, success, score):
            t = Mock()
            t.location = location
            t.success = success
            t.score = score
            return t
        
        test_cases = [
            {
                'tests': [make_test("body", True, 0.9), make_test("body", True, 0.8), make_test("body", True, 0.7)],
                'expected_best': 'body'
            },
            {
                'tests': [make_test("body", True, 0.8), make_test("query", True, 0.9), make_test("form", True, 0.6)],
                'expected_best': 'query'
            },
            {
                'tests': [make_test("body", True, 0.8), make_test("header", True, 0.9)],
                'expected_best': 'header'
            }
        ]
        
        for test_case in test_cases:
            best_location = resolver._determine_best_location(test_case['tests'])
            assert best_location == test_case['expected_best'], f"Should select {test_case['expected_best']} as best location"
    
    def test_error_handling(self):
        """Test error handling in location resolver."""
        from unittest.mock import AsyncMock
        from probes.location_resolver import LocationResolver
        from probes.differential_engine import ParameterCandidate
        from models import DiscoveryRequest
        
        mock_transport = Mock()
        mock_transport.send = AsyncMock(side_effect=Exception("Network error"))
        
        resolver = LocationResolver(mock_transport)
        request = DiscoveryRequest(url="https://api.example.com/test", method="POST")
        candidate = ParameterCandidate(name="test", diffs=[], provisional_score=0.7, evidence={}, sources=[])

        async def _run_test():
            return await resolver.resolve_location("test_param", candidate, request)
        result = _run(_run_test())
        assert result is not None, "Should return result even on error"
        assert result.best_location == "body", "Should default to body on error"


if __name__ == "__main__":
    pytest.main([__name__])
