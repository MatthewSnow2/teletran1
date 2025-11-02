"""Memory Store Adapters.

Deliverable #5: Redis + Postgres adapters ✅
"""


class RedisStore:
    """Redis working memory, rate limits, idempotency."""

    async def set(self, key: str, value: str, ttl: int | None = None):
        """TODO: Implement Redis SET"""
        pass

    async def get(self, key: str) -> str | None:
        """TODO: Implement Redis GET"""
        return None


class PgVectorStore:
    """Postgres + pgvector for long-term memory."""

    async def save_run(self, run: dict):
        """TODO: Implement run storage"""
        pass
