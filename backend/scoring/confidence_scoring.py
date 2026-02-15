"""
Weighted confidence scoring for REST Parameter Discovery v2.

Implements configurable weighted scoring system with normalization
and location-specific confidence calculation.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ScoringWeights:
    """
    Configurable weights for confidence calculation components.
    
    Allows fine-tuning of scoring algorithm for different
API types and discovery scenarios.
    """
    status_changed: float = 3.0      # Weight for status code changes
    hash_changed: float = 3.0        # Weight for body hash changes
    length_delta: float = 2.0        # Weight for significant length changes
    reproducibility: float = 2.0       # Weight for result reproducibility
    framework_signal: float = 1.0      # Weight for framework detection signals
    source_diversity: float = 1.0      # Weight for evidence source diversity
    location_match: float = 2.0           # Weight for location testing matches
    error_pattern_match: float = 2.5    # Weight for error pattern matches
    response_similarity: float = 1.5      # Weight for response fingerprint similarity


@dataclass
class ScoringConfig:
    """
    Configuration for confidence scoring behavior.
    
    Controls thresholds, normalization, and scoring parameters.
    """
    min_confidence_threshold: float = 0.3
    max_confidence: float = 1.0
    length_delta_significance: float = 0.1  # 10% change considered significant
    reproducibility_bonus: float = 0.2      # Bonus for reproducible results
    diversity_bonus: float = 0.1           # Bonus for multiple evidence sources
    location_specific_bonus: float = 0.3     # Bonus for confirmed location


@dataclass
class ParameterConfidence:
    """
    Enhanced confidence result with location information.
    
    Combines overall confidence with location-specific analysis
and detailed evidence tracking.
    """
    name: str
    confidence: float
    evidence: Dict[str, Any]
    sources: List[str]
    location: Optional[str] = None
    location_confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class WeightedConfidenceScorer:
    """
    Weighted confidence scorer with configurable parameters.
    
    Calculates confidence based on multiple evidence sources
