# Chad-Core Context Specification

**Version**: 2.0
**Last Updated**: 2025-11-01
**Owner**: agent-orchestration/context-manager + full-stack-orchestration/security-auditor

---

## 1. Actor Model

### Actor Definition
An **actor** is any entity (human user, n8n workflow, API service) initiating a request to Chad-Core via `/act`. Each actor has:

- **Unique Identifier**: `actor` field in requests (e.g., `user_123`, `n8n_workflow_abc`, `service_chatbot`)
- **Scopes**: Set of capabilities the actor is permitted to use (e.g., `["notion.read", "github.write", "local.summarize"]`)
- **Rate Limit Quota**: Requests per minute (default: 60, stored in Redis)
- **Default Autonomy Level**: L0 (Ask), L1 (Draft), L2 (ExecuteNotify), or L3 (ExecuteSilent)

### Actor Registry (Stub)

```python
# chad_agents/policies/scopes.py (implementation stub)

ACTOR_SCOPES = {
    "admin": ["*"],  # All capabilities
    "n8n_workflow_*": [
        "notion.*", "google.*", "github.read", "outlook.send",
        "local.summarize", "local.markdown_to_pdf"
    ],
    "user_*": [
        "local.summarize", "github.read", "notion.read"
    ],
    "anonymous": []  # No capabilities
}

ACTOR_RATE_LIMITS = {
    "admin": 300,  # 300 req/min
    "n8n_workflow_*": 60,
    "user_*": 30,
    "anonymous": 10
}

DEFAULT_AUTONOMY_LEVELS = {
    "admin": "L3_ExecuteSilent",
    "n8n_workflow_*": "L2_ExecuteNotify",
    "user_*": "L1_Draft",
    "anonymous": "L0_Ask"
}
```

---

## 2. Autonomy Levels (L0–L3)

### Enum Definition

```python
# chad_agents/policies/autonomy.py

from enum import Enum

class AutonomyLevel(str, Enum):
    """
    Autonomy levels control execution behavior and approval requirements.

    Design Philosophy:
    - Lower levels (L0, L1): Human-in-the-loop, explicit approval
    - Higher levels (L2, L3): Autonomous execution with varying notification

    Security Considerations:
    - High-risk tools (payments, deletions, external comms) → Force L0/L1
    - Routine tasks (data fetching, summarization) → Allow L2/L3
    - Actor scopes must be validated BEFORE autonomy level assignment
    """

    L0_Ask = "L0_Ask"
    """
    Every tool call requires explicit user approval BEFORE execution.

    Use Cases:
    - Financial transactions (payments, refunds)
    - Destructive operations (deletions, database drops)
    - External communication (emails, SMS, notifications)
    - First-time operations for new actors

    Execution Flow:
    1. Generate plan
    2. Return plan to user with approval UI
    3. User approves each step individually
    4. Execute step
    5. Repeat for each step

    API Response: 200 OK with plan, pending approval
    """

    L1_Draft = "L1_Draft"
    """
    Generate complete plan with DRY-RUN results; present for approval before execution.

    Use Cases:
    - Complex multi-step workflows
    - Operations with dependencies
    - First-time use of new tool combinations
    - Compliance-regulated environments

    Execution Flow:
    1. Generate plan
    2. Execute each step with dry_run=True
    3. Return plan + dry-run results
    4. User approves entire plan
    5. Re-execute with dry_run=False

    API Response: 200 OK with plan + dry-run results
    """

    L2_ExecuteNotify = "L2_ExecuteNotify"
    """
    Execute plan automatically; notify user of results upon completion.

    Use Cases:
    - Routine data fetching (GitHub issues, emails)
    - Summarization and analysis
    - Report generation
    - Scheduled jobs with low risk

    Execution Flow:
    1. Generate plan
    2. Validate with PolicyGuard
    3. Execute all steps
    4. Notify user via webhook/email/UI
    5. Store results for retrieval

    API Response: 202 Accepted (async) or 200 OK (sync)
    """

    L3_ExecuteSilent = "L3_ExecuteSilent"
    """
    Execute without user notification; log to audit trail only.

    Use Cases:
    - Background monitoring
    - Health checks
    - Automated cleanup jobs
    - System-initiated operations

    Execution Flow:
    1. Generate plan
    2. Validate with PolicyGuard
    3. Execute silently
    4. Log to audit trail (Postgres runs table)
    5. No user notification

    API Response: 202 Accepted (queued)

    Security Warning:
    - Only grant L3 to trusted system actors
    - Audit trail is mandatory for compliance
    """
```

