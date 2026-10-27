"""
Convert modern DeepARG ``*.mapping.ARG`` (gaarangoa/deeparg) to the legacy
column names expected by ``hamronize deeparg``.
"""

from __future__ import annotations

import csv
from pathlib import Path

# Modern DeepARG (HF / PyTorch runtime) → legacy DeepARG columns for hAMRonization
_COLUMN_MAP = {
    "ARG_NAME": "#ARG",
    "QUERY_START": "query-start",
    "QUERY_END": "query-end",
    "QUERY_ID": "read_id",
    "PREDICTED_ARG_CLASS": "predicted_ARG-class",
    "BEST_HIT_FROM_DATABASE": "best-hit",
    "PREDICTION_PROBABILITY": "probability",
    "ALIGNMENT_BESTHIT_IDENTITY (%)": "identity",
    "ALIGNMENT_BESTHIT_IDENTITY": "identity",
    "ALIGNMENT_BESTHIT_LENGTH": "alignment-length",
    "ALIGNMENT_BESTHIT_BITSCORE": "alignment-bitscore",
    "ALIGNMENT_BESTHIT_EVALUE": "alignment-evalue",
    "COUNTS": "counts",
}

_LEGACY_HEADER = [
    "#ARG",
    "query-start",
    "query-end",
    "read_id",
    "predicted_ARG-class",
    "best-hit",
    "probability",
    "identity",
    "alignment-length",
    "alignment-bitscore",
    "alignment-evalue",
    "counts",
]


def is_modern_deeparg_report(path: Path) -> bool:
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        header = fh.readline().strip().split("\t")
    return "ARG_NAME" in header or "PREDICTED_ARG_CLASS" in header


def convert_deeparg_report(src: Path, dest: Path) -> Path:
    """
    If ``src`` is already legacy-formatted, copy as-is.
    Otherwise rewrite to legacy TSV for hamronize.
    """
    with src.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"Empty DeepARG report: {src}")

        fields = list(reader.fieldnames)
        modern = "ARG_NAME" in fields or "PREDICTED_ARG_CLASS" in fields
        rows = list(reader)

    if not modern:
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        return dest

    with dest.open("w", encoding="utf-8", newline="\n") as out:
        writer = csv.DictWriter(out, fieldnames=_LEGACY_HEADER, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            legacy = {h: "" for h in _LEGACY_HEADER}
            for modern_key, legacy_key in _COLUMN_MAP.items():
                if modern_key in row and row[modern_key] not in (None, ""):
                    legacy[legacy_key] = str(row[modern_key]).strip()
            # Fallback: strip (%) suffix variants already handled by map keys
            writer.writerow(legacy)

    return dest
