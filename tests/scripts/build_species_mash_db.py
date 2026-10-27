#!/usr/bin/env python3
"""Download RefSeq genomes and build Mash sketches for AERIS species ID."""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _docker_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"  exists: {dest.name}")
        return dest
    print(f"  downloading {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(dest)
    return dest


def gunzip_to(src_gz: Path, dest_fna: Path) -> Path:
    if dest_fna.exists() and dest_fna.stat().st_size > 1000:
        return dest_fna
    with gzip.open(src_gz, "rb") as zin, dest_fna.open("wb") as zout:
        shutil.copyfileobj(zin, zout)
    return dest_fna


def mash_sketch(
    image: str,
    fasta: Path,
    sketch_out: Path,
    *,
    k: int,
    s: int,
) -> None:
    out_dir = sketch_out.parent
    # mash sketch writes prefix.msh
    prefix = sketch_out.with_suffix("")  # remove .msh
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{_docker_path(fasta.parent)}:/data/in:ro",
        "-v",
        f"{_docker_path(out_dir)}:/data/out",
        image,
        "mash",
        "sketch",
        "-k",
        str(k),
        "-s",
        str(s),
        "-o",
        f"/data/out/{prefix.name}",
        f"/data/in/{fasta.name}",
    ]
    print(" ", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "mash sketch failed")
    if not sketch_out.exists():
        # some mash versions append .msh to -o
        alt = Path(str(prefix) + ".msh")
        if alt.exists() and alt != sketch_out:
            alt.replace(sketch_out)
    if not sketch_out.exists():
        raise FileNotFoundError(f"Expected sketch missing: {sketch_out}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "species_mash_refs.yaml",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "data" / "species_mash",
    )
    parser.add_argument("--image", default="staphb/mash:2.3")
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Optional organism_id filter",
    )
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    sketch_cfg = cfg.get("sketch", {})
    k = int(sketch_cfg.get("k", 21))
    s = int(sketch_cfg.get("sketch_size", 1000))
    refs = cfg.get("references", [])
    if args.only:
        wanted = set(args.only)
        refs = [r for r in refs if r["organism_id"] in wanted]

    raw_dir = args.out_dir / "raw"
    sketch_dir = args.out_dir / "sketches"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sketch_dir.mkdir(parents=True, exist_ok=True)

    index: list[dict] = []
    failures: list[str] = []
    for ref in refs:
        oid = ref["organism_id"]
        print(f"\n[{oid}]")
        try:
            gz = raw_dir / f"{oid}.fna.gz"
            fna = raw_dir / f"{oid}.fna"
            download(ref["url"], gz)
            gunzip_to(gz, fna)
            msh = sketch_dir / f"{oid}.msh"
            mash_sketch(args.image, fna, msh, k=k, s=s)
            index.append(
                {
                    "organism_id": oid,
                    "display_name": ref["display_name"],
                    "accession": ref.get("accession"),
                    "sketch": str(msh.relative_to(args.out_dir)).replace("\\", "/"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED: {exc}")
            failures.append(f"{oid}: {exc}")

    # Also pick up any pre-existing sketches not in this run
    known = {row["organism_id"] for row in index}
    name_by_id = {r["organism_id"]: r for r in (cfg.get("references") or [])}
    for msh in sorted(sketch_dir.glob("*.msh")):
        oid = msh.stem
        if oid in known:
            continue
        meta_ref = name_by_id.get(oid, {})
        index.append(
            {
                "organism_id": oid,
                "display_name": meta_ref.get("display_name", oid.replace("_", " ").title()),
                "accession": meta_ref.get("accession"),
                "sketch": str(msh.relative_to(args.out_dir)).replace("\\", "/"),
            }
        )

    meta = {
        "k": k,
        "sketch_size": s,
        "distance_threshold": float(sketch_cfg.get("distance_threshold", 0.05)),
        "max_distance": float(sketch_cfg.get("max_distance", 0.12)),
        "references": index,
        "failures": failures,
    }
    meta_path = args.out_dir / "index.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nWrote {meta_path} ({len(index)} sketches)")
    if failures:
        print("Failures:")
        for line in failures:
            print(" ", line)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
