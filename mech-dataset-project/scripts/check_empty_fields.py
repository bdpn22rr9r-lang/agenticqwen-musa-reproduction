"""检查空字段与异常短文本。"""
from __future__ import annotations
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S


def run(path: str, min_len: int = 8) -> bool:
    recs = S.load_jsonl(path)
    problems = []
    for r in recs:
        for f in ("instruction", "input", "output"):
            v = str(r.get(f, "")).strip()
            if not v:
                problems.append((r.get("id"), f"{f} 为空"))
            elif len(v) < min_len:
                problems.append((r.get("id"), f"{f} 过短({len(v)}字)"))
    print(f"[empty] {path}: {len(recs)} 条, 问题 {len(problems)}")
    for rid, msg in problems[:10]:
        print(f"  {rid}: {msg}")
    return len(problems) == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="空/短字段检查")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--min-len", type=int, default=8)
    a = ap.parse_args()
    ok = all(run(p, a.min_len) for p in a.inputs)
    sys.exit(0 if ok else 1)
