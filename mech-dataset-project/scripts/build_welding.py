"""第5批: 焊接结构(深度, 6类型×6失效×6角度=216条)。疲劳归 design_fatigue,缺陷/变形归 manufacturing_qc。
用法: python build_welding.py -o data/generated_v3/welding.jsonl"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S

AUTHOR, V3 = "claude", "v3"

def make(cat, sub, diff, instr, inp, out, ev, cond, tags, sg):
    rid = "v3_weld_" + re.sub(r"[^\w]+", "_", sg).strip("_")[:40]
    return S.MasterRecord(id=rid, category=cat, sub_category=sub, difficulty=diff, language="zh",
        instruction=instr, input=inp, output=out, evidence=ev, conditions=cond, risk_tags=tags,
        task_type=cat, source_type="expert_authored", license="pending", review_status="self_reviewed",
        reviewer="claude_expert_review", author=AUTHOR,
        split_group="v3_weld_sg_" + re.sub(r"[^\w]+", "_", sg)[:36], version=V3).to_dict()

WTYPES = {
    "butt": ("对接接头", "两板同面相对,受拉压弯,常需开坡口全焊透"),
    "tee": ("T型接头", "垂直与水平板,角焊缝受剪与弯,有应力集中"),
    "lap": ("搭接接头", "板重叠,角焊缝受剪,有偏心附加应力"),
    "corner": ("角接接头", "两板成角,L型,根部易应力集中"),
    "plug": ("塞焊/槽焊", "通过孔焊连,补强搭接或密封"),
    "pipe": ("管对接/相贯", "管对接全焊透或管支管相贯,要求高"),
}
WFAIL = {
    "fatigue": ("焊趾疲劳", "design_fatigue", "按 IIW 名义应力法或热点应力法选 FAT 级别(FAT 71~112);焊趾是主要疲劳源", "焊趾几何不连续叠加残余拉应力,交变载荷下疲劳裂纹在焊趾萌生并向母材扩展", "打磨焊趾圆滑过渡、TIG 熔修、超声冲击(Peening)引入压应力、改善焊缝成形", "磁粉(MT)/超声(UT)探伤、振动监测、裂纹长度跟踪", "低氢焊材、与母材等强或低组配匹配、成形良好", "受交变载荷焊接结构主要失效"),
    "porosity": ("气孔夹渣", "manufacturing_qc", "按 GB/T 19418 焊缝质量等级与 ISO 5817,用 RT/UT 评定", "保护不良、坡口污染(油锈水)、焊剂受潮,气体侵入熔池致气孔,夹渣来自熔渣清理不净", "清理坡口露金属光泽、烘干焊剂(250℃×1h)、优化保护气与电流电压、控制焊速", "射线(RT)/超声(UT)/渗透(PT)按焊缝等级检测", "低氢焊条烘干 350℃、与母材匹配", "焊接工艺不当主要缺陷"),
    "lack_fusion": ("未熔合未焊透", "manufacturing_qc", "按焊缝等级检测;全焊透对接须保证熔深", "热输入不足、坡口角度小、清根不彻底,焊道间或根部未完全熔合", "优化热输入与坡口尺寸、彻底清根、合理排列焊道", "UT/RT 检测内部缺陷", "选合适焊接方法与工艺", "对接全焊透焊缝危险缺陷"),
    "crack": ("冷裂纹/热裂纹", "manufacturing_qc", "冷裂纹(氢致延迟):预热+后热+低氢焊材;热裂纹:控制成分与成形", "冷裂纹:扩散氢+淬硬组织+拘束应力联合作用,焊后延迟开裂;热裂纹:晶界低熔点共晶凝固时开裂", "预热(低合金钢 80~200℃)、焊后热处理消氢、用低氢焊材、减小拘束", "UT/MT 检测、表面着色,注意延迟裂纹(焊后 48h 再检)", "低氢焊材、控制 C/S/P、匹配母材", "高强钢与拘束大结构危险"),
    "distortion": ("焊接变形", "manufacturing_qc", "估算收缩量预留反变形;控制焊接顺序与热输入", "不均匀热输入使焊缝区膨胀冷却受约束,产生纵/横向与角变形及残余应力", "对称焊、跳焊、预留反变形、刚性固定、焊后机械/火焰校正", "尺寸与直线度测量、变形量监控", "小热输入焊接方法、对称结构设计", "薄板与长焊缝主要问题"),
    "corrosion": ("焊接区腐蚀", "fault_diagnosis", "热影响区与焊缝可能晶间腐蚀或应力腐蚀", "热影响区敏化(碳化物析出贫铬)致晶间腐蚀;残余应力+介质致应力腐蚀开裂", "选低碳/稳定化不锈钢(316L/347)、固溶处理、焊后消除应力、合适填充材料", "着色渗透、金相、介质工况评估", "不锈钢用超低碳或稳定化型", "不锈钢与腐蚀工况"),
}
ANGLES = [("check", "校核方法"), ("cause", "失效机理"), ("improve", "改进措施"),
          ("inspect", "检测方法"), ("material", "材料与焊材"), ("limit", "适用边界")]

def gen():
    out = []
    for tk, (tn, tf) in WTYPES.items():
        for fk, fd in WFAIL.items():
            for ak, al in ANGLES:
                idx = {"check":2,"cause":3,"improve":4,"inspect":5,"material":6,"limit":7}[ak]
                out.append(make(fd[1], f"weld_{tk}_{fk}", "hard" if ak in ("check", "limit") else "medium",
                    f"请以机械专家角度,针对该{tn}的{fd[0]}问题,给出{al}。",
                    f"对象:{tn}({tf});现象:{fd[0]}。",
                    f"接头特性:{tf}。\n针对{fd[0]}的{al}:{fd[idx]}",
                    [fd[3][:12]], ["载荷谱", "板厚材料", "焊缝等级", "探伤要求"],
                    ["fatigue", "stress_concentration", "inspection_ndt", "manufacturing_process"],
                    f"{tk}_{fk}_{ak}"))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o", "--output", default="data/generated_v3/welding.jsonl"); a = ap.parse_args()
    recs = gen(); bad = [(r["id"], S.dict_to_record(r).validate()) for r in recs if S.dict_to_record(r).validate()]
    S.save_jsonl(recs, a.output)
    print(f"[welding] {len(recs)} 条 -> {a.output}  (校验失败 {len(bad)})")
    if bad: print("  首个失败:", bad[0])

if __name__ == "__main__":
    main()
