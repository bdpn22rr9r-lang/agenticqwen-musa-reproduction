# 需求文档

## 背景

用户希望在摩尔线程 MUSA GPU（8×MTT S5000）上，用 `Qwen2.5-7B-Instruct` + LoRA 微调，做一个**机械工程助手**模型，覆盖设计审查、制造工艺规划、设备故障诊断三个方向。

远程训练已在 `worker31005` 服务器上完成环境搭建和链路验证（见 `DEV_LOG.md`）。本项目（`mechqa-qwen-lora`）是这套训练的**数据交付仓库**：把审校过的数据集、验证过的配置、可复现的脚本集中到一个 GitHub 仓库，供远程服务器拉取使用，也便于版本管理和回滚。

## 用户目标

- 提供一份**经人工核验**的机械工程 SFT 数据集（首批 80 训练 + 20 评测）。
- 提供一套**验证过能稳定跑通**的单卡 LoRA 训练配置（不产 NaN）。
- 提供可远程一键「生成 / 校验 / 复制 / 注册」数据的脚本。
- 让训练链路可复现：远程 `git clone` → 跑脚本 → 审阅 → 训练 → 推理验证。

## 功能范围

- 数据集：5 类共 80 条训练样本（设计审查 / 工艺规划 / 故障诊断 / 安全边界 / 材料证据抽取），20 条独立评测集。
- 训练配置：单卡（MUSA）LoRA SFT YAML，含稳定基线参数。
- 脚本：`build_mech_dataset_v1.py`，在远程容器内重新生成、校验类别配比与重叠、复制到训练目录、注册到 Llama-Factory `dataset_info.json`。
- 文档：项目 7 件套 + v1 交付包说明。

## 非目标（第一阶段不做）

- 工业级准确率 / 认证级语料。
- 复杂 CAD 图纸理解。
- 标准条文的精确引用。
- 完整 Agent 工具链 / RAG。
- 8 卡大规模训练（需先确认数据质量和单卡稳定性）。

> 以上放入**第二阶段**：数据扩充（30–100 条经审校样本）、固定评测集、RAG、工具调用、8 卡训练。

## 验收标准

**数据**（v1 已自验 PASS）：

```text
train=80  eval=20
design_review=24  process_planning=20  fault_diagnosis=20
safety_boundary=8  material_evidence=8
duplicate=0  train/eval overlap=0  validation=PASS
```

**训练链路**（第一阶段已验证）：

- 容器内 `torch.musa.is_available()` 为 `True`，8 卡可见。
- 单卡 LoRA 训练成功：loss 持续下降、`grad_norm` 有限、adapter 全部权重有限（无 NaN）。
- LoRA adapter 可加载推理，机械三方向能输出结构化答案，无概率 NaN。
- 数据集可在 Llama-Factory 正确注册并加载。

**仓库**：

- 远程 `git clone` + 跑脚本能完整复现数据注册。
- v1 交付包 ZIP 的 SHA256 已记录（见 `DEV_LOG.md`）。

## 待确认问题

- 代理 `127.0.0.1:7897` 是否要持久化到 git 全局配置（影响本机 push）。
- 第二阶段数据规模目标（30 / 50 / 100 条）与审校资源。
- MechQA 全量数据（约 20 万条）的合规下载通道与商业使用许可边界。
- 是否需要把稳定训练出的 LoRA adapter 也纳入版本管理（当前不入库，仅远程保留）。
