# AERIS — AMR Detection Platform

Resistance-gene screening from `.fasta` / `.fastq`: four database tools plus a
DeepARG deep-learning screen, standardized with **hAMRonization**, on a FastAPI
backend and a React dashboard. Every tool gets its own report — this is
genotypic screening, not a susceptibility test.

## Pipeline

1. Select expected organism + ingest `.fasta` / `.fastq`
2. Species ID (Mash sketches → marker fallback → optional Speciator)
3. Confirm if declared ≠ detected (Accept / Keep / Cancel)
4. Database tools: ResFinder · CARD/RGI · AMRFinderPlus · ARG-ANNOT (ABRicate)
5. AI screen: DeepARG (predicts gene families, kept out of tool agreement)
6. `hamronize` each report → unified JSON, plus each tool's native fields
7. Filter per report: identity ≥ 90%, coverage ≥ 80%

Results open as a per-tool report hub (`/results/:sampleId`), and a finished
tool can be read while later tools are still running. Drug-class majority
voting still exists in `backend/pipeline/consensus.py` for internal analysis and
API compatibility, but it is not the product surface.

### Species Mash DB (once)

```bash
docker pull staphb/mash:2.3
python scripts/build_species_mash_db.py
```

Sketches land in `data/species_mash/`. Short gene-cassette FASTAs (like `sample_amr.fasta`) use marker-based ID when Mash distance is too high.

## Quick start (local)

```bash
# Backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn backend.api.main:app --reload --port 8001

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** → **Run live demo** (fixtures) or **Upload sequence** (real Docker tools).  
API docs: **http://localhost:8001/docs** (port **8001** by default).

### Live FASTA (verified — 5/5 tools)

ABRicate · AMRFinderPlus · ResFinder · RGI · DeepARG ([gaarangoa/deeparg](https://github.com/gaarangoa/deeparg)).  
See [docs/LIVE_TOOLS.md](docs/LIVE_TOOLS.md) for image build / CARD / HF cache.

```bash
# Build DeepARG once
docker build -t aeris-deeparg:latest https://github.com/gaarangoa/deeparg.git#main

python scripts/build_test_fasta.py
curl -X POST "http://127.0.0.1:8001/api/v1/amr/analyze?sample_id=live" \
  -F "file=@data/sample_amr.fasta"
```

Expected on the sample file: `blaKPC`, `blaTEM` and `blaNDM` reported by all
four database tools, and the KPC/TEM/NDM families predicted by DeepARG.

## Docker Compose

```bash
docker compose up --build
```

- Web UI: http://localhost:8080  
- API: http://localhost:8000/docs  

## API highlights

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/amr/organisms` | Organism catalog for Analyze UI |
| `POST /api/v1/amr/analyze/async` | Upload + species gate + AMR job |
| `POST /api/v1/amr/jobs/{id}/confirm` | Accept detected / keep declared / cancel |
| `POST /api/v1/amr/demo` | Instant tool reports from fixtures |
| `POST /api/v1/amr/analyze` | Upload sequence (optional `dry_run=true`) |
| `GET /api/v1/amr/results/{id}` | Fetch stored payload |
| `GET /api/v1/amr/results` | Recent samples |

## Project layout

```
backend/pipeline/   # runner, consensus, schemas
backend/api/        # FastAPI
backend/db/         # SQLAlchemy persistence
frontend/           # AERIS React dashboard
config/tools.yaml   # Docker images & thresholds
tests/fixtures/     # Sample hAMRonized JSON
```
