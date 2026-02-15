"""
Enhanced endpoint classifier for REST Parameter Discovery v2.

Uses multiple signal sources (baseline status, differential signals,
framework signals, auth detection) for comprehensive endpoint classification.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models import DiscoveryRequest, DiscoveryContext
from ..transport import TransportClientInterface
from ..fingerprint import ResponseFingerprint
from ..scoring.framework_signals import FrameworkSignal, FrameworkSignalDetector, FrameworkType
from ..probes.differential_engine import ParameterCandidate


class EndpointType(Enum):
    """Endpoint classification types."""
    AUTH_PROTECTED = "auth_protected"
    NO_REQUIRED_PARAMS = "no_required_params"
    OPTIONAL_PARAMS_ONLY = "optional_params_only"
    REQUIRED_PARAMS_DETECTED = "required_params_detected"
    INVALID_METHOD = "invalid_method"
    INCONCLUSIVE = "exclusive"
    CRUD = "crud"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    SEARCH = "search"
    WEBHOOK = "webhook"


@dataclass
class ClassificationSignals:
    """
    Signals used for endpoint classification.
    
    Contains evidence from different analysis sources
that contribute to the final classification decision.
    """
    baseline_status: Optional[int] = None
    baseline_content_type: Optional[str] = None
    baseline_response_size: Optional[int] = None
    differential_candidates: Optional[int] = None
    framework_signal: Optional[FrameworkSignal] = None
    auth_required: Optional[bool] = None
    error_indicators: Optional[List[str]] = None
    success_indicators: Optional[List[str]] = None
    method_support: Optional[List[str]] = None
    content_type_support: Optional[List[str]] = None


@dataclass
class EndpointClassification:
    """
    Comprehensive endpoint classification result.
    
    Contains endpoint type, confidence, and detailed evidence
from multiple signal sources.
    """
    endpoint_type: EndpointType
    confidence: float
    evidence: Dict[str, Any]
    signals: ClassificationSignals
    metadata: Dict[str, Any]


class EnhancedEndpointClassifier:
    """
    Enhanced endpoint classifier using multiple signal sources.
    
    Combines baseline analysis, differential signals, framework detection,
