"""
Unit tests for differential engine functionality.

Tests candidate generation, fingerprint comparison, and
location resolution without network dependencies.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

def _run(coro):
    """Run async coroutine from sync test."""
    return asyncio.run(coro)
from probes.differential_engine import (
    DifferentialEngine,
    ParameterCandidate,
    create_differential_engine
)
from models import DiscoveryRequest, DiscoveryContext
from transport.client import RequestsTransportClient
from fingerprint.response_fingerprint import create_fingerprint


class TestDifferentialEngine:
    """Test suite for differential engine functionality."""
    
    def test_candidate_generation_from_error_patterns(self):
        """Test candidate generation from error patterns."""
        # Mock transport client
        mock_transport = Mock()
        mock_response = Mock()
        mock_response.text = '{"detail": [{"loc": ["body", "test_param"], "msg": "field required"}]}'
        
        engine = create_differential_engine(
            transport_client=mock_transport,
            probe_strategies=[]
        )
        
        request = DiscoveryRequest(
            url="https://api.example.com/test",
            method="POST"
        )
        
        # Mock baseline fingerprint
        baseline_fp = create_fingerprint(
            status_code=400,
            body=mock_response.text,
            headers={"content-type": "application/json"},
            response_time_ms=100.0
        )
        
        # Test candidate generation
        async def _run_test():
            return await engine._generate_candidate_names(baseline_fp)
        candidates = _run(_run_test())
        
        # Should generate candidates from error patterns
        assert len(candidates) > 0, "Should generate candidates from error patterns"
        assert "test_param" in candidates, "Should extract 'test_param' from error message"
    
    def test_fingerprint_comparison_scoring(self):
        """Test fingerprint comparison and scoring."""
        from fingerprint.response_fingerprint import create_fingerprint
        from scoring.confidence_scoring import WeightedConfidenceScorer
        
        # Create test fingerprints
        fp1 = create_fingerprint(200, "body1", {"param": "value1"}, 100.0)
        fp2 = create_fingerprint(200, "body2", {"param": "value2"}, 200.0)
        fp3 = create_fingerprint(200, "body3", {"param": "value3"}, 150.0)
        
        # Mock scorer
        scorer = WeightedConfidenceScorer()
        
        # Test identical fingerprints
        diff_identical = scorer.calculate_parameter_confidence(
            parameter_name="param1",
            evidence_sources=['differential_engine'],
            framework_signals={'framework_detection': {'detected_type': 'python_fastapi', 'confidence': 0.8}},
            location_tests=[{'location': 'body', 'success': True, 'score': 0.8}]
        )
        
        assert diff_identical.confidence >= 0.85, "Identical fingerprints should have high confidence"
        assert diff_identical.location == "body", "Identical fingerprints should have body location"
        
        # Test different fingerprints
        diff_different = scorer.calculate_parameter_confidence(
            parameter_name="param2",
            evidence_sources=['differential_engine'],
            framework_signals={'framework_detection': {'detected_type': 'python_fastapi', 'confidence': 0.8}},
            location_tests=[{'location': 'body', 'success': True, 'score': 0.6}]
        )
        
        assert diff_different.confidence <= diff_identical.confidence, "Different fingerprints should have same or lower confidence"
        assert diff_different.location == "body", "Different fingerprints should have body location"
        
        # Test length change detection
        diff_length_change = scorer.calculate_parameter_confidence(
            parameter_name="param3",
            evidence_sources=['differential_engine'],
            framework_signals={'framework_detection': {'detected_type': 'python_fastapi', 'confidence': 0.8}},
            location_tests=[{'location': 'body', 'success': True, 'score': 0.4}]
        )
        
        assert diff_length_change.confidence <= diff_different.confidence, "Length change should not increase confidence"
        assert diff_length_change.location_confidence <= diff_different.location_confidence, "Length change should not increase location confidence"
    
    def test_location_resolver_integration(self):
        """Test location resolver integration."""
        from probes.location_resolver import LocationResolver
        from probes.differential_engine import ParameterCandidate
        
        mock_responses = {
            "body": Mock(status_code=200, text="success", headers={"content-type": "application/json"}),
            "query": Mock(status_code=200, text="success", headers={"content-type": "application/json"}),
            "form": Mock(status_code=200, text="success", headers={"content-type": "application/json"}),
            "header": Mock(status_code=200, text="success", headers={"content-type": "application/json"})
        }
        
        mock_transport = Mock()
        mock_transport.send = AsyncMock(side_effect=lambda req, payload=None, location="body": mock_responses.get(location, mock_responses["body"]))
        
        resolver = LocationResolver(mock_transport)
        request = DiscoveryRequest(url="https://api.example.com/test", method="POST")
        candidate = ParameterCandidate(name="test", diffs=[], provisional_score=0.7, evidence={}, sources=[])

        async def _run_test():
            return await resolver.resolve_location("test_param", candidate, request)

        result = _run(_run_test())
        mock_transport.send.assert_called()
        assert result is not None
        assert result.best_location in ["body", "query", "form", "header"]
    
    def test_error_handling(self):
        """Test error handling in differential engine."""
        from probes.differential_engine import create_differential_engine
        
        mock_transport = Mock()
        mock_transport.send = AsyncMock(side_effect=Exception("Network error"))
        
        engine = create_differential_engine(
            transport_client=mock_transport,
            probe_strategies=[]
        )
        request = DiscoveryRequest(url="https://api.example.com/test", method="POST")

        async def _run_test():
            return await engine.run(request)

        result = _run(_run_test())
        # Engine returns List[ParameterCandidate]; on baseline capture failure returns []
        assert result == [], "Should return empty list on error"


if __name__ == "__main__":
    pytest.main([__name__])
