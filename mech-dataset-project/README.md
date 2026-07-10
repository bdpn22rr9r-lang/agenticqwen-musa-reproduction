# mech-dataset-project

机械工程高质量 SFT 数据集建设项目。为 Qwen2.5-7B-Instruct LoRA/SFT 构建一套**会识别风险、会追问、不编造数值**的机械工程训练数据。

> 本项目是 `mechqa-qwen-lora` 仓库的子项目。上游训练链路(MUSA GPU + LlamaFactory)已在该仓库根目录的 `TECH_STACK.md`/`SOP.md` 中就绪。上游计划书:`Codex_LongTerm_Workbench/projects/2026-07-09_model-training/`。

**当前版本:v0.1-seed(种子版)**。完整版目标 5000 训练 + 300/300/100 评测,需按 §迭代路径 分批扩充。本版交付的是**可运行的流水线 + 规范 + 种子数据**,不是完整 5000 条。

---

## 快速开始

```bash
# 需要 Python 3.10+(纯标准库,零依赖)。本机用 winget 装的 3.12。
cd mech-dataset-project
python scripts/run_pipeline.py --version v0.1-seed
```

一键完成:合并数据池 → 分组切分 → 导出 alpaca → 质量报告。产物在 `data/releases/v0.1-seed/` 与 `reports/quality_report_v0.1-seed.json`。

单独运行各环节(均可用 `python scripts/<name>.py -h` 查看用法):

```bash
python scripts/build_golden.py                      # 生成黄金样本
python scripts/generate_engineering_cases.py        # 生成轴类疲劳批次
python scripts/normalize_schema.py --all            # 迁移 mechqa-qwen-lora v1/v2
python scripts/convert_mechqa.py data/raw/mechqa/dataset_example/train_sample.json -n 50
python scripts/validate_schema.py data/releases/v0.1-seed/*_master.jsonl
python scripts/check_near_duplicates.py data/releases/v0.1-seed/train_master.jsonl
python scripts/check_data_leakage.py <train> <test>
```

---

## 目录结构

```text
mech-dataset-project/
├── README.md                     # 本文件
├── docs/                         # 6 份规范(数据质量的基石)
│   ├── dataset_spec.md           #   主数据 schema(20 字段)
│   ├── task_taxonomy.md          #   10 类任务 + 5000 配比 + 对象/维度覆盖
│   ├── answer_style_guide.md     #   答案规范(4 类逻辑)
│   ├── rejection_and_boundary_rules.md  # 禁止编造红线
│   ├── review_rubric.md          #   人工评分(8 维度 + 一票退回)
│   └── dataset_card.md           #   数据集说明卡
├── scripts/                      # 17 个脚本(零依赖标准库)
│   ├── schema.py                 #   主数据 dataclass + 校验 + IO
│   ├── build_golden.py           #   黄金样本生成
│   ├── generate_engineering_cases.py  # 模板驱动批量生成
│   ├── normalize_schema.py       #   v1/v2 迁移
│   ├── convert_mechqa.py         #   MechQA 转换
│   ├── validate_schema.py / check_empty_fields.py / check_duplicates.py
│   ├── check_near_duplicates.py / check_numeric_claims.py
│   ├── check_forbidden_patterns.py / check_units.py / check_data_leakage.py
│   ├── split_dataset.py          #   分组防泄漏切分
│   ├── export_llamafactory.py    #   主格式 → alpaca + dataset_info
│   ├── register.py               #   注册到 LlamaFactory(打印远程命令)
│   ├── build_quality_report.py   #   质量报告
│   └── run_pipeline.py           #   一键主入口
├── prompts/                      # 3 个生成/审核 prompt 模板
├── data/
│   ├── raw/mechqa/               #   clone 的 MechQA(已获取)
│   ├── converted/                #   migrated_v2 + mechqa_converted
│   ├── generated/                #   golden_samples + batch_shaft_fatigue
│   └── releases/v0.1-seed/       #   切分产物 + alpaca + dataset_info
└── reports/
    ├── source_inventory.csv      #   数据来源清单
    └── quality_report_v0.1-seed.json
```

---

## 本次交付(v0.1-seed)

**数据**(共 191 条):
| 来源 | 条数 | task_type | review_status |
|---|---:|---|---|
| 黄金样本 `build_golden` | 29 | 设计/疲劳/信息不足/材料/计算/FEA/故障/基础/工具/证据 | seed_pending_review |
| 轴类批次 `generate` | 32 | design_review / fatigue_failure | model_generated |
| v2 迁移 `normalize` | 80 | v1/v2 旧 5 类(v1/v2 去重保留 v2) | seed_pending_review |
| MechQA 转换 | 50 | context_extraction | seed_pending_review |

