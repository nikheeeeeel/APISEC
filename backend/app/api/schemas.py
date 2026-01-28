"""API request/response schemas."""
from typing import Optional
from pydantic import BaseModel, HttpUrl


class GenerateDocsRequest(BaseModel):
    """Request schema for generating documentation."""
    api_uri: HttpUrl
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None


class GenerateDocsResponse(BaseModel):
    """Response schema for documentation generation."""
    success: bool
    message: str
    discovery_method: Optional[str] = None
    spec_id: Optional[str] = None
    report_id: Optional[str] = None


class ReportInfo(BaseModel):
    """Information about a generated report."""
    id: str
    filename: str
    api_uri: str
    generated_at: str
    discovery_method: str


class ReportsListResponse(BaseModel):
    """Response schema for listing reports."""
    reports: list[ReportInfo]
