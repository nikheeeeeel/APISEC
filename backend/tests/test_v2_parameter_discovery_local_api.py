"""Integration tests against a controlled local API for REST Parameter Discovery v2."""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import pytest
import requests

# Ensure backend package is importable
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from orchestrator.v2_orchestrator import create_v2_orchestrator
from models import DiscoveryRequest

API_URL = "http://127.0.0.1:5050"


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(scope="session")
def test_api_server():
    """Start the controlled Express API once for the entire test session."""
    server_script = BACKEND_ROOT.parent / "test_api" / "server.js"
    if not server_script.exists():
        pytest.skip("test_api server script is missing")

    process = subprocess.Popen(
        ["node", str(server_script)],
        cwd=BACKEND_ROOT.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            resp = requests.get(f"{API_URL}/health", timeout=0.5)
            if resp.status_code == 200:
                break
        except requests.RequestException:
            time.sleep(0.15)
    else:
        process.kill()
        process.wait(1)
        pytest.skip("test_api server failed to start")

    try:
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()


def _build_orchestrator():
    return create_v2_orchestrator(enable_v2=True)


def _discover(endpoint: str, method: str = "GET", headers: Optional[Dict[str, str]] = None):
    orchestrator = _build_orchestrator()
    request = DiscoveryRequest(
        url=f"{API_URL}{endpoint}",
        method=method,
        timeout_seconds=10,
        headers=headers or {},
    )

    return _run(orchestrator.discover_parameters(request))


def test_users_endpoint_discovers_email(test_api_server):
    result = _discover("/users", method="GET")
    names = [param.get("name") for param in result.get("parameters", [])]

    assert len(names) == 1
    assert names[0] == "email"
    assert result.get("meta", {}).get("discovery_version") == "v2"


def test_login_endpoint_discovers_username_and_password(test_api_server):
    result = _discover("/login", method="POST")
    names = sorted(param.get("name") for param in result.get("parameters", []))

    assert names == ["password", "username"]


def test_secure_data_discovery_without_auth_yields_no_parameters(test_api_server):
    result = _discover("/secure-data", method="GET")

    assert result.get("parameters") == []


def test_secure_data_discovery_with_valid_auth_yields_no_parameters(test_api_server):
    result = _discover("/secure-data", method="GET", headers={"Authorization": "Bearer testtoken"})

    assert result.get("parameters") == []
