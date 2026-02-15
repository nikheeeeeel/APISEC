"""
Minimal v2 pipeline stabilization tests.

Validates:
- Mocked validation-error endpoint -> at least one parameter discovered
- Constant 200 response -> zero parameters discovered
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

# Ensure tests run from backend/
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run(coro):
    """Run async coroutine from sync test."""
    return asyncio.run(coro)


@pytest.fixture
def mock_transport_validation_error():
    """Mock transport: 422 on empty body, 200 when param provided (to trigger diff)."""
    transport = Mock()
    err_resp = Mock()
    err_resp.status_code = 422
    err_resp.text = '{"detail": [{"loc": ["body", "username"], "msg": "field required"}]}'
    err_resp.headers = {"content-type": "application/json"}
    ok_resp = Mock()
    ok_resp.status_code = 200
    ok_resp.text = '{"success": true}'
    ok_resp.headers = {"content-type": "application/json"}

    async def send(request, payload=None, location="body"):
        if not payload or (isinstance(payload, dict) and len(payload) == 0):
            return err_resp
        return ok_resp

    transport.send = AsyncMock(side_effect=send)
    return transport


@pytest.fixture
def mock_transport_constant_200():
    """Mock transport that always returns 200 with same body."""
    transport = Mock()
    response = Mock()
    response.status_code = 200
    response.text = '{"status": "ok", "data": []}'
    response.headers = {"content-type": "application/json"}
    transport.send = AsyncMock(return_value=response)
    return transport


def test_validation_error_discovers_parameter(mock_transport_validation_error):
    """Endpoint returning validation error should discover at least one parameter."""
    from models import DiscoveryRequest
    from probes.differential_engine import DifferentialEngine
    from probes.strategies import StringProbe

    async def _run_test():
        engine = DifferentialEngine(
            transport_client=mock_transport_validation_error,
            probe_strategies=[StringProbe()]
        )
        request = DiscoveryRequest(url="https://api.example.com/login", method="POST")
        return await engine.run(request)

    candidates = _run(_run_test())

    param_names = [c.name for c in candidates]
    assert len(param_names) >= 1, f"Expected at least 1 parameter, got: {param_names}"
    assert "username" in param_names, f"Expected 'username' in {param_names}"


def test_constant_200_returns_zero_parameters(mock_transport_constant_200):
    """Endpoint returning constant 200 should discover zero parameters."""
    from models import DiscoveryRequest
    from probes.differential_engine import DifferentialEngine
    from probes.strategies import StringProbe

    async def _run_test():
        engine = DifferentialEngine(
            transport_client=mock_transport_constant_200,
            probe_strategies=[StringProbe()]
        )
        request = DiscoveryRequest(url="https://api.example.com/health", method="GET")
        return await engine.run(request)

    candidates = _run(_run_test())

    assert len(candidates) == 0, f"Expected 0 parameters for constant 200, got: {[c.name for c in candidates]}"


def test_v2_orchestrator_end_to_end_mocked():
    """V2 orchestrator runs end-to-end with mocked transport (integration smoke test)."""
    from models import DiscoveryRequest
    from unittest.mock import patch

    err_response = Mock()
    err_response.status_code = 422
    err_response.text = '{"detail": [{"loc": ["body", "email"], "msg": "field required"}]}'
    err_response.headers = {"content-type": "application/json"}

    ok_response = Mock()
    ok_response.status_code = 200
    ok_response.text = '{"success": true}'
    ok_response.headers = {"content-type": "application/json"}

    async def mock_send(request, payload=None, location="body"):
        # Empty payload -> validation error; non-empty -> success (param accepted)
        if not payload or (isinstance(payload, dict) and len(payload) == 0):
            return err_response
        return ok_response

    async def _run_test():
        with patch('orchestrator.v2_orchestrator.RequestsTransportClient') as MockTransport:
            mock_client = Mock()
            mock_client.send = AsyncMock(side_effect=mock_send)
            MockTransport.return_value = mock_client

            from orchestrator.v2_orchestrator import create_v2_orchestrator

            orchestrator = create_v2_orchestrator()
            request = DiscoveryRequest(url="https://api.example.com/register", method="POST", timeout_seconds=5)
            return await orchestrator.discover_parameters(request)

    result = _run(_run_test())

    assert 'parameters' in result
    assert 'meta' in result
    assert result['meta']['discovery_version'] == 'v2'
    assert 'execution_time_ms' in result['meta']
    assert 'error' not in result['meta'], f"Pipeline should not error: {result.get('meta', {}).get('error')}"
    # Pipeline completes all phases (baseline, differential, location, framework, scoring, classification)
    assert len(result['meta'].get('orchestration_phases', [])) >= 6


def test_determinism_guard_same_endpoint_same_results():
    """
    Determinism guard: same mocked endpoint run twice yields identical parameter results.
    Ensures no hidden state or mutation issues.
    """
    from models import DiscoveryRequest
    from unittest.mock import patch

    err_response = Mock()
    err_response.status_code = 422
    err_response.text = '{"detail": [{"loc": ["body", "id"], "msg": "field required"}]}'
    err_response.headers = {"content-type": "application/json"}

    ok_response = Mock()
    ok_response.status_code = 200
    ok_response.text = '{"success": true}'
    ok_response.headers = {"content-type": "application/json"}

    async def mock_send(request, payload=None, location="body"):
        if not payload or (isinstance(payload, dict) and len(payload) == 0):
            return err_response
        return ok_response

    async def _run_once():
        with patch('orchestrator.v2_orchestrator.RequestsTransportClient') as MockTransport:
            mock_client = Mock()
            mock_client.send = AsyncMock(side_effect=mock_send)
            MockTransport.return_value = mock_client

            from orchestrator.v2_orchestrator import create_v2_orchestrator

            orchestrator = create_v2_orchestrator()
            request = DiscoveryRequest(url="https://api.example.com/items", method="POST", timeout_seconds=5)
            return await orchestrator.discover_parameters(request)

    result1 = _run(_run_once())
    result2 = _run(_run_once())

    params1 = [p.get("name") for p in result1.get("parameters", [])]
    params2 = [p.get("name") for p in result2.get("parameters", [])]

    assert params1 == params2, f"Determinism violated: run1={params1} run2={params2}"
