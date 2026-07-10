# 数据集说明卡(Dataset Card)

## 概述

- **名称**:mech-dataset-project — 机械工程高质量 SFT 数据集
- **用途**:用于 Qwen2.5-7B-Instruct 的 LoRA/SFT,训练一个能识别工程风险、区分失效模式、信息不足时追问、不编造数值的机械工程助手。
- **基座项目**:mechqa-qwen-lora(v1/v2 各 80+20 条链路验证已完成)。
- **上游计划书**:`Codex_LongTerm_Workbench/projects/2026-07-09_model-training/Qwen2.5-7B-LoRA-SFT-PLAN.md` + 用户提供的《机械工程高质量 SFT 数据集建设计划书》。

## 当前版本:v0.1-seed(种子版)

| 项 | 值 |
|---|---|
| 版本 | v0.1-seed |
| 目标规模(完整版) | 训练 5000 / 验证 300 / 测试 300 / 挑战 100 |
| 本版实际规模 | 见 `reports/quality_report_v0.1-seed.json`(黄金样本 + 1 个工程批次 + MechQA 转换样本) |
| 语言 | 中文(MechQA 转换样本保留英文原文 context 作证据) |
| 格式 | 主数据 JSONL(带元数据) → 训练时投影成 alpaca `{instruction,input,output}` |

## 数据来源(source_type)

- `expert_constructed`:黄金样本,人工级撰写,本次由 Claude 生成初稿。
- `mechqa_converted`:从 MechQA(`mz-516/MechQA`,JSONL)转换,保留 context + DOI,标注待人工核验。
- `model_generated`:`generate_engineering_cases.py` 模板组合生成的批次。
- `v1v2_migrated`:从 mechqa-qwen-lora v1/v2 迁移。

## 许可证

- 自建数据:`internal-approved`(内部使用)。
- MechQA:上游论文 CC BY 4.0、代码 GPL-3.0;**商业使用前必须单独确认数据集及上游论文文本的使用边界**。转换样本 `license` 字段标 `cc-by-4.0`,并保留 `source_ref=DOI`。
- 企业内部资料:须完成脱敏、匿名化、保密与训练授权确认后,`license` 方可标 `internal-approved`。

## ⚠️ 局限与诚实声明

1. **v0.1-seed 是种子版,不是完整 5000 条**。完整版需按 README 的迭代路径分批扩充。
2. **所有样本 `review_status=seed_pending_review`,未经真人机械工程师 A 级审核**。Claude 生成的样本**绝不**标 `expert_approved`。在审核完成前,不得用于产品声明、安全决策或标准合规。
3. **MechQA 转换样本含已知标注噪声**(数值串行、单位/性能类型错误)。转换后必须人工逐条核验实体/数值/单位/适用条件/DOI。
4. 训练用 MUSA GPU 时必须 `flash_attn:disabled + bf16`(见 mechqa-qwen-lora `TECH_STACK.md` / `PITFALL_LOG.md`)。

## 工具链要求

- **数据处理脚本**:Python 3.10+(纯标准库,零依赖)。远程训练容器已具备 Python 3.10.12。本机若无 Python,数据正确性由 `tools/validate.pl`(perl,MSYS 自带)保证;python 脚本待在有 Python 的环境运行。
- **训练**:LlamaFactory v0.9.3(MUSA 适配),复用 mechqa-qwen-lora 的注册与配置。

## 字段速查

见 [dataset_spec.md](dataset_spec.md)。任务类型与配比见 [task_taxonomy.md](task_taxonomy.md)。答案规范见 [answer_style_guide.md](answer_style_guide.md),红线见 [rejection_and_boundary_rules.md](rejection_and_boundary_rules.md),审核标准见 [review_rubric.md](review_rubric.md)。

## 引用与致谢

- MechQA: M. Zhang et al., `https://github.com/mz-516/MechQA`(每条转换样本保留 DOI)。
- 基座模型:Qwen2.5-7B-Instruct(阿里巴巴,ModelScope)。
- 训练框架:LlamaFactory(`hiyouga/LlamaFactory`,v0.9.3)。
