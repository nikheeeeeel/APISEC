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

# Guidance keyed by compatibility_rule_id (schema_diff_engine). Used to steer ai_description.
RULE_ANALYSIS_HINTS = {
    1010: (
        "New required field on the request body: existing clients that omit it will typically receive "
        "HTTP 400 Bad Request (validation / schema rejection). Mention SDKs, generated clients, and "
        "manual JSON payloads that must include the new property."
    ),
    1011: (
        "New required field on the response: often backward compatible for clients that ignore unknown "
        "properties, but strict parsers, OpenAPI codegen, or contract tests may need updates."
    ),
    1012: (
        "New required operation parameter (query/header/path/cookie): callers that omit it will usually "
        "get 400 Bad Request. Mention client libraries and request builders."
    ),
    1013: (
        "Optional field added: generally safe for existing clients; note any documentation or discovery impact."
    ),
    1020: (
        "Required response field removed: clients and SDKs that depended on this property may break at runtime."
    ),
    1021: (
        "Required request field removed: server is usually more permissive; existing clients keep working."
    ),
    1022: (
        "Required parameter removed: clients sending the old parameter still work; mention deprecation clarity."
    ),
    1023: (
        "Optional field removed: low risk unless clients relied on the property."
    ),
    1030: (
        "Parameter moved between locations (e.g. query to header): same name is not the same contract—"
        "clients must change how they send the value (URL vs headers)."
    ),
    1040: (
        "Incompatible type change: deserialization and validation often fail; treat as high-risk for clients."
    ),
    1041: (
        "Compatible or widened type change: lower risk but may still affect strict validators."
    ),
    1050: (
        "Field became optional: clients gain flexibility; servers should still accept old payloads."
    ),
    1051: (
        "Field became required on the request: payloads missing it will typically fail with 400 Bad Request."
    ),
    1052: (
        "Field became required on the response: clients should tolerate the new shape; strict code may need updates."
    ),
    1053: (
        "Parameter became required: requests without it may return 400 Bad Request."
    ),
    1060: (
        "Field renamed on the request or parameter surface: clients must use the new name; often breaking."
    ),
    1061: (
        "Field renamed on the response: JSON consumers keyed on old names will break."
    ),
    1070: (
        "Field moved to a different object path: clients using fixed JSON paths must update."
    ),
    1071: (
        "Response field moved: clients using fixed paths or codegen may need updates."
    ),
    8001: (
        "Sensitive or credential-like name exposed in a response field: security and compliance risk "
        "(logging, caching, accidental disclosure). Recommend removing or redacting, never returning secrets in APIs."
    ),
    9001: ("Endpoint path version or naming normalization only; usually routing or URL update."),
    9002: ("HTTP method removed: clients calling it will get 404 or 405."),
    9003: ("New HTTP method added; additive for existing callers."),
    9004: ("Entire endpoint removed; existing clients lose the route."),
    9005: ("New endpoint added; additive."),
}

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


def _direction_label(change: Dict[str, Any]) -> str:
    d = (change.get("direction") or change.get("schema_direction") or "").strip()
    if not d:
        return "unspecified surface"
    return {"request": "Request", "response": "Response", "parameter": "Parameter"}.get(
        d.lower(), d.capitalize()
    )


