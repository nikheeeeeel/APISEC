"""
Probe strategy abstractions for REST Parameter Discovery v2.

Defines strategy pattern for generating different types of payloads
without containing transport logic or HTTP client dependencies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union
from dataclasses import dataclass


class ProbeStrategy(ABC):
    """
    Abstract base class for probe payload generation strategies.
    
    Each strategy focuses on generating specific types of test payloads
to trigger different validation scenarios in target APIs.
    """
    
    @abstractmethod
    def generate_payloads(self, context: 'DiscoveryContext') -> List[Dict[str, Any]]:
        """
        Generate test payloads for this strategy.
        
        Args:
            context: Discovery context with request information
            
        Returns:
            List of payload dictionaries for testing
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Get human-readable name for this strategy.
        
        Returns:
            Strategy name string
        """
        pass
    
    @abstractmethod
    def get_target_parameter_types(self) -> List[str]:
        """
        Get list of parameter types this strategy targets.
        
        Returns:
            List of parameter type names this strategy can discover
        """
        pass
    
    def get_description(self) -> str:
        """
        Get description of what this strategy tests.
        
        Returns:
            Strategy description
        """
        pass


@dataclass
class PayloadConfig:
    """
    Configuration for payload generation.
    
    Controls payload generation behavior and boundaries.
    """
    min_value_length: int = 1
    max_value_length: int = 1000
    include_null_values: bool = True
    include_empty_values: bool = True
    include_undefined_values: bool = True
    test_special_characters: bool = True
    test_boundary_values: bool = True
    max_payloads_per_parameter: int = 10


class StringProbe(ProbeStrategy):
    """
    Strategy for testing string parameters.
    
    Generates various string values to test validation rules,
length constraints, and special character handling.
    """
    
    def generate_payloads(self, context: 'DiscoveryContext') -> List[Dict[str, Any]]:
        """Generate string test payloads."""
        payloads = []
        config = PayloadConfig()
        
        # Get existing parameters to test
        existing_params = list(context.discovered_parameters.keys())
        
        for param_name in existing_params:
            param_payloads = []
            
            # Valid strings
            param_payloads.extend(self._generate_valid_strings(param_name, config))
            
            # Null/empty values
            if config.include_null_values:
                param_payloads.extend(self._generate_null_empty_strings(param_name, config))
            
            # Undefined values
            if config.include_undefined_values:
                param_payloads.extend(self._generate_undefined_strings(param_name, config))
            
            # Special characters
            if config.test_special_characters:
                param_payloads.extend(self._generate_special_char_strings(param_name, config))
            
            # Boundary values
            if config.test_boundary_values:
                param_payloads.extend(self._generate_boundary_strings(param_name, config))
            
            # Add to main payload list
            for payload in param_payloads:
                payloads.append({param_name: payload})
        
        return payloads
    
    def _generate_valid_strings(self, param_name: str, config: PayloadConfig) -> List[Dict[str, Any]]:
        """Generate valid string test values."""
        return [
            {param_name: "test"},
            {param_name: "valid_string"},
            {param_name: "sample"},
            {param_name: "default"},
            {param_name: "example"},
            {param_name: "data"},
            {param_name: "value"}
        ]
    
    def _generate_null_empty_strings(self, param_name: str, config: PayloadConfig) -> List[Dict[str, Any]]:
        """Generate null and empty string test values."""
        return [
            {param_name: ""},
            {param_name: None},
            {param_name: "null"},
            {param_name: "undefined"}
        ]
    
    def _generate_undefined_strings(self, param_name: str, config: PayloadConfig) -> List[Dict[str, Any]]:
        """Generate undefined value test strings."""
        return [
            {param_name: "undefined"},
            {param_name: "UNDEFINED"},
            {param_name: "nil"},
            {param_name: "null"}
        ]
    
    def _generate_special_char_strings(self, param_name: str, config: PayloadConfig) -> List[Dict[str, Any]]:
        """Generate special character test strings."""
        special_chars = [
            "'", '"', '<', '>', '<', '&', '=', '%', '#', '@', '!', '$', '*',
            '(', ')', '[', ']', '{', '}', '|', '\\', '/', '?', '`', '~'
        ]
        
        payloads = []
        for char in special_chars:
            payloads.extend([
                {param_name: f"test{char}value"},
                {param_name: f"prefix{char}suffix"},
                {param_name: char},
                {param_name: f"string_with_{char}"}
            ])
        
        return payloads
    
    def _generate_boundary_strings(self, param_name: str, config: PayloadConfig) -> List[Dict[str, Any]]:
        """Generate boundary value test strings."""
        return [
            {param_name: "a" * config.min_value_length},
            {param_name: "a" * config.max_value_length},
            {param_name: "A" * 50},
            {param_name: "a" * 255},
            {param_name: "0"},
            {param_name: "-1"},
            {param_name: "999999999"},
            {param_name: "-999999999"},
            {param_name: "1.7976931348623157e+308"}
        ]
    
    def get_strategy_name(self) -> str:
        return "string_probe"
    
    def get_target_parameter_types(self) -> List[str]:
        return ["string", "text"]
    
    def get_description(self) -> str:
        return "Tests string parameters with various values, null handling, and boundary conditions"


class NumericProbe(ProbeStrategy):
    """
    Strategy for testing numeric parameters.
    
    Generates various numeric values to test validation rules,
