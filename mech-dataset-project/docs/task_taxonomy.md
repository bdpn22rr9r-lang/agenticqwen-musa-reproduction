# 任务分类体系与覆盖范围

本文件定义数据集的 10 类任务、配比、机械对象覆盖和工程问题维度。**生成数据前必须对照本表,确保覆盖均衡,不围绕单一对象/问法堆砌。**

## 1. 任务类型与配比(目标 5000 条训练集)

| task_type | 中文名 | 训练条数 | 占比 | 说明 |
|---|---|---:|---:|---|
| `structural_strength` | 结构设计与强度分析 | 1000 | 20% | 静强度/刚度/稳定性校核路径 |
| `fatigue_failure` | 疲劳、应力集中与失效 | 750 | 15% | 交变载荷、缺口效应、S-N、失效模式 |
| `info_insufficient` | 信息不足、主动追问、禁止编造 | 750 | 15% | 缺条件时追问、不编造数值 |
| `material_heat_treatment` | 材料、热处理与表面完整性 | 600 | 12% | 选材、热处理工艺、表层影响 |
| `engineering_calculation` | 工程计算与公式解释 | 500 | 10% | 含完整计算过程+单位+假设 |
| `fea_interpretation` | 有限元结果解释与评审 | 500 | 10% | 网格、边界、应力结果判读 |
| `fault_diagnosis` | 故障诊断与维护 | 350 | 7% | 现象→原因→排查 |
| `basic_concept` | 基础概念与术语 | 250 | 5% | 力学/材料/制造基础 |
| `context_extraction` | 基于上下文的信息抽取 | 150 | 3% | MechQA 类,限占比,带证据 |
| `tool_awareness` | 工具调用意识 | 150 | 3% | 识别何时该查标准/调计算工具 |
| | **合计** | **5000** | **100%** | |

评测集:验证 300 / 测试 300 / 挑战 100(均不参与训练,见 [dataset_spec.md](dataset_spec.md) §3)。

> **刻意压低 `context_extraction` 占比**:避免模型被训练成只输出"765 MPa"式属性抽取器。MechQA 类必须带文献上下文、保留适用条件、附 DOI。

## 2. 机械对象覆盖(domain)

每类任务都要覆盖不同对象,**禁止大量围绕同一种轴或同一种问法改写**:

| domain | 对象 |
|---|---|
| `shaft` | 轴、销轴、横向孔、键槽、轴肩、花键 |
| `gear` | 齿轮、蜗轮蜗杆、链轮、带轮 |
| `bearing` | 滚动轴承、滑动轴承、轴承座 |
| `bolted_joint` | 螺栓连接、销连接、键连接、过盈配合 |
| `weldment` | 焊接结构、支架、机架、箱体 |
| `spring_coupling` | 弹簧、联轴器、离合器、制动器 |
| `beam_plate` | 梁、板、壳体、薄壁结构 |
| `hydraulic_seal` | 液压元件、传动部件、密封结构 |

## 3. 工程问题维度(同一对象必须从多维度构造)

同一个机械对象,必须沿以下维度展开不同问题,避免同义改写:

```text
静强度           刚度与变形        交变载荷与疲劳     应力集中
屈曲与稳定性     磨损与接触疲劳    振动与共振         热变形与热应力
制造工艺         热处理           表面完整性         装配与公差
检测与无损检测   维护与失效分析
```

## 4. 难度分布建议

- `easy`(30%):单一概念、可直接回答
- `medium`(50%):需识别 2~3 个风险点、给出校核路径
- `hard`(20%):信息不足、多失效模式耦合、需追问或工具——挑战集以 hard 为主

## 5. 反例样本(fabricated_value_risk)

少量样本故意构造"错误答案"(如直接给"圆角 R2、Ra0.8、HRC45、安全系数1.5"),`risk_tags` 含 `fabricated_value_risk`,用于训练模型识别和拒绝编造。这类样本在 `output` 中应明确标注"此为不当回答示例"或通过对照结构呈现正/误。

## 6. 生成批次规划(供迭代扩量)

按"对象 × 维度 × 任务类型"组合成批次,每批 50~100 条。示例批次:

- `batch_shaft_fatigue`:交变弯曲下带横向孔/键槽/台阶的轴 → `fatigue_failure`
- `batch_bolt_loosening`:周期载荷下螺栓防松 → `fault_diagnosis` + `fatigue_failure`
- `batch_fea_mesh`:FEA 网格敏感性、边界条件 → `fea_interpretation`
- `batch_missing_params`:故意缺关键参数的设计题 → `info_insufficient`
- `batch_material_selection`:选材与热处理匹配 → `material_heat_treatment`

详见 `scripts/generate_engineering_cases.py` 的模板库。
