"""Memory Store Adapters.

Redis-backed working memory for agent execution state persistence.
"""

import json
from typing import Any
from datetime import timedelta

from redis import asyncio as aioredis


# ============================================================================
# REDIS WORKING MEMORY STORE
# ============================================================================


class RedisStore:
    """Redis working memory for agent execution.

    Stores:
    - Agent state (plan, current step, working memory)
    - Step results (tool outputs)
    - LLM call tracking (model used, tokens, cost)
    - Final results

    Key Structure:
    - run:{run_id}:state → AgentState (JSON)
    - run:{run_id}:step:{step_number} → StepResult (JSON)
    - run:{run_id}:final → FinalResult (JSON)
    - run:{run_id}:llm_calls → List of LLM call records
    """

    def __init__(self, redis_url: str, default_ttl: int = 86400):
        """Initialize Redis store.

        Args:
            redis_url: Redis connection URL (redis://localhost:6379/0)
            default_ttl: Default TTL in seconds (24 hours)
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._client is None:
            self._client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> aioredis.Redis:
        """Get Redis client.

        Raises:
            RuntimeError: If not connected
        """
        if self._client is None:
            raise RuntimeError("RedisStore not connected. Call connect() first.")
        return self._client

    # ------------------------------------------------------------------------
    # BASIC OPERATIONS
    # ------------------------------------------------------------------------

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None
    ) -> None:
        """Set key-value pair with optional TTL.

        Args:
            key: Redis key
            value: Value to store
            ttl: Time-to-live in seconds (default: 24 hours)
        """
        ttl = ttl or self.default_ttl
        await self.client.set(key, value, ex=ttl)

    async def get(self, key: str) -> str | None:
        """Get value by key.

        Args:
            key: Redis key

        Returns:
            Value or None if not found
        """
        return await self.client.get(key)

    async def delete(self, key: str) -> None:
        """Delete key.

        Args:
            key: Redis key
        """
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Redis key

        Returns:
            True if key exists
        """
        return bool(await self.client.exists(key))

    async def expire(self, key: str, ttl: int) -> None:
        """Set TTL on existing key.

        Args:
            key: Redis key
            ttl: Time-to-live in seconds
        """
        await self.client.expire(key, ttl)

    # ------------------------------------------------------------------------
    # AGENT STATE OPERATIONS
    # ------------------------------------------------------------------------

    async def save_state(
        self,
        run_id: str,
        state: dict[str, Any],
        ttl: int | None = None
    ) -> None:
        """Save agent state.

        Args:
            run_id: Run identifier
            state: Agent state dict
            ttl: Optional TTL override
        """
        key = f"run:{run_id}:state"
        value = json.dumps(state)
        await self.set(key, value, ttl=ttl)

    async def get_state(self, run_id: str) -> dict[str, Any] | None:
        """Get agent state.

        Args:
            run_id: Run identifier

        Returns:
            Agent state or None if not found
        """
        key = f"run:{run_id}:state"
        value = await self.get(key)

        if value:
            return json.loads(value)
        return None

    async def update_state(
        self,
        run_id: str,
        updates: dict[str, Any]
    ) -> None:
        """Update specific fields in agent state.

        Args:
            run_id: Run identifier
            updates: Dict of fields to update
        """
        state = await self.get_state(run_id)

        if state:
            state.update(updates)
            await self.save_state(run_id, state)

    # ------------------------------------------------------------------------
    # STEP RESULT OPERATIONS
    # ------------------------------------------------------------------------

    async def save_step_result(
        self,
        run_id: str,
        step_number: int,
        result: dict[str, Any],
        ttl: int | None = None
    ) -> None:
        """Save step execution result.

        Args:
            run_id: Run identifier
            step_number: Step number (1-indexed)
            result: Step result dict
            ttl: Optional TTL override
        """
        key = f"run:{run_id}:step:{step_number}"
        value = json.dumps(result)
        await self.set(key, value, ttl=ttl)

    async def get_step_result(
        self,
        run_id: str,
        step_number: int
    ) -> dict[str, Any] | None:
        """Get step execution result.

        Args:
            run_id: Run identifier
            step_number: Step number (1-indexed)

        Returns:
            Step result or None if not found
        """
        key = f"run:{run_id}:step:{step_number}"
        value = await self.get(key)

        if value:
            return json.loads(value)
        return None

    async def get_all_step_results(
        self,
        run_id: str
    ) -> list[dict[str, Any]]:
        """Get all step results for a run.

        Args:
            run_id: Run identifier

        Returns:
            List of step results in order
        """
        # Find all step keys
        pattern = f"run:{run_id}:step:*"
        keys = await self.client.keys(pattern)

        if not keys:
            return []

        # Sort keys by step number
        sorted_keys = sorted(keys, key=lambda k: int(k.split(":")[-1]))

        # Get all results
        results = []
        for key in sorted_keys:
            value = await self.get(key)
            if value:
                results.append(json.loads(value))

        return results

    # ------------------------------------------------------------------------
    # FINAL RESULT OPERATIONS
    # ------------------------------------------------------------------------

    async def save_final_result(
        self,
        run_id: str,
        result: dict[str, Any],
        ttl: int | None = None
    ) -> None:
        """Save final workflow result.

        Args:
            run_id: Run identifier
            result: Final result dict
            ttl: Optional TTL override (default: 7 days for final results)
        """
        key = f"run:{run_id}:final"
        value = json.dumps(result)
        # Final results get 7 day TTL by default
        ttl = ttl or (self.default_ttl * 7)
        await self.set(key, value, ttl=ttl)

    async def get_final_result(
        self,
        run_id: str
    ) -> dict[str, Any] | None:
        """Get final workflow result.

        Args:
            run_id: Run identifier

        Returns:
            Final result or None if not found
        """
        key = f"run:{run_id}:final"
        value = await self.get(key)

        if value:
            return json.loads(value)
        return None

    # ------------------------------------------------------------------------
    # LLM CALL TRACKING
    # ------------------------------------------------------------------------

    async def track_llm_call(
        self,
        run_id: str,
        model: str,
        task_type: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0
    ) -> None:
        """Track LLM API call.

        Args:
            run_id: Run identifier
            model: Model used (gpt-4o, claude-3-5-sonnet-20241022)
            task_type: Task type (planning, reflection, user_response)
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            cost: Estimated cost in USD
        """
        key = f"run:{run_id}:llm_calls"

        call_record = {
            "model": model,
            "task_type": task_type,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost": cost,
            "timestamp": None,  # Redis doesn't store timestamps in lists
        }

        # Append to list
        await self.client.rpush(key, json.dumps(call_record))
        # Set TTL on first call
        await self.expire(key, self.default_ttl)

    async def get_llm_calls(self, run_id: str) -> list[dict[str, Any]]:
        """Get all LLM calls for a run.

        Args:
            run_id: Run identifier

        Returns:
            List of LLM call records
        """
        key = f"run:{run_id}:llm_calls"
        records = await self.client.lrange(key, 0, -1)

        return [json.loads(record) for record in records]

    async def get_llm_usage_summary(self, run_id: str) -> dict[str, Any]:
        """Get LLM usage summary for a run.

        Args:
            run_id: Run identifier

        Returns:
            Summary dict with total tokens and cost
        """
        calls = await self.get_llm_calls(run_id)

        if not calls:
            return {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "by_model": {},
            }

        total_tokens = sum(c["total_tokens"] for c in calls)
        total_cost = sum(c["cost"] for c in calls)

        # Group by model
        by_model: dict[str, Any] = {}
        for call in calls:
            model = call["model"]
            if model not in by_model:
                by_model[model] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0.0,
                }
            by_model[model]["calls"] += 1
            by_model[model]["tokens"] += call["total_tokens"]
            by_model[model]["cost"] += call["cost"]

        return {
            "total_calls": len(calls),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "by_model": by_model,
        }

    # ------------------------------------------------------------------------
    # CLEANUP OPERATIONS
    # ------------------------------------------------------------------------

    async def delete_run(self, run_id: str) -> int:
        """Delete all data for a run.

        Args:
            run_id: Run identifier

        Returns:
            Number of keys deleted
        """
        pattern = f"run:{run_id}:*"
        keys = await self.client.keys(pattern)

        if keys:
            return await self.client.delete(*keys)
        return 0

    async def get_run_keys(self, run_id: str) -> list[str]:
        """Get all Redis keys for a run.

        Args:
            run_id: Run identifier

        Returns:
            List of Redis keys
        """
        pattern = f"run:{run_id}:*"
        return await self.client.keys(pattern)

    # ------------------------------------------------------------------------
    # BATCH OPERATIONS
    # ------------------------------------------------------------------------

    async def get_all_run_ids(self) -> list[str]:
        """Get all run IDs in Redis.

        Returns:
            List of run IDs
        """
        pattern = "run:*:state"
        keys = await self.client.keys(pattern)

        # Extract run IDs from keys
        run_ids = [key.split(":")[1] for key in keys]
        return run_ids

    async def cleanup_expired_runs(self, max_age_hours: int = 168) -> int:
        """Clean up runs older than max_age.

        Args:
            max_age_hours: Maximum age in hours (default: 7 days)

        Returns:
            Number of runs deleted
        """
        # This is a simple implementation
        # In production, use Redis key expiration or separate metadata
        run_ids = await self.get_all_run_ids()
        deleted = 0

        for run_id in run_ids:
            # Check if run has final result (completed)
            final = await self.get_final_result(run_id)
            if final and final.get("status") in ["completed", "failed"]:
                # Could check timestamp here
                # For now, just delete completed runs
                await self.delete_run(run_id)
                deleted += 1

        return deleted


# ============================================================================
# POSTGRES + PGVECTOR STORE (STUB)
# ============================================================================


class PgVectorStore:
    """Postgres + pgvector for long-term memory and embeddings.

    Stores:
    - Completed run history
    - Conversation embeddings for semantic search
    - Tool usage analytics
    - User preferences

    TODO: Implement in Phase 4
    """

    async def save_run(self, run: dict):
        """Save completed run to Postgres.

        TODO: Implement Postgres storage
        """
        pass

    async def search_similar_runs(
        self,
        query_embedding: list[float],
        limit: int = 10
    ) -> list[dict]:
        """Search for similar runs using pgvector.

        TODO: Implement vector similarity search
        """
        return []


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


async def create_redis_store(redis_url: str) -> RedisStore:
    """Create and connect Redis store.

    Args:
        redis_url: Redis connection URL

    Returns:
        Connected RedisStore
    """
    store = RedisStore(redis_url)
    await store.connect()
    return store


async def create_pg_vector_store(database_url: str) -> PgVectorStore:
    """Create Postgres vector store.

    Args:
        database_url: Database connection URL

    Returns:
        PgVectorStore (stub)

    TODO: Implement Postgres connection
    """
    return PgVectorStore()
