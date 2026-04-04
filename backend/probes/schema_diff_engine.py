"""
Semantic OpenAPI 3.x diff engine.

Compares API contracts by normalized endpoint identity, resolved JSON Schemas,
and backward-compatibility-oriented field semantics — not raw JSON structure.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

from .semantic_schema_core import (
    collect_body_nodes,
    collect_parameter_nodes,
    dedupe_semantic_changes,
    detect_semantic_changes,
    greedy_one_to_one_match,
    normalize_openapi_document,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HTTP_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
)

NOISE_PATH_PATTERNS = [
    re.compile(r"^/admin(?:/|$)", re.IGNORECASE),
    re.compile(r"^/health(?:/|$)", re.IGNORECASE),
    re.compile(r"^/metrics(?:/|$)", re.IGNORECASE),
    # Root-only paths (often accidental / duplicate keys); avoid pairing with real routes
    re.compile(r"^/$"),
]

# Substrings matched against field names for internal/public leakage (lowercased)
SENSITIVE_KEYWORDS = ("password", "secret", "token", "api_key", "db_url")

METADATA_KEYS = frozenset(
    {
        "description",
        "summary",
        "title",
        "example",
        "examples",
        "tags",
        "externalDocs",
        "deprecated",
    }
)


# ---------------------------------------------------------------------------
# Directional compatibility rules (request vs response vs parameter)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompatibilityRule:
    """Catalog entry: stable ID, human name, default severity, breaking flag."""

    rule_id: int
    name: str
    severity: str
    breaking: bool


def _resolve_compatibility_rule(change: Dict[str, Any]) -> CompatibilityRule:
    """Map a raw semantic event (with ``direction``) to a catalog rule."""
    t = str(change.get("type", ""))
    direction = str(change.get("direction", "request"))
    if direction not in ("request", "response", "parameter"):
        direction = "request"
    det = change.get("details") or {}

    if t == "parameter_in_changed":
        return CompatibilityRule(1030, "ParameterLocationChanged", "HIGH", True)

    if t == "added":
        req = bool(det.get("new_required"))
        if not req:
            return CompatibilityRule(1013, "AddedOptionalField", "LOW", False)
        if direction == "request":
            return CompatibilityRule(1010, "AddedRequiredRequestField", "HIGH", True)
        if direction == "response":
            return CompatibilityRule(1011, "AddedRequiredResponseField", "LOW", False)
        return CompatibilityRule(1012, "AddedRequiredParameter", "HIGH", True)

    if t == "removed":
        req = bool(det.get("old_required"))
        if not req:
            return CompatibilityRule(1023, "RemovedOptionalField", "LOW", False)
        if direction == "request":
            return CompatibilityRule(1021, "RemovedRequiredRequestField", "LOW", False)
        if direction == "response":
            return CompatibilityRule(1020, "RemovedRequiredResponseField", "HIGH", True)
        return CompatibilityRule(1022, "RemovedRequiredParameter", "HIGH", True)

    if t == "required_change":
        became_required = bool(det.get("new_required")) and not bool(
            det.get("old_required")
        )
        became_optional = bool(det.get("old_required")) and not bool(
            det.get("new_required")
        )
        if became_optional:
            return CompatibilityRule(1050, "RequiredToOptional", "LOW", False)
        if became_required:
            if direction == "request":
                return CompatibilityRule(1051, "OptionalToRequiredRequest", "HIGH", True)
            if direction == "response":
                return CompatibilityRule(1052, "OptionalToRequiredResponse", "LOW", False)
            return CompatibilityRule(1053, "OptionalToRequiredParameter", "HIGH", True)
        return CompatibilityRule(1054, "RequiredStatusChanged", "MEDIUM", True)

    if t == "type_change":
        ts_sim = float(det.get("type_similarity", 0.0))
        breaking = ts_sim < 0.7
        if breaking:
            return CompatibilityRule(1040, "TypeChangedIncompatible", "HIGH", True)
        return CompatibilityRule(1041, "TypeChangedCompatible", "MEDIUM", False)

    if t == "rename":
        if direction == "response":
            return CompatibilityRule(1061, "FieldRenamedResponse", "MEDIUM", True)
        return CompatibilityRule(1060, "FieldRenamed", "HIGH", True)

    if t == "moved":
        if direction == "response":
            return CompatibilityRule(1071, "FieldMovedResponse", "MEDIUM", True)
        return CompatibilityRule(1070, "FieldMoved", "HIGH", True)

    if t == "version_bump":
        return CompatibilityRule(9001, "EndpointVersionBump", "LOW", False)
    if t == "method_removed":
        return CompatibilityRule(9002, "MethodRemoved", "HIGH", True)
    if t == "method_added":
        return CompatibilityRule(9003, "MethodAdded", "LOW", False)
    if t == "endpoint_removed":
        return CompatibilityRule(9004, "EndpointRemoved", "HIGH", True)
    if t == "endpoint_added":
        return CompatibilityRule(9005, "EndpointAdded", "LOW", False)

    return CompatibilityRule(9999, "UnknownChange", "MEDIUM", True)


def apply_compatibility_rules(change: Dict[str, Any]) -> Dict[str, Any]:
    """Attach rule id, name, severity, and breaking flag to one semantic change."""
    out = dict(change)
    rule = _resolve_compatibility_rule(out)
    out["compatibility_rule_id"] = rule.rule_id
    out["compatibility_rule_name"] = rule.name
    out["severity"] = rule.severity
    out["breaking"] = rule.breaking
    return out


def _schema_path_matches_sensitive_keyword(schema_path: str) -> bool:
    """True if any path segment (e.g. property name) matches SENSITIVE_KEYWORDS."""
    if not schema_path:
        return False
    normalized = schema_path.replace("[]", ".")
    parts = re.split(r"[.\[\]]+", normalized)
    for p in parts:
        if not p:
            continue
        low = p.lower()
        if any(kw in low for kw in SENSITIVE_KEYWORDS):
            return True
    return False


def _apply_sensitive_response_escalation(change: Dict[str, Any]) -> Dict[str, Any]:
    """
    Response fields that expose sensitive-like names are always CRITICAL security issues,
    independent of contract-breaking classification.
    """
    out = dict(change)
    if out.get("type") != "added" or out.get("direction") != "response":
        return out
    path = str(out.get("to", ""))
    if not _schema_path_matches_sensitive_keyword(path):
        return out
    out["security_issue"] = True
    out["compatibility_rule_id"] = 8001
    out["compatibility_rule_name"] = "SensitiveFieldExposedInResponse"
    out["severity"] = "CRITICAL"
    out["breaking"] = False
    return out


def rule_category_for_change(change: Dict[str, Any]) -> str:
    """High-level bucket for UI and prompts (Security vs contract vs additive)."""
    if change.get("security_issue") or change.get("compatibility_rule_id") == 8001:
        return "Security"
    if change.get("breaking") is True:
        return "Contract violation"
    rid = change.get("compatibility_rule_id")
    additive_ids = (
        9001,
        9003,
        9005,
        1011,
        1013,
        1050,
        1052,
        1021,
        1023,
        1041,
    )
    if rid in additive_ids:
        return "Additive / compatible"
    return "Contract change"


def _enrich_semantic_change(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Apply compatibility rules, security escalation, and rule category."""
    s = apply_compatibility_rules(dict(raw))
    s = _apply_sensitive_response_escalation(s)
    s["rule_category"] = rule_category_for_change(s)
    return s