def _change_prompt_block(index: int, change: Dict[str, Any]) -> str:
    """One change with explicit rule and direction for context-aware analysis."""
    rid = change.get("compatibility_rule_id")
    rname = change.get("compatibility_rule_name") or "UnknownRule"
    category = change.get("rule_category") or "Unknown"
    direction = _direction_label(change)
    path = (
        change.get("path")
        or change.get("original_path")
        or change.get("new_path")
        or ""
    )
    method = change.get("method") or ""
    st = change.get("semantic_type") or change.get("type") or ""
    breaking = change.get("breaking_change") or (
        "breaking" if change.get("breaking") is True else (
            "non_breaking" if change.get("breaking") is False else "unknown"
        )
    )
    sec = change.get("security_issue")
    hint = ""
    if isinstance(rid, int) and rid in RULE_ANALYSIS_HINTS:
        hint = RULE_ANALYSIS_HINTS[rid]

    lines = [
        f"Change #{index + 1}:",
        f"  - API path / logical key: {path}",
        f"  - HTTP method (if any): {method or '(n/a)'}",
        f"  - Direction (Request / Response / Parameter): {direction}",
        f"  - Compatibility rule: Rule {rid} ({rname})" if rid is not None else f"  - Compatibility rule: ({rname})",
        f"  - Rule category: {category}",
        f"  - Contract breaking (rules engine): {breaking}",
    ]
    if sec:
        lines.append("  - Security flag: CRITICAL — sensitive or credential-like exposure in response")
    if hint:
        lines.append(f"  - Rule-specific guidance (use this in ai_description): {hint}")
    lines.append(f"  - Raw change record: {json.dumps(change, default=str)}")
    return "\n".join(lines)


def _build_prompt(changes: List[Dict[str, Any]], old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> str:
    """Build the analysis prompt for Gemini."""

    old_summary = _summarize_schema(old_schema)
    new_summary = _summarize_schema(new_schema)

    change_blocks = "\n\n".join(
        _change_prompt_block(i, c) for i, c in enumerate(changes)
    )

    prompt = f"""You are an API compatibility and security expert. Analyze the following API schema changes detected between two OpenAPI schema versions.

For EACH change (in order), the prompt includes:
- **Direction**: whether the change affects the Request body, Response body, or Parameters (operation parameters).
- **Rule ID and name**: the compatibility rule that fired (from the rules engine).
- **Rule category**: e.g. Security, Contract violation, Additive / compatible.
- **Rule-specific guidance**: when present, you MUST incorporate it into **ai_description** so the text reflects the real-world effect (e.g. for Rule 1010, explicitly mention that existing clients may get **HTTP 400 Bad Request** if they omit the new required request field).

For EACH change, provide:
1. **ai_description**: 2–3 sentences. Ground the explanation in the **rule name and rule-specific guidance** above—not generic diff text. If the rule implies validation failures (e.g. 400), say so clearly.
2. **ai_impact_analysis**: One sentence on who is affected (SDKs, mobile/web clients, CI, etc.).
3. **ai_fix_suggestion**: Set to **null** only for purely non-breaking, non-security additive changes. For **contract-breaking** changes OR **security_issue** / Rule 8001 / Critical security, provide concrete remediation steps (never null for those).

## Old Schema Summary
```json
{json.dumps(old_summary, indent=2)}
```

## New Schema Summary
```json
{json.dumps(new_summary, indent=2)}
```

## Detected Changes (context-aware; one block per change)
{change_blocks}

## Response Format
Respond with ONLY a valid JSON array. Each element must correspond to a change (same order as input) with these fields:
```json
[
  {{
    "ai_description": "Human-readable explanation",
    "ai_impact_analysis": "Who is affected",
    "ai_fix_suggestion": "Steps to fix (null only if safe additive non-security)"
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
        rid = change.get("compatibility_rule_id")
        rname = change.get("compatibility_rule_name")
        category = change.get("rule_category")
        direction = _direction_label(change)
        path = (
            change.get("path")
            or change.get("original_path")
            or change.get("new_path")
            or ""
        )
        method = change.get("method") or ""
        hint = ""
        if isinstance(rid, int) and rid in RULE_ANALYSIS_HINTS:
            hint = RULE_ANALYSIS_HINTS[rid]
        security_note = ""
        if change.get("security_issue") or rid == 8001:
            security_note = (
                "\nThis change is flagged as a **CRITICAL security issue** (sensitive-like data in an API response). "
                "Prioritize data protection, logging, and removal/redaction in your explanation.\n"
            )

        prompt = f"""You are an expert API developer and architect. Analyze this specific API schema change detected between two OpenAPI versions.
Your goal is to explain this change to a fellow developer who consumes this API.

## Context (rules engine)
- **Path**: {path}
- **Method**: {method or '(n/a)'}
- **Direction**: {direction} (Request vs Response vs Parameter)
- **Rule**: Rule {rid} — {rname}
- **Rule category**: {category or 'Unknown'}
{security_note}{f"- **Rule-specific guidance** (use in your explanation): {hint}" if hint else ""}

## Old Schema Summary
```json
{json.dumps(old_summary, indent=2)}
```

## New Schema Summary
```json
{json.dumps(new_summary, indent=2)}
```

## The Specific Change (raw)
```json
{change_text}
```

Please provide a detailed, markdown-formatted explanation of this change containing:
1. **What Changed**: What was modified, added, or removed—tie it to the **rule** above.
2. **Why it Matters**: Implications for SDKs and clients. If the rule implies HTTP **400** validation failures or security exposure, state that explicitly.
3. **How to Adapt**: Concrete steps to update clients or fix security issues.

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


def _truncate_json_for_prompt(data: Any, max_chars: int = 4500) -> str:
    try:
        s = json.dumps(data, indent=2, default=str)
    except (TypeError, ValueError):
        s = str(data)
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 40] + "\n... (truncated for prompt size)"


