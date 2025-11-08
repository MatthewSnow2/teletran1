# Notion Adapter Design for Chad-Core

**Purpose**: Notion as Chad's primary knowledge base - search, read, create, and organize knowledge.

**Status**: Design Phase
**Agent**: Phase 2 - Notion Integration
**Date**: 2025-11-03

---

## Overview

The Notion adapter provides Chad-Core with tools to interact with Notion as a knowledge base. It enables:
- **Reading knowledge** from Notion pages and databases
- **Searching** across the workspace
- **Creating new knowledge** (pages, database entries)
- **Querying structured data** from databases

---

## Architecture

### Tool Organization

All Notion tools will be implemented in `chad_tools/adapters/notion/`:

```
chad_tools/adapters/notion/
├── __init__.py                 # Exports all Notion tools
├── client.py                   # Notion API client wrapper
├── tools/
│   ├── __init__.py
│   ├── search.py               # NotionSearchTool
│   ├── read_page.py            # NotionReadPageTool
│   ├── create_page.py          # NotionCreatePageTool
│   ├── query_database.py       # NotionQueryDatabaseTool
│   └── create_database_entry.py # NotionCreateDatabaseEntryTool
└── schemas.py                  # Pydantic input/output schemas
```

---

## Notion Tools Specification

### 1. NotionSearchTool

**Capability**: `notion.search`
**Risk Level**: `low`
**Idempotent**: `true` (same query → same results)
**Requires Approval**: `false`
**Dry-Run Supported**: `true`

**Purpose**: Search across Notion workspace for pages and databases.

**Input Schema**:
```python
class NotionSearchInput(BaseModel):
    query: str = Field(..., description="Search query string")
    filter_type: Literal["page", "database"] | None = None
    max_results: int = Field(10, ge=1, le=100)
    dry_run: bool = False
```

**Output Schema**:
```python
class NotionSearchOutput(BaseModel):
    results: list[NotionSearchResult]
    total_count: int
    has_more: bool

class NotionSearchResult(BaseModel):
    id: str                     # Page/database ID
    type: Literal["page", "database"]
    title: str
    url: str
    created_time: str
    last_edited_time: str
    parent_type: str            # "workspace", "page", "database"
```

**Use Cases**:
- "Find all pages about Python best practices"
- "Search for database containing customer information"
- "Locate pages modified in the last week"

---

### 2. NotionReadPageTool

**Capability**: `notion.pages.read`
**Risk Level**: `low`
**Idempotent**: `true`
**Requires Approval**: `false`
**Dry-Run Supported**: `true`

**Purpose**: Retrieve full content of a Notion page including blocks (text, headings, code, etc.).

**Input Schema**:
```python
class NotionReadPageInput(BaseModel):
    page_id: str = Field(..., description="Notion page ID (UUID)")
    include_children: bool = True  # Include nested blocks
    max_depth: int = Field(3, ge=1, le=10)  # Max nesting depth
    dry_run: bool = False
```

**Output Schema**:
```python
class NotionReadPageOutput(BaseModel):
    page_id: str
    title: str
    url: str
    properties: dict[str, Any]  # Page properties (tags, dates, etc.)
    content: list[NotionBlock]  # Structured blocks
    markdown: str               # Rendered as markdown
    created_time: str
    last_edited_time: str

class NotionBlock(BaseModel):
    id: str
    type: str                   # "paragraph", "heading_1", "code", etc.
    content: str                # Extracted text
    metadata: dict[str, Any]    # Type-specific data
    children: list[NotionBlock] = []
```

**Use Cases**:
- "Read the entire 'Project Guidelines' page"
- "Extract code snippets from 'API Documentation' page"
- "Get content from page ID abc123"

---

### 3. NotionCreatePageTool

**Capability**: `notion.pages.create`
**Risk Level**: `medium`
**Idempotent**: `false` (creates new page each time)
**Requires Approval**: `true` (writes to Notion)
**Dry-Run Supported**: `true`

**Purpose**: Create new Notion pages with structured content.

**Input Schema**:
```python
class NotionCreatePageInput(BaseModel):
    parent_id: str = Field(..., description="Parent page or database ID")
    parent_type: Literal["page_id", "database_id"] = "page_id"
    title: str = Field(..., description="Page title")
    content_markdown: str = Field("", description="Page content as markdown")
    properties: dict[str, Any] = {}  # For database entries
    icon_emoji: str | None = None
    dry_run: bool = False
```

**Output Schema**:
```python
class NotionCreatePageOutput(BaseModel):
    page_id: str
    url: str
    title: str
    created_time: str
    status: Literal["created", "dry_run"]
```

**Use Cases**:
- "Create a new page titled 'Meeting Notes - 2025-11-03'"
- "Add a page to the 'Projects' database with status 'In Progress'"
- "Generate a summary page from recent research"

---

### 4. NotionQueryDatabaseTool

**Capability**: `notion.databases.query`
**Risk Level**: `low`
**Idempotent**: `true`
**Requires Approval**: `false`
**Dry-Run Supported**: `true`

**Purpose**: Query Notion databases with filters and sorting.

