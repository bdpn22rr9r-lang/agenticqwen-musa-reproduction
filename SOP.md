# 项目 SOP

本项目的标准执行流程：数据构建 → 上传 GitHub → 远程拉取注册 → 训练 → 推理验证。

> 前置依赖（远程已就绪）：长期容器 `mech-qwen-sft-official`、`LlamaFactory_MUSA`（已迁移安装）、基础模型 `Qwen2.5-7B-Instruct`、`modelscope`/`ahocorapy` 已装。环境细节见 `TECH_STACK.md`，搭建历史见 `DEV_LOG.md`。

---

## 1. 数据构建（本地 / 远程均可）

数据由 `mech-qwen-sft-v1/scripts/build_mech_dataset_v1.py` 统一生成、校验、复制、注册。脚本做的事：

1. 重新生成 80 条训练集 + 20 条评测集（5 类配比）。
2. 自验：类别计数、`duplicate=0`、`train/eval overlap=0`、`validation=PASS`。
3. 复制到远程训练目录并注册进 `LlamaFactory_MUSA/data/dataset_info.json`。

> 数据是训练验证初稿，非工业认证语料。MechQA 类样本必须人工核验，详见 `RETROSPECTIVE.md` 风险边界与全局 `COMPOUND_LOG.md`。

## 2. 上传 GitHub（本机）

本机 git 必须走代理（见全局 `SOP.md` / `PITFALL_LOG.md`）：

```bash
cd C:/Users/22475/Desktop/Workspace/10_Projects/mechqa-qwen-lora

# 提交
git add -A
git -c core.autocrlf=false commit -m "说明

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"

# 推送（带代理；若已 git config --global http.proxy 则直接 git push）
HTTPS_PROXY=http://127.0.0.1:7897 HTTP_PROXY=http://127.0.0.1:7897 git push
```

注意：模型权重 / adapter / checkpoint / `__pycache__` 不入库（大文件 + 非交付物）。

## 3. 远程拉取 + 注册数据（容器内）

```bash
cd /workspace/mech-qwen-sft
git clone https://github.com/bdpn22rr9r-lang/mechqa-qwen-lora.git imports/mechqa-qwen-lora
python imports/mechqa-qwen-lora/scripts/build_mech_dataset_v1.py
```

脚本写入并注册：

```text
/workspace/mech-qwen-sft/datasets/processed/mech_sft_v1_80.json
/workspace/mech-qwen-sft/eval/mech_eval_v1_20.json
/workspace/mech-qwen-sft/configs/qwen25_7b_mech_lora_sft_v1_80.yaml
/workspace/mech-qwen-sft/third_party/LlamaFactory_MUSA/data/mech_sft_v1_80.json
```

## 4. 审阅数据（必须）

训练前人工审阅 `mech_sft_v1_80.json`，确认无标注错误、无安全隐患、类别配比符合预期。不合格样本淘汰，不猜测修补。

## 5. 单卡训练（稳定基线）

```bash
cd /workspace/mech-qwen-sft/third_party/LlamaFactory_MUSA

MUSA_LAUNCH_BLOCKING=1 MUSA_VISIBLE_DEVICES=0 \
  llamafactory-cli train /workspace/mech-qwen-sft/configs/qwen25_7b_mech_lora_sft_v1_80.yaml \
  2>&1 | tee /workspace/mech-qwen-sft/logs/mech_sft_v1_80.log
```

关键配置（必须）：`bf16: true` + `flash_attn: disabled` + `learning_rate: 5.0e-5`。另开终端 `watch -n 1 mthreads-gmi` 观察。

## 6. 推理验证

```bash
MUSA_VISIBLE_DEVICES=0 \
  llamafactory-cli chat \
  --model_name_or_path /workspace/mech-qwen-sft/models/Qwen2.5-7B-Instruct \
  --adapter_name_or_path /workspace/mech-qwen-sft/outputs/<本次输出目录> \
  --infer_dtype bfloat16 --flash_attn disabled \
  --template qwen
```

## 7. 8 卡训练（第二阶段，单卡稳定 + 数据质量确认后再用）

```bash
MUSA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
FORCE_TORCHRUN=1 NNODES=1 NPROC_PER_NODE=8 \
MASTER_ADDR=127.0.0.1 MASTER_PORT=29500 \
  llamafactory-cli train /workspace/mech-qwen-sft/configs/qwen25_7b_mech_lora_sft_8gpu.yaml \
  2>&1 | tee /workspace/mech-qwen-sft/logs/8gpu_lora_sft.log
```

## 8. 合并导出（部署前）

```bash
llamafactory-cli export /workspace/mech-qwen-sft/configs/export_qwen25_7b_mech_lora.yaml
# 输出 /workspace/mech-qwen-sft/outputs/qwen25-7b-mech-merged
```

---

## 训练前检查清单

- [ ] 远程容器 `mech-qwen-sft-official` 在运行，`torch.musa.is_available()==True`，`device_count==8`。
- [ ] 基础模型 `Qwen2.5-7B-Instruct` 完整（4 分片 + config + tokenizer）。
- [ ] 数据已 `git clone` + 脚本注册，自验 `validation=PASS`。
- [ ] 数据已人工审阅。
- [ ] 训练 YAML 含 `bf16: true` + `flash_attn: disabled`，输出目录独立不覆盖。
- [ ] 先小 batch / 少 step 试跑，确认 loss 下降 + `grad_norm` 有限 + 无 NaN。
- [ ] 训练用 `tee` 存日志，`tmux`/`nohup` 防断线。
- [ ] 大文件（模型/checkpoint/日志）在大容量盘，不放 `/home`。

## 推理前检查清单

- [ ] `--infer_dtype bfloat16`（与训练 dtype 对齐）。
- [ ] `--flash_attn disabled`（与训练一致）。
- [ ] 加载 adapter 前已知其权重无 NaN（训后扫描过）。
