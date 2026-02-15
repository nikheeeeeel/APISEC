"""
Mock validation scenarios for REST Parameter Discovery v2.

Provides deterministic test scenarios without network dependencies
for CI/CD pipeline validation and behavioral testing.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from validation.validation_interfaces import (
    ValidationEngine, ValidationCategory, ValidationStatus, 
    ValidationResult, ValidationConfig, ParameterDiscoveryEngine
)


@dataclass
class MockScenario:
    """Mock scenario for validation testing."""
    name: str
    endpoint_type: str
    expected_parameters: List[str]
    expected_confidence: float
    mock_response: Dict[str, Any]
    should_succeed: bool = True


class MockParameterDiscoveryEngine:
    """Mock parameter discovery engine for testing."""
    
    def __init__(self):
        """Initialize mock discovery engine."""
        self.scenarios = {
            "required_param": MockScenario(
                name="required_param",
                endpoint_type="required",
                expected_parameters=["user_id", "content"],
                expected_confidence=0.8,
                mock_response={
                    "parameters": [
                        {"name": "user_id", "type": "integer", "required": True, "confidence": 0.8},
                        {"name": "content", "type": "string", "required": True, "confidence": 0.8}
                    ],
                    "meta": {"total_parameters": 2, "execution_time_ms": 1000}
                }
            ),
            "optional_param": MockScenario(
                name="optional_param",
                endpoint_type="optional",
                expected_parameters=["filter"],
                expected_confidence=0.5,
                mock_response={
                    "parameters": [
                        {"name": "filter", "type": "string", "required": False, "confidence": 0.5}
                    ],
                    "meta": {"total_parameters": 1, "execution_time_ms": 800}
                }
            ),
            "empty_response": MockScenario(
                name="empty_response",
                endpoint_type="empty",
                expected_parameters=[],
                expected_confidence=0.0,
                mock_response={
                    "parameters": [],
                    "meta": {"total_parameters": 0, "execution_time_ms": 500}
                }
            ),
            "type_sensitive": MockScenario(
                name="type_sensitive",
                endpoint_type="typed",
                expected_parameters=["age", "price"],
                expected_confidence=0.9,
                mock_response={
                    "parameters": [
                        {"name": "age", "type": "integer", "required": True, "confidence": 0.9},
                        {"name": "price", "type": "float", "required": True, "confidence": 0.9}
                    ],
                    "meta": {"total_parameters": 2, "execution_time_ms": 1200}
                }
            ),
            "false_positive": MockScenario(
                name="false_positive",
                endpoint_type="random",
                expected_parameters=[],
                expected_confidence=0.0,
                mock_response={
                    "parameters": [],
                    "meta": {"total_parameters": 0, "execution_time_ms": 300}
                }
            )
        }
    
    async def discover_parameters(self, request: 'DiscoveryRequest') -> Dict[str, Any]:
        """Mock parameter discovery based on URL patterns."""
        from ..models import DiscoveryRequest
        
        url = request.url.lower()
        
        # Determine scenario based on URL pattern
        if "required" in url:
            scenario = self.scenarios["required_param"]
        elif "optional" in url:
            scenario = self.scenarios["optional_param"]
        elif "empty" in url:
            scenario = self.scenarios["empty_response"]
        elif "type" in url:
            scenario = self.scenarios["type_sensitive"]
        elif "random" in url:
            scenario = self.scenarios["false_positive"]
        else:
            # Default to required param scenario
            scenario = self.scenarios["required_param"]
        
        # Simulate processing time
        await asyncio.sleep(0.1)  # Simulate network delay
        
        return scenario.mock_response


class BehavioralValidationEngine(ValidationEngine):
    """Validates behavioral correctness with mock scenarios."""
    
    def __init__(self, discovery_engine: ParameterDiscoveryEngine):
        """Initialize with discovery engine."""
        self.discovery_engine = discovery_engine
        self.category = ValidationCategory.BEHAVIORAL_CORRECTNESS
    
    async def validate(self, config: ValidationConfig) -> List[ValidationResult]:
        """Validate behavioral correctness with mock scenarios."""
        results = []
        
        # Test 1: Required parameter detection
        start_time = time.time()
        try:
            from ..models import DiscoveryRequest
            
            request = DiscoveryRequest(
                url="https://api.example.com/required",
                method="POST",
                timeout_seconds=5
            )
            
            result = await self.discovery_engine.discover_parameters(request)
            
            param_count = len(result.get('parameters', []))
            expected_count = 2  # From mock scenario
            
            success = param_count >= expected_count
            
            results.append(ValidationResult(
                test_name="required_parameter_detection",
                status=ValidationStatus.PASS if success else ValidationStatus.FAIL,
                message=f"Required parameter detection: {param_count} >= {expected_count}" if success else f"Insufficient parameters: {param_count} < {expected_count}",
                details={
                    "parameter_count": param_count,
                    "expected_count": expected_count,
                    "parameters": result.get('parameters', [])
                },
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="required_parameter_detection",
                status=ValidationStatus.FAIL,
                message=f"Error in required parameter detection: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        # Test 2: Optional parameter handling
        start_time = time.time()
        try:
            from ..models import DiscoveryRequest
            
            request = DiscoveryRequest(
                url="https://api.example.com/optional",
                method="GET",
                timeout_seconds=5
            )
            
            result = await self.discovery_engine.discover_parameters(request)
            
            # Should handle gracefully
            completed_successfully = 'error' not in result.get('meta', {})
            
            results.append(ValidationResult(
                test_name="optional_parameter_handling",
                status=ValidationStatus.PASS if completed_successfully else ValidationStatus.FAIL,
                message="Optional parameter handling successful" if completed_successfully else "Failed to handle optional parameters",
                details={
                    "completed_successfully": completed_successfully,
                    "meta": result.get('meta', {})
                },
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="optional_parameter_handling",
                status=ValidationStatus.FAIL,
                message=f"Error in optional parameter handling: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        # Test 3: Type-sensitive validation
        start_time = time.time()
        try:
            from ..models import DiscoveryRequest
            
            request = DiscoveryRequest(
                url="https://api.example.com/type",
                method="POST",
                timeout_seconds=5
            )
            
            result = await self.discovery_engine.discover_parameters(request)
            
            # Check for type information
            parameters = result.get('parameters', [])
            has_type_info = all('type' in param for param in parameters)
            
            results.append(ValidationResult(
                test_name="type_sensitive_validation",
                status=ValidationStatus.PASS if has_type_info else ValidationStatus.WARN,
                message="Type information present in parameters" if has_type_info else "Missing type information in parameters",
                details={
                    "has_type_info": has_type_info,
                    "parameter_count": len(parameters),
                    "parameters": parameters
                },
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="type_sensitive_validation",
                status=ValidationStatus.FAIL,
                message=f"Error in type-sensitive validation: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        # Test 4: False positive prevention
        start_time = time.time()
        try:
            from ..models import DiscoveryRequest
            
            request = DiscoveryRequest(
                url="https://api.example.com/random",
                method="GET",
                timeout_seconds=5
            )
            
            result = await self.discovery_engine.discover_parameters(request)
            
            # Should not detect parameters in random data
            has_params = len(result.get('parameters', [])) > 0
            
            results.append(ValidationResult(
                test_name="false_positive_prevention",
                status=ValidationStatus.PASS if not has_params else ValidationStatus.WARN,
                message="Random data should not trigger parameter discovery" if not has_params else "Unexpected parameters detected in random data",
                details={
                    "parameter_count": len(result.get('parameters', [])),
                    "parameters": result.get('parameters', [])
                },
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="false_positive_prevention",
                status=ValidationStatus.FAIL,
                message=f"Error in false positive prevention: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        return results
    
    def get_category(self) -> ValidationCategory:
        """Return validation category."""
        return self.category


class ConfidenceQualityEngine(ValidationEngine):
    """Validates confidence quality and thresholds."""
    
    def __init__(self):
        """Initialize confidence quality validator."""
        self.category = ValidationCategory.FALSE_POSITIVE_PREVENTION
    
    async def validate(self, config: ValidationConfig) -> List[ValidationResult]:
        """Validate confidence quality metrics."""
        results = []
        
        # Test 1: Minimum average confidence for confirmed parameters
        start_time = time.time()
        try:
            from ..scoring.confidence_scoring import WeightedConfidenceScorer
            
            scorer = WeightedConfidenceScorer()
            
            # Test with high confidence parameters
            high_confidence_result = scorer.calculate_parameter_confidence(
                parameter_name="test_param",
                evidence_sources=['probe_string', 'probe_numeric', 'detection_fastapi'],
                framework_signals={'framework_detection': {'detected_type': 'python_fastapi', 'confidence': 0.9}}
            )
            
            min_confirmed = config.confidence_thresholds.get('min_confirmed', 0.75)
            meets_threshold = high_confidence_result.confidence >= min_confirmed
            
            results.append(ValidationResult(
                test_name="minimum_confidence_threshold",
                status=ValidationStatus.PASS if meets_threshold else ValidationStatus.FAIL,
                message=f"Confidence meets minimum threshold: {high_confidence_result.confidence:.2f} >= {min_confirmed:.2f}" if meets_threshold else f"Confidence below threshold: {high_confidence_result.confidence:.2f} < {min_confirmed:.2f}",
                details={
                    "confidence": high_confidence_result.confidence,
                    "threshold": min_confirmed,
                    "sources": high_confidence_result.sources
                },
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="minimum_confidence_threshold",
                status=ValidationStatus.FAIL,
                message=f"Error in confidence threshold test: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        # Test 2: Maximum confidence threshold for false positives
        start_time = time.time()
        try:
            from ..scoring.confidence_scoring import WeightedConfidenceScorer
            
            scorer = WeightedConfidenceScorer()
            
            # Test with low confidence parameters
            low_confidence_result = scorer.calculate_parameter_confidence(
                parameter_name="test_param",
                evidence_sources=['probe_string'],  # Single source
                framework_signals={'framework_detection': {'detected_type': 'unknown', 'confidence': 0.1}}
            )
            
            max_false_positive = config.confidence_thresholds.get('max_false_positive', 0.4)
            below_threshold = low_confidence_result.confidence <= max_false_positive
            
            results.append(ValidationResult(
                test_name="maximum_false_positive_threshold",
                status=ValidationStatus.PASS if below_threshold else ValidationStatus.WARN,
                message=f"Confidence below false positive threshold: {low_confidence_result.confidence:.2f} <= {max_false_positive:.2f}" if below_threshold else f"Confidence above false positive threshold: {low_confidence_result.confidence:.2f} > {max_false_positive:.2f}",
                details={
                    "confidence": low_confidence_result.confidence,
                    "threshold": max_false_positive,
                    "sources": low_confidence_result.sources
                },
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="maximum_false_positive_threshold",
                status=ValidationStatus.FAIL,
                message=f"Error in false positive threshold test: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        return results
    
    def get_category(self) -> ValidationCategory:
        """Return validation category."""
        return self.category
