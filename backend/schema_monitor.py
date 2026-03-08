import requests
import json
import io
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

SCHEMA_PATHS = [
    '/schema',
    '/openapi',
    '/swagger',
    '/docs',
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


def crawl_for_schema(base_url: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Crawl the API base URL for schema endpoints."""
    
    if not base_url.startswith('http://') and not base_url.startswith('https://'):
        base_url = 'https://' + base_url
    
    session = requests.Session()
    session.headers.update({
        'Accept': 'application/json, application/yaml, text/html',
        'User-Agent': 'APISec-Schema-Monitor/1.0'
    })
    
    for path in SCHEMA_PATHS:
        url = base_url.rstrip('/') + path
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                
                if 'json' in content_type:
                    try:
                        schema = response.json()
                        if is_valid_openapi_schema(schema):
                            return schema, url
                    except:
                        pass
                elif 'yaml' in content_type:
                    try:
                        import yaml
                        schema = yaml.safe_load(response.text)
                        if is_valid_openapi_schema(schema):
                            return schema, url
                    except:
                        pass
                else:
                    try:
                        schema = response.json()
                        if is_valid_openapi_schema(schema):
                            return schema, url
                    except:
                        pass
                        
        except requests.exceptions.RequestException:
            continue
    
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
    """Compare two schemas and return a list of changes."""
    changes = []
    
    old_paths = old_schema.get('paths', {})
    new_paths = new_schema.get('paths', {})
    
    old_endpoints = set(old_paths.keys())
    new_endpoints = set(new_paths.keys())
    
    for endpoint in new_endpoints - old_endpoints:
        changes.append({
            'type': 'added',
            'category': 'endpoint',
            'severity': 'low',
            'details': f'New endpoint added: {endpoint}',
            'path': endpoint
        })
    
    for endpoint in old_endpoints - new_endpoints:
        changes.append({
            'type': 'removed',
            'category': 'endpoint',
            'severity': 'high',
            'details': f'Endpoint removed: {endpoint}',
            'path': endpoint
        })
    
    for endpoint in old_endpoints & new_endpoints:
        old_methods = old_paths.get(endpoint, {})
        new_methods = new_paths.get(endpoint, {})
        
        if isinstance(old_methods, dict) and isinstance(new_methods, dict):
            old_method_set = set(k.lower() for k in old_methods.keys() if k.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
            new_method_set = set(k.lower() for k in new_methods.keys() if k.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
            
            for method in new_method_set - old_method_set:
                changes.append({
                    'type': 'added',
                    'category': 'endpoint',
                    'severity': 'low',
                    'details': f'New method {method.upper()} added to {endpoint}',
                    'path': endpoint
                })
            
            for method in old_method_set - new_method_set:
                changes.append({
                    'type': 'removed',
                    'category': 'endpoint',
                    'severity': 'high',
                    'details': f'Method {method.upper()} removed from {endpoint}',
                    'path': endpoint
                })
            
            for method in old_method_set & new_method_set:
                old_details = old_methods.get(method.upper()) or old_methods.get(method.lower()) or {}
                new_details = new_methods.get(method.upper()) or new_methods.get(method.lower()) or {}
                
                old_params = old_details.get('parameters', [])
                new_params = new_details.get('parameters', [])
                
                old_param_names = {p.get('name'): p for p in old_params if isinstance(p, dict)}
                new_param_names = {p.get('name'): p for p in new_params if isinstance(p, dict)}
                
                for param_name in set(new_param_names.keys()) - set(old_param_names.keys()):
                    changes.append({
                        'type': 'added',
                        'category': 'parameter',
                        'severity': 'medium',
                        'details': f'New parameter "{param_name}" added to {endpoint} {method.upper()}',
                        'path': f"{endpoint}/{method.upper()}/{param_name}"
                    })
                
                for param_name in set(old_param_names.keys()) - set(new_param_names.keys()):
                    changes.append({
                        'type': 'removed',
                        'category': 'parameter',
                        'severity': 'high',
                        'details': f'Parameter "{param_name}" removed from {endpoint} {method.upper()}',
                        'path': f"{endpoint}/{method.upper()}/{param_name}"
                    })
                
                for param_name in set(old_param_names.keys()) & set(new_param_names.keys()):
                    old_param = old_param_names[param_name]
                    new_param = new_param_names[param_name]
                    
                    if old_param.get('required') != new_param.get('required'):
                        changes.append({
                            'type': 'modified',
                            'category': 'parameter',
                            'severity': 'high',
                            'details': f'Parameter "{param_name}" required status changed from {old_param.get("required")} to {new_param.get("required")} in {endpoint} {method.upper()}',
                            'path': f"{endpoint}/{method.upper()}/{param_name}"
                        })
                
                old_responses = old_details.get('responses', {})
                new_responses = new_details.get('responses', {})
                
                old_response_codes = set(old_responses.keys())
                new_response_codes = set(new_responses.keys())
                
                for code in new_response_codes - old_response_codes:
                    changes.append({
                        'type': 'added',
                        'category': 'response',
                        'severity': 'low',
                        'details': f'New response code {code} added to {endpoint} {method.upper()}',
                        'path': f"{endpoint}/{method.upper()}/responses/{code}"
                    })
                
                for code in old_response_codes - new_response_codes:
                    changes.append({
                        'type': 'removed',
                        'category': 'response',
                        'severity': 'medium',
                        'details': f'Response code {code} removed from {endpoint} {method.upper()}',
                        'path': f"{endpoint}/{method.upper()}/responses/{code}"
                    })
    
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