async def analyze_runtime_endpoint_failure(
    base_url: str,
    endpoint_test: Dict[str, Any],
) -> str:
    """
    Explain why a single runtime validation probe failed (status vs spec, schema drift, errors).
    """
    model = _get_gemini_model()
    if not model:
        return (
            "AI analysis is currently unavailable. Set GEMINI_API_KEY in the server environment "
            "to enable explanations."
        )

    spec_status = endpoint_test.get("expected_status")
    actual_status = endpoint_test.get("actual_status")
    method = endpoint_test.get("method") or ""
    path = endpoint_test.get("path") or ""
    url = endpoint_test.get("url") or ""
    err = endpoint_test.get("error")
    status_mismatch = endpoint_test.get("status_mismatch")
    schema_mismatch = endpoint_test.get("schema_mismatch")
    response_time_ms = endpoint_test.get("response_time_ms")

    expected_schema = endpoint_test.get("expected_response_schema")
    actual_body = endpoint_test.get("actual_response")

    probe_summary = {
        "method": method,
        "path": path,
        "request_url": url,
        "expected_status_from_spec": spec_status,
        "actual_http_status": actual_status,
        "status_mismatch": status_mismatch,
        "schema_mismatch": schema_mismatch,
        "transport_or_client_error": err,
        "response_time_ms": response_time_ms,
        "expected_response_schema_excerpt": _truncate_json_for_prompt(expected_schema, 2500),
        "actual_response_body_excerpt": _truncate_json_for_prompt(actual_body, 2500),
    }

    prompt = f"""You are an API reliability engineer. A runtime contract check compared live HTTP behavior to an OpenAPI-style spec for one operation.

**API base URL (context only):** {base_url}

**Probe result (JSON):**
```json
{json.dumps(probe_summary, indent=2, default=str)}
```

Explain in markdown:
1. **What failed** — status code vs documented default, connection/timeout error, or JSON shape vs declared response schema.
2. **Likely causes** — spec outdated, wrong environment, auth, validation on server, nullable/required drift, etc. Be specific to the fields above.
3. **What to do next** — concrete checks (fix spec, fix server, adjust test base URL, auth headers).

Do not invent HTTP statuses or response bodies not indicated above. If the excerpt is truncated, say that full bodies may reveal more. Keep it concise and actionable."""

    try:
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
        logger.error("Gemini returned empty response for runtime failure analysis")
        return "Failed to generate analysis (empty response from AI)."
    except Exception as e:
        logger.error(f"Runtime failure AI analysis failed: {e}")
        return f"Analysis failed due to an error: {str(e)}"