### Autonomy Level Determination Logic

```python
# chad_agents/policies/policy_guard.py (stub)

def determine_autonomy_level(
    actor: str,
    plan: Plan,
    context: ExecutionContext
) -> AutonomyLevel:
    """
    Determine autonomy level based on actor, plan risk, and tool metadata.

    Priority Order:
    1. Forced autonomy from request (if actor has override permission)
    2. Tool-level requirements (any tool with requires_approval=True → L0/L1)
    3. Actor default autonomy level
    4. Risk-based heuristics (plan complexity, external API calls)

    TODO: Implement risk scoring algorithm
    - Count external API calls
    - Detect destructive operations (DELETE, DROP, etc.)
    - Check for PII in inputs
    - Evaluate plan complexity (>10 steps → L1)
    """
    # Stub logic
    if any(tool.metadata.requires_approval for tool in plan.tools):
        return AutonomyLevel.L1_Draft

    return AutonomyLevel.L2_ExecuteNotify
```

---

## 3. Idempotency

### Idempotency Key Contract

**Client Responsibility**: Provide unique `idempotency_key` per logical operation.

**Key Format**: Any string (max 256 chars). Recommended: UUID, workflow_id, or `{source}_{timestamp}_{nonce}`.

**Examples**:
- n8n: `n8n_exec_{{$execution.id}}`
- API client: `client_req_550e8400-e29b-41d4-a716-446655440000`
- Scheduled job: `cron_daily_report_2025-11-01`

### Server-Side Handling

```python
# apps/core_api/routers/act.py (stub)

from redis import Redis
from datetime import timedelta

async def handle_idempotency(
    idempotency_key: str,
    redis: Redis
) -> tuple[bool, str | None]:
    """
    Check if request with idempotency_key already processed.

    Returns:
        (is_duplicate, existing_run_id)

    Redis Schema:
        Key: f"idempotency:{idempotency_key}"
        Value: run_id (UUID)
        TTL: REDIS_IDEMPOTENCY_TTL (default 24h)

    Flow:
    1. Check Redis for existing key
    2. If exists → Return (True, run_id) → 409 Conflict
    3. If not exists → Generate new run_id, store in Redis with TTL
    4. Return (False, None) → Proceed with execution

    Race Condition Handling:
    - Use Redis SETNX (SET if Not eXists) for atomic check-and-set
    - If SETNX fails → Another request won the race → Return existing
    """
    # TODO: Implement Redis SETNX logic
    pass
```

### Idempotent Tool Execution

```python
# chad_tools/base.py

from pydantic import BaseModel

class ToolMetadata(BaseModel):
    """
    Tool capability metadata for policy decisions.
    """
    requires_approval: bool = False
    dry_run_supported: bool = False
    idempotent: bool = False  # Safe to retry with same inputs
    capabilities: list[str] = []
    risk_level: str = "low"  # low, medium, high

    class Config:
        frozen = True

# Example: Idempotent tool
class MarkdownToPdfTool:
    metadata = ToolMetadata(
        requires_approval=False,
        dry_run_supported=True,
        idempotent=True,  # Same markdown → same PDF
        capabilities=["local.convert"],
        risk_level="low"
    )

# Example: Non-idempotent tool
class SendEmailTool:
    metadata = ToolMetadata(
        requires_approval=True,
        dry_run_supported=True,
        idempotent=False,  # Each call sends a new email
        capabilities=["outlook.send", "external_api"],
        risk_level="high"
    )
```

---

## 4. Dry-Run Mode

### Dry-Run Flag Contract

**Request-Level Dry-Run**: `POST /act` with `"dry_run": true` in body.

**Tool-Level Dry-Run**: Individual tool input schemas include `dry_run: bool` field.

### Behavior

