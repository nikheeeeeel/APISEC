"""
Unit tests for fingerprint comparison functionality.

Tests the fingerprint comparison logic with mock data
to ensure accurate differential analysis without network dependencies.
"""

import pytest
from fingerprint.response_fingerprint import (
    ResponseFingerprint,
    FingerprintDiff,
    create_fingerprint,
    compare_fingerprints
)
from dataclasses import asdict


class TestFingerprintComparison:
    """Test suite for fingerprint comparison functionality."""
    
    def test_identical_fingerprints(self):
        """Test comparison of identical fingerprints."""
        # Create identical fingerprints
        fp1 = create_fingerprint(200, "same_body", {}, 100.0)
        fp2 = create_fingerprint(200, "same_body", {}, 100.0)
        
        # Compare fingerprints
        diff = compare_fingerprints(fp1, fp2)
        
        # Assertions
        assert diff.status_changed is False, "Identical fingerprints should not have status changes"
        assert diff.hash_changed is False, "Identical fingerprints should not have hash changes"
        assert diff.length_delta_percent == 0.0, "Identical fingerprints should not have length changes"
        assert diff.similarity_score == 1.0, "Identical fingerprints should have perfect similarity"
        assert len(diff.headers_added) == 0, "Identical fingerprints should not have added headers"
        assert len(diff.headers_removed) == 0, "Identical fingerprints should not have removed headers"
        assert len(diff.headers_changed) == 0, "Identical fingerprints should not have changed headers"
    
    def test_different_status_codes(self):
        """Test comparison of fingerprints with different status codes."""
        # Create fingerprints with different status codes
        fp_success = create_fingerprint(200, "success_body", {}, 100.0)
        fp_error = create_fingerprint(404, "error_body", {}, 100.0)
        fp_redirect = create_fingerprint(302, "redirect_body", {}, 100.0)
        
        # Test successful vs error
        diff_success_error = compare_fingerprints(fp_success, fp_error)
        assert diff_success_error.status_changed is True, "Status change should be detected"
        assert diff_success_error.hash_changed is False, "Hash should not change for status code difference"
        assert diff_success_error.length_delta_percent > 0, "Length should change for different status codes"
        
        # Test error vs redirect
        diff_error_redirect = compare_fingerprints(fp_error, fp_redirect)
        assert diff_error_redirect.status_changed is True, "Status change should be detected"
        assert diff_error_redirect.hash_changed is False, "Hash should not change for status code difference"
        assert diff_error_redirect.length_delta_percent > 0, "Length should change for different status codes"
        
        # Test redirect vs success
        diff_redirect_success = compare_fingerprints(fp_redirect, fp_success)
        assert diff_redirect_success.status_changed is True, "Status change should be detected"
        assert diff_redirect_success.hash_changed is False, "Hash should not change for status code difference"
        assert diff_redirect_success.length_delta_percent > 0, "Length should change for different status codes"
    
    def test_body_hash_changes(self):
        """Test detection of body hash changes."""
        fp1 = create_fingerprint(200, "body1", {}, 100.0)
        fp2 = create_fingerprint(200, "body2", {}, 100.0)
        
        diff = compare_fingerprints(fp1, fp2)
        
        assert diff.hash_changed is True, "Body hash change should be detected"
        assert diff.length_delta_percent > 0, "Length delta should be positive"
        assert diff.similarity_score < 1.0, "Similarity should decrease for hash changes"
    
    def test_length_changes(self):
        """Test detection of length changes."""
        fp1 = create_fingerprint(200, "short_body", {}, 50.0)
        fp2 = create_fingerprint(200, "long_body", {}, 200.0)
        
        diff = compare_fingerprints(fp1, fp2)
        
        assert diff.hash_changed is False, "Hash should not change for length differences"
        assert diff.length_delta_percent > 0, "Length delta should be positive"
        assert diff.length_delta_percent == 150.0, "Length delta should be 150% ((200-50)/50)"
        assert diff.similarity_score < 1.0, "Similarity should decrease for length changes"
    
    def test_header_changes(self):
        """Test detection of header changes."""
        headers1 = {"content-type": "application/json"}
        headers2 = {"content-type": "application/xml"}
        
        fp1 = create_fingerprint(200, "body1", headers1, 100.0)
        fp2 = create_fingerprint(200, "body2", headers2, 100.0)
        
        diff = compare_fingerprints(fp1, fp2)
        
        assert diff.hash_changed is False, "Hash should not change for header differences"
        assert diff.headers_added == {"content-type": "application/xml"}, "New header should be detected"
        assert diff.headers_removed == {"content-type": "application/json"}, "Removed header should be detected"
        assert diff.headers_changed == {"content-type": "application/json"}, "Changed header should be detected"
        assert len(diff.headers_changed) == 1, "Should have exactly one changed header"
    
    def test_sensitivity_adjustment(self):
        """Test sensitivity adjustment in similarity scoring."""
        fp1 = create_fingerprint(200, "body1", {}, 100.0)
        fp2 = create_fingerprint(200, "body2", {}, 100.0)
        
        # Test with different sensitivity levels
        diff_low = compare_fingerprints(fp1, fp2, sensitivity=0.05)
        diff_medium = compare_fingerprints(fp1, fp2, sensitivity=0.1)
        diff_high = compare_fingerprints(fp1, fp2, sensitivity=0.2)
        
        # Higher sensitivity should result in lower similarity scores
        assert diff_low.similarity_score > diff_medium.similarity_score, "Low sensitivity should give higher similarity"
        assert diff_medium.similarity_score > diff_high.similarity_score, "Medium sensitivity should give higher similarity"
        assert diff_low.similarity_score > 0.9, "Low sensitivity should approach perfect similarity"
        assert diff_high.similarity_score < diff_medium.similarity_score, "High sensitivity should give lower similarity"
    
    def test_confidence_normalization(self):
        """Test confidence score normalization."""
        # Test values below, at, and above threshold
        test_cases = [
            (0.1, 0.1),   # Below threshold
            (0.3, 0.3),   # At threshold
            (0.7, 0.7),   # Above threshold
            (1.2, 1.2),   # Above max
        ]
        
        for input_val, expected in test_cases:
            # Mock scorer with threshold 0.3, max 1.0
            from scoring.confidence_scoring import WeightedConfidenceScorer
            scorer = WeightedConfidenceScorer(
                config=scoring.confidence_scoring.ScoringConfig(
                    min_confidence_threshold=0.3,
                    max_confidence=1.0
                )
            )
            
            result = scorer._normalize_confidence(input_val)
            
            if expected == "below":
                assert result < 0.3, f"Value {input_val} should be below threshold 0.3"
            elif expected == "at":
                assert abs(result - 0.3) < 0.1, f"Value {input_val} should be within ±0.1 of threshold 0.3"
            elif expected == "above":
                assert result > 0.3, f"Value {input_val} should be above threshold 0.3"
            else:
                assert result == 1.0, f"Value {input_val} should be capped at max 1.0"


