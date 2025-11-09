# Quick Start: Database Layer

Fast-track guide to get the database layer up and running.

## Prerequisites

- Postgres 12+ with pgvector extension
- Python 3.11+
- All dependencies installed (`pip install -e .`)

## 5-Minute Setup

### 1. Create Database

```bash
# Connect to Postgres
psql -U postgres

# Create database
CREATE DATABASE chad_core;

# Connect to database
\c chad_core

# Enable pgvector extension
CREATE EXTENSION vector;

# Exit
\q
```

### 2. Configure Database URL

```bash
# Set environment variable
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/chad_core"

# OR add to .env file
echo "DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/chad_core" >> .env
```

### 3. Run Migrations

```bash
cd /workspace/chad-core-database

# Apply migrations
alembic upgrade head

# Verify
alembic current
# Should show: 001 (head)
```

### 4. Test the Implementation

```bash
# Run integration tests
pytest tests/test_memory.py -v -m integration

# Run all tests
pytest tests/test_memory.py -v
```

### 5. Start the API

```bash
# Run the API server
uvicorn apps.core_api.main:app --reload --port 8000

# In another terminal, test endpoints
curl http://localhost:8000/runs -H "Authorization: Bearer test_token"
```

## Quick Test

```python
import asyncio
from uuid import uuid4
from chad_memory.stores import PostgresStore
from chad_memory.database import get_session_factory

async def test_quick():
    # Initialize store
    session_factory = get_session_factory()
    store = PostgresStore(session_factory)

    # Create a run
    run_id = uuid4()
    await store.save_run({
        "id": run_id,
        "actor": "test_user",
        "request_payload": {"goal": "Hello database!"},
        "status": "completed",
        "trace_id": f"trace-{run_id}",
    })

    # Retrieve it
    run = await store.get_run(str(run_id))
    print(f"Run created: {run['id']}")
    print(f"Status: {run['status']}")

# Run test
asyncio.run(test_quick())
```

## Common Commands

```bash
# Check migration status
alembic current

# View migration history
alembic history

# Create new migration (after model changes)
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1

# Reset database (DANGER: drops all data)
alembic downgrade base
alembic upgrade head

# Run specific tests
pytest tests/test_memory.py::test_postgres_store_save_and_get_run -v

# Check database connection
python -c "from chad_memory.database import check_db_connection; import asyncio; print(asyncio.run(check_db_connection()))"
```

## API Endpoints

Once server is running:

```bash
# List runs (requires auth)
curl http://localhost:8000/runs \
  -H "Authorization: Bearer test_token"

# Get specific run
curl http://localhost:8000/runs/{run_id} \
  -H "Authorization: Bearer test_token"

# Get run steps
curl http://localhost:8000/runs/{run_id}/steps \
  -H "Authorization: Bearer test_token"

# Get run stats
curl http://localhost:8000/runs/{run_id}/stats \
  -H "Authorization: Bearer test_token"
```

## Troubleshooting

### Database Connection Failed

```bash
# Check Postgres is running
pg_isready

# Check database exists
psql -U postgres -l | grep chad_core

# Verify DATABASE_URL
echo $DATABASE_URL
```

### pgvector Extension Missing

```sql
-- Connect to database
psql -U postgres -d chad_core

-- Check extensions
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Install if missing
CREATE EXTENSION vector;
```

### Migration Failed

```bash
# Check current state
alembic current

# View pending migrations
alembic history

# Force to specific version
alembic stamp 001

# Try upgrade again
alembic upgrade head
```

### Import Errors

```bash
# Reinstall in development mode
cd /workspace/chad-core-database
pip install -e .

# Verify imports
python -c "from chad_memory.database import get_session_factory; print('OK')"
```

## Next Steps

1. ✅ Database running and migrations applied
2. ✅ Tests passing
3. ✅ API responding

Now you can:
- Integrate with LangGraph agent to persist runs
- Add LLM call tracking in agent execution
- Implement embedding generation for semantic search
- Add monitoring and metrics

## Full Documentation

- **Setup & Usage**: [DATABASE_README.md](DATABASE_README.md)
- **Implementation Details**: [DATABASE_IMPLEMENTATION_SUMMARY.md](DATABASE_IMPLEMENTATION_SUMMARY.md)

## Support

If you encounter issues:
1. Check logs: `tail -f /tmp/chad-core.log`
2. Enable SQL logging: Set `echo=True` in `database.py`
3. Review test output: `pytest tests/test_memory.py -v -s`
4. Check Alembic logs: `alembic history --verbose`

---

**Ready to go!** 🚀