range constraints, and edge cases.
    """
    
    def generate_payloads(self, context: 'DiscoveryContext') -> List[Dict[str, Any]]:
        """Generate numeric test payloads."""
        payloads = []
        config = PayloadConfig()
        
        existing_params = list(context.discovered_parameters.keys())
        
        for param_name in existing_params:
            param_payloads = []
            
            # Valid numbers
            param_payloads.extend(self._generate_valid_numbers(param_name, config))
            
            # Zero and null values
            if config.include_null_values:
                param_payloads.extend(self._generate_null_numbers(param_name, config))
            
            # Boundary values
            if config.test_boundary_values:
                param_payloads.extend(self._generate_boundary_numbers(param_name, config))
            
            # Special numeric values
            param_payloads.extend(self._generate_special_numbers(param_name, config))
            
            for payload in param_payloads:
                payloads.append({param_name: payload})
        
        return payloads
    
    def _generate_valid_numbers(self, param_name: str, config: PayloadConfig) -> List[Dict[str, Any]]:
        """Generate valid numeric test values."""
        return [
            {param_name: 0},
            {param_name: 1},
            {param_name: -1},
            {param_name: 42},
            {param_name: 100},
            {param_name: 999},
            {param_name: 1000},
            {param_name: 3.14},
            {param_name: 2.718}
        ]
    
    def _generate_null_numbers(self, param_name: str, config: PayloadConfig) -> List[Dict[str, Any]]:
        """Generate null numeric test values."""
        return [
            {param_name: 0},
            {param_name: None},
            {param_name: "null"}
        ]
    
    def _generate_boundary_numbers(self, param_name: str, config: PayloadConfig) -> List[Dict[str, Any]]:
        """Generate boundary numeric test values."""
        return [
            {param_name: -2147483648},  # 32-bit int min
            {param_name: 2147483647},   # 32-bit int max
            {param_name: -9223372036854775808},  # 64-bit int min
            {param_name: 9223372036854775807},   # 64-bit int max
            {param_name: 1.7976931348623157e+308}, # Float max
            {param_name: -1.7976931348623157e+308}  # Float min
        ]
    
    def _generate_special_numbers(self, param_name: str, config: PayloadConfig) -> List[Dict[str, Any]]:
        """Generate special numeric test values."""
        return [
            {param_name: -1},
            {param_name: 999999999},
            {param_name: 0.0001},
            {param_name: 1e-10},
            {param_name: 1e+10}
        ]
    
    def get_strategy_name(self) -> str:
        return "numeric_probe"
    
    def get_target_parameter_types(self) -> List[str]:
        return ["integer", "number", "float", "decimal"]
    
    def get_description(self) -> str:
        return "Tests numeric parameters with various values, boundary conditions, and edge cases"


class BooleanProbe(ProbeStrategy):
    """
    Strategy for testing boolean parameters.
    
    Generates boolean true/false values and edge cases.
    """
    
    def generate_payloads(self, context: 'DiscoveryContext') -> List[Dict[str, Any]]:
        """Generate boolean test payloads."""
        payloads = []
        existing_params = list(context.discovered_parameters.keys())
        
        for param_name in existing_params:
            param_payloads = [
                {param_name: True},
                {param_name: False},
                {param_name: "true"},
                {param_name: "false"},
                {param_name: "1"},
                {param_name: "0"},
                {param_name: "yes"},
                {param_name: "no"},
                {param_name: "on"},
                {param_name: "off"}
            ]
            
            for payload in param_payloads:
                payloads.append({param_name: payload})
        
        return payloads
    
    def get_strategy_name(self) -> str:
        return "boolean_probe"
    
    def get_target_parameter_types(self) -> List[str]:
        return ["boolean", "bool"]
    
    def get_description(self) -> str:
        return "Tests boolean parameters with true/false values and various representations"


class ArrayProbe(ProbeStrategy):
    """
    Strategy for testing array parameters.
    
    Generates array payloads with different sizes, types, and edge cases.
    """
    
    def generate_payloads(self, context: 'DiscoveryContext') -> List[Dict[str, Any]]:
        """Generate array test payloads."""
        payloads = []
        existing_params = list(context.discovered_parameters.keys())
        
        for param_name in existing_params:
            param_payloads = []
            
            # Empty arrays
            param_payloads.extend(self._generate_empty_arrays(param_name))
            
            # Single element arrays
            param_payloads.extend(self._generate_single_arrays(param_name))
            
            # Multi-element arrays
            param_payloads.extend(self._generate_multi_arrays(param_name))
            
            # Nested arrays
            param_payloads.extend(self._generate_nested_arrays(param_name))
            
            # Type mixing arrays
            param_payloads.extend(self._generate_type_mixed_arrays(param_name))
            
            for payload in param_payloads:
                payloads.append({param_name: payload})
        
        return payloads
    
    def _generate_empty_arrays(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate empty array test payloads."""
        return [
            {param_name: []},
            {param_name: [""]},
            {param_name: None},
            {param_name: "[]"},
            {param_name: "null"}
        ]
    
    def _generate_single_arrays(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate single element array test payloads."""
        return [
            {param_name: ["item"]},
            {param_name: [1]},
            {param_name: [0]},
            {param_name: [True]},
            {param_name: [False]},
            {param_name: ["test"]},
            {param_name: ["value"]}
        ]
    
    def _generate_multi_arrays(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate multi-element array test payloads."""
        return [
            {param_name: ["item1", "item2", "item3"]},
            {param_name: [1, 2, 3]},
            {param_name: [True, False, None]},
            {param_name: ["value1", "value2", "value3"]},
            {param_name: range(1, 6)}  # Will be converted to list
        ]
    
    def _generate_nested_arrays(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate nested array test payloads."""
        return [
            {param_name: [{"nested": "value"}]},
            {param_name: [{"item": {"property": "value"}}]},
            {param_name: [{"data": [{"id": 1}, {"id": 2}]}]}
        ]
    
    def _generate_type_mixed_arrays(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate type-mixed array test payloads."""
        return [
            {param_name: [1, "string", 2.5, True, None]},
            {param_name: [{"id": 1}, {"name": "test"}, {"active": False}]}
        ]
    
    def get_strategy_name(self) -> str:
        return "array_probe"
    
    def get_target_parameter_types(self) -> List[str]:
        return ["array", "list"]
    
    def get_description(self) -> str:
        return "Tests array parameters with different sizes, types, and nested structures"


class ObjectProbe(ProbeStrategy):
    """
    Strategy for testing object parameters.
    
    Generates object payloads with different structures, required fields,
and nested objects.
    """
    
    def generate_payloads(self, context: 'DiscoveryContext') -> List[Dict[str, Any]]:
        """Generate object test payloads."""
        payloads = []
        existing_params = list(context.discovered_parameters.keys())
        
        for param_name in existing_params:
            param_payloads = []
            
            # Empty objects
            param_payloads.extend(self._generate_empty_objects(param_name))
            
            # Simple objects
            param_payloads.extend(self._generate_simple_objects(param_name))
            
            # Nested objects
            param_payloads.extend(self._generate_nested_objects(param_name))
            
            # Required field testing
            param_payloads.extend(self._generate_required_field_objects(param_name))
            
            for payload in param_payloads:
                payloads.append({param_name: payload})
        
        return payloads
    
    def _generate_empty_objects(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate empty object test payloads."""
        return [
            {param_name: {}},
            {param_name: {"": ""}},
            {param_name: None},
            {param_name: "null"},
            {param_name: "{}"}
        ]
    
    def _generate_simple_objects(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate simple object test payloads."""
        return [
            {param_name: {"key": "value"}},
            {param_name: {"name": "test", "type": "string"}},
            {param_name: {"id": 1, "active": True}},
            {param_name: {"data": {"items": []}}}
        ]
    
    def _generate_nested_objects(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate nested object test payloads."""
        return [
            {param_name: {"user": {"profile": {"name": "test"}}}},
            {param_name: {"data": {"items": [{"id": 1}, {"id": 2}]}}},
            {param_name: {"config": {"settings": {"theme": "dark", "notifications": True}}}}
        ]
    
    def _generate_required_field_objects(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate objects with missing required fields."""
        return [
            {param_name: {}},  # Missing all fields
            {param_name: {"id": 1}},  # Missing name field
            {param_name: {"name": "test"}},  # Missing type field
            {param_name: {"type": "string", "required": True}}  # Missing required field
        ]
    
    def get_strategy_name(self) -> str:
        return "object_probe"
    
    def get_target_parameter_types(self) -> List[str]:
        return ["object"]
    
    def get_description(self) -> str:
        return "Tests object parameters with different structures, required fields, and nested objects"


class BoundaryProbe(ProbeStrategy):
    """
    Strategy for testing boundary conditions and edge cases.
    
    Generates payloads that test system limits, validation boundaries,
and extreme edge cases.
    """
    
    def generate_payloads(self, context: 'DiscoveryContext') -> List[Dict[str, Any]]:
        """Generate boundary test payloads."""
        payloads = []
        existing_params = list(context.discovered_parameters.keys())
        
        for param_name in existing_params:
            param_payloads = []
            
            # Length boundaries
            param_payloads.extend(self._generate_length_boundaries(param_name))
            
            # Value boundaries
            param_payloads.extend(self._generate_value_boundaries(param_name))
            
            # Type boundaries
            param_payloads.extend(self._generate_type_boundaries(param_name))
            
            # Encoding boundaries
            param_payloads.extend(self._generate_encoding_boundaries(param_name))
            
            # System limits
            param_payloads.extend(self._generate_system_limits(param_name))
            
            for payload in param_payloads:
                payloads.append({param_name: payload})
        
        return payloads
    
    def _generate_length_boundaries(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate length boundary test payloads."""
        return [
            {param_name: "x" * 1000},  # Max length
            {param_name: ""},  # Empty string
            {param_name: " " * 100},  # Whitespace only
            {param_name: "\0" * 50},  # Null bytes
            {param_name: "a" * 256 + "b"}  # Buffer overflow test
        ]
    
    def _generate_value_boundaries(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate value boundary test payloads."""
        return [
            {param_name: -999999999},  # Min int32
            {param_name: 999999999},   # Max int32
            {param_name: -1.7976931348623157e+308},  # Min float64
            {param_name: 1.7976931348623157e+308},   # Max float64
            {param_name: "9999-12-31"},  # Invalid date
            {param_name: "not-a-valid-email"},  # Invalid format
            {param_name: "javascript:void(0)"},  # XSS attempt
        ]
    
    def _generate_type_boundaries(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate type boundary test payloads."""
        return [
            {param_name: 123},  # Number when string expected
            {param_name: "true"},  # String when boolean expected
            {param_name: ["not", "an", "array"]},  # Array when string expected
            {param_name: {"nested": "object"}},  # Object when string expected
            {param_name: "2023-13-32T00:00:00Z"},  # Date when string expected
        ]
    
    def _generate_encoding_boundaries(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate encoding boundary test payloads."""
        return [
            {param_name: "café"},  # UTF-8 with accent
            {param_name: "测试"},  # Chinese characters
            {param_name: "🚀"},  # Emoji
            {param_name: "%E2%80%A9"},  # Invalid UTF-8 sequence
            {param_name: "&#x3C;script&#x3E;alert&#x27;XSS&#x27;"},  # HTML entities
        ]
    
    def _generate_system_limits(self, param_name: str) -> List[Dict[str, Any]]:
        """Generate system limit test payloads."""
        return [
            {param_name: "admin"},  # Privileged role
            {param_name: "root"},  # Superuser
            {param_name: "../../../etc/passwd"},  # Path traversal
            {param_name: "' OR '1'='1"},  # SQL injection
            {param_name: "{{7*7}}"},  # Template injection
            {param_name: "${jndi:ldap://}"},  # JNDI injection
        ]
    
    def get_strategy_name(self) -> str:
        return "boundary_probe"
    
    def get_target_parameter_types(self) -> List[str]:
        return ["string", "integer", "float", "boolean", "array", "object"]
    
    def get_description(self) -> str:
        return "Tests boundary conditions, system limits, encoding issues, and extreme edge cases"


class NullProbe(ProbeStrategy):
    """
    Strategy for testing null and undefined value handling.
    
    Generates payloads specifically designed to test how APIs handle
missing, null, and undefined parameter values.
    """
    
    def generate_payloads(self, context: 'DiscoveryContext') -> List[Dict[str, Any]]:
        """Generate null test payloads."""
        payloads = []
        existing_params = list(context.discovered_parameters.keys())
        
        for param_name in existing_params:
            param_payloads = [
                {param_name: None},
                {param_name: "null"},
                {param_name: "NULL"},
                {param_name: "undefined"},
                {param_name: "nil"},
                {param_name: ""},  # Empty string
                {param_name: []}   # Empty array
            ]
            
            for payload in param_payloads:
                payloads.append({param_name: payload})
        
        return payloads
    
    def get_strategy_name(self) -> str:
        return "null_probe"
    
    def get_target_parameter_types(self) -> List[str]:
        return ["string", "integer", "float", "boolean", "array", "object"]
    
    def get_description(self) -> str:
        return "Tests null and undefined value handling, missing parameter detection, and API error responses"
