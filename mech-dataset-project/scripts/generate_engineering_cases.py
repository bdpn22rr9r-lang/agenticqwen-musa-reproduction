"""模板驱动的工程数据批量生成器(差异化版)。

每个 (对象×工况×问法) 组合产出**实质不同**的 output(独特失效机理/校核重点/制造检测),
避免近似重复。演示计划书阶段四"分批生成"流程。

生成的样本 review_status=model_generated,需人工审核。
扩展: 新增 OBJ/LOAD 条目或 ASK 类型即可扩到更多批次。

用法:
  python generate_engineering_cases.py -o data/generated/batch_shaft_fatigue.jsonl
  python generate_engineering_cases.py --list
"""
from __future__ import annotations
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S

BOUNDARY = ("边界说明:圆角半径、粗糙度、硬度、安全系数等具体数值需结合尺寸、载荷、"
            "材料状态、工艺能力和适用标准由责任工程师确定,不应凭通用记忆直接给出。")

# 每个对象的独特失效/制造/检测描述(用于差异化 output)
OBJ = {
    "cross_hole": {
        "name": "横向销孔",
        "failure": "横向孔削弱净截面,孔边应力集中系数高,交变载荷下易在孔口与轴外表面的交界面萌生疲劳裂纹",
        "mfg": "孔口必须去毛刺并倒圆,关注孔壁表面完整性;若热处理后加工需考虑对表层残余应力的影响",
        "inspect": "对孔区及孔口倒圆处进行磁粉或渗透检测,重点查孔口轴向截面有无裂纹",
    },
    "keyway": {
        "name": "键槽",
        "failure": "键槽根部应力集中,长键槽端部尤其危险,交变扭矩下易从根部圆角萌生疲劳裂纹",
        "mfg": "键槽根部留圆角避免尖角,可喷丸或表面淬火强化,控制键槽侧面与根部粗糙度",
        "inspect": "对键槽根部圆角做磁粉检测,核查键槽与键的配合及端部过渡",
    },
    "shoulder": {
        "name": "轴肩台阶",
        "failure": "轴肩圆角处因截面突变产生应力集中,圆角越小集中越严重,旋转弯曲下易在圆角处疲劳",
        "mfg": "在轴承定位允许范围内尽量加大圆角半径,必要时设卸载槽或过渡环,保证圆角表面质量",
        "inspect": "目检圆角成形,对关键轴肩做磁粉检测确认无裂纹",
    },
    "smooth": {
        "name": "光轴(对照)",
        "failure": "无明显应力集中源,疲劳主要受表面粗糙度、尺寸系数和材料疲劳强度控制",
        "mfg": "保证表面质量和直线度,关键配合面可滚压或喷丸以引入表层压应力",
        "inspect": "检查表面刀痕与直线度,确认无划伤等疲劳源",
    },
}
LOAD = {
    "bending":  {"name": "交变弯曲载荷", "check": "计算最大弯曲名义应力,按旋转/非旋转确定应力循环特性(对称或脉动),结合疲劳缺口系数做疲劳校核", "param": "弯矩载荷谱与最大弯矩"},
    "torsion":  {"name": "交变扭矩",     "check": "计算扭转剪应力幅,注意键槽/花键处的扭转应力集中,按剪切疲劳强度校核",                 "param": "扭矩载荷谱与最大扭矩"},
    "combined": {"name": "弯扭复合交变载荷", "check": "按第三或第四强度理论合成当量应力,分别评估静强度当量应力与疲劳等效应力幅",        "param": "弯矩与扭矩载荷谱"},
    "rotating": {"name": "旋转弯曲(轴转动)", "check": "轴表面每转承受一次对称弯曲循环,按对称循环疲劳极限校核,并核查转速是否接近共振",   "param": "转速与弯矩载荷谱"},
}
HEAT = {"quenched": "调质状态", "induction": "表面感应淬火", "unspecified": "热处理状态未注明"}
MISSING = {
    "geometry": "孔径/轴径/圆角半径等几何尺寸",
    "material": "材料牌号与热处理状态、力学性能",
    "spectrum": "弯矩/扭矩载荷谱与循环次数",
    "all": "几何尺寸、材料状态、载荷谱、目标寿命等关键参数",
}
# ask: (task_type, 问句, output 模板分支)
# 注: conclusion/distinction 类 output 结构性强、跨对象易雷同,放在 golden 样本中精写;
#     批量生成只保留 review/path(已按对象/工况差异化),避免近似重复堆积。
ASK = {
    "review": ("design_review",   "请审查该轴在交变载荷下的可靠性并指出关键风险。", "review"),
    "path":   ("fatigue_failure", "应按什么路径进行强度校核?",                       "path"),
}


