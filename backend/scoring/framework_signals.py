"""
Framework signals detection for REST Parameter Discovery v2.

Detects API framework patterns and provides structured signal analysis
for confidence scoring and strategy selection.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class FrameworkType(Enum):
    """Supported framework types for signal detection."""
    NODE_EXPRESS = "node_express"
    NODE_NEST = "node_nest"
    PYTHON_FLASK = "python_flask"
    PYTHON_FASTAPI = "python_fastapi"
    PYTHON_DRF = "python_drf"
    JAVA_SPRING = "java_spring"
    JAVA_SPRING_BOOT = "java_spring_boot"
    RUBY_RAILS = "ruby_rails"
    PHP_LARAVEL = "php_laravel"
    PHP_WORDPRESS = "php_wordpress"
    ASP_NET_CORE = "asp_net_core"
    DOT_NET_CORE = "dot_net_core"


@dataclass
class FrameworkSignal:
    """
    Structured framework detection signal.
    
    Contains detected framework type, confidence, and supporting evidence.
    """
    framework_type: FrameworkType
    confidence: float
    evidence: Dict[str, Any]
    signal_patterns: List[str]
    metadata: Dict[str, Any]


class FrameworkSignalDetector:
    """
    Advanced framework signal detector with pattern matching.
    
    Detects framework-specific patterns in HTTP responses, headers,
