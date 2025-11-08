"""N8N Workflow Schemas."""

from typing import Any
from pydantic import BaseModel, HttpUrl


class N8nWebhookRequest(BaseModel):
    """Request to n8n webhook."""

    webhook_url: HttpUrl
    payload: dict[str, Any]
    timeout_seconds: int = 300  # 5 minutes default


class N8nWebhookResponse(BaseModel):
    """Response from n8n webhook."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    execution_id: str | None = None  # For async workflows


class N8nWorkflowMetadata(BaseModel):
    """Metadata parsed from Notion documentation."""

    workflow_id: str
    display_name: str
    webhook_url: HttpUrl
    description: str

    # Input schema (JSON Schema)
    input_params: dict[str, Any]

    # Execution settings
    is_async: bool = False
    timeout_seconds: int = 300

    # Risk assessment
    requires_approval: bool = False
    risk_level: str = "low"  # low, medium, high

    # Capabilities
    capabilities: list[str] = []  # e.g., ["notification", "email"]
