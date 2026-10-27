# Live Docker tools (AERIS)

Verified pipeline with [DeepARG (gaarangoa/deeparg)](https://github.com/gaarangoa/deeparg).

## Tools (5/5)

| Tool | Image | Notes |
|------|-------|--------|
| ABRicate | `staphb/abricate:latest` | ARG-ANNOT DB bundled |
| AMRFinderPlus | `ncbi/amr:latest` | DB bundled |
| ResFinder | `genomicepidemiology/resfinder:4.7.2` | `-db_res /databases/resfinder_db`; PointFinder when species is supported |
| CARD / RGI | `quay.io/biocontainers/rgi:6.0.3--pyha8f3691_0` | Needs `data/card_db` |
| DeepARG | `aeris-deeparg:latest` | Build from GitHub; HF cache in `data/hf_cache` |

## ResFinder PointFinder (chromosomal mutations)

Acquired genes (`-acq`) always run. When the confirmed organism has a
PointFinder panel, the runner also passes:

```
-c -s <db_prefix> --ignore_missing_species -db_point /databases/pointfinder_db
```

`<db_prefix>` comes from `resfinder_species` in `config/organism_groups.yaml`
and must match a folder in the image:

```bash
docker run --rm --entrypoint sh genomicepidemiology/resfinder:4.7.2 \
  -c "cat /databases/pointfinder_db/config"
```

These are **not** the AMRFinderPlus keys — *Klebsiella pneumoniae* maps to the
genus-level `klebsiella` panel. Organisms without a panel (Pseudomonas,
Acinetobacter, Enterobacter, S. epidermidis) run acquired-only and the report
records `pointfinder_status: skipped`. If PointFinder itself fails, ResFinder is
re-run acquired-only so gene results are never lost.

## Build DeepARG image

```bash
docker build -t aeris-deeparg:latest https://github.com/gaarangoa/deeparg.git#main
```

First predict downloads models/DIAMOND from Hugging Face into `data/hf_cache`.

## CARD DB (once)

```bash
mkdir -p data/card_db
curl -L https://card.mcmaster.ca/latest/data -o data/card_db/carddata.tar.bz2
docker run --rm -v "${PWD}/data/card_db:/card" -w /card \
  quay.io/biocontainers/rgi:6.0.3--pyha8f3691_0 \
  bash -c "tar -xjf carddata.tar.bz2 && rgi load --card_json /card/card.json --local"
```

## Run all five

```bash
python -c "from backend.pipeline.amr_runner import AMRToolRunner; \
from backend.pipeline.consensus import AMRConsensusAnalyzer; \
r=AMRToolRunner(); run=r.run_all('data/sample_amr.fasta', sample_id='live5'); \
print({k:v.success for k,v in run.tools.items()}); \
print(AMRConsensusAnalyzer().analyze_to_dict(run.hamronized_reports,'live5')['consensus_summary'])"
```
