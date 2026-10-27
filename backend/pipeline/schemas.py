"""Pydantic models for the AMR API response payload and internal hits."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResistanceStatus(str, Enum):
    RESISTANT = "RESISTANT"
    AMBIGUOUS = "AMBIGUOUS / SUSPECTED"
    SUSCEPTIBLE = "SUSCEPTIBLE"


class HarmonizedHit(BaseModel):
    """Subset of hAMRonized fields used by the consensus engine."""

    gene_symbol: Optional[str] = None
    gene_name: Optional[str] = None
    drug_class: Optional[str] = None
    antimicrobial_agent: Optional[str] = None
    sequence_identity: Optional[float] = None
    coverage_percentage: Optional[float] = None
    reference_database_id: Optional[str] = None
    reference_accession: Optional[str] = None
    analysis_software_name: Optional[str] = None
    input_file_name: Optional[str] = None

    # Pipeline annotations (not from hAMRonize)
    tool_key: Optional[str] = None
    tool_display_name: Optional[str] = None
    normalized_drug_class: Optional[str] = None
    passed_quality_filter: Optional[bool] = None

    model_config = {"extra": "allow"}


class ConsensusEntry(BaseModel):
    drug_class: str
    status: ResistanceStatus
    votes: str = Field(description='e.g. "4/5"')
    supporting_tools: list[str] = Field(default_factory=list)
    detected_genes: list[str] = Field(default_factory=list)
    tool_count: int = 0


class ToolRunStatus(BaseModel):
    tool_key: str
    display_name: str
    success: bool
    hit_count: int = 0
    filtered_hit_count: int = 0
    error: Optional[str] = None


class OrganismInfo(BaseModel):
    """Species gate outcome attached to the consensus payload."""

    declared: Optional[str] = None
    detected: Optional[str] = None
    confirmed: Optional[str] = None
    decision: Optional[str] = None
    match_status: Optional[str] = None
    confidence: Optional[float] = None
    amrfinder_organism: Optional[str] = None
    # PointFinder db_prefix; None when PointFinder has no panel for the species.
    resfinder_species: Optional[str] = None
    warning: Optional[str] = None


class AMRResultPayload(BaseModel):
    """
    Dashboard / API payload.

    ``tool_reports`` drives the UI. ``consensus_summary`` and its counts are
    kept for API compatibility and internal analysis; they are not the product.
    """

    sample_id: str
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    consensus_summary: list[ConsensusEntry] = Field(default_factory=list)
    tool_breakdown: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    # Primary result surface: one report per tool (hits + native fields).
    tool_reports: dict[str, dict[str, Any]] = Field(default_factory=dict)
    tool_status: list[ToolRunStatus] = Field(default_factory=list)
    filter_thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "sequence_identity_min": 90.0,
            "coverage_percentage_min": 80.0,
        }
    )
    total_tools: int = 5
    majority_vote_threshold: int = 3
    resistant_count: int = 0
    ambiguous_count: int = 0
    susceptible_count: int = 0
    organism: Optional[OrganismInfo] = None

    def to_api_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["processed_at"] = self.processed_at.isoformat()
        return data
