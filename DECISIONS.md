# Chad-Core: Design Decisions (Locked for Phase 3A–3F)

**Date**: 2025-11-04
**Status**: Locked
**Valid Through**: Phase 3A–3F implementation

---

## Integration Strategy

**Decision**: HTTP-only approach (simplified)

### Chad Architecture
- **Standalone HTTP service** (FastAPI + LangGraph)
- **All integrations via HTTP APIs**:
  - Notion: REST API (official SDK)
  - n8n: Webhook endpoints
  - Future tools: HTTP APIs
- **No MCP runtime dependency**
- Workflows documented in Notion
- Chad reads docs → calls HTTP endpoints

### Development Workflow
- Claude Code helps build/test Chad
- Chad itself uses HTTP-only integrations
- Simple, focused architecture

### Deployment
- Cloud server (likely) or home server
- Private access only (via ChatGPT Custom GPT)
- Self-contained Python service

**Rationale**:
- Simpler architecture (one integration pattern)
- Clear separation: ChatGPT talks to Chad, Chad talks to services
- No confusion about when/how MCP is involved
- Easy deployment anywhere
- Can always add MCP layer later if needed

---

## Workflow Documentation

**Phase 1 (Now)**: Individual Notion pages
- Standard template for consistency
- Easy to create and maintain
- Flexible markdown format

**Phase 2 (At >10 workflows)**: Notion Database
- Structured properties
- Queryable by Chad
- Better organization at scale

**Template Structure**:
```markdown
# n8n Workflow: [Name]

**Workflow ID**: `workflow_[id]`
**Webhook URL**: `https://...`

## Purpose
[What it does]

## Input Parameters
- param1 (type): description
- param2 (type): description

## Example Request
[JSON example]

## Expected Response
[JSON example]

## Error Handling
[Error codes and retry logic]

## Tags
#n8n-workflow #category
```

---

## Notifications (L2 Autonomy)

**Decision**: Single n8n webhook endpoint

**Flow**:
```
Chad completes task
    ↓
POST to n8n webhook
    ↓
n8n fans out to:
    - Slack (#notifications)
    - Email (matthew@...)
    - Other channels as needed
```

**Benefits**:
- Single integration point in Chad
- Flexible routing in n8n
- Easy to add new notification channels
- Centralized notification logic

---

## Secrets / Environment Variables

### Required API Keys (Present in .env)
```bash
# LLM APIs
OPENAI_API_KEY=sk-...              # ChatGPT-5/GPT-4
ANTHROPIC_API_KEY=sk-ant-...       # Claude

# Notion
NOTION_API_KEY=ntn_...             # Knowledge base

# Authentication
JWT_SECRET_KEY=...                 # 64-char secure key
HMAC_SECRET_KEY=...                # 64-char secure key

# Infrastructure
REDIS_URL=redis://localhost:6379   # Working memory
DATABASE_URL=postgresql+asyncpg://... # Supabase (future)
```

### .env.sample for DX
Create `.env.sample` with placeholder values and comments for developer experience.

---

## Implementation Order (Locked)

### Phase 3A: LLM Integration (2-3 hours)
- Install `openai`, `anthropic` SDKs
- Implement `OpenAIClient` (ChatGPT-5/GPT-4)
- Implement `AnthropicClient` (Claude)
- Implement `LLMRouter` with task-based routing
- Add token tracking and retry logic
- **Start immediately**

### Phase 3B: LangGraph Nodes (3-4 hours)
- Define `AgentState` TypedDict
- Implement 5 nodes: initialize, plan, execute, reflect, finalize
- Add routing functions
- Create graph compiler
- Error handling

### Phase 3C: Redis Working Memory (1-2 hours)
- Implement `WorkingMemoryStore`
- State persistence methods
- LLM call tracking
- Context retrieval

### Phase 3D: API Integration (1-2 hours)
- Connect `/act` endpoint to LangGraph
- Async execution queue
- Idempotency checking
- L2 notification to n8n webhook

### Phase 3E: E2E Testing (2-3 hours)
- End-to-end knowledge organization test
- Real Notion workspace validation
- LLM call validation
- Error handling tests
- Performance testing

### Phase 3F: n8n Workflow Adapter (2-3 hours)
- Create `N8nWorkflowTool`
- Notion documentation parser
- Webhook calling logic
- Async polling for long-running workflows
- Create workflow documentation template

---

## Technical Constraints

### LLM Routing Logic
```python
# Task type → LLM mapping
ROUTING_RULES = {
    "plan": "claude",           # Execution planning
    "reflect": "claude",        # Self-evaluation
    "analyze": "claude",        # Technical analysis
    "code": "claude",           # Code generation
    "respond": "chatgpt",       # User-facing responses
    "summarize": "chatgpt",     # Content summarization
    "chat": "chatgpt",          # Conversational
    "explain": "chatgpt"        # Explanations
}
# Default: claude (better reasoning)
```

### Autonomy Level: L2 (ExecuteNotify)
- Execute autonomously (no approval needed)
- Notify on completion via n8n webhook
- User reviews results post-execution

### Rate Limits (Conservative)
- Notion: 3 req/s (existing)
- OpenAI: 3500 tokens/min (tier 1)
- Anthropic: 4000 tokens/min (tier 1)
- n8n webhooks: No limit (internal)

---

## Non-Goals (Out of Scope for Phase 3)

- ❌ Database migration (Supabase Postgres) - Phase 4
- ❌ Production auth (JWT/HMAC full impl) - Phase 4
- ❌ Multiple autonomy levels - L2 only for now
- ❌ Tool approval workflow - All tools auto-approved
- ❌ Custom GPT creation - Post Phase 3
- ❌ GitHub/Slack/Google adapters - Phase 4+

---

## Success Criteria for Phase 3

### Phase 3A
- ✅ Can call OpenAI API (ChatGPT-5/GPT-4)
- ✅ Can call Anthropic API (Claude)
- ✅ LLM router correctly routes by task type
- ✅ Token usage tracked
- ✅ Retries on transient errors

### Phase 3B
- ✅ LangGraph compiles without errors
- ✅ Can execute plan → execute → reflect loop
- ✅ State passes between nodes correctly
- ✅ Routing functions work

### Phase 3C
- ✅ Can save/restore state from Redis
- ✅ Working memory persists across steps
- ✅ LLM calls tracked

### Phase 3D
- ✅ POST /act triggers LangGraph execution
- ✅ Returns 202 Accepted for async
- ✅ Can poll /runs/{run_id} for status
- ✅ L2 notification sent to n8n webhook

### Phase 3E
- ✅ End-to-end test passes
- ✅ Real Notion pages organized
- ✅ Master index created
- ✅ Notification received

### Phase 3F
- ✅ Can call n8n workflow from plan
- ✅ Reads workflow docs from Notion
- ✅ Parses webhook URL correctly
- ✅ Handles workflow errors gracefully

---

## Rollback Plan

If Phase 3 fails:
1. All changes in feature branch
2. Tests still pass on main
3. Can revert to Phase 2 (Notion-only)
4. No production deployment until Phase 3E passes

---

## Approval

**Decisions Locked By**: Matthew Snow
**Date**: 2025-11-04
**Valid Through**: Phase 3F completion
**Review After**: Phase 3F or 2 weeks, whichever comes first

---

**Proceed with Phase 3A immediately.** 🚀
