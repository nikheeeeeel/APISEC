"""Tests for semantic schema diffing, rules engine, and sensitive response detection."""

from probes.schema_diff_engine import (
    DiffEngine,
    _enrich_semantic_change,
    _schema_path_matches_sensitive_keyword,
    compare_schemas_v2,
    rule_category_for_change,
)


def test_schema_path_matches_sensitive_keyword():
    assert _schema_path_matches_sensitive_keyword("response.password")
    assert _schema_path_matches_sensitive_keyword("response.user.api_key")
    assert _schema_path_matches_sensitive_keyword("response.backup_token")
    assert not _schema_path_matches_sensitive_keyword("response.displayName")
    assert not _schema_path_matches_sensitive_keyword("")


def test_enrich_escalates_sensitive_response_field():
    raw = {
        "type": "added",
        "from": "",
        "to": "response.profile.secret",
        "direction": "response",
        "details": {
            "old_type": "",
            "new_type": "string",
            "old_required": False,
            "new_required": False,
        },
        "confidence": 0.85,
    }
    e = _enrich_semantic_change(raw)
    assert e["compatibility_rule_id"] == 8001
    assert e["compatibility_rule_name"] == "SensitiveFieldExposedInResponse"
    assert e["severity"] == "CRITICAL"
    assert e["security_issue"] is True
    assert rule_category_for_change(e) == "Security"


def test_enrich_does_not_escalate_request_sensitive_name():
    raw = {
        "type": "added",
        "from": "",
        "to": "body.password",
        "direction": "request",
        "details": {
            "old_type": "",
            "new_type": "string",
            "old_required": False,
            "new_required": True,
        },
        "confidence": 0.85,
    }
    e = _enrich_semantic_change(raw)
    assert e["compatibility_rule_id"] == 1010
    assert e.get("security_issue") is not True


def test_diff_emits_sensitive_response_field_added():
    old = {
        "paths": {
            "/items": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "properties": {}},
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    new = {
        "paths": {
            "/items": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "api_key": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    result = DiffEngine().diff(old, new)
    types = {c.get("type") for c in result["changes"]}
    assert "SENSITIVE_RESPONSE_FIELD_ADDED" in types
    sec = next(c for c in result["changes"] if c.get("type") == "SENSITIVE_RESPONSE_FIELD_ADDED")
    assert sec.get("security_issue") is True
    assert (sec.get("severity") or "").upper() == "CRITICAL"


def test_compare_schemas_v2_includes_rule_category_on_semantic():
    old = {
        "paths": {
            "/a": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"x": {"type": "string"}},
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    new = {
        "paths": {
            "/a": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "x": {"type": "string"},
                                        "y": {"type": "string"},
                                    },
                                    "required": ["y"],
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    out = compare_schemas_v2(old, new)
    sem = out.get("semantic_changes") or []
    assert sem
    assert all("rule_category" in s for s in sem)
    added = next(s for s in sem if s.get("type") == "added")
    assert added.get("direction") == "request"
    assert added.get("compatibility_rule_id") == 1010
