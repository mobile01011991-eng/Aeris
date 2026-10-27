from pathlib import Path

from backend.pipeline.species_id import (
    identify_by_markers,
    identify_species,
    parse_mash_dist_line,
    parse_speciator_payload,
)
from backend.pipeline.organism import load_organism_catalog


def test_parse_speciator_species_name():
    result = parse_speciator_payload(
        {
            "speciesName": "Klebsiella pneumoniae",
            "mashDistance": 0.01,
            "taxId": 573,
        }
    )
    assert result.success
    assert result.detected_name == "Klebsiella pneumoniae"
    assert result.detected_taxid == "573"
    assert result.confidence is not None and result.confidence > 0.8


def test_parse_nested_result():
    result = parse_speciator_payload(
        {"result": {"scientificName": "Escherichia coli", "distance": 0.02}}
    )
    assert result.success
    assert result.detected_name == "Escherichia coli"


def test_parse_mash_dist_line():
    parsed = parse_mash_dist_line("ref.msh\tquery.msh\t0.0123\t0.0\t900/1000")
    assert parsed is not None
    assert abs(parsed[1] - 0.0123) < 1e-9


def test_markers_blaKPC(tmp_path):
    fasta = tmp_path / "kpc.fasta"
    fasta.write_text(
        ">contig blaKPC-2\nATGCGTACGTAGCTAGCTAGCTA\n",
        encoding="utf-8",
    )
    result = identify_by_markers(fasta, load_organism_catalog())
    assert result.success
    assert result.detected_name == "Klebsiella pneumoniae"
    assert result.method == "markers"


def test_dry_run_uses_markers_without_env(tmp_path):
    fasta = tmp_path / "x.fasta"
    fasta.write_text(">argannot~~~(Bla)blaKPC-2~~~\nATGCATGC\n", encoding="utf-8")
    result = identify_species(fasta, dry_run=True, out_dir=tmp_path / "sid")
    assert result.success
    assert "Klebsiella" in (result.detected_name or "")


def test_dry_run_identify_with_mock(tmp_path):
    fasta = tmp_path / "x.fasta"
    fasta.write_text(">contig\nATGC\n", encoding="utf-8")
    result = identify_species(
        fasta,
        dry_run=True,
        out_dir=tmp_path / "sid",
        mock_detected="Staphylococcus aureus",
        mock_confidence=0.88,
    )
    assert result.success
    assert result.detected_name == "Staphylococcus aureus"
    assert result.method == "dry_run"
