#!/usr/bin/env python3
"""CLI entrypoint: process a FASTA/FASTQ file through the AMR consensus pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running without installing the package
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.pipeline.pipeline import AMRPipeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run AMR tools → hAMRonize → 3/5 drug-class consensus",
    )
    parser.add_argument("input", type=Path, help="FASTA or FASTQ input file")
    parser.add_argument("--sample-id", default=None, help="Sample identifier")
    parser.add_argument("--work-dir", type=Path, default=Path("./work"))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log/skip container execution (wiring check)",
    )
    parser.add_argument(
        "--consensus-only",
        nargs="+",
        metavar="TOOL=PATH",
        help="Skip tools; vote on existing hAMRonized JSON (e.g. resfinder=./r.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write API payload JSON to this path (default: stdout)",
    )
    args = parser.parse_args()

    pipeline = AMRPipeline(dry_run=args.dry_run)

    if args.consensus_only:
        reports: dict[str, Path] = {}
        for item in args.consensus_only:
            if "=" not in item:
                parser.error(f"Expected TOOL=PATH, got: {item}")
            key, path = item.split("=", 1)
            reports[key] = Path(path)
        payload = pipeline.analyze_existing_reports(
            reports,
            sample_id=args.sample_id or args.input.stem,
        )
    else:
        payload = pipeline.process(
            input_path=args.input,
            sample_id=args.sample_id,
            work_dir=args.work_dir,
        )

    text = json.dumps(payload.to_api_dict(), indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