**Input Schema**:
```python
class NotionQueryDatabaseInput(BaseModel):
    database_id: str = Field(..., description="Notion database ID")
    filter_conditions: dict[str, Any] | None = None  # Notion filter object
    sorts: list[dict[str, Any]] = []                 # Sort configurations
    max_results: int = Field(100, ge=1, le=100)
    dry_run: bool = False
```

**Output Schema**:
```python
class NotionQueryDatabaseOutput(BaseModel):
    results: list[NotionDatabaseEntry]
    total_count: int
    has_more: bool

class NotionDatabaseEntry(BaseModel):
    page_id: str
    url: str
    properties: dict[str, Any]  # Database properties
    created_time: str
    last_edited_time: str
```

**Use Cases**:
- "Get all tasks with status 'In Progress'"
- "List projects sorted by priority"
- "Find database entries modified this week"

---

### 5. NotionCreateDatabaseEntryTool

**Capability**: `notion.databases.create_entry`
**Risk Level**: `medium`
**Idempotent**: `false`
**Requires Approval**: `true`
**Dry-Run Supported**: `true`

**Purpose**: Create new entries in Notion databases.

**Input Schema**:
```python
class NotionCreateDatabaseEntryInput(BaseModel):
    database_id: str = Field(..., description="Target database ID")
    properties: dict[str, Any] = Field(..., description="Entry properties")
    content_markdown: str = ""  # Optional page content
    dry_run: bool = False
```

**Output Schema**:
```python
class NotionCreateDatabaseEntryOutput(BaseModel):
    page_id: str
    url: str
    properties: dict[str, Any]
    created_time: str
    status: Literal["created", "dry_run"]
```

**Use Cases**:
- "Add a new task to the 'Todos' database"
- "Create a customer entry with name and email"
- "Log a new research finding"

---

## Notion Client Wrapper

### NotionClientWrapper

**Purpose**: Centralized Notion API client with error handling, rate limiting, and retry logic.

```python
# chad_tools/adapters/notion/client.py

from notion_client import AsyncClient
from notion_client.errors import APIResponseError

class NotionClientWrapper:
    """Notion API client with Chad-Core integration."""

    def __init__(self, api_key: str, version: str = "2022-06-28"):
        self.client = AsyncClient(auth=api_key, notion_version=version)

    async def search(self, query: str, filter_type: str | None = None) -> dict:
        """Search Notion workspace."""
        try:
            return await self.client.search(
                query=query,
                filter={"property": "object", "value": filter_type} if filter_type else None
            )
        except APIResponseError as e:
            # Handle rate limits, auth errors, etc.
            raise NotionAdapterError(f"Search failed: {e.message}")

    async def get_page(self, page_id: str) -> dict:
        """Retrieve page metadata."""
        return await self.client.pages.retrieve(page_id)

    async def get_blocks(self, block_id: str) -> dict:
        """Retrieve page blocks (content)."""
        return await self.client.blocks.children.list(block_id)

    async def create_page(self, parent: dict, properties: dict, children: list = []) -> dict:
        """Create new page."""
        return await self.client.pages.create(
            parent=parent,
            properties=properties,
            children=children
        )

    async def query_database(self, database_id: str, filter_obj: dict = None, sorts: list = []) -> dict:
        """Query database with filters."""
        return await self.client.databases.query(
            database_id=database_id,
            filter=filter_obj,
            sorts=sorts
        )
```

---

## Error Handling

### NotionAdapterError Hierarchy

```python
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
```

**Retry Strategy**:
- Rate limits (429): Exponential backoff (1s, 2s, 4s, 8s)
- Network errors (5xx): Retry 3 times with 1s delay
- Auth errors (401): No retry, raise immediately
- Not found (404): No retry, raise immediately

---

## Dry-Run Implementation

All Notion tools support dry-run mode for L1_Draft autonomy level:

**Dry-Run Behavior**:
1. Validate input schema (always)
2. If `dry_run=False`: Execute real Notion API call
3. If `dry_run=True`: Return mock response with `status: "dry_run"`

**Mock Response Format**:
```python
{
    "status": "dry_run",
    "simulated_output": {
        # Realistic mock data matching output schema
    },
    "would_execute": "POST /pages with title='Meeting Notes'",
    "warning": "This is a simulated response; no real Notion API call made"
}
```

---

## Configuration

### Environment Variables

```bash
# Required
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional
NOTION_VERSION=2022-06-28
NOTION_RATE_LIMIT_PER_SECOND=3  # Max 3 requests/second
NOTION_DEFAULT_MAX_RESULTS=10
NOTION_TIMEOUT_SECONDS=30
```

### Settings Integration

```python
# chad_config/settings.py

class Settings(BaseSettings):
    # ... existing settings ...

    # Notion Configuration
    NOTION_API_KEY: str = Field(..., description="Notion integration API key")
    NOTION_VERSION: str = "2022-06-28"
    NOTION_RATE_LIMIT_PER_SECOND: int = 3
    NOTION_DEFAULT_MAX_RESULTS: int = 10
    NOTION_TIMEOUT_SECONDS: int = 30
```

---

## Testing Strategy

