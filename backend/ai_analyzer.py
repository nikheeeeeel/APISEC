"""
AI-powered schema change analyzer using Google Gemini.

Enriches schema diff changes with human-readable descriptions,
impact analysis, and fix suggestions for breaking changes.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Try to load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try to import Gemini SDK
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. AI analysis will be disabled.")


def _get_gemini_model():
    """Initialize and return a Gemini model, or None if unavailable."""
    if not GEMINI_AVAILABLE:
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set. AI analysis will be disabled.")
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        return model
    except Exception as e:
        logger.error(f"Failed to initialize Gemini model: {e}")
        return None


def _build_prompt(changes: List[Dict[str, Any]], old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> str:
    """Build the analysis prompt for Gemini."""
    
    # Trim schemas to relevant parts to save tokens
    old_summary = _summarize_schema(old_schema)
    new_summary = _summarize_schema(new_schema)
    
    changes_text = json.dumps(changes, indent=2, default=str)
    
    prompt = f"""You are an API compatibility expert. Analyze the following API schema changes detected between two OpenAPI schema versions.

For EACH change, provide:
1. **ai_description**: A clear, human-readable explanation of what changed and why it matters. Write this for a developer who needs to understand the impact. Be specific and concise (2-3 sentences max).
2. **ai_impact_analysis**: Who/what is affected — API consumers, client SDKs, frontend apps, mobile apps, CI/CD pipelines, etc. One sentence.
3. **ai_fix_suggestion**: For breaking changes ONLY, provide concrete actionable steps to fix or handle the breaking change. For non-breaking changes, set this to null. Be specific with code-level guidance when possible.

## Old Schema Summary
```json
{json.dumps(old_summary, indent=2)}
```

## New Schema Summary
```json
{json.dumps(new_summary, indent=2)}
```

## Detected Changes
```json
{changes_text}
```

## Response Format
Respond with ONLY a valid JSON array. Each element must correspond to a change (same order as input) with these fields:
```json
[
  {{
    "ai_description": "Human-readable explanation",
    "ai_impact_analysis": "Who is affected",
    "ai_fix_suggestion": "Steps to fix (null if non-breaking)"
  }}
]
```

CRITICAL: Return ONLY the JSON array, no markdown fences, no other text. The array MUST have exactly {len(changes)} elements, one for each input change, in the same order."""
    
    return prompt


def _summarize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a compact summary of a schema for the AI prompt.
    Keeps paths, components, and info but removes large response bodies.
    """
    summary = {}
    
    if "info" in schema:
        summary["info"] = schema["info"]
    
    if "openapi" in schema:
        summary["openapi"] = schema["openapi"]
    elif "swagger" in schema:
        summary["swagger"] = schema["swagger"]
    
    # Summarize paths - keep structure but trim large nested schemas
    if "paths" in schema:
        paths_summary = {}
        for path, methods in schema.get("paths", {}).items():
            if not isinstance(methods, dict):
                continue
            path_summary = {}
            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue
                method_summary = {
                    "parameters": details.get("parameters", []),
                }
                if "requestBody" in details:
                    method_summary["requestBody"] = details["requestBody"]
                # Only include response status codes and top-level schema info
                if "responses" in details:
                    resp_summary = {}
                    for status, resp in details["responses"].items():
                        if isinstance(resp, dict):
                            resp_summary[status] = {
                                "description": resp.get("description", ""),
                            }
                            content = resp.get("content", {})
                            if content:
                                resp_summary[status]["content"] = content
                    method_summary["responses"] = resp_summary
                path_summary[method] = method_summary
            paths_summary[path] = path_summary
        summary["paths"] = paths_summary
    
    # Include component schemas
    if "components" in schema:
        summary["components"] = schema["components"]
    
    # Include security
    if "security" in schema:
        summary["security"] = schema["security"]
    
    return summary


