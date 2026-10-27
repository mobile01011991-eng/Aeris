"""ResFinder PointFinder wiring: species mapping, command flags, parsing."""

import json

from backend.pipeline.amr_runner import (
    POINTFINDER_DB_PATH,
    AMRToolRunner,
)
from backend.pipeline.organism import load_organism_catalog
from backend.pipeline.tool_reports import (
    POINTFINDER_CONTEXT_FILE,
    parse_native_outputs,
)

# Panels shipped in genomicepidemiology/resfinder:4.7.2
# (/databases/pointfinder_db/config).
POINTFINDER_PANELS = {
    "campylobacter",
    "escherichia_coli",
    "salmonella",
    "plasmodium_falciparum",
    "neisseria_gonorrhoeae",
    "mycobacterium_tuberculosis",
    "enterococcus_faecalis",
    "enterococcus_faecium",
    "klebsiella",
    "helicobacter_pylori",
    "staphylococcus_aureus",
}

# One real PointFinder hit: E. coli gyrA S83L.
POINTFINDER_RESULTS_TSV = (
    "Mutation\tNucleotide change\tAmino acid change\tResistance\tPMID\n"
    "gyrA p.S83L\tTCG -> TTG\tS -> L\tNalidixic Acid, Ciprofloxacin\t8891148\n"
)

RESFINDER_JSON_WITH_MUTATION = {
    "seq_regions": {
        "gyrA;;1;;CP073768.1": {
            "name": "gyrA",
            "identity": 99.96194824961948,
            "coverage": 100.0,
            "query_id": "contig_gyrA gyrA S83L synthetic",
        }
    },
    "seq_variations": {
        "gyrA;;1;;CP073768.1;;83;;l": {
            "seq_regions": ["gyrA;;1;;CP073768.1"],
            "phenotypes": ["ciprofloxacin", "nalidixic acid"],
            "seq_var": "p.S83L",
            "ref_codon": "tcg",
            "var_codon": "ttg",
            "ref_aa": "s",
            "var_aa": "l",
            "ref_start_pos": 83,
            "substitution": True,
            "deletion": False,
            "insertion": False,
            "ref_id": "gyrA;;1;;CP073768.1_83_l",
            "key": "gyrA;;1;;CP073768.1;;83;;l",
            "pmids": ["8891148"],
        }
    },
    "phenotypes": {},
}


def _write_context(tool_dir, status, species, reason=""):
    (tool_dir / POINTFINDER_CONTEXT_FILE).write_text(
        json.dumps({"status": status, "species": species, "reason": reason}),
        encoding="utf-8",
    )


# ----------------------------------------------------------------------
# Species mapping
# ----------------------------------------------------------------------


def test_resfinder_species_only_maps_to_existing_panels():
    catalog = load_organism_catalog()
    for organism in catalog.list_organisms():
        species = organism.resfinder_species
        if species is not None:
            assert species in POINTFINDER_PANELS, organism.id


def test_klebsiella_uses_genus_panel_not_amrfinder_key():
    catalog = load_organism_catalog()
    # AMRFinder wants Klebsiella_pneumoniae; PointFinder only has a genus panel.
    assert catalog.amrfinder_key("Klebsiella pneumoniae") == "Klebsiella_pneumoniae"
    assert catalog.resfinder_species_key("Klebsiella pneumoniae") == "klebsiella"
    assert catalog.resfinder_species_key("Escherichia coli") == "escherichia_coli"
    assert catalog.resfinder_species_key("Pseudomonas aeruginosa") is None
    assert catalog.resfinder_species_key("Other / Unknown") is None
    assert catalog.resfinder_species_key(None) is None


# ----------------------------------------------------------------------
# Command construction
# ----------------------------------------------------------------------


def test_commands_add_pointfinder_for_supported_species(tmp_path):
    runner = AMRToolRunner(dry_run=True)
    fasta = tmp_path / "in.fasta"
    fasta.write_text(">c\nATGC\n", encoding="utf-8")
    raw = tmp_path / "data_resfinder.json"

    local, docker_inner = runner.resfinder_commands(
        fasta, tmp_path, raw, "escherichia_coli"
    )

    for cmd in (local, docker_inner):
        assert "-acq" in cmd
        assert "-c" in cmd
        assert cmd[cmd.index("-s") + 1] == "escherichia_coli"
        assert "--ignore_missing_species" in cmd
    assert docker_inner[docker_inner.index("-db_point") + 1] == POINTFINDER_DB_PATH


def test_commands_are_acquired_only_without_species(tmp_path):
    runner = AMRToolRunner(dry_run=True)
    fasta = tmp_path / "in.fasta"
    fasta.write_text(">c\nATGC\n", encoding="utf-8")
    raw = tmp_path / "data_resfinder.json"

    local, docker_inner = runner.resfinder_commands(fasta, tmp_path, raw, None)

    for cmd in (local, docker_inner):
        assert "-acq" in cmd
        assert "-c" not in cmd
        assert "-s" not in cmd
        assert "-db_point" not in cmd


