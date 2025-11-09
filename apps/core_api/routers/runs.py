"""
/runs Router - Run Viewer API.

Endpoints:
- GET /runs: List runs for actor
- GET /runs/{id}: Get run details
- GET /runs/{id}/steps: Get step timeline

Agent: api-scaffolding/fastapi-pro
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.core_api.deps import get_current_user
from apps.core_api.auth import User

router = APIRouter()


class RunListResponse(BaseModel):
    """List of runs."""

    runs: list[dict]
    total: int
    limit: int
    offset: int


class RunDetailResponse(BaseModel):
    """Single run details."""

    id: str
    actor: str
    status: str
    autonomy_level: str | None
    trace_id: str
    plan: dict | None
    artifacts: list[dict]
    created_at: str
    completed_at: str | None


@router.get("", response_model=RunListResponse)
async def list_runs(
    user: User = Depends(get_current_user),
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List runs for authenticated actor.

    TODO: Implement Postgres query
    TODO: Add filtering (status, date range)
    TODO: Add pagination
    """
    # Stub
    return RunListResponse(runs=[], total=0, limit=limit, offset=offset)


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(run_id: str, user: User = Depends(get_current_user)):
    """
    Get run details.

    TODO: Implement Postgres query
    TODO: Check actor owns run
    """
    # Stub
    raise HTTPException(404, "Run not found (stub)")


@router.get("/{run_id}/steps")
async def get_run_steps(run_id: str, user: User = Depends(get_current_user)):
    """
    Get detailed step timeline.

    TODO: Implement with joins (runs → steps → tool_calls)
    """
    return {"run_id": run_id, "steps": []}
