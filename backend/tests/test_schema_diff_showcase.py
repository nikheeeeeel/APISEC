"""Sanity checks for schema_diff_engine paired fixtures (no DB)."""

import json
from pathlib import Path

from probes.schema_diff_engine import compare_schemas_v2

SHOWCASE = Path(__file__).resolve().parent.parent / "fixtures" / "schema_diff_showcase"


def _load(name: str) -> dict:
    return json.loads((SHOWCASE / name).read_text(encoding="utf-8"))


def test_diff_showcase_covers_engine_surface():
    v1 = _load("diff_showcase_v1.openapi.json")
    v2 = _load("diff_showcase_v2.openapi.json")
    r = compare_schemas_v2(v1, v2)
    types = {c.get("type") for c in r["changes"]}
    assert "VERSION_BUMP" in types
    assert "ENDPOINT_ADDED" in types
    assert "ENDPOINT_REMOVED" in types
    assert "METHOD_ADDED" in types
    assert "METHOD_REMOVED" in types
    assert "PARAMETER_LOCATION_CHANGED" in types
    assert "FIELD_RENAMED" in types
    assert "REQUIRED_STATUS_CHANGED" in types
    assert "FIELD_TYPE_CHANGED" in types
    assert "OPTIONAL_FIELD_ADDED" in types
    assert "FIELD_REMOVED" in types
    assert "FIELD_ADDED" in types
    assert "SENSITIVE_RESPONSE_FIELD_ADDED" in types
    assert len(r["changes"]) >= 12