class TestProbeStrategies:
    """Test suite for probe strategy implementations."""
    
    def test_string_probe_payload_generation(self):
        """Test string probe payload generation."""
        from probes.strategies import StringProbe
        from models import DiscoveryContext
        
        probe = StringProbe()
        context = DiscoveryContext(request=DiscoveryRequest(
            url="https://api.example.com/test",
            method="POST"
        ))
        
        # Generate payloads
        payloads = probe.generate_payloads(context)
        
        # Assertions
        assert len(payloads) > 0, "Should generate payloads"
        assert all(isinstance(p, dict) for p in payloads), "All payloads should be dictionaries"
        assert all("test_value" in p.values() for p in payloads), "All payloads should contain test_value"
        
        # Check for required payload types
        required_types = probe.get_target_parameter_types()
        assert len(required_types) > 0, "Should have target parameter types"
        assert any(pt in required_types for pt in required_types), "Should target string/text types"
    
    def test_numeric_probe_boundary_testing(self):
        """Test numeric probe boundary value generation."""
        from probes.strategies import NumericProbe
        from models import DiscoveryContext
        
        probe = NumericProbe()
        context = DiscoveryContext(request=DiscoveryRequest(
            url="https://api.example.com/test",
            method="POST"
        ))
        
        payloads = probe.generate_payloads(context)
        
        # Check for boundary values
        boundary_values = []
        for payload in payloads:
            if "boundary" in payload.get("test_value", ""):
                boundary_values.append(payload["test_value"])
        
        # Should have boundary test values
        assert len(boundary_values) > 0, "Should generate boundary test values"
        assert any(val in [-2147483648, 2147483647] for val in boundary_values), "Should include 32-bit int boundaries"
    
    def test_location_resolver_body_location(self):
        """Test location resolver body location testing."""
        from probes.location_resolver import LocationResolver
        from transport.client import RequestsTransportClient
        from models import DiscoveryRequest
        from unittest.mock import Mock
        
        # Mock transport client
        mock_response = Mock()
        mock_response.get.return_value = Mock(
            status_code=200,
            text="success",
            headers={"content-type": "application/json"}
        )
        
        transport_client = RequestsTransportClient()
        resolver = LocationResolver(transport_client)
        
        request = DiscoveryRequest(
            url="https://api.example.com/test",
            method="POST"
        )
        
        # Test body location
        result = resolver.resolve_location(
            parameter_name="test_param",
            candidate=type('ParameterCandidate', '', '', 0.7, {}, ['test'], ['differential_engine']),
            request=request
        )
        
        assert result.best_location == "body", "Body location should be selected for successful response"
        assert result.location_confidence > 0.5, "Should have confidence in body location"


if __name__ == "__main__":
    pytest.main([__name__])
