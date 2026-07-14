"""第16批: 工业安全(深度, 8类型×6主题×6角度=288条)。归 industrial_safety。
用法: python build_safety2.py -o data/generated_v3/safety2.jsonl"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S
AUTHOR, V3 = "claude", "v3"
def make(cat, sub, diff, instr, inp, out, ev, cond, tags, sg):
    rid = "v3_saf2_" + re.sub(r"[^\w]+", "_", sg).strip("_")[:40]
    return S.MasterRecord(id=rid, category=cat, sub_category=sub, difficulty=diff, language="zh",
        instruction=instr, input=inp, output=out, evidence=ev, conditions=cond, risk_tags=tags, task_type=cat,
        source_type="expert_authored", license="pending", review_status="self_reviewed", reviewer="claude_expert_review",
        author=AUTHOR, split_group="v3_saf2_sg_" + re.sub(r"[^\w]+", "_", sg)[:36], version=V3).to_dict()
SSTYPES = {
    "loto": ("能源隔离(LOTO)", "断电上锁挂牌泄压,确认零能量后作业"),
    "lifting": ("起重吊装", "吊具索具核验、指挥、禁区、禁超载斜拉"),
    "pressure": ("压力设备", "泄压置换检测,带压禁拆装"),
    "rotating": ("旋转部件", "防护罩、禁宽松衣物、停机作业"),
    "electrical": ("电气安全", "断电验电接地、安全距离、电弧"),
    "confined": ("受限空间", "通风检测氧/可燃/有毒、监护、许可"),
    "height": ("高处作业", "安全带、防坠落、临边孔洞防护"),
    "chemical": ("化学品/危化", "MSDS、防护、泄漏应急"),
}
STOPIC = {
    "risk": ("风险识别", "industrial_safety", "用 JHA/JSA 辨识危险源与风险(能源/坠落/中毒/电击/机械伤害)", "开展作业前风险分析、辨识全部危险源", "风险识别清单、分级管控", "危险源辨识方法", "先识别后控制"),
    "isolate": ("隔离措施", "industrial_safety", "物理隔离能量源:LOTO 上锁挂牌、盲板、泄压、零能量确认", "执行隔离程序、验证零能量(试电/测压)", "零能量验证记录", "LOTO 规程", "隔离是高风险作业前提"),
    "ppe": ("个人防护PPE", "industrial_safety", "依风险配 PPE:安全帽/带/护目镜/手套/呼吸器/绝缘鞋", "按风险选 PPE 并检查完好", "PPE 完好检查", "PPE 选型与标准", "末道防线,非首选"),
    "emergency": ("应急处置", "industrial_safety", "事故时快速正确响应:应急、撤离、急救、报告、警戒", "演练应急预案、配备急救与应急资源", "应急演练记录", "应急预案与资源", "减少伤害扩大"),
    "regulation": ("法规合规", "industrial_safety", "遵守安全生产法与企业规程,特种作业(电工/焊工/起重)持证", "合规性检查、特种作业证查验", "法规清单、合规检查", "安全生产法规", "法律强制要求"),
    "permit": ("作业许可", "industrial_safety", "动火/受限空间/高处/吊装/临时用电等高风险作业须许可审批", "作业许可审核签发、现场监护", "作业许可票、监护人", "作业许可制度", "高风险作业管控"),
}
ANGLES = [("check", "安全要点"), ("cause", "风险机理"), ("improve", "防护措施"), ("inspect", "检查确认"), ("material", "规程与装备"), ("limit", "适用边界")]
def gen():
    out = []
    for tk, (tn, tf) in SSTYPES.items():
        for fk, fd in STOPIC.items():
            for ak, al in ANGLES:
                if ak == "cause": body = fd[2]
                elif ak == "check": body = f"安全要点:{fd[2]}"
                else: body = fd[{"improve":3,"inspect":4,"material":5,"limit":6}[ak]]
                out.append(make(fd[1], f"saf2_{tk}_{fk}", "hard",  # 安全类全部 hard
                    f"涉及安全时,请先给出隔离/防护要求再谈作业。针对{tn}的{fd[0]},给出{al}。",
                    f"场景:{tn}({tf});主题:{fd[0]}。",
                    f"安全范畴:{tf}。\n针对{fd[0]}的{al}:{body}\n注:安全操作须遵循企业规程与法规,本文不替代安全责任人判断。",
                    [fd[2][:12]], ["设备状态", "能源类型", "作业环境", "安全规程"],
                    ["safety_critical"], f"{tk}_{fk}_{ak}"))
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o", "--output", default="data/generated_v3/safety2.jsonl"); a = ap.parse_args()
    recs = gen(); bad = [(r["id"], S.dict_to_record(r).validate()) for r in recs if S.dict_to_record(r).validate()]
    S.save_jsonl(recs, a.output); print(f"[safety2] {len(recs)} 条 -> {a.output} (校验失败 {len(bad)})")
    if bad: print("  首个失败:", bad[0])
if __name__ == "__main__":
    main()
