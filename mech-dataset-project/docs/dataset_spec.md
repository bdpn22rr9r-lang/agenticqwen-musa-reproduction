# 数据集规范 — 主数据 Schema

本文件定义机械工程 SFT 数据集的**主数据格式**(master schema)。所有数据(人工撰写、开源转换、批量生成)统一落成此格式,存为 JSONL(每行一条)。训练前由 `export_llamafactory.py` 投影成 LLaMA-Factory 的 alpaca 三字段格式。

> 与 mechqa-qwen-lora 旧版 v1/v2 的 4 字段(`category/instruction/input/output`)格式的关系:`normalize_schema.py` 负责把旧数据迁移成本格式。本格式是 v1/v2 的超集。

## 1. 主数据字段定义

| 字段 | 类型 | 必填 | 取值/规范 |
|---|---|---|---|
| `id` | string | ✅ | 全局唯一。命名 `<domain>_<subdomain>_<6位序号>`,如 `shaft_cross_hole_fatigue_000123` |
| `task_type` | string | ✅ | 任务类型,见 [task_taxonomy.md](task_taxonomy.md) 的 10 类枚举 |
| `domain` | string | ✅ | 机械对象大类,如 `shaft`/`gear`/`bearing`/`bolted_joint`/`weldment`/`spring`/`beam_plate`/`hydraulic` |
| `subdomain` | string | ✅ | 对象+失效模式细分,如 `cross_hole_fatigue`/`gear_pitting`/`bolt_loosening` |
| `difficulty` | string | ✅ | `easy` / `medium` / `hard` |
| `language` | string | ✅ | `zh`(本阶段全中文) |
| `instruction` | string | ✅ | 角色+任务提示,非空 |
| `input` | string | ✅ | 问题/场景描述,非空 |
| `output` | string | ✅ | 标准答案,非空,遵循 [answer_style_guide.md](answer_style_guide.md) |
| `risk_tags` | string[] | ✅ | 工程风险标签(可为空数组 `[]`),见下方枚举 |
| `numeric_claims` | object[] | ✅ | output 中出现的具体数值声明,可为 `[]`;每项 `{value, unit, source}` |
| `requires_tool` | bool | ✅ | 是否需要调用计算工具(FEA/强度计算器) |
| `requires_rag` | bool | ✅ | 是否需要检索标准/材料库 |
| `source_type` | string | ✅ | `expert_constructed` / `mechqa_converted` / `model_generated` / `literature_extract` / `v1v2_migrated` |
| `source_ref` | string | ✅ | 来源标识(DOI / 文件名 / 批次号),可空字符串 |
| `license` | string | ✅ | `internal-approved` / `cc-by-4.0` / `gpl-3.0` / `unverified` |
| `review_status` | string | ✅ | 审核状态机,见 §3 |
| `reviewer` | string | ✅ | 审核人 ID,未审核为空字符串 |
| `split_group` | string | ✅ | 切分分组键,同案例多问法共享;`split_dataset.py` 按此整组划分 |
| `version` | string | ✅ | 数据集版本,如 `v0.1-seed` |

## 2. 风险标签枚举(risk_tags)

从下列中选取(可多选),用于统计风险覆盖度:

```text
net_section_reduction        净截面削弱
stress_concentration         应力集中
fatigue                      交变疲劳
static_strength              静强度
stiffness_deflection         刚度/变形
buckling_stability           屈曲/稳定性
wear_contact_fatigue         磨损/接触疲劳
vibration_resonance          振动/共振
thermal_deformation          热变形/热应力
surface_integrity            表面完整性
heat_treatment               热处理影响
manufacturing_process        制造工艺
assembly_tolerance           装配/公差
inspection_ndt               检测/无损检测
corrosion                    腐蚀/环境
fastener_loosening           紧固件松动
missing_information          信息不足/需追问
fabricated_value_risk        编造数值风险(反例样本用)
```

