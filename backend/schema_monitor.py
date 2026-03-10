import requests
import json
import io
import re
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime

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


def compare_schemas(old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compare two schemas and return a comprehensive list of changes."""
    changes = []
    
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
                    value_diffs = deep_compare(obj1[key], obj2[key], new_path, key)
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
    schema_differences = deep_compare(old_schema, new_schema)
    
    # Add specific endpoint, parameter, and response comparisons
    old_paths = old_schema.get('paths', {})
    new_paths = new_schema.get('paths', {})
    
    # Endpoint changes
    old_endpoints = set(old_paths.keys())
    new_endpoints = set(new_paths.keys())
    
    for endpoint in new_endpoints - old_endpoints:
        changes.append({
            'type': 'added',
            'category': 'endpoint',
            'severity': 'low',
            'details': f'New endpoint "{endpoint}" added to API',
            'path': endpoint
        })
    
    for endpoint in old_endpoints - new_endpoints:
        changes.append({
            'type': 'removed',
            'category': 'endpoint',
            'severity': 'high',
            'details': f'Endpoint "{endpoint}" removed from API',
            'path': endpoint
        })
    
    # Detailed endpoint method and parameter comparison
    for endpoint in old_endpoints & new_endpoints:
        old_methods = old_paths.get(endpoint, {})
        new_methods = new_paths.get(endpoint, {})
        
        if isinstance(old_methods, dict) and isinstance(new_methods, dict):
            old_method_set = set(k.lower() for k in old_methods.keys() if k.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
            new_method_set = set(k.lower() for k in new_methods.keys() if k.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
            
            # Method changes
            for method in new_method_set - old_method_set:
                changes.append({
                    'type': 'added',
                    'category': 'endpoint',
                    'severity': 'low',
                    'details': f'New method {method.upper()} added to {endpoint}',
                    'path': f"{endpoint}/{method.upper()}"
                })
            
            for method in old_method_set - new_method_set:
                changes.append({
                    'type': 'removed',
                    'category': 'endpoint',
                    'severity': 'high',
                    'details': f'Method {method.upper()} removed from {endpoint}',
                    'path': f"{endpoint}/{method.upper()}"
                })
            
            # Detailed parameter comparison for each method
            for method in old_method_set & new_method_set:
                old_details = old_methods.get(method.upper()) or old_methods.get(method.lower()) or {}
                new_details = new_methods.get(method.upper()) or new_methods.get(method.lower()) or {}
                
                old_params = old_details.get('parameters', [])
                new_params = new_details.get('parameters', [])
                
                # Parameter additions
                for param in new_params:
                    if param not in old_params:
                        param_name = param.get('name', 'unnamed')
                        param_type = param.get('type', 'unknown')
                        param_required = param.get('required', False)
                        changes.append({
                            'type': 'added',
                            'category': 'parameter',
                            'severity': 'medium',
                            'details': f'Parameter "{param_name}" ({param_type}) added to {endpoint} {method.upper()}',
                            'path': f"{endpoint}/{method.upper()}/parameters/{param_name}"
                        })
                
                # Parameter removals
                for param in old_params:
                    if param not in new_params:
                        param_name = param.get('name', 'unnamed')
                        param_type = param.get('type', 'unknown')
                        changes.append({
                            'type': 'removed',
                            'category': 'parameter',
                            'severity': 'high',
                            'details': f'Parameter "{param_name}" ({param_type}) removed from {endpoint} {method.upper()}',
                            'path': f"{endpoint}/{method.upper()}/parameters/{param_name}"
                        })
                
                # Parameter modifications
                for param in old_params:
                    if param in new_params:
                        old_param = old_params[old_params.index(param)]
                        new_param = new_params[new_params.index(param)]
                        
                        param_name = param.get('name', 'unnamed')
                        param_path = f"{endpoint}/{method.upper()}/parameters/{param_name}"
                        
                        # Check for type changes
                        if old_param.get('type') != new_param.get('type'):
                            changes.append({
                                'type': 'modified',
                                'category': 'parameter',
                                'severity': 'medium',
                                'details': f'Parameter "{param_name}" type changed from {old_param.get("type", "unknown")} to {new_param.get("type", "unknown")} in {endpoint} {method.upper()}',
                                'path': param_path
                            })
                        
                        # Check for required status changes
                        if old_param.get('required') != new_param.get('required'):
                            changes.append({
                                'type': 'modified',
                                'category': 'parameter',
                                'severity': 'high',
                                'details': f'Parameter "{param_name}" required status changed from {old_param.get("required")} to {new_param.get("required")} in {endpoint} {method.upper()}',
                                'path': param_path
                            })
                        
                        # Check for description changes
                        if old_param.get('description') != new_param.get('description'):
                            changes.append({
                                'type': 'modified',
                                'category': 'parameter',
                                'severity': 'low',
                                'details': f'Parameter "{param_name}" description changed in {endpoint} {method.upper()}',
                                'path': param_path
                            })
                        
                        # Deep compare parameter schemas
                        if 'schema' in old_param and 'schema' in new_param:
                            schema_diffs = deep_compare(old_param['schema'], new_param['schema'], param_path, 'schema')
                            changes.extend(schema_diffs)
                
                # Response changes
                old_responses = old_details.get('responses', {})
                new_responses = new_details.get('responses', {})
                
                old_response_codes = set(old_responses.keys())
                new_response_codes = set(new_responses.keys())
                
                # Added response codes
                for code in new_response_codes - old_response_codes:
                    changes.append({
                        'type': 'added',
                        'category': 'response',
                        'severity': 'low',
                        'details': f'New response code {code} added to {endpoint} {method.upper()}',
                        'path': f"{endpoint}/{method.upper()}/responses/{code}"
                    })
                
                # Removed response codes
                for code in old_response_codes - new_response_codes:
                    changes.append({
                        'type': 'removed',
                        'category': 'response',
                        'severity': 'medium',
                        'details': f'Response code {code} removed from {endpoint} {method.upper()}',
                        'path': f"{endpoint}/{method.upper()}/responses/{code}"
                    })
                
                # Modified response codes
                for code in old_response_codes & new_response_codes:
                    old_resp = old_responses[code]
                    new_resp = new_responses[code]
                    
                    if old_resp.get('description') != new_resp.get('description'):
                        changes.append({
                            'type': 'modified',
                            'category': 'response',
                            'severity': 'low',
                            'details': f'Response {code} description changed in {endpoint} {method.upper()}',
                            'path': f"{endpoint}/{method.upper()}/responses/{code}/description"
                        })
                    
                    # Deep compare response schemas
                    if 'schema' in old_resp and 'schema' in new_resp:
                        schema_diffs = deep_compare(old_resp['schema'], new_resp['schema'], f"{endpoint}/{method.upper()}/responses/{code}", 'schema')
                        changes.extend(schema_diffs)
    
    # Security changes
    old_security = old_schema.get('security', [])
    new_security = new_schema.get('security', [])
    
    if not old_security and new_security:
        changes.append({
            'type': 'modified',
            'category': 'authentication',
            'severity': 'critical',
            'details': 'Authentication requirements added to API'
        })
    elif old_security and not new_security:
        changes.append({
            'type': 'modified',
            'category': 'authentication',
            'severity': 'critical',
            'details': 'Authentication requirements removed from API'
        })
    elif old_security != new_security:
        changes.append({
            'type': 'modified',
            'category': 'authentication',
            'severity': 'high',
            'details': 'Authentication configuration changed'
        })
    
    return changes