```python
# chad_agents/graphs/executor.py (stub)

async def execute_tool(
    tool: Tool,
    input_data: dict,
    dry_run: bool = False
) -> dict:
    """
    Execute tool with optional dry-run mode.

    Dry-Run Behavior:
    1. Validate input schema (always)
    2. If dry_run=False:
       - Execute tool.execute(input)
       - Return real output
    3. If dry_run=True:
       - Check tool.metadata.dry_run_supported
       - If supported: Call tool.execute(input, dry_run=True)
       - If not supported: Return mock output with warning

    Mock Output Format:
    {
        "status": "dry_run",
        "simulated_output": {...},
        "warning": "This is a simulated response; no real action taken",
        "would_execute": "POST /api/notion/pages with {title: 'Summary'}"
    }
    """
    if not dry_run:
        return await tool.execute(input_data)

    if tool.metadata.dry_run_supported:
        return await tool.execute(input_data, dry_run=True)
    else:
        # Return mock
        return {
            "status": "dry_run",
            "simulated_output": {"placeholder": "mock_data"},
            "warning": f"Tool {tool.name} does not support dry-run; this is a mock response"
        }
```

### L1_Draft Autonomy + Dry-Run

When autonomy level is `L1_Draft`, ALL tools are executed with `dry_run=True` automatically:

```python
# chad_agents/graphs/graph_langgraph.py (stub)

def execute_with_autonomy(plan: Plan, autonomy: AutonomyLevel):
    """
    Execute plan respecting autonomy level.

    L1_Draft Flow:
    1. Generate plan
    2. Execute each step with dry_run=True (forced)
    3. Collect dry-run results
    4. Return to user for approval
    5. User approves → Re-execute with dry_run=False
    6. User rejects → Cancel execution
    """
    if autonomy == AutonomyLevel.L1_Draft:
        dry_run_results = []
        for step in plan.steps:
            result = await execute_tool(step.tool, step.input, dry_run=True)
            dry_run_results.append(result)

        return {
            "status": "awaiting_approval",
            "plan": plan,
            "dry_run_results": dry_run_results,
            "approve_url": f"/runs/{run_id}/approve"
        }
```

---

## 5. Scopes & Capabilities

### Capability Taxonomy

Capabilities use dot-notation hierarchy:

```
{adapter}.{resource}.{action}
```

Examples:
- `notion.pages.read` - Read Notion pages
- `notion.pages.create` - Create Notion pages
- `github.repos.read` - Read GitHub repositories
- `github.issues.create` - Create GitHub issues
- `local.summarize` - Use local summarization tool
- `*` - Wildcard (admin only)

### Scope Validation

```python
# chad_agents/policies/scopes.py (stub)

def check_scope(actor: str, required_capability: str) -> bool:
    """
    Check if actor has required capability.

    Matching Rules:
    1. Exact match: actor has "notion.pages.create"
    2. Wildcard parent: actor has "notion.*"
    3. Global wildcard: actor has "*"
    4. Pattern match: actor pattern "n8n_workflow_*" matches "n8n_workflow_123"

    TODO: Implement fnmatch or glob-style pattern matching
    """
    actor_scopes = get_actor_scopes(actor)

    # Check exact match
    if required_capability in actor_scopes:
        return True

    # Check wildcard match
    parts = required_capability.split(".")
    for i in range(len(parts)):
        wildcard = ".".join(parts[:i]) + ".*"
        if wildcard in actor_scopes:
            return True

    # Check global wildcard
    if "*" in actor_scopes:
        return True

    return False
```

### Tool Capability Declaration

```python
# chad_tools/adapters/notion.py (stub)

class NotionSearchTool:
    metadata = ToolMetadata(
        capabilities=["notion.pages.read", "notion.search"],
        requires_approval=False,
        risk_level="low"
    )

class NotionCreatePageTool:
    metadata = ToolMetadata(
        capabilities=["notion.pages.create", "notion.write"],
        requires_approval=True,  # Writing requires approval
        risk_level="medium"
    )
```

---

## 6. Rate Limiting

### Rate Limit Strategy

**Storage**: Redis with sliding window counter.

