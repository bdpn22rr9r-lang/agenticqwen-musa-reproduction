"""校验主数据 schema 合法性(字段齐全/枚举合法/必填非空)。退出码: 0=全通过, 1=有问题。"""
from __future__ import annotations
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S


def run(path: str) -> bool:
    recs = S.load_jsonl(path)
    problems = []
    for i, r in enumerate(recs):
        errs = S.dict_to_record(r).validate()
        if errs:
            problems.append((r.get("id", f"line{i}"), errs))
    print(f"[validate] {path}: {len(recs)} 条, 非法 {len(problems)}")
    for rid, errs in problems[:10]:
        print(f"  {rid}: {errs}")
    return len(problems) == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="schema 合法性校验")
    ap.add_argument("inputs", nargs="+", help="jsonl 文件")
    a = ap.parse_args()
    ok = all(run(p) for p in a.inputs)
    sys.exit(0 if ok else 1)
