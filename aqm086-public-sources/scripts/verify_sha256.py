#!/usr/bin/env python3
"""Verify SHA256 of a file, a zip archive (every member), or a jsonl.

Examples
  python verify_sha256.py hotpot_train_v1.1.json --expected 26650cf5...
  python verify_sha256.py data_ids_april7.zip --zip
  python verify_sha256.py Omni-Math.jsonl --expected 7c87be8e...
"""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path


def sha256_stream(path: Path, buf: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()


def is_unsafe(name: str) -> bool:
    norm = name.replace("\\", "/")
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return True
    return ".." in norm.split("/")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", help="file to hash")
    ap.add_argument("--expected", help="expected sha256 (hex); exit 1 on mismatch")
    ap.add_argument("--zip", action="store_true", help="hash every member of a zip archive")
    args = ap.parse_args()

    p = Path(args.path)
    if not p.exists():
        print(f"ERROR: not found: {p}", file=sys.stderr)
        return 2

    if args.zip:
        with zipfile.ZipFile(p) as zf:
            bad = zf.testzip()
            print(f"archive={p.name}  size={p.stat().st_size}  sha256={sha256_stream(p)}")
            print(f"testzip_corrupt_member={bad}  (None means OK)")
            for info in zf.infolist():
                unsafe = is_unsafe(info.filename)
                digest = hashlib.sha256(zf.read(info.filename)).hexdigest()
                flag = "  <-- UNSAFE PATH" if unsafe else ""
                print(f"  {info.filename}\tsize={info.file_size}\tsha256={digest}{flag}")
        return 0

    digest = sha256_stream(p)
    print(f"file={p.name}  size={p.stat().st_size}  sha256={digest}")
    if args.expected:
        ok = digest.lower() == args.expected.lower()
        print(f"expected={args.expected}  match={ok}")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
