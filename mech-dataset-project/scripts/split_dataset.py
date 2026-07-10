"""按 split_group 分组的数据集划分(非随机,防泄漏)。

同一 split_group(同案例/同模板的多问法)整组进入同一分区,从结构上杜绝 train/test 泄漏。
可指定某些 group 强制进 challenge(如"横向销孔调质轴"难题)。

用法:
  python split_dataset.py <pool.jsonl> -o data/releases/v0.1-seed/ \
      --challenge-groups shaft_cross_hole_conclusion
"""
from __future__ import annotations
import os, sys, argparse, hashlib
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S


def split(pool_path: str, out_dir: str, ratios=(0.80, 0.10, 0.07, 0.03),
          challenge_groups=None, seed=42) -> dict:
    """ratios = (train, validation, test, challenge)。按 split_group 整组分配。"""
    recs = S.load_jsonl(pool_path)
    by_group = defaultdict(list)
    for r in recs:
        g = r.get("split_group") or r.get("id", "")
        by_group[g].append(r)

    groups = sorted(by_group.keys())
    challenge_groups = set(challenge_groups or [])

    train, val, test, challenge = [], [], [], []
    # 先抽出强制 challenge 组
    for g in groups:
        if g in challenge_groups:
            challenge.extend(by_group[g])
    rest = [g for g in groups if g not in challenge_groups]

    # 确定性可复现分配:用 md5 哈希(内置 hash 受 PYTHONHASHSEED 影响跨进程不固定,故用 hashlib)
    n = len(rest)
    n_val = max(1, int(round(n * ratios[1])))
    n_test = max(1, int(round(n * ratios[2])))
    assigned_val, assigned_test = 0, 0
    def _h(s: str) -> int:
        return int(hashlib.md5((s + str(seed)).encode("utf-8")).hexdigest(), 16) % 10000
    for g in rest:
        h = _h(g)
        if assigned_val < n_val and h < 10000 * ratios[1]:
            val.extend(by_group[g]); assigned_val += 1
        elif assigned_test < n_test and h < 10000 * (ratios[1] + ratios[2]):
            test.extend(by_group[g]); assigned_test += 1
        else:
            train.extend(by_group[g])

    out = {"train": train, "validation": val, "test": test, "challenge": challenge}
    for name, recs_ in out.items():
        S.save_jsonl(recs_, os.path.join(out_dir, f"{name}_master.jsonl"))
    print(f"[split] {pool_path}: 共 {len(recs)} 条 / {len(groups)} 组")
    print(f"  train={len(train)} validation={len(val)} test={len(test)} challenge={len(challenge)}")
    print(f"  -> {out_dir}/{{train,validation,test,challenge}}_master.jsonl")
    return {k: len(v) for k, v in out.items()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="分组防泄漏切分")
    ap.add_argument("pool", help="待切分的主格式 jsonl(通常为 reviewed 池)")
    ap.add_argument("-o", "--out", default="data/releases/v0.1-seed")
    ap.add_argument("--challenge-groups", nargs="*", default=[],
                   help="强制进 challenge 的 split_group(如横向销孔调质轴)")
    a = ap.parse_args()
    split(a.pool, a.out, challenge_groups=a.challenge_groups)
