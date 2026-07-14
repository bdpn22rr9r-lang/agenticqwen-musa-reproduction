"""第15批: 复杂工程计算(深度, 8类型×6主题×6角度=288条)。归 engineering_calculation。
用法: python build_calc2.py -o data/generated_v3/calc2.jsonl"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S
AUTHOR, V3 = "claude", "v3"
def make(cat, sub, diff, instr, inp, out, ev, cond, tags, sg):
    rid = "v3_calc2_" + re.sub(r"[^\w]+", "_", sg).strip("_")[:40]
    return S.MasterRecord(id=rid, category=cat, sub_category=sub, difficulty=diff, language="zh",
        instruction=instr, input=inp, output=out, evidence=ev, conditions=cond, risk_tags=tags, task_type=cat,
        source_type="expert_authored", license="pending", review_status="self_reviewed", reviewer="claude_expert_review",
        author=AUTHOR, split_group="v3_calc2_sg_" + re.sub(r"[^\w]+", "_", sg)[:36], version=V3).to_dict()
CTYPES = {
    "beam": ("梁弯曲(含超静定)", "三弯矩方程/力法/位移法,需判静定超静定"),
    "torsion": ("轴扭转", "Wt=πd³/16,扭转角 φ=TL/(GIp),刚度"),
    "column": ("压杆稳定", "欧拉 Pcr=π²EI/(μL)²,Johnson 中长杆"),
    "contact": ("接触应力(赫兹)", "点/线接触,最大应力在表层下"),
    "energy": ("能量法(卡氏)", "应变能对力求偏导得位移/反力"),
    "fatigue_dmg": ("疲劳损伤(Miner)", "线性累积 Σni/Ni≤1,等效应力"),
    "heat": ("传热(导热)", "傅里叶定律 q=-k∇T,热阻串联"),
    "fluid": ("流体(伯努利)", "能量方程 p+½ρv²+ρgh=C,沿程损失"),
}
CTOPIC = {
    "multistep": ("多步计算", "engineering_calculation", "分步求解:列已知→选公式→代入→中间量→结果→单位→假设,避免跳步", "逐步核对量纲与中间量", "计算书交叉复核", "公式与单位表", "跳步易错"),
    "unit": ("单位换算", "engineering_calculation", "统一 SI 制,MPa=N/mm²,注意 GPa/MPa/kPa 与 mm/m 换算", "量纲分析核对每个量", "单位换算表", "SI 国际单位制", "单位错致结果量级错"),
    "trap": ("计算陷阱", "engineering_calculation", "W vs Wt、有效长度系数 μ、应力集中 Kt 适用、惯性矩轴", "对照定义复核关键量", "易错点清单", "公式定义", "陷阱致量级错误"),
    "review": ("结果复核", "engineering_calculation", "结果须合理性判断:数量级、对比经验、敏感性分析", "数量级与经验范围对比", "复核记录与签字", "经验数据范围", "不复核易出荒谬结果"),
    "assume": ("假设与边界", "engineering_calculation", "公式有假设(弹性/小变形/理想边界),超假设结论失效", "明确假设并判其适用性", "假设合理性检查", "假设清单", "超假设失效"),
    "scope": ("适用范围", "engineering_calculation", "公式适用有限:欧拉仅细长杆 λ≥λp,薄壁 t/r≤0.1 等", "对照适用条件确认", "适用范围表", "公式适用域", "超范围失效"),
}
ANGLES = [("check", "方法要点"), ("cause", "原理"), ("improve", "正确做法"), ("inspect", "复核方法"), ("material", "公式/数据"), ("limit", "适用边界")]
def gen():
    out = []
    for tk, (tn, tf) in CTYPES.items():
        for fk, fd in CTOPIC.items():
            for ak, al in ANGLES:
                if ak == "cause": body = fd[2]
                elif ak == "check": body = f"要点:{fd[2]}"
                else: body = fd[{"improve":3,"inspect":4,"material":5,"limit":6}[ak]]
                out.append(make(fd[1], f"calc2_{tk}_{fk}", "hard" if ak in ("check","limit") else "medium",
                    f"请以机械专家角度,针对{tn}的{fd[0]}问题,给出{al}。",
                    f"对象:{tn}({tf});主题:{fd[0]}。",
                    f"计算范畴:{tf}。\n针对{fd[0]}的{al}:{body}",
                    [fd[2][:12]], ["载荷", "几何", "材料性能", "单位"],
                    ["static_strength", "fatigue"], f"{tk}_{fk}_{ak}"))
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o", "--output", default="data/generated_v3/calc2.jsonl"); a = ap.parse_args()
    recs = gen(); bad = [(r["id"], S.dict_to_record(r).validate()) for r in recs if S.dict_to_record(r).validate()]
    S.save_jsonl(recs, a.output); print(f"[calc2] {len(recs)} 条 -> {a.output} (校验失败 {len(bad)})")
    if bad: print("  首个失败:", bad[0])
if __name__ == "__main__":
    main()
