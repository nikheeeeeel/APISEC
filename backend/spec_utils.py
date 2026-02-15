import json
import yaml
from typing import List, Dict, Any
from pathlib import Path
from .models import CanonicalParameter

def load_spec(file_path: str) -> dict:
    """
    Load OpenAPI spec from JSON or YAML file.
    
    Args:
        file_path: Path to the OpenAPI spec file
        
    Returns:
        dict: Parsed OpenAPI specification
        
    Raises:
        ValueError: If file format unsupported or file invalid
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Spec file not found: {file_path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() in ['.json']:
                return json.load(f)
            elif path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}. Supported formats: .json, .yaml, .yml")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format: {e}")
    except Exception as e:
        raise ValueError(f"Error reading spec file: {e}")


def diff_spec(spec_dict: dict, params: List[CanonicalParameter]) -> List[CanonicalParameter]:
    """
    Compare canonical parameters (from Arjun) to OpenAPI spec.
    Returns a list of parameters missing from the spec.
    
    Args:
        spec_dict: Parsed OpenAPI specification
        params: List of discovered parameters from Arjun
        
    Returns:
        List[CanonicalParameter]: Parameters missing from the spec
    """
    # Extract parameters from OpenAPI spec
    spec_params = set()
    
    # Get parameters from all paths and methods
    paths = spec_dict.get('paths', {})
    for path_name, path_item in paths.items():
        for method_name, operation in path_item.items():
            if isinstance(operation, dict) and 'parameters' in operation:
                for param in operation['parameters']:
                    param_name = param.get('name')
                    param_in = param.get('in', 'query')
                    if param_name:
                        spec_params.add((param_name, param_in))
    
    # Get parameters from global components
    components = spec_dict.get('components', {})
    parameters = components.get('parameters', {})
    for param_name, param_obj in parameters.items():
        param_in = param_obj.get('in', 'query')
        if param_name:
            spec_params.add((param_name, param_in))
    
    # Find missing parameters
    missing_params = []
    for param in params:
        param_key = (param.name, param.in_)
        if param_key not in spec_params:
            missing_params.append(param)
    
    return missing_params


def merge_spec(spec_dict: dict, params: List[CanonicalParameter]) -> dict:
    """
    Adds missing parameters to correct path/method in spec.
    Avoids overwriting existing parameters.
    
    Args:
        spec_dict: Parsed OpenAPI specification
        params: List of parameters to add (from Arjun discoveries)
        
    Returns:
        dict: Updated OpenAPI specification
    """
    # Make a deep copy to avoid modifying the original
    import copy
    updated_spec = copy.deepcopy(spec_dict)
    
    # Ensure paths and components exist
    if 'paths' not in updated_spec:
        updated_spec['paths'] = {}
    if 'components' not in updated_spec:
        updated_spec['components'] = {}
    if 'parameters' not in updated_spec['components']:
        updated_spec['components']['parameters'] = {}
    
    # Track existing parameters to avoid duplicates
    existing_params = set()
    
    # Collect existing parameters from all paths and methods
    for path_name, path_item in updated_spec.get('paths', {}).items():
        for method_name, operation in path_item.items():
            if isinstance(operation, dict) and 'parameters' in operation:
                for param in operation['parameters']:
                    param_name = param.get('name')
                    param_in = param.get('in', 'query')
                    if param_name:
                        existing_params.add((param_name, param_in))
    
    # Collect existing parameters from components
    for param_name, param_obj in updated_spec['components']['parameters'].items():
        param_in = param_obj.get('in', 'query')
        if param_name:
            existing_params.add((param_name, param_in))
    
    # Add missing parameters
    for param in params:
        param_key = (param.name, param.in_)
        
        if param_key not in existing_params:
            # Create parameter schema
            param_schema = {
                'name': param.name,
                'in': param.in_,
                'required': param.required,
                'schema': {
                    'type': param.type_
                }
            }
            
            if param.description:
                param_schema['description'] = param.description
            
            if param.example:
                param_schema['example'] = param.example
            
            # Add to components/parameters
            param_ref_name = f"{param.name}_{param.in_}"
            updated_spec['components']['parameters'][param_ref_name] = param_schema
            
            # For now, add to a generic /discover endpoint (can be enhanced later)
            if '/discover' not in updated_spec['paths']:
                updated_spec['paths']['/discover'] = {
                    'get': {
                        'summary': 'Discovered parameters endpoint',
                        'description': 'Endpoint with parameters discovered by Arjun',
                        'parameters': [],
                        'responses': {
                            '200': {
                                'description': 'Success'
                            }
                        }
                    }
                }
            
            # Add parameter reference to the endpoint
            param_ref = {
                '$ref': f'#/components/parameters/{param_ref_name}'
            }
            updated_spec['paths']['/discover']['get']['parameters'].append(param_ref)
    
    return updated_spec
