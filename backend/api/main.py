"""
FastAPI surface: upload sequence → species gate → async AMR pipeline → consensus.
"""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.jobs import (
    JOB_STORE,
    TOOL_STEP_LABELS,
    AnalysisJob,
    build_demo_steps,
    build_live_steps,
)
from backend.db.models import (
    AMRSampleResult,
    fetch_latest_payload,
    get_session_factory,
    persist_amr_result,
)
from backend.pipeline.amr_runner import TOOL_KEYS, safe_file_name, safe_path_name
from backend.pipeline.organism import get_default_catalog
from backend.pipeline.pipeline import AMRPipeline
from backend.pipeline.schemas import OrganismInfo
from backend.pipeline.species_id import identify_species
from backend.pipeline.tool_reports import (
    TOOL_DISPLAY_NAMES,
    gene_family,
    strip_gene_prefix,
    tool_kind,
)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"

app = FastAPI(
    title="AERIS AMR Detection API",
    description="Species gate + five AMR tools, hAMRonize, and 3/5 drug-class consensus.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SessionLocal = get_session_factory()


class ConfirmBody(BaseModel):
    decision: str = Field(
        description="accept_system | keep_user | cancel",
    )


def _load_fixture_reports() -> dict[str, list[dict[str, Any]]]:
    reports: dict[str, list[dict[str, Any]]] = {}
    for key in ("resfinder", "rgi", "amrfinderplus", "abricate", "deeparg"):
        path = FIXTURES / f"{key}.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing fixture: {path}")
        reports[key] = json.loads(path.read_text(encoding="utf-8"))
    return reports


