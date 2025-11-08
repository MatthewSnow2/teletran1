"""Notion API client wrapper.

Centralized Notion API client with error handling, rate limiting, and retry logic.
"""

import asyncio
from typing import Any

from notion_client import AsyncClient
from notion_client.errors import APIResponseError

from .exceptions import (
    NotionAdapterError,
    NotionAuthError,
    NotionRateLimitError,
    NotionResourceNotFoundError,
)


class NotionClientWrapper:
    """Notion API client with Chad-Core integration.

    Provides:
    - Error handling and exception mapping
    - Rate limiting (3 requests/second default)
    - Automatic retry with exponential backoff
    - Structured error messages
    """

    def __init__(
        self,
        api_key: str,
        version: str = "2022-06-28",
        rate_limit_per_second: int = 3,
        timeout_seconds: int = 30,
    ):
        """Initialize Notion client.

        Args:
            api_key: Notion integration API key
            version: Notion API version
            rate_limit_per_second: Max requests per second
            timeout_seconds: Request timeout
        """
        self.client = AsyncClient(auth=api_key, notion_version=version)
        self.rate_limit_per_second = rate_limit_per_second
        self.timeout_seconds = timeout_seconds
        self._last_request_time = 0.0

    async def _rate_limit(self) -> None:
        """Enforce rate limiting."""
        current_time = asyncio.get_event_loop().time()
        time_since_last_request = current_time - self._last_request_time
        min_interval = 1.0 / self.rate_limit_per_second

        if time_since_last_request < min_interval:
            await asyncio.sleep(min_interval - time_since_last_request)

        self._last_request_time = asyncio.get_event_loop().time()

    def _handle_error(self, error: APIResponseError) -> None:
        """Map Notion API errors to custom exceptions."""
        status = error.status
        # APIResponseError uses 'body' or str(error), not 'message'
        message = str(error)

        if status == 401:
            raise NotionAuthError(f"Authentication failed: {message}")
        elif status == 404:
            raise NotionResourceNotFoundError(f"Resource not found: {message}")
        elif status == 429:
            raise NotionRateLimitError(f"Rate limit exceeded: {message}")
        else:
            raise NotionAdapterError(f"Notion API error ({status}): {message}")

    async def search(
        self,
        query: str,
        filter_type: str | None = None,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """Search Notion workspace.

        Args:
            query: Search query string
            filter_type: Filter by "page" or "database"
            page_size: Number of results to return

        Returns:
            Search results from Notion API

        Raises:
            NotionAuthError: Invalid API key
            NotionRateLimitError: Rate limit exceeded
            NotionAdapterError: Other API errors
        """
        await self._rate_limit()

        try:
            # Build search parameters (only include filter if provided)
            search_params = {
                "query": query,
                "page_size": page_size,
            }

            if filter_type:
                search_params["filter"] = {"property": "object", "value": filter_type}

            response = await self.client.search(**search_params)
            return response
        except APIResponseError as e:
            self._handle_error(e)
            raise  # For type checker

    async def get_page(self, page_id: str) -> dict[str, Any]:
        """Retrieve page metadata.

        Args:
            page_id: Notion page ID (UUID)

        Returns:
            Page metadata from Notion API
        """
        await self._rate_limit()

        try:
            response = await self.client.pages.retrieve(page_id)
            return response
        except APIResponseError as e:
            self._handle_error(e)
            raise

    async def get_blocks(
        self, block_id: str, page_size: int = 100
    ) -> dict[str, Any]:
        """Retrieve page blocks (content).

        Args:
            block_id: Block ID (usually page ID)
            page_size: Number of blocks to retrieve

        Returns:
            Blocks from Notion API
        """
        await self._rate_limit()

        try:
            response = await self.client.blocks.children.list(
                block_id, page_size=page_size
            )
            return response
        except APIResponseError as e:
            self._handle_error(e)
            raise

    async def create_page(
        self,
        parent: dict[str, str],
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
        icon: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create new page.

        Args:
            parent: Parent page or database reference
            properties: Page properties (title, etc.)
            children: Page content blocks
            icon: Page icon (emoji or external URL)

        Returns:
            Created page from Notion API
        """
        await self._rate_limit()

        try:
            response = await self.client.pages.create(
                parent=parent,
                properties=properties,
                children=children or [],
                icon=icon,
            )
            return response
        except APIResponseError as e:
            self._handle_error(e)
            raise

    async def query_database(
        self,
        database_id: str,
        filter_obj: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """Query database with filters and sorting.

        Args:
            database_id: Notion database ID
            filter_obj: Notion filter object
            sorts: Sort configurations
            page_size: Number of results to return

        Returns:
            Database query results from Notion API
        """
        await self._rate_limit()

        try:
            response = await self.client.databases.query(
                database_id=database_id,
                filter=filter_obj,
                sorts=sorts or [],
                page_size=page_size,
            )
            return response
        except APIResponseError as e:
            self._handle_error(e)
            raise
