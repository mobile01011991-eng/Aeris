"""
End-to-end AMR pipeline: sequence → tools → hAMRonize → consensus → payload.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .amr_runner import AMRToolRunner, PipelineRunResult, ToolRunResult
from .consensus import AMRConsensusAnalyzer, scale_majority_threshold
from .schemas import AMRResultPayload
from .tool_reports import (
    TOOL_DISPLAY_NAMES,
    parse_native_outputs,
    tool_kind,
)

logger = logging.getLogger(__name__)

ProgressCb = Callable[[str, str, str], None]
# (step_id, status, detail)
ToolReportCb = Callable[[str, dict[str, Any]], None]
# (tool_key, report)


class AMRPipeline:
    """
    Orchestrates tool execution, consensus voting, and result persistence hooks.
    """

    def __init__(
        self,
        runner: Optional[AMRToolRunner] = None,
        analyzer: Optional[AMRConsensusAnalyzer] = None,
        config_path: Optional[Path] = None,
        dry_run: bool = False,
    ) -> None:
        self.runner = runner or AMRToolRunner(config_path=config_path, dry_run=dry_run)
        consensus_cfg = (self.runner.config or {}).get("consensus", {})
        self.analyzer = analyzer or AMRConsensusAnalyzer(
            identity_threshold=float(consensus_cfg.get("identity_threshold", 90.0)),
            coverage_threshold=float(consensus_cfg.get("coverage_threshold", 80.0)),
            majority_vote_threshold=int(consensus_cfg.get("majority_vote_threshold", 3)),
            total_tools=int(consensus_cfg.get("total_tools", 5)),
        )

    def process(
        self,
        input_path: Path | str,
        sample_id: Optional[str] = None,
        work_dir: Optional[Path | str] = None,
        tools: Optional[list[str]] = None,
        *,
        persist_callback: Optional[Any] = None,
        on_progress: Optional[ProgressCb] = None,
        on_tool_report: Optional[ToolReportCb] = None,
        amrfinder_organism: Optional[str] = None,
        resfinder_species: Optional[str] = None,
        organism_info: Optional[Any] = None,
        skip_ingest_progress: bool = False,
    ) -> AMRResultPayload:
        from .schemas import OrganismInfo

        def progress(step_id: str, status: str, detail: str = "") -> None:
            if on_progress:
                on_progress(step_id, status, detail)

        if not skip_ingest_progress:
            progress("ingest", "running", "Staging input sequence")
            progress("ingest", "done", "Sequence ready")

        tool_reports: dict[str, dict[str, Any]] = {}

        def on_tool_start(key: str) -> None:
            progress(f"tool:{key}", "running", f"Executing {key}")

        def on_tool_done(key: str, result: ToolRunResult) -> None:
            report = self.build_tool_report(key, result)
            tool_reports[key] = report
            if on_tool_report:
                on_tool_report(key, report)

            if result.success:
                passed = report.get("filtered_hit_count", 0)
                total = report.get("hit_count", 0)
                progress(f"tool:{key}", "done", f"{passed}/{total} hits passed filter")
            else:
                progress(f"tool:{key}", "failed", result.error or "Failed")

        run: PipelineRunResult = self.runner.run_all(
            input_path=input_path,
            sample_id=sample_id,
            work_dir=work_dir,
            tools=tools,
            on_tool_start=on_tool_start,
            on_tool_done=on_tool_done,
            amrfinder_organism=amrfinder_organism,
            resfinder_species=resfinder_species,
        )

        reports = run.hamronized_reports
        if not reports:
            logger.warning(
                "No successful hAMRonized reports for sample %s; returning empty consensus",
                run.sample_id,
            )

        progress("consensus", "running", "Applying filters and majority vote")
        n_tools = len(run.tools) if run.tools else max(1, len(reports))
        maj = scale_majority_threshold(n_tools)
        payload = self.analyzer.analyze(
            tool_reports=reports,
            sample_id=run.sample_id,
            processed_at=datetime.now(timezone.utc),
            total_tools=n_tools,
            majority_vote_threshold=maj,
        )
        payload = self._attach_tool_status(payload, run)
        payload.tool_reports = tool_reports
        if organism_info is not None:
            if isinstance(organism_info, OrganismInfo):
                payload.organism = organism_info
            elif isinstance(organism_info, dict):
                payload.organism = OrganismInfo.model_validate(organism_info)
        progress(
            "consensus",
            "done",
            f"{len(reports)} tool reports aggregated",
        )

        progress("persist", "running", "Writing consensus payload")
        out_json = run.work_dir / "consensus_payload.json"
        out_json.write_text(
            json.dumps(payload.to_api_dict(), indent=2),
            encoding="utf-8",
        )
        logger.info("Wrote consensus payload → %s", out_json)

        if persist_callback is not None:
            persist_callback(payload, run)
        progress("persist", "done", "Stored")

        return payload

    def build_tool_report(self, tool_key: str, result: ToolRunResult) -> dict[str, Any]:
        """
        One tool's own report: shared hAMRonized hits plus native fields.

        Called as soon as a tool finishes so the UI can open a finished report
        while later tools are still running.
        """
        hits: list[dict[str, Any]] = []
        if result.hamronized_json and Path(result.hamronized_json).exists():
            try:
                hits = [
                    hit.model_dump(exclude_none=True)
                    for hit in self.analyzer.load_annotated_hits(
                        Path(result.hamronized_json), tool_key
                    )
                ]
            except Exception:  # noqa: BLE001
                logger.exception("Could not load hAMRonized hits for %s", tool_key)

        return {
            "tool_key": tool_key,
            "display_name": result.display_name
            or TOOL_DISPLAY_NAMES.get(tool_key, tool_key),
            "kind": tool_kind(tool_key),
            "success": bool(result.success),
            "error": result.error,
            "hit_count": len(hits),
            "filtered_hit_count": sum(
                1 for hit in hits if hit.get("passed_quality_filter")
            ),
            "hits": hits,
            "extras": parse_native_outputs(tool_key, result.raw_output),
        }

    @staticmethod
    def _attach_tool_status(payload: AMRResultPayload, run: PipelineRunResult) -> AMRResultPayload:
        from .schemas import ToolRunStatus

        by_key = {t.tool_key: t for t in payload.tool_status}
        merged: list[ToolRunStatus] = []
        for key, result in run.tools.items():
            existing = by_key.get(key)
            hit_count = existing.hit_count if existing else 0
            filtered = existing.filtered_hit_count if existing else 0
            merged.append(
                ToolRunStatus(
                    tool_key=key,
                    display_name=result.display_name,
                    success=result.success,
                    hit_count=hit_count,
                    filtered_hit_count=filtered,
                    error=result.error,
                )
            )
        payload.tool_status = merged
        return payload

    def analyze_existing_reports(
        self,
        tool_reports: dict[str, Path | str],
        sample_id: str,
        *,
        on_progress: Optional[ProgressCb] = None,
    ) -> AMRResultPayload:
        """Consensus-only path when tools were already run externally."""

        def progress(step_id: str, status: str, detail: str = "") -> None:
            if on_progress:
                on_progress(step_id, status, detail)

        for key in tool_reports:
            progress(f"tool:{key}", "running", "Loading report")
            progress(f"tool:{key}", "done", "Loaded")

        progress("consensus", "running", "Voting")
        n_tools = max(1, len(tool_reports))
        payload = self.analyzer.analyze(
            tool_reports=tool_reports,
            sample_id=sample_id,
            total_tools=n_tools,
            majority_vote_threshold=scale_majority_threshold(n_tools),
        )
        progress("consensus", "done", "Complete")
        return payload
