# 审核 Prompt

> 供真人机械工程师审核,或二次大模型辅助筛选时统一口径。对应 `docs/review_rubric.md`。

## 审核任务

对每条样本按 8 个维度打 0~5 分,并检查一票退回条件。**不只看语言通顺,要判工程逻辑正确性。**

## 8 个维度

专业准确性 / 风险覆盖 / 边界意识 / 数值可信度 / 公式与单位 / 工程可执行性 / 表达质量 / 安全性。
综合 ≥ 4/5 方通过。

## 一票退回(出现任一即 reject)

1. 编造标准编号(引用不存在的 GB/T、ISO、ASTM)
2. 编造材料参数(强度/硬度/模量与已知矛盾)
3. 无依据给安全系数
4. 公式错误
5. 单位错误或量级错误(如 GPa 写成 MPa)
6. 把静强度结论当作疲劳寿命结论
7. 条件不足时给出确定的安全结论
8. 引用不存在的检测或制造要求

## 审核输出

```json
{"id":"shaft_cross_hole_fatigue_000123","verdict":"approve|reject",
 "scores":{"accuracy":5,"risk_coverage":4,"boundary":5,"numeric":5,
            "formula_unit":5,"executability":4,"expression":4,"safety":5},
 "reject_reason":"","comment":"...","reviewer":"reviewer_01"}
```

## 审核分级

- **A 级(100% 审)**: 安全关键设计、强度/疲劳结论、材料与热处理参数、标准规范、FEA 结论、带计算值、故障结论。
- **B 级(≥30%)**: 原理解释、设计评审、追问、工艺分析。
- **C 级(≥10%)**: 基础术语、简单抽取、普通知识。

## 关于 v0.1-seed 的特别提醒

本批由 Claude 生成,`review_status=seed_pending_review`。审核通过后改为 `expert_approved` 并填 `reviewer`,方可进正式训练。MechQA 转换样本(`source_type=mechqa_converted`)需额外核对数值与性能的对应关系(已知有自动标注噪声)。