## 3. 审核状态机(review_status)

```text
model_generated       大模型生成的原始初稿,未做任何检查
seed_pending_review   生成并自检通过,等待真人审核(本次 v0.1-seed 黄金样本的默认态)
self_reviewed         生成方自评通过(结构/数值/单位自查)
expert_approved       真人机械工程师终审通过 —— 唯一允许进正式训练/产品的状态
rejected              审核退回(进 data/rejected/,附 reason)
```

> ⚠️ **铁律**:只有 `review_status=expert_approved` 的样本才能进入正式训练集 `releases/`。A 级样本(安全关键/强度疲劳/材料参数/标准/计算值/故障结论)必须 100% 真人审核。我(Claude)生成的样本**只能停在 `seed_pending_review` / `self_reviewed`**,绝不标 `expert_approved`。

## 4. 示例(横向销孔轴 — 设计评审正例)

```json
{
  "id": "shaft_cross_hole_fatigue_000001",
  "task_type": "design_review",
  "domain": "shaft",
  "subdomain": "cross_hole_fatigue",
  "difficulty": "hard",
  "language": "zh",
  "instruction": "你是一名机械设计审查工程师。请识别关键风险并给出校核路径;缺少依据时不得编造固定数值。",
  "input": "对象:调质传动轴,中部有一横向销孔,位于高弯矩区。工况:承受交变弯曲载荷。未提供孔径、轴径、材料牌号、载荷谱和目标寿命。",
  "output": "当前信息不足,不能直接给出强度或寿命结论。\n1. 失效模式:横向孔导致净截面削弱,孔边产生显著应力集中,在交变弯曲下需按疲劳校核(非静强度)。\n2. 校核路径:先确认几何(孔径/轴径/孔口倒圆)、材料状态(牌号/热处理/硬度)与载荷谱;计算名义应力与理论应力集中系数,结合疲劳强度缩减系数和表面系数估算疲劳寿命。\n3. 制造与表面:孔口应去毛刺、倒圆,关注表面完整性;若热处理后加工需考虑加工对表层残余应力的影响。\n4. 检测:必要时对孔区进行磁粉/渗透等表面无损检测。\n5. 缺失信息:孔径、轴径、材料牌号与热处理状态、弯矩载荷谱、循环次数、目标寿命、适用安全等级。\n边界说明:圆角半径、粗糙度、硬度、安全系数等具体数值需结合尺寸、载荷、材料状态、工艺能力和适用标准由责任工程师确定,不应凭通用记忆直接给出。",
  "risk_tags": ["net_section_reduction","stress_concentration","fatigue","surface_integrity","heat_treatment","inspection_ndt","missing_information"],
  "numeric_claims": [],
  "requires_tool": true,
  "requires_rag": true,
  "source_type": "expert_constructed",
  "source_ref": "",
  "license": "internal-approved",
  "review_status": "seed_pending_review",
  "reviewer": "",
  "split_group": "shaft_cross_hole_case_A",
  "version": "v0.1-seed"
}
```

## 5. 训练投影格式(alpaca)

`export_llamafactory.py` 从主数据投影出(丢弃元数据):

```json
{"instruction": "...", "input": "...", "output": "..."}
```

并生成 `dataset_info.json`:

```json
{"mech_sft_v0_1_seed": {"file_name": "train_alpaca.json", "columns": {"prompt": "instruction", "query": "input", "response": "output"}}}
```

## 6. 文件组织

- 主数据按 `review_status` + 用途分散存放:`data/generated/`(初稿)、`data/converted/`(开源转换)、`data/reviewed/`(审核通过)、`data/rejected/`(退回)。
- 最终切分产物在 `data/releases/<version>/`:`train/validation/test/challenge` 的 `_master.jsonl` + `_alpaca.json` + `dataset_info.json`。
- 所有 JSONL 文件:UTF-8、无 BOM、每行一条独立 JSON 对象。
