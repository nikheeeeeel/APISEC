import requests
import json
import io
import re
from typing import Dict, Any, List, Optional, Tuple, Callable, Set
from datetime import datetime
from copy import deepcopy

# Optional yaml import for schema conversion
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

SCHEMA_PATHS = [
    '/schema',
    '/openapi',
    '/swagger',
    '/docs',
    '/api/schema/view/',
    '/schema/view/',
    '/v2/swagger.json',
    '/api/schema',
    '/api/openapi',
    '/api/swagger',
    '/openapi.json',
    '/openapi.yaml',
    '/swagger.json',
    '/swagger.yaml',
    '/api-docs',
    '/v2/api-docs',
    '/v3/api-docs',
    '/api/',
    '/api/v1/',
    '/api/v2/',
    '/api/schema/',
    '/api/openapi.json',
    '/api/swagger.json',
    '/redoc',
    '/swagger-ui/',
    '/swagger-ui',
    '/docs/json',
    '/api-docs.json',
    '/api-doc',
    '/documentation',
    '/doc',
    '/json',
    '/api.json',
    '/_next/static/openapi.json',
    '/swagger/v1/',
    '/v2/api-docs',
    '/v3/api-docs',
    '/openapi',
    '/api-docs',
    '/documentation',
    '/docs-json',
    '/swagger/v1',
    '/_swagger',
    '/swagger',
]

PRIORITY_PATHS = [
    '/api/schema/',
    '/api/schema',
    '/openapi.json',
    '/openapi.yaml',
    '/swagger.json',
    '/swagger.yaml',
    '/v3/api-docs',
    '/docs',
    '/openapi',
]

def normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize OpenAPI schema for stable comparison.
    
    This function:
    - Resolves all $ref references
    - Sorts dictionary keys deterministically  
    - Removes non-contract fields (description, summary, examples, externalDocs)
    - Ensures consistent data types
    
    Args:
        schema: Raw OpenAPI schema dictionary
        
    Returns:
        Normalized schema ready for comparison
    """
    if not isinstance(schema, dict):
        return schema
    
    # Create a deep copy to avoid modifying the original
    normalized = deepcopy(schema)
    
    # Resolve $ref references first
    normalized = _resolve_refs(normalized, normalized)
    
    # Remove non-contract fields
    normalized = _remove_non_contract_fields(normalized)
    
    # Sort keys deterministically
    normalized = _sort_keys_deterministically(normalized)
    
    return normalized


def _resolve_refs(schema: Dict[str, Any], root_schema: Dict[str, Any], visited: Optional[Set[str]] = None) -> Dict[str, Any]:
    """
    Recursively resolve all $ref references in the schema.
    
    Args:
        schema: Current schema object being processed
        root_schema: Root schema for reference resolution
        visited: Set of visited references to prevent infinite recursion
        
    Returns:
        Schema with all references resolved
    """
    if visited is None:
        visited = set()
    
    if isinstance(schema, dict):
        # Handle $ref
        if '$ref' in schema:
            ref_path = schema['$ref']
            if ref_path in visited:
                return {}  # Prevent infinite recursion
            # Copy visited set per branch to support diamond-shaped refs
            branch_visited = visited | {ref_path}
            
            # Resolve the reference
            resolved = _resolve_reference_path(ref_path, root_schema)
            if resolved:
                return _resolve_refs(resolved, root_schema, branch_visited)
            else:
                return schema
        
        # Process all dictionary values
        resolved_dict = {}
        for key, value in schema.items():
            resolved_dict[key] = _resolve_refs(value, root_schema, visited)
        return resolved_dict
    
    elif isinstance(schema, list):
        # Process all list items
        return [_resolve_refs(item, root_schema, visited) for item in schema]
    
    else:
        # Return primitive values as-is
        return schema


def _resolve_reference_path(ref_path: str, root_schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Resolve a JSON Pointer reference path within the schema.
    
    Args:
        ref_path: JSON Pointer path (e.g., "#/components/schemas/User")
        root_schema: Root schema to search within
        
    Returns:
        Resolved schema object or None if not found
    """
    if not ref_path.startswith('#/'):
        return None  # Only support internal references for now
    
    # Remove the '#/' prefix and split by '/'
    path_parts = ref_path[2:].split('/')
    
    current = root_schema
    for part in path_parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    
    return current if isinstance(current, dict) else None


def _remove_non_contract_fields(obj: Any, parent_key: str = '') -> Any:
    """
    Remove non-contract fields that don't affect API behavior.
    
    Removes: summary, examples, externalDocs, and other documentation-only fields.
    Preserves: description in info object, but removes it from other contexts.
    
    Args:
        obj: Schema object to clean
        parent_key: Key of the parent object (for context)
        
    Returns:
        Cleaned schema object
    """
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            # Skip non-contract fields (but preserve description in info)
            if key in ['summary', 'examples', 'externalDocs', 'tags', 'deprecated', 'termsOfService', 'contact', 'license']:
                continue
            if key == 'description' and parent_key != 'info':
                # Remove description from non-info objects
                continue
            
            # Recursively clean nested objects
            cleaned[key] = _remove_non_contract_fields(value, key)
        return cleaned
    
    elif isinstance(obj, list):
        return [_remove_non_contract_fields(item, parent_key) for item in obj]
    
    else:
        return obj


def _sort_keys_deterministically(obj: Any) -> Any:
    """
    Sort dictionary keys deterministically for stable comparison.
    
    Args:
        obj: Schema object to sort
        
    Returns:
        Schema object with sorted keys
    """
    if isinstance(obj, dict):
        # Sort keys but keep 'openapi' first if present
        keys = sorted(obj.keys())
        if 'openapi' in keys:
            keys.remove('openapi')
            keys = ['openapi'] + keys
        
        return {k: _sort_keys_deterministically(obj[k]) for k in keys}
    
    elif isinstance(obj, list):
        return [_sort_keys_deterministically(item) for item in obj]
    
    else:
        return obj


def convert_yaml_to_json(schema_data: Any) -> Dict[str, Any]:
    """
    Convert YAML schema data to JSON format.
    
    Args:
        schema_data: Schema data (could be dict or YAML string)
        
    Returns:
        Schema data as JSON-compatible dictionary
    """
    if isinstance(schema_data, str):
        if YAML_AVAILABLE:
            try:
                # Try to parse as YAML
                parsed = yaml.safe_load(schema_data)
                if isinstance(parsed, dict):
                    return parsed
            except yaml.YAMLError:
                pass
        
        try:
            # Try to parse as JSON string
            return json.loads(schema_data)
        except json.JSONDecodeError:
            pass
    
    elif isinstance(schema_data, dict):
        return schema_data
    
    # Return as-is if no conversion needed/possible
    return schema_data


