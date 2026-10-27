from backend.pipeline.drug_class_map import normalize_drug_class


def test_carbapenemase_overrides_broad_beta_lactam():
    assert (
        normalize_drug_class("Beta-lactam", gene_symbol="blaKPC-2") == "Carbapenem"
    )


def test_explicit_carbapenem_preserved():
    assert normalize_drug_class("carbapenem", gene_symbol="blaKPC-2") == "Carbapenem"
