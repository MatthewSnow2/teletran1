"""N8N Webhook HTTP Client."""

import asyncio
from typing import Any

import httpx

from .schemas import N8nWebhookResponse


class N8nClient:
    """HTTP client for calling n8n webhooks."""

    def __init__(self, timeout: int = 300, api_key: str | None = None):
        """Initialize n8n client.

        Args:
            timeout: Default timeout in seconds
            api_key: Optional API key for X-CHAD-API-KEY header
        """
        self.timeout = timeout
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=timeout)

    async def call_webhook(
        self,
        webhook_url: str,
        payload: dict[str, Any],
        api_key: str | None = None,
    ) -> N8nWebhookResponse:
        """Call n8n webhook and return response.

        Args:
            webhook_url: Full webhook URL
            payload: JSON payload to send
            api_key: Optional API key (overrides instance key)

        Returns:
            N8nWebhookResponse with success/error info

        Raises:
            httpx.HTTPError: On network/timeout errors
        """
        headers = {"Content-Type": "application/json"}

        # Add API key if provided
        key = api_key or self.api_key
        if key:
            headers["X-CHAD-API-KEY"] = key

        try:
            response = await self.client.post(
                webhook_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()

            return N8nWebhookResponse(
                success=True,
                data=data,
                execution_id=data.get("execution_id"),
            )

        except httpx.HTTPStatusError as e:
            # Try to parse error response
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", e.response.text)
            except Exception:
                error_msg = e.response.text

            return N8nWebhookResponse(
                success=False,
                error=f"HTTP {e.response.status_code}: {error_msg}",
            )
        except httpx.TimeoutException:
            return N8nWebhookResponse(
                success=False,
                error=f"Webhook timed out after {self.timeout}s",
            )
        except Exception as e:
            return N8nWebhookResponse(
                success=False,
                error=f"Unexpected error: {str(e)}",
            )

    async def poll_execution(
        self,
        webhook_url: str,
        execution_id: str,
        max_polls: int = 10,
        poll_interval: int = 5,
        api_key: str | None = None,
    ) -> N8nWebhookResponse:
        """Poll for async workflow execution result.

        For long-running workflows that return execution_id immediately.

        Args:
            webhook_url: Webhook URL with /status endpoint
            execution_id: Execution ID to poll for
            max_polls: Maximum number of polling attempts
            poll_interval: Seconds between polls
            api_key: Optional API key for authentication

        Returns:
            Final N8nWebhookResponse when complete
        """
        status_url = f"{webhook_url}/status/{execution_id}"

        for attempt in range(max_polls):
            response = await self.call_webhook(status_url, {}, api_key=api_key)

            if response.success and response.data:
                status = response.data.get("status")

                if status == "completed":
                    return response
                elif status == "failed":
                    return N8nWebhookResponse(
                        success=False,
                        error=response.data.get("error", "Workflow failed"),
                    )
                # Still running, continue polling

            await asyncio.sleep(poll_interval)

        return N8nWebhookResponse(
            success=False,
            error=f"Workflow polling timeout after {max_polls} attempts",
        )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