def generate_pdf_from_json(schema_json: Dict[str, Any]) -> str:
    """Generate a simple PDF representation of the schema as base64."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        import base64
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=12)
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14, spaceAfter=10, textColor=colors.HexColor('#1a365d'))
        normal_style = styles['Normal']
        
        info = schema_json.get('info', {})
        story.append(Paragraph(f"API Schema - {info.get('title', 'Untitled')}", title_style))
        story.append(Paragraph(f"Version: {info.get('version', 'N/A')}", normal_style))
        if info.get('description'):
            story.append(Paragraph(info['description'], normal_style))
        story.append(Spacer(1, 0.3*inch))
        
        paths = schema_json.get('paths', {})
        if paths:
            story.append(Paragraph("Endpoints", heading_style))
            
            for path, methods in sorted(paths.items()):
                story.append(Paragraph(f"<b>{path}</b>", normal_style))
                
                if isinstance(methods, dict):
                    for method, details in methods.items():
                        method_upper = method.upper()
                        story.append(Paragraph(f"  • {method_upper}", normal_style))
                        
                        if isinstance(details, dict):
                            summary = details.get('summary') or details.get('operationId', '')
                            if summary:
                                story.append(Paragraph(f"    {summary}", normal_style))
                                
                            params = details.get('parameters', [])
                            if params:
                                story.append(Paragraph(f"    Parameters: {len(params)}", normal_style))
                                
                            responses = details.get('responses', {})
                            if responses:
                                story.append(Paragraph(f"    Responses: {', '.join(responses.keys())}", normal_style))
                story.append(Spacer(1, 0.1*inch))
        
        components = schema_json.get('components', {})
        if components:
            story.append(Paragraph("Components", heading_style))
            
            schemas = components.get('schemas', {})
            if schemas:
                story.append(Paragraph(f"Schemas: {len(schemas)} defined", normal_style))
        
        doc.build(story)
        
        buffer.seek(0)
        pdf_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return pdf_base64
        
    except ImportError:
        return None
    except Exception as e:
        print(f"PDF generation error: {e}")
        return None


def crawl_for_schema(
    base_url: str, 
    timeout: float = 5.0,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Crawl the API base URL for schema endpoints.
    
    Args:
        base_url: The base URL of the API
        timeout: Request timeout in seconds (default 5)
        progress_callback: Optional callback function(status, path, progress, total)
            Called during crawling to report progress
    """
    
    if not base_url.startswith('http://') and not base_url.startswith('https://'):
        base_url = 'https://' + base_url
    
    session = requests.Session()
    session.headers.update({
        'Accept': 'application/json, application/yaml, text/html',
        'User-Agent': 'APISec-Schema-Monitor/1.0'
    })
    
    priority_paths = [p for p in PRIORITY_PATHS if p in SCHEMA_PATHS]
    remaining_paths = [p for p in SCHEMA_PATHS if p not in PRIORITY_PATHS]
    all_paths = priority_paths + remaining_paths
    
    total = len(all_paths)
    
    for idx, path in enumerate(all_paths):
        if progress_callback:
            progress_callback("checking", path, idx + 1, total)
        
        url = base_url.rstrip('/') + path
        try:
            response = session.get(url, timeout=timeout)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                
                if 'json' in content_type:
                    try:
                        schema = response.json()
                        if is_valid_openapi_schema(schema):
                            if progress_callback:
                                progress_callback("found", url, idx + 1, total)
                            return schema, url
                    except:
                        pass
                elif 'yaml' in content_type:
                    try:
                        import yaml
                        schema = yaml.safe_load(response.text)
                        if is_valid_openapi_schema(schema):
                            if progress_callback:
                                progress_callback("found", url, idx + 1, total)
                            return schema, url
                    except:
                        pass
                else:
                    try:
                        schema = response.json()
                        if is_valid_openapi_schema(schema):
                            if progress_callback:
                                progress_callback("found", url, idx + 1, total)
                            return schema, url
                    except:
                        pass
                        
        except requests.exceptions.RequestException:
            continue
    
    schema, found_url = discover_schema_from_html(base_url, session, timeout, progress_callback, total)
    if schema:
        return schema, found_url
    
    return None, None


