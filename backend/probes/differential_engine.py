"""
Differential engine for REST Parameter Discovery v2.

Provides stateless, reusable differential analysis for identifying
parameter candidates through systematic fingerprint comparison.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from ..models import DiscoveryRequest, DiscoveryContext
from ..transport import TransportClientInterface
from ..fingerprint import (
    ResponseFingerprint,
    FingerprintDiff,
    create_fingerprint,
    compare_fingerprints,
    extract_error_patterns_from_fingerprint,
    calculate_fingerprint_confidence
)
from .strategies import ProbeStrategy, StringProbe, NumericProbe, BooleanProbe


@dataclass
class ParameterCandidate:
    """
    Candidate parameter discovered through differential analysis.
    
    Contains evidence, confidence, and fingerprint diffs supporting
the parameter's existence and characteristics.
    """
    name: str
    diffs: List['FingerprintDiff']
    provisional_score: float
    evidence: Dict[str, Any]
    sources: List[str]
    parameter_type: Optional[str] = None
    required: Optional[bool] = None
    location: Optional[str] = None


class DifferentialEngine:
    """
    Differential analysis engine for systematic parameter discovery.
    
    Uses fingerprint comparison to identify parameter candidates
by analyzing response changes across different payload variations.
    """
    
    def __init__(
        self,
        transport_client: TransportClientInterface,
        probe_strategies: List[ProbeStrategy],
        max_candidates_per_parameter: int = 10
    ):
        """
        Initialize differential engine.
        
        Args:
            transport_client: HTTP client for making requests
            probe_strategies: List of probe strategies to use
            max_candidates_per_parameter: Maximum candidates to generate per parameter
        """
        self.transport_client = transport_client
        self.probe_strategies = probe_strategies
        self.max_candidates_per_parameter = max_candidates_per_parameter
    
    async def run(self, request: DiscoveryRequest) -> List[ParameterCandidate]:
        """
        Run differential analysis to discover parameters.
        
        Args:
            request: Discovery request with context
            
        Returns:
            List of ParameterCandidate objects with discovered parameters
        """
        print(f"🔍 Starting Differential Analysis for {request.url}")
        
        # Step 1: Capture baseline fingerprint
        baseline_fingerprint = await self._capture_baseline_fingerprint(request)
        
        if not baseline_fingerprint:
            return []
        
        # Step 2: Generate candidate parameters
        candidate_names = await self._generate_candidate_names(baseline_fingerprint)
        
        # Step 3: Test each candidate systematically
        results = []
        for candidate_name in candidate_names:
            print(f"   Testing candidate: {candidate_name}")
            
            # Apply all probe strategies to this candidate
            candidate_results = await self._test_candidate_parameter(
                request, candidate_name, baseline_fingerprint
            )
            
            if candidate_results:
                results.extend(candidate_results)
        
        return results
    
    async def _capture_baseline_fingerprint(self, request: DiscoveryRequest) -> Optional[ResponseFingerprint]:
        """
        Capture baseline fingerprint with minimal payload.
        
        Args:
            request: Discovery request
            
        Returns:
            Baseline fingerprint or None if request fails
        """
        try:
            # Send minimal request to get baseline
            response = await self.transport_client.send(
                request=request,
                payload={},  # Empty payload
                location="body"
            )
            
            return create_fingerprint(
                status_code=response.status_code,
                body=response.text or "",
                headers=dict(response.headers),
                response_time_ms=100.0  # Placeholder
            )
            
        except Exception as e:
            print(f"   Baseline capture failed: {str(e)}")
            return None
    
    async def _generate_candidate_names(self, baseline_fingerprint: ResponseFingerprint) -> List[str]:
        """
        Generate candidate parameter names from baseline fingerprint.
        
        Args:
            baseline_fingerprint: Baseline response fingerprint
            
        Returns:
            List of candidate parameter names
        """
        candidates = []
        
        # Extract parameter names from error patterns
        error_patterns = extract_error_patterns_from_fingerprint(baseline_fingerprint)
        
        # Use raw body text for pattern matching; body_hash is SHA256 hex and cannot match text patterns
        body_text = baseline_fingerprint.body_text or ""
        if not body_text and baseline_fingerprint.body_length > 0:
            body_text = ""  # Cannot extract from hash; stay empty

        # Look for parameter name patterns in error messages
        if error_patterns.get('http_error') and body_text:
            import re

            # Pattern: "parameter 'X' is required"
            param_pattern = re.compile(r"parameter\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
            matches = param_pattern.findall(body_text)
            candidates.extend(matches)

            # Pattern: "field X cannot be null/empty"
            field_pattern = re.compile(r"field\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
            matches = field_pattern.findall(body_text)
            candidates.extend(matches)

            # Pattern: "missing X" or "X is missing"
            missing_pattern = re.compile(r"(?:missing|not\s+found)\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
            matches = missing_pattern.findall(body_text)
            candidates.extend(matches)

            # Pattern: "loc" JSON array (FastAPI-style) - capture param name (last or second elem)
            loc_pattern = re.compile(r'"loc"\s*:\s*\[\s*"[^"]+"\s*,\s*"([^"]+)"', re.IGNORECASE)
            matches = loc_pattern.findall(body_text)
            candidates.extend(matches)
            # Also try pattern for single-element loc
            loc_simple = re.compile(r'"loc"\s*:\s*\[\s*"([^"]+)"\s*\]', re.IGNORECASE)
            candidates.extend(loc_simple.findall(body_text))
        
        # Fallback: extract quoted strings from JSON-like body for short error messages
        if not candidates and len(body_text) < 500:
            import re
            json_param_pattern = re.compile(r'"([a-zA-Z_][a-zA-Z0-9_]*)"\s*:', re.IGNORECASE)
            matches = json_param_pattern.findall(body_text)
            candidates.extend(matches)

        # Remove duplicates and limit candidates
        unique_candidates = list(dict.fromkeys(candidates))  # preserve order, remove duplicates
        return unique_candidates[:self.max_candidates_per_parameter]
    
    async def _test_candidate_parameter(
        self,
        request: DiscoveryRequest,
        candidate_name: str,
        baseline_fingerprint: ResponseFingerprint
    ) -> List[ParameterCandidate]:
        """
        Test a candidate parameter using all probe strategies.
        
        Args:
            request: Discovery request
            candidate_name: Candidate parameter name
            baseline_fingerprint: Baseline fingerprint for comparison
            
        Returns:
            List of ParameterCandidate objects for this candidate
        """
        results = []
        diffs = []
        
        # Test with each strategy
        for strategy in self.probe_strategies:
            print(f"     Strategy: {strategy.get_strategy_name()}")
            
            # Generate payloads for this candidate (seed context so strategies produce payloads)
            context = self._create_test_context(request, baseline_fingerprint, candidate_name)
            payloads = strategy.generate_payloads(context)
            
            # Test each payload
            for payload in payloads:
                try:
                    # Create test payload with just this parameter
                    test_payload = {candidate_name: payload[candidate_name]}
                    
                    response = await self.transport_client.send(
                        request=request,
                        payload=test_payload,
                        location="body"
                    )
                    
                    # Create fingerprint for comparison
                    test_fingerprint = create_fingerprint(
                        status_code=response.status_code,
                        body=response.text or "",
                        headers=dict(response.headers),
                        response_time_ms=100.0  # Placeholder
                    )
                    
                    # Compare with baseline
                    diff = compare_fingerprints(baseline_fingerprint, test_fingerprint)
                    
                    if diff.hash_changed or diff.status_changed or diff.length_delta_percent > 0.1:
                        # Parameter likely exists - record evidence as ParameterCandidate
                        param_type = strategy.get_target_parameter_types()[0] if strategy.get_target_parameter_types() else 'string'
                        evidence = {
                            'baseline_status': baseline_fingerprint.status,
                            'test_status': test_fingerprint.status,
                            'status_change': diff.status_changed,
                            'body_hash_change': diff.hash_changed,
                            'length_change': diff.length_delta_percent,
                            'response_diff': diff.__dict__,
                            'parameter_type': param_type,
                            'required': self._infer_required_from_response(response),
                        }
                        result = ParameterCandidate(
                            name=candidate_name,
                            diffs=[diff],
                            provisional_score=0.7,
                            evidence=evidence,
                            sources=[f'differential_{strategy.get_strategy_name()}'],
                            parameter_type=param_type,
                            required=self._infer_required_from_response(response),
                            location="body"
                        )
                        results.append(result)
                        diffs.append(diff)
                    
                except Exception as e:
                    print(f"       Payload {candidate_name}: {payload[candidate_name]} - Error: {str(e)}")
                    continue
        
        return results
    
    def _create_test_context(
        self, request: DiscoveryRequest, baseline_fingerprint: ResponseFingerprint,
        candidate_name: Optional[str] = None
    ) -> DiscoveryContext:
        """
        Create test context for differential analysis.
        
        Args:
            request: Original discovery request
            baseline_fingerprint: Baseline fingerprint
            candidate_name: Optional candidate to seed so strategies generate payloads
        Returns:
            Discovery context for testing
        """
        from ..models import DiscoveryContext
        
        discovered = {candidate_name: {"type": "string", "required": False}} if candidate_name else {}
        return DiscoveryContext(
            request=request,
            session_headers=dict(request.headers) if hasattr(request.headers, 'copy') else {},
            discovered_parameters=discovered,
            evidence={'baseline_fingerprint': baseline_fingerprint.__dict__},
            execution_stats={}
        )
    
    def _infer_required_from_response(self, response) -> bool:
        """
        Infer if parameter is required from response characteristics.
        
        Args:
            response: HTTP response object
            
        Returns:
            True if parameter appears to be required
        """
        # Simple heuristic: if response indicates missing required field
        response_text = response.text.lower() if response.text else ""
        
        required_indicators = [
            'is required',
            'is mandatory',
            'must be provided',
            'cannot be null',
            'cannot be empty',
            'missing required'
        ]
        
        return any(indicator in response_text for indicator in required_indicators)


# Factory function for creating differential engine
def create_differential_engine(
    transport_client: TransportClientInterface,
    probe_strategies: Optional[List[ProbeStrategy]] = None
) -> DifferentialEngine:
    """
    Create a differential engine with default strategies.
    
    Args:
        transport_client: HTTP client for making requests
        probe_strategies: Optional list of probe strategies
        
    Returns:
        Configured DifferentialEngine instance
    """
    if probe_strategies is None:
        # Default strategies for comprehensive testing
        probe_strategies = [
            StringProbe(),
            NumericProbe(),
            BooleanProbe()
        ]
    
    return DifferentialEngine(
        transport_client=transport_client,
        probe_strategies=probe_strategies
    )
