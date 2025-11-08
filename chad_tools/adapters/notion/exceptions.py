"""Notion adapter exceptions.

Custom exception hierarchy for Notion API errors.
"""


class NotionAdapterError(Exception):
    """Base exception for Notion adapter."""

    pass


class NotionAuthError(NotionAdapterError):
    """Invalid API key or insufficient permissions."""

    pass


class NotionRateLimitError(NotionAdapterError):
    """Rate limit exceeded (429 response)."""

    pass


class NotionResourceNotFoundError(NotionAdapterError):
    """Page/database not found (404 response)."""

    pass


class NotionValidationError(NotionAdapterError):
    """Invalid input parameters."""

    pass
