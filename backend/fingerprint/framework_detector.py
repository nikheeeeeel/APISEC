"""
Framework detection for REST Parameter Discovery v2.

Identifies API frameworks and technologies to enable
framework-specific parameter discovery strategies.
"""

import re
from typing import Dict, List, Optional, Tuple
from ..models import DetectionResult, DiscoveryContext
from ..transport import HttpClientInterface


class FrameworkDetector:
    """
    Detects API frameworks from HTTP responses and URL patterns.
    
    Supports major frameworks: FastAPI, Express, Django, Spring Boot,
Ruby on Rails, ASP.NET Core, Flask, etc.
    """
    
    def __init__(self, http_client: Optional[HttpClientInterface] = None):
        """
        Initialize framework detector.
        
        Args:
            http_client: Optional HTTP client for making requests
        """
        self.http_client = http_client
        self.framework_patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Initialize regex patterns for framework detection."""
        return {
            'fastapi': [
                re.compile(r'"detail":\s*"[^"]*missing"', re.IGNORECASE),
                re.compile(r'"loc":\s*\["[^"]*"', re.IGNORECASE),
                re.compile(r'422\s+Unprocessable\s+Entity', re.IGNORECASE),
                re.compile(r'FastAPI', re.IGNORECASE),
                re.compile(r'"type":\s*"validation_error"', re.IGNORECASE)
            ],
            'express': [
                re.compile(r'Express\s*\d+\.\d+\.\d+', re.IGNORECASE),
                re.compile(r'"message":\s*"[^"]*[^"]*required"', re.IGNORECASE),
                re.compile(r'Cannot\s+POST\s*/', re.IGNORECASE),
                re.compile(r'Error:\s*[^"]*[^"]*is\s+required', re.IGNORECASE)
            ],
            'django': [
                re.compile(r'Django\s*\d+\.\d+\.\d+', re.IGNORECASE),
                re.compile(r'"field":\s*"[^"]*"', re.IGNORECASE),
                re.compile(r'This\s+field\s+may\s+not\s+be\s+blank', re.IGNORECASE),
                re.compile(r'Integrity\s+Error', re.IGNORECASE),
                re.compile(r'ValidationError', re.IGNORECASE)
            ],
            'spring_boot': [
                re.compile(r'Spring\s+Boot', re.IGNORECASE),
                re.compile(r'"timestamp":\s*\d{13}', re.IGNORECASE),
                re.compile(r'"status":\s*\d{3}', re.IGNORECASE),
                re.compile(r'"error":\s*"[^"]*[^"]*required"', re.IGNORECASE),
                re.compile(r'org\.springframework', re.IGNORECASE)
            ],
            'rails': [
                re.compile(r'Rails\s*\d+\.\d+\.\d+', re.IGNORECASE),
                re.compile(r'"errors":\s*\{[^}]*\}', re.IGNORECASE),
                re.compile(r'ActionController', re.IGNORECASE),
                re.compile(r'param\s+is\s+missing\s+or\s+the\s+value\s+is\s+invalid', re.IGNORECASE)
            ],
            'aspnet_core': [
                re.compile(r'\.NET\s+Core', re.IGNORECASE),
                re.compile(r'"type":\s*"[^"]*[^"]*required"', re.IGNORECASE),
                re.compile(r'"$id":\s*"[^"]*"', re.IGNORECASE),
                re.compile(r'Microsoft\.AspNetCore', re.IGNORECASE)
            ],
            'flask': [
                re.compile(r'Flask\s*\d+\.\d+\.\d+', re.IGNORECASE),
                re.compile(r'KeyError\s*\'[^\']*\'', re.IGNORECASE),
                re.compile(r'werkzeug', re.IGNORECASE),
                re.compile(r'Internal\s+Server\s+Error', re.IGNORECASE)
            ],
            'laravel': [
                re.compile(r'Laravel', re.IGNORECASE),
                re.compile(r'"message":\s*"[^"]*[^"]*required"', re.IGNORECASE),
                re.compile(r'The\s+given\s+data\s+was\s+invalid', re.IGNORECASE),
                re.compile(r'Illuminate', re.IGNORECASE)
            ]
        }
    
    async def detect_framework(
        self, 
        context: DiscoveryContext,
        sample_response: Optional[str] = None
    ) -> DetectionResult:
        """
        Detect API framework from context and sample response.
        
        Args:
            context: Discovery context with request information
            sample_response: Optional sample HTTP response for analysis
            
        Returns:
            DetectionResult with framework information and confidence
        """
        framework_scores = {}
        evidence = {}
        
        # Analyze URL patterns
        url_analysis = self._analyze_url_patterns(context.request.url)
        for framework, score in url_analysis.items():
            framework_scores[framework] = framework_scores.get(framework, 0) + score
            evidence[f'url_pattern_{framework}'] = score
        
        # Analyze sample response if provided
        if sample_response:
            response_analysis = self._analyze_response_content(sample_response)
            for framework, score in response_analysis.items():
                framework_scores[framework] = framework_scores.get(framework, 0) + score
                evidence[f'response_pattern_{framework}'] = score
        
        # Determine most likely framework
        if not framework_scores:
            return DetectionResult(
                detected_type="unknown",
                confidence=0.0,
                evidence={"message": "No framework patterns detected"}
            )
        
        best_framework = max(framework_scores, key=framework_scores.get)
        confidence = min(framework_scores[best_framework] / 2.0, 1.0)  # Normalize to 0-1 range
        
        return DetectionResult(
            detected_type=best_framework,
            confidence=confidence,
            evidence={
                "framework_scores": framework_scores,
                "best_match": best_framework,
                **evidence
            },
            metadata={
                "total_patterns_matched": sum(framework_scores.values()),
                "alternatives": [
                    fw for fw, score in sorted(framework_scores.items(), key=lambda x: x[1], reverse=True)
                    if fw != best_framework and score > 0
                ]
            }
        )
    
    def _analyze_url_patterns(self, url: str) -> Dict[str, float]:
        """Analyze URL patterns for framework detection."""
        scores = {}
        url_lower = url.lower()
        
        # Framework-specific URL patterns
        if any(pattern in url_lower for pattern in ['/api/', '/v1/', '/v2/']):
            scores['fastapi'] += 0.2
            scores['express'] += 0.2
            scores['django'] += 0.2
            scores['spring_boot'] += 0.2
        
        if '/graphql' in url_lower:
            scores['rails'] += 0.3  # Rails often has GraphQL endpoints
            scores['express'] += 0.2
        
        if any(pattern in url_lower for pattern in ['/admin/', '/wp-json/', '/wp/']):
            scores['wordpress'] += 0.4
            scores['php'] += 0.2
        
        if '.aspx' in url_lower or '/api/' in url_lower:
            scores['aspnet_core'] += 0.3
        
        if '/laravel' in url_lower or '/api/v' in url_lower:
            scores['laravel'] += 0.3
        
        return scores
    
    def _analyze_response_content(self, response_content: str) -> Dict[str, float]:
        """Analyze HTTP response content for framework patterns."""
        scores = {}
        
        for framework, patterns in self.framework_patterns.items():
            framework_score = 0
            matched_patterns = []
            
            for pattern in patterns:
                matches = pattern.findall(response_content)
                if matches:
                    framework_score += len(matches) * 0.1
                    matched_patterns.append(pattern.pattern)
            
            if framework_score > 0:
                scores[framework] = framework_score
                evidence[f'{framework}_patterns'] = matched_patterns
        
        return scores
    
    def get_framework_specific_strategies(self, framework: str) -> List[str]:
        """
        Get framework-specific probe strategies.
        
        Args:
            framework: Detected framework name
            
        Returns:
            List of recommended probe strategies
        """
        strategy_map = {
            'fastapi': ['error_probe', 'type_probe', 'null_probe'],
            'express': ['error_probe', 'boundary_probe', 'success_probe'],
            'django': ['error_probe', 'null_probe', 'boundary_probe'],
            'spring_boot': ['error_probe', 'type_probe', 'boundary_probe'],
            'rails': ['error_probe', 'success_probe', 'type_probe'],
            'aspnet_core': ['error_probe', 'boundary_probe', 'type_probe'],
            'flask': ['error_probe', 'null_probe'],
            'laravel': ['error_probe', 'boundary_probe', 'success_probe']
        }
        
        return strategy_map.get(framework, ['error_probe', 'type_probe'])
    
    async def make_detection_request(
        self, 
        context: DiscoveryContext
    ) -> Optional[str]:
        """
        Make a request to gather sample response for framework detection.
        
        Args:
            context: Discovery context
            
        Returns:
            Response content string or None if request fails
        """
        if not self.http_client:
            return None
        
        try:
            # Make a simple request to get sample response
            response = await self.http_client.get(
                context.request.url,
                headers=context.request.headers,
                timeout=min(5, context.request.timeout_seconds)
            )
            
            if response.status_code == 200:
                return response.text
            else:
                return response.text  # Even error responses can have framework signatures
                
        except Exception as e:
            print(f"[FrameworkDetector] Detection request failed: {str(e)}")
            return None