def test_unsupported_species_skips_pointfinder(tmp_path):
    """Acinetobacter has no panel, so ResFinder must run acquired-only."""
    runner = AMRToolRunner(dry_run=True)
    catalog = load_organism_catalog()
    fasta = tmp_path / "in.fasta"
    fasta.write_text(">c\nATGC\n", encoding="utf-8")
    out_dir = tmp_path / "resfinder"
    out_dir.mkdir()

    runner._resfinder_species = catalog.resfinder_species_key(
        "Acinetobacter baumannii"
    )
    result = runner.run_resfinder(fasta, out_dir)
    assert result.success

    extras = parse_native_outputs("resfinder", out_dir / "data_resfinder.json")
    assert extras["pointfinder_status"] == "skipped"
    assert extras["pointfinder_species"] is None
    assert extras["point_mutations"] == []
    assert extras["pointfinder_reason"]


def test_supported_species_records_ran_context(tmp_path):
    runner = AMRToolRunner(dry_run=True)
    fasta = tmp_path / "in.fasta"
    fasta.write_text(">c\nATGC\n", encoding="utf-8")
    out_dir = tmp_path / "resfinder"
    out_dir.mkdir()

    runner._resfinder_species = "escherichia_coli"
    assert runner.run_resfinder(fasta, out_dir).success

    context = json.loads(
        (out_dir / POINTFINDER_CONTEXT_FILE).read_text(encoding="utf-8")
    )
    assert context == {"status": "ran", "species": "escherichia_coli", "reason": ""}


# ----------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------


def test_parses_point_mutation_from_resfinder_json(tmp_path):
    (tmp_path / "data_resfinder.json").write_text(
        json.dumps(RESFINDER_JSON_WITH_MUTATION), encoding="utf-8"
    )
    (tmp_path / "PointFinder_results.txt").write_text(
        POINTFINDER_RESULTS_TSV, encoding="utf-8"
    )
    _write_context(tmp_path, "ran", "escherichia_coli")

    extras = parse_native_outputs("resfinder", tmp_path / "data_resfinder.json")
    assert extras["pointfinder_status"] == "ran"
    assert extras["pointfinder_species"] == "escherichia_coli"

    row = extras["point_mutations"][0]
    assert row["gene"] == "gyrA"
    assert row["mutation"] == "p.S83L"
    assert row["nucleotide_change"] == "TCG -> TTG"
    assert row["amino_acid_change"] == "S -> L"
    assert row["antimicrobials"] == ["ciprofloxacin", "nalidixic acid"]
    assert row["variation_type"] == "substitution"
    assert row["codon_position"] == 83
    assert row["coverage"] == 100.0
    assert row["contig"] == "contig_gyrA"


def test_parses_point_mutation_from_results_table_only(tmp_path):
    """Fallback when the JSON has no seq_variations section."""
    (tmp_path / "PointFinder_results.txt").write_text(
        POINTFINDER_RESULTS_TSV, encoding="utf-8"
    )
    _write_context(tmp_path, "ran", "escherichia_coli")

    extras = parse_native_outputs("resfinder", tmp_path / "data_resfinder.json")
    row = extras["point_mutations"][0]
    assert row["gene"] == "gyrA"
    assert row["mutation"] == "p.S83L"
    assert row["antimicrobials"] == ["Nalidixic Acid", "Ciprofloxacin"]
    assert extras["pointfinder_status"] == "ran"


def test_ran_with_no_hits_keeps_ran_status(tmp_path):
    """Header-only table is the normal result for a gene-cassette FASTA."""
    (tmp_path / "PointFinder_results.txt").write_text(
        "Mutation\tNucleotide change\tAmino acid change\tResistance\tPMID\n",
        encoding="utf-8",
    )
    _write_context(tmp_path, "ran", "klebsiella")

    extras = parse_native_outputs("resfinder", tmp_path / "data_resfinder.json")
    assert extras["pointfinder_status"] == "ran"
    assert extras["pointfinder_species"] == "klebsiella"
    assert extras["point_mutations"] == []


def test_failed_context_is_reported(tmp_path):
    _write_context(tmp_path, "failed", "escherichia_coli", "boom")

    extras = parse_native_outputs("resfinder", tmp_path / "data_resfinder.json")
    assert extras["pointfinder_status"] == "failed"
    assert extras["pointfinder_reason"] == "boom"
    assert extras["point_mutations"] == []


def test_acquired_phenotypes_still_parsed_alongside_pointfinder(tmp_path):
    (tmp_path / "pheno_table.txt").write_text(
        "# Antimicrobial\tClass\tWGS-predicted phenotype\tMatch\tGenetic background\n"
        "meropenem\tbeta-lactam\tResistant\t3\tblaKPC-2\n",
        encoding="utf-8",
    )
    (tmp_path / "PointFinder_results.txt").write_text(
        POINTFINDER_RESULTS_TSV, encoding="utf-8"
    )
    _write_context(tmp_path, "ran", "escherichia_coli")

    extras = parse_native_outputs("resfinder", tmp_path / "data_resfinder.json")
    assert extras["phenotypes"][0]["antimicrobial"] == "meropenem"
    assert extras["point_mutations"]
