# 技术栈

## 模型与微调方法

| 项 | 说明 |
|---|---|
| 基础模型 | `Qwen/Qwen2.5-7B-Instruct`（约 15G，4 个 safetensors 分片，ModelScope 下载） |
| 微调方法 | LoRA SFT（监督微调，轻量适配参数） |
| LoRA 目标层 | `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj` |
| 训练阶段 | `stage: sft`，`finetuning_type: lora` |
| 模板 | `qwen` |

## 训练框架

- **Llama-Factory v0.9.3**，经摩尔线程 MUSA 适配的副本 `LlamaFactory_MUSA`（用 `musify-text` 迁移 + 人工补丁，详见 `DEV_LOG.md`）。
- 安装方式：`pip install -e .`（可编辑模式，容器内）。
- CLI：`llamafactory-cli`（train / chat / export）。

## 硬件与驱动

| 项 | 值 |
|---|---|
| GPU | 8 × MTT S5000（摩尔线程），单卡约 80GB 显存 |
| 宿主机驱动 | `3.3.5-server` |
| GPU 工具 | `mthreads-gmi`（不是 nvidia-smi） |
| 服务器 | `worker31005`，用户 `mccxadmin` |

## 容器与镜像

- 长期训练容器：`mech-qwen-sft-official`（基于官方 `musa-train` 镜像）。
- 官方镜像：`registry.mthreads.com/public/musa-train:4.3.4_kuae2.1_20260106_alinux`。
- 容器内 Python 环境：Python 3.10.12、Torch 2.5.0、`torch_musa` 可用、`musa available: True`、`device count: 8`。
- 容器内已额外安装：`ahocorapy`（musify-text 依赖）、`modelscope`（下载模型）。
- 挂载：宿主机 `/home/mccxadmin/projects/mech-qwen-sft` ↔ 容器 `/workspace/mech-qwen-sft`。

## 训练稳定基线（第一阶段验证通过，必须遵守）

> ⚠️ MUSA 上 Torch SDPA 反向传播会产全 NaN，**必须关闭**。详见 `PITFALL_LOG.md`。

```yaml
# 训练（关键项）
bf16: true                  # 不用 fp16（动态范围小易溢出）
flash_attn: disabled        # 强制 vanilla/eager attention，关闭 SDPA
learning_rate: 5.0e-5       # 从 2.0e-4 降下来，更稳
per_device_train_batch_size: 1
template: qwen
finetuning_type: lora
```

```bash
# 推理（关键项）
--infer_dtype bfloat16 --flash_attn disabled   # dtype 必须与训练对齐
```

排查工具：`MUSA_LAUNCH_BLOCKING=1`（同步定位）、`max_steps: 1`（单步诊断）。

## 数据格式

- LLaMA-Factory 三字段：`instruction` / `input` / `output`。
- 注册于 `LlamaFactory_MUSA/data/dataset_info.json`，`columns` 映射 `prompt=instruction, query=input, response=output`。

## 仓库与版本控制

- Git 仓库：https://github.com/bdpn22rr9r-lang/mechqa-qwen-lora
- 本机 git 访问 GitHub 需走代理 `127.0.0.1:7897`（见全局 `PITFALL_LOG.md`）。
- 数据集 / 配置 / 脚本 / 文档入库；模型权重、adapter、checkpoint 不入库（远程保留）。

## 关键路径（远程）

```text
宿主机项目目录：  /home/mccxadmin/projects/mech-qwen-sft
容器内项目目录：  /workspace/mech-qwen-sft
本仓库克隆位置：  /workspace/mech-qwen-sft/imports/mechqa-qwen-lora
基础模型：        /workspace/mech-qwen-sft/models/Qwen2.5-7B-Instruct
LlamaFactory：    /workspace/mech-qwen-sft/third_party/LlamaFactory_MUSA
训练输出：        /workspace/mech-qwen-sft/outputs/...
训练日志：        /workspace/mech-qwen-sft/logs/...
```

## 运行方式（摘要）

完整流程见 `SOP.md`。核心三步：① `git clone` 本仓库 → ② `python scripts/build_mech_dataset_v1.py` 生成/注册数据 → ③ `llamafactory-cli train <yaml>` 训练。
