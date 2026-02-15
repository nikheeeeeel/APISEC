"""
Location resolver for REST Parameter Discovery v2.

Determines optimal parameter locations through systematic injection testing
and fingerprint differential analysis.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from ..models import DiscoveryRequest, DiscoveryContext
from ..transport import TransportClientInterface
from ..fingerprint import (
    ResponseFingerprint,
    FingerprintDiff,
    create_fingerprint,
    compare_fingerprints
)
from .differential_engine import ParameterCandidate


@dataclass
class LocationTest:
    """
    Result of testing a parameter at a specific location.
    
    Contains fingerprint comparison and location-specific evidence.
    """
    location: str
    fingerprint: ResponseFingerprint
    diff: FingerprintDiff
    success: bool
    evidence: Dict[str, Any]
    score: float


@dataclass
class LocationResult:
    """
    Result of location resolution for a parameter.
    
    Contains the best location and supporting evidence.
    """
    parameter_name: str
    best_location: str
    location_score: float
    location_evidence: Dict[str, LocationTest]
    supporting_differences: List[FingerprintDiff]


class LocationResolver:
    """
    Resolves optimal parameter locations through systematic testing.
    
    Tests parameters in different locations (body, query, form, header)
to determine where they are accepted and most effective.
    """
    
    def __init__(
        self,
        transport_client: TransportClientInterface,
        test_payload: Any = None
    ):
        """
        Initialize location resolver.
        
        Args:
            transport_client: HTTP client for making requests
            test_payload: Test payload to include in all requests
        """
        self.transport_client = transport_client
        self.test_payload = test_payload or {"test": "location_test"}
    
    async def resolve_location(
        self,
        parameter_name: str,
        candidate: ParameterCandidate,
        request: DiscoveryRequest
    ) -> LocationResult:
        """
        Resolve the best location for a parameter candidate.
        
        Args:
            parameter_name: Parameter name to resolve
            candidate: Parameter candidate with evidence
            request: Discovery request
            
        Returns:
            LocationResult with optimal location and evidence
        """
        print(f"🔍 Resolving location for parameter: {parameter_name}")
        
        # Test all locations systematically
        location_tests = await self._test_all_locations(
            parameter_name, candidate, request
        )
        
        # Analyze results and determine best location
        best_location = self._determine_best_location(location_tests)
        
        # Calculate location score
        location_score = self._calculate_location_score(location_tests, best_location)
        
        # Compile evidence
        location_evidence = {
            test.location: test for test in location_tests
        }
        
        supporting_differences = [
            test.diff for test in location_tests if test.diff
        ]
        
        return LocationResult(
            parameter_name=parameter_name,
            best_location=best_location,
            location_score=location_score,
            location_evidence=location_evidence,
            supporting_differences=supporting_differences
        )
    
    async def _test_all_locations(
        self,
        parameter_name: str,
        candidate: ParameterCandidate,
        request: DiscoveryRequest
    ) -> List[LocationTest]:
        """
        Test parameter in all possible locations.
        
        Args:
            parameter_name: Parameter name to test
            candidate: Parameter candidate with evidence
            request: Discovery request
            
        Returns:
            List of location test results
        """
        location_tests = []
        
        # Test body location
        body_test = await self._test_body_location(parameter_name, candidate, request)
        if body_test:
            location_tests.append(body_test)
        
        # Test query location
        query_test = await self._test_query_location(parameter_name, candidate, request)
        if query_test:
            location_tests.append(query_test)
        
        # Test form location
        form_test = await self._test_form_location(parameter_name, candidate, request)
        if form_test:
            location_tests.append(form_test)
        
        # Test header location
        header_test = await self._test_header_location(parameter_name, candidate, request)
        if header_test:
            location_tests.append(header_test)
        
        return location_tests
    
    async def _test_body_location(
        self,
        parameter_name: str,
        candidate: ParameterCandidate,
        request: DiscoveryRequest
    ) -> Optional[LocationTest]:
        """Test parameter in body location."""
        try:
            # Create payload with parameter in body
            payload = {parameter_name: candidate.evidence.get('test_value', 'test')}
            
            response = await self.transport_client.send(
                request=request,
                payload=payload,
                location="body"
            )
            
            fingerprint = create_fingerprint(
                status_code=response.status_code,
                body=response.text or "",
                headers=dict(response.headers),
                response_time_ms=100.0
            )
            
            # Compare with baseline (assuming empty body baseline)
            baseline_fingerprint = ResponseFingerprint(
                status_code=200,  # Assume baseline was successful
                body_hash="empty_body_hash",
                body_length=0,
                headers_normalized={},
                response_time_ms=100.0
            )
            
            diff = compare_fingerprints(baseline_fingerprint, fingerprint)
            
            return LocationTest(
                location="body",
                fingerprint=fingerprint,
                diff=diff,
                success=response.status_code == 200,
                evidence={
                    'payload_tested': payload,
                    'response_code': response.status_code,
                    'body_length': fingerprint.body_length,
                    'location_effectiveness': self._calculate_location_effectiveness(diff)
                },
                score=self._calculate_test_score(diff)
            )
            
        except Exception as e:
            print(f"     Body location test failed: {str(e)}")
            return None
    
    async def _test_query_location(
        self,
        parameter_name: str,
        candidate: ParameterCandidate,
        request: DiscoveryRequest
    ) -> Optional[LocationTest]:
        """Test parameter in query location."""
        try:
            # Create payload with parameter in query
            # For query, we modify the URL
            base_url = request.url
            separator = '&' if '?' in base_url else '?'
            
            payload = {parameter_name: candidate.evidence.get('test_value', 'test')}
            test_url = f"{base_url}{separator}{parameter_name}={payload.get('test_value', 'test')}"
            
            response = await self.transport_client.send(
                request=DiscoveryRequest(
                    url=test_url,
                    method=request.method,
                    headers=request.headers,
                    timeout_seconds=request.timeout_seconds
                ),
                payload={},  # No body for GET with query
                location="query"
            )
            
            fingerprint = create_fingerprint(
                status_code=response.status_code,
                body=response.text or "",
                headers=dict(response.headers),
                response_time_ms=100.0
            )
            
            # Compare with baseline
            baseline_fingerprint = ResponseFingerprint(
                status_code=200,
                body_hash="empty_query_hash",
                body_length=0,
                headers_normalized={},
                response_time_ms=100.0
            )
            
            diff = compare_fingerprints(baseline_fingerprint, fingerprint)
            
            return LocationTest(
                location="query",
                fingerprint=fingerprint,
                diff=diff,
                success=response.status_code == 200,
                evidence={
                    'payload_tested': payload,
                    'response_code': response.status_code,
                    'test_url': test_url,
                    'location_effectiveness': self._calculate_location_effectiveness(diff)
                },
                score=self._calculate_test_score(diff)
            )
            
        except Exception as e:
            print(f"     Query location test failed: {str(e)}")
            return None
    
    async def _test_form_location(
        self,
        parameter_name: str,
        candidate: ParameterCandidate,
        request: DiscoveryRequest
    ) -> Optional[LocationTest]:
        """Test parameter in form location."""
        try:
            # Create payload with parameter in form data
            payload = {parameter_name: candidate.evidence.get('test_value', 'test')}
            
            response = await self.transport_client.send(
                request=request,
                payload=payload,
                location="form"
            )
            
            fingerprint = create_fingerprint(
                status_code=response.status_code,
                body=response.text or "",
                headers=dict(response.headers),
                response_time_ms=100.0
            )
            
            # Compare with baseline
            baseline_fingerprint = ResponseFingerprint(
                status_code=200,
                body_hash="empty_form_hash",
                body_length=0,
                headers_normalized={},
                response_time_ms=100.0
            )
            
            diff = compare_fingerprints(baseline_fingerprint, fingerprint)
            
            return LocationTest(
                location="form",
                fingerprint=fingerprint,
                diff=diff,
                success=response.status_code == 200,
                evidence={
                    'payload_tested': payload,
                    'response_code': response.status_code,
                    'content_type': response.headers.get('content-type', ''),
                    'location_effectiveness': self._calculate_location_effectiveness(diff)
                },
                score=self._calculate_test_score(diff)
            )
            
        except Exception as e:
            print(f"     Form location test failed: {str(e)}")
            return None
    
    async def _test_header_location(
        self,
        parameter_name: str,
        candidate: ParameterCandidate,
        request: DiscoveryRequest
    ) -> Optional[LocationTest]:
        """Test parameter in header location."""
        try:
            # Create payload with parameter as custom header
            payload = {parameter_name: candidate.evidence.get('test_value', 'test')}
            
            # Add test payload to base request
            test_headers = request.headers.copy()
            test_headers[f"X-APISec-{parameter_name.title()}"] = payload.get('test_value', 'test')
            
            response = await self.transport_client.send(
                request=request,
                payload={},  # No body for header test
                location="header"
            )
            
            fingerprint = create_fingerprint(
                status_code=response.status_code,
                body=response.text or "",
                headers=dict(response.headers),
                response_time_ms=100.0
            )
            
            # Compare with baseline
            baseline_fingerprint = ResponseFingerprint(
                status_code=200,
                body_hash="empty_header_hash",
                body_length=0,
                headers_normalized={},
                response_time_ms=100.0
            )
            
            diff = compare_fingerprints(baseline_fingerprint, fingerprint)
            
            return LocationTest(
                location="header",
                fingerprint=fingerprint,
                diff=diff,
                success=response.status_code == 200,
                evidence={
                    'payload_tested': payload,
                    'response_code': response.status_code,
                    'header_received': response.headers.get(f"x-apisec-{parameter_name.title()}", ""),
                    'location_effectiveness': self._calculate_location_effectiveness(diff)
                },
                score=self._calculate_test_score(diff)
            )
            
        except Exception as e:
            print(f"     Header location test failed: {str(e)}")
            return None
    
    def _determine_best_location(self, location_tests: List[LocationTest]) -> str:
        """
        Determine the best location from test results.
        
        Args:
            location_tests: List of location test results
            
        Returns:
            Best location string
        """
        if not location_tests:
            return "body"  # Default to body
        
        # Score each location
        location_scores = {
            "body": 0,
            "query": 0,
            "form": 0,
            "header": 0
        }
        
        for test in location_tests:
            if test.success:
                location_scores[test.location] += test.score
        
        # Return location with highest score
        return max(location_scores, key=location_scores.get)
    
    def _calculate_location_score(self, location_tests: List[LocationTest], best_location: str) -> float:
        """
        Calculate overall location resolution score.
        
        Args:
            location_tests: List of location test results
            best_location: Location that was determined as best
            
        Returns:
            Normalized score (0-1)
        """
        if not location_tests:
            return 0.0
        
        # Get score for best location
        best_score = 0.0
        for test in location_tests:
            if test.location == best_location and test.success:
                best_score = max(best_score, test.score)
        
        # Calculate confidence based on best score vs total possible
        total_success_tests = sum(1 for test in location_tests if test.success)
        max_possible_score = len(location_tests) * 1.0  # Each successful test = 1.0
        
        if max_possible_score > 0:
            return best_score / max_possible_score
        else:
            return 0.0
    
    def _calculate_test_score(self, diff: FingerprintDiff) -> float:
        """
        Calculate score for individual location test.
        
        Args:
            diff: Fingerprint difference from test
            
        Returns:
            Test score (0-1)
        """
        score = 0.0
        
        # Success bonus
        if diff.status_changed is False:  # Status remained stable
            score += 0.5
        
        # Change detection bonus (parameter likely exists)
        if diff.hash_changed:
            score += 0.3
        
        # Length change bonus (parameter affected response)
        if diff.length_delta_percent > 0.05:  # 5% or more change
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_location_effectiveness(self, diff: FingerprintDiff) -> str:
        """
        Calculate effectiveness of location test.
        
        Args:
            diff: Fingerprint difference
            
        Returns:
            Effectiveness description
        """
        if diff.status_changed:
            if diff.hash_changed:
                return "parameter_accepted"
            else:
                return "parameter_rejected"
        else:
            return "test_inconclusive"


# Factory function
def create_location_resolver(
    transport_client: TransportClientInterface
) -> LocationResolver:
    """
    Create a location resolver with default configuration.
    
    Args:
        transport_client: HTTP client for making requests
        
    Returns:
        Configured LocationResolver instance
    """
    return LocationResolver(transport_client=transport_client)