with proper normalization and location-specific scoring.
    """
    
    def __init__(self, weights: ScoringWeights = None, config: ScoringConfig = None):
        """
        Initialize weighted confidence scorer.
        
        Args:
            weights: Optional custom weights for scoring
            config: Optional scoring configuration
        """
        self.weights = weights or ScoringWeights()
        self.config = config or ScoringConfig()
    
    def calculate_parameter_confidence(
        self,
        parameter_name: str,
        evidence_sources: List[str],
        framework_signals: Optional[Dict[str, Any]] = None,
        location_tests: Optional[List[Any]] = None
    ) -> ParameterConfidence:
        """
        Calculate confidence score for a parameter with weighted scoring.
        
        Args:
            parameter_name: Name of the parameter
            evidence_sources: List of evidence source identifiers
            framework_signals: Optional framework detection signals
            location_tests: Optional location test results
            
        Returns:
            ParameterConfidence with calculated confidence and location
        """
        # Initialize scoring components
        score_components = {
            'status_changed': 0.0,
            'hash_changed': 0.0,
            'length_delta': 0.0,
            'reproducibility': 0.0,
            'framework_signal': 0.0,
            'source_diversity': 0.0,
            'location_match': 0.0,
            'error_pattern_match': 0.0,
            'response_similarity': 0.0
        }
        
        evidence = {}
        sources = []
        
        # Process evidence sources
        for source in evidence_sources:
            if source.startswith('probe_'):
                # Process probe evidence
                probe_score = self._calculate_probe_confidence(
                    parameter_name, evidence_sources, framework_signals
                )
                if probe_score > 0:
                    score_components['status_changed'] += probe_score * self.weights.status_changed
                    score_components['hash_changed'] += probe_score * self.weights.hash_changed
                    score_components['length_delta'] += probe_score * self.weights.length_delta
                    score_components['reproducibility'] += probe_score * self.weights.reproducibility
                    score_components['framework_signal'] += probe_score * self.weights.framework_signal
                    score_components['source_diversity'] += self.weights.source_diversity
                
                evidence[f'probe_{source}'] = probe_score
                sources.append(source)

            elif source.startswith('detection_'):
                # Process detection evidence
                detection_score = self._calculate_detection_confidence(
                    parameter_name, evidence_sources
                )
                if detection_score > 0:
                    score_components['framework_signal'] += detection_score * self.weights.framework_signal
                    score_components['source_diversity'] += self.weights.source_diversity

                evidence[f'detection_{source}'] = detection_score
                sources.append(source)

            elif source.startswith('location_'):
                # Process location testing evidence
                if location_tests:
                    location_score = self._calculate_location_confidence(location_tests)
                    if location_score > 0:
                        score_components['location_match'] += location_score * self.weights.location_match
                        score_components['reproducibility'] += location_score * self.weights.reproducibility

                    evidence[f'location_{source}'] = location_score
                    sources.append(source)

            else:
                # Fallback for differential_engine, framework_signals, etc.
                if source in ('differential_engine', 'framework_signals'):
                    score_components['source_diversity'] += self.weights.source_diversity
                    evidence[source] = 0.5
                    sources.append(source)

        # Calculate base confidence from components
        base_confidence = sum(score_components.values())
        
        # Apply normalization
        normalized_confidence = self._normalize_confidence(base_confidence)
        
        # Apply bonuses
        final_confidence = self._apply_bonuses(
            normalized_confidence, score_components, evidence_sources
        )
        
        # Determine location
        best_location = self._determine_best_location(location_tests)
        location_confidence = self._calculate_location_confidence(location_tests)
        
        return ParameterConfidence(
            name=parameter_name,
            confidence=final_confidence,
            location=best_location,
            location_confidence=location_confidence,
            evidence=evidence,
            sources=sources,
            metadata={
                'scoring_components': score_components,
                'base_confidence': base_confidence,
                'normalized_confidence': normalized_confidence,
                'weights_used': self.weights.__dict__,
                'config_used': self.config.__dict__
            }
        )
    
    def _calculate_probe_confidence(
        self,
        parameter_name: str,
        evidence_sources: List[str],
        framework_signals: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate confidence from probe evidence sources.
        
        Args:
            parameter_name: Parameter name
            evidence_sources: List of probe evidence source identifiers
            framework_signals: Optional framework detection signals
            
        Returns:
            Confidence score from probe evidence
        """
        score = 0.0
        
        # Count different probe types
        probe_types = set()
        for source in evidence_sources:
            if source.startswith('probe_'):
                probe_type = source.split('_', 1)[1]
                probe_types.add(probe_type)
        
        # Bonus for multiple probe types
        type_diversity_bonus = min(len(probe_types) / 5.0, 1.0) * self.config.diversity_bonus
        
        # Base score from probe evidence
        evidence_count = len([s for s in evidence_sources if s.startswith('probe_')])
        if evidence_count > 0:
            score = 0.3  # Base score for having probe evidence
            score += type_diversity_bonus
        
        return score
    
    def _calculate_detection_confidence(
        self,
        parameter_name: str,
        evidence_sources: List[str]
    ) -> float:
        """
        Calculate confidence from detection evidence sources.
        
        Args:
            parameter_name: Parameter name
            evidence_sources: List of detection evidence source identifiers
            
        Returns:
            Confidence score from detection evidence
        """
        score = 0.0
        
        # Check for framework detection
        detection_count = len([s for s in evidence_sources if s.startswith('detection_')])
        if detection_count > 0:
            score = 0.4  # Detection evidence is strong
            score += self.config.diversity_bonus
        
        return score
    
    def _calculate_location_confidence(self, location_tests: Optional[List[Any]]) -> float:
        """
        Calculate confidence from location testing evidence.
        
        Args:
            location_tests: List of location test results
            
        Returns:
            Location confidence score
        """
        if not location_tests:
            return 0.0
        
        # Score successful location tests
        successful_tests = [test for test in location_tests if hasattr(test, 'success') and test.success]
        if successful_tests:
            return len(successful_tests) / len(location_tests)
        
        return 0.0
    
    def _determine_best_location(self, location_tests: Optional[List[Any]]) -> str:
        """
        Determine best location from location test results.
        
        Args:
            location_tests: List of location test results
            
        Returns:
            Best location string
        """
        if not location_tests:
            return "body"
        
        # Count successful tests by location
        location_scores = {
            "body": 0,
            "query": 0,
            "form": 0,
            "header": 0
        }
        
        for test in location_tests:
            if hasattr(test, 'success') and test.success:
                location_scores[test.location] += 1
        
        # Return location with highest score
        return max(location_scores, key=location_scores.get)
    
    def _normalize_confidence(self, confidence: float) -> float:
        """
        Normalize confidence to 0-1 range.
        
        Args:
            confidence: Raw confidence score
            
        Returns:
            Normalized confidence score
        """
        # Apply min/max constraints
        normalized = max(min(confidence, self.config.max_confidence), self.config.min_confidence_threshold)
        
        # Apply sigmoid-like normalization for better distribution
        if normalized < 0.5:
            return normalized * 1.2  # Amplify low scores
        elif normalized > 0.8:
            return normalized * 0.9  # Compress high scores
        else:
            return normalized
    
    def _apply_bonuses(
        self,
        confidence: float,
        score_components: Dict[str, float],
        evidence_sources: List[str]
    ) -> float:
        """
        Apply bonuses and adjustments to confidence score.
        
        Args:
            confidence: Base confidence score
            score_components: Scoring component scores
            evidence_sources: List of evidence sources
            
        Returns:
            Final confidence score with bonuses applied
        """
        final_confidence = confidence
        
        # Reproducibility bonus
        if score_components.get('reproducibility', 0) > 0:
            final_confidence += self.config.reproducibility_bonus
        
        # Source diversity bonus
        unique_sources = len(set(evidence_sources))
        if unique_sources >= 3:
            final_confidence += self.config.diversity_bonus * 0.5
        elif unique_sources >= 2:
            final_confidence += self.config.diversity_bonus * 0.25
        
        # Length delta significance bonus
        if score_components.get('length_delta', 0) > self.config.length_delta_significance:
            final_confidence += self.config.diversity_bonus * 0.3
        
        return min(final_confidence, self.config.max_confidence)


