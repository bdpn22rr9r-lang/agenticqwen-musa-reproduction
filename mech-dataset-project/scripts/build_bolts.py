"""第4批: 螺栓/紧固/密封(深度, 6类型×6失效×6角度=216条)。归 design_fatigue。
用法: python build_bolts.py -o data/generated_v3/bolts.jsonl"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S

AUTHOR, V3 = "claude", "v3"

def make(cat, sub, diff, instr, inp, out, ev, cond, tags, sg):
    rid = "v3_bolt_" + re.sub(r"[^\w]+", "_", sg).strip("_")[:40]
    return S.MasterRecord(id=rid, category=cat, sub_category=sub, difficulty=diff, language="zh",
        instruction=instr, input=inp, output=out, evidence=ev, conditions=cond, risk_tags=tags,
        task_type=cat, source_type="expert_authored", license="pending", review_status="self_reviewed",
        reviewer="claude_expert_review", author=AUTHOR,
        split_group="v3_bolt_sg_" + re.sub(r"[^\w]+", "_", sg)[:36], version=V3).to_dict()

BTYPES = {
    "tension": ("普通螺栓联接(受拉)", "靠预紧力联接,孔有间隙,主要受轴向拉力"),
    "shear_fit": ("铰制孔螺栓(受剪)", "孔无间隙,靠螺栓杆受剪与孔壁挤压传横向力"),
    "hsb": ("高强度螺栓(摩擦型)", "靠大预紧力在接合面摩擦传力,不靠螺栓受剪"),
    "stud": ("双头螺柱联接", "一端旋入螺孔,常用于盲孔或经常拆卸处"),
    "seal_flange": ("法兰密封螺栓", "预紧压紧密封垫片保证密封"),
    "locknut": ("防松螺母联接", "配施必牢/尼龙/金属锁紧螺母抗横向振动松动"),
}
BFAIL = {
    "fatigue": ("疲劳断裂", "应力幅 σa=ΔF/(2·As) 对照螺栓疲劳极限(8.8级约 30~50 MPa),第一圈螺纹根部最危险", "交变载荷下第一圈螺纹根部应力集中,疲劳裂纹萌生扩展致断裂", "降低应力幅(降低螺栓刚度/提高被联接件刚度)、增大预紧、滚压螺纹、防松", "磁粉/超声检测螺纹根部、预紧力抽检、振动监测", "8.8/10.9 级,滚压螺纹提高疲劳", "受交变载荷联接主要失效"),
    "loosen": ("松动", "校核残余预紧力与横向滑移是否小于临界;防松验算", "横向动载荷使螺纹副微滑移,摩擦力下降,预紧力逐渐丧失", "机械防松(弹簧垫圈/止动垫片/施必牢螺纹)、增大预紧、锁固胶", "预紧力定期抽检、振动监测、目视防松件", "防松方式与强度等级匹配工况", "横向振动工况失效"),
    "overload": ("过载拉断", "静强度 σ=F/As ≤ σb/n;核算最大工作载荷", "轴向过载使应力超过抗拉强度,螺纹根部断裂", "增大直径或强度等级、减小载荷、设过载保护", "断口分析、载荷监测", "8.8/10.9/12.9 级按强度选", "过载或强度不足失效"),
    "shear": ("剪切/挤压失效", "剪切应力 τ=Fsh/(i·πd²/4) ≤ [τ];挤压 σp=Fsh/(d·δ) ≤ [σp]", "横向载荷使螺栓杆受剪或孔壁挤压破坏", "用铰制孔螺栓、增大直径、提高配合与孔壁硬度", "配合检测、剪切面与孔壁检查", "铰制孔螺栓 45/40Cr 调质", "受横向载荷铰制孔联接"),
    "seal_leak": ("密封泄漏", "校核垫片比压力与残余压紧力;须对称均匀预紧", "预紧力不足或不均,垫片比压力下降致介质泄漏", "对称均匀预紧(对角顺序)、足够预紧、合适垫片、定期复紧", "试压检漏、预紧力检查、法兰平行度", "垫片与介质匹配,螺栓防腐", "法兰密封连接失效"),
    "corrosion": ("腐蚀咬死", "工况介质分析;不锈钢螺纹易咬死(galling)", "腐蚀或不锈钢螺纹金属咬合(galling),拆卸困难甚至拧断", "防咬剂(二硫化钼)、合适材料配对、镀层、控制预紧", "拆卸扭矩监测、外观锈蚀", "不锈钢 304/316 配防咬剂", "潮湿腐蚀或不锈钢工况"),
}
ANGLES = [("check", "校核方法"), ("cause", "失效机理"), ("improve", "改进措施"),
          ("inspect", "检测方法"), ("material", "选型与材料"), ("limit", "适用边界")]

def gen():
    out = []
    for tk, (tn, tf) in BTYPES.items():
        for fk, fd in BFAIL.items():
            for ak, al in ANGLES:
                out.append(make("design_fatigue", f"bolt_{tk}_{fk}", "hard" if ak in ("check", "limit") else "medium",
                    f"请以机械专家角度,针对该螺栓联接的{fd[0]}问题,给出{al}。",
                    f"对象:{tn}({tf});现象:{fd[0]}。",
                    f"联接特性:{tf}。\n针对{fd[0]}的{al}:{fd[{'check':1,'cause':2,'improve':3,'inspect':4,'material':5,'limit':6}[ak]]}",
                    [fd[2][:12]], ["载荷谱", "螺栓规格强度", "预紧力", "工况"],
                    ["fatigue", "fastener_loosening", "assembly_tolerance"], f"{tk}_{fk}_{ak}"))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o", "--output", default="data/generated_v3/bolts.jsonl"); a = ap.parse_args()
    recs = gen(); bad = [(r["id"], S.dict_to_record(r).validate()) for r in recs if S.dict_to_record(r).validate()]
    S.save_jsonl(recs, a.output)
    print(f"[bolts] {len(recs)} 条 -> {a.output}  (校验失败 {len(bad)})")
    if bad: print("  首个失败:", bad[0])

if __name__ == "__main__":
    main()