### Unit Tests

```python
# tests/adapters/test_notion.py

@pytest.mark.asyncio
async def test_notion_search_tool():
    """Test NotionSearchTool with mocked API."""
    tool = NotionSearchTool(api_key="fake_key")

    with patch.object(tool.client, 'search') as mock_search:
        mock_search.return_value = {"results": [...]}

        result = await tool.execute(
            ctx={},
            input_data={"query": "Python", "max_results": 5}
        )

        assert result["total_count"] > 0
        assert len(result["results"]) <= 5

@pytest.mark.asyncio
async def test_notion_read_page_dry_run():
    """Test dry-run mode returns mock data."""
    tool = NotionReadPageTool(api_key="fake_key")

    result = await tool.execute(
        ctx={},
        input_data={"page_id": "abc123", "dry_run": True}
    )

    assert result["status"] == "dry_run"
    assert "would_execute" in result
```

### Integration Tests (Optional, requires real Notion workspace)

```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("NOTION_API_KEY"), reason="No Notion API key")
async def test_real_notion_search():
    """Integration test with real Notion API."""
    tool = NotionSearchTool(api_key=os.getenv("NOTION_API_KEY"))
    result = await tool.execute(ctx={}, input_data={"query": "test"})
    assert "results" in result
```

---

## Tool Registration

### Registering Notion Tools

```python
# chad_tools/adapters/notion/__init__.py

from chad_tools.registry import ToolRegistry
from .tools.search import NotionSearchTool
from .tools.read_page import NotionReadPageTool
from .tools.create_page import NotionCreatePageTool
from .tools.query_database import NotionQueryDatabaseTool
from .tools.create_database_entry import NotionCreateDatabaseEntryTool

def register_notion_tools(registry: ToolRegistry, api_key: str) -> None:
    """Register all Notion tools with the tool registry."""
    registry.register(NotionSearchTool(api_key=api_key))
    registry.register(NotionReadPageTool(api_key=api_key))
    registry.register(NotionCreatePageTool(api_key=api_key))
    registry.register(NotionQueryDatabaseTool(api_key=api_key))
    registry.register(NotionCreateDatabaseEntryTool(api_key=api_key))
```

---

## Usage Example

### Agent Workflow with Notion

```python
# Example: Chad searches Notion, reads a page, creates summary

# 1. Search for relevant knowledge
search_result = await notion_search_tool.execute(
    ctx={"actor": "n8n_workflow_123"},
    input_data={"query": "API authentication best practices", "max_results": 5}
)

# 2. Read the top result
page_id = search_result["results"][0]["id"]
page_content = await notion_read_page_tool.execute(
    ctx={"actor": "n8n_workflow_123"},
    input_data={"page_id": page_id}
)

# 3. Process content with LLM (TODO: implement)
summary = await llm_summarize(page_content["markdown"])

# 4. Create new page with summary (L1 autonomy - requires approval)
create_result = await notion_create_page_tool.execute(
    ctx={"actor": "n8n_workflow_123"},
    input_data={
        "parent_id": "workspace_root",
        "title": "Summary: API Authentication Best Practices",
        "content_markdown": summary,
        "dry_run": True  # First generate plan
    }
)

# User approves → Re-execute with dry_run=False
```

---

## Security Considerations

1. **API Key Protection**:
   - Store in environment variables, never commit
   - Use Doppler/1Password in production
   - Rotate keys periodically

2. **Scope Validation**:
   - Check actor has `notion.*` capability before execution
   - Enforce `requires_approval=True` for write operations

3. **Rate Limiting**:
   - Respect Notion's rate limits (3 req/s default)
   - Implement exponential backoff for 429 responses

4. **Data Privacy**:
   - Do not log full Notion page content
   - Sanitize error messages (no page titles in logs)
   - Respect Notion workspace permissions

---

## Performance Optimization

1. **Caching** (Future):
   - Cache search results in Redis (TTL: 5 minutes)
   - Cache page content (TTL: 1 hour)
   - Invalidate on create/update operations

2. **Batch Operations** (Future):
   - Read multiple pages in parallel
   - Batch database queries

3. **Pagination**:
   - Support `has_more` for large result sets
   - Implement cursor-based pagination

---

## Roadmap

### Phase 2.1 - Core Tools (Current)
- [x] Design architecture
- [ ] Install notion-client SDK
- [ ] Implement NotionSearchTool
- [ ] Implement NotionReadPageTool
- [ ] Implement NotionCreatePageTool
- [ ] Create unit tests

### Phase 2.2 - Database Tools
- [ ] Implement NotionQueryDatabaseTool
- [ ] Implement NotionCreateDatabaseEntryTool
- [ ] Add database schema introspection

### Phase 2.3 - Advanced Features
- [ ] Page update tool
- [ ] Block-level operations
- [ ] Rich text formatting
- [ ] File attachment handling

### Phase 2.4 - Optimization
- [ ] Redis caching layer
- [ ] Batch operations
- [ ] Webhook support for real-time updates

---

## Agent Sign-Off

- ✅ Phase 2 - Notion Integration (Design)
- 🔄 Implementation in progress...
