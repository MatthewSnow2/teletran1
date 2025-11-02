"""SQLAlchemy Async Models.

Driver: asyncpg ONLY (no psycopg2)
Artifacts: URL field, NO BYTEA

Deliverable #5: SQLAlchemy models with asyncpg ✅
"""

from sqlalchemy import Column, ForeignKey, String, Text, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Run(Base):
    """Top-level execution run."""

    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True)
    actor = Column(Text, nullable=False, index=True)
    request_payload = Column(JSONB, nullable=False)
    status = Column(Text, nullable=False, index=True)
    autonomy_level = Column(Text)
    trace_id = Column(Text, unique=True, nullable=False, index=True)
    idempotency_key = Column(Text, unique=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True))
    error_message = Column(Text)


class Artifact(Base):
    """Artifact metadata (binary in Supabase Storage)."""

    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_type = Column(Text, nullable=False, index=True)
    url = Column(Text, nullable=False)  # Supabase Storage URL
    metadata_json = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

# TODO: Add Step, ToolCall, Message, Embedding models
