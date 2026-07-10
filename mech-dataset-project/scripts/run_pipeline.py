"""一键主入口: 合并数据池 -> 分组切分 -> 导出 alpaca -> 质量报告。

流程(对应计划书阶段五~六):
  1. gather: 合并 data/generated/*.jsonl + data/converted/*.jsonl 为 pool(按 id 去重)
  2. split: 按 split_group 分组切分到 releases/<version>/
  3. export: 投影成 alpaca + dataset_info.json
  4. report: 生成质量报告

用法:
  python run_pipeline.py                       # 默认 v0.1-seed
  python run_pipeline.py --version v0.2        # 指定版本
  python run_pipeline.py --no-split            # 跳过切分(已有切分只重出报告)
"""
from __future__ import annotations
import os, sys, argparse, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S
import split_dataset as SP
import export_llamafactory as EX
import build_quality_report as QR


def gather_pool(dirs: list) -> list:
    pool = {}
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
            for r in S.load_jsonl(f):
                rid = r.get("id", "")
                if rid and rid not in pool:
                    pool[rid] = r
    return list(pool.values())


def main():
    ap = argparse.ArgumentParser(description="数据集流水线主入口")
    ap.add_argument("--version", default="v0.1-seed")
    ap.add_argument("--release-dir", default=None, help="默认 data/releases/<version>")
    ap.add_argument("--pool-dirs", nargs="*", default=["data/generated", "data/converted"])
    ap.add_argument("--challenge-groups", nargs="*", default=[],
                   help="强制进 challenge 的 split_group")
    ap.add_argument("--no-split", action="store_true")
    a = ap.parse_args()

    release_dir = a.release_dir or f"data/releases/{a.version}"
    os.makedirs(release_dir, exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    # 1. gather pool
    pool = gather_pool(a.pool_dirs)
    pool_path = os.path.join(release_dir, "_pool.jsonl")
    S.save_jsonl(pool, pool_path)
    print(f"[pipeline] pool: {len(pool)} 条(来自 {a.pool_dirs}) -> {pool_path}")

    # 2. split
    if not a.no_split:
        SP.split(pool_path, release_dir, challenge_groups=a.challenge_groups)
    else:
        print("[pipeline] 跳过切分(--no-split)")

    # 3. export alpaca + dataset_info
    dataset_name = "mech_sft_" + a.version.replace(".", "_")
    for name, fn in [("train", "train_master.jsonl"), ("validation", "validation_master.jsonl"),
                     ("test", "test_master.jsonl"), ("challenge", "challenge_master.jsonl")]:
        mp = os.path.join(release_dir, fn)
        if os.path.exists(mp):
            EX.export_alpaca(mp, os.path.join(release_dir, f"{name}_alpaca.json"))
    EX.write_dataset_info(release_dir, dataset_name, "train_alpaca.json")
    print(f"[pipeline] export alpaca + dataset_info (dataset={dataset_name})")

    # 4. quality report
    QR.build(release_dir, a.version)
    print(f"[pipeline] 完成。产物在 {release_dir}/ 和 reports/")


if __name__ == "__main__":
    main()