**Key Format**: `rate_limit:{actor}:{window_start}`

**Default Limits**:
- Admin: 300 req/min
- n8n workflows: 60 req/min
- Users: 30 req/min
- Anonymous: 10 req/min

### Implementation Stub

```python
# apps/core_api/middleware.py (stub)

from fastapi import Request, HTTPException
from redis import Redis
import time

async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware using Redis sliding window.

    Algorithm:
    1. Extract actor from JWT token
    2. Get actor rate limit (default 60/min)
    3. Check Redis counter: rate_limit:{actor}:{current_minute}
    4. If count >= limit → 429 Too Many Requests
    5. Increment counter, set TTL=60s
    6. Proceed to handler

    Response Headers:
    - X-RateLimit-Limit: 60
    - X-RateLimit-Remaining: 45
    - X-RateLimit-Reset: 1699123456 (Unix timestamp)

    TODO: Implement Redis sliding window with MULTI/EXEC transaction
    """
    pass
```

---

## 7. Security Context

### Authentication Flow

```
1. n8n workflow generates request payload
2. Compute HMAC-SHA256(payload, HMAC_SECRET_KEY)
3. Generate short-lived JWT (60min) via /auth/token endpoint
4. Attach headers:
   - Authorization: Bearer <JWT>
   - X-HMAC-Signature: <hex_digest>
5. POST /act with payload
6. Chad-Core validates:
   a. JWT signature (python-jose)
   b. JWT expiration
   c. HMAC signature (hashlib.hmac)
   d. Actor scopes
7. If valid → Proceed; If invalid → 401 Unauthorized
```

### HMAC Validation Stub

```python
# apps/core_api/auth.py (stub)

import hmac
import hashlib
from fastapi import HTTPException, Header, Request

async def validate_hmac(
    request: Request,
    x_hmac_signature: str = Header(...)
) -> None:
    """
    Validate HMAC signature of request body.

    Algorithm:
    1. Read raw request body
    2. Compute HMAC-SHA256(body, HMAC_SECRET_KEY)
    3. Compare with x_hmac_signature (constant-time comparison)
    4. If mismatch → 401 Unauthorized

    Security Notes:
    - Use hmac.compare_digest() to prevent timing attacks
    - HMAC_SECRET_KEY must be shared securely with n8n (encrypt in transit)
    - Rotate HMAC_SECRET_KEY periodically
    """
    body = await request.body()
    expected_signature = hmac.new(
        HMAC_SECRET_KEY.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, x_hmac_signature):
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")
```

### JWT Validation Stub

```python
# apps/core_api/auth.py (stub)

from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def validate_jwt(token: str = Depends(security)) -> dict:
    """
    Validate JWT token and extract actor claim.

    JWT Payload:
    {
        "sub": "actor_id",  # Subject (actor identifier)
        "exp": 1699123456,  # Expiration (Unix timestamp)
        "iat": 1699119856,  # Issued at
        "scopes": ["notion.*", "github.read"]  # Optional: embed scopes
    }

    Validation:
    1. Verify signature with JWT_SECRET_KEY
    2. Check expiration (exp > now)
    3. Extract actor from "sub" claim
    4. Return decoded payload

    TODO: Implement token refresh logic
    TODO: Add token revocation list (Redis blacklist)
    """
    try:
        payload = jwt.decode(
            token.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid JWT: {e}")
```

---

## 8. Audit Trail

All executions are logged to Postgres for compliance and debugging.

### Audit Schema

```sql
-- runs table (top-level execution)
CREATE TABLE runs (
    id UUID PRIMARY KEY,
    actor TEXT NOT NULL,
    request_payload JSONB NOT NULL,
    status TEXT NOT NULL,  -- pending, running, completed, failed
    autonomy_level TEXT,
    trace_id TEXT UNIQUE NOT NULL,  -- OpenTelemetry trace ID
    idempotency_key TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

-- tool_calls table (audit trail of tool invocations)
CREATE TABLE tool_calls (
    id UUID PRIMARY KEY,
    step_id UUID REFERENCES steps(id),
    tool_name TEXT NOT NULL,
    tool_input JSONB NOT NULL,
    tool_output JSONB,
    error TEXT,
    duration_ms INT,
    dry_run BOOLEAN DEFAULT FALSE,
    idempotency_key TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for audit queries
CREATE INDEX idx_tool_calls_actor_time ON tool_calls(actor, created_at DESC);
CREATE INDEX idx_runs_trace_id ON runs(trace_id);
```