def _parse_ai_response(response_text: str, num_changes: int) -> Optional[List[Dict[str, Any]]]:
    """Parse the AI response JSON, handling common formatting issues."""
    text = response_text.strip()
    
    # Remove markdown code fences if present
    if text.startswith("```"):
        # Remove opening fence
        first_newline = text.index("\n")
        text = text[first_newline + 1:]
        # Remove closing fence
        if text.endswith("```"):
            text = text[:-3].strip()
    
    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        logger.debug(f"Raw response: {text[:500]}")
        return None
    
    if not isinstance(result, list):
        logger.error(f"AI response is not a list, got {type(result).__name__}")
        return None
    
    if len(result) != num_changes:
        logger.warning(
            f"AI returned {len(result)} analyses for {num_changes} changes. "
            "Will pad/trim to match."
        )
        # Pad with empty dicts if too few
        while len(result) < num_changes:
            result.append({
                "ai_description": "AI analysis unavailable for this change.",
                "ai_impact_analysis": "Unable to determine impact.",
                "ai_fix_suggestion": None
            })
        # Trim if too many
        result = result[:num_changes]
    
    return result


async def analyze_changes(
    changes: List[Dict[str, Any]],
    old_schema: Dict[str, Any],
    new_schema: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Analyze schema changes using AI and enrich each change with insights.
    
    Args:
        changes: List of change dicts from compare_schemas()
        old_schema: The old OpenAPI schema
        new_schema: The new OpenAPI schema
        
    Returns:
        The same changes list, enriched with ai_description, 
        ai_impact_analysis, and ai_fix_suggestion fields.
        Falls back gracefully if AI is unavailable.
    """
    if not changes:
        return changes
    
    model = _get_gemini_model()
    if not model:
        logger.info("AI model unavailable, returning changes without AI analysis.")
        return changes
    
    try:
        prompt = _build_prompt(changes, old_schema, new_schema)
        
        # Call Gemini
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            logger.error("Gemini returned empty response")
            return changes
        
        # Parse the response
        ai_analyses = _parse_ai_response(response.text, len(changes))
        
        if not ai_analyses:
            logger.error("Failed to parse AI response, returning original changes")
            return changes
        
        # Merge AI analysis into changes
        enriched_changes = []
        for change, analysis in zip(changes, ai_analyses):
            enriched = {**change}
            enriched["ai_description"] = analysis.get("ai_description", "")
            enriched["ai_impact_analysis"] = analysis.get("ai_impact_analysis", "")
            enriched["ai_fix_suggestion"] = analysis.get("ai_fix_suggestion")
            enriched_changes.append(enriched)
        
        logger.info(f"Successfully enriched {len(enriched_changes)} changes with AI analysis")
        return enriched_changes
        
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return changes


async def analyze_single_change(
    change: Dict[str, Any],
    old_schema: Dict[str, Any],
    new_schema: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a detailed developer-focused explanation for a specific schema change.
    """
    model = _get_gemini_model()
    if not model:
        logger.info("AI model unavailable, returning change without detailed analysis.")
        enriched = {**change}
        enriched["detailed_analysis"] = "AI analysis is currently unavailable. Please check your API key configuration."
        return enriched

    try:
        # Trim schemas to save tokens
        old_summary = _summarize_schema(old_schema)
        new_summary = _summarize_schema(new_schema)
        
        change_text = json.dumps(change, indent=2, default=str)
        
        prompt = f"""You are an expert API developer and architect. Analyze this specific API schema change detected between two OpenAPI versions.
Your goal is to explain this change to a fellow developer who consumes this API.

## Old Schema Summary
```json
{json.dumps(old_summary, indent=2)}
```

## New Schema Summary
```json
{json.dumps(new_summary, indent=2)}
```

## The Specific Change
```json
{change_text}
```

Please provide a detailed, markdown-formatted explanation of this change containing:
1. **What Changed**: A clear explanation of exactly what was modified, added, or removed.
2. **Why it Matters**: The implications of this change for developers consuming the API. If it's a breaking change, explain why it broke.
3. **How to Adapt**: Concrete steps or examples showing how developers should update their clients/code to handle this change. If it's not breaking, mention what new capabilities this unlocks.

Keep your response concise, professional, and directly actionable. Use code blocks for examples if relevant. Do NOT output a JSON response, just output the raw markdown text."""
        
        # Call Gemini
        response = model.generate_content(prompt)
        
        enriched = {**change}
        if response and response.text:
            enriched["detailed_analysis"] = response.text.strip()
        else:
            logger.error("Gemini returned empty response for detailed analysis")
            enriched["detailed_analysis"] = "Failed to generate detailed analysis (empty response)."
            
        return enriched
        
    except Exception as e:
        logger.error(f"Single change AI analysis failed: {e}")
        enriched = {**change}
        enriched["detailed_analysis"] = f"Analysis failed due to an error: {str(e)}"
        return enriched
