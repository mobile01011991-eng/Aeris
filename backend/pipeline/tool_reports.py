"""
Per-tool report builders.

hAMRonization gives a shared subset of fields, but drops what makes each tool
report useful on its own: ResFinder phenotype tables, RGI Cut_Off / mechanism,
AMRFinderPlus method + subtype, ABRicate BLAST coordinates, DeepARG
probability. Each tool page reads its own native output through these parsers.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Sequence-vs-database screens. DeepARG is deliberately not part of this group.
DATABASE_TOOL_KEYS = ("resfinder", "rgi", "amrfinderplus", "abricate")
AI_TOOL_KEYS = ("deeparg",)

TOOL_DISPLAY_NAMES = {
    "resfinder": "ResFinder",
    "rgi": "CARD / RGI",
    "amrfinderplus": "AMRFinderPlus",
    "abricate": "ABRicate (ARG-ANNOT)",
    "deeparg": "DeepARG",
}

# Written by the ResFinder runner so the report can tell "PointFinder found
# nothing" apart from "PointFinder never ran".
POINTFINDER_CONTEXT_FILE = "pointfinder_context.json"

TOOL_KINDS = {
    "resfinder": "database",
    "rgi": "database",
    "amrfinderplus": "database",
    "abricate": "database",
    "deeparg": "ai",
}


def tool_kind(tool_key: str) -> str:
    return TOOL_KINDS.get(tool_key, "database")


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        rows: list[dict[str, str]] = []
        for raw in reader:
            row = {
                str(key).strip(): ("" if value is None else str(value).strip())
                for key, value in raw.items()
                if key is not None
            }
            if any(row.values()):
                rows.append(row)
        return rows


def _pick(row: dict[str, str], *names: str, default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return default


def _num(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip().rstrip("%"))
    except ValueError:
        return None


def strip_gene_prefix(gene: str) -> str:
    """ARG-ANNOT ships genes as ``(Bla)blaKPC-2``; show the bare symbol."""
    text = (gene or "").strip()
    if text.startswith("(") and ")" in text:
        return text.split(")", 1)[1].strip() or text
    return text


_ALLELE_SUFFIX = re.compile(r"[-_]?\d+[A-Za-z]?$")


def gene_family(gene: str) -> str:
    """
    Family-level symbol shared by allele callers and DeepARG.

    ``blaKPC-2`` and ``(Bla)blaKPC-2`` both become ``KPC``, which is the level
    DeepARG predicts at.
    """
    text = strip_gene_prefix(gene or "")
    if not text:
        return ""
    text = re.sub(r"^bla", "", text, flags=re.IGNORECASE)
    text = _ALLELE_SUFFIX.sub("", text)
    return text.strip("-_").upper() or strip_gene_prefix(gene).upper()


# ----------------------------------------------------------------------
# ResFinder
# ----------------------------------------------------------------------


def _parse_pheno_table(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        rows.append(
            {
                "antimicrobial": parts[0].strip(),
                "drug_class": parts[1].strip(),
                "phenotype": parts[2].strip(),
                "match": parts[3].strip(),
                "genetic_background": parts[4].strip() if len(parts) > 4 else "",
            }
        )
    return rows


def _first_token(value: Any) -> str:
    text = str(value or "").strip()
    return text.split()[0] if text else ""


def _variation_type(var: dict[str, Any]) -> str:
    for name in ("substitution", "insertion", "deletion"):
        if var.get(name):
            return name
    return ""


def _phenotypes_for_variation(
    data: dict[str, Any],
    var_key: Optional[str],
) -> list[str]:
    """Antimicrobials linked to one mutation, when the variation omits them."""
    if not var_key:
        return []
    agents = [
        str(name)
        for name, entry in (data.get("phenotypes") or {}).items()
        if entry.get("amr_resistant")
        and var_key in (entry.get("seq_variations") or [])
    ]
    return sorted(agents)


def _point_mutations_from_json(path: Path) -> list[dict[str, Any]]:
    """
    Read PointFinder hits from the ResFinder JSON.

    ``seq_variations`` carries the mutation and ``seq_regions`` the gene it sits
    in, which is where identity, coverage and the contig come from.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        # A truncated or empty report must not drop the acquired-gene extras.
        logger.warning("Unreadable ResFinder JSON at %s", path)
        return []
    if not isinstance(data, dict):
        return []

    variations = data.get("seq_variations") or {}
    regions = data.get("seq_regions") or {}

    rows: list[dict[str, Any]] = []
    for var_key, var in variations.items():
        region_keys = var.get("seq_regions") or []
        region = regions.get(region_keys[0], {}) if region_keys else {}

        ref_codon = str(var.get("ref_codon") or "").upper()
        var_codon = str(var.get("var_codon") or "").upper()
        ref_aa = str(var.get("ref_aa") or "").upper()
        var_aa = str(var.get("var_aa") or "").upper()

        agents = [str(p) for p in (var.get("phenotypes") or [])]
        if not agents:
            agents = _phenotypes_for_variation(data, var.get("key") or var_key)

        rows.append(
            {
                "gene": region.get("name")
                or str(var.get("ref_id") or "").split(";;")[0],
                "mutation": var.get("seq_var") or "",
                "nucleotide_change": (
                    f"{ref_codon} -> {var_codon}" if ref_codon and var_codon else ""
                ),
                "amino_acid_change": (
                    f"{ref_aa} -> {var_aa}" if ref_aa and var_aa else ""
                ),
                "antimicrobials": agents,
                "variation_type": _variation_type(var),
                "codon_position": var.get("ref_start_pos"),
                "identity": region.get("identity"),
                "coverage": region.get("coverage"),
                "contig": _first_token(region.get("query_id")),
                "pmids": [str(p) for p in (var.get("pmids") or []) if p],
            }
        )
    return rows


