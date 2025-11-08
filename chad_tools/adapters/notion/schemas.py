"""Notion adapter Pydantic schemas.

Input and output schemas for all Notion tools.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


# ============================================================================
# SEARCH TOOL SCHEMAS
# ============================================================================


class NotionSearchInput(BaseModel):
    """Input schema for NotionSearchTool."""

    query: str = Field(..., description="Search query string")
    filter_type: Literal["page", "database"] | None = Field(
        None, description="Filter by object type"
    )
    max_results: int = Field(10, ge=1, le=100, description="Maximum results to return")
    dry_run: bool = False


class NotionSearchResult(BaseModel):
    """Single search result."""

    id: str = Field(..., description="Page/database ID (UUID)")
    type: Literal["page", "database"]
    title: str
    url: str
    created_time: str
    last_edited_time: str
    parent_type: str = Field(..., description="workspace, page, or database")


class NotionSearchOutput(BaseModel):
    """Output schema for NotionSearchTool."""

    results: list[NotionSearchResult]
    total_count: int
    has_more: bool
    status: Literal["success", "dry_run"] = "success"


# ============================================================================
# READ PAGE TOOL SCHEMAS
# ============================================================================


class NotionReadPageInput(BaseModel):
    """Input schema for NotionReadPageTool."""

    page_id: str = Field(..., description="Notion page ID (UUID)")
    include_children: bool = Field(True, description="Include nested blocks")
    max_depth: int = Field(3, ge=1, le=10, description="Maximum nesting depth")
    dry_run: bool = False


class NotionBlock(BaseModel):
    """Notion block representation."""

    id: str
    type: str = Field(..., description="paragraph, heading_1, code, etc.")
    content: str = Field("", description="Extracted text content")
    metadata: dict[str, Any] = Field(default_factory=dict)
    children: list["NotionBlock"] = Field(default_factory=list)


class NotionReadPageOutput(BaseModel):
    """Output schema for NotionReadPageTool."""

    page_id: str
    title: str
    url: str
    properties: dict[str, Any] = Field(default_factory=dict)
    content: list[NotionBlock]
    markdown: str = Field(..., description="Full page content as markdown")
    created_time: str
    last_edited_time: str
    status: Literal["success", "dry_run"] = "success"


# ============================================================================
# CREATE PAGE TOOL SCHEMAS
# ============================================================================


class NotionCreatePageInput(BaseModel):
    """Input schema for NotionCreatePageTool."""

    parent_id: str = Field(..., description="Parent page or database ID")
    parent_type: Literal["page_id", "database_id"] = "page_id"
    title: str = Field(..., description="Page title")
    content_markdown: str = Field("", description="Page content as markdown")
    properties: dict[str, Any] = Field(
        default_factory=dict, description="For database entries"
    )
    icon_emoji: str | None = None
    dry_run: bool = False


class NotionCreatePageOutput(BaseModel):
    """Output schema for NotionCreatePageTool."""

    page_id: str
    url: str
    title: str
    created_time: str
    status: Literal["created", "dry_run"]


# ============================================================================
# QUERY DATABASE TOOL SCHEMAS
# ============================================================================


class NotionQueryDatabaseInput(BaseModel):
    """Input schema for NotionQueryDatabaseTool."""

    database_id: str = Field(..., description="Notion database ID")
    filter_conditions: dict[str, Any] | None = Field(None, description="Notion filter object")
    sorts: list[dict[str, Any]] = Field(default_factory=list, description="Sort configurations")
    max_results: int = Field(100, ge=1, le=100)
    dry_run: bool = False


class NotionDatabaseEntry(BaseModel):
    """Single database entry result."""

    page_id: str
    url: str
    properties: dict[str, Any]
    created_time: str
    last_edited_time: str


class NotionQueryDatabaseOutput(BaseModel):
    """Output schema for NotionQueryDatabaseTool."""

    results: list[NotionDatabaseEntry]
    total_count: int
    has_more: bool
    status: Literal["success", "dry_run"] = "success"


# ============================================================================
# CREATE DATABASE ENTRY TOOL SCHEMAS
# ============================================================================


class NotionCreateDatabaseEntryInput(BaseModel):
    """Input schema for NotionCreateDatabaseEntryTool."""

    database_id: str = Field(..., description="Target database ID")
    properties: dict[str, Any] = Field(..., description="Entry properties")
    content_markdown: str = Field("", description="Optional page content")
    dry_run: bool = False


class NotionCreateDatabaseEntryOutput(BaseModel):
    """Output schema for NotionCreateDatabaseEntryTool."""

    page_id: str
    url: str
    properties: dict[str, Any]
    created_time: str
    status: Literal["created", "dry_run"]
