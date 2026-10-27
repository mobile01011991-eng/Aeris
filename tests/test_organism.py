from backend.pipeline.organism import (
    OrganismCatalog,
    OrganismEntry,
    load_organism_catalog,
    normalize_organism_name,
)


def test_normalize_organism_name():
    assert normalize_organism_name("K. pneumoniae") == "k. pneumoniae"
    assert normalize_organism_name("Klebsiella_pneumoniae") == "klebsiella pneumoniae"
    assert normalize_organism_name("  E. coli  ") == "e. coli"


def test_resolve_aliases():
    cat = load_organism_catalog()
    assert cat.resolve("E. coli").id == "escherichia_coli"
    assert cat.resolve("Klebsiella pneumoniae").id == "klebsiella_pneumoniae"
    assert cat.resolve("klebsiella_pneumoniae").id == "klebsiella_pneumoniae"
    assert cat.amrfinder_key("S. aureus") == "Staphylococcus_aureus"


def test_match_same_species():
    cat = load_organism_catalog()
    result = cat.compare("Escherichia coli", "E. coli", confidence=0.9)
    assert result.match_status == "match"


def test_match_genus_level():
    cat = load_organism_catalog()
    result = cat.compare("Klebsiella", "Klebsiella pneumoniae", confidence=0.8)
    assert result.match_status == "match"


def test_mismatch_different_species():
    cat = load_organism_catalog()
    result = cat.compare(
        "Neisseria gonorrhoeae",
        "Staphylococcus aureus",
        confidence=0.95,
    )
    assert result.match_status == "mismatch"
    assert result.detected_name == "Staphylococcus aureus"


def test_uncertain_low_confidence():
    cat = load_organism_catalog()
    result = cat.compare(
        "Escherichia coli",
        "Escherichia coli",
        confidence=0.2,
    )
    assert result.match_status == "uncertain"


def test_uncertain_other_unknown():
    cat = load_organism_catalog()
    result = cat.compare("other_unknown", "Escherichia coli", confidence=0.9)
    assert result.match_status == "uncertain"


def test_failed_detection():
    cat = OrganismCatalog(
        [
            OrganismEntry(
                id="escherichia_coli",
                display_name="Escherichia coli",
                group="Enterobacterales",
                aliases=("E. coli",),
                amrfinder_organism="Escherichia",
            )
        ]
    )
    result = cat.compare("Escherichia coli", None, detection_failed=True)
    assert result.match_status == "failed"