def _point_mutations_from_table(path: Path) -> list[dict[str, Any]]:
    """Fallback: ``PointFinder_results.txt`` (gene is a prefix of Mutation)."""
    rows: list[dict[str, Any]] = []
    for row in _read_tsv(path):
        label = _pick(row, "Mutation")
        if not label:
            continue
        parts = label.split(None, 1)
        agents = [
            agent.strip()
            for agent in _pick(row, "Resistance").split(",")
            if agent.strip()
        ]
        rows.append(
            {
                "gene": parts[0],
                "mutation": parts[1] if len(parts) > 1 else "",
                "nucleotide_change": _pick(row, "Nucleotide change"),
                "amino_acid_change": _pick(row, "Amino acid change"),
                "antimicrobials": agents,
                "variation_type": "",
                "codon_position": None,
                "identity": None,
                "coverage": None,
                "contig": "",
                "pmids": [p.strip() for p in _pick(row, "PMID").split(",") if p.strip()],
            }
        )
    return rows


def _parse_resfinder(tool_dir: Path) -> dict[str, Any]:
    extras: dict[str, Any] = {}

    pheno = tool_dir / "pheno_table.txt"
    if pheno.exists():
        extras["phenotypes"] = _parse_pheno_table(pheno)

    context: dict[str, Any] = {}
    context_path = tool_dir / POINTFINDER_CONTEXT_FILE
    if context_path.exists():
        try:
            context = json.loads(context_path.read_text(encoding="utf-8")) or {}
        except ValueError:
            logger.warning("Unreadable PointFinder context in %s", tool_dir)

    results_table = tool_dir / "PointFinder_results.txt"
    ran = results_table.exists() or (tool_dir / "PointFinder_table.txt").exists()

    mutations: list[dict[str, Any]] = []
    resfinder_json = tool_dir / "data_resfinder.json"
    if resfinder_json.exists():
        mutations = _point_mutations_from_json(resfinder_json)
    if not mutations and results_table.exists():
        mutations = _point_mutations_from_table(results_table)

    status = str(context.get("status") or ("ran" if ran else "skipped"))
    reason = str(context.get("reason") or "")
    if status == "ran" and not ran and not mutations:
        status = "skipped"
        reason = reason or "PointFinder produced no output for this species"
    if status == "skipped" and not reason:
        reason = "PointFinder was not run for this sample"

    extras["point_mutations"] = mutations
    extras["pointfinder_status"] = status
    extras["pointfinder_species"] = context.get("species")
    if reason:
        extras["pointfinder_reason"] = reason

    return extras


# ----------------------------------------------------------------------
# CARD / RGI
# ----------------------------------------------------------------------


def _parse_rgi(tool_dir: Path) -> dict[str, Any]:
    path = tool_dir / "rgi.txt"
    if not path.exists():
        return {}

    hits: list[dict[str, Any]] = []
    for row in _read_tsv(path):
        hits.append(
            {
                "contig": _pick(row, "Contig"),
                "start": _pick(row, "Start"),
                "stop": _pick(row, "Stop"),
                "orientation": _pick(row, "Orientation"),
                "cut_off": _pick(row, "Cut_Off"),
                "best_hit_aro": _pick(row, "Best_Hit_ARO"),
                "aro": _pick(row, "ARO"),
                "model_type": _pick(row, "Model_type"),
                "identity": _num(_pick(row, "Best_Identities")),
                "percent_length": _num(
                    _pick(row, "Percentage Length of Reference Sequence")
                ),
                "drug_class": _pick(row, "Drug Class"),
                "resistance_mechanism": _pick(row, "Resistance Mechanism"),
                "amr_gene_family": _pick(row, "AMR Gene Family"),
                "antibiotic": _pick(row, "Antibiotic"),
                "snps": _pick(row, "SNPs_in_Best_Hit_ARO"),
            }
        )
    return {"hits": hits}


# ----------------------------------------------------------------------
# AMRFinderPlus
# ----------------------------------------------------------------------


