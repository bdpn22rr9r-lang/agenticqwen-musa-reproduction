"""第14批: 标准核验与拒绝编造(深度, 7类型×6主题×6角度=252条)。归 standard_evidence_refusal。
用法: python build_standard2.py -o data/generated_v3/standard2.jsonl"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S
AUTHOR, V3 = "claude", "v3"
def make(cat, sub, diff, instr, inp, out, ev, cond, tags, sg):
    rid = "v3_std2_" + re.sub(r"[^\w]+", "_", sg).strip("_")[:40]
    return S.MasterRecord(id=rid, category=cat, sub_category=sub, difficulty=diff, language="zh",
        instruction=instr, input=inp, output=out, evidence=ev, conditions=cond, risk_tags=tags, task_type=cat,
        source_type="expert_authored", license="pending", review_status="self_reviewed", reviewer="claude_expert_review",
        author=AUTHOR, split_group="v3_std2_sg_" + re.sub(r"[^\w]+", "_", sg)[:36], version=V3).to_dict()
STYPES = {
    "gear": ("齿轮标准", "GB/T 3480 强度、GB/T 10095 精度"),
    "bearing": ("轴承标准", "GB/T 6391 寿命、GB/T 307 公差"),
    "bolt": ("紧固件标准", "GB/T 3098 力学、GB/T 197 螺纹、GB/T 5780 六角头"),
    "weld": ("焊接标准", "GB/T 19418 质量、GB/T 11345 无损、GB/T 985 坡口"),
    "pressure": ("压力容器标准", "GB/T 150 强度、TSG 21 监检规程"),
    "material": ("材料标准", "GB/T 699 碳钢、GB/T 3077 合金钢、GB/T 1220 不锈钢"),
    "tolerance": ("公差标准", "GB/T 1800 配合、GB/T 1184 形位公差"),
}
STOPIC = {
    "cite": ("正确引用", "standard_evidence_refusal", "引用须含标准号、年份、名称、适用条款,使用前核对最新有效版本", "查标准原文确认号/年/条款", "标准核验台账登记", "标准数据库/原文", "缺一不可"),
    "version": ("版本核对", "standard_evidence_refusal", "标准会更新,旧版可能作废或不适用,强制性条款会变化", "查发布与实施日期、强条变化", "版本台账更新", "标准化信息系统", "用错版本致结论失效"),
    "scope": ("适用范围", "standard_evidence_refusal", "标准有适用边界(对象/参数/工况),不能跨域套用", "对照适用范围条款确认", "适用性评估记录", "标准适用条款", "超范围套用错误"),
    "refuse_val": ("拒绝无依据数值", "standard_evidence_refusal", "无来源/版本/适用范围时不得给固定数值,须查标准或计算", "判断数值是否有可追溯来源", "数值来源台账", "标准与计算依据", "V3 红线,违规即废"),
    "refuse_info": ("拒绝信息不足", "standard_evidence_refusal", "缺载荷/材料/几何/工况时不得下确定结论,须列缺失信息", "核对必要信息是否齐全", "信息完整性检查表", "设计输入清单", "V3 红线"),
    "ledger": ("标准核验台账", "standard_evidence_refusal", "标准引用须可追溯核验,建立台账(号/年/名/条款/适用/状态)", "台账核对与定期更新", "台账管理系统", "标准台账模板", "可追溯是合规要求"),
}
ANGLES = [("check", "判定要点"), ("cause", "问题/原则"), ("improve", "正确做法"), ("inspect", "核验方法"), ("material", "标准依据"), ("limit", "适用边界")]
def gen():
    out = []
    for tk, (tn, tf) in STYPES.items():
        for fk, fd in STOPIC.items():
            for ak, al in ANGLES:
                if ak == "cause": body = fd[2]
                elif ak == "check": body = f"判定要点:{fd[2]}"
                else: body = fd[{"improve":3,"inspect":4,"material":5,"limit":6}[ak]]
                out.append(make(fd[1], f"std2_{tk}_{fk}", "hard" if ak in ("check","limit") else "medium",
                    f"请以机械专家角度,针对{tn}的{fd[0]}问题,给出{al}。",
                    f"对象:{tn}({tf});主题:{fd[0]}。",
                    f"标准范畴:{tf}。\n针对{fd[0]}的{al}:{body}",
                    [fd[2][:12]], ["标准版本", "适用范围", "条款", "来源"],
                    ["standard_citation", "fabricated_value_risk"], f"{tk}_{fk}_{ak}"))
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o", "--output", default="data/generated_v3/standard2.jsonl"); a = ap.parse_args()
    recs = gen(); bad = [(r["id"], S.dict_to_record(r).validate()) for r in recs if S.dict_to_record(r).validate()]
    S.save_jsonl(recs, a.output); print(f"[standard2] {len(recs)} 条 -> {a.output} (校验失败 {len(bad)})")
    if bad: print("  首个失败:", bad[0])
if __name__ == "__main__":
    main()
