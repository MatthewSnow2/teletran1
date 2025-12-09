# Chad-Core Blueprint

Project status and phase tracking for the Chad-Core MCP pivot.

## Current Status: Phase 1 & 3 Complete, Phase 2 Deferred

Last updated: 2025-12-08

---

## Phase Overview

### [x] Phase 1: Claude-Only Consolidation
**Goal**: Remove dual-LLM architecture (ChatGPT + Claude) and consolidate to Claude-only.

**Completed**:
- [x] Delete `chad_llm/openai_client.py` and `chad_llm/router.py`
- [x] Update `chad_llm/__init__.py` to export only `AnthropicClient`
- [x] Update `chad_agents/graphs/graph_langgraph.py` to use `AnthropicClient` directly
- [x] Update `apps/core_api/routers/act.py` - change `LLMRouter()` to `AnthropicClient()`
- [x] Update `apps/queue_worker/main.py` - same change
- [x] Remove `openai>=1.10.0` from `pyproject.toml`
- [x] Update `tests/llm/test_llm_clients.py` - remove OpenAI and router tests
- [x] Update `tests/test_agent_loop.py` - use `mock_claude` instead of `mock_llm_router`

**Success Criteria**: All imports work, 13 tests pass.

---

### [ ] Phase 2: MCP Integration (DEFERRED)
**Goal**: Enable Claude to call MCP servers for external tools (GitHub, Google, Slack).

**Status**: Waiting for MCP deployment approach decision.

**Options**:
1. n8n-hosted MCP servers
2. Standalone MCP server processes
3. Anthropic API-level MCP configuration

**When Ready**:
- [ ] Create `chad_tools/mcp_executor.py`
- [ ] Add MCP server URL settings to `chad_config/settings.py`
- [ ] Update `chad_agents/graphs/graph_langgraph.py` execute_tool_node
- [ ] Set `MCP_ENABLED=true`
- [ ] Test MCP tool execution

**Dependencies**: Requires MCP deployment decision.

---

### [x] Phase 3: Adapter Cleanup
**Goal**: Remove HTTP adapters replaced by MCP, keep Notion direct integration.

**Completed**:
- [x] Delete `chad_tools/adapters/github/` directory
- [x] Delete `chad_tools/adapters/google/` directory
- [x] Delete `chad_tools/adapters/slack/` directory
- [x] Delete `chad_tools/adapters/n8n/` directory
- [x] Delete adapter test files (`test_github.py`, `test_google.py`, `test_slack.py`, `test_n8n_adapter.py`)
- [x] Update `apps/core_api/main.py` - remove n8n workflow discovery
- [x] Update `chad_config/settings.py` - remove old adapter URLs, add `MCP_ENABLED`
- [x] Update `chad_tools/adapters/__init__.py` - update documentation

**Success Criteria**: App starts without errors, Notion tools still work.

---

### [x] Phase 4: Verification
**Goal**: Ensure all changes work correctly.

**Completed**:
- [x] Run `ruff check` - no critical errors in modified code
- [x] Verify imports work (`chad_llm`, `chad_agents.graphs`, `chad_tools`)
- [x] Run pytest - 13/13 tests pass

---

## Architecture After Pivot

```
n8n (triggers via webhook)
         │
         ▼ POST /act
┌─────────────────────────────────────────┐
│         Chad-Core API (FastAPI)         │
│  PolicyGuard → Autonomy (L0-L3) → Auth  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│      LangGraph State Machine            │
│  Initialize → Plan → Execute → Reflect  │
│                                         │
│         Claude (Anthropic)              │
│  • All planning & reflection            │
│  • Notifications (no more ChatGPT)      │
│  • Native MCP tool calls (future)       │
└─────────────────────────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐  ┌─────────────────┐
│ Notion │  │   MCP Servers   │
│ Direct │  │ (when enabled)  │
│ Python │  │ GitHub, Google, │
└────────┘  │ Slack, etc.     │
            └─────────────────┘
```

---

## What Stays Valuable

- **LangGraph plan→execute→reflect loop** - Autonomous multi-step execution
- **Autonomy levels L0-L3** - Policy-driven execution control
- **Notion direct integration** - Knowledge base and tracking
- **Observable execution** - OTel tracing, Prometheus metrics, structlog
- **Redis working memory** - State persistence
- **FastAPI orchestration API** - `/act` endpoint

---

## Files Deleted (Summary)

| Category | Files Removed |
|----------|---------------|
| LLM | `openai_client.py`, `router.py` |
| Adapters | `github/*`, `google/*`, `slack/*`, `n8n/*` (~25 files) |
| Tests | `test_github.py`, `test_google.py`, `test_slack.py`, `test_n8n_adapter.py` |
| **Total** | ~31 files |

---

## Key Files Modified

| File | Change |
|------|--------|
| `chad_llm/__init__.py` | Export only `AnthropicClient` |
| `chad_agents/graphs/graph_langgraph.py` | Use `claude: AnthropicClient` instead of `llm_router: LLMRouter` |
| `apps/core_api/routers/act.py` | Initialize `AnthropicClient()` directly |
| `apps/queue_worker/main.py` | Same change |
| `apps/core_api/main.py` | Remove n8n workflow discovery |
| `chad_config/settings.py` | Add `MCP_ENABLED`, remove old adapter URLs |
| `pyproject.toml` | Remove `openai>=1.10.0` |

---

## Next Steps (When Resuming)

1. **If continuing with MCP**: Determine deployment approach, then implement Phase 2
2. **If testing the API**: Run `make run` and test `/act` endpoint
3. **If adding new tools**: Add to Notion adapter or wait for MCP

---

## Notes

- Coverage dropped below 70% threshold due to deleted code - expected behavior
- Python 3.14 shows Pydantic V1 compatibility warnings - cosmetic only
- n8n now triggers Chad-Core (not the reverse) - this is the new architecture
