"""Native tool-output parsers and the per-tool report surface."""

import time

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.pipeline.tool_reports import (
    AI_TOOL_KEYS,
    DATABASE_TOOL_KEYS,
    gene_family,
    parse_native_outputs,
    strip_gene_prefix,
    tool_kind,
)

client = TestClient(app)


def test_deeparg_is_not_a_database_tool():
    assert "deeparg" not in DATABASE_TOOL_KEYS
    assert AI_TOOL_KEYS == ("deeparg",)
    assert tool_kind("deeparg") == "ai"
    assert all(tool_kind(k) == "database" for k in DATABASE_TOOL_KEYS)


def test_gene_family_normalizes_alleles_to_deeparg_level():
    assert gene_family("blaKPC-2") == "KPC"
    assert gene_family("(Bla)blaKPC-2") == "KPC"
    assert gene_family("blaTEM-1B") == "TEM"
    assert gene_family("blaNDM-1") == "NDM"
    assert gene_family("KPC") == "KPC"
    assert gene_family("") == ""
    assert strip_gene_prefix("(Bla)blaKPC-2") == "blaKPC-2"


def test_parse_resfinder_phenotype_table(tmp_path):
    (tmp_path / "pheno_table.txt").write_text(
        "# ResFinder phenotype results.\n"
        "# Antimicrobial\tClass\tWGS-predicted phenotype\tMatch\tGenetic background\n"
        "gentamicin\taminoglycoside\tNo resistance\t0\t\n"
        "meropenem\tbeta-lactam\tResistant\t3\tblaKPC-2 (blaKPC-2_AY034847)\n",
        encoding="utf-8",
    )

    extras = parse_native_outputs("resfinder", tmp_path / "data_resfinder.json")
    rows = extras["phenotypes"]
    assert len(rows) == 2
    assert rows[1]["antimicrobial"] == "meropenem"
    assert rows[1]["phenotype"] == "Resistant"
    assert rows[1]["match"] == "3"
    assert "blaKPC-2" in rows[1]["genetic_background"]


def test_parse_rgi_keeps_ontology_and_drops_sequences(tmp_path):
    (tmp_path / "rgi.txt").write_text(
        "ORF_ID\tContig\tStart\tStop\tOrientation\tCut_Off\tBest_Hit_ARO\t"
        "Best_Identities\tARO\tModel_type\tSNPs_in_Best_Hit_ARO\tDrug Class\t"
        "Resistance Mechanism\tAMR Gene Family\tPredicted_Protein\t"
        "Percentage Length of Reference Sequence\tAntibiotic\n"
        "contig1_1\tcontig1\t1\t882\t+\tPerfect\tKPC-2\t100.0\t3002312\t"
        "protein homolog model\tn/a\tcarbapenem\tantibiotic inactivation\t"
        "KPC beta-lactamase\tMSLYRR\t100.00\tmeropenem\n",
        encoding="utf-8",
    )

    row = parse_native_outputs("rgi", tmp_path / "rgi.txt")["hits"][0]
    assert row["cut_off"] == "Perfect"
    assert row["resistance_mechanism"] == "antibiotic inactivation"
    assert row["amr_gene_family"] == "KPC beta-lactamase"
    assert row["identity"] == 100.0
    assert "Predicted_Protein" not in row


