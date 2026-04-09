#!/usr/bin/env python3
"""
Register runtime-validator demo APIs, a schema-diff showcase (two OpenAPI versions on one API),
and their schema snapshots.

Requires Postgres (same env as main app: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME).

Usage (from host, DB default localhost):
  python seed_runtime_validator_fixtures.py

Docker backend container:
  docker compose exec backend python seed_runtime_validator_fixtures.py

Optional env:
  RTV_SEED_USER / RTV_SEED_PASSWORD (default: rtv_demo / rtv_demo)
  RTV_DEMO_BASE_URL — must match where the browser/backend can reach demo routes
    (default http://127.0.0.1:8000). Inside Docker backend use http://127.0.0.1:8000.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

from passlib.context import CryptContext  # noqa: E402
from registry_db import ApiRegistry, SchemaSnapshot, UserRegistry, init_db  # noqa: E402
from runtime_validator import create_runtime_validator  # noqa: E402
from schema_monitor import generate_pdf_from_json  # noqa: E402

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

FIXTURES: List[Tuple[str, str]] = [
    ("Northwind · Product Catalog (runtime — all pass)", "rtv_schema_1.openapi.json"),
    ("Fabrikam · Partner Hub (runtime — all pass)", "rtv_schema_2.openapi.json"),
    ("Adventure Works · Warehouse API (runtime — 2 drift checks)", "rtv_schema_3.openapi.json"),
]

DIFF_SHOWCASE_API_NAME = "Contoso · HR Directory (OpenAPI v1 vs v2)"
DIFF_SHOWCASE_DIR = BACKEND / "fixtures" / "schema_diff_showcase"
DIFF_SHOWCASE_VERSIONS: List[Tuple[str, str]] = [
    ("diff_showcase_v1.openapi.json", "fixture://diff_showcase_v1.openapi.json"),
    ("diff_showcase_v2.openapi.json", "fixture://diff_showcase_v2.openapi.json"),
]


def _load_schema(fname: str) -> Dict[str, Any]:
    path = BACKEND / "fixtures" / "runtime_validator" / fname
    return json.loads(path.read_text(encoding="utf-8"))


def _load_diff_showcase_schema(fname: str) -> Dict[str, Any]:
    path = DIFF_SHOWCASE_DIR / fname
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_user(username: str, password: str) -> Dict[str, Any]:
    user = UserRegistry.get_by_username(username)
    if user:
        return user
    created = UserRegistry.create(username, pwd.hash(password))
    if created:
        return created
    got = UserRegistry.get_by_username(username)
    if not got:
        raise RuntimeError(f"Could not create or load user {username!r}")
    return got


def seed_schemas(base_url: str, username: str, password: str) -> None:
    init_db()
    user = _ensure_user(username, password)
    user_id = user["id"]
    base_url = base_url.rstrip("/")

    for name, fname in FIXTURES:
        schema = _load_schema(fname)
        apis = ApiRegistry.get_all(user_id)
        api = next((a for a in apis if a["name"] == name), None)
        desc = f"OpenAPI fixture {fname}; demo HTTP routes are implemented on the APISEC backend."
        if not api:
            api = ApiRegistry.create(user_id, name, base_url, description=desc)
        else:
            ApiRegistry.update(user_id, api["id"], name, base_url, api.get("description") or desc)

        schema_url = f"fixture://{fname}"
        result = SchemaSnapshot.create_if_different(api["id"], schema, schema_url=schema_url)
        if result.get("status") == "unchanged":
            print(f"[unchanged] {name}")
        else:
            SchemaSnapshot.update_pdf(result["id"], generate_pdf_from_json(schema))
            print(f"[stored] {name} — snapshot id {result['id']} v{result['version_number']}")


def seed_diff_showcase(user_id: int, base_url: str) -> None:
    """
    One API with two chronological snapshots (v1 then v2) for schema_diff_engine / compare UI.
    """
    apis = ApiRegistry.get_all(user_id)
    api = next((a for a in apis if a["name"] == DIFF_SHOWCASE_API_NAME), None)
    desc = (
        "Contoso HR directory: paired OpenAPI v1 vs v2 for schema_diff_engine demos "
        "(version bump, method add/remove, endpoint add/remove, parameter location, renames, "
        "required flips, type narrowing, security-tagged response fields)."
    )
    if not api:
        api = ApiRegistry.create(user_id, DIFF_SHOWCASE_API_NAME, base_url, description=desc)
    else:
        ApiRegistry.update(user_id, api["id"], DIFF_SHOWCASE_API_NAME, base_url, api.get("description") or desc)

    for fname, schema_url in DIFF_SHOWCASE_VERSIONS:
        schema = _load_diff_showcase_schema(fname)
        result = SchemaSnapshot.create_if_different(api["id"], schema, schema_url=schema_url)
        if result.get("status") == "unchanged":
            print(f"[unchanged] {DIFF_SHOWCASE_API_NAME} — {fname}")
        else:
            SchemaSnapshot.update_pdf(result["id"], generate_pdf_from_json(schema))
            print(
                f"[stored] {DIFF_SHOWCASE_API_NAME} — {fname} "
                f"snapshot id {result['id']} v{result['version_number']}"
            )


async def verify_fixtures(base_url: str) -> int:
    """Return process exit code: 0 if all expectations met."""
    base_url = base_url.rstrip("/")
    validator = create_runtime_validator(timeout=15, max_concurrent=10)
    exit_code = 0

    for idx, (_, fname) in enumerate(FIXTURES, start=1):
        schema = _load_schema(fname)
        result = await validator.validate_schema(base_url, schema)
        n = len(result.endpoint_tests)
        passed = result.passed_endpoints
        failed = result.failed_endpoints
        print(f"\n=== Schema {idx} ({fname}) ===")
        print(f"endpoints={result.total_endpoints} tested={n} passed={passed} failed={failed} overall={result.overall_status}")

        if idx in (1, 2):
            if failed != 0 or result.overall_status != "passed":
                print("EXPECTED: all endpoints pass")
                exit_code = 1
            for t in result.endpoint_tests:
                if not t.validation_passed:
                    print(f"  unexpected fail: {t.method} {t.path} err={t.error} sm={t.status_mismatch} zm={t.schema_mismatch}")
                    exit_code = 1
        else:
            bad = [t for t in result.endpoint_tests if not t.validation_passed]
            if len(bad) != 2:
                print(f"EXPECTED: exactly 2 failing endpoints, got {len(bad)}")
                exit_code = 1
            for t in bad:
                print(f"  expected fail: {t.method} {t.path} status_mismatch={t.status_mismatch} schema_mismatch={t.schema_mismatch} actual={t.actual_status}")

    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed RTV demo APIs + optional verify.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("RTV_DEMO_BASE_URL", "http://127.0.0.1:8000"),
        help="API base URL stored on registry rows and used for verify",
    )
    parser.add_argument("--user", default=os.environ.get("RTV_SEED_USER", "rtv_demo"))
    parser.add_argument("--password", default=os.environ.get("RTV_SEED_PASSWORD", "rtv_demo"))
    parser.add_argument("--verify", action="store_true", help="Run runtime validator after seed")
    args = parser.parse_args()

    seed_schemas(args.base_url, args.user, args.password)
    user = _ensure_user(args.user, args.password)
    seed_diff_showcase(user["id"], args.base_url.rstrip("/"))

    if args.verify:
        code = asyncio.run(verify_fixtures(args.base_url))
        raise SystemExit(code)


if __name__ == "__main__":
    main()
