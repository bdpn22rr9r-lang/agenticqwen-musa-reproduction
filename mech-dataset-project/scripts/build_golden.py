"""黄金样本生成器(v0.1-seed 种子主体)。

精心编写的多任务高质量样本,覆盖计划书重点: 应力集中、静强度vs疲劳、缺失条件、
材料热处理、FEA误读、不编造数值、检测制造要求、故障诊断、工程计算。

每条 output 遵循 docs/answer_style_guide.md, 不含无依据数值。
review_status=seed_pending_review(未经真人审核,不进正式训练)。

用法:
  python build_golden.py -o data/generated/golden_samples.jsonl
"""
from __future__ import annotations
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S

BOUNDARY = ("边界说明:圆角半径、粗糙度、硬度、安全系数等具体数值需结合尺寸、载荷、"
            "材料状态、工艺能力和适用标准由责任工程师确定,不应凭通用记忆直接给出。")

# 核心案例: (task_type, domain, subdomain, difficulty, instruction, input, output, risk_tags, tool, rag)
# id 与 split_group 在 build 时生成
CASES = [
    # ---------- 设计评审 ----------
    ("design_review", "shaft", "cross_hole_fatigue", "hard",
     "你是一名机械设计审查工程师。请识别关键风险并给出校核路径;缺少依据时不得编造固定数值。",
     "对象:调质传动轴,中部有一横向销孔,位于高弯矩区。工况:承受交变弯曲载荷。未提供孔径、轴径、材料牌号、载荷谱和目标寿命。",
     "当前信息不足,不能直接给出强度或寿命结论。\n1. 失效模式:横向孔导致净截面削弱,孔边产生显著应力集中,交变弯曲下需按疲劳校核(非静强度)。\n2. 校核路径:确认孔径/轴径/孔口倒圆、材料与热处理状态、载荷谱;算名义应力与理论应力集中系数,结合疲劳强度缩减系数与表面系数估算寿命。\n3. 制造与表面:孔口去毛刺、倒圆,关注表面完整性;热处理后加工需考虑对表层残余应力的影响。\n4. 检测:必要时对孔区做磁粉或渗透等表面无损检测。\n5. 缺失信息:孔径、轴径、材料牌号与热处理状态、弯矩载荷谱、循环次数、目标寿命、适用安全等级。\n" + BOUNDARY,
     ["net_section_reduction", "stress_concentration", "fatigue", "surface_integrity", "inspection_ndt", "missing_information"], True, True),

    ("design_review", "shaft", "keyway_fatigue", "hard",
     "你是一名机械设计审查工程师。请识别关键风险并给出校核路径;缺少依据时不得编造固定数值。",
     "对象:传动轴上开有平键槽,位于扭矩输入端。工况:承受交变扭矩与弯矩。未提供键槽尺寸、圆角、材料牌号和载荷谱。",
     "当前信息不足,不能直接判定是否安全。\n1. 失效模式:键槽根部存在应力集中,在交变扭矩+弯矩下易萌生疲劳裂纹,长键槽端部尤其危险。\n2. 校核路径:确认键槽型式、宽度、深度、根部圆角与配合;按合成应力(弯+扭)做疲劳校核,关注键槽过渡区。\n3. 制造与表面:键槽根部应留圆角、避免尖角,可考虑表面淬火或喷丸强化以提高疲劳强度。\n4. 缺失信息:键槽几何、圆角半径、材料与热处理、载荷谱、目标寿命。\n" + BOUNDARY,
     ["stress_concentration", "fatigue", "surface_integrity", "heat_treatment", "missing_information"], True, True),

    ("design_review", "shaft", "shoulder_fatigue", "medium",
     "你是一名机械设计审查工程师。请识别关键风险并给出校核路径;缺少依据时不得编造固定数值。",
     "对象:阶梯轴,轴肩处直径突变,用于轴承定位。承受旋转弯曲。未提供两段直径、圆角半径和材料。",
     "轴肩是常见应力集中源,需重点关注。\n1. 失效模式:轴肩圆角处应力集中,旋转弯曲下易疲劳开裂。\n2. 校核路径:确认大小端直径比、圆角半径与相邻零件(轴承内圈)的干涉,算理论应力集中系数并做疲劳校核。\n3. 设计建议:在定位允许范围内尽量加大圆角半径,必要时用卸载槽减小应力集中。\n4. 缺失信息:两段直径、圆角半径、材料与热处理、载荷谱。\n" + BOUNDARY,
     ["stress_concentration", "fatigue", "surface_integrity", "missing_information"], True, False),

    ("design_review", "gear", "tooth_root_fatigue", "hard",
     "你是一名齿轮设计审查工程师。请指出关键失效风险与校核方向。",
     "对象:某闭式齿轮传动,持续传递较大扭矩。未提供模数、齿数、材料、热处理和载荷谱。",
     "信息不足,无法给出确定性结论。\n1. 失效风险:齿根弯曲疲劳折断、齿面点蚀/剥落(接触疲劳)、胶合。\n2. 校核方向:齿根弯曲应力按 ISO 6336 或 GB/T 3480 校核;齿面接触应力按赫兹接触校核;高速重载还需校核胶合。\n3. 材料/热处理:渗碳淬火或调质,需保证齿面硬度与心部韧性匹配。\n4. 缺失信息:模数、齿数、压力角、螺旋角、材料与热处理、载荷谱、润滑条件。\n" + BOUNDARY,
     ["fatigue", "wear_contact_fatigue", "stress_concentration", "heat_treatment", "missing_information"], True, True),

    ("design_review", "bearing", "fit_clearance", "medium",
     "你是一名机械设计审查工程师。请评估轴承配合与游隙选择的合理性。",
     "对象:深沟球轴承,内圈旋转、受径向载荷。未提供载荷大小、转速、工况温度和座孔公差。",
     "配合与游隙需结合工况确定,不能凭通用值给出。\n1. 关注点:内圈受旋转载荷应选过盈配合;游隙要补偿温升和过盈引起的膨胀;转速影响 dn 值与润滑选择。\n2. 校核方向:计算当量动载荷与额定寿命 L10;核查配合后游隙是否仍处在合适范围。\n3. 缺失信息:径向/轴向载荷、转速、温度、公差等级、预期寿命。\n" + BOUNDARY,
     ["assembly_tolerance", "fatigue", "thermal_deformation", "missing_information"], False, True),

    ("design_review", "bolted_joint", "loosening_fatigue", "hard",
     "你是一名机械设计审查工程师。请分析该螺栓连接在交变载荷下的风险。",
     "对象:受轴向交变载荷的螺栓连接,被连接件为金属。未提供螺栓规格、预紧力、载荷幅和材料。",
     "信息不足,无法给出确定性结论。\n1. 失效风险:交变载荷下螺栓疲劳断裂、被连接件分离导致松动、预紧力衰减后疲劳寿命急剧下降。\n2. 校核路径:按螺栓疲劳强度校核应力幅;保证残余预紧力大于分离要求;应力幅应尽量小(低螺栓刚度/高被连接件刚度)。\n3. 防松措施:合适预紧、防松件(弹垫/尼龙螺母/施必牢螺纹/点焊等)按工况选择,不能笼统给一个数值。\n4. 缺失信息:螺栓规格、强度等级、预紧力、载荷幅、被连接件刚度、工况温度。\n" + BOUNDARY,
     ["fatigue", "fastener_loosening", "assembly_tolerance", "missing_information"], True, True),

    ("design_review", "weldment", "weld_toe_fatigue", "hard",
     "你是一名焊接结构审查工程师。请指出该焊接接头的疲劳风险与改进方向。",
     "对象:承载梁的对接+角焊缝组合接头,承受交变载荷。未提供板厚、焊缝形式、载荷谱和材质。",
     "信息不足,无法给出寿命结论。\n1. 失效风险:焊趾处应力集中与残余拉应力叠加,是疲劳裂纹主要起源;未熔合、咬边等缺陷会进一步降低疲劳强度。\n2. 评估方向:按名义应力法或热点应力法(IIW 推荐)做疲劳评估;关键焊缝可考虑焊趾打磨/TIG 熔修/超声冲击提高疲劳强度。\n3. 制造要求:控制焊缝成形、避免咬边与未熔合,重要接头做无损检测。\n4. 缺失信息:板厚、焊缝形式、材质、载荷谱、探伤等级。\n" + BOUNDARY,
     ["fatigue", "stress_concentration", "surface_integrity", "inspection_ndt", "manufacturing_process", "missing_information"], True, True),

    ("design_review", "beam_plate", "thin_wall_buckling", "hard",
     "你是一名结构设计审查工程师。请评估薄壁梁的稳定性风险。",
     "对象:薄壁箱形梁,受弯剪。未提供板厚、高厚比、加筋布置和载荷。",
     "信息不足,无法判定是否安全。\n1. 失效风险:薄板在压应力区可能局部失稳(屈曲),先于强度破坏;腹板在高剪下也可能剪切屈曲。\n2. 校核路径:按板壳屈曲理论或规范校核受压翼缘与腹板的宽厚比/高厚比;必要时设置纵向加劲肋。\n3. 缺失信息:板厚、截面尺寸、加筋布置、材料、载荷与边界约束。\n" + BOUNDARY,
     ["buckling_stability", "stiffness_deflection", "missing_information"], True, True),

    # ---------- 疲劳与失效 ----------
    ("fatigue_failure", "shaft", "rotating_bending_fatigue", "medium",
     "你是一名疲劳分析工程师。请说明校核方法与所需信息。",
     "对象:旋转轴,承受恒定横向力(旋转弯曲)。请说明应如何做疲劳校核。",
     "旋转弯曲下轴上一点承受对称循环弯曲应力,需做疲劳校核而非静强度校核。\n1. 方法:算最大弯曲名义应力;查材料的疲劳极限(或由强度极限估算)与疲劳缺口系数;考虑尺寸、表面、置信度等修正系数得到零件疲劳极限;按 σ_a 与疲劳极限比较或做有限寿命估算。\n2. 关键区分:静强度用最大应力对屈服/强度的比;疲劳用应力幅与疲劳极限。两者不能混用。\n3. 缺失信息:几何、材料疲劳性能、载荷幅、目标寿命、应力集中源。\n" + BOUNDARY,
     ["fatigue", "stress_concentration", "surface_integrity", "missing_information"], True, True),

    ("fatigue_failure", "gear", "contact_fatigue_pitting", "medium",
     "你是一名齿轮失效分析工程师。请解释齿面点蚀的成因与应对。",
     "现象:闭式齿轮工作一段时间后齿面出现点蚀。请分析原因与改进方向。",
     "点蚀是齿面接触疲劳的典型表现。\n1. 成因:齿面接触应力反复作用,次表面剪切应力最大处萌生微裂纹,扩展后材料剥落形成凹坑;润滑不良、齿面硬度不足、接触应力过大会加速点蚀。\n2. 应对:校核接触应力是否满足许用值;提高齿面硬度(渗碳/表面淬火);改善润滑与表面粗糙度;必要时修正齿轮修形以减小偏载。\n3. 区分:早期点蚀可能跑合后收敛,扩展性点蚀则预示寿命不足,需停机处理。\n4. 缺失信息:载荷、材料硬度、润滑状态、点蚀发展阶段。",
     ["wear_contact_fatigue", "surface_integrity", "heat_treatment", "missing_information"], False, True),

    ("fatigue_failure", "spring_coupling", "spring_fatigue", "medium",
     "你是一名机械设计工程师。请说明螺旋压缩弹簧疲劳校核要点。",
     "对象:承受交变载荷的圆柱螺旋压缩弹簧。请说明疲劳校核要点与易错点。",
     "弹簧在交变载荷下需做疲劳校核。\n1. 方法:计算簧丝内侧最大剪切应力幅与平均应力;查材料的剪切疲劳极限;按 Goodman/Gerber 型模型校核;关注共振(工作频率远离固有频率)。\n2. 易错点:不能只用最大剪切应力做静强度判断;喷丸可显著提高弹簧疲劳强度;表面脱碳与划伤会大幅降低寿命。\n3. 缺失信息:簧丝直径、中径、有效圈数、材料、载荷幅与频率。",
     ["fatigue", "surface_integrity", "vibration_resonance", "missing_information"], True, False),

    # ---------- 信息不足 / 追问 ----------
    ("info_insufficient", "shaft", "missing_all_params", "hard",
     "你是一名谨慎的机械工程助手。信息不足时必须说明缺什么,不得强行下结论。",
     "问题:这根轴能不能承受 10 kN·m 的扭矩?是否安全?",
     "当前无法判断是否安全,缺少大量必要信息。\n需要补充:\n1. 几何:轴径、长度、有无键槽/孔/台阶等应力集中源。\n2. 材料:牌号、热处理状态、许用剪应力或强度数据。\n3. 载荷性质:10 kN·m 是静载还是交变?有无弯矩叠加?\n4. 约束与寿命:支承跨距、转速、目标寿命与可靠度。\n5. 标准:适用的安全系数与设计规范。\n补充后可进行的校核:静强度(τ=T/Wt)、扭转刚度、若交变则疲劳校核。\n" + BOUNDARY,
     ["missing_information", "static_strength", "fatigue", "missing_information"], True, False),

    ("info_insufficient", "general", "missing_material", "medium",
     "你是一名谨慎的机械工程助手。信息不足时必须说明缺什么。",
     "问题:这个零件用 45 钢做,许用应力取多少?",
     "不能直接给出许用应力数值。\n原因:45 钢的力学性能随热处理状态(正火/调质/表面淬火)和毛坯尺寸差异很大;许用应力还需依据载荷性质(静/交变)、失效准则(屈服/疲劳)和适用安全系数确定。\n需要补充:热处理状态与硬度、毛坯截面尺寸、载荷性质、适用的设计标准。\n补充后可从材料手册或标准查对应强度并按安全系数折算。该问题建议检索材料标准(requires_rag)。",
     ["missing_information", "heat_treatment", "static_strength"], False, True),

    ("info_insufficient", "general", "missing_load_spectrum", "medium",
     "你是一名谨慎的机械工程助手。信息不足时必须说明缺什么。",
     "问题:这台减速机能用 10 年吗?",
     "无法判断寿命,缺少关键信息。\n需要补充:\n1. 载荷谱:实际工况下的扭矩/功率随时间分布(不是名义值)。\n2. 寿命定义:是指齿轮/轴承的疲劳寿命,还是大修周期?\n3. 工况:每天运行小时数、启停次数、冲击载荷、环境温度。\n4. 维护:润滑与保养状况。\n5. 设计依据:原始设计的强度等级、材料与精度。\n补充后可按 Miner 累积损伤或轴承 L10 寿命估算。",
     ["missing_information", "fatigue", "wear_contact_fatigue"], True, False),

    # ---------- 材料与热处理 ----------
    ("material_heat_treatment", "general", "selection_strength_toughness", "medium",
     "你是一名材料选择工程师。请说明选材权衡。",
     "问题:某轴要求高强度同时有较好韧性,应如何考虑材料与热处理?",
     "高强度与高韧性常需权衡。\n1. 思路:中碳调质钢(如 40Cr、42CrMo)调质后能获得较好的强韧匹配;对更高强度可考虑表面淬火(硬化表层抗疲劳、心部保持韧性)或渗碳钢(渗碳淬火用于齿面)。\n2. 关键:不能只看抗拉强度,要同时关注屈服强度、冲击韧性与疲劳性能;还要考虑淬透性(截面越大越要选淬透性高的钢)。\n3. 工艺影响:调质后若再加工,注意加工余量与表层性能;表面强化(喷丸/滚压)可提升疲劳强度。\n4. 缺失信息:载荷性质、截面尺寸、工况温度、成本与可制造性约束。具体牌号与硬度需结合标准确定(requires_rag)。",
     ["heat_treatment", "static_strength", "fatigue", "surface_integrity", "missing_information"], False, True),

    ("material_heat_treatment", "general", "heat_treat_distortion", "medium",
     "你是一名热处理工程师。请说明热处理变形控制要点。",
     "问题:精密零件淬火后变形超差,可能原因与对策?",
     "淬火变形常见,需系统控制。\n1. 原因:加热/冷却不均产生热应力与相变应力;零件几何不对称、截面突变会加剧变形;材料淬透性与淬火介质影响显著。\n2. 对策:优化结构(对称、避免截面突变);选择合适淬火介质(油淬/分级/等温);控制加热温度与保温;采用淬火压床或工装定型;预留精加工余量;对已变形件可校直+去应力回火。\n3. 表面完整性:注意脱碳与淬火裂纹,关键件做无损检测。\n4. 缺失信息:材料、零件几何、热处理工艺、精度要求。",
     ["heat_treatment", "thermal_deformation", "manufacturing_process", "surface_integrity", "missing_information"], False, False),

    ("material_heat_treatment", "general", "surface_hardening", "medium",
     "你是一名机械设计工程师。请说明表面淬火对疲劳的影响。",
     "问题:表面感应淬火为什么能提高轴的疲劳强度?",
     "表面感应淬火能显著提高疲劳强度,机理是多方面的。\n1. 表层形成高硬度马氏体,提高强度与耐磨性,疲劳裂纹更难萌生。\n2. 淬火后在表层形成有利的残余压应力,能抵消部分工作拉应力,显著延长疲劳寿命。\n3. 注意:硬化层深度与位置要覆盖高应力区;过渡区(硬度回落处)可能成为新的薄弱点;淬火后要回火并控制裂纹。\n4. 局限:对接触疲劳也有效,但不能替代几何优化(圆角/倒圆仍是基础)。\n5. 缺失信息:材料、硬化层深度要求、工况载荷。",
     ["heat_treatment", "surface_integrity", "fatigue", "stress_concentration", "missing_information"], False, False),

    # ---------- 工程计算 ----------
    ("engineering_calculation", "shaft", "torsion_shear_calc", "medium",
     "你是一名工程计算工程师。请给出完整计算过程,含公式、单位、假设。",
     "已知:实心圆轴承受扭矩 T=5 kN·m,轴径 d=50 mm。求最大扭转剪应力。材料许用剪应力待确认。",
     "已知:T=5 kN·m=5×10^6 N·mm,d=50 mm。\n1. 抗扭截面系数:Wt=π·d³/16=π×50³/16≈24544 mm³。\n2. 最大扭转剪应力:τ=T/Wt=(5×10^6)/24544≈203.7 MPa。\n3. 单位换算:1 kN·m=10^6 N·mm,结果为 MPa(N/mm²)。\n4. 假设:纯扭转、实心圆截面、弹性范围内、无应力集中。\n5. 未考虑:键槽/孔/台阶引起的应力集中(实际需乘理论应力集中系数);弯矩叠加;交变载荷下的疲劳。\n6. 进一步校核:需对照材料许用剪应力判断是否安全;若为交变载荷需做疲劳校核而非仅静强度。许用剪应力需查材料标准与安全系数(requires_rag)。",
     ["static_strength", "stress_concentration"], False, True),

    ("engineering_calculation", "beam_plate", "bending_stress_calc", "medium",
     "你是一名工程计算工程师。请给出完整计算过程。",
     "已知:矩形截面简支梁,b=20 mm,h=50 mm,跨中受集中力 F=2 kN,跨度 L=200 mm。求跨中最大弯曲应力。",
     "已知:F=2 kN=2000 N,L=200 mm,b=20 mm,h=50 mm。\n1. 跨中弯矩(简支梁中点集中力):M=F·L/4=2000×200/4=1.0×10^5 N·mm。\n2. 抗弯截面系数:W=b·h²/6=20×50²/6≈8333 mm³。\n3. 最大弯曲应力:σ=M/W=(1.0×10^5)/8333≈12.0 MPa。\n4. 单位:N/mm²=MPa。\n5. 假设:线弹性、小变形、材料各向同性、忽略自重。\n6. 未考虑:剪切应力、稳定性(薄壁需另算)、长期蠕变、应力集中。\n7. 进一步校核:对照材料许用应力与安全系数判断。",
     ["static_strength", "stiffness_deflection", "buckling_stability"], False, False),

    ("engineering_calculation", "bolted_joint", "preload_calc", "medium",
     "你是一名工程计算工程师。请说明螺栓预紧与剩余预紧的校核。",
     "已知:螺栓承受工作拉力 F=10 kN,要求残余预紧力不小于工作拉力的 0.5 倍。请说明如何确定所需预紧力并校核螺栓总拉力。",
     "已知:工作拉力 F=10 kN,要求残余预紧力 F''≥0.5F=5 kN。\n1. 相对刚度法:螺栓总拉力 F0=F''+F×(螺栓刚度相对总刚度之比)。常用近似:若被连接件刚度远大于螺栓,外载主要由被连接件承担,F0≈F''+F。\n2. 所需预紧力:为保证 F''≥5 kN,需施加预紧力 F'=F''+(1-相对刚度比)×F;具体需知道螺栓与被连接件刚度比。\n3. 校核:螺栓总拉力产生的应力应低于许用应力;应力幅(与载荷变幅有关)决定疲劳寿命。\n4. 假设:弹性范围内、连接不分离、刚度已知。\n5. 缺失信息:螺栓规格、刚度比、强度等级、载荷是否交变。需结合标准与刚度数据(requires_rag)。",
     ["fastener_loosening", "fatigue", "assembly_tolerance", "missing_information"], False, True),

    # ---------- FEA ----------
    ("fea_interpretation", "general", "mesh_sensitivity", "medium",
     "你是一名有限元分析工程师。请说明应力结果的网格敏感性。",
     "问题:某 FEA 模型加密网格后应力峰值升高很多,如何判断结果是否可信?",
     "网格敏感性问题需谨慎处理。\n1. 现象:在应力集中区(缺口、圆角、接触),网格越密名义应力峰值越高,可能不收敛于真实值——这是奇异点的典型表现。\n2. 判断方法:做网格收敛性研究(逐级加密),看应力是否趋于稳定;若持续发散,说明该点是理论奇异,应改用名义应力+应力集中系数或热点应力法,而不是直接取峰值。\n3. 边界与单元:检查约束是否过约束、单元类型与长宽比是否合理、线性 vs 非线性。\n4. 工程判断:FEA 结果要结合解析解与规范,不能只看云图颜色;对疲劳关键点要用合适的应力提取方法。\n5. 缺失信息:几何、载荷、单元类型、网格尺寸序列。",
     ["stress_concentration", "missing_information"], True, False),

    ("fea_interpretation", "general", "boundary_condition", "medium",
     "你是一名有限元分析工程师。请说明边界条件设置对结果的影响。",
     "问题:FEA 中约束位置对结果影响大吗?应如何设置?",
     "边界条件对结果影响很大,常被低估。\n1. 影响:约束位置与方式直接决定刚度与载荷路径,过约束会人为提高刚度、低估变形与应力,欠约束则可能刚体位移或应力失真。\n2. 原则:尽量模拟真实传力路径;对称结构用对称边界;接触面用接触而非硬约束;集中力作用处易应力奇异,应避免在该处取应力。\n3. 验证:检查反力是否与外载平衡;变形形态是否合理;必要时用 Saint-Venant 原理判断关注区是否远离边界。\n4. 缺失信息:模型几何、载荷、实际安装约束。",
     ["stiffness_deflection", "stress_concentration", "missing_information"], True, False),

    # ---------- 故障诊断 ----------
    ("fault_diagnosis", "general", "reducer_vibration", "medium",
     "你是一名设备故障诊断工程师。请根据现象分析原因与排查步骤。",
     "现象:减速机运行中温升偏高,伴随周期性振动,润滑油颜色变深。",
     "现象提示润滑与啮合/轴承可能存在问题。\n可能原因(按概率):\n1. 润滑油老化、污染或粘度不当,润滑不良导致温升与磨损。\n2. 轴承磨损、游隙异常或装配不良,产生周期性振动。\n3. 齿轮啮合不良、齿面点蚀或偏载,啮合频率振动增大、油中磨粒增多使油色变深。\n4. 联轴器对中不良,引入附加载荷。\n排查步骤:\n1. 检查油位、油品、污染物与换油周期,取样做油液分析(磨粒)。\n2. 采集振动频谱,判断是否存在轴承特征频率或啮合频率及其边带。\n3. 检查联轴器对中与地脚螺栓。\n4. 停机后检查齿面接触斑点、轴承状态与箱体内部。\n5. 依据结果决定换油、校中、更换轴承或修复齿轮。需结合具体型号与运行参数。",
     ["wear_contact_fatigue", "vibration_resonance", "inspection_ndt"], False, False),

    ("fault_diagnosis", "bearing", "bearing_noise", "medium",
     "你是一名设备故障诊断工程师。请分析轴承异响的可能原因。",
     "现象:运转中的滚动轴承发出周期性异响,伴有轻微温升。",
     "异响与温升提示滚动体或滚道可能受损。\n可能原因:\n1. 滚道或滚动体表面出现点蚀/剥落/压痕,周期性冲击产生异响(对应缺陷特征频率)。\n2. 润滑不良或润滑脂流失,干摩擦引起温升与噪声。\n3. 游隙过大或配合松动,引起冲击声。\n4. 安装不当(过盈量过大/锤击损伤)导致滚道损伤。\n排查步骤:\n1. 采集振动/声信号,用包络解调找轴承缺陷特征频率(外圈/内圈/滚动体)。\n2. 检查润滑状态与补充润滑。\n3. 测量游隙与配合。\n4. 必要时拆检滚道与滚动体表面。\n区分:早期点蚀可监测运行,剥落快速扩展则需及时更换。",
     ["wear_contact_fatigue", "vibration_resonance", "inspection_ndt", "assembly_tolerance"], False, False),

    # ---------- 基础概念 ----------
    ("basic_concept", "general", "stress_concentration_concept", "easy",
     "你是一名机械工程教师。请简明解释一个基础概念。",
     "问题:什么是应力集中?为什么它对疲劳特别危险?",
     "应力集中指在几何突变处(缺口、孔、台阶、键槽等)局部应力显著高于名义应力的现象,用理论应力集中系数 Kt 描述。\n对疲劳特别危险的原因:\n1. 疲劳寿命对应力幅极其敏感,局部应力升高会使疲劳寿命呈幂律急剧下降。\n2. 应力集中处易成为疲劳裂纹萌生源。\n3. 静载下局部超过屈服可通过塑性重分布缓解,但交变载荷下高应变循环会持续累积损伤。\n减小措施:加大圆角、避免尖角、表面强化(喷丸/滚压)、降低表面粗糙度、合理设计过渡区。",
     ["stress_concentration", "fatigue", "surface_integrity"], False, False),

    ("basic_concept", "general", "static_vs_fatigue", "easy",
     "你是一名机械工程教师。请简明解释一个基础概念。",
     "问题:静强度校核和疲劳校核有什么区别?",
     "两者关注不同的失效方式。\n静强度校核:针对一次性或缓慢施加的载荷,校核最大应力是否低于屈服或强度极限,防止塑性变形或瞬时断裂。关注的是最大应力与许用应力。\n疲劳校核:针对交变载荷,关注应力幅(变化范围)与平均应力,依据材料的疲劳极限或 S-N 曲线估算寿命。即便最大应力远低于屈服,长期交变也可能疲劳断裂。\n关键区别:\n1. 静强度看最大应力;疲劳看应力幅与循环次数。\n2. 交变载荷必须做疲劳校核,不能用静强度合格代替疲劳合格。\n3. 应力集中、表面质量、尺寸对疲劳影响巨大,对静强度影响相对小。",
     ["static_strength", "fatigue", "stress_concentration", "surface_integrity"], False, False),

    # ---------- 工具调用意识 ----------
    ("tool_awareness", "general", "needs_rag", "medium",
     "你是一名机械工程助手。判断该问题是否需要检索标准或工具,并说明。",
     "问题:Q345 钢的许用应力是多少?",
     "该问题需要检索材料标准或设计规范,不能仅凭通用记忆给出最终设计值。\n原因:Q345 的许用应力取决于载荷性质(静/动载)、工况温度、板厚分组以及适用的设计规范(不同行业规范取值不同);通用模型记忆的数值可能是平均值或不适用,直接给出会误导设计。\n建议:检索适用的国家标准或行业规范(如钢结构设计标准),按板厚分组与载荷工况查许用应力或由强度标准值除以抗力分项系数确定。此问题应走 RAG/标准检索。",
     ["missing_information", "static_strength"], False, True),

    ("tool_awareness", "general", "needs_calc_tool", "medium",
     "你是一名机械工程助手。判断该问题是否需要调用计算工具。",
     "问题:复杂薄壁结构在工作载荷下的应力分布与稳定性如何?",
     "该问题应调用有限元(FEA)等计算工具,难以用解析法准确求解。\n原因:复杂薄壁结构的应力分布、局部稳定性与屈曲行为依赖几何细节、边界条件与载荷路径,解析公式只能给出近似,工程决策需 FEA。\n建议:建立合理的 FEA 模型(注意网格收敛、边界条件、单元类型),对关键区域做应力提取与稳定性校核;FEA 结果仍需结合工程判断与规范。此问题应走计算工具。",
     ["buckling_stability", "stiffness_deflection", "stress_concentration", "missing_information"], True, False),

    # ---------- 上下文抽取(非 MechQA,人工构造的带证据题) ----------
    ("context_extraction", "general", "evidence_property", "medium",
     "请仅依据给定文献片段提取材料性能,并说明适用条件。不得把条件性数值泛化为材料常数。",
     "文献片段:某文献报告经 T6 处理的 A356 铝合金,在室温下测得抗拉强度 324 MPa、屈服强度 280 MPa、延伸率 5%。问题:该材料经 T6 处理后的屈服强度是多少?",
     "依据文献片段,经 T6 处理的 A356 铝合金在室温下屈服强度为 280 MPa。\n适用条件:该数值仅适用于 T6 热处理状态、室温、文献所述的成分与工艺条件;不可泛化为 A356 在所有状态下的屈服强度(铸态、其他热处理状态的数值会不同)。如需用于设计,应以相应标准或认证数据为准。",
     ["missing_information"], False, True),
]


