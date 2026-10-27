"""
SQLAlchemy models for storing normalized AMR consensus payloads.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from backend.pipeline.schemas import AMRResultPayload


class Base(DeclarativeBase):
    pass


class AMRSampleResult(Base):
    """One row per processed isolate / sample."""

    __tablename__ = "amr_sample_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status_summary: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resistant_classes: Mapped[int] = mapped_column(Integer, default=0)
    ambiguous_classes: Mapped[int] = mapped_column(Integer, default=0)
    # Full API payload (consensus_summary + tool_breakdown)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    work_dir: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def get_engine(database_url: Optional[str] = None):
    url = database_url or os.environ.get("AMR_DATABASE_URL", "sqlite:///./amr_results.db")
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)


def get_session_factory(database_url: Optional[str] = None) -> sessionmaker[Session]:
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def persist_amr_result(
    session: Session,
    payload: AMRResultPayload,
    work_dir: Optional[str] = None,
) -> AMRSampleResult:
    """Store consensus payload and return the ORM row."""
    import json

    data = payload.to_api_dict()
    resistant = sum(1 for c in payload.consensus_summary if c.status.value == "RESISTANT")
    ambiguous = sum(
        1 for c in payload.consensus_summary if c.status.value == "AMBIGUOUS / SUSPECTED"
    )
    if resistant:
        status = "RESISTANT"
    elif ambiguous:
        status = "AMBIGUOUS / SUSPECTED"
    else:
        status = "SUSCEPTIBLE"

    row = AMRSampleResult(
        sample_id=payload.sample_id,
        processed_at=payload.processed_at,
        status_summary=status,
        resistant_classes=resistant,
        ambiguous_classes=ambiguous,
        payload_json=json.dumps(data),
        work_dir=work_dir,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def fetch_latest_payload(session: Session, sample_id: str) -> Optional[dict[str, Any]]:
    import json

    stmt = (
        select(AMRSampleResult)
        .where(AMRSampleResult.sample_id == sample_id)
        .order_by(AMRSampleResult.processed_at.desc())
        .limit(1)
    )
    row = session.scalars(stmt).first()
    if not row:
        return None
    return json.loads(row.payload_json)
