# Chad-Core Makefile
# Agent: deployment-strategies/deployment-engineer

.PHONY: help setup install lint typecheck test run queue-worker migrate docker-up docker-down clean docs

# Default target
.DEFAULT_GOAL := help

# ============================================================================
# HELP
# ============================================================================
help: ## Show this help message
	@echo "Chad-Core - Jarvis-inspired Agentic Service"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# DEVELOPMENT SETUP
# ============================================================================
setup: install ## Complete development setup (install + pre-commit + migrate)
	@echo "✅ Installing pre-commit hooks..."
	pre-commit install
	@echo "✅ Setup complete! Run 'make run' to start the API."

install: ## Install dependencies
	@echo "📦 Installing dependencies..."
	pip install -e ".[dev]"
	@echo "✅ Dependencies installed!"

# ============================================================================
# CODE QUALITY
# ============================================================================
lint: ## Lint and auto-fix code (Ruff + Black)
	@echo "🔍 Running Ruff (autofix enabled)..."
	ruff check --fix .
	@echo "🎨 Running Black (autofix enabled)..."
	black .
	@echo "✅ Linting complete!"

typecheck: ## Run type checking with MyPy
	@echo "🔎 Running MyPy type checker..."
	mypy apps chad_agents chad_tools chad_memory chad_obs chad_config
	@echo "✅ Type checking complete!"

format: lint ## Alias for lint (autofix)

# ============================================================================
# TESTING
# ============================================================================
test: ## Run test suite with coverage
	@echo "🧪 Running tests..."
	pytest
	@echo "✅ Tests complete! Coverage report: htmlcov/index.html"

test-fast: ## Run tests without coverage (faster)
	@echo "🧪 Running fast tests..."
	pytest --no-cov -x
	@echo "✅ Fast tests complete!"

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo "👀 Running tests in watch mode..."
	ptw -- --no-cov

# ============================================================================
# RUNNING SERVICES
# ============================================================================
run: ## Start FastAPI server (dev mode with auto-reload)
	@echo "🚀 Starting Chad-Core API on http://localhost:8000..."
	@echo "📊 Metrics: http://localhost:8000/metrics"
	@echo "❤️  Health: http://localhost:8000/healthz"
	uvicorn apps.core_api.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Start FastAPI server (production mode)
	@echo "🚀 Starting Chad-Core API (production)..."
	uvicorn apps.core_api.main:app \
		--host 0.0.0.0 \
		--port 8000 \
		--workers 4 \
		--log-level info

queue-worker: ## Start queue worker (processes Redis stream)
	@echo "⚙️  Starting queue worker..."
	python -m apps.queue_worker.main

# ============================================================================
# DATABASE MIGRATIONS
# ============================================================================
migrate: ## Run database migrations (alembic upgrade head)
	@echo "🗄️  Running database migrations..."
	alembic upgrade head
	@echo "✅ Migrations complete!"

migrate-create: ## Create new migration (Usage: make migrate-create MSG="description")
	@echo "📝 Creating new migration: $(MSG)"
	alembic revision --autogenerate -m "$(MSG)"

migrate-downgrade: ## Rollback last migration
	@echo "⏪ Rolling back last migration..."
	alembic downgrade -1

migrate-history: ## Show migration history
	@echo "📜 Migration history:"
	alembic history --verbose

# ============================================================================
# DOCKER
# ============================================================================
docker-build: ## Build Docker images
	@echo "🐳 Building Docker images..."
	docker compose -f infra/docker/docker-compose.yml build

docker-up: ## Start all services with Docker Compose
	@echo "🐳 Starting Docker services (API, Worker, Redis, Postgres)..."
	docker compose -f infra/docker/docker-compose.yml up -d
	@echo "✅ Services started!"
	@echo "📡 API: http://localhost:8000"
	@echo "🗄️  Postgres: localhost:5432"
	@echo "💾 Redis: localhost:6379"

docker-down: ## Stop all Docker services
	@echo "🛑 Stopping Docker services..."
	docker compose -f infra/docker/docker-compose.yml down
	@echo "✅ Services stopped!"

docker-logs: ## Show Docker logs (all services)
	docker compose -f infra/docker/docker-compose.yml logs -f

docker-logs-api: ## Show Docker logs (API only)
	docker compose -f infra/docker/docker-compose.yml logs -f api

docker-logs-worker: ## Show Docker logs (queue worker only)
	docker compose -f infra/docker/docker-compose.yml logs -f queue-worker

docker-ps: ## Show running Docker containers
	docker compose -f infra/docker/docker-compose.yml ps

# ============================================================================
# ADAPTERS (HTTP Tool Adapters)
# ============================================================================
adapter-notion: ## Run Notion adapter server
	@echo "🔌 Starting Notion adapter on http://localhost:8001..."
	python chad_tools/adapters/server.py --adapter=notion --port=8001

adapter-google: ## Run Google adapter server
	@echo "🔌 Starting Google adapter on http://localhost:8002..."
	python chad_tools/adapters/server.py --adapter=google --port=8002

adapter-github: ## Run GitHub adapter server
	@echo "🔌 Starting GitHub adapter on http://localhost:8003..."
	python chad_tools/adapters/server.py --adapter=github --port=8003

# ============================================================================
# UTILITIES
# ============================================================================
clean: ## Clean cache and build artifacts
	@echo "🧹 Cleaning cache and build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage build dist
	@echo "✅ Cleanup complete!"

shell: ## Open Python REPL with project context
	@echo "🐍 Opening Python shell..."
	python -i -c "import sys; sys.path.insert(0, '.'); print('Chad-Core shell ready!')"

db-shell: ## Open Postgres shell (requires running database)
	@echo "🗄️  Opening Postgres shell..."
	psql $$DATABASE_URL

redis-cli: ## Open Redis CLI (requires running Redis)
	@echo "💾 Opening Redis CLI..."
	redis-cli -u $$REDIS_URL

# ============================================================================
# UI (Netlify Deployment)
# ============================================================================
ui-install: ## Install UI dependencies
	@echo "📦 Installing UI dependencies..."
	cd ui && npm install

ui-dev: ## Start UI dev server
	@echo "🎨 Starting UI dev server on http://localhost:5173..."
	cd ui && npm run dev

ui-build: ## Build UI for production
	@echo "🏗️  Building UI for production..."
	cd ui && npm run build

ui-preview: ## Preview production UI build
	@echo "👀 Previewing production UI..."
	cd ui && npm run preview

# ============================================================================
# DEPLOYMENT
# ============================================================================
deploy-check: lint typecheck test ## Pre-deployment checks (lint + typecheck + test)
	@echo "✅ All pre-deployment checks passed!"

# ============================================================================
# MONITORING
# ============================================================================
metrics: ## Open Prometheus metrics endpoint
	@echo "📊 Fetching metrics from http://localhost:8000/metrics..."
	curl http://localhost:8000/metrics

health: ## Check API health
	@echo "❤️  Checking API health..."
	@curl -s http://localhost:8000/healthz | jq . || echo "API not running or jq not installed"

ready: ## Check API readiness (DB + Redis + Queue)
	@echo "🔍 Checking API readiness..."
	@curl -s http://localhost:8000/readyz | jq . || echo "API not running or jq not installed"

# ============================================================================
# DOCUMENTATION
# ============================================================================
docs: ## Generate documentation (placeholder)
	@echo "📚 Generating documentation..."
	@echo "TODO: Add Sphinx or MkDocs setup"

# ============================================================================
# AGENT SIGN-OFF
# ============================================================================
# ✅ deployment-strategies/deployment-engineer
# ✅ tdd-workflows/tdd-orchestrator