**切分**:train 159 / validation 16 / test 13 / challenge 3(按 `split_group` 整组防泄漏)。

**质量指标**:
| 指标 | 结果 | 计划书目标 |
|---|---|---|
| JSON/Schema 合法率 | 100% | 100% ✓ |
| 空 instruction/input/output | 0 | 0 ✓ |
| 完全重复 | 0 | 0% ✓ |
| 无来源具体数值 | 0 | ≤1% ✓ |
| 禁止编造表述 | 0 | — ✓ |
| train/test 泄漏(split_group) | 0 | 0 ✓ |
| 近似重复(≥0.88) | 93 对 | ≤5% ⚠️ 见已知局限 |

---

## ⚠️ 已知局限(诚实声明)

1. **非完整 5000 条**:本版是种子(v0.1-seed),完整版需按 §迭代路径 分批扩充。
2. **未经真人审核**:所有样本 `review_status` 为 `seed_pending_review`/`model_generated`,**绝不**标 `expert_approved`。A 级样本(安全关键/强度疲劳/材料参数)必须真人机械工程师审核后方可用于正式训练/产品。
3. **近似重复偏高(93 对)**:主要来自轴类 batch 的"同对象跨工况"样本,是单批次同主题的固有特征。review/path 两类已按对象/工况差异化;扩到多主题多批次 + 人工去重后整体会降到 ≤5%。
4. **MechQA 转换样本含已知标注噪声**(数值串行、性能类型错误):每条已加警示,必须人工核验实体/数值/单位/条件/DOI。
5. **units 检查 1 条良性告警**:工程计算样本中"N/mm²=MPa"的单位等价说明,非真实错误。

---

## 迭代到 5000 条的路径

按计划书"构建→训练→评估→按错误补数据"闭环:

1. **规范先行**(已就绪):`docs/` 6 份规范定义了 schema、10 类配比、答案风格、红线、审核标准。生成前必读。
2. **分批生成**(每批 50-100 条,单一主题):
   - 参照 `generate_engineering_cases.py` 的模板思路,新建批次(齿轮/轴承/螺栓/焊接/FEA/计算/故障等),每批一个 `(对象×维度×任务)` 组合。
   - 用 `prompts/` 的 prompt 驱动大模型生成初稿,或直接精写(如 `build_golden.py`)。
   - **控制近似重复**:同主题批次不超过 ~100 条,跨主题分散;conclusion/distinction 类精写不批量。
3. **自动检查**:`run_pipeline.py` 跑通后,用 `check_*.py` 验证。不达标(scheme/重复/泄漏/数值)的进 `data/rejected/`。
4. **人工审核**:按 `review_rubric.md` 的 A(100%)/B(≥30%)/C(≥10%) 三级,通过后 `review_status=expert_approved`。
5. **训练验证**:`register.py` → 远程 `mech-qwen-sft-official` 容器 → `llamafactory-cli train`(配置见仓库根 `TECH_STACK.md`,务必 `flash_attn:disabled + bf16`)。
6. **按错误补数据**:记录模型在未见案例上的错误类型(漏风险/编造数值/不追问/混淆静强度疲劳),针对性补反例与追问数据。
7. **扩到 10 类配比**:对照 `task_taxonomy.md` 的 5000 条配比,逐类补齐。

**关键原则**:不以"已生成 N 条"为完成标准;以"未见测试题上的工程准确性、风险覆盖、边界意识、无依据数值率"为验收指标。

---

## 与 mechqa-qwen-lora 训练的衔接

```bash
# 远程容器内(mech-qwen-sft-official):
LF=/workspace/mech-qwen-sft/third_party/LlamaFactory_MUSA
cp <本仓库>/mech-dataset-project/data/releases/v0.1-seed/train_alpaca.json $LF/data/mech_sft_v0_1_seed.json
# 合并 dataset_info.json 中的 "mech_sft_v0_1_seed" 条目(见 register.py 输出)
MUSA_LAUNCH_BLOCKING=1 MUSA_VISIBLE_DEVICES=0 \
  llamafactory-cli train <config>.yaml   # dataset: mech_sft_v0_1_seed
```

`register.py -r data/releases/v0.1-seed --lf-data <LF data 目录>` 可自动复制并合并(本机无 LlamaFactory 时只打印命令)。

## 工具链

- **Python 3.10+**(零依赖标准库)。本机原本无 Python(只有 WindowsApps 占位符),已用 `winget install Python.Python.3.12` 安装 3.12.10。
- 调用注意:若 `python` 仍指向 Store 占位符,用显式路径 `C:\Users\<user>\AppData\Local\Programs\Python\Python312\python.exe`,并设 `PYTHONIOENCODING=utf-8` 避免终端中文乱码。
- 终端中文乱码仅为显示问题,数据文件均为 UTF-8 正确存储。
