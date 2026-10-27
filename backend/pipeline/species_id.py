"""Species identification: Mash sketches (primary), Speciator (optional), marker fallback."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from .organism import OrganismCatalog, get_default_catalog, load_organism_catalog

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "tools.yaml"
DEFAULT_MASH_DIR = Path(__file__).resolve().parents[2] / "data" / "species_mash"

# Gene / header markers → likely organism_id (for gene-cassette / short assemblies)
_MARKER_RULES: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"\bmecA\b|\bmecC\b", re.I), "staphylococcus_aureus", 0.72),
    (re.compile(r"\bvanA\b|\bvanB\b", re.I), "enterococcus_faecium", 0.7),
    (re.compile(r"\bblaKPC\b|\bkpc-", re.I), "klebsiella_pneumoniae", 0.68),
    (re.compile(r"\bblaNDM\b|\bndm-", re.I), "klebsiella_pneumoniae", 0.62),
    (re.compile(r"\bblaOXA-48\b|\boxa-48", re.I), "klebsiella_pneumoniae", 0.6),
    (re.compile(r"\bblaCTX-M\b|\bblaTEM\b|\bblaSHV\b", re.I), "escherichia_coli", 0.55),
    (re.compile(r"\bmcr-1\b|\bmcr1\b", re.I), "escherichia_coli", 0.58),
    (re.compile(r"\bspa\b|\bpvl\b", re.I), "staphylococcus_aureus", 0.65),
    (re.compile(r"gonorrhoeae|neisseria", re.I), "neisseria_gonorrhoeae", 0.8),
    (re.compile(r"pseudomonas", re.I), "pseudomonas_aeruginosa", 0.75),
    (re.compile(r"acinetobacter", re.I), "acinetobacter_baumannii", 0.75),
    (re.compile(r"klebsiella", re.I), "klebsiella_pneumoniae", 0.8),
    (re.compile(r"escherichia|e\.?\s*coli", re.I), "escherichia_coli", 0.8),
    (re.compile(r"salmonella", re.I), "salmonella_enterica", 0.8),
    (re.compile(r"enterococcus\s*faecalis", re.I), "enterococcus_faecalis", 0.8),
    (re.compile(r"enterococcus", re.I), "enterococcus_faecium", 0.7),
]


def _docker_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


@dataclass
class SpeciesIdResult:
    success: bool
    detected_name: Optional[str] = None
    detected_taxid: Optional[str] = None
    confidence: Optional[float] = None
    mash_distance: Optional[float] = None
    raw: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    method: str = "mash"

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "detected_name": self.detected_name,
            "detected_taxid": self.detected_taxid,
            "confidence": self.confidence,
            "mash_distance": self.mash_distance,
            "raw": self.raw,
            "error": self.error,
            "method": self.method,
        }


def _confidence_from_distance(distance: Optional[float]) -> Optional[float]:
    if distance is None:
        return None
    try:
        d = float(distance)
    except (TypeError, ValueError):
        return None
    if d <= 0:
        return 1.0
    if d >= 0.15:
        return 0.05
    return max(0.0, min(1.0, 1.0 - (d / 0.15)))


def parse_speciator_payload(data: Any) -> SpeciesIdResult:
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        return SpeciesIdResult(
            success=False, error="Unrecognized Speciator output", raw={}, method="speciator"
        )

    for nest in ("result", "species", "match", "bestMatch", "assignment"):
        inner = data.get(nest)
        if isinstance(inner, dict):
            merged = {**data, **inner}
            break
        if isinstance(inner, str) and inner.strip():
            merged = {**data, "speciesName": inner}
            break
    else:
        merged = data

    name_keys = (
        "speciesName",
        "species_name",
        "scientificName",
        "scientific_name",
        "organismName",
        "organism_name",
        "organism",
        "species",
        "taxonName",
        "taxon_name",
        "name",
    )
    detected = None
    for key in name_keys:
        val = merged.get(key)
        if isinstance(val, str) and val.strip() and val.strip().lower() not in {
            "unknown",
            "unclassified",
            "none",
            "null",
        }:
            detected = val.strip()
            break

    taxid = None
    for key in ("taxId", "taxid", "taxonId", "taxon_id", "speciesTaxId", "organism_code"):
        if merged.get(key) is not None:
            taxid = str(merged[key])
            break

    distance = None
    for key in ("mashDistance", "mash_distance", "distance", "minDistance", "dist"):
        if merged.get(key) is not None:
            try:
                distance = float(merged[key])
            except (TypeError, ValueError):
                distance = None
            break

    confidence = None
    for key in ("confidence", "score", "identity"):
        if merged.get(key) is not None:
            try:
                confidence = float(merged[key])
                if confidence > 1.0:
                    confidence = confidence / 100.0
            except (TypeError, ValueError):
                confidence = None
            break
    if confidence is None:
        confidence = _confidence_from_distance(distance)

    if not detected:
        return SpeciesIdResult(
            success=False,
            detected_taxid=taxid,
            confidence=confidence,
            mash_distance=distance,
            raw=data if isinstance(data, dict) else {"value": data},
            error="Speciator did not report a species name",
            method="speciator",
        )

    return SpeciesIdResult(
        success=True,
        detected_name=detected,
        detected_taxid=taxid,
        confidence=confidence,
        mash_distance=distance,
        raw=data if isinstance(data, dict) else {"value": data},
        method="speciator",
    )


def _fasta_total_bases(path: Path, limit_bytes: int = 2_000_000) -> int:
    total = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.startswith(">"):
                    continue
                total += len(re.sub(r"\s+", "", line))
                if total > limit_bytes:
                    break
    except OSError:
        return 0
    return total


def _read_fasta_text(path: Path, limit_chars: int = 500_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit_chars]
    except OSError:
        return ""


def identify_by_markers(
    input_path: Path,
    catalog: OrganismCatalog,
) -> SpeciesIdResult:
    text = _read_fasta_text(input_path)
    if not text.strip():
        return SpeciesIdResult(
            success=False, error="Empty FASTA", method="markers"
        )

    best: Optional[tuple[str, float, str]] = None
    for pattern, organism_id, score in _MARKER_RULES:
        if pattern.search(text):
            if best is None or score > best[1]:
                best = (organism_id, score, pattern.pattern)

    if not best:
        return SpeciesIdResult(
            success=False,
            error="No species markers found in sequence headers/content",
            method="markers",
            raw={"scanned_chars": len(text)},
        )

    entry = catalog.get(best[0]) or catalog.resolve(best[0])
    name = entry.display_name if entry else best[0]
    return SpeciesIdResult(
        success=True,
        detected_name=name,
        confidence=best[1],
        method="markers",
        raw={"organism_id": best[0], "rule": best[2], "bases": _fasta_total_bases(input_path)},
    )


def parse_mash_dist_line(line: str) -> Optional[tuple[str, float]]:
    # reference query distance p-value shared-hashes
    parts = line.strip().split("\t")
    if len(parts) < 3:
        return None
    ref, _query, dist_s = parts[0], parts[1], parts[2]
    try:
        dist = float(dist_s)
    except ValueError:
        return None
    return ref, dist


class SpeciesIdentifier:
    """Identify isolate species via Mash DB, optional Speciator, then markers."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        dry_run: bool = False,
        docker_bin: str = "docker",
        catalog: Optional[OrganismCatalog] = None,
        mash_dir: Optional[Path] = None,
    ) -> None:
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load_config(self.config_path)
        self.species_cfg: dict[str, Any] = self.config.get("species_id") or {}
        self.mash_cfg: dict[str, Any] = self.species_cfg.get("mash") or {}
        self.speciator_cfg: dict[str, Any] = self.species_cfg.get("speciator") or {}
        docker_cfg = self.config.get("docker", {})
        self.use_docker = bool(docker_cfg.get("enabled", True))
        self.dry_run = dry_run
        self.docker_bin = docker_bin
        self.catalog = catalog or get_default_catalog()
        self.mash_dir = Path(
            mash_dir
            or self.mash_cfg.get("db_path")
            or os.environ.get("AERIS_SPECIES_MASH_DIR")
            or DEFAULT_MASH_DIR
        )
        self.mash_image = self.mash_cfg.get("image", "staphb/mash:2.3")
        self.prefer = str(self.species_cfg.get("prefer", "mash")).lower()

    def identify(
        self,
        input_path: Path | str,
        out_dir: Optional[Path | str] = None,
        *,
        mock_detected: Optional[str] = None,
        mock_confidence: Optional[float] = None,
    ) -> SpeciesIdResult:
        input_path = Path(input_path).resolve()
        if not input_path.exists():
            return SpeciesIdResult(success=False, error=f"Input not found: {input_path}")

        work = Path(out_dir) if out_dir else input_path.parent / "species_id"
        work.mkdir(parents=True, exist_ok=True)
        out_json = work / "species_id.json"

        if self.dry_run:
            result = self._dry_run_result(
                input_path,
                mock_detected=mock_detected,
                mock_confidence=mock_confidence,
            )
            out_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
            return result

        errors: list[str] = []
        methods = self._method_order()

        for method in methods:
            try:
                if method == "mash":
                    result = self._identify_mash(input_path, work)
                elif method == "speciator":
                    result = self._identify_speciator(input_path, work)
                elif method == "markers":
                    result = identify_by_markers(input_path, self.catalog)
                else:
                    continue
            except Exception as exc:  # noqa: BLE001
                logger.warning("Species ID method %s failed: %s", method, exc)
                errors.append(f"{method}: {exc}")
                continue

            if result.success and result.detected_name:
                out_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
                return result
            if result.error:
                errors.append(f"{method}: {result.error}")

        result = SpeciesIdResult(
            success=False,
            error="; ".join(errors) if errors else "All species ID methods failed",
            method="none",
            raw={"errors": errors},
        )
        out_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        return result

    def _method_order(self) -> list[str]:
        if self.prefer == "speciator":
            return ["speciator", "mash", "markers"]
        if self.prefer == "markers":
            return ["markers", "mash", "speciator"]
        return ["mash", "markers", "speciator"]

    def _dry_run_result(
        self,
        input_path: Path,
        *,
        mock_detected: Optional[str],
        mock_confidence: Optional[float],
    ) -> SpeciesIdResult:
        detected = mock_detected or os.environ.get("AERIS_MOCK_SPECIES")
        confidence = mock_confidence
        if confidence is None and os.environ.get("AERIS_MOCK_SPECIES_CONFIDENCE"):
            try:
                confidence = float(os.environ["AERIS_MOCK_SPECIES_CONFIDENCE"])
            except ValueError:
                confidence = 0.9

        if detected:
            return SpeciesIdResult(
                success=True,
                detected_name=detected,
                confidence=confidence if confidence is not None else 0.92,
                mash_distance=0.01,
                raw={"dry_run": True, "source": "mock"},
                method="dry_run",
            )

        # Prefer marker scan even in dry-run so local demos work without env vars
        marker = identify_by_markers(input_path, self.catalog)
        if marker.success:
            marker.method = "dry_run_markers"
            marker.raw = {**(marker.raw or {}), "dry_run": True}
            return marker

        return SpeciesIdResult(
            success=False,
            error="dry-run: no mock species and no markers found",
            method="dry_run",
        )

    def _load_mash_index(self) -> Optional[dict[str, Any]]:
        index_path = self.mash_dir / "index.json"
        if not index_path.exists():
            return None
        return json.loads(index_path.read_text(encoding="utf-8"))

    def _identify_mash(self, input_path: Path, work: Path) -> SpeciesIdResult:
        index = self._load_mash_index()
        if not index or not index.get("references"):
            return SpeciesIdResult(
                success=False,
                error=(
                    f"Mash species DB missing at {self.mash_dir}. "
                    "Run: python scripts/build_species_mash_db.py"
                ),
                method="mash",
            )

        sketches_dir = self.mash_dir / "sketches"
        if not sketches_dir.exists():
            return SpeciesIdResult(
                success=False,
                error=f"Mash sketches directory missing: {sketches_dir}",
                method="mash",
            )

        query_prefix = work / "query"
        query_msh = work / "query.msh"
        self._mash_sketch(input_path, query_prefix)

        max_distance = float(index.get("max_distance", self.mash_cfg.get("max_distance", 0.12)))
        distance_threshold = float(
            index.get("distance_threshold", self.mash_cfg.get("distance_threshold", 0.05))
        )

        best: Optional[dict[str, Any]] = None
        rows: list[dict[str, Any]] = []
        for ref in index["references"]:
            sketch_rel = ref["sketch"]
            sketch_path = self.mash_dir / sketch_rel
            if not sketch_path.exists():
                continue
            dist = self._mash_dist(sketch_path, query_msh)
            if dist is None:
                continue
            row = {
                "organism_id": ref["organism_id"],
                "display_name": ref["display_name"],
                "distance": dist,
            }
            rows.append(row)
            if best is None or dist < best["distance"]:
                best = row

        rows.sort(key=lambda r: r["distance"])
        (work / "mash_dist.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

        if not best:
            return SpeciesIdResult(
                success=False,
                error="Mash produced no distances",
                method="mash",
                raw={"rows": rows},
            )

        if best["distance"] > max_distance:
            # Short gene-only FASTAs often fail Mash vs full genomes — soft-fail to next method
            return SpeciesIdResult(
                success=False,
                error=(
                    f"Best Mash hit {best['display_name']} distance "
                    f"{best['distance']:.4f} > max {max_distance}"
                ),
                mash_distance=best["distance"],
                method="mash",
                raw={"best": best, "top": rows[:5]},
            )

        confidence = _confidence_from_distance(best["distance"]) or 0.0
        if best["distance"] <= distance_threshold:
            confidence = max(confidence, 0.75)
        else:
            # Between threshold and max → lower confidence (uncertain gate)
            confidence = min(confidence, 0.65)

        return SpeciesIdResult(
            success=True,
            detected_name=best["display_name"],
            confidence=confidence,
            mash_distance=best["distance"],
            method="mash",
            raw={"best": best, "top": rows[:5]},
        )

    def _mash_sketch(self, fasta: Path, prefix: Path) -> Path:
        out_dir = prefix.parent
        cmd = [
            self.docker_bin,
            "run",
            "--rm",
            "-v",
            f"{_docker_path(fasta.parent)}:/data/in:ro",
            "-v",
            f"{_docker_path(out_dir)}:/data/out",
            self.mash_image,
            "mash",
            "sketch",
            "-k",
            str(int(self.mash_cfg.get("k", 21))),
            "-s",
            str(int(self.mash_cfg.get("sketch_size", 1000))),
            "-o",
            f"/data/out/{prefix.name}",
            f"/data/in/{fasta.name}",
        ]
        logger.info("Mash sketch: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(
                f"mash sketch failed ({proc.returncode}): {(proc.stderr or proc.stdout)[:800]}"
            )
        msh = Path(str(prefix) + ".msh")
        if not msh.exists():
            raise FileNotFoundError(f"mash sketch missing: {msh}")
        return msh

    def _mash_dist(self, ref_msh: Path, query_msh: Path) -> Optional[float]:
        # Mount both parent dirs
        ref_dir = ref_msh.parent.resolve()
        query_dir = query_msh.parent.resolve()
        if ref_dir == query_dir:
            cmd = [
                self.docker_bin,
                "run",
                "--rm",
                "-v",
                f"{_docker_path(ref_dir)}:/data:ro",
                self.mash_image,
                "mash",
                "dist",
                f"/data/{ref_msh.name}",
                f"/data/{query_msh.name}",
            ]
        else:
            cmd = [
                self.docker_bin,
                "run",
                "--rm",
                "-v",
                f"{_docker_path(ref_dir)}:/ref:ro",
                "-v",
                f"{_docker_path(query_dir)}:/query:ro",
                self.mash_image,
                "mash",
                "dist",
                f"/ref/{ref_msh.name}",
                f"/query/{query_msh.name}",
            ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            logger.warning("mash dist failed: %s", proc.stderr or proc.stdout)
            return None
        for line in (proc.stdout or "").splitlines():
            parsed = parse_mash_dist_line(line)
            if parsed:
                return parsed[1]
        return None

    def _identify_speciator(self, input_path: Path, work: Path) -> SpeciesIdResult:
        image = self.speciator_cfg.get("image", "speciator:latest")
        # Skip quickly if image is clearly unset / library missing and prefer mash
        library_path = self.speciator_cfg.get("library_path") or os.environ.get(
            "SPECIATOR_LIBRARY"
        )
        lib = Path(library_path) if library_path else None
        if lib and not lib.exists():
            return SpeciesIdResult(
                success=False,
                error=f"Speciator library missing: {lib}",
                method="speciator",
            )

        out_json = work / "speciator.json"
        input_dir = input_path.parent.resolve()
        bash_inner = (
            f"speciator fasta /data/input/{input_path.name} "
            f"> /data/out/speciator.json"
        )
        cmd = [
            self.docker_bin,
            "run",
            "--rm",
            "-v",
            f"{_docker_path(input_dir)}:/data/input:ro",
            "-v",
            f"{_docker_path(work)}:/data/out",
        ]
        if lib and lib.exists():
            cmd.extend(["-v", f"{_docker_path(lib.resolve())}:/speciator/library:ro"])
        cmd.extend([image, "bash", "-lc", bash_inner])

        logger.info("Speciator: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        payload = None
        if out_json.exists() and out_json.stat().st_size > 0:
            try:
                payload = json.loads(out_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = None
        if payload is None and proc.stdout:
            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError:
                payload = None
        if payload is None:
            return SpeciesIdResult(
                success=False,
                error=(
                    f"Speciator failed ({proc.returncode}): "
                    f"{(proc.stderr or proc.stdout or '')[:500]}"
                ),
                method="speciator",
            )
        return parse_speciator_payload(payload)

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}


def identify_species(
    input_path: Path | str,
    *,
    dry_run: bool = False,
    out_dir: Optional[Path | str] = None,
    config_path: Optional[Path] = None,
    mock_detected: Optional[str] = None,
    mock_confidence: Optional[float] = None,
    catalog: Optional[OrganismCatalog] = None,
) -> SpeciesIdResult:
    identifier = SpeciesIdentifier(
        config_path=config_path,
        dry_run=dry_run,
        catalog=catalog or load_organism_catalog(),
    )
    return identifier.identify(
        input_path,
        out_dir=out_dir,
        mock_detected=mock_detected,
        mock_confidence=mock_confidence,
    )