def build_output(obj_key, load_key, heat_key, miss_key, ask_key) -> str:
    o = OBJ[obj_key]; l = LOAD[load_key]; heat = HEAT[heat_key]; miss = MISSING[miss_key]
    if ask_key == "review":
        lines = [
            "当前信息不足,不能直接给出强度或寿命结论。",
            f"1. 失效模式:{o['name']}在{l['name']}下,{o['failure']}。",
            f"2. 校核路径:{l['check']}。需结合{heat}、几何尺寸与{l['param']}。",
            f"3. 制造与表面:{o['mfg']}。",
            f"4. 检测:{o['inspect']}。",
            f"5. 缺失信息:{miss}。",
            BOUNDARY,
        ]
    elif ask_key == "conclusion":
        lines = [
            "当前不能给出「安全或不安全」的确定结论,因为缺少进行任何校核所必需的信息。",
            f"针对该{o['name']}在{l['name']}下的情形,关键风险在于:{o['failure']}。",
            f"要判断该风险是否实际导致失效,需要确认:{miss};并取得{heat}下的材料疲劳或静强度数据。",
            f"在缺少{l['param']}与几何尺寸时,无法确定实际应力水平是否超过限值,故不能下确定结论。",
            f"补充后可进行{l['check']};制造方面{o['mfg']},检测方面{o['inspect']}。",
        ]
    elif ask_key == "path":
        lines = [
            f"该{o['name']}在{l['name']}下应按疲劳校核路径进行分析,建议步骤如下:",
            f"1. 确认几何(尤其{o['name']}的特征尺寸与圆角)和{heat}下的材料疲劳性能。",
            f"2. 由{l['param']}确定应力幅与平均应力;{l['check']}。",
            f"3. 引入应力集中系数、尺寸系数、表面系数等修正,得到零件疲劳极限。",
            f"4. 制造方面:{o['mfg']};检测方面:{o['inspect']}。",
            f"5. 综合判断是否满足目标寿命;若不足,从几何优化、表面强化或降低应力幅入手。",
            BOUNDARY,
        ]
    else:  # distinction
        lines = [
            f"该{o['name']}承受{l['name']},属于交变载荷工况,应按**疲劳**校核,而非仅做静强度校核。",
            f"原因:交变载荷下即使最大应力远低于屈服,长期循环也会因疲劳而失效;{o['failure']}正是疲劳关注的重点。",
            f"二者区别:静强度校核只看一次加载的最大应力是否低于{heat}下的屈服或强度极限;疲劳校核关注{l['name']}下的应力幅与寿命,并修正{o['name']}的应力集中、尺寸与表面影响。",
            f"区分要点:静强度看最大应力 vs 许用应力;疲劳看应力幅 vs 疲劳极限(经{o['name']}的应力集中、尺寸、表面修正)。",
            f"补充{l['param']}后,按{l['check']}执行疲劳校核。",
        ]
    return "\n".join(lines)


def risk_tags_for(obj_key, load_key, ask_key) -> list:
    tags = []
    if obj_key != "smooth":
        tags += ["stress_concentration"]
    tags += ["fatigue"]
    if load_key == "combined":
        tags.append("static_strength")
    if ask_key == "conclusion":
        tags.append("missing_information")
    tags += ["surface_integrity"]
    return list(dict.fromkeys(tags))


def combinations():
    combos = []
    idx = 0
    for obj in OBJ:
        for load in LOAD:
            for ask in ASK:
                miss = "all" if ask in ("conclusion", "distinction") else (
                    "geometry" if obj == "cross_hole" else "spectrum")
                heat = "unspecified" if ask == "conclusion" else "quenched"
                combos.append((obj, load, heat, miss, ask, idx))
                idx += 1
    return combos


def to_record(combo, version) -> S.MasterRecord:
    obj, load, heat, miss, ask, idx = combo
    tt, q, _ = ASK[ask]
    o = OBJ[obj]; l = LOAD[load]
    rec = S.MasterRecord(
        id=f"gen_{obj}_{load}_{ask}_{idx:03d}",
        task_type=tt, domain="shaft", subdomain=f"shaft_{obj}_{load}",
        difficulty="hard" if ask in ("conclusion", "distinction") else "medium",
        language="zh",
        instruction=("你是一名机械设计审查工程师。请识别关键风险并给出校核路径;缺少依据时不得编造固定数值。"
                     if tt != "info_insufficient"
                     else "你是一名谨慎的机械工程助手。信息不足时必须说明缺什么,不得强行下结论。"),
        input=(f"对象:{HEAT[heat]}传动轴,{o['name']},位于高应力区。工况:承受{l['name']}。"
               f"未提供{l['param']}、几何尺寸、材料牌号与目标寿命。\n问题:{q}"),
        output=build_output(obj, load, heat, miss, ask),
        risk_tags=risk_tags_for(obj, load, ask),
        numeric_claims=[], requires_tool=True, requires_rag=True,
        source_type="model_generated", source_ref="batch:shaft_fatigue",
        license="internal-approved", review_status="model_generated", reviewer="",
        split_group=f"shaft_{obj}_{load}_{ask}", version=version,
    )
    return rec


def main():
    ap = argparse.ArgumentParser(description="生成轴类疲劳工程数据批次(差异化)")
    ap.add_argument("-o", "--output", default="data/generated/batch_shaft_fatigue.jsonl")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--version", default="v0.1-seed")
    a = ap.parse_args()
    combos = combinations()
    if a.list:
        for c in combos:
            print(f"  {c[5]:03d}: obj={c[0]} load={c[1]} ask={c[4]}")
        print(f"合计 {len(combos)} 条")
        return
    recs = [to_record(c, a.version) for c in combos]
    bad = [(r.id, r.validate()) for r in recs if r.validate()]
    S.save_jsonl([r.to_dict() for r in recs], a.output)
    from collections import Counter
    print(f"[generate] {len(recs)} 条 -> {a.output}  (校验失败 {len(bad)})")
    print(f"  task_type: {dict(Counter(r.task_type for r in recs))}")
    if bad:
        print("  首个失败:", bad[0])


if __name__ == "__main__":
    main()
