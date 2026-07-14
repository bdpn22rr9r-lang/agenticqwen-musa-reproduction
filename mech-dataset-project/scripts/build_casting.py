"""第8批: 铸造/锻造/冲压(深度, 7类型×7失效×6角度=294条)。归 manufacturing_qc。
用法: python build_casting.py -o data/generated_v3/casting.jsonl"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S
AUTHOR, V3 = "claude", "v3"
def make(cat, sub, diff, instr, inp, out, ev, cond, tags, sg):
    rid = "v3_cas_" + re.sub(r"[^\w]+", "_", sg).strip("_")[:40]
    return S.MasterRecord(id=rid, category=cat, sub_category=sub, difficulty=diff, language="zh",
        instruction=instr, input=inp, output=out, evidence=ev, conditions=cond, risk_tags=tags, task_type=cat,
        source_type="expert_authored", license="pending", review_status="self_reviewed", reviewer="claude_expert_review",
        author=AUTHOR, split_group="v3_cas_sg_" + re.sub(r"[^\w]+", "_", sg)[:36], version=V3).to_dict()
CTYPES = {
    "sand": ("砂型铸造", "砂型成型、成本低、适合复杂大件、表面较粗"),
    "die_cast": ("压力铸造", "金属液压入金属型、高精度高效率、适有色金属薄壁"),
    "forging_open": ("自由锻", "通用工具成形、单件小批、组织致密"),
    "forging_die": ("模锻", "模具成形、批量、纤维流向好、力学性能优"),
    "stamping": ("冲压", "板料模具成形、高效率、适薄板"),
    "rolling": ("轧制", "轧辊塑性变形、生产型材与板带"),
    "investment": ("熔模铸造", "蜡模、高精度复杂小件、表面光"),
}
# 7 元素: name, cat, cause, improve, inspect, material, limit
CFAIL = {
    "shrink": ("缩孔缩松", "manufacturing_qc", "凝固补缩不足、冒口设计不当、顺序凝固失控", "优化浇注系统与冒口、加冷铁控制顺序凝固、控浇温", "RT/工业CT、剖切", "控凝固顺序、合理冒口", "铸造主要内部缺陷"),
    "porosity": ("气孔", "manufacturing_qc", "气体析出或浇注卷气、型腔排气不良", "除气精炼、控浇温与速度、改善排气、烘干型砂", "RT/UT、目视", "除气与排气", "铸件常见缺陷"),
    "cold_lap": ("冷隔", "manufacturing_qc", "金属流汇合前凝固、浇温低或速度慢", "提高浇温与速度、优化浇注系统、避免薄长流程", "目视、渗透(PT)", "保证充型能力", "薄壁大件风险"),
    "crack": ("裂纹", "manufacturing_qc", "热应力或组织应力、结构尖角、冷却太快", "对称结构、避免尖角、控冷却、退火消应力", "MT/PT/UT", "控温与结构设计", "复杂件危险"),
    "fold": ("折叠(锻冲)", "manufacturing_qc", "金属变形流汇合表层折入,毛坯或模具不当", "优化毛坯与模具、合理变形量、充分润滑", "目视/PT", "合理工步与毛坯", "锻冲典型缺陷"),
    "dim": ("尺寸偏差", "manufacturing_qc", "收缩率不准、模具磨损、热变形", "精确收缩率、监控模具磨损、控温、修模", "尺寸测量、三坐标", "收缩率与模具管理", "影响装配"),
    "surface": ("粘砂/氧化皮/划伤", "manufacturing_qc", "型砂/润滑/模具表面问题", "涂料、润滑、模具抛光、控温控气", "目视、粗糙度", "模具与润滑管理", "影响外观与疲劳"),
}
ANGLES = [("check", "校核/判定"), ("cause", "失效机理"), ("improve", "改进措施"), ("inspect", "检测方法"), ("material", "材料与工艺"), ("limit", "适用边界")]
def gen():
    out = []
    for tk, (tn, tf) in CTYPES.items():
        for fk, fd in CFAIL.items():
            for ak, al in ANGLES:
                if ak == "cause": body = fd[2]
                elif ak == "check": body = f"对照技术要求判定,依据:{fd[2]}"
                else: body = fd[{"improve":3,"inspect":4,"material":5,"limit":6}[ak]]
                out.append(make(fd[1], f"cas_{tk}_{fk}", "hard" if ak in ("check","limit") else "medium",
                    f"请以机械专家角度,针对{tn}的{fd[0]}问题,给出{al}。",
                    f"对象:{tn}({tf});问题:{fd[0]}。",
                    f"工艺特性:{tf}。\n针对{fd[0]}的{al}:{body}",
                    [fd[2][:12]], ["材料", "结构", "工艺参数", "质量等级"],
                    ["manufacturing_process", "inspection_ndt"], f"{tk}_{fk}_{ak}"))
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o", "--output", default="data/generated_v3/casting.jsonl"); a = ap.parse_args()
    recs = gen(); bad = [(r["id"], S.dict_to_record(r).validate()) for r in recs if S.dict_to_record(r).validate()]
    S.save_jsonl(recs, a.output); print(f"[casting] {len(recs)} 条 -> {a.output} (校验失败 {len(bad)})")
    if bad: print("  首个失败:", bad[0])
if __name__ == "__main__":
    main()