def discover_schema_from_html(
    base_url: str, 
    session: requests.Session,
    timeout: float = 5.0,
    progress_callback: Optional[Callable[[str, str, int, int], None]] = None,
    current_progress: int = 0
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Discover schema from HTML pages by parsing link tags and script tags."""
    
    if progress_callback:
        progress_callback("checking", "/ (HTML discovery)", current_progress + 1, current_progress + 1)
    
    try:
        response = session.get(base_url, timeout=timeout)
        if response.status_code != 200:
            return None, None
        
        html_content = response.text
        
        link_patterns = [
            r'<link[^>]+rel=["\']api-doc["\'][^>]+href=["\']([^"\']+)["\']',
            r'<link[^>]+href=["\']([^"\']+api[^"\']*)["\'][^>]+rel=["\'][^"\']*["\']',
            r'<link[^>]+rel=["\'][^"\']*["\'][^>]+href=["\']([^"\']+swagger[^"\']*)["\']',
        ]
        
        for pattern in link_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match.startswith('http'):
                    url = match
                else:
                    url = base_url.rstrip('/') + match
                
                try:
                    schema_response = session.get(url, timeout=timeout)
                    if schema_response.status_code == 200:
                        try:
                            schema = schema_response.json()
                            if is_valid_openapi_schema(schema):
                                return schema, url
                        except:
                            pass
                except:
                    continue
        
        script_patterns = [
            r'<script[^>]+src=["\']([^"\']+openapi[^"\']*)["\']',
            r'<script[^>]+src=["\']([^"\']+swagger[^"\']*)["\']',
            r'window\.openApiSpec\s*=\s*({[^}]+})',
        ]
        
        for pattern in script_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match.startswith('{'):
                    try:
                        schema = json.loads(match)
                        if is_valid_openapi_schema(schema):
                            return schema, base_url
                    except:
                        pass
                
                if match.startswith('http'):
                    url = match
                else:
                    url = base_url.rstrip('/') + match
                
                try:
                    schema_response = session.get(url, timeout=timeout)
                    if schema_response.status_code == 200:
                        try:
                            schema = schema_response.json()
                            if is_valid_openapi_schema(schema):
                                return schema, url
                        except:
                            pass
                except:
                    continue
        
    except requests.exceptions.RequestException:
        pass
    
    return None, None


def is_valid_openapi_schema(schema: Any) -> bool:
    """Check if the schema is a valid OpenAPI/Swagger schema."""
    if not isinstance(schema, dict):
        return False
    
    if 'openapi' in schema:
        return True
    if 'swagger' in schema:
        return True
    if 'paths' in schema and isinstance(schema['paths'], dict):
        return True
    
    return False


def normalize_method_name(method: str) -> str:
    """
    Normalize HTTP method name to uppercase for consistent comparison.
    
    Args:
        method: HTTP method name (GET, post, etc.)
        
    Returns:
        Normalized uppercase method name
    """
    return method.upper()


def extract_endpoint_signature(methods: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract semantic signature from endpoint methods for comparison.
    
    This extracts contract-relevant information while ignoring documentation.
    
    Args:
        methods: Dictionary of HTTP methods and their definitions
        
    Returns:
        Dictionary containing semantic signatures
    """
    signature = {}
    
    for method, details in methods.items():
        if not isinstance(details, dict):
            continue
            
        method_norm = normalize_method_name(method)
        if method_norm not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']:
            continue
            
        method_sig = {
            'parameters': [],
            'requestBody': None,
            'responses': {},
            'security': []
        }
        
        # Extract parameters (contract-relevant only, excluding body parameters)
        params = details.get('parameters', [])
        if isinstance(params, list):
            for param in params:
                if isinstance(param, dict) and param.get('in') != 'body':  # Skip body parameters
                    param_sig = {
                        'name': param.get('name'),
                        'in': param.get('in'),
                        'required': param.get('required', False),
                        'type': param.get('type'),
                        'schema': param.get('schema'),
                        'enum': param.get('enum'),
                        'default': param.get('default'),
                        'format': param.get('format'),
                        'nullable': param.get('nullable'),
                        'allowEmptyValue': param.get('allowEmptyValue')
                    }
                    
                    # Extract enum and default from schema if present
                    schema = param.get('schema')
                    if isinstance(schema, dict):
                        if 'enum' in schema:
                            param_sig['enum'] = schema['enum']
                        if 'default' in schema:
                            param_sig['default'] = schema['default']
                        if 'type' in schema and not param_sig.get('type'):
                            param_sig['type'] = schema['type']
                        if 'format' in schema and not param_sig.get('format'):
                            param_sig['format'] = schema['format']
                        if 'nullable' in schema:
                            param_sig['nullable'] = schema['nullable']
                    
                    # Remove None values to clean comparison
                    param_sig = {k: v for k, v in param_sig.items() if v is not None}
                    method_sig['parameters'].append(param_sig)
        
        # Extract request body (handle both OpenAPI 2.0 and 3.0 styles)
        request_body = details.get('requestBody')
        if request_body and isinstance(request_body, dict):
            method_sig['requestBody'] = {
                'required': request_body.get('required', False),
                'content': request_body.get('content', {})
            }
        else:
            # Check for OpenAPI 2.0 style body parameters
            body_params = details.get('parameters', [])
            if isinstance(body_params, list):
                for param in body_params:
                    if isinstance(param, dict) and param.get('in') == 'body':
                        method_sig['requestBody'] = {
                            'required': param.get('required', False),
                            'content': {
                                'application/json': {
                                    'schema': param.get('schema', {})
                                }
                            }
                        }
                        break
        
        # Extract responses (status codes and schemas)
        responses = details.get('responses', {})
        if isinstance(responses, dict):
            for status, resp_details in responses.items():
                if isinstance(resp_details, dict):
                    resp_sig = {
                        'description': resp_details.get('description', ''),
                        'content': resp_details.get('content', {}),
                        'headers': resp_details.get('headers', {})
                    }
                    method_sig['responses'][status] = resp_sig
        
        # Extract security requirements
        security = details.get('security', [])
        if isinstance(security, list):
            method_sig['security'] = security
        
        signature[method_norm] = method_sig
    
    return signature


def compare_request_body_schemas(old_body: Dict[str, Any], new_body: Dict[str, Any], endpoint: str, method: str) -> List[Dict[str, Any]]:
    """
    Compare request body schemas with detailed field-level analysis.
    
    Args:
        old_body: Old request body definition
        new_body: New request body definition
        endpoint: Endpoint path for context
        method: HTTP method for context
        
    Returns:
        List of detected changes
    """
    changes = []
    
    # Extract content schemas
    old_content = old_body.get('content', {})
    new_content = new_body.get('content', {})
    
    # Compare content types
    old_content_types = set(old_content.keys())
    new_content_types = set(new_content.keys())
    
    # Added content types
    for content_type in new_content_types - old_content_types:
        changes.append({
            'type': 'added',
            'category': 'request_body',
            'severity': 'low',
            'details': f'Content type "{content_type}" added to request body in {endpoint} {method}',
            'path': f"{endpoint}/{method}/requestBody/content/{content_type}"
        })
    
    # Removed content types
    for content_type in old_content_types - new_content_types:
        changes.append({
            'type': 'removed',
            'category': 'request_body',
            'severity': 'medium',
            'details': f'Content type "{content_type}" removed from request body in {endpoint} {method}',
            'path': f"{endpoint}/{method}/requestBody/content/{content_type}"
        })
    
    # Compare schemas for common content types
    for content_type in old_content_types & new_content_types:
        old_schema = old_content[content_type].get('schema', {})
        new_schema = new_content[content_type].get('schema', {})
        
        if old_schema and new_schema:
            schema_changes = compare_schemas_detailed(old_schema, new_schema, f"{endpoint}/{method}/requestBody/content/{content_type}/schema")
            changes.extend(schema_changes)
    
    return changes


def compare_schemas_detailed(old_schema: Dict[str, Any], new_schema: Dict[str, Any], base_path: str) -> List[Dict[str, Any]]:
    """
    Compare two schemas with detailed field-level analysis.
    
    Args:
        old_schema: Old schema definition
        new_schema: New schema definition
        base_path: Base path for change reporting
        
    Returns:
        List of detected changes
    """
    changes = []
    
    # Handle object schemas
    if old_schema.get('type') == 'object' or new_schema.get('type') == 'object':
        old_props = old_schema.get('properties', {})
        new_props = new_schema.get('properties', {})
        old_required = set(old_schema.get('required', []))
        new_required = set(new_schema.get('required', []))
        
        # Added properties
        for prop_name in new_props.keys() - old_props.keys():
            prop = new_props[prop_name]
            severity = 'low' if prop_name not in new_required else 'medium'
            changes.append({
                'type': 'added',
                'category': 'schema',
                'severity': severity,
                'details': f'Property "{prop_name}" added to object schema',
                'path': f"{base_path}/properties/{prop_name}"
            })
        
        # Removed properties
        for prop_name in old_props.keys() - new_props.keys():
            severity = 'high' if prop_name in old_required else 'medium'
            changes.append({
                'type': 'removed',
                'category': 'schema',
                'severity': severity,
                'details': f'Property "{prop_name}" removed from object schema',
                'path': f"{base_path}/properties/{prop_name}"
            })
        
        # Modified properties
        for prop_name in old_props.keys() & new_props.keys():
            old_prop = old_props[prop_name]
            new_prop = new_props[prop_name]
            
            # Type changes
            if old_prop.get('type') != new_prop.get('type'):
                changes.append({
                    'type': 'modified',
                    'category': 'schema',
                    'severity': 'medium',
                    'details': f'Property "{prop_name}" type changed from {old_prop.get("type", "unknown")} to {new_prop.get("type", "unknown")}',
                    'path': f"{base_path}/properties/{prop_name}"
                })
            
            # Required status changes
            was_required = prop_name in old_required
            is_required = prop_name in new_required
            
            if was_required != is_required:
                if is_required:
                    changes.append({
                        'type': 'modified',
                        'category': 'schema',
                        'severity': 'high',
                        'details': f'Property "{prop_name}" became required',
                        'path': f"{base_path}/properties/{prop_name}"
                    })
                else:
                    changes.append({
                        'type': 'modified',
                        'category': 'schema',
                        'severity': 'medium',
                        'details': f'Property "{prop_name}" became optional',
                        'path': f"{base_path}/properties/{prop_name}"
                    })
            
            # Nested comparison for complex properties
            if old_prop.get('type') == 'object' and new_prop.get('type') == 'object':
                nested_changes = compare_schemas_detailed(
                    old_prop, new_prop, f"{base_path}/properties/{prop_name}"
                )
                changes.extend(nested_changes)
    
    # Handle array schemas
    elif old_schema.get('type') == 'array' or new_schema.get('type') == 'array':
        old_items = old_schema.get('items', {})
        new_items = new_schema.get('items', {})
        
        if old_items and new_items:
            item_changes = compare_schemas_detailed(
                old_items, new_items, f"{base_path}/items"
            )
            changes.extend(item_changes)
    
    # Handle type changes at root level
    if old_schema.get('type') != new_schema.get('type'):
        changes.append({
            'type': 'modified',
            'category': 'schema',
            'severity': 'high',
            'details': f'Schema type changed from {old_schema.get("type", "unknown")} to {new_schema.get("type", "unknown")}',
            'path': base_path
        })
    
    return changes


def compare_endpoint_signatures(old_sig: Dict[str, Any], new_sig: Dict[str, Any], endpoint: str) -> List[Dict[str, Any]]:
    """
    Compare two endpoint signatures semantically.
    
    Args:
        old_sig: Old endpoint signature
        new_sig: New endpoint signature  
        endpoint: Endpoint path for context
        
    Returns:
        List of detected changes
    """
    changes = []
    
    old_methods = set(old_sig.keys())
    new_methods = set(new_sig.keys())
    
    # Method additions
    for method in new_methods - old_methods:
        changes.append({
            'type': 'added',
            'category': 'endpoint',
            'severity': 'low',
            'details': f'New method {method} added to {endpoint}',
            'path': f"{endpoint}/{method}"
        })
    
    # Method removals
    for method in old_methods - new_methods:
        changes.append({
            'type': 'removed',
            'category': 'endpoint',
            'severity': 'high',
            'details': f'Method {method} removed from {endpoint}',
            'path': f"{endpoint}/{method}"
        })
    
    # Method modifications
    for method in old_methods & new_methods:
        old_method_sig = old_sig[method]
        new_method_sig = new_sig[method]
        
        # Compare parameters
        old_params = {p['name']: p for p in old_method_sig.get('parameters', []) if 'name' in p}
        new_params = {p['name']: p for p in new_method_sig.get('parameters', []) if 'name' in p}
        
        # Parameter additions
        for param_name in new_params.keys() - old_params.keys():
            param = new_params[param_name]
            changes.append({
                'type': 'added',
                'category': 'parameter',
                'severity': 'medium' if param.get('required', False) else 'low',
                'details': f'Parameter "{param_name}" ({param.get("type", "unknown")}) added to {endpoint} {method}',
                'path': f"{endpoint}/{method}/parameters/{param_name}"
            })
        
        # Parameter removals
        for param_name in old_params.keys() - new_params.keys():
            param = old_params[param_name]
            changes.append({
                'type': 'removed',
                'category': 'parameter',
                'severity': 'high' if param.get('required', False) else 'medium',
                'details': f'Parameter "{param_name}" ({param.get("type", "unknown")}) removed from {endpoint} {method}',
                'path': f"{endpoint}/{method}/parameters/{param_name}"
            })
        
        # Parameter modifications
        for param_name in old_params.keys() & new_params.keys():
            old_param = old_params[param_name]
            new_param = new_params[param_name]
            
            # Check for location changes
            if old_param.get('in') != new_param.get('in'):
                changes.append({
                    'type': 'modified',
                    'category': 'parameter',
                    'severity': 'high',
                    'details': f'Parameter "{param_name}" location changed from {old_param.get("in", "unknown")} to {new_param.get("in", "unknown")} in {endpoint} {method}',
                    'path': f"{endpoint}/{method}/parameters/{param_name}"
                })
            
            # Check for type changes
            if old_param.get('type') != new_param.get('type'):
                changes.append({
                    'type': 'modified',
                    'category': 'parameter',
                    'severity': 'medium',
                    'details': f'Parameter "{param_name}" type changed from {old_param.get("type", "unknown")} to {new_param.get("type", "unknown")} in {endpoint} {method}',
                    'path': f"{endpoint}/{method}/parameters/{param_name}"
                })
            
            # Check for format changes
            if old_param.get('format') != new_param.get('format'):
                changes.append({
                    'type': 'modified',
                    'category': 'parameter',
                    'severity': 'low',
                    'details': f'Parameter "{param_name}" format changed from {old_param.get("format", "none")} to {new_param.get("format", "none")} in {endpoint} {method}',
                    'path': f"{endpoint}/{method}/parameters/{param_name}"
                })
            
            # Check for required status changes
            if old_param.get('required', False) != new_param.get('required', False):
                changes.append({
                    'type': 'modified',
                    'category': 'parameter',
                    'severity': 'high',
                    'details': f'Parameter "{param_name}" required status changed from {old_param.get("required", False)} to {new_param.get("required", False)} in {endpoint} {method}',
                    'path': f"{endpoint}/{method}/parameters/{param_name}"
                })
            
            # Check for enum changes
            old_enum = old_param.get('enum')
            new_enum = new_param.get('enum')
            
            if old_enum != new_enum:
                if old_enum and not new_enum:
                    changes.append({
                        'type': 'removed',
                        'category': 'parameter',
                        'severity': 'medium',
                        'details': f'Parameter "{param_name}" enum values removed in {endpoint} {method}',
                        'path': f"{endpoint}/{method}/parameters/{param_name}"
                    })
                elif not old_enum and new_enum:
                    changes.append({
                        'type': 'added',
                        'category': 'parameter',
                        'severity': 'low',
                        'details': f'Parameter "{param_name}" enum values added in {endpoint} {method}',
                        'path': f"{endpoint}/{method}/parameters/{param_name}"
                    })
                else:
                    # Both have enums, compare differences
                    old_set = set(old_enum) if old_enum else set()
                    new_set = set(new_enum) if new_enum else set()
                    
                    added_values = new_set - old_set
                    removed_values = old_set - new_set
                    
                    if added_values:
                        changes.append({
                            'type': 'added',
                            'category': 'parameter',
                            'severity': 'low',
                            'details': f'Parameter "{param_name}" enum values added: {", ".join(map(str, added_values))} in {endpoint} {method}',
                            'path': f"{endpoint}/{method}/parameters/{param_name}"
                        })
                    
                    if removed_values:
                        changes.append({
                            'type': 'removed',
                            'category': 'parameter',
                            'severity': 'medium',
                            'details': f'Parameter "{param_name}" enum values removed: {", ".join(map(str, removed_values))} in {endpoint} {method}',
                            'path': f"{endpoint}/{method}/parameters/{param_name}"
                        })
            
            # Check for default value changes
            if old_param.get('default') != new_param.get('default'):
                if old_param.get('default') is None and new_param.get('default') is not None:
                    changes.append({
                        'type': 'added',
                        'category': 'parameter',
                        'severity': 'low',
                        'details': f'Parameter "{param_name}" default value set to {new_param.get("default")} in {endpoint} {method}',
                        'path': f"{endpoint}/{method}/parameters/{param_name}"
                    })
                elif old_param.get('default') is not None and new_param.get('default') is None:
                    changes.append({
                        'type': 'removed',
                        'category': 'parameter',
                        'severity': 'low',
                        'details': f'Parameter "{param_name}" default value removed in {endpoint} {method}',
                        'path': f"{endpoint}/{method}/parameters/{param_name}"
                    })
                else:
                    changes.append({
                        'type': 'modified',
                        'category': 'parameter',
                        'severity': 'low',
                        'details': f'Parameter "{param_name}" default value changed from {old_param.get("default")} to {new_param.get("default")} in {endpoint} {method}',
                        'path': f"{endpoint}/{method}/parameters/{param_name}"
                    })
            
            # Check for nullable changes
            if old_param.get('nullable') != new_param.get('nullable'):
                changes.append({
                    'type': 'modified',
                    'category': 'parameter',
                    'severity': 'low',
                    'details': f'Parameter "{param_name}" nullable status changed from {old_param.get("nullable")} to {new_param.get("nullable")} in {endpoint} {method}',
                    'path': f"{endpoint}/{method}/parameters/{param_name}"
                })
        
        # Compare request bodies with detailed field-level analysis
        old_body = old_method_sig.get('requestBody')
        new_body = new_method_sig.get('requestBody')
        
        if old_body and not new_body:
            changes.append({
                'type': 'removed',
                'category': 'request_body',
                'severity': 'high',
                'details': f'Request body removed from {endpoint} {method}',
                'path': f"{endpoint}/{method}/requestBody"
            })
        elif not old_body and new_body:
            changes.append({
                'type': 'added',
                'category': 'request_body',
                'severity': 'medium',
                'details': f'Request body added to {endpoint} {method}',
                'path': f"{endpoint}/{method}/requestBody"
            })
        elif old_body and new_body:
            # Detailed comparison of request body schemas
            body_changes = compare_request_body_schemas(old_body, new_body, endpoint, method)
            changes.extend(body_changes)
        
        # Compare responses
        old_responses = set(old_method_sig.get('responses', {}).keys())
        new_responses = set(new_method_sig.get('responses', {}).keys())
        
        # Response additions
        for status in new_responses - old_responses:
            changes.append({
                'type': 'added',
                'category': 'response',
                'severity': 'low',
                'details': f'New response code {status} added to {endpoint} {method}',
                'path': f"{endpoint}/{method}/responses/{status}"
            })
        
        # Response removals
        for status in old_responses - new_responses:
            changes.append({
                'type': 'removed',
                'category': 'response',
                'severity': 'medium',
                'details': f'Response code {status} removed from {endpoint} {method}',
                'path': f"{endpoint}/{method}/responses/{status}"
            })
        
        # Response modifications with detailed schema analysis
        for status in old_responses & new_responses:
            old_resp = old_method_sig['responses'][status]
            new_resp = new_method_sig['responses'][status]
            
            # Compare content schemas with detailed analysis
            old_content = old_resp.get('content', {})
            new_content = new_resp.get('content', {})
            
            old_content_types = set(old_content.keys())
            new_content_types = set(new_content.keys())
            
            # Added content types
            for content_type in new_content_types - old_content_types:
                changes.append({
                    'type': 'added',
                    'category': 'response',
                    'severity': 'low',
                    'details': f'Content type "{content_type}" added to response {status} in {endpoint} {method}',
                    'path': f"{endpoint}/{method}/responses/{status}/content/{content_type}"
                })
            
            # Removed content types
            for content_type in old_content_types - new_content_types:
                changes.append({
                    'type': 'removed',
                    'category': 'response',
                    'severity': 'medium',
                    'details': f'Content type "{content_type}" removed from response {status} in {endpoint} {method}',
                    'path': f"{endpoint}/{method}/responses/{status}/content/{content_type}"
                })
            
            # Compare schemas for common content types
            for content_type in old_content_types & new_content_types:
                old_schema = old_content[content_type].get('schema', {})
                new_schema = new_content[content_type].get('schema', {})
                
                if old_schema and new_schema:
                    schema_changes = compare_schemas_detailed(
                        old_schema, new_schema, f"{endpoint}/{method}/responses/{status}/content/{content_type}/schema"
                    )
                    changes.extend(schema_changes)
            
            # Compare headers
            old_headers = old_resp.get('headers', {})
            new_headers = new_resp.get('headers', {})
            
            old_header_names = set(old_headers.keys())
            new_header_names = set(new_headers.keys())
            
            # Added headers
            for header_name in new_header_names - old_header_names:
                changes.append({
                    'type': 'added',
                    'category': 'response',
                    'severity': 'low',
                    'details': f'Header "{header_name}" added to response {status} in {endpoint} {method}',
                    'path': f"{endpoint}/{method}/responses/{status}/headers/{header_name}"
                })
            
            # Removed headers
            for header_name in old_header_names - new_header_names:
                changes.append({
                    'type': 'removed',
                    'category': 'response',
                    'severity': 'medium',
                    'details': f'Header "{header_name}" removed from response {status} in {endpoint} {method}',
                    'path': f"{endpoint}/{method}/responses/{status}/headers/{header_name}"
                })
            
            # Modified headers
            for header_name in old_header_names & new_header_names:
                old_header = old_headers[header_name]
                new_header = new_headers[header_name]
                
                if old_header != new_header:
                    changes.append({
                        'type': 'modified',
                        'category': 'response',
                        'severity': 'low',
                        'details': f'Header "{header_name}" modified in response {status} in {endpoint} {method}',
                        'path': f"{endpoint}/{method}/responses/{status}/headers/{header_name}"
                    })
    
    return changes


def classify_change_breaking(change: Dict[str, Any]) -> str:
    """
    Classify a change as breaking, non-breaking, or info.
    
    Args:
        change: Change dictionary with type, category, severity, and details
        
    Returns:
        Classification: 'breaking', 'non_breaking', or 'info'
    """
    change_type = change.get('type', '')
    category = change.get('category', '')
    details = change.get('details', '').lower()
    
    # BREAKING changes
    breaking_patterns = [
        # Endpoint removals
        ('endpoint', 'removed'),
        ('endpoint', 'removed'),
        
        # Required parameter changes
        ('parameter', 'required'),
        ('parameter', 'removed'),
        
        # Schema property removals and required changes
        ('schema', 'removed'),
        ('schema', 'became required'),
        ('schema', 'type changed'),
        
        # Request body removals
        ('request_body', 'removed'),
        
        # Response removals
        ('response', 'removed'),
        
        # Component schema removals
        ('component', 'removed'),
        
        # Authentication changes
        ('authentication', 'modified'),
    ]
    
    for cat, typ in breaking_patterns:
        if (cat in category or cat == category) and (typ in change_type or typ in details):
            return 'breaking'
    
    # NON_BREAKING changes
    non_breaking_patterns = [
        # Endpoint additions
        ('endpoint', 'added'),
        
        # Optional parameter additions
        ('parameter', 'added'),
        
        # Optional schema property additions
        ('schema', 'added'),
        ('schema', 'became optional'),
        
        # Request body additions
        ('request_body', 'added'),
        
        # Response additions
        ('response', 'added'),
        
        # Component additions
        ('component', 'added'),
    ]
    
    for cat, typ in non_breaking_patterns:
        if (cat in category or cat == category) and (typ in change_type or typ in details):
            return 'non_breaking'
    
    # INFO changes (documentation-only, low impact)
    info_patterns = [
        # Description changes
        ('description', 'changed'),
        
        # Low severity changes
        ('low', ''),
        
        # Header additions/modifications
        ('header', 'added'),
        ('header', 'modified'),
        
        # Enum additions
        ('enum', 'added'),
        
        # Default value changes
        ('default', 'changed'),
        ('default', 'added'),
        ('default', 'removed'),
        
        # Format changes
        ('format', 'changed'),
        
        # Nullable changes
        ('nullable', 'changed'),
    ]
    
    for cat, typ in info_patterns:
        if (cat in details or cat in category) and (typ in details or typ in change_type):
            return 'info'
    
    # Default classification based on severity
    severity = change.get('severity', '').lower()
    if severity in ['critical', 'high']:
        return 'breaking'
    elif severity == 'medium':
        return 'non_breaking'
    else:
        return 'info'


def generate_diff_summary(changes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for schema changes.
    
    Args:
        changes: List of change dictionaries
        
    Returns:
        Summary dictionary with statistics
    """
    summary = {
        'total_changes': len(changes),
        'added_endpoints': 0,
        'removed_endpoints': 0,
        'breaking_changes': 0,
        'non_breaking_changes': 0,
        'info_changes': 0,
        'by_category': {},
        'by_severity': {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
    }
    
    for change in changes:
        # Count by breaking classification
        breaking_change = change.get('breaking_change', 'info')
        if breaking_change == 'breaking':
            summary['breaking_changes'] += 1
        elif breaking_change == 'non_breaking':
            summary['non_breaking_changes'] += 1
        else:
            summary['info_changes'] += 1
        
        # Count by category
        category = change.get('category', 'unknown')
        if category not in summary['by_category']:
            summary['by_category'][category] = 0
        summary['by_category'][category] += 1
        
        # Count by severity
        severity = change.get('severity', 'low')
        if severity in summary['by_severity']:
            summary['by_severity'][severity] += 1
        
        # Count endpoint additions/removals
        if category == 'endpoint':
            if change.get('type') == 'added':
                summary['added_endpoints'] += 1
            elif change.get('type') == 'removed':
                summary['removed_endpoints'] += 1
    
    return summary


def compare_schemas_structured(old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two schemas and return structured output with summary.
    
    This function provides the enhanced output format with summary statistics
    while maintaining backward compatibility.
    
    Args:
        old_schema: Old OpenAPI schema
        new_schema: New OpenAPI schema
        
    Returns:
        Structured diff result with summary and changes
    """
    # Get the raw changes using the existing function
    changes = compare_schemas(old_schema, new_schema)
    
    # Generate summary
    summary = generate_diff_summary(changes)
    
    # Return structured result
    return {
        'summary': summary,
        'changes': changes
    }


def enhance_change_classification(changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhance changes with breaking/non-breaking/info classification.
    
    Args:
        changes: List of change dictionaries
        
    Returns:
        Enhanced list with classification added
    """
    for change in changes:
        classification = classify_change_breaking(change)
        change['breaking_change'] = classification
        
        # Adjust severity based on breaking classification
        if classification == 'breaking' and change.get('severity') == 'medium':
            change['severity'] = 'high'
        elif classification == 'info' and change.get('severity') == 'medium':
            change['severity'] = 'low'
    
    return changes


def compare_component_schemas(old_components: Dict[str, Any], new_components: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compare component schemas with detailed analysis.
    
    Args:
        old_components: Old components section
        new_components: New components section
        
    Returns:
        List of detected changes
    """
    changes = []
    
    # Get schemas from both versions
    old_schemas = old_components.get('schemas', {})
    new_schemas = new_components.get('schemas', {})
    
    # Added schemas
    for schema_name in new_schemas.keys() - old_schemas.keys():
        changes.append({
            'type': 'added',
            'category': 'component',
            'severity': 'low',
            'details': f'Component schema "{schema_name}" added',
            'path': f"components/schemas/{schema_name}"
        })
    
    # Removed schemas
    for schema_name in old_schemas.keys() - new_schemas.keys():
        changes.append({
            'type': 'removed',
            'category': 'component',
            'severity': 'high',
            'details': f'Component schema "{schema_name}" removed',
            'path': f"components/schemas/{schema_name}"
        })
    
    # Modified schemas
    for schema_name in old_schemas.keys() & new_schemas.keys():
        old_schema = old_schemas[schema_name]
        new_schema = new_schemas[schema_name]
        
        schema_changes = compare_schemas_detailed(
            old_schema, new_schema, f"components/schemas/{schema_name}"
        )
        changes.extend(schema_changes)
    
    # Compare other component types (parameters, responses, etc.)
    for component_type in ['parameters', 'responses', 'securitySchemes', 'headers', 'examples', 'requestBodies']:
        old_items = old_components.get(component_type, {})
        new_items = new_components.get(component_type, {})
        
        # Added items
        for item_name in new_items.keys() - old_items.keys():
            changes.append({
                'type': 'added',
                'category': 'component',
                'severity': 'low',
                'details': f'Component {component_type} "{item_name}" added',
                'path': f"components/{component_type}/{item_name}"
            })
        
        # Removed items
        for item_name in old_items.keys() - new_items.keys():
            changes.append({
                'type': 'removed',
                'category': 'component',
                'severity': 'medium',
                'details': f'Component {component_type} "{item_name}" removed',
                'path': f"components/{component_type}/{item_name}"
            })
        
        # Modified items
        for item_name in old_items.keys() & new_items.keys():
            old_item = old_items[item_name]
            new_item = new_items[item_name]
            
            if old_item != new_item:
                changes.append({
                    'type': 'modified',
                    'category': 'component',
                    'severity': 'low',
                    'details': f'Component {component_type} "{item_name}" modified',
                    'path': f"components/{component_type}/{item_name}"
                })
    
    return changes


def deduplicate_changes(changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate changes from the list based on path and type.
    
    Args:
        changes: List of change dictionaries
        
    Returns:
        Deduplicated list of changes
    """
    seen = set()
    deduplicated = []
    
    for change in changes:
        # Create a unique key based on path, type, and the essential change details
        path = change.get('path', '')
        change_type = change.get('type', '')
        details = change.get('details', '')
        category = change.get('category', '')
        
        # Handle component schema removals that appear in multiple forms
        if change_type == 'removed' and 'components/schemas/' in path:
            # Extract the component name from the path
            comp_name = path.split('components/schemas/')[-1].split('/')[0]
            
            # Create a unified key for component removals regardless of how they're detected
            if ('Component schema' in details or 
                'Property "' in details and 'removed from' in details or
                category in ['component', 'schema']):
                
                unique_key = f"component:removed:{comp_name}"
            else:
                unique_key = f"{change_type}:{path}:{details[:50]}"
        
        # Handle property changes in object schemas (not component schemas)
        elif ('Property "' in details and 
              ('" removed from object schema' in details or '" added to object schema' in details) and
              'components/schemas/' not in path):
            
            if '" removed from object schema' in details:
                action = 'removed'
            else:
                action = 'added'
            
            prop_match = details.split('Property "')[1].split('"')[0]
            path_parts = path.split('/properties/')
            if len(path_parts) > 1:
                base_path = path_parts[0]
                unique_key = f"{change_type}:{base_path}:property:{prop_match}:{action}"
            else:
                unique_key = f"{change_type}:{path}:{prop_match}:{action}"
        
        # Handle explicit component changes
        elif category == 'component' and ('Component schema "' in details or 'Component ' in details):
            if 'removed' in details:
                action = 'removed'
            elif 'added' in details:
                action = 'added'
            else:
                action = 'modified'
            
            # Extract component name from details
            if 'Component schema "' in details:
                comp_name = details.split('Component schema "')[1].split('"')[0]
            elif 'Component ' in details and '"' in details:
                comp_name = details.split('Component ')[1].split(' "')[1].split('"')[0] if ' "' in details else details.split('Component ')[1].split('"')[0]
            else:
                comp_name = path.split('/')[-1]
            
            unique_key = f"component:{action}:{comp_name}"
        
        # Handle endpoint changes
        elif category == 'endpoint' and ('endpoint' in details.lower()):
            if 'added' in details.lower():
                action = 'added'
            elif 'removed' in details.lower():
                action = 'removed'
            else:
                action = 'modified'
            
            endpoint_name = path if path else details.split('"')[1] if '"' in details else details
            unique_key = f"{change_type}:endpoint:{endpoint_name}:{action}"
        
        # Handle parameter, response, and request body changes
        elif category in ['parameter', 'response', 'request_body']:
            if 'removed' in details.lower():
                action = 'removed'
            elif 'added' in details.lower():
                action = 'added'
            else:
                action = 'modified'
            
            if '"' in details:
                item_name = details.split('"')[1]
            else:
                item_name = path.split('/')[-1] if path else details
            
            unique_key = f"{change_type}:{category}:{item_name}:{action}"
        
        else:
            # For other changes, use the full path and type with a simplified details hash
            import hashlib
            details_hash = hashlib.md5(details.encode()).hexdigest()[:8]
            unique_key = f"{change_type}:{path}:{details_hash}"
        
        if unique_key not in seen:
            seen.add(unique_key)
            deduplicated.append(change)
    
    return deduplicated


def compare_schemas(old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compare two schemas and return a comprehensive list of changes."""
    changes = []
    
    # Normalize both schemas for stable comparison
    try:
        old_normalized = normalize_schema(old_schema)
        new_normalized = normalize_schema(new_schema)
    except Exception as e:
        # Fallback to original schemas if normalization fails
        old_normalized = old_schema
        new_normalized = new_schema
        print(f"Schema normalization failed: {e}")
    
    def deep_compare(obj1, obj2, path="", current_path=""):
        """Recursively compare two objects and find all differences."""
        differences = []
        
        if type(obj1) != type(obj2):
            differences.append({
                'type': 'modified',
                'category': 'schema',
                'severity': 'high',
                'details': f'Type changed from {type(obj1).__name__} to {type(obj2).__name__} at {path}',
                'path': current_path or 'root'
            })
            return differences
        
        if isinstance(obj1, dict) and isinstance(obj2, dict):
            # Check for removed keys
            for key in obj1:
                if key not in obj2:
                    differences.append({
                        'type': 'removed',
                        'category': 'schema',
                        'severity': 'medium',
                        'details': f'Property "{key}" removed from {path}',
                        'path': f"{current_path}/{key}" if current_path else key
                    })
            
            # Check for added keys
            for key in obj2:
                if key not in obj1:
                    differences.append({
                        'type': 'added',
                        'category': 'schema',
                        'severity': 'medium',
                        'details': f'Property "{key}" added to {path}',
                        'path': f"{current_path}/{key}" if current_path else key
                    })
            
            # Check for modified values
            for key in obj1:
                if key in obj2:
                    new_path = f"{current_path}/{key}" if current_path else key
                    value_diffs = deep_compare(obj1[key], obj2[key], new_path, new_path)
                    differences.extend(value_diffs)
        
        elif isinstance(obj1, list) and isinstance(obj2, list):
            # Check for removed items
            for i, item in enumerate(obj1):
                if item not in obj2:
                    differences.append({
                        'type': 'removed',
                        'category': 'schema',
                        'severity': 'low',
                        'details': f'Array item removed from {path}[{i}]',
                        'path': f"{current_path}[{i}]"
                    })
            
            # Check for added items
            for i, item in enumerate(obj2):
                if item not in obj1:
                    differences.append({
                        'type': 'added',
                        'category': 'schema',
                        'severity': 'low',
                        'details': f'Array item added to {path}[{i}]',
                        'path': f"{current_path}[{i}]"
                    })
        
        elif isinstance(obj1, str) and isinstance(obj2, str):
            if obj1 != obj2:
                differences.append({
                    'type': 'modified',
                    'category': 'schema',
                    'severity': 'low',
                    'details': f'Value changed from "{obj1}" to "{obj2}" at {path}',
                    'path': current_path or 'root'
                })
        
        return differences
    
    # Perform comprehensive comparison
    schema_differences = deep_compare(old_normalized, new_normalized)
    
    # Add specific endpoint, parameter, and response comparisons
    old_paths = old_normalized.get('paths', {})
    new_paths = new_normalized.get('paths', {})
    
    # Endpoint changes using semantic comparison
    old_endpoints = set(old_paths.keys())
    new_endpoints = set(new_paths.keys())
    
    # Added endpoints
    for endpoint in new_endpoints - old_endpoints:
        changes.append({
            'type': 'added',
            'category': 'endpoint',
            'severity': 'low',
            'details': f'New endpoint "{endpoint}" added to API',
            'path': endpoint
        })
    
    # Removed endpoints
    for endpoint in old_endpoints - new_endpoints:
        changes.append({
            'type': 'removed',
            'category': 'endpoint',
            'severity': 'high',
            'details': f'Endpoint "{endpoint}" removed from API',
            'path': endpoint
        })
    
    # Semantic comparison for existing endpoints
    for endpoint in old_endpoints & new_endpoints:
        old_methods = old_paths.get(endpoint, {})
        new_methods = new_paths.get(endpoint, {})
        
        if isinstance(old_methods, dict) and isinstance(new_methods, dict):
            # Extract semantic signatures for comparison
            old_signature = extract_endpoint_signature(old_methods)
            new_signature = extract_endpoint_signature(new_methods)
            
            # Compare signatures semantically
            semantic_changes = compare_endpoint_signatures(old_signature, new_signature, endpoint)
            changes.extend(semantic_changes)
    
    # Component schema comparison
    old_components = old_normalized.get('components', {})
    new_components = new_normalized.get('components', {})
    
    if old_components or new_components:
        component_changes = compare_component_schemas(old_components, new_components)
        changes.extend(component_changes)
    
    # Security changes
    old_security = old_schema.get('security', [])
    new_security = new_schema.get('security', [])
    
    if not old_security and new_security:
        changes.append({
            'type': 'modified',
            'category': 'authentication',
            'severity': 'critical',
            'details': 'Authentication requirements added to API',
            'path': 'security'
        })
    elif old_security and not new_security:
        changes.append({
            'type': 'modified',
            'category': 'authentication',
            'severity': 'critical',
            'details': 'Authentication requirements removed from API',
            'path': 'security'
        })
    elif old_security != new_security:
        changes.append({
            'type': 'modified',
            'category': 'authentication',
            'severity': 'high',
            'details': 'Authentication configuration changed',
            'path': 'security'
        })
    
    # Combine all changes
    all_changes = schema_differences + changes
    
    # Enhance changes with breaking/non-breaking/info classification
    all_changes = enhance_change_classification(all_changes)
    
    # Remove duplicates
    all_changes = deduplicate_changes(all_changes)
    
    return all_changes
