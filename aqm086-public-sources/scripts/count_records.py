#!/usr/bin/env python3
"""Count records in a dataset file.

- .jsonl / .ndjson / .jsonl.gz : number of non-empty lines
- .json (single JSON array)    : len(array)
- .json (object)               : 1
- .zip                         : per-member record count (recurses into each member)

Example
  python count_records.py 2wiki/data_ids_april7.zip
  python count_records.py Omni-Math.jsonl
"""
import argparse
import gzip
import json
import sys
import zipfile
from pathlib import Path


def count_jsonl(path: Path) -> int:
    opener = gzip.open if path.suffix == ".gz" else open
    n = 0
    with opener(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def count_json_array(path: Path) -> int:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    if isinstance(data, list):
        return len(data)
    return 1 if isinstance(data, dict) else 0


def count_member(zf: zipfile.ZipFile, name: str) -> int:
    low = name.lower()
    if low.endswith((".jsonl", ".ndjson")):
        n = 0
        for line in zf.read(name).decode("utf-8", "replace").splitlines():
            if line.strip():
                n += 1
        return n
    if low.endswith(".json"):
        try:
            data = json.loads(zf.read(name).decode("utf-8", "replace"))
            return len(data) if isinstance(data, list) else 1
        except json.JSONDecodeError:
            # likely JSONL (e.g. id_aliases.json): fall back to line count
            return sum(1 for ln in zf.read(name).decode("utf-8", "replace").splitlines() if ln.strip())
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    args = ap.parse_args()
    p = Path(args.path)
    if not p.exists():
        print(f"ERROR: not found: {p}", file=sys.stderr)
        return 2

    if zipfile.is_zipfile(p):
        with zipfile.ZipFile(p) as zf:
            print(f"archive={p.name}  members={len(zf.namelist())}")
            for info in zf.infolist():
                if info.is_dir():
                    continue
                print(f"  {info.filename}\trecords={count_member(zf, info.filename)}")
        return 0

    low = p.suffix.lower()
    if low in (".jsonl", ".ndjson"):
        print(f"file={p.name}  records(lines)={count_jsonl(p)}")
    elif low == ".json":
        print(f"file={p.name}  records={count_json_array(p)}")
    elif low == ".gz":
        print(f"file={p.name}  records(lines)={count_jsonl(p)}")
    else:
        print(f"file={p.name}  unsupported extension {low}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
