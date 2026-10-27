"""
AMR consensus engine: quality filter → drug-class normalization → 3/5 voting.

Implements the majority-voting rule at the drug_class level across five
hAMRonized tool reports (ResFinder, CARD/RGI, AMRFinderPlus, ARG-ANNOT/ABRicate,
DeepARG).
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

from .drug_class_map import normalize_drug_class
from .schemas import (
    AMRResultPayload,
    ConsensusEntry,
    HarmonizedHit,
    ResistanceStatus,
    ToolRunStatus,
)

JsonPath = Union[str, Path]
ToolReports = Mapping[str, Union[JsonPath, Sequence[Mapping[str, Any]], Sequence[HarmonizedHit]]]

# Stable display names for API payload (keys are runner / hamronize tool ids).
DEFAULT_TOOL_DISPLAY: dict[str, str] = {
    "resfinder": "ResFinder",
    "rgi": "CARD_RGI",
    "amrfinderplus": "AMRFinderPlus",
    "abricate": "ARG_ANNOT",
    "deeparg": "DeepARG",
}


def scale_majority_threshold(n_tools: int, *, of_five: int = 3) -> int:
    """Scale the classic 3/5 rule to an arbitrary tool count (min 1)."""
    import math

    n = max(1, int(n_tools))
    return max(1, math.ceil(n * of_five / 5))


class AMRConsensusAnalyzer:
    """
    Process five hAMRonized JSON outputs into a consensus dashboard payload.

    Parameters
    ----------
    identity_threshold:
        Minimum ``sequence_identity`` (%) to retain a hit.
    coverage_threshold:
        Minimum ``coverage_percentage`` (%) to retain a hit.
    majority_vote_threshold:
        Distinct tools required for RESISTANT (default 3 of 5).
    total_tools:
        Denominator shown in ``votes`` strings (default 5).
    tool_display_names:
        Optional override map of tool_key → display label.
    """

    def __init__(
        self,
        identity_threshold: float = 90.0,
        coverage_threshold: float = 80.0,
        majority_vote_threshold: int = 3,
        total_tools: int = 5,
        tool_display_names: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.identity_threshold = float(identity_threshold)
        self.coverage_threshold = float(coverage_threshold)
        self.majority_vote_threshold = int(majority_vote_threshold)
        self.total_tools = int(total_tools)
        self.tool_display_names = {
            **DEFAULT_TOOL_DISPLAY,
            **(dict(tool_display_names) if tool_display_names else {}),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        tool_reports: ToolReports,
        sample_id: str,
        *,
        processed_at: Optional[datetime] = None,
        total_tools: Optional[int] = None,
        majority_vote_threshold: Optional[int] = None,
    ) -> AMRResultPayload:
        """
        Run filter → normalize → majority vote on hAMRonized reports.

        ``tool_reports`` maps tool keys (e.g. ``resfinder``) to either:
        - a path to a hAMRonized JSON file, or
        - an in-memory list of hit dicts / ``HarmonizedHit`` models.

        Optional ``total_tools`` / ``majority_vote_threshold`` override the
        instance defaults for this run (e.g. when the user selected a subset).
        """
        if total_tools is not None:
            n_tools = max(1, int(total_tools))
        elif tool_reports:
            n_tools = max(1, len(tool_reports))
        else:
            n_tools = self.total_tools

        if majority_vote_threshold is not None:
            maj = max(1, int(majority_vote_threshold))
        elif total_tools is not None or tool_reports:
            maj = scale_majority_threshold(n_tools)
        else:
            maj = self.majority_vote_threshold

        filtered_by_tool: dict[str, list[HarmonizedHit]] = {}
        raw_breakdown: dict[str, list[dict[str, Any]]] = {}

        for tool_key, report in tool_reports.items():
            hits = self._load_hits(report, tool_key=tool_key)
            annotated = [self._annotate_hit(h) for h in hits]
            raw_breakdown[tool_key] = [
                h.model_dump(exclude_none=True) for h in annotated
            ]
            filtered_by_tool[tool_key] = [
                h for h in annotated if h.passed_quality_filter
            ]

        consensus = self._majority_vote(
            filtered_by_tool,
            total_tools=n_tools,
            majority_vote_threshold=maj,
        )

        resistant_count = sum(1 for c in consensus if c.status == ResistanceStatus.RESISTANT)
        ambiguous_count = sum(1 for c in consensus if c.status == ResistanceStatus.AMBIGUOUS)
        susceptible_count = sum(1 for c in consensus if c.status == ResistanceStatus.SUSCEPTIBLE)

        tool_status: list[ToolRunStatus] = []
        for tool_key, hits in filtered_by_tool.items():
            raw_hits = raw_breakdown.get(tool_key, [])
            tool_status.append(
                ToolRunStatus(
                    tool_key=tool_key,
                    display_name=self.tool_display_names.get(tool_key, tool_key),
                    success=True,
                    hit_count=len(raw_hits),
                    filtered_hit_count=len(hits),
                )
            )

        return AMRResultPayload(
            sample_id=sample_id,
            processed_at=processed_at or datetime.now(timezone.utc),
            consensus_summary=consensus,
            tool_breakdown=raw_breakdown,
            tool_status=tool_status,
            filter_thresholds={
                "sequence_identity_min": self.identity_threshold,
                "coverage_percentage_min": self.coverage_threshold,
            },
            total_tools=n_tools,
            majority_vote_threshold=maj,
            resistant_count=resistant_count,
            ambiguous_count=ambiguous_count,
            susceptible_count=susceptible_count,
        )

    def analyze_to_dict(
        self,
        tool_reports: ToolReports,
        sample_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Convenience wrapper returning a JSON-serializable dict."""
        return self.analyze(tool_reports, sample_id, **kwargs).to_api_dict()

    def load_annotated_hits(
        self,
        report: Union[JsonPath, Sequence[Mapping[str, Any]], Sequence[HarmonizedHit]],
        tool_key: str,
    ) -> list[HarmonizedHit]:
        """Hits with normalized drug class and filter verdict, for tool reports."""
        return [
            self._annotate_hit(hit)
            for hit in self._load_hits(report, tool_key=tool_key)
        ]

    # ------------------------------------------------------------------
    # Step A — quality filtering
    # ------------------------------------------------------------------

    def passes_quality_filter(self, hit: HarmonizedHit) -> bool:
        """Discard hits below identity / coverage thresholds."""
        identity = self._as_float(hit.sequence_identity)
        coverage = self._as_float(hit.coverage_percentage)
        if identity is None:
            return False
        if identity < self.identity_threshold:
            return False
        # DeepARG (and some parsers) omit coverage breadth — require identity only then.
        if coverage is None:
            return True
        return coverage >= self.coverage_threshold

    def filter_hits(self, hits: Iterable[HarmonizedHit]) -> list[HarmonizedHit]:
        annotated = [self._annotate_hit(h) for h in hits]
        return [h for h in annotated if h.passed_quality_filter]

    # ------------------------------------------------------------------
    # Step B — drug class normalization
    # ------------------------------------------------------------------

    def normalize_hit_drug_class(self, hit: HarmonizedHit) -> str:
        return normalize_drug_class(
            drug_class=hit.drug_class,
            gene_symbol=hit.gene_symbol,
            antimicrobial_agent=hit.antimicrobial_agent,
        )

    # ------------------------------------------------------------------
    # Step C — majority voting (3/5)
    # ------------------------------------------------------------------

    def _majority_vote(
        self,
        filtered_by_tool: Mapping[str, Sequence[HarmonizedHit]],
        *,
        total_tools: Optional[int] = None,
        majority_vote_threshold: Optional[int] = None,
    ) -> list[ConsensusEntry]:
        """
        Aggregate by normalized drug_class.

        Count distinct tools that retain ≥1 qualifying hit for that class.
        """
        n_tools = int(total_tools) if total_tools is not None else self.total_tools
        maj = (
            int(majority_vote_threshold)
            if majority_vote_threshold is not None
            else self.majority_vote_threshold
        )

        # drug_class → tool_display → set(genes)
        class_tool_genes: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )

        for tool_key, hits in filtered_by_tool.items():
            display = self.tool_display_names.get(tool_key, tool_key)
            for hit in hits:
                drug_class = hit.normalized_drug_class or self.normalize_hit_drug_class(hit)
                gene = (hit.gene_symbol or hit.gene_name or "unknown").strip()
                # Normalize ABRicate prefixes like "(Bla)blaKPC-2"
                if gene.startswith("(") and ")" in gene:
                    gene = gene.split(")", 1)[1].strip() or gene
                class_tool_genes[drug_class][display].add(gene)

        entries: list[ConsensusEntry] = []
        for drug_class in sorted(class_tool_genes.keys()):
            tool_genes = class_tool_genes[drug_class]
            supporting = sorted(tool_genes.keys())
            tool_count = len(supporting)
            genes = sorted({g for gs in tool_genes.values() for g in gs})
            status = self._status_from_count(tool_count, majority_vote_threshold=maj)
            entries.append(
                ConsensusEntry(
                    drug_class=drug_class,
                    status=status,
                    votes=f"{tool_count}/{n_tools}",
                    supporting_tools=supporting,
                    detected_genes=genes,
                    tool_count=tool_count,
                )
            )

        # Deterministic ordering: RESISTANT → AMBIGUOUS → SUSCEPTIBLE, then name
        status_rank = {
            ResistanceStatus.RESISTANT: 0,
            ResistanceStatus.AMBIGUOUS: 1,
            ResistanceStatus.SUSCEPTIBLE: 2,
        }
        entries.sort(key=lambda e: (status_rank[e.status], e.drug_class.lower()))
        return entries

    def _status_from_count(
        self,
        tool_count: int,
        *,
        majority_vote_threshold: Optional[int] = None,
    ) -> ResistanceStatus:
        maj = (
            int(majority_vote_threshold)
            if majority_vote_threshold is not None
            else self.majority_vote_threshold
        )
        if tool_count >= maj:
            return ResistanceStatus.RESISTANT
        if tool_count >= 1:
            return ResistanceStatus.AMBIGUOUS
        return ResistanceStatus.SUSCEPTIBLE

    # ------------------------------------------------------------------
    # Loading / annotation helpers
    # ------------------------------------------------------------------

    def _annotate_hit(self, hit: HarmonizedHit) -> HarmonizedHit:
        hit.normalized_drug_class = self.normalize_hit_drug_class(hit)
        hit.passed_quality_filter = self.passes_quality_filter(hit)
        if hit.tool_key and not hit.tool_display_name:
            hit.tool_display_name = self.tool_display_names.get(hit.tool_key, hit.tool_key)
        return hit

    def _load_hits(
        self,
        report: Union[JsonPath, Sequence[Mapping[str, Any]], Sequence[HarmonizedHit]],
        tool_key: str,
    ) -> list[HarmonizedHit]:
        if isinstance(report, (str, Path)):
            records = self._read_hamronized_json(Path(report))
        else:
            records = list(report)

        hits: list[HarmonizedHit] = []
        for rec in records:
            if isinstance(rec, HarmonizedHit):
                hit = rec.model_copy(deep=True)
            else:
                hit = self._dict_to_hit(dict(rec))
            hit.tool_key = tool_key
            hit.tool_display_name = self.tool_display_names.get(tool_key, tool_key)
            if not hit.analysis_software_name:
                hit.analysis_software_name = tool_key
            hits.append(hit)
        return hits

    @staticmethod
    def _read_hamronized_json(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"hAMRonized report not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        # hamronize JSON may be a list of results or {"records": [...]}
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("records", "results", "hits", "data"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            # Single-record object
            if "gene_symbol" in data or "gene_name" in data:
                return [data]
        raise ValueError(f"Unrecognized hAMRonized JSON structure in {path}")

    @staticmethod
    def _dict_to_hit(rec: dict[str, Any]) -> HarmonizedHit:
        # Accept both snake_case (hAMRonize) and occasional alternate keys.
        aliases = {
            "coverage_percentage": [
                "coverage_percentage",
                "coverage_%",
                "coverage_percent",
                "percent_coverage",
            ],
            "sequence_identity": [
                "sequence_identity",
                "percent_identity",
                "identity",
            ],
            "reference_database_id": [
                "reference_database_id",
                "reference_database",
                "reference_db",
            ],
            "drug_class": ["drug_class", "Drug Class"],
            "gene_symbol": ["gene_symbol", "Gene Symbol"],
            "gene_name": ["gene_name", "Gene Name"],
            "antimicrobial_agent": ["antimicrobial_agent", "Antimicrobial Agent"],
        }
        normalized: dict[str, Any] = dict(rec)
        for canonical, keys in aliases.items():
            if canonical in normalized and normalized[canonical] is not None:
                continue
            for k in keys:
                if k in rec and rec[k] is not None:
                    normalized[canonical] = rec[k]
                    break

        # Coerce numeric strings
        for num_field in ("sequence_identity", "coverage_percentage"):
            if num_field in normalized:
                normalized[num_field] = AMRConsensusAnalyzer._as_float(normalized[num_field])

        return HarmonizedHit.model_validate(normalized)

    @staticmethod
    def _as_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().rstrip("%")
        try:
            return float(text)
        except ValueError:
            return None


# Backward-compatible module alias name referenced in the design brief.
amr_consensus_engine = AMRConsensusAnalyzer