def _demo_extras(tool_key: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Native-like fields for fixture demos.

    Fixtures are hAMRonized-only, so each tool page would otherwise be empty.
    Everything here is derived from the fixture hit and flagged as demo data.
    """
    if tool_key == "resfinder":
        rows: list[dict[str, Any]] = []
        for hit in hits:
            agents = [
                a.strip()
                for a in str(hit.get("antimicrobial_agent") or "").split(",")
                if a.strip()
            ]
            for agent in agents:
                rows.append(
                    {
                        "antimicrobial": agent,
                        "drug_class": hit.get("normalized_drug_class")
                        or hit.get("drug_class")
                        or "",
                        "phenotype": "Resistant",
                        "match": "3" if hit.get("sequence_identity") == 100 else "1",
                        "genetic_background": hit.get("gene_symbol") or "",
                    }
                )
        return {
            "phenotypes": rows,
            "point_mutations": [],
            "pointfinder_status": "skipped",
            "pointfinder_species": None,
            "pointfinder_reason": "PointFinder does not run in fixture demo mode",
        }

    if tool_key == "rgi":
        return {
            "hits": [
                {
                    "contig": hit.get("input_sequence_id") or "",
                    "cut_off": "Perfect"
                    if hit.get("sequence_identity") == 100
                    else "Strict",
                    "best_hit_aro": hit.get("gene_symbol") or "",
                    "aro": hit.get("reference_accession") or "",
                    "model_type": "protein homolog model",
                    "identity": hit.get("sequence_identity"),
                    "percent_length": hit.get("coverage_percentage"),
                    "drug_class": hit.get("drug_class") or "",
                    "resistance_mechanism": "",
                    "amr_gene_family": gene_family(hit.get("gene_symbol") or ""),
                    "antibiotic": hit.get("antimicrobial_agent") or "",
                    "snps": "",
                }
                for hit in hits
            ]
        }

    if tool_key == "amrfinderplus":
        return {
            "amr": [
                {
                    "contig": hit.get("input_sequence_id") or "",
                    "element_symbol": hit.get("gene_symbol") or "",
                    "element_name": hit.get("gene_name") or "",
                    "scope": "core",
                    "type": "AMR",
                    "subtype": "AMR",
                    "drug_class": hit.get("drug_class") or "",
                    "subclass": hit.get("antimicrobial_agent") or "",
                    "method": "ALLELEX"
                    if hit.get("sequence_identity") == 100
                    else "BLASTX",
                    "identity": hit.get("sequence_identity"),
                    "coverage": hit.get("coverage_percentage"),
                    "accession": hit.get("reference_accession") or "",
                    "reference_name": hit.get("gene_name") or "",
                }
                for hit in hits
            ],
            "point": [],
            "other": [],
        }

    if tool_key == "abricate":
        return {
            "hits": [
                {
                    "gene": hit.get("gene_symbol") or "",
                    "gene_display": strip_gene_prefix(hit.get("gene_symbol") or ""),
                    "contig": hit.get("input_sequence_id") or "",
                    "identity": hit.get("sequence_identity"),
                    "coverage": hit.get("coverage_percentage"),
                    "accession": hit.get("reference_accession") or "",
                    "database": "argannot",
                    "product": hit.get("gene_name") or "",
                    "resistance": "",
                }
                for hit in hits
            ]
        }

    if tool_key == "deeparg":
        return {
            "predictions": [
                {
                    "gene_family": gene_family(hit.get("gene_symbol") or ""),
                    "predicted_class": hit.get("drug_class") or "",
                    "probability": None,
                    "identity": hit.get("sequence_identity"),
                    "contig": hit.get("input_sequence_id") or "",
                    "best_hit": hit.get("reference_accession") or "",
                }
                for hit in hits
            ]
        }

    return {}


def _build_demo_tool_report(
    tool_key: str,
    records: list[dict[str, Any]],
    analyzer: Any,
) -> dict[str, Any]:
    hits = [
        hit.model_dump(exclude_none=True)
        for hit in analyzer.load_annotated_hits(records, tool_key)
    ]
    extras = _demo_extras(tool_key, hits)
    extras["demo"] = True
    return {
        "tool_key": tool_key,
        "display_name": TOOL_DISPLAY_NAMES.get(tool_key, tool_key),
        "kind": tool_kind(tool_key),
        "success": True,
        "error": None,
        "hit_count": len(hits),
        "filtered_hit_count": sum(
            1 for hit in hits if hit.get("passed_quality_filter")
        ),
        "hits": hits,
        "extras": extras,
    }


def _enabled_tools() -> list[str]:
    pipeline = AMRPipeline(dry_run=True)
    return [
        k
        for k in TOOL_KEYS
        if pipeline.runner.tools_cfg.get(k, {}).get("enabled", True) is not False
    ]


def _organism_info_from_job(job: AnalysisJob) -> OrganismInfo:
    report = job.species_report or {}
    match = report.get("match") or {}
    warning = None
    if job.organism_decision == "keep_user" and match.get("match_status") in {
        "mismatch",
        "uncertain",
        "failed",
    }:
        warning = (
            "Using user-declared organism despite Speciator disagreement; "
            "results may be less reliable."
        )
    return OrganismInfo(
        declared=job.declared_organism,
        detected=job.detected_organism,
        confirmed=job.confirmed_organism,
        decision=job.organism_decision,
        match_status=match.get("match_status"),
        confidence=match.get("confidence"),
        amrfinder_organism=match.get("amrfinder_organism")
        or get_default_catalog().amrfinder_key(job.confirmed_organism),
        resfinder_species=get_default_catalog().resfinder_species_key(
            job.confirmed_organism
        ),
        warning=warning,
    )


def _amrfinder_key_for_job(job: AnalysisJob) -> Optional[str]:
    info = _organism_info_from_job(job)
    if info.amrfinder_organism:
        return info.amrfinder_organism
    return get_default_catalog().amrfinder_key(job.confirmed_organism)


def _continue_amr(job: AnalysisJob) -> None:
    """Run AMR tools after species gate is resolved."""
    if not job.input_path or not job.work_dir:
        job.status = "failed"
        job.error = "Missing job input context"
        job.touch()
        return

    job.status = "running"
    job.touch()

    def on_progress(step_id: str, status: str, detail: str = "") -> None:
        job.set_step(step_id, status, detail)

    try:
        pipeline = AMRPipeline(dry_run=job.dry_run)
        organism_info = _organism_info_from_job(job)

        def _persist(payload, run):
            with SessionLocal() as session:
                persist_amr_result(session, payload, work_dir=str(run.work_dir))

        payload = pipeline.process(
            input_path=Path(job.input_path),
            sample_id=job.sample_id,
            work_dir=Path(job.work_dir),
            tools=job.tools or None,
            persist_callback=_persist,
            on_progress=on_progress,
            on_tool_report=job.set_tool_report,
            amrfinder_organism=_amrfinder_key_for_job(job),
            resfinder_species=organism_info.resfinder_species,
            organism_info=organism_info,
            skip_ingest_progress=True,
        )
        job.result = payload.to_api_dict()
        job.status = "completed"
        job.touch()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s AMR phase failed", job.id)
        job.status = "failed"
        job.error = str(exc)
        job.touch()


def _run_live_job(job_id: str) -> None:
    job = JOB_STORE.get(job_id)
    if not job or not job.input_path:
        return
    job.status = "running"
    job.touch()

    catalog = get_default_catalog()
    input_path = Path(job.input_path)
    work_dir = Path(job.work_dir) if job.work_dir else input_path.parent / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    species_dir = work_dir / "species_id"

    try:
        job.set_step("ingest", "running", "Staging input sequence")
        job.set_step("ingest", "done", "Sequence ready")

        job.set_step("species_id", "running", "Identifying species (Mash/markers)")
        sid = identify_species(
            input_path,
            dry_run=job.dry_run,
            out_dir=species_dir,
        )
        match = catalog.compare(
            job.declared_organism,
            sid.detected_name if sid.success else None,
            confidence=sid.confidence,
            detection_failed=not sid.success,
        )
        job.detected_organism = match.detected_name or sid.detected_name
        job.species_report = {
            "identification": sid.to_dict(),
            "match": match.to_dict(),
        }

        if match.match_status == "match":
            job.confirmed_organism = match.detected_name or job.declared_organism
            job.organism_decision = "auto_match"
            # Prefer AMRFinder mapping from match
            if match.amrfinder_organism:
                job.species_report["match"]["amrfinder_organism"] = match.amrfinder_organism
            job.set_step(
                "species_id",
                "done",
                f"Match: {job.confirmed_organism}",
            )
            _continue_amr(job)
            return

        # mismatch / uncertain / failed → wait for user
        detail = match.reason or match.match_status
        if job.detected_organism:
            detail = f"{match.match_status}: detected {job.detected_organism}"
        job.set_step("species_id", "done", detail)
        job.status = "awaiting_organism_confirmation"
        job.touch()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s species gate failed", job_id)
        job.status = "failed"
        job.error = str(exc)
        job.set_step("species_id", "failed", str(exc))
        job.touch()


def _run_demo_job(job_id: str, sample_id: str, declared_organism: Optional[str]) -> None:
    job = JOB_STORE.get(job_id)
    if not job:
        return
    job.status = "running"
    job.touch()
    catalog = get_default_catalog()
    try:
        job.set_step("ingest", "running", "Loading fixtures")
        time.sleep(0.2)
        reports = _load_fixture_reports()
        job.set_step("ingest", "done", "Fixtures ready")

        # Demo species: treat sampleA fixtures as Klebsiella-like carbapenem sample
        demo_detected = "Klebsiella pneumoniae"
        declared = declared_organism or "klebsiella_pneumoniae"
        job.declared_organism = declared
        job.set_step("species_id", "running", "Demo species check")
        time.sleep(0.15)
        match = catalog.compare(declared, demo_detected, confidence=0.95)
        job.detected_organism = demo_detected
        job.species_report = {
            "identification": {
                "success": True,
                "detected_name": demo_detected,
                "confidence": 0.95,
                "method": "demo",
            },
            "match": match.to_dict(),
        }

        if match.match_status == "match":
            job.confirmed_organism = demo_detected
            job.organism_decision = "auto_match"
            job.set_step("species_id", "done", f"Match: {demo_detected}")
        else:
            job.set_step(
                "species_id",
                "done",
                f"{match.match_status}: detected {demo_detected}",
            )
            job.status = "awaiting_organism_confirmation"
            job.touch()
            # Wait until confirm sets decision and signals, or timeout handled by confirm endpoint continuing
            if not job._confirm_event.wait(timeout=3600):
                if job.status == "awaiting_organism_confirmation":
                    job.status = "cancelled"
                    job.error = "Organism confirmation timed out"
                    job.touch()
                return
            if job.organism_decision == "cancel" or job.status == "cancelled":
                return
            job.status = "running"
            job.touch()

        pipeline = AMRPipeline(dry_run=True)
        for key in reports:
            job.set_step(f"tool:{key}", "running", "Reading fixture report")
            time.sleep(0.15)
            report = _build_demo_tool_report(key, reports[key], pipeline.analyzer)
            job.set_tool_report(key, report)
            job.set_step(
                f"tool:{key}",
                "done",
                f"{report['filtered_hit_count']}/{report['hit_count']} hits passed filter",
            )

        job.set_step("consensus", "running", "Aggregating tool reports")
        payload = pipeline.analyzer.analyze(tool_reports=reports, sample_id=sample_id)
        payload.organism = _organism_info_from_job(job)
        payload.tool_reports = dict(job.tool_reports)
        job.set_step(
            "consensus",
            "done",
            f"{len(reports)} tool reports aggregated",
        )

        job.set_step("persist", "running", "Saving")
        with SessionLocal() as session:
            persist_amr_result(session, payload, work_dir="fixtures-demo")
        job.set_step("persist", "done", "Stored")

        job.result = payload.to_api_dict()
        job.status = "completed"
        job.touch()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Demo job %s failed", job_id)
        job.status = "failed"
        job.error = str(exc)
        job.touch()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aeris-api"}


@app.get("/api/v1/amr/sample-fasta")
def sample_fasta():
    path = ROOT / "data" / "sample_amr.fasta"
    if not path.exists():
        raise HTTPException(status_code=404, detail="sample_amr.fasta not found")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename="sample_amr.fasta",
    )


@app.get("/api/v1/amr/organisms")
def list_organisms() -> dict:
    catalog = get_default_catalog()
    return {
        "confidence_threshold": catalog.confidence_threshold,
        "organisms": [o.to_api_dict() for o in catalog.list_organisms()],
    }


@app.get("/api/v1/amr/tools")
def list_tools() -> dict:
    pipeline = AMRPipeline(dry_run=True)
    tools_cfg = pipeline.runner.tools_cfg
    items = []
    for key in TOOL_KEYS:
        cfg = tools_cfg.get(key, {})
        items.append(
            {
                "key": key,
                "display_name": cfg.get("display_name", TOOL_STEP_LABELS.get(key, key)),
                "enabled": cfg.get("enabled", True) is not False,
                "image": cfg.get("image"),
            }
        )
    return {"tools": items}


@app.get("/api/v1/amr/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@app.post("/api/v1/amr/jobs/{job_id}/confirm")
def confirm_organism(job_id: str, body: ConfirmBody) -> dict:
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "awaiting_organism_confirmation":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not awaiting confirmation (status={job.status})",
        )

    decision = body.decision.strip().lower()
    if decision not in {"accept_system", "keep_user", "cancel"}:
        raise HTTPException(
            status_code=400,
            detail="decision must be accept_system, keep_user, or cancel",
        )

    if decision == "cancel":
        job.organism_decision = "cancel"
        job.status = "cancelled"
        job.error = "Cancelled at organism confirmation"
        job.touch()
        job._confirm_event.set()
        return job.to_dict()

    catalog = get_default_catalog()
    if decision == "accept_system":
        confirmed = job.detected_organism
        if not confirmed:
            raise HTTPException(
                status_code=400,
                detail="No detected organism to accept",
            )
        job.confirmed_organism = confirmed
        job.organism_decision = "accept_system"
        # Refresh amrfinder mapping from detected
        if job.species_report and "match" in job.species_report:
            job.species_report["match"]["amrfinder_organism"] = catalog.amrfinder_key(
                confirmed
            )
    else:  # keep_user
        if not job.declared_organism:
            raise HTTPException(status_code=400, detail="No declared organism to keep")
        entry = catalog.resolve(job.declared_organism)
        job.confirmed_organism = (
            entry.display_name if entry else job.declared_organism
        )
        job.organism_decision = "keep_user"
        if job.species_report and "match" in job.species_report:
            job.species_report["match"]["amrfinder_organism"] = catalog.amrfinder_key(
                job.confirmed_organism
            )

    job._confirm_event.set()

    # Leave awaiting immediately so the UI/poller does not re-open the modal
    job.status = "running"
    job.touch()

    if job.mode == "demo":
        # Demo thread is waiting on the event; it will continue.
        return job.to_dict()

    # Live: continue AMR in a new thread
    thread = threading.Thread(target=_continue_amr, args=(job,), daemon=True)
    thread.start()
    return job.to_dict()


@app.post("/api/v1/amr/analyze/async")
async def analyze_amr_async(
    file: UploadFile = File(..., description="FASTA or FASTQ sequence file"),
    sample_id: Optional[str] = Query(None),
    dry_run: bool = Query(False),
    tools: Optional[str] = Query(None),
    declared_organism: Optional[str] = Query(
        None, description="User-declared organism id or name"
    ),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    if not declared_organism:
        raise HTTPException(
            status_code=400,
            detail="declared_organism is required (choose species before analysis)",
        )

    catalog = get_default_catalog()
    if not catalog.resolve(declared_organism):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown organism: {declared_organism}",
        )

    suffix = Path(file.filename).suffix.lower()
    allowed = {".fasta", ".fastq", ".fa", ".fq", ".fna", ".gz"}
    if suffix not in allowed and not file.filename.lower().endswith(
        (".fasta.gz", ".fastq.gz", ".fa.gz", ".fq.gz", ".fna.gz")
    ):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    sid = sample_id or Path(file.filename).stem
    selected = [t.strip() for t in tools.split(",") if t.strip()] if tools else _enabled_tools()
    for key in selected:
        if key not in TOOL_KEYS:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {key}")

    tmp_root = Path(tempfile.mkdtemp(prefix="amr_upload_"))
    input_path = tmp_root / safe_file_name(file.filename)
    with input_path.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)

    work_dir = tmp_root / "work" / safe_path_name(sid) / uuid.uuid4().hex[:8]
    job = JOB_STORE.create(
        sid,
        "live",
        build_live_steps(selected),
        declared_organism=declared_organism,
        input_path=input_path,
        work_dir=work_dir,
        tools=selected,
        dry_run=dry_run,
    )

    thread = threading.Thread(target=_run_live_job, args=(job.id,), daemon=True)
    thread.start()
    return job.to_dict()


@app.post("/api/v1/amr/demo/async")
def run_demo_async(
    sample_id: str = Query("sampleA"),
    declared_organism: Optional[str] = Query("klebsiella_pneumoniae"),
) -> dict:
    job = JOB_STORE.create(
        sample_id,
        "demo",
        build_demo_steps(),
        declared_organism=declared_organism,
    )
    thread = threading.Thread(
        target=_run_demo_job,
        args=(job.id, sample_id, declared_organism),
        daemon=True,
    )
    thread.start()
    return job.to_dict()


@app.post("/api/v1/amr/analyze")
async def analyze_amr(
    file: UploadFile = File(...),
    sample_id: Optional[str] = Query(None),
    dry_run: bool = Query(False),
    tools: Optional[str] = Query(None),
    declared_organism: Optional[str] = Query(None),
) -> dict:
    """Synchronous analyze (CLI/scripts). Species gate is auto-accept when match else uses declared."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    sid = sample_id or Path(file.filename).stem
    tmp_root = Path(tempfile.mkdtemp(prefix="amr_upload_"))
    input_path = tmp_root / safe_file_name(file.filename)
    try:
        with input_path.open("wb") as fh:
            shutil.copyfileobj(file.file, fh)

        catalog = get_default_catalog()
        pipeline = AMRPipeline(dry_run=dry_run)
        work_dir = tmp_root / "work" / safe_path_name(sid) / uuid.uuid4().hex[:8]
        species_dir = work_dir / "species_id"
        work_dir.mkdir(parents=True, exist_ok=True)

        organism_info = None
        amr_org = None
        if declared_organism:
            sid_result = identify_species(
                input_path, dry_run=dry_run, out_dir=species_dir
            )
            match = catalog.compare(
                declared_organism,
                sid_result.detected_name if sid_result.success else None,
                confidence=sid_result.confidence,
                detection_failed=not sid_result.success,
            )
            confirmed = (
                match.detected_name
                if match.match_status == "match"
                else (
                    catalog.resolve(declared_organism).display_name
                    if catalog.resolve(declared_organism)
                    else declared_organism
                )
            )
            organism_info = OrganismInfo(
                declared=declared_organism,
                detected=match.detected_name,
                confirmed=confirmed,
                decision="auto_match" if match.match_status == "match" else "keep_user",
                match_status=match.match_status,
                confidence=match.confidence,
                amrfinder_organism=catalog.amrfinder_key(confirmed),
                resfinder_species=catalog.resfinder_species_key(confirmed),
            )
            amr_org = organism_info.amrfinder_organism

        def _persist(payload, run):
            with SessionLocal() as session:
                persist_amr_result(session, payload, work_dir=str(run.work_dir))

        selected = [t.strip() for t in tools.split(",") if t.strip()] if tools else None
        payload = pipeline.process(
            input_path=input_path,
            sample_id=sid,
            work_dir=work_dir,
            tools=selected,
            persist_callback=_persist,
            amrfinder_organism=amr_org,
            resfinder_species=(
                organism_info.resfinder_species if organism_info else None
            ),
            organism_info=organism_info,
        )
        return payload.to_api_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("AMR analyze failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/v1/amr/results/{sample_id}")
def get_result(sample_id: str) -> dict:
    with SessionLocal() as session:
        data = fetch_latest_payload(session, sample_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"No results for sample_id={sample_id}")
    return data


@app.post("/api/v1/amr/consensus")
async def consensus_only(body: dict) -> dict:
    sample_id = body.get("sample_id")
    tool_reports = body.get("tool_reports")
    if not sample_id or not isinstance(tool_reports, dict):
        raise HTTPException(
            status_code=400,
            detail="Body must include sample_id and tool_reports object",
        )

    pipeline = AMRPipeline(dry_run=True)
    payload = pipeline.analyzer.analyze(tool_reports=tool_reports, sample_id=sample_id)
    with SessionLocal() as session:
        persist_amr_result(session, payload)
    return payload.to_api_dict()


@app.post("/api/v1/amr/demo")
def run_demo(sample_id: str = Query("sampleA")) -> dict:
    reports = _load_fixture_reports()
    pipeline = AMRPipeline(dry_run=True)
    payload = pipeline.analyzer.analyze(tool_reports=reports, sample_id=sample_id)
    payload.tool_reports = {
        key: _build_demo_tool_report(key, records, pipeline.analyzer)
        for key, records in reports.items()
    }
    payload.organism = OrganismInfo(
        declared="klebsiella_pneumoniae",
        detected="Klebsiella pneumoniae",
        confirmed="Klebsiella pneumoniae",
        decision="auto_match",
        match_status="match",
        confidence=0.95,
        amrfinder_organism="Klebsiella_pneumoniae",
        resfinder_species="klebsiella",
    )
    with SessionLocal() as session:
        persist_amr_result(session, payload, work_dir="fixtures-demo")
    return payload.to_api_dict()


@app.get("/api/v1/amr/results")
def list_results(limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    with SessionLocal() as session:
        stmt = (
            select(AMRSampleResult)
            .order_by(AMRSampleResult.processed_at.desc())
            .limit(limit)
        )
        rows = session.scalars(stmt).all()
        return [
            {
                "id": r.id,
                "sample_id": r.sample_id,
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
                "status_summary": r.status_summary,
                "resistant_classes": r.resistant_classes,
                "ambiguous_classes": r.ambiguous_classes,
            }
            for r in rows
        ]
