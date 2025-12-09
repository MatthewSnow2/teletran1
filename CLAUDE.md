# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chad-Core is a hybrid agentic service with LangGraph orchestration, policy-driven execution (L0-L3 autonomy levels), and tool adapters. It uses a dual-LLM architecture (OpenAI for conversational, Anthropic Claude for technical planning/reasoning).

## Build & Run Commands

```bash
# Setup
make setup              # Install deps + pre-commit hooks
pip install -e ".[dev]" # Manual install

# Run services
make run                # API server (dev mode, port 8000)
make queue-worker       # Background worker (Redis streams)
make docker-up          # Start all services via Docker Compose

# Database
make migrate            # Run Alembic migrations
make migrate-create MSG="description"  # New migration

# Quality
make lint               # Ruff + Black autofix
make typecheck          # MyPy strict mode
make test               # Pytest with coverage (70% minimum)
make test-fast          # Quick tests without coverage

# Run single test
pytest tests/test_api.py::test_act_endpoint -v
pytest -k "test_policy"  # Pattern matching
```

## Architecture

```
chad-core/
├── apps/
│   ├── core_api/        # FastAPI application
│   │   ├── main.py      # App entry point, middleware setup
│   │   ├── routers/     # API endpoints (/act, /runs, /health, /metrics)
│   │   ├── auth.py      # JWT + HMAC authentication
│   │   └── deps.py      # Dependency injection
│   └── queue_worker/    # Redis Streams background processor
├── chad_agents/
│   ├── graphs/          # LangGraph execution engine (plan → execute → reflect)
│   ├── policies/        # Autonomy levels (L0-L3), policy guard, scope validation
│   └── reflex/          # Fast routing (rules or SLM-based intent classification)
├── chad_llm/            # LLM client wrappers and router
│   ├── router.py        # Routes to OpenAI (conversational) or Claude (technical)
│   ├── openai_client.py
│   └── anthropic_client.py
├── chad_tools/
│   ├── registry.py      # Tool registration and capability filtering
│   ├── base.py          # Tool base class
│   └── adapters/        # HTTP adapters (Notion, GitHub, Google, Slack, n8n)
├── chad_memory/
│   ├── database.py      # SQLAlchemy async session
│   ├── models.py        # SQLAlchemy ORM models (runs, artifacts, embeddings)
│   └── stores.py        # Redis working memory, state persistence
├── chad_obs/            # Observability (OTel tracing, Prometheus metrics, structlog)
└── chad_config/
    └── settings.py      # Pydantic Settings (env var loading)
```

## Key Patterns

**Request Flow**: POST /act → Auth (JWT+HMAC) → PolicyGuard → Reflex Router → LangGraph → Tool Execution

**Autonomy Levels**:
- L0 (Ask): Approval before each tool call
- L1 (Draft): Plan with dry-run, await approval
- L2 (ExecuteNotify): Auto-execute, notify results
- L3 (ExecuteSilent): Silent execution, audit only

**Database**: Async only with `postgresql+asyncpg://` driver (no psycopg2). Uses Supabase Postgres with pgvector for embeddings.

**Artifacts**: Binary data stored in Cloudflare R2/Supabase Storage, metadata in Postgres (no BYTEA columns).

## Testing

All tests use mocks - no real API calls or database connections. Tests are in `tests/` directory. Coverage must stay above 70%.

```bash
# Run with markers
pytest -m "not slow"           # Skip slow tests
pytest -m "not integration"    # Skip integration tests
```

## Environment

Copy `.env.example` to `.env`. Key variables:
- `DATABASE_URL`: Must use `postgresql+asyncpg://` prefix
- `REDIS_URL`: For working memory, queues, rate limits
- `JWT_SECRET_KEY`, `HMAC_SECRET_KEY`: Auth secrets
- `NOTION_API_KEY`, `GITHUB_TOKEN`: Adapter credentials
