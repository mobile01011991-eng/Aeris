"""In-memory async AMR analysis jobs with step progress for the UI."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class JobStep:
    id: str
    label: str
    status: str = "pending"  # pending | running | done | failed | skipped
    detail: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "status": self.status,
            "detail": self.detail,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass
class AnalysisJob:
    id: str
    sample_id: str
    status: str = "queued"
    # queued | running | awaiting_organism_confirmation | completed | failed | cancelled
    mode: str = "live"  # live | demo
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    steps: list[JobStep] = field(default_factory=list)
    # Filled in as each tool finishes so a report can be opened mid-run.
    tool_reports: dict[str, Any] = field(default_factory=dict)

    # Species gate
    declared_organism: Optional[str] = None
    detected_organism: Optional[str] = None
    confirmed_organism: Optional[str] = None
    organism_decision: Optional[str] = None  # accept_system | keep_user | cancel | auto_match
    species_report: Optional[dict[str, Any]] = None

    # Resume context for confirm → continue AMR (not always serialized fully)
    input_path: Optional[str] = None
    work_dir: Optional[str] = None
    tools: list[str] = field(default_factory=list)
    dry_run: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _confirm_event: threading.Event = field(default_factory=threading.Event, repr=False)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def set_tool_report(self, tool_key: str, report: dict[str, Any]) -> None:
        with self._lock:
            self.tool_reports[tool_key] = report
            self.touch()

    def set_step(
        self,
        step_id: str,
        status: str,
        detail: str = "",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            for step in self.steps:
                if step.id != step_id:
                    continue
                step.status = status
                if detail:
                    step.detail = detail
                if status == "running" and not step.started_at:
                    step.started_at = now
                if status in {"done", "failed", "skipped"}:
                    step.finished_at = now
                break
            self.touch()

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "job_id": self.id,
                "sample_id": self.sample_id,
                "status": self.status,
                "mode": self.mode,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "error": self.error,
                "steps": [s.to_dict() for s in self.steps],
                "tool_reports": dict(self.tool_reports),
                "result": self.result,
                "declared_organism": self.declared_organism,
                "detected_organism": self.detected_organism,
                "confirmed_organism": self.confirmed_organism,
                "organism_decision": self.organism_decision,
                "species_report": self.species_report,
            }


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._lock = threading.Lock()

    def create(
        self,
        sample_id: str,
        mode: str,
        step_defs: list[tuple[str, str]],
        *,
        declared_organism: Optional[str] = None,
        input_path: Optional[Path | str] = None,
        work_dir: Optional[Path | str] = None,
        tools: Optional[list[str]] = None,
        dry_run: bool = False,
    ) -> AnalysisJob:
        job = AnalysisJob(
            id=uuid.uuid4().hex,
            sample_id=sample_id,
            mode=mode,
            steps=[JobStep(id=sid, label=label) for sid, label in step_defs],
            declared_organism=declared_organism,
            input_path=str(input_path) if input_path else None,
            work_dir=str(work_dir) if work_dir else None,
            tools=list(tools or []),
            dry_run=dry_run,
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[AnalysisJob]:
        with self._lock:
            return self._jobs.get(job_id)


JOB_STORE = JobStore()

TOOL_STEP_LABELS = {
    "resfinder": "ResFinder",
    "rgi": "CARD / RGI",
    "amrfinderplus": "AMRFinderPlus",
    "abricate": "ABRicate (ARG-ANNOT)",
    "deeparg": "DeepARG",
}


def build_live_steps(tools: list[str]) -> list[tuple[str, str]]:
    steps = [
        ("ingest", "Validate & stage sequence"),
        ("species_id", "Identify species (Mash)"),
    ]
    for key in tools:
        steps.append((f"tool:{key}", f"Run {TOOL_STEP_LABELS.get(key, key)} + hamronize"))
    steps.append(("consensus", "Aggregate tool reports"))
    steps.append(("persist", "Store results"))
    return steps


def build_demo_steps() -> list[tuple[str, str]]:
    return [
        ("ingest", "Load fixture reports"),
        ("species_id", "Species check (demo)"),
        ("tool:resfinder", "ResFinder (fixture)"),
        ("tool:rgi", "CARD / RGI (fixture)"),
        ("tool:amrfinderplus", "AMRFinderPlus (fixture)"),
        ("tool:abricate", "ABRicate (fixture)"),
        ("tool:deeparg", "DeepARG (fixture)"),
        ("consensus", "Aggregate tool reports"),
        ("persist", "Store results"),
    ]
