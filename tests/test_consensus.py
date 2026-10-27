"""Unit tests for AMRConsensusAnalyzer filtering and 3/5 majority voting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.pipeline.consensus import AMRConsensusAnalyzer
from backend.pipeline.drug_class_map import normalize_drug_class
from backend.pipeline.schemas import ResistanceStatus

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tool_reports() -> dict[str, Path]:
    return {
        "resfinder": FIXTURES / "resfinder.json",
        "rgi": FIXTURES / "rgi.json",
        "amrfinderplus": FIXTURES / "amrfinderplus.json",
        "abricate": FIXTURES / "abricate.json",
        "deeparg": FIXTURES / "deeparg.json",
    }


@pytest.fixture
def analyzer() -> AMRConsensusAnalyzer:
    return AMRConsensusAnalyzer(
        identity_threshold=90.0,
        coverage_threshold=80.0,
        majority_vote_threshold=3,
        total_tools=5,
    )


def test_quality_filter_discards_low_identity(analyzer: AMRConsensusAnalyzer, tool_reports):
    payload = analyzer.analyze(tool_reports, sample_id="sampleA")
    # tetA in resfinder has identity 85% → filtered; must not appear as Tetracycline from that hit alone
    tet = [c for c in payload.consensus_summary if c.drug_class == "Tetracycline"]
    assert tet == []

    # low_quality_hit macrolide from deeparg filtered
    mac = [c for c in payload.consensus_summary if c.drug_class == "Macrolide"]
    assert mac == []


def test_carbapenem_majority_resistant(analyzer: AMRConsensusAnalyzer, tool_reports):
    """
    Carbapenem / blaKPC supported by ResFinder, RGI, AMRFinderPlus, and ARG-ANNOT
    (ABRicate maps blaKPC → Carbapenem via gene symbol even if drug_class says Beta-lactam).
    """
    payload = analyzer.analyze(tool_reports, sample_id="sampleA")
    by_class = {c.drug_class: c for c in payload.consensus_summary}

    # blaKPC gene-symbol mapping forces Carbapenem for abricate hit
    assert "Carbapenem" in by_class
    carb = by_class["Carbapenem"]
    assert carb.status == ResistanceStatus.RESISTANT
    assert carb.tool_count >= 3
    assert carb.votes.endswith("/5")
    assert "ResFinder" in carb.supporting_tools
    assert "CARD_RGI" in carb.supporting_tools
    assert "AMRFinderPlus" in carb.supporting_tools
    assert any("KPC" in g.upper() or "BLAKPC" in g.upper() for g in carb.detected_genes)


def test_aminoglycoside_resistant(analyzer: AMRConsensusAnalyzer, tool_reports):
    payload = analyzer.analyze(tool_reports, sample_id="sampleA")
    by_class = {c.drug_class: c for c in payload.consensus_summary}
    assert "Aminoglycoside" in by_class
    amino = by_class["Aminoglycoside"]
    assert amino.status == ResistanceStatus.RESISTANT
    assert amino.tool_count >= 3


def test_sulfonamide_ambiguous(analyzer: AMRConsensusAnalyzer, tool_reports):
    """sul1 only from AMRFinderPlus → AMBIGUOUS / SUSPECTED."""
    payload = analyzer.analyze(tool_reports, sample_id="sampleA")
    by_class = {c.drug_class: c for c in payload.consensus_summary}
    assert "Sulfonamide" in by_class
    sul = by_class["Sulfonamide"]
    assert sul.status == ResistanceStatus.AMBIGUOUS
    assert sul.tool_count == 1
    assert sul.votes == "1/5"


def test_api_payload_shape(analyzer: AMRConsensusAnalyzer, tool_reports):
    data = analyzer.analyze_to_dict(tool_reports, sample_id="sampleA")
    assert data["sample_id"] == "sampleA"
    assert "processed_at" in data
    assert isinstance(data["consensus_summary"], list)
    assert set(data["tool_breakdown"].keys()) == {
        "resfinder",
        "rgi",
        "amrfinderplus",
        "abricate",
        "deeparg",
    }
    entry = data["consensus_summary"][0]
    for key in ("drug_class", "status", "votes", "supporting_tools", "detected_genes"):
        assert key in entry


def test_in_memory_reports(analyzer: AMRConsensusAnalyzer):
    reports = {
        "resfinder": [
            {
                "gene_symbol": "mcr-1",
                "drug_class": "colistin",
                "sequence_identity": 99.0,
                "coverage_percentage": 100.0,
            }
        ],
        "rgi": [
            {
                "gene_symbol": "MCR-1",
                "drug_class": "peptide antibiotic",
                "sequence_identity": 99.0,
                "coverage_percentage": 100.0,
            }
        ],
        "amrfinderplus": [
            {
                "gene_symbol": "mcr-1",
                "drug_class": "COLISTIN",
                "sequence_identity": 100.0,
                "coverage_percentage": 100.0,
            }
        ],
        "abricate": [],
        "deeparg": [],
    }
    # Force colistin via gene map for rgi "peptide antibiotic"
    payload = analyzer.analyze(reports, sample_id="col")
    by_class = {c.drug_class: c for c in payload.consensus_summary}
    assert by_class["Colistin"].status == ResistanceStatus.RESISTANT
    assert by_class["Colistin"].votes == "3/5"


def test_normalize_drug_class_gene_fallback():
    assert normalize_drug_class(None, gene_symbol="blaNDM-1") == "Carbapenem"
    assert normalize_drug_class(None, gene_symbol="tetB") == "Tetracycline"
    assert normalize_drug_class("fluoroquinolone antibiotic", None) == "Fluoroquinolone"


def test_missing_metrics_filtered(analyzer: AMRConsensusAnalyzer):
    reports = {
        "resfinder": [
            {"gene_symbol": "blaKPC-2", "drug_class": "carbapenem"}  # no identity/coverage
        ],
        "rgi": [],
        "amrfinderplus": [],
        "abricate": [],
        "deeparg": [],
    }
    payload = analyzer.analyze(reports, sample_id="x")
    assert payload.consensus_summary == []