def _legacy_impact_from_rule(c: Dict[str, Any], fallback: str) -> str:
    s = c.get("severity")
    if isinstance(s, str) and s in ("HIGH", "MEDIUM", "LOW", "CRITICAL"):
        return s
    return fallback


# ---------------------------------------------------------------------------
# PathNormalizer
# ---------------------------------------------------------------------------


class PathNormalizer:
    """
    Maps concrete paths to a stable logical key:
    - Version segments /v1/, /v2/ → /vX/
    - Path parameter names → {param} so /users/{id} matches /users/{user_id}
    """

    _VERSION_SEG = re.compile(r"/v\d+(?=/|$)")
    _PARAM = re.compile(r"\{[^}]+\}")

    @classmethod
    def normalize(cls, path: str) -> str:
        if not path or not str(path).strip():
            # Distinct token so "" does not collide with concrete "/"
            return "__root__"
        p = path.strip()
        if not p.startswith("/"):
            p = "/" + p
        p = cls._VERSION_SEG.sub("/vX", p)
        p = cls._PARAM.sub("{param}", p)
        return p if p else "__root__"


# ---------------------------------------------------------------------------
# SchemaResolver
# ---------------------------------------------------------------------------


class SchemaResolver:
    """
    Resolves $ref (OpenAPI root document), merges allOf, and unions oneOf/anyOf
    object branches for property-level comparison.
    """

    def __init__(self, root: Dict[str, Any], max_ref_depth: int = 48):
        self.root = root
        self._max_ref_depth = max_ref_depth

    def resolve_ref(self, ref: str) -> Any:
        if not isinstance(ref, str) or not ref.startswith("#/"):
            return {}
        node: Any = self.root
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return {}
        return node

    def deref(self, schema: Any, depth: int = 0) -> Dict[str, Any]:
        cur: Any = schema
        d = depth
        while isinstance(cur, dict) and "$ref" in cur and d < self._max_ref_depth:
            nxt = self.resolve_ref(cur["$ref"])
            if not nxt:
                break
            cur = nxt
            d += 1
        return cur if isinstance(cur, dict) else {}

    def extract_object_view(
        self, schema: Any, depth: int = 0
    ) -> Tuple[Dict[str, Dict[str, Any]], Set[str]]:
        """
        Returns (properties_map, required_names) for JSON Schema `object` semantics,
        including composition keywords.
        """
        if depth > 64 or not isinstance(schema, dict):
            return {}, set()

        s = self.deref(schema, depth)
        if not s:
            return {}, set()

        if s.get("type") == "array":
            return self.extract_object_view(s.get("items") or {}, depth + 1)

        merged_props: Dict[str, Dict[str, Any]] = {}
        merged_required: Set[str] = set()

        for sub in s.get("allOf", []) or []:
            sp, sr = self.extract_object_view(sub, depth + 1)
            merged_props.update(sp)
            merged_required |= sr

        for branch_key in ("oneOf", "anyOf"):
            branches = s.get(branch_key) or []
            if not branches:
                continue
            branch_views = [
                self.extract_object_view(sub, depth + 1) for sub in branches
            ]
            for sp, _ in branch_views:
                merged_props.update(sp)
            req_sets = [sr for _, sr in branch_views]
            if len(req_sets) == 1:
                merged_required |= req_sets[0]
            elif len(req_sets) > 1:
                merged_required |= set.intersection(*req_sets)

        props = s.get("properties") or {}
        if isinstance(props, dict):
            for k, v in props.items():
                merged_props[k] = self.deref(v if isinstance(v, dict) else {}, depth + 1)

        req = s.get("required") or []
        if isinstance(req, list):
            merged_required |= {x for x in req if isinstance(x, str)}

        return merged_props, merged_required


