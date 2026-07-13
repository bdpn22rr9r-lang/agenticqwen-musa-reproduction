"""V3 流水线主入口。

按 V3 第5.3节"评测集严格隔离":
  - golden_v3(训练池) -> 按 split_group 分组切分为 train / validation
  - eval_v3(评测池)   -> 高风险题进 challenge, 其余进 test (与训练隔离)

用法: python run_pipeline_v3.py
"""
from __future__ import annotations
import os, sys, argparse, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S
import export_llamafactory as EX
import build_quality_report as QR


def main():
    ap = argparse.ArgumentParser(description="V3 数据流水线")
    ap.add_argument("--version", default="v3")
    ap.add_argument("--golden", default="data/generated_v3/golden_v3.jsonl")
    ap.add_argument("--eval", default="data/generated_v3/eval_v3.jsonl")
    ap.add_argument("--release-dir", default=None)
    ap.add_argument("--val-ratio", type=float, default=0.15)
    a = ap.parse_args()

    release_dir = a.release_dir or f"data/releases/{a.version}"
    os.makedirs(release_dir, exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    golden = S.load_jsonl(a.golden)
    evalr = S.load_jsonl(a.eval)

    # golden -> train / validation (按 split_group 整组, 确定性哈希)
    train, val = [], []
    val_groups = set()
    for r in golden:
        g = r.get("split_group", "") or r.get("id", "")
        h = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16) % 100
        if h < int(100 * a.val_ratio):
            val.append(r); val_groups.add(g)
        else:
            train.append(r)

    # eval -> test / challenge (高风险进 challenge)
    test, challenge = [], []
    for r in evalr:
        if "_hr_" in (r.get("split_group", "") or ""):  # eval_hr_ 为高风险题
            challenge.append(r)
        else:
            test.append(r)

    S.save_jsonl(train, os.path.join(release_dir, "train_master.jsonl"))
    S.save_jsonl(val, os.path.join(release_dir, "validation_master.jsonl"))
    S.save_jsonl(test, os.path.join(release_dir, "test_master.jsonl"))
    S.save_jsonl(challenge, os.path.join(release_dir, "challenge_master.jsonl"))

    print(f"[v3-pipeline] golden={len(golden)} eval={len(evalr)}")
    print(f"  train={len(train)} validation={len(val)} test={len(test)} challenge={len(challenge)}")

    # 泄漏自检: train/val(golden) 与 test/challenge(eval) 不共享 split_group
    g_groups = {r.get("split_group", "") for r in golden}
    e_groups = {r.get("split_group", "") for r in evalr}
    leak = g_groups & e_groups
    print(f"  泄漏自检: 训练池/评测池共享 split_group = {len(leak)} (应为 0)")

    # export alpaca + dataset_info
    dataset_name = "mech_sft_v3"
    for name in ("train", "validation", "test", "challenge"):
        mp = os.path.join(release_dir, f"{name}_master.jsonl")
        if os.path.exists(mp):
            EX.export_alpaca(mp, os.path.join(release_dir, f"{name}_alpaca.json"))
    EX.write_dataset_info(release_dir, dataset_name, "train_alpaca.json")
    print(f"[v3-pipeline] export alpaca + dataset_info (dataset={dataset_name})")

    QR.build(release_dir, a.version)
    print(f"[v3-pipeline] 完成。产物在 {release_dir}/ 和 reports/")


if __name__ == "__main__":
    main()