# Factory function for creating weighted scorer
def create_weighted_scorer(
    weights: Optional[ScoringWeights] = None,
    config: Optional[ScoringConfig] = None
) -> WeightedConfidenceScorer:
    """
    Create a weighted confidence scorer with configuration.
    
    Args:
        weights: Optional custom scoring weights
        config: Optional scoring configuration
        
    Returns:
        Configured WeightedConfidenceScorer instance
    """
    return WeightedConfidenceScorer(weights=weights, config=config)


# Backward compatibility functions
def calculate_simple_confidence(
    parameter_name: str,
    evidence_count: int,
    base_score: float = 0.3
) -> ParameterConfidence:
    """
    Simple confidence calculation for backward compatibility.
    
    Args:
        parameter_name: Parameter name
        evidence_count: Number of evidence items
        base_score: Base confidence score
        
    Returns:
        ParameterConfidence with simple calculation
    """
    # Simple evidence count bonus
    if evidence_count >= 3:
        base_score += 0.2
    elif evidence_count >= 2:
        base_score += 0.1
    elif evidence_count >= 1:
        base_score += 0.05
    
    normalized_score = min(max(base_score, 1.0), 0.0)
    
    return ParameterConfidence(
        name=parameter_name,
        confidence=normalized_score,
        evidence={'evidence_count': evidence_count},
        sources=['simple_scoring']
    )
