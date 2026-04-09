from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class RuntimeValidationRequest(BaseModel):
    base_url: str
    schema_info: Dict[str, Any]


class EndpointTestResult(BaseModel):
    method: str
    path: str
    url: str
    expected_status: Optional[int] = None
    actual_status: Optional[int] = None
    expected_response_schema: Optional[Dict] = None
    actual_response: Optional[Any] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    status_mismatch: bool = False
    schema_mismatch: bool = False
    validation_passed: bool = True


class RuntimeFailureAnalysisRequest(BaseModel):
    """Body for AI explanation of a single failed runtime endpoint test."""

    base_url: str
    endpoint_test: EndpointTestResult


class RuntimeValidationResponse(BaseModel):
    base_url: str
    total_endpoints: int
    tested_endpoints: int
    passed_endpoints: int
    failed_endpoints: int
    endpoint_tests: List[EndpointTestResult]
    validation_timestamp: datetime
    overall_status: str  # "passed", "failed", "partial"
    summary: str
