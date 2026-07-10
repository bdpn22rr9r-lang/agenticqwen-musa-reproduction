"""完全重复检查: id 主键重复 + instruction/input 文本指纹重复。"""
from __future__ import annotations
import os, sys, argparse
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S


def run(path: str) -> bool:
    recs = S.load_jsonl(path)
    ids = [r.get("id", "") for r in recs]
    fps = [S.dict_to_record(r).text_fingerprint() for r in recs]
    dup_id = [k for k, c in Counter(ids).items() if c > 1 and k]
    dup_fp = [k for k, c in Counter(fps).items() if c > 1]
    print(f"[dup] {path}: {len(recs)} 条, id重复 {len(dup_id)}, 文本指纹重复 {len(dup_fp)}")
    if dup_id:
        print("  重复 id:", dup_id[:5])
    return (not dup_id) and (not dup_fp)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="完全重复检查")
    ap.add_argument("inputs", nargs="+")
    a = ap.parse_args()
    ok = all(run(p) for p in a.inputs)
    sys.exit(0 if ok else 1)
