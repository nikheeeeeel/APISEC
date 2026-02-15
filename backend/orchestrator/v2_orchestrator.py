"""
REST Parameter Discovery v2 Orchestrator.

Implements complete modular discovery flow with transport layer,
differential engine, location resolver, confidence scoring, framework signals,
and endpoint classification while preserving v1 compatibility.
"""

import time
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..models import DiscoveryRequest, DiscoveryContext, create_legacy_request, create_legacy_context
from ..transport import TransportClientInterface, RequestsTransportClient
from ..probes import ProbeFactory
from ..fingerprint import ResponseFingerprint
from ..probes.differential_engine import DifferentialEngine, create_differential_engine
from ..probes.location_resolver import LocationResolver, create_location_resolver
from ..scoring.confidence_scoring import WeightedConfidenceScorer, create_weighted_scorer
from ..classification.endpoint_classifier import EnhancedEndpointClassifier, create_enhanced_classifier


@dataclass
class OrchestratorConfig:
    """Configuration for orchestrator behavior."""
    enable_v2: bool = os.getenv('ENABLE_REST_V2', 'true').lower() == 'true'
    fallback_to_v1_on_error: bool = False


class V2Orchestrator:
    """
    Complete REST Parameter Discovery v2 orchestrator.
    
    Implements the full modular discovery pipeline with clean separation
of concerns and no business logic in the orchestration layer.
    """
    
    def __init__(
        self,
        config: OrchestratorConfig = OrchestratorConfig()
    ):
        """
        Initialize V2 orchestrator with configuration.
        
        Args:
            config: Orchestrator configuration
        """
        self.config = config
        self.transport_client = RequestsTransportClient()
        self.probe_factory = ProbeFactory()
        self.differential_engine = create_differential_engine(
            transport_client=self.transport_client,
            probe_strategies=self.probe_factory.get_available_probes()
        )
        self.location_resolver = create_location_resolver(
            transport_client=self.transport_client
        )
        self.confidence_scorer = create_weighted_scorer()
        from ..scoring.framework_signals import create_framework_detector
        framework_detector = create_framework_detector()
        self.endpoint_classifier = create_enhanced_classifier(
            transport_client=self.transport_client,
            framework_detector=framework_detector
        )
    
    async def discover_parameters(
        self,
        request: DiscoveryRequest
    ) -> Dict[str, Any]:
        """
        Orchestrate complete parameter discovery using v2 architecture.
        
        Args:
            request: Enhanced discovery request
            
        Returns:
            Dictionary with discovered parameters and comprehensive metadata
        """
        if not self.config.enable_v2:
            # Fallback to v1 if v2 is disabled
            print("🔄 V2 disabled, falling back to v1 inference")
            return await self._fallback_to_v1(request)
        
        print(f"🚀 Starting REST Parameter Discovery v2")
        print(f"Target: {request.url}")
        print(f"Method: {request.method}")
        print(f"Timeout: {request.timeout_seconds}s")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Phase 1: Transport Layer - Baseline Fingerprinting
            print("\n🌐 Phase 1: Transport Layer - Baseline Fingerprinting...")
            baseline_fingerprint = await self._capture_baseline_fingerprint(request)
            
            if not baseline_fingerprint:
                return self._create_error_result(request, "Failed to capture baseline fingerprint", time.time() - start_time)
            
            # Phase 2: Differential Engine - Candidate Generation
            print("\n🔬 Phase 2: Differential Engine - Candidate Generation...")
            candidates = await self.differential_engine.run(request)
            
            # Phase 3: Location Resolver - Optimal Location Testing
            print("\n📍 Phase 3: Location Resolver - Optimal Location Testing...")
            location_results = []
            for candidate in candidates:
                location_result = await self.location_resolver.resolve_location(
                    candidate.name, candidate, request
                )
                if location_result:
                    # Update candidate with location information
                    candidate.evidence['location_resolution'] = location_result.__dict__
                    candidate.provisional_score = location_result.location_score
                    location_results.append(location_result)
            
            # Phase 4: Framework Signals - API Technology Detection
            print("\n🏗️ Phase 4: Framework Signals - API Technology Detection...")
            framework_signal = None
            if baseline_fingerprint:
                body_text = getattr(baseline_fingerprint, 'body_text', None) or ""
                headers = getattr(baseline_fingerprint, 'headers_normalized', None) or {}
                framework_signal = self.endpoint_classifier.framework_detector.detect_signals(
                    response_text=body_text,
                    response_headers=headers,
                    status_code=baseline_fingerprint.status
                )
            
            # Phase 5: Confidence Scoring - Evidence Aggregation
            print("\n📊 Phase 5: Confidence Scoring - Evidence Aggregation...")
            
            # Score all candidates with comprehensive evidence
            scored_parameters = {}
            for candidate in candidates:
                # Combine all evidence sources
                evidence_sources = ['differential_engine']
                if framework_signal:
                    evidence_sources.append('framework_signals')
                
                # Calculate confidence using weighted scorer
                confidence_result = self.confidence_scorer.calculate_parameter_confidence(
                    parameter_name=candidate.name,
                    evidence_sources=evidence_sources,
                    framework_signals=framework_signal.__dict__ if framework_signal else None,
                    location_tests=[location_result.__dict__ for location_result in location_results if location_result]
                )
                
                if confidence_result.confidence > 0.3:  # Only include confident parameters
                    scored_parameters[candidate.name] = {
                        'name': candidate.name,
                        'type': confidence_result.evidence.get('parameter_type', 'string'),
                        'location': confidence_result.location,
                        'required': confidence_result.evidence.get('required', False),
                        'confidence': confidence_result.confidence,
                        'evidence': confidence_result.evidence,
                        'sources': confidence_result.sources
                    }
            
            # Phase 6: Endpoint Classification - Strategy Selection
            print("\n🎯 Phase 6: Endpoint Classification - Strategy Selection...")
            
            # Classify endpoint for strategy selection
            endpoint_classification = await self.endpoint_classifier.classify_endpoint(
                request=request,
                initial_response=baseline_fingerprint,
                candidates=candidates
            )
            
            # Phase 7: Result Assembly - Final Output
            print("\n📋 Phase 7: Result Assembly - Final Output...")
            
            # Filter parameters by confidence threshold
            final_parameters = {
                name: info['name']
                for name, info in scored_parameters.items()
                if info['confidence'] > 0.3
            }
            
            # Assemble comprehensive result
            execution_time = time.time() - start_time
            
            result = {
                'url': request.url,
                'method': request.method,
                'parameters': list(final_parameters.values()),
                'meta': {
                    'total_parameters': len(final_parameters),
                    'execution_time_ms': int(execution_time * 1000),
                    'discovery_version': 'v2',
                    'orchestration_phases': [
                        'baseline_fingerprinting',
                        'differential_engine',
                        'location_resolver',
                        'framework_signals',
                        'confidence_scoring',
                        'endpoint_classification'
                    ],
                    'v2_features': {
                        'differential_candidates': len(candidates),
                        'location_testing': len(location_results),
                        'framework_detected': endpoint_classification.signals.framework_signal is not None,
                        'weighted_scoring': True,
                        'enhanced_classification': True
                    },
                    'baseline_fingerprint': baseline_fingerprint.__dict__,
                    'endpoint_classification': endpoint_classification.__dict__,
                    'differential_analysis': {
                        'candidates': [candidate.__dict__ for candidate in candidates]
                    },
                    'location_resolution': {
                        c.name: lr.__dict__ for c, lr in zip(candidates, location_results)
                    } if len(candidates) == len(location_results) else {},
                    'confidence_scoring': {
                        name: info for name, info in scored_parameters.items()
                    }
                }
            }
            
            print(f"\n✅ Discovery Complete: {len(result['parameters'])} parameters")
            print(f"⏱️  Execution Time: {result['meta']['execution_time_ms']}ms")
            
            return result
            
        except Exception as e:
            print(f"\n❌ Discovery Failed: {str(e)}")
            return self._create_error_result(request, str(e), time.time() - start_time)
    
    async def _capture_baseline_fingerprint(self, request: DiscoveryRequest) -> Optional[ResponseFingerprint]:
        """Capture baseline fingerprint for differential analysis."""
        try:
            response = await self.transport_client.send(
                request=request,
                payload={},  # Empty payload for baseline
                location="body"
            )
            
            from ..fingerprint import create_fingerprint
            return create_fingerprint(
                status_code=response.status_code,
                body=response.text or "",
                headers=dict(response.headers),
                response_time_ms=100.0
            )
            
        except Exception as e:
            print(f"   Baseline capture failed: {str(e)}")
            return None
    
    async def _fallback_to_v1(self, request: DiscoveryRequest) -> Dict[str, Any]:
        """Fallback to v1 inference pipeline."""
        print("🔄 Falling back to v1 inference pipeline")
        
        # Import v1 orchestrator for fallback
        try:
            from .discovery_orchestrator import legacy_orchestrate_inference as v1_orchestrate
            
            # Create v1 request from v2 request
            v1_request = create_legacy_request(
                url=request.url,
                method=request.method,
                max_time_seconds=request.timeout_seconds
            )
            
            # Run v1 inference
            result = await v1_orchestrate(v1_request)
            
            # Mark as v1 result for compatibility
            if 'meta' in result:
                result['meta']['discovery_version'] = 'v1_fallback'
            
            return result
            
        except Exception as e:
            return self._create_error_result(request, f"V1 fallback failed: {str(e)}", 0.0)
    
    def _create_error_result(self, request: DiscoveryRequest, error_message: str, execution_time: float) -> Dict[str, Any]:
        """Create standardized error result."""
        return {
            'url': request.url,
            'method': request.method,
            'parameters': [],
            'meta': {
                'total_parameters': 0,
                'execution_time_ms': int(execution_time * 1000),
                'error': error_message,
                'discovery_version': 'v2'
            }
        }


