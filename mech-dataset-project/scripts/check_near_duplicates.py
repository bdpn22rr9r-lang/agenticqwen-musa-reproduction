"""近似重复检查: 基于 difflib 的文本相似度(标准库,零依赖)。

对 input 文本两两计算相似度,超过阈值则告警。O(n^2),适合数千条以内。
"""
from __future__ import annotations
import os, sys, argparse, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S


def run(path: str, threshold: float = 0.9) -> bool:
    recs = S.load_jsonl(path)
    inputs = [str(r.get("input", "")) for r in recs]
    ids = [r.get("id", "") for r in recs]
    near = []
    n = len(inputs)
    for i in range(n):
        for j in range(i + 1, n):
            r = difflib.SequenceMatcher(None, inputs[i], inputs[j]).ratio()
            if r >= threshold:
                near.append((ids[i], ids[j], round(r, 3)))
    print(f"[near_dup] {path}: {n} 条, 近似对(>= {threshold}) {len(near)}")
    for a, b, r in near[:10]:
        print(f"  {a} ~ {b} : {r}")
    return len(near) == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="近似重复检查")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-t", "--threshold", type=float, default=0.9)
    a = ap.parse_args()
    ok = all(run(p, a.threshold) for p in a.inputs)
    sys.exit(0 if ok else 1)
