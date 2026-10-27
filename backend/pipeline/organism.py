"""Organism catalog, name normalization, and declared-vs-detected matching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

DEFAULT_ORGANISM_CONFIG = Path(__file__).resolve().parents[2] / "config" / "organism_groups.yaml"


def normalize_organism_name(name: Optional[str]) -> str:
    """Lowercase, strip punctuation quirks, collapse whitespace for comparison."""
    if not name:
        return ""
    text = str(name).strip().lower()
    text = text.replace("_", " ")
    text = re.sub(r"[^\w\s.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Expand common genus abbreviations: "e. coli" already fine; "k pneumoniae" → keep
    text = re.sub(r"^([a-z])\.\s+", r"\1. ", text)
    return text


@dataclass(frozen=True)
class OrganismEntry:
    id: str
    display_name: str
    group: str
    aliases: tuple[str, ...]
    amrfinder_organism: Optional[str]
    # PointFinder db_prefix; None when PointFinder has no panel for the species.
    resfinder_species: Optional[str] = None

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "group": self.group,
            "aliases": list(self.aliases),
            "amrfinder_organism": self.amrfinder_organism,
            "resfinder_species": self.resfinder_species,
        }


@dataclass
class OrganismMatchResult:
    match_status: str  # match | mismatch | uncertain | failed
    declared_id: Optional[str]
    declared_name: Optional[str]
    detected_name: Optional[str]
    detected_id: Optional[str] = None
    confidence: Optional[float] = None
    reason: str = ""
    amrfinder_organism: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_status": self.match_status,
            "declared_id": self.declared_id,
            "declared_name": self.declared_name,
            "detected_name": self.detected_name,
            "detected_id": self.detected_id,
            "confidence": self.confidence,
            "reason": self.reason,
            "amrfinder_organism": self.amrfinder_organism,
        }


class OrganismCatalog:
    def __init__(
        self,
        organisms: list[OrganismEntry],
        confidence_threshold: float = 0.55,
    ) -> None:
        self.organisms = organisms
        self.confidence_threshold = float(confidence_threshold)
        self._by_id = {o.id: o for o in organisms}
        self._alias_index: dict[str, OrganismEntry] = {}
        for org in organisms:
            for alias in (org.display_name, *org.aliases, org.id.replace("_", " ")):
                key = normalize_organism_name(alias)
                if key:
                    self._alias_index[key] = org

    def list_organisms(self) -> list[OrganismEntry]:
        return list(self.organisms)

    def get(self, organism_id: str) -> Optional[OrganismEntry]:
        return self._by_id.get(organism_id)

    def resolve(self, name_or_id: Optional[str]) -> Optional[OrganismEntry]:
        if not name_or_id:
            return None
        if name_or_id in self._by_id:
            return self._by_id[name_or_id]
        key = normalize_organism_name(name_or_id)
        if key in self._alias_index:
            return self._alias_index[key]
        # Partial: genus-level match if unique
        tokens = key.split()
        if tokens:
            genus = tokens[0].rstrip(".")
            hits = [
                o
                for o in self.organisms
                if normalize_organism_name(o.display_name).startswith(genus)
                or any(
                    normalize_organism_name(a).startswith(genus) for a in o.aliases
                )
            ]
            # Prefer exact genus + species when available
            if len(hits) == 1:
                return hits[0]
            for o in hits:
                disp = normalize_organism_name(o.display_name)
                if disp == key or disp.startswith(key) or key.startswith(disp):
                    return o
            # Same genus shared by multiple — still accept if declared is that genus group
            if len(tokens) == 1 and hits:
                return hits[0]
        return None

    def amrfinder_key(self, name_or_id: Optional[str]) -> Optional[str]:
        entry = self.resolve(name_or_id)
        return entry.amrfinder_organism if entry else None

    def resfinder_species_key(self, name_or_id: Optional[str]) -> Optional[str]:
        """PointFinder db_prefix for an organism, or None when unsupported."""
        entry = self.resolve(name_or_id)
        return entry.resfinder_species if entry else None

    def compare(
        self,
        declared: Optional[str],
        detected_name: Optional[str],
        *,
        confidence: Optional[float] = None,
        detection_failed: bool = False,
    ) -> OrganismMatchResult:
        declared_entry = self.resolve(declared)
        declared_id = declared_entry.id if declared_entry else None
        declared_name = (
            declared_entry.display_name if declared_entry else (declared or None)
        )

        if detection_failed:
            return OrganismMatchResult(
                match_status="failed",
                declared_id=declared_id,
                declared_name=declared_name,
                detected_name=None,
                confidence=confidence,
                reason="Species identification failed",
            )

        if not detected_name:
            return OrganismMatchResult(
                match_status="uncertain",
                declared_id=declared_id,
                declared_name=declared_name,
                detected_name=None,
                confidence=confidence,
                reason="No species detected from sequence",
            )

        detected_entry = self.resolve(detected_name)
        detected_id = detected_entry.id if detected_entry else None

        if confidence is not None and confidence < self.confidence_threshold:
            return OrganismMatchResult(
                match_status="uncertain",
                declared_id=declared_id,
                declared_name=declared_name,
                detected_name=detected_name,
                detected_id=detected_id,
                confidence=confidence,
                reason=f"Low confidence ({confidence:.2f} < {self.confidence_threshold})",
                amrfinder_organism=(
                    detected_entry.amrfinder_organism if detected_entry else None
                ),
            )

        # "Other / Unknown" declared → always treat as needing confirmation unless empty detect
        if declared_entry and declared_entry.id == "other_unknown":
            return OrganismMatchResult(
                match_status="uncertain",
                declared_id=declared_id,
                declared_name=declared_name,
                detected_name=detected_name,
                detected_id=detected_id,
                confidence=confidence,
                reason="Declared organism is Other/Unknown",
                amrfinder_organism=(
                    detected_entry.amrfinder_organism if detected_entry else None
                ),
            )

        if declared_entry and detected_entry and declared_entry.id == detected_entry.id:
            return OrganismMatchResult(
                match_status="match",
                declared_id=declared_id,
                declared_name=declared_name,
                detected_name=detected_entry.display_name,
                detected_id=detected_id,
                confidence=confidence,
                reason="Declared organism matches detected species",
                amrfinder_organism=declared_entry.amrfinder_organism,
            )

        # Same group genus-level soft match: e.g. declared Klebsiella, detected K. pneumoniae
        if declared_entry and detected_entry:
            d_genus = normalize_organism_name(declared_entry.display_name).split()[0]
            t_genus = normalize_organism_name(detected_entry.display_name).split()[0]
            if d_genus.rstrip(".") == t_genus.rstrip("."):
                return OrganismMatchResult(
                    match_status="match",
                    declared_id=declared_id,
                    declared_name=declared_name,
                    detected_name=detected_entry.display_name,
                    detected_id=detected_id,
                    confidence=confidence,
                    reason="Genus-level match between declared and detected",
                    amrfinder_organism=detected_entry.amrfinder_organism
                    or declared_entry.amrfinder_organism,
                )

        # Fuzzy string equality after normalize
        if (
            declared_name
            and detected_name
            and normalize_organism_name(declared_name)
            == normalize_organism_name(detected_name)
        ):
            return OrganismMatchResult(
                match_status="match",
                declared_id=declared_id,
                declared_name=declared_name,
                detected_name=detected_name,
                detected_id=detected_id,
                confidence=confidence,
                reason="Normalized names are equal",
                amrfinder_organism=self.amrfinder_key(detected_name),
            )

        return OrganismMatchResult(
            match_status="mismatch",
            declared_id=declared_id,
            declared_name=declared_name,
            detected_name=(
                detected_entry.display_name if detected_entry else detected_name
            ),
            detected_id=detected_id,
            confidence=confidence,
            reason="Declared organism does not match detected species",
            amrfinder_organism=(
                detected_entry.amrfinder_organism if detected_entry else None
            ),
        )


def load_organism_catalog(path: Optional[Path] = None) -> OrganismCatalog:
    cfg_path = Path(path) if path else DEFAULT_ORGANISM_CONFIG
    if not cfg_path.exists():
        return OrganismCatalog([], confidence_threshold=0.55)
    with cfg_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    organisms: list[OrganismEntry] = []
    for row in data.get("organisms", []) or []:
        organisms.append(
            OrganismEntry(
                id=str(row["id"]),
                display_name=str(row["display_name"]),
                group=str(row.get("group", "Other")),
                aliases=tuple(str(a) for a in (row.get("aliases") or [])),
                amrfinder_organism=row.get("amrfinder_organism"),
                resfinder_species=row.get("resfinder_species"),
            )
        )
    return OrganismCatalog(
        organisms,
        confidence_threshold=float(data.get("confidence_threshold", 0.55)),
    )


@lru_cache(maxsize=1)
def get_default_catalog() -> OrganismCatalog:
    return load_organism_catalog()