# Factory function
def create_v2_orchestrator(
    enable_v2: Optional[bool] = None,
    fallback_to_v1_on_error: Optional[bool] = None
) -> V2Orchestrator:
    """
    Create a V2 orchestrator with configuration.
    
    Args:
        enable_v2: Force enable v2 (overrides environment variable)
        fallback_to_v1_on_error: Fallback to v1 on errors
        
    Returns:
        Configured V2Orchestrator instance
    """
    env_enable_v2 = enable_v2 if enable_v2 is not None else os.getenv('ENABLE_REST_V2', 'true').lower() == 'true'
    env_fallback = fallback_to_v1_on_error if fallback_to_v1_on_error is not None else False

    config = OrchestratorConfig(
        enable_v2=env_enable_v2,
        fallback_to_v1_on_error=env_fallback
    )
    
    return V2Orchestrator(config=config)


# Backward compatibility - enhanced v2 entry point
async def orchestrate_inference_v2(
    url: str,
    method: str = "POST",
    max_time_seconds: int = 30
) -> Dict[str, Any]:
    """
    Enhanced v2 inference entry point with feature flag support.
    
    Args:
        url: Target API endpoint
        method: HTTP method
        max_time_seconds: Maximum execution time
        
    Returns:
        Discovery result using v2 architecture if enabled
    """
    from ..models import DiscoveryRequest
    
    # Create v2 orchestrator
    orchestrator = create_v2_orchestrator()
    
    # Create v2 request
    request = DiscoveryRequest(
        url=url,
        method=method,
        timeout_seconds=max_time_seconds
    )
    
    # Run v2 orchestration
    return await orchestrator.discover_parameters(request)
