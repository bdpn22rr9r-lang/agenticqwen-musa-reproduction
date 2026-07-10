"""把 MechQA JSONL 转换为主格式。

MechQA 字段: question / context / DOI / answers{text,answer_start} / qa_type / id
策略:
  - 保留英文 context 作证据原文(不翻译,避免数值失真)
  - instruction/output 用中文包裹
  - 强制标注自动标注噪声,review_status=seed_pending_review
  - 保留 DOI 到 source_ref
  - 限条数,控制占总训练集 ≤3%

用法:
  python convert_mechqa.py data/raw/mechqa/dataset_example/train_sample.json -o data/converted/mechqa_converted.jsonl -n 50
"""
from __future__ import annotations
import os, sys, argparse, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S

INSTRUCTION_ZH = (
    "请仅依据下方英文文献片段提取材料性能,并说明其适用条件。"
    "不得把带工艺、温度、方向或应变率条件的实验值泛化为无条件材料常数。"
    "数值必须能在给定片段中找到来源。"
)
NOISE_NOTE = (
    "注:MechQA 为自动标注,存在数值串行、性能类型或单位错误的风险,"
    "本条数值与性能的对应关系须经机械工程人员人工核验后方可使用。"
)

NUM_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:MPa|GPa|kPa|Pa|%|mm|°C)", re.IGNORECASE)


def to_record(obj: dict, idx: int, version: str) -> S.MasterRecord:
    q = obj.get("question", "").strip()
    ctx = obj.get("context", "").strip()
    doi = obj.get("DOI", "").strip()
    ans = obj.get("answers", {}).get("text", [])
    ans_txt = ans[0].strip() if ans else ""
    qtype = obj.get("qa_type", "").strip()
    src_id = str(obj.get("id", "") or idx)

    inp = f"问题:{q}\n文献片段(英文原文,作证据):{ctx}"
    if doi:
        inp += f"\nDOI:{doi}"
    out = (f"依据文献片段,所提取的性能为:{ans_txt}。"
           + (f"(问答类型:{qtype})。" if qtype else "")
           + "该数值仅适用于片段所述材料状态与实验条件,不可泛化为材料常数。"
           + NOISE_NOTE
           + (f" 来源 DOI:{doi}。" if doi else ""))

    nums = NUM_RE.findall(ctx)[:10]
    claims = [{"value": n.strip(), "unit": "", "source": f"mechqa_ctx:{doi or src_id}"}
              for n in nums]

    sub = ("mechqa_" + qtype.lower().replace(" ", "_")) if qtype else "mechqa_property"
    return S.MasterRecord(
        id=f"mechqa_material_{src_id}",
        task_type="context_extraction",
        domain="general",
        subdomain=sub,
        difficulty="medium",
        language="zh",
        instruction=INSTRUCTION_ZH,
        input=inp,
        output=out,
        risk_tags=["missing_information"],
        numeric_claims=claims,
        requires_tool=False,
        requires_rag=True,
        source_type="mechqa_converted",
        source_ref=doi or f"mechqa:{src_id}",
        license="cc-by-4.0",
        review_status="seed_pending_review",
        reviewer="",
        split_group=f"mechqa_{src_id}",
        version=version,
    )


def main():
    ap = argparse.ArgumentParser(description="MechQA JSONL -> 主格式")
    ap.add_argument("input", help="MechQA jsonl(如 train_sample.json)")
    ap.add_argument("-o", "--output", default="data/converted/mechqa_converted.jsonl")
    ap.add_argument("-n", "--limit", type=int, default=50, help="最多转换条数(默认50)")
    ap.add_argument("--offset", type=int, default=0, help="跳过前 N 条")
    ap.add_argument("--version", default="v0.1-seed")
    a = ap.parse_args()

    out_recs = []
    seen_ids = set()
    skipped = 0
    with open(a.input, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            if i < a.offset:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            src_id = str(obj.get("id", "") or i)
            if src_id in seen_ids:  # 去重
                continue
            seen_ids.add(src_id)
            rec = to_record(obj, i, a.version)
            out_recs.append(rec.to_dict())
            if len(out_recs) >= a.limit:
                break

    S.save_jsonl(out_recs, a.output)
    bad = sum(1 for r in out_recs if S.dict_to_record(r).validate())
    print(f"[mechqa] {a.input} -> {a.output}  ({len(out_recs)} 条, 跳过非法 {skipped}, 校验失败 {bad})")
    print(f"[mechqa] 占比提示: MechQA 类应 ≤ 总训练集 3%(5000→≤150)。当前 {len(out_recs)} 条。")


if __name__ == "__main__":
    main()