def _parse_amrfinderplus(tool_dir: Path) -> dict[str, Any]:
    path = tool_dir / "amrfinder.tsv"
    if not path.exists():
        return {}

    amr: list[dict[str, Any]] = []
    point: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []

    for row in _read_tsv(path):
        row_type = _pick(row, "Type").upper()
        subtype = _pick(row, "Subtype").upper()
        item = {
            "contig": _pick(row, "Contig id", "Contig", "Contig name"),
            "start": _pick(row, "Start"),
            "stop": _pick(row, "Stop"),
            "strand": _pick(row, "Strand"),
            "element_symbol": _pick(row, "Element symbol", "Gene symbol"),
            "element_name": _pick(row, "Element name", "Sequence name"),
            "scope": _pick(row, "Scope"),
            "type": row_type,
            "subtype": subtype,
            "drug_class": _pick(row, "Class"),
            "subclass": _pick(row, "Subclass"),
            "method": _pick(row, "Method"),
            "identity": _num(
                _pick(
                    row,
                    "% Identity to reference",
                    "% Identity to reference sequence",
                )
            ),
            "coverage": _num(
                _pick(
                    row,
                    "% Coverage of reference",
                    "% Coverage of reference sequence",
                )
            ),
            "accession": _pick(
                row,
                "Closest reference accession",
                "Accession of closest sequence",
            ),
            "reference_name": _pick(
                row,
                "Closest reference name",
                "Name of closest sequence",
            ),
        }

        if "POINT" in (row_type, subtype):
            point.append(item)
        elif row_type in ("", "AMR"):
            amr.append(item)
        else:
            other.append(item)

    return {"amr": amr, "point": point, "other": other}


# ----------------------------------------------------------------------
# ABRicate / ARG-ANNOT
# ----------------------------------------------------------------------


def _parse_abricate(tool_dir: Path) -> dict[str, Any]:
    path = tool_dir / "abricate_argannot.tsv"
    if not path.exists():
        return {}

    hits: list[dict[str, Any]] = []
    for row in _read_tsv(path):
        gene = _pick(row, "GENE")
        hits.append(
            {
                "gene": gene,
                "gene_display": strip_gene_prefix(gene),
                "contig": _pick(row, "SEQUENCE"),
                "start": _pick(row, "START"),
                "end": _pick(row, "END"),
                "strand": _pick(row, "STRAND"),
                "identity": _num(_pick(row, "%IDENTITY")),
                "coverage": _num(_pick(row, "%COVERAGE")),
                "coverage_range": _pick(row, "COVERAGE"),
                "gaps": _pick(row, "GAPS"),
                "database": _pick(row, "DATABASE"),
                "accession": _pick(row, "ACCESSION"),
                "product": _pick(row, "PRODUCT"),
                "resistance": _pick(row, "RESISTANCE"),
            }
        )
    return {"hits": hits}


# ----------------------------------------------------------------------
# DeepARG
# ----------------------------------------------------------------------


def _deeparg_primary_report(tool_dir: Path) -> Optional[Path]:
    candidates = [
        p for p in sorted(tool_dir.glob("*.mapping.ARG"))
        if "potential" not in p.name.lower()
    ]
    if not candidates:
        return None
    modern = [p for p in candidates if "legacy" not in p.name.lower()]
    return modern[0] if modern else candidates[0]


def _parse_deeparg(tool_dir: Path) -> dict[str, Any]:
    path = _deeparg_primary_report(tool_dir)
    if path is None:
        return {}

    predictions: list[dict[str, Any]] = []
    for row in _read_tsv(path):
        predictions.append(
            {
                "gene_family": _pick(row, "#ARG", "ARG", "ARG_NAME"),
                "predicted_class": _pick(
                    row, "predicted_ARG-class", "PREDICTED_ARG_CLASS"
                ),
                "probability": _num(
                    _pick(row, "probability", "PREDICTION_PROBABILITY")
                ),
                "identity": _num(
                    _pick(
                        row,
                        "identity",
                        "ALIGNMENT_BESTHIT_IDENTITY (%)",
                        "ALIGNMENT_BESTHIT_IDENTITY",
                    )
                ),
                "contig": _pick(row, "read_id", "QUERY_ID"),
                "best_hit": _pick(row, "best-hit", "BEST_HIT_FROM_DATABASE"),
            }
        )
    return {"predictions": predictions, "source_file": path.name}


_PARSERS = {
    "resfinder": _parse_resfinder,
    "rgi": _parse_rgi,
    "amrfinderplus": _parse_amrfinderplus,
    "abricate": _parse_abricate,
    "deeparg": _parse_deeparg,
}


def parse_native_outputs(
    tool_key: str,
    raw_output: Optional[Path | str],
) -> dict[str, Any]:
    """Parse a tool's own output files into UI rows (never raises)."""
    parser = _PARSERS.get(tool_key)
    if parser is None or raw_output is None:
        return {}

    candidate = Path(raw_output)
    tool_dir = candidate if candidate.is_dir() else candidate.parent
    if not tool_dir.exists():
        return {}

    try:
        return parser(tool_dir) or {}
    except Exception:  # noqa: BLE001 — a bad report must not fail the run
        logger.exception("Could not parse native output for %s", tool_key)
        return {}
