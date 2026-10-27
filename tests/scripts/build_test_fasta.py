"""Build a small multi-contig FASTA from ARG-ANNOT sequences for end-to-end tests."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "argannot_sequences.fa"
OUT = ROOT / "data" / "sample_amr.fasta"

# Prefer one representative per phenotype family.
PREFERRED = [
    ("KPC-2", "KPC-2"),
    ("KPC", "blaKPC"),
    ("TEM-1", "TEM-1"),
    ("NDM-1", "NDM-1"),
    ("sul1", "sul1"),
    ("aac(6')-Ib-cr", "aac(6')-Ib-cr"),
    ("aac(6')-Ib", "aac(6')-Ib"),
]


def main() -> None:
    text = SRC.read_text(encoding="utf-8", errors="replace")
    records: dict[str, tuple[str, str]] = {}
    header: str | None = None
    seq: list[str] = []

    for line in text.splitlines():
        if line.startswith(">"):
            if header and seq:
                records[header] = (header, "".join(seq))
            header = line
            seq = []
        else:
            seq.append(line.strip())
    if header and seq:
        records[header] = (header, "".join(seq))

    picked: list[tuple[str, str]] = []
    used_headers: set[str] = set()
    for needle, _label in PREFERRED:
        for h, (header, s) in records.items():
            if h in used_headers:
                continue
            if needle in h:
                picked.append((header, s))
                used_headers.add(h)
                break
        if len(picked) >= 4:
            break

    with OUT.open("w", encoding="utf-8") as fh:
        for i, (h, s) in enumerate(picked, 1):
            fh.write(f">contig{i} {h[1:]}\n")
            for j in range(0, len(s), 80):
                fh.write(s[j : j + 80] + "\n")

    print(f"Wrote {OUT} with {len(picked)} contigs")
    for h, _ in picked:
        print(" ", h[:110])


if __name__ == "__main__":
    main()
