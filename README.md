# mechqa-qwen-lora

基于 `Qwen2.5-7B-Instruct` 的机械工程 LoRA SFT **数据交付仓库**：存放经审校的训练/评测数据集、验证过的训练配置和远程执行脚本，供远程摩尔线程 GPU 训练服务器 `git clone` 后直接使用。

> 上游训练项目：`Codex_LongTerm_Workbench/projects/2026-07-09_model-training`（远程服务器 `worker31005`，8×MTT S5000）。本仓库是它的「数据 + 配置 + 脚本」交付物，不是训练产物本体。

## 项目状态

- 当前阶段：**第一阶段完成**（训练链路验证 + 首批 80 条数据交付）
- 最后更新：2026-07-10
- GitHub：https://github.com/bdpn22rr9r-lang/mechqa-qwen-lora

## 仓库内容

```text
mechqa-qwen-lora/
├── README.md                 # 本文件（项目总览）
├── REQUIREMENTS.md           # 需求、范围、验收标准
├── TECH_STACK.md             # 模型/框架/硬件/容器/关键参数
├── DEV_LOG.md                # 开发记录（环境搭建→NaN 定位→数据交付）
├── PITFALL_LOG.md            # 项目踩坑（SDPA/dtype/musify/数据噪声）
├── SOP.md                    # 数据构建→上传→注册→训练→推理流程
├── RETROSPECTIVE.md          # 第一阶段复盘 + 第二阶段规划
└── mech-qwen-sft-v1/         # v1 数据交付包
    ├── README.md
    ├── datasets/mech_sft_v1_80.json     # 80 条训练样本
    ├── eval/mech_eval_v1_20.json        # 20 条评测样本（不参与训练）
    ├── configs/qwen25_7b_mech_lora_sft_v1_80.yaml   # 验证过的单卡训练配置
    └── scripts/build_mech_dataset_v1.py # 远程生成/校验/复制/注册脚本
```

## 训练数据类别配比（v1，共 80 条）

| 类别 | 数量 |
|---|---:|
| 机械设计审查 | 24 |
| 制造工艺规划 | 20 |
| 设备故障诊断 | 20 |
| 安全/信息不足与拒绝编造 | 8 |
| 带证据的材料性能抽取（MechQA，人工核验） | 8 |
| **合计** | **80** |

另建 20 条固定评测集，不参与训练。

## 远程使用方式（摘要）

在远程 `mech-qwen-sft-official` 容器内：

```bash
cd /workspace/mech-qwen-sft
git clone https://github.com/bdpn22rr9r-lang/mechqa-qwen-lora.git imports/mechqa-qwen-lora
python imports/mechqa-qwen-lora/scripts/build_mech_dataset_v1.py   # 生成/校验/注册数据集
# 审阅数据后，用稳定基线训练：
MUSA_LAUNCH_BLOCKING=1 MUSA_VISIBLE_DEVICES=0 \
  llamafactory-cli train /workspace/mech-qwen-sft/configs/qwen25_7b_mech_lora_sft_v1_80.yaml \
  2>&1 | tee /workspace/mech-qwen-sft/logs/mech_sft_v1_80.log
```

完整流程见 `SOP.md`；训练稳定基线见 `TECH_STACK.md`。

## 重要约束

- v1 数据是**训练验证初稿，不是工业认证语料**；产品化前需机械工程人员逐条审校。
- 训练/推理必须显式 `flash_attn: disabled` + `bf16`（MUSA SDPA 反向会产 NaN，详见 `PITFALL_LOG.md`）。
- 执行任何任务前，先读 Workspace 全局文档（`00_Global/`）+ 本项目文档。

## 关键入口

- 想了解「为什么这么做」→ `DEV_LOG.md`、`RETROSPECTIVE.md`
- 想跑训练 → `SOP.md`、`TECH_STACK.md`
- 踩坑速查 → `PITFALL_LOG.md`
- 数据怎么来的 → `mech-qwen-sft-v1/README.md`、`SOP.md`
