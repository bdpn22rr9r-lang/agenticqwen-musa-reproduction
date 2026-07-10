"""把 mechqa-qwen-lora v1/v2 的旧 4 字段(category/instruction/input/output)迁移成主格式。

用法:
  python normalize_schema.py <v1或v2的json> -o data/converted/<name>.jsonl
  python normalize_schema.py --all          # 一键迁移仓库内 v1+v2

旧 category 直接作为 task_type(旧名已在 schema.TASK_TYPES 中兼容保留)。
domain 由 input 文本关键词推断。
"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S

DOMAIN_HINTS = [
    (r"轴|销孔|销轴|键槽|花键|轴肩|阶梯轴", "shaft"),
    (r"齿轮|蜗轮|链轮|带轮|啮合", "gear"),
    (r"轴承|游隙|滚动体", "bearing"),
    (r"螺栓|螺钉|螺纹|销连接|过盈|预紧", "bolted_joint"),
    (r"焊|焊缝|支架|机架|箱体", "weldment"),
    (r"弹簧|联轴器|离合器|制动", "spring_coupling"),
    (r"梁|薄板|壳体|薄壁|法兰", "beam_plate"),
    (r"液压|密封|油缸|泵|马达", "hydraulic_seal"),
]
DIFFICULTY_HINTS = [(r"交变|疲劳|寿命|谱|稳定|屈曲|应力集中", "hard"),
                    (r"校核|强度|刚度|材料|热处理", "medium")]


def infer(text, hints, default):
    for pat, val in hints:
        if re.search(pat, text):
            return val
    return default


def migrate_one(row: dict, idx: int, version: str) -> S.MasterRecord:
    cat = row.get("category", "design_review")
    inp = row.get("input", "")
    out = row.get("output", "")
    text = inp + " " + out
    return S.MasterRecord(
        id=f"migrated_{cat}_{idx:05d}",
        task_type=cat,
        domain=infer(text, DOMAIN_HINTS, "general"),
        subdomain=cat,
        difficulty=infer(text, DIFFICULTY_HINTS, "medium"),
        language="zh",
        instruction=row.get("instruction", ""),
        input=inp,
        output=out,
        risk_tags=[],
        numeric_claims=[],
        requires_tool=False,
        requires_rag=False,
        source_type="v1v2_migrated",
        source_ref="",
        license="internal-approved",
        review_status="seed_pending_review",
        reviewer="",
        split_group=f"{cat}_migrated_{idx // 5}",
        version=version,
    )


def migrate_file(path: str, out_path: str, version: str) -> int:
    rows = S.load_json(path)
    recs = [migrate_one(r, i, version) for i, r in enumerate(rows)]
    bad = [(r.id, r.validate()) for r in recs if r.validate()]
    S.save_jsonl([r.to_dict() for r in recs], out_path)
    print(f"[normalize] {path} -> {out_path}  ({len(recs)} 条, 校验失败 {len(bad)})")
    if bad:
        print("  首个失败:", bad[0])
    return len(recs)


def main():
    ap = argparse.ArgumentParser(description="迁移 v1/v2 旧数据为主格式")
    ap.add_argument("input", nargs="?", help="v1/v2 json 路径")
    ap.add_argument("-o", "--output", default="data/converted/migrated.jsonl")
    ap.add_argument("--all", action="store_true", help="一键迁移仓库内 v1+v2")
    ap.add_argument("--version", default="v0.1-seed")
    a = ap.parse_args()

    if a.all:
        repo = Path(__file__).resolve().parents[1].parent  # mechqa-qwen-lora/
        targets = [
            (repo / "mech-qwen-sft-v1/datasets/mech_sft_v1_80.json", "v1"),
            (repo / "mech-qwen-sft-v2/datasets/mech_sft_v2_80.json", "v2"),
        ]
        total = 0
        for p, tag in targets:
            if p.exists():
                total += migrate_file(str(p), f"data/converted/migrated_{tag}.jsonl", a.version)
            else:
                print(f"[normalize] 跳过(不存在): {p}")
        print(f"[normalize] 合计迁移 {total} 条 -> data/converted/")
        return

    if not a.input:
        ap.error("需要 input 路径或 --all")
    migrate_file(a.input, a.output, a.version)


from pathlib import Path
if __name__ == "__main__":
    main()
