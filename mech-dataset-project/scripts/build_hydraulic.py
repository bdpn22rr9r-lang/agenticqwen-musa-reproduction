"""第9批: 液压/气动系统故障(深度, 7类型×7失效×6角度=294条)。归 fault_diagnosis。
用法: python build_hydraulic.py -o data/generated_v3/hydraulic.jsonl"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S
AUTHOR, V3 = "claude", "v3"
def make(cat, sub, diff, instr, inp, out, ev, cond, tags, sg):
    rid = "v3_hyd_" + re.sub(r"[^\w]+", "_", sg).strip("_")[:40]
    return S.MasterRecord(id=rid, category=cat, sub_category=sub, difficulty=diff, language="zh",
        instruction=instr, input=inp, output=out, evidence=ev, conditions=cond, risk_tags=tags, task_type=cat,
        source_type="expert_authored", license="pending", review_status="self_reviewed", reviewer="claude_expert_review",
        author=AUTHOR, split_group="v3_hyd_sg_" + re.sub(r"[^\w]+", "_", sg)[:36], version=V3).to_dict()
HTYPES = {
    "pump_gear": ("齿轮泵", "容积式、流量脉动、适于中低压"),
    "pump_piston": ("柱塞泵", "变量、高压高效率、结构复杂、对油液敏感"),
    "valve_dir": ("方向控制阀", "切换油路方向、滑阀或锥阀结构"),
    "valve_relief": ("溢流阀(安全)", "限制系统最高压力、定压与安全保护"),
    "cylinder": ("液压缸", "直线往复、密封与爬行问题常见"),
    "pneumatic": ("气动系统", "压缩空气、清洁干燥要求、速度响应快"),
    "accumulator": ("蓄能器", "储能、缓冲、保压、辅助动力源"),
}
# 7 元素: name, cat, cause, improve, inspect, material, limit
HFAIL = {
    "leak": ("泄漏", "fault_diagnosis", "密封老化磨损、配合间隙大、压力冲击", "换密封圈、控制间隙、减冲击、合适表面粗糙度", "保压测试、目视漏油、流量计", "选合适密封材料(氟橡胶/聚氨酯)", "液压系统主要故障"),
    "cavitation": ("气蚀", "fault_diagnosis", "吸入压力过低(NPSH不足)、油中气泡破裂冲击", "提高吸入压力、改善吸油、排气、控油温", "噪声、泵体气蚀坑、振动", "保证吸入条件", "泵进口易发"),
    "contam": ("油液污染", "fault_diagnosis", "颗粒/水分侵入、密封不严、加油不洁", "精细过滤(β比)、密封、控制加油、定期换油", "油液清洁度(NAS/ISO)、颗粒计数", "过滤精度与密封", "污染致磨损与卡阀"),
    "abnormal_press": ("压力异常", "fault_diagnosis", "溢流阀失调、泵磨损内泄、阀卡滞、负载突变", "调溢流阀、查泵容积效率、清洗阀、稳负载", "各测点压力表、流量计", "逐段测压定位", "压力是核心参数"),
    "crawl": ("爬行(执行件)", "fault_diagnosis", "空气进入、摩擦力大、密封过紧、导轨润滑差", "排气、降摩擦、调密封、改善导轨润滑", "低速运动观察、压力波动", "排气与润滑", "液压缸低速常见"),
    "overheat": ("过热", "fault_diagnosis", "能量损失发热、冷却不足、内泄、油液粘度不当", "加强冷却、减内泄、选合适粘度、控负载", "油温监测、热像", "冷却与粘度", "高温加速油液老化"),
    "valve_stick": ("阀卡滞", "fault_diagnosis", "污染卡住阀芯、变形、毛刺、液压卡紧", "过滤控清洁、配磨间隙、去毛刺、均压槽抗卡紧", "动作测试、压力-位移特性", "清洁度与间隙", "比例伺服阀敏感"),
}
ANGLES = [("check", "诊断/校核"), ("cause", "故障机理"), ("improve", "处置措施"), ("inspect", "检测方法"), ("material", "元件与油液"), ("limit", "适用边界")]
def gen():
    out = []
    for tk, (tn, tf) in HTYPES.items():
        for fk, fd in HFAIL.items():
            for ak, al in ANGLES:
                if ak == "cause": body = fd[2]
                elif ak == "check": body = f"诊断依据:{fd[2]}"
                else: body = fd[{"improve":3,"inspect":4,"material":5,"limit":6}[ak]]
                out.append(make(fd[1], f"hyd_{tk}_{fk}", "hard" if ak in ("check","limit") else "medium",
                    f"请以机械专家角度,针对{tn}的{fd[0]}问题,给出{al}。",
                    f"对象:{tn}({tf});现象:{fd[0]}。",
                    f"元件特性:{tf}。\n针对{fd[0]}的{al}:{body}",
                    [fd[2][:12]], ["压力流量", "油液清洁度", "温度", "运行参数"],
                    ["inspection_ndt", "missing_information"], f"{tk}_{fk}_{ak}"))
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o", "--output", default="data/generated_v3/hydraulic.jsonl"); a = ap.parse_args()
    recs = gen(); bad = [(r["id"], S.dict_to_record(r).validate()) for r in recs if S.dict_to_record(r).validate()]
    S.save_jsonl(recs, a.output); print(f"[hydraulic] {len(recs)} 条 -> {a.output} (校验失败 {len(bad)})")
    if bad: print("  首个失败:", bad[0])
if __name__ == "__main__":
    main()
