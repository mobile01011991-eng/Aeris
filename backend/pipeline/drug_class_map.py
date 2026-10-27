"""
Normalize heterogeneous drug_class / gene annotations into canonical classes.

hAMRonized `drug_class` values vary by tool (semicolon lists, ARO labels,
ResFinder phenotype strings). Gene-symbol fallbacks cover gaps when a tool
omits drug_class.
"""

from __future__ import annotations

import re
from typing import Optional

# Canonical drug classes used for consensus voting.
CANONICAL_DRUG_CLASSES = frozenset(
    {
        "Aminoglycoside",
        "Beta-lactam",
        "Carbapenem",
        "Cephalosporin",
        "Fluoroquinolone",
        "Glycopeptide",
        "Macrolide",
        "Phenicol",
        "Rifamycin",
        "Sulfonamide",
        "Tetracycline",
        "Trimethoprim",
        "Colistin",
        "Fosfomycin",
        "Nitroimidazole",
        "Oxazolidinone",
        "Streptogramin",
        "Lincosamide",
        "Fusidic acid",
        "Mupirocin",
        "Bleomycin",
        "Quinolone",
        "Multidrug",
        "Other",
    }
)

# Substring / alias → canonical class (matched case-insensitively).
_CLASS_ALIASES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p, re.I), cls)
    for p, cls in [
        (r"carbapenem", "Carbapenem"),
        (r"beta[-\s]?lactam|penicillin|bla\b", "Beta-lactam"),
        (r"cephalosporin", "Cephalosporin"),
        (r"aminoglycoside|aminoglycosid", "Aminoglycoside"),
        (r"fluoroquinolone|quinolone", "Fluoroquinolone"),
        (r"glycopeptide|vancomycin", "Glycopeptide"),
        (r"macrolide|macrolid", "Macrolide"),
        (r"phenicol|chloramphenicol", "Phenicol"),
        (r"rifam(ycin|pin)", "Rifamycin"),
        (r"sulfonamide|sulphonamide|folate", "Sulfonamide"),
        (r"tetracycline|tetracyclin", "Tetracycline"),
        (r"trimethoprim", "Trimethoprim"),
        (r"colistin|polymyxin", "Colistin"),
        (r"fosfomycin", "Fosfomycin"),
        (r"nitroimidazole|metronidazole", "Nitroimidazole"),
        (r"oxazolidinone|linezolid", "Oxazolidinone"),
        (r"streptogramin", "Streptogramin"),
        (r"lincosamide|clindamycin", "Lincosamide"),
        (r"fusidic", "Fusidic acid"),
        (r"mupirocin", "Mupirocin"),
        (r"bleomycin", "Bleomycin"),
        (r"multi[-\s]?drug|efflux", "Multidrug"),
    ]
]

# Gene-symbol prefix / pattern → canonical class when drug_class is missing.
_GENE_TO_CLASS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p, re.I), cls)
    for p, cls in [
        # Carbapenemases (narrower before generic bla*)
        (r"^bla(KPC|NDM|VIM|IMP|OXA-48|OXA-23|OXA-24|OXA-58|OXA-181|GES)", "Carbapenem"),
        # DeepARG short symbols
        (r"^(KPC|NDM|VIM|IMP|OXA-48|GES)([-_]|$)", "Carbapenem"),
        (r"^bla(TEM|SHV|CTX-M|OXA|PER|VEB|BEL|CMY|DHA|FOX|LAT|ACT|MIR|ADC)", "Beta-lactam"),
        (r"^(TEM|SHV|CTX-M)([-_]|$)", "Beta-lactam"),
        (r"^bla", "Beta-lactam"),
        (r"^(mecA|mecC|pbp)", "Beta-lactam"),
        (r"^(aac|aad|ant|aph|armA|rmt|npmA)", "Aminoglycoside"),
        (r"^(qnr|oqx|qepA|aac\(6'\)-Ib-cr)", "Fluoroquinolone"),
        (r"^(gyrA|parC|parE)", "Fluoroquinolone"),
        (r"^(van[A-Z])", "Glycopeptide"),
        (r"^(erm|mph|mef|msr|ere)", "Macrolide"),
        (r"^(cat|cml|floR|fex)", "Phenicol"),
        (r"^(rpoB|arr)", "Rifamycin"),
        (r"^(sul[123])", "Sulfonamide"),
        (r"^(tet[A-Z]|tet\()", "Tetracycline"),
        (r"^(dfr)", "Trimethoprim"),
        (r"^(mcr)", "Colistin"),
        (r"^(fos[A-Z]|fos)", "Fosfomycin"),
        (r"^(nim)", "Nitroimidazole"),
        (r"^(cfr|optrA|poxtA)", "Oxazolidinone"),
        (r"^(vat|vgb)", "Streptogramin"),
        (r"^(lnu|lsa)", "Lincosamide"),
        (r"^(fus)", "Fusidic acid"),
        (r"^(mup)", "Mupirocin"),
        (r"^(ble)", "Bleomycin"),
    ]
]


def _split_multi_class(raw: str) -> list[str]:
    """Split tool-specific multi-class strings (`;`, `,`, `/`, `|`)."""
    parts = re.split(r"[;,/|]+", raw)
    return [p.strip() for p in parts if p.strip()]


# When a tool reports a broad parent class, gene-symbol resolution may be narrower
# (e.g. drug_class=Beta-lactam + blaKPC → Carbapenem).
_BROAD_PARENTS = frozenset({"Beta-lactam", "Other", "Multidrug"})


def _resolve_from_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    for token in _split_multi_class(str(text)):
        resolved = _match_alias(token)
        if resolved:
            return resolved
        for canonical in CANONICAL_DRUG_CLASSES:
            if canonical.lower() == token.lower():
                return canonical
    return None


def _clean_gene_symbol(gene_symbol: str) -> str:
    """Strip ABRicate-style phenotype prefixes, e.g. ``(Bla)blaKPC-2`` → ``blaKPC-2``."""
    text = gene_symbol.strip()
    text = re.sub(r"^\([^)]+\)", "", text)
    return text.strip()


def _resolve_from_gene(gene_symbol: Optional[str]) -> Optional[str]:
    if not gene_symbol:
        return None
    cleaned = _clean_gene_symbol(gene_symbol)
    for pattern, cls in _GENE_TO_CLASS:
        if pattern.search(cleaned) or pattern.search(gene_symbol.strip()):
            return cls
    return None


def normalize_drug_class(
    drug_class: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    antimicrobial_agent: Optional[str] = None,
) -> str:
    """
    Map a hAMRonized hit to a single canonical drug class.

    Preference order:
      1. Explicit drug_class (first resolvable token if multi-valued)
      2. antimicrobial_agent
      3. gene_symbol heuristics
      4. \"Other\"

    If the tool class is a broad parent (e.g. Beta-lactam) and the gene maps to a
    more specific class (e.g. Carbapenem), the gene mapping wins.
    """
    from_class = _resolve_from_text(drug_class)
    from_agent = _resolve_from_text(antimicrobial_agent)
    from_gene = _resolve_from_gene(gene_symbol)

    primary = from_class or from_agent
    if primary and from_gene and primary in _BROAD_PARENTS and from_gene != primary:
        return from_gene
    if primary:
        return primary
    if from_gene:
        return from_gene
    return "Other"


def _match_alias(text: str) -> Optional[str]:
    for pattern, cls in _CLASS_ALIASES:
        if pattern.search(text):
            return cls
    return None