# ---------------------------------------------------------------------------
# ChangeClassifier
# ---------------------------------------------------------------------------


class ChangeClassifier:
    """Maps change kinds to impact levels (semantic, not structural)."""

    @staticmethod
    def endpoint_removed() -> str:
        return "HIGH"

    @staticmethod
    def endpoint_added() -> str:
        return "LOW"

    @staticmethod
    def version_bump() -> str:
        return "LOW"

    @staticmethod
    def method_removed() -> str:
        return "HIGH"

    @staticmethod
    def method_added() -> str:
        return "LOW"

    @staticmethod
    def field_removed(was_required: bool) -> str:
        return "HIGH" if was_required else "MEDIUM"

    @staticmethod
    def field_added_required() -> str:
        return "MEDIUM"

    @staticmethod
    def optional_field_added() -> str:
        return "LOW"

    @staticmethod
    def field_renamed() -> str:
        return "HIGH"

    @staticmethod
    def field_type_changed() -> str:
        return "HIGH"

    @staticmethod
    def required_status_changed() -> str:
        return "HIGH"


# ---------------------------------------------------------------------------
# EndpointMatcher
# ---------------------------------------------------------------------------


class EndpointMatcher:
    """
    Pairs concrete paths that share the same normalized identity.
    Leftovers are unmatched removals / additions.
    """

    @staticmethod
    def build_pairs(
        paths_old: Set[str], paths_new: Set[str]
    ) -> Tuple[List[Tuple[str, str]], Set[str], Set[str]]:
        norm_old: Dict[str, List[str]] = {}
        for p in paths_old:
            norm_old.setdefault(PathNormalizer.normalize(p), []).append(p)
        norm_new: Dict[str, List[str]] = {}
        for p in paths_new:
            norm_new.setdefault(PathNormalizer.normalize(p), []).append(p)

        used_old: Set[str] = set()
        used_new: Set[str] = set()
        pairs: List[Tuple[str, str]] = []

        for norm in sorted(set(norm_old) | set(norm_new)):
            lo = sorted(norm_old.get(norm, []))
            ln = sorted(norm_new.get(norm, []))
            for a, b in zip(lo, ln):
                pairs.append((a, b))
                used_old.add(a)
                used_new.add(b)

        only_old = paths_old - used_old
        only_new = paths_new - used_new
        return pairs, only_old, only_new


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_noise_path(path: str) -> bool:
    if path is None:
        return True
    p = str(path).strip()
    if p == "" or p == "/":
        return True
    n = PathNormalizer.normalize(path)
    return any(pat.match(n) for pat in NOISE_PATH_PATTERNS)


