"""API-level tests for organism confirmation gate (in-memory jobs)."""

import time

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_list_organisms():
    res = client.get("/api/v1/amr/organisms")
    assert res.status_code == 200
    data = res.json()
    assert "organisms" in data
    assert any(o["id"] == "escherichia_coli" for o in data["organisms"])


def test_analyze_requires_declared_organism(tmp_path):
    fasta = tmp_path / "x.fasta"
    fasta.write_text(">c\nATGC\n", encoding="utf-8")
    with fasta.open("rb") as fh:
        res = client.post(
            "/api/v1/amr/analyze/async",
            files={"file": ("x.fasta", fh, "application/octet-stream")},
        )
    assert res.status_code == 400


def test_confirm_accept_after_mismatch(monkeypatch, tmp_path):
    from backend.pipeline.species_id import SpeciesIdResult

    def fake_identify(*args, **kwargs):
        return SpeciesIdResult(
            success=True,
            detected_name="Staphylococcus aureus",
            confidence=0.95,
            mash_distance=0.01,
            method="mock",
        )

    monkeypatch.setattr("backend.api.main.identify_species", fake_identify)

    # Avoid running real Docker AMR tools after confirm
    def fake_continue(job):
        job.status = "completed"
        job.result = {
            "sample_id": job.sample_id,
            "organism": {"confirmed": job.confirmed_organism},
        }
        job.touch()

    monkeypatch.setattr("backend.api.main._continue_amr", fake_continue)

    fasta = tmp_path / "sample.fasta"
    fasta.write_text(">c\nATGCATGC\n", encoding="utf-8")

    with fasta.open("rb") as fh:
        res = client.post(
            "/api/v1/amr/analyze/async?declared_organism=escherichia_coli&dry_run=true",
            files={"file": ("sample.fasta", fh, "application/octet-stream")},
        )
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    # Poll until awaiting
    status = None
    job = {}
    for _ in range(50):
        job = client.get(f"/api/v1/amr/jobs/{job_id}").json()
        status = job["status"]
        if status in {"awaiting_organism_confirmation", "failed", "completed"}:
            break
        time.sleep(0.05)

    assert status == "awaiting_organism_confirmation", job
    assert job["detected_organism"] == "Staphylococcus aureus"

    conf = client.post(
        f"/api/v1/amr/jobs/{job_id}/confirm",
        json={"decision": "accept_system"},
    )
    assert conf.status_code == 200
    assert conf.json()["organism_decision"] == "accept_system"
    assert conf.json()["confirmed_organism"] == "Staphylococcus aureus"

    for _ in range(50):
        job = client.get(f"/api/v1/amr/jobs/{job_id}").json()
        if job["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)
    assert job["status"] == "completed"
