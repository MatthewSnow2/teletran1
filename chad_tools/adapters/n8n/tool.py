"""N8N Workflow Tool."""

from typing import Any

from chad_tools.base import Tool, ToolMetadata

from .client import N8nClient
from .schemas import N8nWorkflowMetadata


class N8nWorkflowTool:
    """Tool for calling n8n workflows via webhook."""

    def __init__(
        self,
        workflow_metadata: N8nWorkflowMetadata,
        client: N8nClient | None = None,
        api_key: str | None = None,
    ):
        """Initialize n8n workflow tool.

        Args:
            workflow_metadata: Workflow metadata from Notion docs
            client: Optional N8nClient instance (creates new if None)
            api_key: Optional API key for authentication
        """
        self.workflow_metadata = workflow_metadata
        self.client = client or N8nClient(api_key=api_key)
        self.api_key = api_key

        # Tool interface properties
        self.name = f"n8n_{workflow_metadata.workflow_id}"
        self.description = workflow_metadata.description
        self.metadata = ToolMetadata(
            requires_approval=workflow_metadata.requires_approval,
            dry_run_supported=True,
            idempotent=False,  # Webhooks are generally not idempotent
            capabilities=workflow_metadata.capabilities,
            risk_level=workflow_metadata.risk_level,
        )

    async def execute(
        self,
        ctx: dict,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute n8n workflow.

        Args:
            ctx: Execution context (dry_run, actor, run_id)
            input_data: Workflow input parameters

        Returns:
            Tool result with success/error info
        """
        # Handle dry-run mode
        if ctx.get("dry_run", False):
            return {
                "status": "dry_run",
                "message": f"Would call n8n workflow: {self.workflow_metadata.display_name}",
                "webhook_url": str(self.workflow_metadata.webhook_url),
                "input": input_data,
            }

        # Validate input against schema
        validation_error = self._validate_input(input_data)
        if validation_error:
            return {
                "status": "error",
                "error": f"Input validation failed: {validation_error}",
            }

        # Call webhook
        response = await self.client.call_webhook(
            webhook_url=str(self.workflow_metadata.webhook_url),
            payload=input_data,
            api_key=self.api_key,
        )

        # Handle async workflows
        if (
            self.workflow_metadata.is_async
            and response.success
            and response.execution_id
        ):
            response = await self.client.poll_execution(
                webhook_url=str(self.workflow_metadata.webhook_url),
                execution_id=response.execution_id,
                api_key=self.api_key,
            )

        # Return result
        if response.success:
            return {
                "status": "success",
                "data": response.data,
                "execution_id": response.execution_id,
            }
        else:
            return {
                "status": "error",
                "error": response.error,
            }

    def _validate_input(self, input_data: dict[str, Any]) -> str | None:
        """Validate input against JSON schema.

        Returns:
            Error message if validation fails, None if valid
        """
        # Simple validation - check required fields
        required = self.workflow_metadata.input_params.get("required", [])

        for field in required:
            if field not in input_data:
                return f"Missing required field: {field}"

        # TODO: Use jsonschema library for full validation
        # from jsonschema import validate, ValidationError
        # try:
        #     validate(instance=input_data, schema=self.workflow_metadata.input_params)
        # except ValidationError as e:
        #     return str(e)

        return None