and authentication analysis for comprehensive classification.
    """
    
    def __init__(
        self,
        transport_client: Optional[TransportClientInterface] = None,
        framework_detector: Optional[FrameworkSignalDetector] = None
    ):
        """
        Initialize enhanced endpoint classifier.
        
        Args:
            transport_client: Optional HTTP client for requests
            framework_detector: Optional framework detector for analysis
        """
        self.transport_client = transport_client
        self.framework_detector = framework_detector or FrameworkSignalDetector()
    
    async def classify_endpoint(
        self,
        request: DiscoveryRequest,
        initial_response: Optional[Any] = None,
        candidates: Optional[List[ParameterCandidate]] = None
    ) -> EndpointClassification:
        """
        Classify endpoint using multiple signal sources.
        
        Args:
            request: Discovery request with context
            initial_response: Optional initial HTTP response
            candidates: Optional parameter candidates from differential analysis
            
        Returns:
            Comprehensive endpoint classification
        """
        print(f"🔍 Classifying endpoint: {request.method} {request.url}")
        
        # Initialize classification signals
        signals = ClassificationSignals()
        
        # Step 1: Baseline analysis (accept ResponseFingerprint or HTTP response)
        response_text = ""
        if initial_response:
            signals.baseline_status = getattr(initial_response, 'status_code', None) or getattr(initial_response, 'status', None)
            response_text = getattr(initial_response, 'text', None) or getattr(initial_response, 'body_text', None) or ""
            signals.baseline_content_type = self._extract_content_type_from_response(response_text)
            if hasattr(initial_response, 'content_type') and initial_response.content_type:
                signals.baseline_content_type = signals.baseline_content_type or initial_response.content_type
            signals.baseline_response_size = len(response_text) or getattr(initial_response, 'body_length', 0)
        
        # Step 2: Differential analysis
        if candidates:
            signals.differential_candidates = len(candidates)
        
        # Step 3: Framework detection (sync method - no await)
        if self.framework_detector and initial_response and response_text:
            h1 = getattr(initial_response, 'headers', None)
            h2 = getattr(initial_response, 'headers_normalized', None)
            headers = h1 if isinstance(h1, dict) else (h2 if isinstance(h2, dict) else {})
            signals.framework_signal = self.framework_detector.detect_signals(
                response_text=response_text,
                response_headers=headers,
                status_code=signals.baseline_status or 0
            )
        
        # Step 4: Method validation
        signals.method_support = self._validate_method(request.method)
        
        # Step 5: Content-type analysis
        signals.content_type_support = self._analyze_content_type_support(initial_response)
        
        # Step 6: Pattern-based classification
        pattern_evidence = self._extract_classification_patterns(response_text)
        
        # Step 7: Comprehensive classification
        endpoint_type, confidence = self._determine_endpoint_type(
            signals, pattern_evidence, request
        )
        
        # Compile evidence
        evidence = {
            'baseline_analysis': {
                'status_code': signals.baseline_status,
                'content_type': signals.baseline_content_type,
                'response_size': signals.baseline_response_size
            },
            'differential_analysis': {
                'candidates_count': signals.differential_candidates
            },
            'framework_detection': signals.framework_signal.__dict__ if signals.framework_signal else {},
            'method_validation': {
                'supported_methods': signals.method_support
            },
            'content_type_analysis': {
                'supported_types': signals.content_type_support
            },
            'pattern_analysis': pattern_evidence
        }
        
        if signals.framework_signal:
            evidence['framework_detection'] = signals.framework_signal.__dict__
        
        return EndpointClassification(
            endpoint_type=endpoint_type,
            confidence=confidence,
            evidence=evidence,
            signals=signals,
            metadata={
                'classification_method': 'multi_signal_analysis',
                'has_initial_response': initial_response is not None,
                'has_differential_candidates': candidates is not None,
                'framework_detected': signals.framework_signal is not None
            }
        )
    
    def _extract_content_type_from_response(self, response_text: str) -> Optional[str]:
        """Extract content type from response text."""
        content_type_patterns = [
            (r'application/json', 'json'),
            (r'text/html', 'html'),
            (r'application/xml', 'xml'),
            (r'text/plain', 'text'),
            (r'application/x-www-form-urlencoded', 'form'),
            (r'multipart/form-data', 'multipart')
        ]
        
        for pattern, content_type in content_type_patterns:
            if pattern in response_text.lower():
                return content_type
        
        return None
    
    def _analyze_content_type_support(self, response: Optional[Any]) -> List[str]:
        """Analyze content-type support from response."""
        supported_types = []
        
        if not response:
            return supported_types
        
        h1 = getattr(response, 'headers', None)
        h2 = getattr(response, 'headers_normalized', None)
        headers = h1 if isinstance(h1, dict) else (h2 if isinstance(h2, dict) else {})
        
        # Check Accept header
        accept_header = headers.get('accept', '')
        if accept_header:
            supported_types.extend([ct.strip() for ct in str(accept_header).split(',') if ct.strip()])
        
        # Check Content-Type in response
        content_type_header = headers.get('content-type', '')
        if content_type_header:
            supported_types.append(content_type_header.split(';')[0].strip())
        
        return list(set(supported_types))
    
    def _validate_method(self, method: str) -> List[str]:
        """Validate HTTP method and return supported methods."""
        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        
        if method.upper() not in valid_methods:
            return []
        
        # Determine method capabilities based on common patterns
        method_capabilities = [method.upper()]
        
        # Add common method variations
        if method.upper() in ['GET', 'POST']:
            method_capabilities.extend(['JSON', 'Form'])
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            method_capabilities.extend(['Multipart'])
        if method.upper() in ['GET']:
            method_capabilities.extend(['Query'])
        
        return method_capabilities
    
    def _extract_classification_patterns(self, text: str) -> Dict[str, Any]:
        """Extract classification patterns from response text."""
        patterns = {
            'auth_indicators': [],
            'error_indicators': [],
            'success_indicators': [],
            'crud_indicators': [],
            'upload_indicators': [],
            'download_indicators': [],
            'search_indicators': [],
            'webhook_indicators': []
        }
        
        # Authentication indicators
        auth_patterns = [
            r'unauthorized', r'authentication\s+failed', r'access\s+denied',
            r'invalid\s+token', r'expired\s+session', r'login\s+required'
        ]
        for pattern in auth_patterns:
            if isinstance(pattern, str):
                if pattern in text.lower():
                    patterns['auth_indicators'].append(pattern)
            else:
                matches = pattern.findall(text)
                patterns['auth_indicators'].extend(matches)
        
        # Error indicators
        error_patterns = [
            r'error', r'invalid', r'forbidden', r'not\s+found',
            r'missing', r'required', r'unprocessable', r'bad\s+request'
        ]
        for pattern in error_patterns:
            if isinstance(pattern, str):
                if pattern in text.lower():
                    patterns['error_indicators'].append(pattern)
            else:
                matches = pattern.findall(text)
                patterns['error_indicators'].extend(matches)
        
        # Success indicators
        success_patterns = [
            r'success', r'created', r'updated', r'completed', r'ok'
        ]
        for pattern in success_patterns:
            if isinstance(pattern, str):
                if pattern in text.lower():
                    patterns['success_indicators'].append(pattern)
            else:
                matches = pattern.findall(text)
                patterns['success_indicators'].extend(matches)
        
        # CRUD indicators
        crud_patterns = [
            r'create', r'read', r'update', r'delete', r'list', r'get'
        ]
        for pattern in crud_patterns:
            if isinstance(pattern, str):
                if pattern in text.lower():
                    patterns['crud_indicators'].append(pattern)
            else:
                matches = pattern.findall(text)
                patterns['crud_indicators'].extend(matches)
        
        # Upload indicators
        upload_patterns = [
            r'upload', r'file', r'multipart', r'attachment', r'image', r'document'
        ]
        for pattern in upload_patterns:
            if isinstance(pattern, str):
                if pattern in text.lower():
                    patterns['upload_indicators'].append(pattern)
            else:
                matches = pattern.findall(text)
                patterns['upload_indicators'].extend(matches)
        
        # Download indicators
        download_patterns = [
            r'download', r'export', r'file', r'attachment', r'report'
        ]
        for pattern in download_patterns:
            if isinstance(pattern, str):
                if pattern in text.lower():
                    patterns['download_indicators'].append(pattern)
            else:
                matches = pattern.findall(text)
                patterns['download_indicators'].extend(matches)
        
        # Search indicators
        search_patterns = [
            r'search', r'query', r'filter', r'find', r'list', r'get'
        ]
        for pattern in search_patterns:
            if isinstance(pattern, str):
                if pattern in text.lower():
                    patterns['search_indicators'].append(pattern)
            else:
                matches = pattern.findall(text)
                patterns['search_indicators'].extend(matches)
        
        # Webhook indicators
        webhook_patterns = [
            r'webhook', r'callback', r'event', r'notify', r'trigger'
        ]
        for pattern in webhook_patterns:
            if isinstance(pattern, str):
                if pattern in text.lower():
                    patterns['webhook_indicators'].append(pattern)
            else:
                matches = pattern.findall(text)
                patterns['webhook_indicators'].extend(matches)
        
        return patterns
    
    def _determine_endpoint_type(
        self,
        signals: ClassificationSignals,
        pattern_evidence: Dict[str, Any],
        request: DiscoveryRequest
    ) -> Tuple[EndpointType, float]:
        """
        Determine endpoint type and confidence from signals and patterns.
        
        Args:
            signals: Classification signals from analysis
            pattern_evidence: Extracted patterns from response
            request: Discovery request for context
            
        Returns:
            Tuple of endpoint type and confidence
        """
        endpoint_scores = {
            EndpointType.AUTH_PROTECTED: 0.0,
            EndpointType.NO_REQUIRED_PARAMS: 0.0,
            EndpointType.OPTIONAL_PARAMS_ONLY: 0.0,
            EndpointType.REQUIRED_PARAMS_DETECTED: 0.0,
            EndpointType.INVALID_METHOD: 0.0,
            EndpointType.INCONCLUSIVE: 0.0,
            EndpointType.CRUD: 0.3,  # Default assumption
            EndpointType.UPLOAD: 0.0,
            EndpointType.DOWNLOAD: 0.0,
            EndpointType.SEARCH: 0.0,
            EndpointType.WEBHOOK: 0.0
        }
        
        confidence = 0.5  # Base confidence
        
        # Analyze authentication requirements (from pattern_evidence)
        auth_indicators = pattern_evidence.get('auth_indicators', [])
        if auth_indicators:
            endpoint_scores[EndpointType.AUTH_PROTECTED] += 2.0
            confidence += 0.3
        
        # Analyze error patterns
        error_indicators = pattern_evidence.get('error_indicators', [])
        if error_indicators:
            endpoint_scores[EndpointType.AUTH_PROTECTED] += 1.0
            confidence += 0.2
        
        # Analyze success patterns
        success_indicators = pattern_evidence.get('success_indicators', [])
        if success_indicators:
            endpoint_scores[EndpointType.CRUD] += 0.5
            confidence += 0.1
        
        # Analyze CRUD patterns
        crud_indicators = pattern_evidence.get('crud_indicators', [])
        if crud_indicators:
            crud_score = len(crud_indicators)
            if crud_score >= 3:
                endpoint_scores[EndpointType.CRUD] += 1.0
                confidence += 0.3
            elif crud_score >= 2:
                endpoint_scores[EndpointType.CRUD] += 0.5
                confidence += 0.2
            elif crud_score >= 1:
                endpoint_scores[EndpointType.CRUD] += 0.2
                confidence += 0.1
        
        # Analyze upload patterns
        upload_indicators = pattern_evidence.get('upload_indicators', [])
        if upload_indicators:
            endpoint_scores[EndpointType.UPLOAD] += 2.0
            confidence += 0.4
        
        # Analyze download patterns
        download_indicators = pattern_evidence.get('download_indicators', [])
        if download_indicators:
            endpoint_scores[EndpointType.DOWNLOAD] += 1.5
            confidence += 0.3
        
        # Analyze search patterns
        search_indicators = pattern_evidence.get('search_indicators', [])
        if search_indicators:
            endpoint_scores[EndpointType.SEARCH] += 1.0
            confidence += 0.2
        
        # Analyze webhook patterns
        webhook_indicators = pattern_evidence.get('webhook_indicators', [])
        if webhook_indicators:
            endpoint_scores[EndpointType.WEBHOOK] += 1.5
            confidence += 0.2
        
        # Analyze framework signals
        if signals.framework_signal:
            fw_type = signals.framework_signal.framework_type
            if fw_type == FrameworkType.PYTHON_FASTAPI:
                endpoint_scores[EndpointType.CRUD] += 1.0
                confidence += 0.3
            elif fw_type == FrameworkType.NODE_EXPRESS:
                endpoint_scores[EndpointType.CRUD] += 0.5
                confidence += 0.2
            elif fw_type == FrameworkType.PYTHON_FLASK:
                endpoint_scores[EndpointType.CRUD] += 0.4
                confidence += 0.2
        
        # Analyze method capabilities
        if signals.method_support:
            if 'JSON' in signals.method_support:
                endpoint_scores[EndpointType.CRUD] += 0.2
                confidence += 0.1
            if 'Multipart' in signals.method_support:
                endpoint_scores[EndpointType.UPLOAD] += 1.0
                confidence += 0.2
            if 'Query' in signals.method_support:
                endpoint_scores[EndpointType.SEARCH] += 0.5
                confidence += 0.1
        
        # Analyze content-type support
        if signals.content_type_support:
            if 'json' in signals.content_type_support:
                endpoint_scores[EndpointType.CRUD] += 0.2
                confidence += 0.1
            if 'multipart' in signals.content_type_support:
                endpoint_scores[EndpointType.UPLOAD] += 0.5
                confidence += 0.2
        
        # Analyze baseline status
        if signals.baseline_status:
            if signals.baseline_status == 200:
                endpoint_scores[EndpointType.CRUD] += 0.1
                confidence += 0.05
            elif signals.baseline_status in [400, 401, 403]:
                endpoint_scores[EndpointType.AUTH_PROTECTED] += 0.5
                confidence += 0.2
            elif signals.baseline_status in [404, 405]:
                endpoint_scores[EndpointType.NO_REQUIRED_PARAMS] += 0.3
                confidence += 0.1
        
        # Analyze response size
        if signals.baseline_response_size and signals.baseline_response_size > 0:
            if signals.baseline_response_size < 50:  # Small response
                endpoint_scores[EndpointType.OPTIONAL_PARAMS_ONLY] += 0.2
                confidence += 0.1
            elif signals.baseline_response_size < 200:  # Medium response
                endpoint_scores[EndpointType.REQUIRED_PARAMS_DETECTED] += 0.3
                confidence += 0.1
        
        # Determine best endpoint type
        best_endpoint_type = max(endpoint_scores, key=endpoint_scores.get)
        best_score = endpoint_scores[best_endpoint_type]
        
        # Normalize confidence
        normalized_confidence = min(best_score / 3.0, 1.0)  # Normalize to reasonable range
        
        return best_endpoint_type, normalized_confidence


# Factory function
def create_enhanced_classifier(
    transport_client: Optional[TransportClientInterface] = None,
    framework_detector: Optional[FrameworkSignalDetector] = None
) -> EnhancedEndpointClassifier:
    """
    Create an enhanced endpoint classifier with default configuration.
    
    Args:
        transport_client: Optional HTTP client for requests
        framework_detector: Optional framework detector for analysis
        
    Returns:
        Configured EnhancedEndpointClassifier instance
    """
    return EnhancedEndpointClassifier(transport_client, framework_detector)
