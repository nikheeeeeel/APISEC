"""
Semantic schema diff core: normalization, AST extraction, similarity matching,
and change detection for OpenAPI 3.x JSON Schemas (request/response/parameters).
"""

from __future__ import annotations

import copy
import difflib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

SchemaDirection = Literal["request", "response", "parameter"]

# Metadata keys removed before structural comparison (non-semantic)
SCHEMA_NOISE_KEYS = frozenset(
    {
        "description",
        "title",
        "example",
        "examples",
        "default",
        "externalDocs",
    }
)


def sort_keys_recursive(obj: Any) -> Any:
    """Deterministic key ordering for stable hashing and comparison."""
    if isinstance(obj, dict):
        return {k: sort_keys_recursive(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [sort_keys_recursive(x) for x in obj]
    return obj


def strip_schema_noise(node: Any) -> Any:
    """Remove non-semantic fields from schema-like trees."""
    if isinstance(node, dict):
        out: Dict[str, Any] = {}
        for k, v in node.items():
            if k in SCHEMA_NOISE_KEYS:
                continue
            out[k] = strip_schema_noise(v)
        return out
    if isinstance(node, list):
        return [strip_schema_noise(x) for x in node]
    return node


def normalize_openapi_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-copy, strip noise fields, sort keys for consistent ordering."""
    cleaned = strip_schema_noise(copy.deepcopy(doc))
    return sort_keys_recursive(cleaned)


@dataclass(frozen=True)
class SemanticNode:
    """Single comparable field in an API surface."""

    schema_path: str  # e.g. body.email, response.id, param.query.page
    name: str
    type_str: str  # normalized type label
    required: bool
    parent_path: str
    depth: int
    context: str  # "{METHOD} {logical_path} request|response|parameter"
    direction: SchemaDirection  # request body, response body, or operation parameter
    param_in: Optional[str] = None  # OpenAPI `in` for parameters; None for body fields
    constraints_key: str = ""  # enum, format-adjacent constraints for similarity

    def match_key(self) -> Tuple[str, str]:
        return (self.context, self.schema_path)


def _camel_split(s: str) -> List[str]:
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    return [t.lower() for t in re.split(r"[\s_\-]+", s) if t]


def name_similarity(a: str, b: str) -> float:
    """Case-insensitive; snake_case vs camelCase; token overlap + edit distance."""
    if not a or not b:
        return 0.0
    if a.lower() == b.lower():
        return 1.0
    ta, tb = set(_camel_split(a)), set(_camel_split(b))
    jacc = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    seq = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return max(jacc, seq * 0.85)


def _base_type_parts(t: str) -> Tuple[str, str]:
    if ":" in t:
        b, f = t.split(":", 1)
        return b, f
    return t, ""


def type_similarity(t1: str, t2: str) -> float:
    if t1 == t2:
        return 1.0
    b1, _ = _base_type_parts(t1)
    b2, _ = _base_type_parts(t2)
    if b1 == b2:
        return 0.85
    pair = tuple(sorted([b1, b2]))
    if pair == ("integer", "number"):
        return 0.7
    if b1.startswith("array") and b2.startswith("array"):
        inner1 = t1[t1.find("[") + 1 : t1.rfind("]")] if "[" in t1 else ""
        inner2 = t2[t2.find("[") + 1 : t2.rfind("]")] if "[" in t2 else ""
        if inner1 and inner2:
            return 0.5 * type_similarity(inner1, inner2)
        return 0.5
    return 0.0


def parent_similarity(pa: str, pb: str) -> float:
    if pa == pb:
        return 1.0
    if not pa and not pb:
        return 1.0
    if not pa or not pb:
        return 0.3
    return difflib.SequenceMatcher(None, pa, pb).ratio()


def depth_similarity(d1: int, d2: int) -> float:
    return max(0.0, 1.0 - 0.25 * abs(d1 - d2))


def constraint_similarity(c1: str, c2: str) -> float:
    """Strong signal for enum / pattern / length bounds so unlike fields are not paired as renames."""
    if c1 == c2:
        return 1.0
    if not c1 and not c2:
        return 1.0
    if not c1 or not c2:
        return 0.55
    return 0.2


def pair_score(n1: SemanticNode, n2: SemanticNode) -> float:
    if n1.direction != n2.direction:
        return 0.0
    if n1.context != n2.context:
        return 0.0
    if n1.param_in is not None and n2.param_in is not None and n1.param_in != n2.param_in:
        return 0.0
    ns = name_similarity(n1.name, n2.name)
    ts = type_similarity(n1.type_str, n2.type_str)
    cs = constraint_similarity(n1.constraints_key, n2.constraints_key)
    ps = parent_similarity(n1.parent_path, n2.parent_path)
    ds = depth_similarity(n1.depth, n2.depth)
    base = 0.22 * ns + 0.42 * ts + 0.18 * cs + 0.12 * ps + 0.06 * ds
    # Same parent object + compatible type: allow pairing when names differ (renames)
    if (
        n1.parent_path == n2.parent_path
        and n1.parent_path != ""
        and ts >= 0.7
        and ps >= 0.95
        and cs >= 0.85
    ):
        base = max(
            base,
            min(
                1.0,
                0.18 * ns + 0.38 * ts + 0.22 * cs + 0.14 * ps + 0.08 * ds + 0.2,
            ),
        )
    return min(1.0, base)


MATCH_THRESHOLD = 0.6

# Parent path difference → treat as "moved" if ratio below this
MOVED_PARENT_THRESHOLD = 0.55


class SchemaResolverProtocol:
    """Minimal resolver interface (implemented by schema_diff_engine.SchemaResolver)."""

    def deref(self, schema: Any, depth: int = 0) -> Dict[str, Any]: ...

    def extract_object_view(
        self, schema: Any, depth: int = 0
    ) -> Tuple[Dict[str, Dict[str, Any]], Set[str]]: ...


def _normalized_type_label(resolver: SchemaResolverProtocol, s: Dict[str, Any]) -> str:
    raw = resolver.deref(s)
    if not raw:
        return "unknown"
    t = raw.get("type")
    fmt = str(raw.get("format") or "")
    if t == "array":
        items = raw.get("items") or {}
        inner = _normalized_type_label(resolver, items if isinstance(items, dict) else {})
        return f"array[{inner}]"
    if t in ("object", None) and raw.get("properties"):
        return "object"
    if t is None and raw.get("$ref"):
        return "ref"
    base = str(t or "unknown")
    if fmt:
        return f"{base}:{fmt}"
    return base


def _constraint_signature(resolver: SchemaResolverProtocol, s: Dict[str, Any]) -> str:
    raw = resolver.deref(s)
    if not raw:
        return ""
    parts: List[str] = []
    en = raw.get("enum")
    if isinstance(en, list) and en:
        parts.append("enum:" + ",".join(sorted(repr(x) for x in en)))
    if raw.get("pattern") is not None:
        parts.append("pat:" + str(raw.get("pattern")))
    for k in (
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "minItems",
        "maxItems",
        "uniqueItems",
        "multipleOf",
    ):
        if k in raw:
            parts.append(f"{k}:{raw[k]}")
    fmt = raw.get("format")
    if fmt:
        parts.append("fmt:" + str(fmt))
    return "|".join(parts)


def _walk_object_properties(
    resolver: SchemaResolverProtocol,
    schema: Any,
    *,
    depth: int,
    context: str,
    direction: SchemaDirection,
    prefix: str,
    parent_dotted: str,
    nodes: List[SemanticNode],
    max_depth: int = 48,
) -> None:
    if depth > max_depth:
        return
    props, req = resolver.extract_object_view(schema, 0)
    for key in sorted(props.keys()):
        child = props[key]
        deref_child = resolver.deref(child)
        spath = f"{prefix}.{key}" if prefix else key
        parent_p = parent_dotted
        type_label = _normalized_type_label(resolver, deref_child)
        is_req = key in req
        ckey = _constraint_signature(resolver, deref_child)
        nodes.append(
            SemanticNode(
                schema_path=spath,
                name=key,
                type_str=type_label,
                required=is_req,
                parent_path=parent_p,
                depth=depth,
                context=context,
                direction=direction,
                param_in=None,
                constraints_key=ckey,
            )
        )
        ct = deref_child.get("type")
        if ct == "object" or deref_child.get("properties"):
            _walk_object_properties(
                resolver,
                child,
                depth=depth + 1,
                context=context,
                direction=direction,
                prefix=spath,
                parent_dotted=spath,
                nodes=nodes,
                max_depth=max_depth,
            )
        elif ct == "array":
            items = deref_child.get("items") or {}
            ideref = resolver.deref(items if isinstance(items, dict) else {})
            it = ideref.get("type")
            if it == "object" or ideref.get("properties"):
                arr_prefix = f"{spath}[]"
                _walk_object_properties(
                    resolver,
                    items,
                    depth=depth + 1,
                    context=context,
                    direction=direction,
                    prefix=arr_prefix,
                    parent_dotted=arr_prefix,
                    nodes=nodes,
                    max_depth=max_depth,
                )


def collect_parameter_nodes(
    resolver: SchemaResolverProtocol,
    operation: Dict[str, Any],
    *,
    logical_path: str,
    method: str,
) -> List[SemanticNode]:
    nodes: List[SemanticNode] = []
    for raw in operation.get("parameters") or []:
        p = raw
        if isinstance(raw, dict) and "$ref" in raw:
            # Resolve parameter object if full OpenAPI doc available via resolver.root
            continue  # caller should inline parameters; skip unresolved refs
        if not isinstance(p, dict):
            continue
        name = p.get("name")
        pin = p.get("in")
        if not name or not pin:
            continue
        direction: SchemaDirection = "parameter"
        ctx = f"{method.upper()} {logical_path} {direction}"
        sch = p.get("schema") or {}
        type_label = _normalized_type_label(resolver, sch if isinstance(sch, dict) else {})
        req = bool(p.get("required"))
        prefix = f"param.{pin}.{name}"
        ckey = _constraint_signature(resolver, sch if isinstance(sch, dict) else {})
        nodes.append(
            SemanticNode(
                schema_path=prefix,
                name=str(name),
                type_str=type_label,
                required=req,
                parent_path="",
                depth=0,
                context=ctx,
                direction=direction,
                param_in=str(pin),
                constraints_key=ckey,
            )
        )
    return nodes


def collect_body_nodes(
    resolver: SchemaResolverProtocol,
    schema: Dict[str, Any],
    *,
    logical_path: str,
    method: str,
    direction: str,
    label: str,
) -> List[SemanticNode]:
    dir_lit: SchemaDirection = direction if direction in ("request", "response") else "request"
    ctx = f"{method.upper()} {logical_path} {dir_lit}"
    nodes: List[SemanticNode] = []
    if not schema:
        return nodes
    _walk_object_properties(
        resolver,
        schema,
        depth=0,
        context=ctx,
        direction=dir_lit,
        prefix=label,
        parent_dotted=label,
        nodes=nodes,
    )
    return nodes


def greedy_one_to_one_match(
    old_nodes: List[SemanticNode], new_nodes: List[SemanticNode]
) -> Tuple[List[Tuple[int, int, float]], Set[int], Set[int]]:
    """Highest-score bipartite matching with threshold MATCH_THRESHOLD."""
    pairs: List[Tuple[float, int, int]] = []
    for i, a in enumerate(old_nodes):
        for j, b in enumerate(new_nodes):
            sc = pair_score(a, b)
            if sc >= MATCH_THRESHOLD:
                pairs.append((sc, i, j))
    pairs.sort(key=lambda x: -x[0])
    used_o: Set[int] = set()
    used_n: Set[int] = set()
    out: List[Tuple[int, int, float]] = []
    for sc, i, j in pairs:
        if i in used_o or j in used_n:
            continue
        used_o.add(i)
        used_n.add(j)
        out.append((i, j, sc))
    all_o = set(range(len(old_nodes)))
    all_n = set(range(len(new_nodes)))
    return out, all_o - used_o, all_n - used_n


def detect_semantic_changes(
    old_nodes: List[SemanticNode],
    new_nodes: List[SemanticNode],
    matches: List[Tuple[int, int, float]],
    unmatched_old: Set[int],
    unmatched_new: Set[int],
) -> List[Dict[str, Any]]:
    """Produce structured changes (spec STEP 5)."""
    changes: List[Dict[str, Any]] = []

    for i, j, score in matches:
        o, n = old_nodes[i], new_nodes[j]
        ps = parent_similarity(o.parent_path, n.parent_path)
        ns = name_similarity(o.name, n.name)
        ts = type_similarity(o.type_str, n.type_str)

        name_changed = o.name.lower() != n.name.lower()
        parent_shifted = ps < MOVED_PARENT_THRESHOLD
        type_meaningfully_changed = o.type_str != n.type_str and ts < 0.85

        dir_o = o.direction

        if type_meaningfully_changed:
            changes.append(
                {
                    "type": "type_change",
                    "from": o.schema_path,
                    "to": n.schema_path,
                    "details": {
                        "old_type": o.type_str,
                        "new_type": n.type_str,
                        "old_required": o.required,
                        "new_required": n.required,
                        "type_similarity": round(ts, 4),
                    },
                    "confidence": round(min(1.0, score * (0.5 + 0.5 * max(ts, 0.2))), 3),
                    "direction": dir_o,
                }
            )

        if o.required != n.required:
            changes.append(
                {
                    "type": "required_change",
                    "from": o.schema_path,
                    "to": n.schema_path,
                    "details": {
                        "old_type": o.type_str,
                        "new_type": n.type_str,
                        "old_required": o.required,
                        "new_required": n.required,
                    },
                    "confidence": round(score, 3),
                    "direction": dir_o,
                }
            )

        if not type_meaningfully_changed:
            if name_changed:
                changes.append(
                    {
                        "type": "rename",
                        "from": o.schema_path,
                        "to": n.schema_path,
                        "details": {
                            "old_type": o.type_str,
                            "new_type": n.type_str,
                            "old_required": o.required,
                            "new_required": n.required,
                            **(
                                {
                                    "old_parent": o.parent_path,
                                    "new_parent": n.parent_path,
                                }
                                if parent_shifted
                                else {}
                            ),
                        },
                        "confidence": round(min(1.0, 0.5 * score + 0.5 * max(ns, 0.2)), 3),
                        "direction": dir_o,
                    }
                )
            elif parent_shifted:
                changes.append(
                    {
                        "type": "moved",
                        "from": o.schema_path,
                        "to": n.schema_path,
                        "details": {
                            "old_type": o.type_str,
                            "new_type": n.type_str,
                            "old_required": o.required,
                            "new_required": n.required,
                            "old_parent": o.parent_path,
                            "new_parent": n.parent_path,
                        },
                        "confidence": round(min(1.0, 0.5 * score + 0.5 * ps), 3),
                        "direction": dir_o,
                    }
                )

    for j in unmatched_new:
        n = new_nodes[j]
        changes.append(
            {
                "type": "added",
                "from": "",
                "to": n.schema_path,
                "details": {
                    "old_type": "",
                    "new_type": n.type_str,
                    "old_required": False,
                    "new_required": n.required,
                },
                "confidence": 0.85,
                "direction": n.direction,
            }
        )

    for i in unmatched_old:
        o = old_nodes[i]
        changes.append(
            {
                "type": "removed",
                "from": o.schema_path,
                "to": "",
                "details": {
                    "old_type": o.type_str,
                    "new_type": "",
                    "old_required": o.required,
                    "new_required": False,
                },
                "confidence": 0.85,
                "direction": o.direction,
            }
        )

    return dedupe_semantic_changes(changes)


def dedupe_semantic_changes(changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop duplicate events for the same logical edit."""
    seen: Set[Tuple[str, str, str, str]] = set()
    out: List[Dict[str, Any]] = []
    for c in changes:
        key = (
            str(c.get("type")),
            str(c.get("from")),
            str(c.get("to")),
            str(c.get("details")),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


__all__ = [
    "SemanticNode",
    "SchemaDirection",
    "MATCH_THRESHOLD",
    "normalize_openapi_document",
    "sort_keys_recursive",
    "strip_schema_noise",
    "name_similarity",
    "type_similarity",
    "parent_similarity",
    "depth_similarity",
    "pair_score",
    "constraint_similarity",
    "collect_body_nodes",
    "collect_parameter_nodes",
    "greedy_one_to_one_match",
    "detect_semantic_changes",
    "dedupe_semantic_changes",
]