and error messages to provide structured signals for confidence scoring.
    """
    
    def __init__(self):
        """Initialize framework signal detector."""
        self.patterns = self._initialize_detection_patterns()
    
    def _initialize_detection_patterns(self) -> Dict[FrameworkType, List[re.Pattern]]:
        """
        Initialize comprehensive detection patterns for frameworks.
        
        Returns:
            Dictionary mapping framework types to regex patterns
        """
        return {
            FrameworkType.NODE_EXPRESS: [
                # Express.js patterns
                re.compile(r'express\s+\d+\.\d+\.\d+', re.IGNORECASE),
                re.compile(r'"message":\s*"[^"]*[^"]*required"', re.IGNORECASE),
                re.compile(r'Cannot\s+POST\s*/', re.IGNORECASE),
                re.compile(r'Error:\s*[^"]*[^"]*is\s+required', re.IGNORECASE),
                re.compile(r'X-Powered-By:\s*Express', re.IGNORECASE),
                re.compile(r'app\.set\s*\(\s*["\']([^"\']+)["\']\s*\)', re.IGNORECASE)
            ],
            
            FrameworkType.NODE_NEST: [
                # Nest.js patterns
                re.compile(r'nest\s+framework', re.IGNORECASE),
                re.compile(r'"engine":\s*"nest"', re.IGNORECASE),
                re.compile(r'@nestjs', re.IGNORECASE),
                re.compile(r'nestjs', re.IGNORECASE),
                re.compile(r'node_modules/@nestjs', re.IGNORECASE)
            ],
            
            FrameworkType.PYTHON_FLASK: [
                # Flask patterns
                re.compile(r'flask\s+\d+\.\d+\.\d+', re.IGNORECASE),
                re.compile(r'werkzeug', re.IGNORECASE),
                re.compile(r'jinja2', re.IGNORECASE),
                re.compile(r'Internal\s+Server\s+Error', re.IGNORECASE),
                re.compile(r'KeyError\s*\'[^\']*\'', re.IGNORECASE),
                re.compile(r'flask\.app\.Flask', re.IGNORECASE)
            ],
            
            FrameworkType.PYTHON_FASTAPI: [
                # FastAPI patterns
                re.compile(r'fastapi', re.IGNORECASE),
                re.compile(r'"type":\s*"validation_error"', re.IGNORECASE),
                re.compile(r'"loc":\s*\["[^"]*"', re.IGNORECASE),
                re.compile(r'422\s+Unprocessable\s+Entity', re.IGNORECASE),
                re.compile(r'pydantic\.ValidationError', re.IGNORECASE),
                re.compile(r'"detail":\s*"[^"]*missing"', re.IGNORECASE),
                re.compile(r'@app\.get', re.IGNORECASE)
            ],
            
            FrameworkType.PYTHON_DRF: [
                # Django REST Framework patterns
                re.compile(r'django\s+rest\s+framework', re.IGNORECASE),
                re.compile(r'"detail":\s*"[^"]*[^"]*"', re.IGNORECASE),
                re.compile(r'"field":\s*"[^"]*"', re.IGNORECASE),
                re.compile(r'non_field_errors', re.IGNORECASE),
                re.compile(r'Integrity\s+Error', re.IGNORECASE),
                re.compile(r'ValidationError', re.IGNORECASE)
            ],
            
            FrameworkType.JAVA_SPRING: [
                # Spring Framework patterns
                re.compile(r'org\.springframework', re.IGNORECASE),
                re.compile(r'"timestamp":\s*\d{13}', re.IGNORECASE),
                re.compile(r'"status":\s*\d{3}', re.IGNORECASE),
                re.compile(r'"error":\s*"[^"]*[^"]*required"', re.IGNORECASE),
                re.compile(r'spring\s+boot', re.IGNORECASE),
                re.compile(r'whitelabel\.error', re.IGNORECASE)
            ],
            
            FrameworkType.JAVA_SPRING_BOOT: [
                # Spring Boot patterns
                re.compile(r'"error":\s*"[^"]*[^"]*required"', re.IGNORECASE),
                re.compile(r'"type":\s*"about:blank"', re.IGNORECASE),
                re.compile(r'@SpringBootApplication', re.IGNORECASE),
                re.compile(r'spring\.boot\.autoconfigure', re.IGNORECASE)
            ],
            
            FrameworkType.RUBY_RAILS: [
                # Ruby on Rails patterns
                re.compile(r'rails\s+\d+\.\d+\.\d+', re.IGNORECASE),
                re.compile(r'"errors":\s*\{[^}]*\}', re.IGNORECASE),
                re.compile(r'ActionController', re.IGNORECASE),
                re.compile(r'param\s+is\s+missing\s+or\s+the\s+value\s+is\s+invalid', re.IGNORECASE),
                re.compile(r'ActiveRecord::RecordInvalid', re.IGNORECASE)
            ],
            
            FrameworkType.PHP_LARAVEL: [
                # Laravel patterns
                re.compile(r'laravel', re.IGNORECASE),
                re.compile(r'"message":\s*"[^"]*[^"]*required"', re.IGNORECASE),
                re.compile(r'The\s+given\s+data\s+was\s+invalid', re.IGNORECASE),
                re.compile(r'Illuminate', re.IGNORECASE),
                re.compile(r'validation\.exception', re.IGNORECASE)
            ],
            
            FrameworkType.PHP_WORDPRESS: [
                # WordPress patterns
                re.compile(r'wordpress', re.IGNORECASE),
                re.compile(r'wp-json', re.IGNORECASE),
                re.compile(r'wp-admin', re.IGNORECASE),
                re.compile(r'wp-api', re.IGNORECASE)
            ],
            
            FrameworkType.ASP_NET_CORE: [
                # ASP.NET Core patterns
                re.compile(r'\.NET\s+Core', re.IGNORECASE),
                re.compile(r'"type":\s*"[^"]*[^"]*required"', re.IGNORECASE),
                re.compile(r'"$id":\s*"[^"]*"', re.IGNORECASE),
                re.compile(r'Microsoft\.AspNetCore', re.IGNORECASE),
                re.compile(r'controller\.Base', re.IGNORECASE)
            ],
            
            FrameworkType.DOT_NET_CORE: [
                # .NET Core patterns
                re.compile(r'\.NET\s+Core', re.IGNORECASE),
                re.compile(r'"type":\s*"[^"]*[^"]*required"', re.IGNORECASE),
                re.compile(r'System\.Web\.HttpException', re.IGNORECASE)
            ]
        }
    
    def detect_signals(
        self,
        response_text: str,
        response_headers: Dict[str, str],
        status_code: int,
        response_body: Optional[str] = None
    ) -> FrameworkSignal:
        """
        Detect framework signals from HTTP response.
        
        Args:
            response_text: HTTP response body text
            response_headers: HTTP response headers
            status_code: HTTP status code
            response_body: Optional response body (separate from text)
            
        Returns:
            FrameworkSignal with detected framework and confidence
        """
        framework_scores = {fw_type: 0.0 for fw_type in FrameworkType}
        detected_patterns = []
        evidence = {}
        
        # Check each framework type
        for framework_type, patterns in self.patterns.items():
            score = 0.0
            matched_patterns = []
            
            for pattern in patterns:
                matches = []
                
                # Search in response text
                if response_text:
                    text_matches = pattern.findall(response_text)
                    matches.extend(text_matches)
                
                # Search in response headers
                for header_name, header_value in response_headers.items():
                    header_matches = pattern.findall(header_value)
                    matches.extend(header_matches)
                
                # Search in response body if provided
                if response_body:
                    body_matches = pattern.findall(response_body)
                    matches.extend(body_matches)
                
                if matches:
                    score += 0.5  # Base score for pattern match
                    matched_patterns.extend([pattern.pattern for _ in matches])
            
            if score > 0:
                framework_scores[framework_type] = score
                evidence[f'patterns_{framework_type.value}'] = matched_patterns
            
            if matched_patterns:
                detected_patterns.extend(matched_patterns)
        
        # Determine best framework
        if not framework_scores or max(framework_scores.values()) == 0:
            return FrameworkSignal(
                framework_type=FrameworkType.PYTHON_FASTAPI,  # Default assumption
                confidence=0.1,
                evidence={'no_patterns_detected': True},
                signal_patterns=[],
                metadata={'detection_method': 'pattern_matching'}
            )
        
        best_framework_type = max(framework_scores, key=framework_scores.get)
        best_score = framework_scores[best_framework_type]
        
        # Normalize confidence
        normalized_confidence = min(best_score / 2.0, 1.0)  # Normalize to 0-1 range
        
        return FrameworkSignal(
            framework_type=best_framework_type,
            confidence=normalized_confidence,
            evidence={
                'framework_scores': framework_scores,
                'best_framework': best_framework_type.value,
                'detected_patterns': detected_patterns,
                'pattern_matches': {best_framework_type.value: detected_patterns}
            },
            signal_patterns=detected_patterns,
            metadata={
                'detection_method': 'pattern_matching',
                'total_patterns_tested': len(self.patterns),
                'patterns_matched': len(detected_patterns)
            }
        )
    
    def get_framework_specific_strategies(
        self,
        framework_type: FrameworkType
    ) -> List[str]:
        """
        Get recommended probe strategies for a detected framework.
        
        Args:
            framework_type: Detected framework type
            
        Returns:
            List of recommended strategy names
        """
        strategy_map = {
            FrameworkType.NODE_EXPRESS: ['string_probe', 'boundary_probe', 'error_probe'],
            FrameworkType.NODE_NEST: ['string_probe', 'object_probe', 'error_probe'],
            FrameworkType.PYTHON_FLASK: ['string_probe', 'null_probe', 'error_probe'],
            FrameworkType.PYTHON_FASTAPI: ['string_probe', 'type_probe', 'null_probe', 'boundary_probe'],
            FrameworkType.PYTHON_DRF: ['string_probe', 'object_probe', 'error_probe', 'null_probe'],
            FrameworkType.JAVA_SPRING: ['string_probe', 'object_probe', 'boundary_probe', 'error_probe'],
            FrameworkType.JAVA_SPRING_BOOT: ['string_probe', 'object_probe', 'boundary_probe', 'error_probe'],
            FrameworkType.RUBY_RAILS: ['string_probe', 'object_probe', 'error_probe'],
            FrameworkType.PHP_LARAVEL: ['string_probe', 'boundary_probe', 'error_probe'],
            FrameworkType.PHP_WORDPRESS: ['string_probe', 'boundary_probe', 'error_probe'],
            FrameworkType.ASP_NET_CORE: ['string_probe', 'object_probe', 'boundary_probe', 'error_probe'],
            FrameworkType.DOT_NET_CORE: ['string_probe', 'object_probe', 'boundary_probe', 'error_probe']
        }
        
        return strategy_map.get(framework_type, ['error_probe'])


# Factory function
def create_framework_detector() -> FrameworkSignalDetector:
    """
    Create a framework signal detector with default configuration.
    
    Returns:
        Configured FrameworkSignalDetector instance
    """
    return FrameworkSignalDetector()