### Audit Query Examples

```sql
-- All actions by actor in last 24h
SELECT r.id, r.actor, r.status, tc.tool_name, tc.created_at
FROM runs r
JOIN steps s ON s.run_id = r.id
JOIN tool_calls tc ON tc.step_id = s.id
WHERE r.actor = 'n8n_workflow_123'
  AND r.created_at > NOW() - INTERVAL '24 hours'
ORDER BY tc.created_at DESC;

-- Failed executions for debugging
SELECT r.id, r.actor, r.error_message, r.trace_id
FROM runs r
WHERE r.status = 'failed'
  AND r.created_at > NOW() - INTERVAL '7 days'
ORDER BY r.created_at DESC;
```

---

## 9. Context Propagation (OpenTelemetry)

### Trace Context Injection

Every request generates a `trace_id` that propagates through all systems:

```python
# chad_obs/tracing.py (stub)

from opentelemetry import trace
from opentelemetry.trace import SpanKind

def create_execution_span(run_id: str, actor: str):
    """
    Create root span for execution.

    Span Attributes:
    - run_id: UUID
    - actor: Actor identifier
    - autonomy_level: L0/L1/L2/L3
    - idempotency_key: If provided

    Context Propagation:
    1. FastAPI auto-instruments incoming request → Root span
    2. LangGraph creates child spans per step
    3. Tool executions create grandchild spans
    4. httpx auto-instruments outbound HTTP calls
    5. SQLAlchemy auto-instruments DB queries
    6. Redis auto-instruments cache operations

    Result: Complete trace from /act request → final tool execution
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(
        "agent_execution",
        kind=SpanKind.SERVER,
        attributes={
            "run_id": run_id,
            "actor": actor
        }
    ) as span:
        # Execution happens within this span context
        pass
```

---

## 10. Rollback Context

### Compensating Actions

Tools should implement rollback methods when possible:

```python
# chad_tools/base.py (stub)

class Tool(Protocol):
    """
    Tool interface with optional rollback support.
    """

    async def execute(self, ctx: ExecutionContext, input: BaseModel) -> BaseModel:
        """Execute tool action."""
        pass

    async def rollback(self, ctx: ExecutionContext, execution_result: dict) -> None:
        """
        Optional: Compensating action to undo execute().

        Example:
        - create_page.execute() → create_page.rollback() deletes page
        - send_email.execute() → No rollback (email already sent)

        Rollback is best-effort; not all actions are reversible.
        """
        raise NotImplementedError(f"{self.name} does not support rollback")
```

### Rollback Procedure (Manual)

1. Identify failed run: `GET /runs?status=failed`
2. Review audit trail: `GET /runs/{id}/steps`
3. Identify successful tool calls before failure
4. Manually invoke compensating actions
5. Update run status: `PATCH /runs/{id}` with `{"status": "rolled_back"}`

**Future Enhancement**: Automatic rollback via `/runs/{id}/rollback` endpoint.

---

## Summary

This context specification defines:

1. **Actors**: Identity, scopes, rate limits, default autonomy
2. **Autonomy Levels**: L0 (Ask) → L3 (Silent) with clear use cases
3. **Idempotency**: Client-provided keys, Redis-backed deduplication
4. **Dry-Run**: Tool-level simulation, L1 Draft integration
5. **Scopes**: Dot-notation capability hierarchy with wildcard matching
6. **Rate Limiting**: Redis sliding window per actor
7. **Security**: HMAC + JWT dual authentication, scope validation
8. **Audit Trail**: Postgres-backed compliance logging
9. **Tracing**: OpenTelemetry context propagation
10. **Rollback**: Compensating actions with audit trail

All stubs marked with `TODO` for implementation.

---

**Agent Sign-Off**:
- ✅ agent-orchestration/context-manager
- ✅ full-stack-orchestration/security-auditor
