"""Unit checks for runtime_validator OpenAPI fixtures (no live HTTP)."""

import json
import os
from pathlib import Path

import pytest

from runtime_validator import RuntimeValidator

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "runtime_validator"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _count_operations(schema: dict) -> int:
    n = 0
    for path_item in schema.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                if isinstance(op, dict):
                    n += 1
    return n


@pytest.mark.parametrize(
    "fname",
    [
        "rtv_schema_1.openapi.json",
        "rtv_schema_2.openapi.json",
        "rtv_schema_3.openapi.json",
    ],
)
def test_fixture_endpoint_count_in_range(fname: str):
    schema = _load(fname)
    v = RuntimeValidator()
    extracted = v._extract_endpoints_from_schema(schema)
    assert 6 <= len(extracted) <= 10
    assert len(extracted) == _count_operations(schema)


def test_schema_three_includes_misbehave_paths():
    schema = _load("rtv_schema_3.openapi.json")
    paths = schema["paths"]
    assert "/adventureworks/warehouse/v1/replication/sync-status" in paths
    assert "/adventureworks/warehouse/v1/replication/lag-summary" in paths


@pytest.mark.skipif(
    os.environ.get("RTV_E2E") != "1",
    reason="Set RTV_E2E=1 with backend running at RTV_DEMO_BASE_URL",
)
def test_e2e_runtime_validation_against_demo_server():
    import asyncio

    from seed_runtime_validator_fixtures import verify_fixtures

    base = os.environ.get("RTV_DEMO_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    assert asyncio.run(verify_fixtures(base)) == 0