def _resolve_parameters(operation: Dict[str, Any], root: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Inline parameter $ref objects for semantic extraction."""
    sr = SchemaResolver(root)
    out: List[Dict[str, Any]] = []
    for p in operation.get("parameters") or []:
        if isinstance(p, dict) and "$ref" in p:
            q = sr.resolve_ref(p["$ref"])
            if isinstance(q, dict):
                out.append(q)
        elif isinstance(p, dict):
            out.append(p)
    return out


def _leaf_name(schema_path: str) -> str:
    if not schema_path:
        return ""
    parts = schema_path.replace("[]", ".[]").split(".")
    return parts[-1] if parts else schema_path


def _semantic_to_legacy(
    semantic: List[Dict[str, Any]],
    *,
    logical_path: str,
    direction: str,
    method: str,
    original_path: str,
    new_path: str,
    classifier: ChangeClassifier,
) -> List[Dict[str, Any]]:
    """Map semantic diff records to legacy FIELD_* change dicts."""
    out: List[Dict[str, Any]] = []
    for c in semantic:
        t = c.get("type")
        details = c.get("details") or {}
        conf = c.get("confidence")
        breaking = c.get("breaking")
        rule_id = c.get("compatibility_rule_id")
        rule_name = c.get("compatibility_rule_name")
        base = {
            "path": logical_path,
            "original_path": original_path,
            "new_path": new_path,
            "direction": direction,
            "method": method.upper(),
        }
        if conf is not None:
            base["confidence"] = conf
        if breaking is not None:
            base["breaking"] = breaking
        if rule_id is not None:
            base["compatibility_rule_id"] = rule_id
        if rule_name is not None:
            base["compatibility_rule_name"] = rule_name
        if c.get("severity") is not None:
            base["severity"] = c.get("severity")
        if c.get("rule_category"):
            base["rule_category"] = c["rule_category"]
        if c.get("security_issue"):
            base["security_issue"] = True

        if t == "rename":
            out.append(
                {
                    **base,
                    "type": "FIELD_RENAMED",
                    "from": _leaf_name(str(c.get("from", ""))),
                    "to": _leaf_name(str(c.get("to", ""))),
                    "field": _leaf_name(str(c.get("to", ""))),
                    "impact": _legacy_impact_from_rule(c, classifier.field_renamed()),
                }
            )
        elif t == "type_change":
            out.append(
                {
                    **base,
                    "type": "FIELD_TYPE_CHANGED",
                    "field": _leaf_name(str(c.get("from", "") or c.get("to", ""))),
                    "impact": _legacy_impact_from_rule(c, classifier.field_type_changed()),
                    "old_type": details.get("old_type"),
                    "new_type": details.get("new_type"),
                }
            )
        elif t == "required_change":
            out.append(
                {
                    **base,
                    "type": "REQUIRED_STATUS_CHANGED",
                    "field": _leaf_name(str(c.get("from", "") or c.get("to", ""))),
                    "required_before": details.get("old_required"),
                    "required_after": details.get("new_required"),
                    "impact": _legacy_impact_from_rule(c, classifier.required_status_changed()),
                }
            )
        elif t == "added" and c.get("security_issue"):
            req = bool(details.get("new_required"))
            out.append(
                {
                    **base,
                    "type": "SENSITIVE_RESPONSE_FIELD_ADDED",
                    "field": _leaf_name(str(c.get("to", ""))),
                    "schema_path": c.get("to"),
                    "optional": not req,
                    "security_issue": True,
                    "impact": _legacy_impact_from_rule(c, "CRITICAL"),
                }
            )
        elif t == "added":
            req = bool(details.get("new_required"))
            out.append(
                {
                    **base,
                    "type": "FIELD_ADDED" if req else "OPTIONAL_FIELD_ADDED",
                    "field": _leaf_name(str(c.get("to", ""))),
                    "optional": not req,
                    "impact": _legacy_impact_from_rule(
                        c,
                        classifier.field_added_required()
                        if req
                        else classifier.optional_field_added(),
                    ),
                }
            )
        elif t == "removed":
            was_req = bool(details.get("old_required"))
            out.append(
                {
                    **base,
                    "type": "FIELD_REMOVED",
                    "field": _leaf_name(str(c.get("from", ""))),
                    "impact": _legacy_impact_from_rule(
                        c, classifier.field_removed(was_req)
                    ),
                }
            )
        elif t == "moved":
            out.append(
                {
                    **base,
                    "type": "FIELD_MOVED",
                    "field": _leaf_name(str(c.get("from", ""))),
                    "from_path": c.get("from"),
                    "to_path": c.get("to"),
                    "impact": _legacy_impact_from_rule(c, classifier.field_renamed()),
                }
            )
        elif t == "parameter_in_changed":
            out.append(
                {
                    **base,
                    "type": "PARAMETER_LOCATION_CHANGED",
                    "field": _leaf_name(str(details.get("name", ""))),
                    "from_path": c.get("from"),
                    "to_path": c.get("to"),
                    "old_in": details.get("old_in"),
                    "new_in": details.get("new_in"),
                    "impact": _legacy_impact_from_rule(c, "HIGH"),
                }
            )
    return out


def _finalize_semantic_events(
    raw: List[Dict[str, Any]], context_line: str
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in raw:
        s2 = _enrich_semantic_change(dict(s))
        s2["context"] = context_line
        out.append(s2)
    return out


def _extract_json_schemas(operation: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    req: Dict[str, Any] = {}
    for ct, block in (operation.get("requestBody") or {}).get("content", {}).items():
        if "json" in str(ct).lower():
            req = (block or {}).get("schema") or {}
            break

    res: Dict[str, Any] = {}
    for code, resp in (operation.get("responses") or {}).items():
        if str(code) not in {"200", "201", "202", "default"}:
            continue
        for ct, block in (resp or {}).get("content", {}).items():
            if "json" in str(ct).lower():
                res = (block or {}).get("schema") or {}
                break
        if res:
            break

    return req, res


def _dedupe_changes(changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Set[Tuple[Any, ...]] = set()
    out: List[Dict[str, Any]] = []
    for c in changes:
        key = (
            c.get("type"),
            c.get("original_path"),
            c.get("new_path"),
            c.get("path"),
            c.get("method"),
            c.get("direction"),
            c.get("field"),
            c.get("from"),
            c.get("to"),
            c.get("required_before"),
            c.get("required_after"),
            c.get("optional"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


# ---------------------------------------------------------------------------
# DiffEngine (DifferentialEngine)
# ---------------------------------------------------------------------------


class DiffEngine:
    """Orchestrates semantic OpenAPI diffing."""

    def __init__(self):
        self._classifier = ChangeClassifier()

    def _compare_request_bodies(
        self,
        ro: SchemaResolver,
        rn: SchemaResolver,
        *,
        logical_path: str,
        method: str,
        original_path: str,
        new_path: str,
        req_o: Dict[str, Any],
        req_n: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not req_o and not req_n:
            return [], []
        nodes_o = collect_body_nodes(
            ro,
            req_o or {},
            logical_path=logical_path,
            method=method,
            direction="request",
            label="body",
        )
        nodes_n = collect_body_nodes(
            rn,
            req_n or {},
            logical_path=logical_path,
            method=method,
            direction="request",
            label="body",
        )
        matches, uo, un = greedy_one_to_one_match(nodes_o, nodes_n)
        sem = dedupe_semantic_changes(
            detect_semantic_changes(nodes_o, nodes_n, matches, uo, un)
        )
        ctx = f"{method.upper()} {logical_path} request-body"
        sem_f = _finalize_semantic_events(sem, ctx)
        legacy = _semantic_to_legacy(
            sem_f,
            logical_path=logical_path,
            direction="request",
            method=method,
            original_path=original_path,
            new_path=new_path,
            classifier=self._classifier,
        )
        return legacy, sem_f

    def _compare_parameters(
        self,
        ro: SchemaResolver,
        rn: SchemaResolver,
        *,
        logical_path: str,
        method: str,
        original_path: str,
        new_path: str,
        op_params_o: Dict[str, Any],
        op_params_n: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        params_o = op_params_o.get("parameters") or []
        params_n = op_params_n.get("parameters") or []
        if not params_o and not params_n:
            return [], []
        nodes_o = collect_parameter_nodes(
            ro, op_params_o, logical_path=logical_path, method=method
        )
        nodes_n = collect_parameter_nodes(
            rn, op_params_n, logical_path=logical_path, method=method
        )

        skip_o: Set[int] = set()
        skip_n: Set[int] = set()
        extra_raw: List[Dict[str, Any]] = []
        by_name_o: Dict[str, List[int]] = defaultdict(list)
        by_name_n: Dict[str, List[int]] = defaultdict(list)
        for i, nd in enumerate(nodes_o):
            by_name_o[nd.name.lower()].append(i)
        for j, nd in enumerate(nodes_n):
            by_name_n[nd.name.lower()].append(j)
        for name in set(by_name_o.keys()) & set(by_name_n.keys()):
            ios = by_name_o[name]
            jns = by_name_n[name]
            if len(ios) == 1 and len(jns) == 1:
                io, jn = ios[0], jns[0]
                o, nn = nodes_o[io], nodes_n[jn]
                if o.param_in != nn.param_in:
                    skip_o.add(io)
                    skip_n.add(jn)
                    extra_raw.append(
                        {
                            "type": "parameter_in_changed",
                            "from": o.schema_path,
                            "to": nn.schema_path,
                            "details": {
                                "name": o.name,
                                "old_in": o.param_in,
                                "new_in": nn.param_in,
                                "old_type": o.type_str,
                                "new_type": nn.type_str,
                                "old_required": o.required,
                                "new_required": nn.required,
                            },
                            "confidence": 1.0,
                            "direction": "parameter",
                        }
                    )

        sub_o = [n for i, n in enumerate(nodes_o) if i not in skip_o]
        sub_n = [n for j, n in enumerate(nodes_n) if j not in skip_n]
        matches, uo, un = greedy_one_to_one_match(sub_o, sub_n)
        sem = dedupe_semantic_changes(
            detect_semantic_changes(sub_o, sub_n, matches, uo, un)
        )
        merged = dedupe_semantic_changes(extra_raw + sem)
        ctx = f"{method.upper()} {logical_path} parameters"
        sem_f = _finalize_semantic_events(merged, ctx)
        legacy = _semantic_to_legacy(
            sem_f,
            logical_path=logical_path,
            direction="parameter",
            method=method,
            original_path=original_path,
            new_path=new_path,
            classifier=self._classifier,
        )
        return legacy, sem_f

    def _compare_responses(
        self,
        ro: SchemaResolver,
        rn: SchemaResolver,
        *,
        logical_path: str,
        method: str,
        original_path: str,
        new_path: str,
        res_o: Dict[str, Any],
        res_n: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not res_o and not res_n:
            return [], []
        nodes_ro = collect_body_nodes(
            ro,
            res_o or {},
            logical_path=logical_path,
            method=method,
            direction="response",
            label="response",
        )
        nodes_rn = collect_body_nodes(
            rn,
            res_n or {},
            logical_path=logical_path,
            method=method,
            direction="response",
            label="response",
        )
        matches_r, uo_r, un_r = greedy_one_to_one_match(nodes_ro, nodes_rn)
        sem_r = dedupe_semantic_changes(
            detect_semantic_changes(nodes_ro, nodes_rn, matches_r, uo_r, un_r)
        )
        ctx_r = f"{method.upper()} {logical_path} response"
        sem_f = _finalize_semantic_events(sem_r, ctx_r)
        legacy = _semantic_to_legacy(
            sem_f,
            logical_path=logical_path,
            direction="response",
            method=method,
            original_path=original_path,
            new_path=new_path,
            classifier=self._classifier,
        )
        return legacy, sem_f

    def _semantic_diff_operation_surface(
        self,
        ro: SchemaResolver,
        rn: SchemaResolver,
        *,
        logical_path: str,
        method: str,
        original_path: str,
        new_path: str,
        op_old: Dict[str, Any],
        op_new: Dict[str, Any],
        old_doc: Dict[str, Any],
        new_doc: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Request body, parameters, and response bodies compared separately."""
        legacy: List[Dict[str, Any]] = []
        semantic_out: List[Dict[str, Any]] = []

        req_o, res_o = _extract_json_schemas(op_old)
        req_n, res_n = _extract_json_schemas(op_new)
        op_params_o = {"parameters": _resolve_parameters(op_old, old_doc)}
        op_params_n = {"parameters": _resolve_parameters(op_new, new_doc)}

        l1, s1 = self._compare_request_bodies(
            ro,
            rn,
            logical_path=logical_path,
            method=method,
            original_path=original_path,
            new_path=new_path,
            req_o=req_o or {},
            req_n=req_n or {},
        )
        l2, s2 = self._compare_parameters(
            ro,
            rn,
            logical_path=logical_path,
            method=method,
            original_path=original_path,
            new_path=new_path,
            op_params_o=op_params_o,
            op_params_n=op_params_n,
        )
        l3, s3 = self._compare_responses(
            ro,
            rn,
            logical_path=logical_path,
            method=method,
            original_path=original_path,
            new_path=new_path,
            res_o=res_o or {},
            res_n=res_n or {},
        )
        legacy.extend(l1)
        legacy.extend(l2)
        legacy.extend(l3)
        semantic_out.extend(s1)
        semantic_out.extend(s2)
        semantic_out.extend(s3)
        return legacy, semantic_out

    def _diff_paired_paths(
        self,
        pairs: List[Tuple[str, str]],
        p_old: Dict[str, Any],
        p_new: Dict[str, Any],
        old_doc: Dict[str, Any],
        new_doc: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        changes: List[Dict[str, Any]] = []
        semantic_changes: List[Dict[str, Any]] = []
        for old_path, new_path in pairs:
            logical = PathNormalizer.normalize(old_path)
            if old_path != new_path:
                changes.append(
                    {
                        "type": "VERSION_BUMP",
                        "original_path": old_path,
                        "new_path": new_path,
                        "path": logical,
                        "impact": self._classifier.version_bump(),
                    }
                )
                semantic_changes.append(
                    _enrich_semantic_change(
                        {
                            "type": "version_bump",
                            "from": old_path,
                            "to": new_path,
                            "details": {"logical": logical},
                            "confidence": 1.0,
                            "context": logical,
                            "direction": "request",
                        }
                    )
                )

            ops_o = p_old.get(old_path) or {}
            ops_n = p_new.get(new_path) or {}

            m_old = {m.lower() for m in ops_o if m.lower() in HTTP_METHODS}
            m_new = {m.lower() for m in ops_n if m.lower() in HTTP_METHODS}

            for m in sorted(m_old - m_new):
                changes.append(
                    {
                        "type": "METHOD_REMOVED",
                        "path": logical,
                        "original_path": old_path,
                        "new_path": new_path,
                        "method": m.upper(),
                        "impact": self._classifier.method_removed(),
                    }
                )
                semantic_changes.append(
                    _enrich_semantic_change(
                        {
                            "type": "method_removed",
                            "from": f"{m.upper()} {old_path}",
                            "to": "",
                            "details": {"logical": logical},
                            "confidence": 1.0,
                            "context": logical,
                            "direction": "request",
                        }
                    )
                )
            for m in sorted(m_new - m_old):
                changes.append(
                    {
                        "type": "METHOD_ADDED",
                        "path": logical,
                        "original_path": old_path,
                        "new_path": new_path,
                        "method": m.upper(),
                        "impact": self._classifier.method_added(),
                    }
                )
                semantic_changes.append(
                    _enrich_semantic_change(
                        {
                            "type": "method_added",
                            "from": "",
                            "to": f"{m.upper()} {new_path}",
                            "details": {"logical": logical},
                            "confidence": 1.0,
                            "context": logical,
                            "direction": "request",
                        }
                    )
                )

            ro = SchemaResolver(old_doc)
            rn = SchemaResolver(new_doc)

            for m in sorted(m_old & m_new):
                leg, sem = self._semantic_diff_operation_surface(
                    ro,
                    rn,
                    logical_path=logical,
                    method=m,
                    original_path=old_path,
                    new_path=new_path,
                    op_old=ops_o[m] or {},
                    op_new=ops_n[m] or {},
                    old_doc=old_doc,
                    new_doc=new_doc,
                )
                changes.extend(leg)
                semantic_changes.extend(sem)

        return changes, semantic_changes

    def _diff_unmatched_endpoints(
        self, only_old: Set[str], only_new: Set[str]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        changes: List[Dict[str, Any]] = []
        semantic_changes: List[Dict[str, Any]] = []
        for p in sorted(only_old):
            lp = PathNormalizer.normalize(p)
            changes.append(
                {
                    "type": "ENDPOINT_REMOVED",
                    "original_path": p,
                    "path": lp,
                    "impact": self._classifier.endpoint_removed(),
                }
            )
            semantic_changes.append(
                _enrich_semantic_change(
                    {
                        "type": "endpoint_removed",
                        "from": p,
                        "to": "",
                        "details": {"logical": lp},
                        "confidence": 1.0,
                        "context": lp,
                        "direction": "request",
                    }
                )
            )

        for p in sorted(only_new):
            lp = PathNormalizer.normalize(p)
            changes.append(
                {
                    "type": "ENDPOINT_ADDED",
                    "original_path": p,
                    "path": lp,
                    "impact": self._classifier.endpoint_added(),
                }
            )
            semantic_changes.append(
                _enrich_semantic_change(
                    {
                        "type": "endpoint_added",
                        "from": "",
                        "to": p,
                        "details": {"logical": lp},
                        "confidence": 1.0,
                        "context": lp,
                        "direction": "request",
                    }
                )
            )
        return changes, semantic_changes

    def diff(self, old_doc: Dict[str, Any], new_doc: Dict[str, Any]) -> Dict[str, Any]:
        raw_old = old_doc.get("paths") or {}
        raw_new = new_doc.get("paths") or {}

        p_old = {p: ops for p, ops in raw_old.items() if not _is_noise_path(p)}
        p_new = {p: ops for p, ops in raw_new.items() if not _is_noise_path(p)}

        pairs, only_old, only_new = EndpointMatcher.build_pairs(
            set(p_old.keys()), set(p_new.keys())
        )

        c1, s1 = self._diff_paired_paths(pairs, p_old, p_new, old_doc, new_doc)
        c2, s2 = self._diff_unmatched_endpoints(only_old, only_new)
        changes = c1 + c2
        semantic_changes = s1 + s2

        return {
            "changes": _dedupe_changes(changes),
            "semantic_changes": dedupe_semantic_changes(semantic_changes),
        }

    def compare_public_vs_internal_schema(
        self, public: Dict[str, Any], internal: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        pub_keys: Set[str] = set()
        int_keys: Set[str] = set()

        def collect(node: Any, dest: Set[str]) -> None:
            if isinstance(node, dict):
                props = node.get("properties")
                if isinstance(props, dict):
                    for k, v in props.items():
                        dest.add(k)
                        collect(v, dest)
                for k, v in node.items():
                    if k in METADATA_KEYS:
                        continue
                    if k == "properties":
                        continue
                    collect(v, dest)
            elif isinstance(node, list):
                for it in node:
                    collect(it, dest)

        collect(public, pub_keys)
        collect(internal, int_keys)

        leaked = sorted(int_keys - pub_keys)
        out: List[Dict[str, Any]] = []
        for f in leaked:
            lf = f.lower()
            if any(kw in lf for kw in SENSITIVE_KEYWORDS):
                out.append(
                    {"type": "SENSITIVE_LEAKAGE", "field": f, "impact": "CRITICAL"}
                )
        return out


# Public class name expected by tests and imports
DifferentialEngine = DiffEngine


def compare_schemas_v2(
    old_doc: Dict[str, Any], new_doc: Dict[str, Any]
) -> Dict[str, Any]:
    """Entry point for `schema_monitor.compare_schemas_structured`."""
    return DiffEngine().diff(old_doc, new_doc)


def semantic_schema_diff(
    old_doc: Dict[str, Any], new_doc: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Return a merged semantic changelog: field-level events
    (``rename``, ``type_change``, ``added``, ``removed``, ``required_change``, ``moved``,
    ``parameter_in_changed``)
    plus endpoint-level entries (``version_bump``, ``endpoint_removed``, ``endpoint_added``).
    """
    normalized_old = normalize_openapi_document(old_doc)
    normalized_new = normalize_openapi_document(new_doc)
    result = DiffEngine().diff(normalized_old, normalized_new)
    return list(result.get("semantic_changes") or [])


__all__ = [
    "PathNormalizer",
    "EndpointMatcher",
    "SchemaResolver",
    "ChangeClassifier",
    "CompatibilityRule",
    "apply_compatibility_rules",
    "rule_category_for_change",
    "DiffEngine",
    "DifferentialEngine",
    "compare_schemas_v2",
    "semantic_schema_diff",
]
