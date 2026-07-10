"""汇总质量报告: 分布统计 + 计划书第十章质量指标对照。

输出 reports/quality_report_<version>.json,包含: 规模、任务/对象/来源分布、
JSON合法率、空值、重复、无来源数值、禁止表述、各 review_status 占比、对照计划书目标。
"""
from __future__ import annotations
import os, sys, argparse, re
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S
import check_numeric_claims as CN
import check_forbidden_patterns as CF

SPLIT_NAMES = ("train", "validation", "test", "challenge")


def collect(release_dir: str) -> dict:
    files = {}
    for name in SPLIT_NAMES:
        p = os.path.join(release_dir, f"{name}_master.jsonl")
        if os.path.exists(p):
            files[name] = p
    return files


def analyze(recs: list) -> dict:
    objs = [S.dict_to_record(r) for r in recs]
    invalid = sum(1 for o in objs if o.validate())
    empty_out = sum(1 for r in recs if not str(r.get("output", "")).strip())
    ids = [r.get("id", "") for r in recs]
    dup_id = len(ids) - len(set(ids))
    # 无来源数值 & 禁止表述计数(复用 check 模块正则)
    unsourced = 0
    forbidden = 0
    for r in recs:
        if r.get("task_type") in CN.EXEMPT:
            continue
        out = str(r.get("output", "")); inp = str(r.get("input", ""))
        out_nums = {CN.norm_num(x) for x in CN.NUM_RE.findall(out)}
        src_nums = {CN.norm_num(x) for x in CN.NUM_RE.findall(inp)}
        if any(n not in src_nums for n in out_nums):
            unsourced += 1
        if r.get("task_type") not in CF.EXEMPT and CF.FORBIDDEN.findall(out):
            forbidden += 1
    n = max(len(recs), 1)
    return {
        "total": len(recs),
        "schema_invalid": invalid,
        "schema_valid_rate": round((len(recs) - invalid) / n, 4),
        "empty_output": empty_out,
        "duplicate_id": dup_id,
        "unsourced_numeric": unsourced,
        "forbidden_pattern": forbidden,
    }


def build(release_dir: str, version: str) -> dict:
    files = collect(release_dir)
    per_split = {}
    all_recs = []
    for name, p in files.items():
        recs = S.load_jsonl(p)
        per_split[name] = analyze(recs)
        all_recs.extend(recs)
    total = len(all_recs)
    report = {
        "version": version,
        "release_dir": release_dir,
        "totals": {n: per_split[n]["total"] for n in per_split},
        "overall_total": total,
        "distribution": {
            "by_task_type": dict(Counter(r.get("task_type") for r in all_recs)),
            "by_domain": dict(Counter(r.get("domain") for r in all_recs)),
            "by_source_type": dict(Counter(r.get("source_type") for r in all_recs)),
            "by_review_status": dict(Counter(r.get("review_status") for r in all_recs)),
            "by_difficulty": dict(Counter(r.get("difficulty") for r in all_recs)),
        },
        "per_split_quality": per_split,
        "plan_targets_check": {
            "json_schema_valid_rate_100pct": all(s["schema_valid_rate"] == 1.0 for s in per_split.values()),
            "empty_output_zero": all(s["empty_output"] == 0 for s in per_split.values()),
            "duplicate_id_zero": all(s["duplicate_id"] == 0 for s in per_split.values()),
            "note": "近似重复/泄漏由独立 check 脚本检查; MechQA 类噪声需人工核验(review_status!=expert_approved)。",
        },
        "honesty_note": ("所有样本 review_status 应为 seed_pending_review/model_generated, "
                         "未经真人机械工程师 A 级审核,不得用于正式训练/产品。"),
    }
    out = f"reports/quality_report_{version}.json"
    S.save_json(report, out)
    print(f"[report] {out}")
    print(f"  overall_total={total}  totals={report['totals']}")
    print(f"  task_type 分布: {report['distribution']['by_task_type']}")
    print(f"  review_status 分布: {report['distribution']['by_review_status']}")
    print(f"  schema_valid_rate: " + ", ".join(f"{n}={per_split[n]['schema_valid_rate']}" for n in per_split))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="生成质量报告")
    ap.add_argument("-r", "--release-dir", default="data/releases/v0.1-seed")
    ap.add_argument("--version", default="v0.1-seed")
    a = ap.parse_args()
    build(a.release_dir, a.version)
