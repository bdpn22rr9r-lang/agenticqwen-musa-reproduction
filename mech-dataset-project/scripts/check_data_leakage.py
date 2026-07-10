"""数据泄漏检查: train 与 eval/test 不得共享 split_group(同案例/同模板的多问法)。

也额外检查 input 文本的完全重复跨集。
用法:
  python check_data_leakage.py <train.jsonl> <test_or_eval.jsonl> [...]
"""
from __future__ import annotations
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S


def run(train_path: str, *eval_paths: str) -> bool:
    train = S.load_jsonl(train_path)
    train_groups = {r.get("split_group", "") for r in train if r.get("split_group")}
    train_inputs = {str(r.get("input", "")).strip() for r in train}
    ok = True
    for ep in eval_paths:
        ev = S.load_jsonl(ep)
        ev_groups = {r.get("split_group", "") for r in ev if r.get("split_group")}
        ev_inputs = {str(r.get("input", "")).strip() for r in ev}
        shared_groups = train_groups & ev_groups
        shared_inputs = train_inputs & ev_inputs
        leak = len(shared_groups) + len(shared_inputs)
        print(f"[leakage] train={train_path} vs {ep}: "
              f"共享split_group {len(shared_groups)}, 共享input文本 {len(shared_inputs)}")
        if shared_groups:
            print("  泄漏 group:", list(shared_groups)[:5])
        if shared_inputs:
            print("  泄漏 input(首条):", list(shared_inputs)[0][:80])
        if leak:
            ok = False
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="train/test 泄漏检查")
    ap.add_argument("train", help="训练集 jsonl")
    ap.add_argument("evals", nargs="+", help="评测/测试集 jsonl")
    a = ap.parse_args()
    ok = run(a.train, *a.evals)
    sys.exit(0 if ok else 1)
