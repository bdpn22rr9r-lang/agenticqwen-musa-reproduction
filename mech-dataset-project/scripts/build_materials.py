"""第11批: 材料力学/选材(深度, 9类型×7失效×6角度=378条)。归 material_heat_treatment。
用法: python build_materials.py -o data/generated_v3/materials.jsonl"""
from __future__ import annotations
import os, sys, argparse, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S
AUTHOR, V3 = "claude", "v3"
def make(cat, sub, diff, instr, inp, out, ev, cond, tags, sg):
    rid = "v3_mat2_" + re.sub(r"[^\w]+", "_", sg).strip("_")[:40]
    return S.MasterRecord(id=rid, category=cat, sub_category=sub, difficulty=diff, language="zh",
        instruction=instr, input=inp, output=out, evidence=ev, conditions=cond, risk_tags=tags, task_type=cat,
        source_type="expert_authored", license="pending", review_status="self_reviewed", reviewer="claude_expert_review",
        author=AUTHOR, split_group="v3_mat2_sg_" + re.sub(r"[^\w]+", "_", sg)[:36], version=V3).to_dict()
MTYPES = {
    "carbon": ("碳钢(20/45)", "通用、成本低、可焊性好、强度中等"),
    "alloy": ("合金钢(40Cr/35CrMo)", "强度韧性高、需热处理、用于关键件"),
    "stainless": ("不锈钢(304/316)", "耐蚀、铬镍、注意应力腐蚀与加工硬化"),
    "cast_iron": ("铸铁(HT250/QT600)", "铸造好、减振、抗压、塑性低"),
    "aluminum": ("铝合金(6061/7075)", "轻、导电、比强度高、疲劳强度较低"),
    "copper": ("铜合金(黄铜/青铜)", "导电导热、耐磨、耐蚀"),
    "titanium": ("钛合金(TC4)", "高强轻、耐蚀、成本高、难加工"),
    "plastic": ("工程塑料(尼龙/PEEK)", "轻、耐蚀、自润滑、强度低耐温低"),
    "composite": ("复合材料(碳纤维)", "高比强度比刚度、各向异性、成本高"),
}
MFAIL = {
    "select": ("选材权衡", "material_heat_treatment", "依强度/韧性/疲劳/刚度/温度/腐蚀/成本/可制造性综合权衡,截面大须考虑淬透性", "建立需求矩阵选材、查材料手册与认证数据、考虑工艺性", "对照设计要求与工况选材", "材料手册(GB/T 标准数据)", "无万能材料,需权衡取舍", "选材是设计基础"),
    "yield": ("屈服失效", "material_heat_treatment", "应力超过屈服强度,发生塑性变形", "增大截面或提强度等级、减载、用安全系数 n", "应力校核 σ≤σs/n", "材料屈服强度 σs 数据", "塑性材料主要静载失效", "静载过载工况"),
    "brittle": ("脆性断裂", "material_heat_treatment", "冲击或低温、应力集中,材料脆性开裂", "提韧性、查冲击功、避低温脆性转变温度", "夏比冲击 CVN、断裂韧度 KIC", "材料韧性与转变温度数据", "铸铁/高强钢低温危险", "冲击或低温工况"),
    "fatigue": ("疲劳失效", "material_heat_treatment", "交变应力下疲劳裂纹萌生扩展至断裂,远低于屈服", "提疲劳强度、减应力集中、表面强化(喷丸/滚压)", "S-N/ε-N 曲线、疲劳极限", "材料疲劳数据", "交变载荷主要失效", "无明确疲劳极限需无限寿命设计"),
    "corrosion": ("腐蚀失效", "material_heat_treatment", "化学/电化学腐蚀,均匀或局部(点蚀/晶间/应力腐蚀)", "选耐蚀材料、防护涂层、阴极保护、控制介质", "工况介质分析、腐蚀速率试验", "耐蚀材料与防护方法", "腐蚀环境关键失效", "降低寿命与承载"),
    "weld": ("可焊性", "material_heat_treatment", "碳当量高易冷裂、热影响区性能变化", "选低碳当量材料、预热、合适焊材与工艺", "碳当量 CE 估算、裂纹敏感性试验", "材料成分(CE)", "高碳高合金难焊", "影响焊接结构选材"),
    "harden": ("可热处理性", "material_heat_treatment", "淬透性决定截面内部能否淬硬,影响大件性能", "选合适淬透性材料、匹配截面尺寸", "淬透性曲线、端淬(Jominy)试验", "材料淬透性数据", "大截面须选高淬透性钢", "影响热处理效果"),
}
ANGLES = [("check", "判定/选材"), ("cause", "失效机理"), ("improve", "改进措施"), ("inspect", "检测方法"), ("material", "材料数据"), ("limit", "适用边界")]
def gen():
    out = []
    for tk, (tn, tf) in MTYPES.items():
        for fk, fd in MFAIL.items():
            for ak, al in ANGLES:
                if ak == "cause": body = fd[2]
                elif ak == "check": body = f"判定依据:{fd[2]}"
                else: body = fd[{"improve":3,"inspect":4,"material":5,"limit":6}[ak]]
                out.append(make(fd[1], f"mat2_{tk}_{fk}", "hard" if ak in ("check","limit") else "medium",
                    f"请以机械专家角度,针对{tn}的{fd[0]}问题,给出{al}。",
                    f"对象:{tn}({tf});问题:{fd[0]}。",
                    f"材料特性:{tf}。\n针对{fd[0]}的{al}:{body}",
                    [fd[2][:12]], ["载荷性质", "温度", "介质", "截面尺寸"],
                    ["static_strength", "fatigue", "heat_treatment"], f"{tk}_{fk}_{ak}"))
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-o", "--output", default="data/generated_v3/materials.jsonl"); a = ap.parse_args()
    recs = gen(); bad = [(r["id"], S.dict_to_record(r).validate()) for r in recs if S.dict_to_record(r).validate()]
    S.save_jsonl(recs, a.output); print(f"[materials] {len(recs)} 条 -> {a.output} (校验失败 {len(bad)})")
    if bad: print("  首个失败:", bad[0])
if __name__ == "__main__":
    main()
