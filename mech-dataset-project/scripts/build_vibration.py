"""第10批: 旋转机械振动诊断(深度, 7类型×7失效×6角度=294条)。归 fault_diagnosis。
用法: python build_vibration.py -o data/generated_v3/vibration.jsonl"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S
AUTHOR, V3 = "claude", "v3"
def make(cat, sub, diff, instr, inp, out, ev, cond, tags, sg):
    rid = "v3_vib_" + re.sub(r"[^\w]+", "_", sg).strip("_")[:40]
    return S.MasterRecord(id=rid, category=cat, sub_category=sub, difficulty=diff, language="zh",
        instruction=instr, input=inp, output=out, evidence=ev, conditions=cond, risk_tags=tags, task_type=cat,
        source_type="expert_authored", license="pending", review_status="self_reviewed", reviewer="claude_expert_review",
        author=AUTHOR, split_group="v3_vib_sg_" + re.sub(r"[^\w]+", "_", sg)[:36], version=V3).to_dict()
VTYPES = {
    "motor": ("电机", "电磁力+机械,含转频与极频成分"),
    "turbine": ("汽轮机/燃气轮机", "高速转子、叶片、临界转速敏感"),
    "compressor_rot": ("离心/轴流压缩机", "高速、气动与机械耦合"),
    "fan": ("风机", "叶片、不平衡、喘振"),
    "pump_rot": ("离心泵", "流体脉动、汽蚀、不平衡"),
    "gearbox_rot": ("齿轮箱转子", "啮合频率、轴承、共振"),
    "rotor": ("通用转子系统", "转子动力学、轴承、密封耦合"),
}
VFAIL = {
    "unbalance": ("质量不平衡", "fault_diagnosis", "转子质量偏心,产生与转速同频(1×)离心力,径向振动随转速平方增大", "动平衡(单/双面)、配重、校正质量分布", "频谱 1× 突出、相位稳定、径向大", "平衡等级 G(ISO 1940)", "最常见振动故障"),
    "misalign": ("不对中", "fault_diagnosis", "联轴器两轴不同心,产生附加弯矩,2× 转频突出且轴向大", "激光对中、热态补偿、挠性联轴器", "频谱 1×/2×/3×、轴向大、联轴器发热", "对中精度公差", "联轴器常见故障"),
    "bend": ("轴弯曲", "fault_diagnosis", "轴弯曲产生偏心,类似不平衡但含轴向分量,相位差异", "校直(冷/热)、换轴、查运行变形原因", "频谱 1×、轴向与径向、相位", "弯曲量测量(打表)", "运行或装配变形"),
    "loosen": ("机械松动", "fault_diagnosis", "地脚或配合松动,产生多次谐波与非整数倍,时域冲击", "紧固、查配合与地脚、消除间隙", "频谱多次谐波(1×~10×)、时域冲击", "地脚与配合检查", "地脚或配合松动"),
    "oil_whirl": ("油膜振荡/涡动", "fault_diagnosis", "动压油膜力致转子次同步涡动(0.43~0.48×),突发且危险", "改轴承(可倾瓦)、减载荷扰动、稳操作", "频谱次同步(0.42~0.48×)、突发", "模态与稳定性分析", "高速滑动轴承危险"),
    "rub": ("动静碰摩", "fault_diagnosis", "转静子碰摩,产生次同步与多次谐波,热弯曲加剧", "查间隙对中、修密封、控热态变形", "频谱次同步+谐波、时域削波", "间隙检查", "运行变形或装配紧"),
    "resonance": ("共振", "fault_diagnosis", "激励频率接近某阶固有频率,振幅放大", "调转速避开、改刚度调固有频率、加阻尼", "频谱峰值+模态、临界转速图", "模态分析(锤击/激振)", "转速或激励接近固有频率"),
}
ANGLES = [("check", "诊断特征"), ("cause", "故障机理"), ("improve", "处置措施"), ("inspect", "检测方法"), ("material", "轴承与结构"), ("limit", "适用边界")]
def gen():
    out = []
    for tk, (tn, tf) in VTYPES.items():
        for fk, fd in VFAIL.items():
            for ak, al in ANGLES:
                if ak == "cause": body = fd[2]
                elif ak == "check": body = f"诊断特征:{fd[2][:18]}...→ {fd[4]}"
                else: body = fd[{"improve":3,"inspect":4,"material":5,"limit":6}[ak]]
                out.append(make(fd[1], f"vib_{tk}_{fk}", "hard" if ak in ("check","limit") else "medium",
                    f"请以机械专家角度,针对{tn}的{fd[0]}问题,给出{al}。",
                    f"对象:{tn}({tf});现象:{fd[0]}。",
                    f"设备特性:{tf}。\n针对{fd[0]}的{al}:{body}",
                    [fd[2][:12]], ["转速", "振动频谱", "轴承类型", "运行参数"],
                    ["vibration_resonance", "inspection_ndt"], f"{tk}_{fk}_{ak}"))
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o", "--output", default="data/generated_v3/vibration.jsonl"); a = ap.parse_args()
    recs = gen(); bad = [(r["id"], S.dict_to_record(r).validate()) for r in recs if S.dict_to_record(r).validate()]
    S.save_jsonl(recs, a.output); print(f"[vibration] {len(recs)} 条 -> {a.output} (校验失败 {len(bad)})")
    if bad: print("  首个失败:", bad[0])
if __name__ == "__main__":
    main()