def test_parse_amrfinderplus_splits_point_and_non_amr(tmp_path):
    (tmp_path / "amrfinder.tsv").write_text(
        "Contig id\tStart\tStop\tStrand\tElement symbol\tElement name\tScope\t"
        "Type\tSubtype\tClass\tSubclass\tMethod\t"
        "% Coverage of reference\t% Identity to reference\t"
        "Closest reference accession\tClosest reference name\n"
        "contig1\t1\t879\t+\tblaKPC-2\tKPC-2\tcore\tAMR\tAMR\tBETA-LACTAM\t"
        "CARBAPENEM\tALLELEX\t100.00\t100.00\tWP_004199234.1\tKPC-2\n"
        "contig2\t5\t900\t+\tgyrA_S83L\tGyrA\tcore\tAMR\tPOINT\tQUINOLONE\t"
        "QUINOLONE\tPOINTX\t100.00\t99.00\tWP_1\tGyrA\n"
        "contig3\t1\t500\t+\tsitA\tSitA\tcore\tVIRULENCE\tVIRULENCE\t\t\t"
        "BLASTX\t99.00\t98.00\tWP_2\tSitA\n",
        encoding="utf-8",
    )

    extras = parse_native_outputs("amrfinderplus", tmp_path / "amrfinder.tsv")
    assert [r["element_symbol"] for r in extras["amr"]] == ["blaKPC-2"]
    assert [r["element_symbol"] for r in extras["point"]] == ["gyrA_S83L"]
    assert [r["element_symbol"] for r in extras["other"]] == ["sitA"]
    assert extras["amr"][0]["method"] == "ALLELEX"


def test_parse_abricate_keeps_original_and_display_gene(tmp_path):
    (tmp_path / "abricate_argannot.tsv").write_text(
        "#FILE\tSEQUENCE\tSTART\tEND\tSTRAND\tGENE\tCOVERAGE\tCOVERAGE_MAP\t"
        "GAPS\t%COVERAGE\t%IDENTITY\tDATABASE\tACCESSION\tPRODUCT\tRESISTANCE\n"
        "in.fasta\tcontig1\t1\t882\t+\t(Bla)blaKPC-2\t1-882/882\t=====\t0/0\t"
        "100.00\t100.00\targannot\tJN048642\t(Bla)blaKPC-2\t\n",
        encoding="utf-8",
    )

    row = parse_native_outputs(
        "abricate", tmp_path / "abricate_argannot.tsv"
    )["hits"][0]
    assert row["gene"] == "(Bla)blaKPC-2"
    assert row["gene_display"] == "blaKPC-2"
    assert row["resistance"] == ""


def test_parse_deeparg_prefers_primary_report(tmp_path):
    header = (
        "#ARG\tquery-start\tquery-end\tread_id\tpredicted_ARG-class\tbest-hit\t"
        "probability\tidentity\n"
    )
    (tmp_path / "deeparg.mapping.ARG").write_text(
        header + "KPC\t1\t293\tcontig1\tbeta-lactam\tAY034847\t0.98\t100\n",
        encoding="utf-8",
    )
    (tmp_path / "deeparg.mapping.potential.ARG").write_text(
        header + "OXA\t1\t100\tcontig9\tbeta-lactam\tXX\t0.4\t60\n",
        encoding="utf-8",
    )

    extras = parse_native_outputs("deeparg", tmp_path / "deeparg.mapping.ARG")
    assert extras["source_file"] == "deeparg.mapping.ARG"
    assert [r["gene_family"] for r in extras["predictions"]] == ["KPC"]
    assert extras["predictions"][0]["probability"] == 0.98


def test_missing_output_returns_no_extras(tmp_path):
    assert parse_native_outputs("rgi", tmp_path / "rgi.txt") == {}
    assert parse_native_outputs("resfinder", None) == {}


def test_demo_job_exposes_a_report_per_tool():
    res = client.post(
        "/api/v1/amr/demo/async?sample_id=test_reports"
        "&declared_organism=klebsiella_pneumoniae"
    )
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    job = {}
    for _ in range(80):
        job = client.get(f"/api/v1/amr/jobs/{job_id}").json()
        if job["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.05)

    assert job["status"] == "completed", job
    reports = job["tool_reports"]
    assert set(reports) == set(DATABASE_TOOL_KEYS) | set(AI_TOOL_KEYS)
    assert reports["deeparg"]["kind"] == "ai"
    assert reports["resfinder"]["extras"]["phenotypes"]
    assert reports["amrfinderplus"]["extras"]["amr"]
    assert job["result"]["tool_reports"].keys() == reports.keys()