def build(output: str) -> list:
    recs = []
    for i, c in enumerate(CASES):
        tt, dom, sub, diff, instr, inp, out, tags, tool, rag = c
        rec = S.MasterRecord(
            id=f"golden_{dom}_{sub}_{i:03d}",
            task_type=tt, domain=dom, subdomain=sub, difficulty=diff, language="zh",
            instruction=instr, input=inp, output=out,
            risk_tags=tags, numeric_claims=[],
            requires_tool=tool, requires_rag=rag,
            source_type="expert_constructed", source_ref="",
            license="internal-approved",
            review_status="seed_pending_review", reviewer="",
            split_group=f"golden_{dom}_{sub}",
            version="v0.1-seed",
        )
        recs.append(rec.to_dict())
    return recs


def main():
    ap = argparse.ArgumentParser(description="生成黄金样本(种子主体)")
    ap.add_argument("-o", "--output", default="data/generated/golden_samples.jsonl")
    a = ap.parse_args()
    recs = build(a.output)
    bad = [(r["id"], S.dict_to_record(r).validate()) for r in recs if S.dict_to_record(r).validate()]
    S.save_jsonl(recs, a.output)
    from collections import Counter
    print(f"[golden] {len(recs)} 条 -> {a.output}  (校验失败 {len(bad)})")
    print(f"  task_type 分布: {dict(Counter(r['task_type'] for r in recs))}")
    print(f"  domain 分布: {dict(Counter(r['domain'] for r in recs))}")
    if bad:
        print("  首个失败:", bad[0])


if __name__ == "__main__":
    main()
