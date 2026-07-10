# 开发记录

> 本记录从上游训练项目（`Codex_LongTerm_Workbench/projects/2026-07-09_model-training`）的计划书提炼整理，是本项目「为什么这么做」的依据。日志倒序（新→旧）。

---

## 2026-07-10 - Workspace 文档体系建立 + 数据仓库规范完善

背景：用户要求把 mechqa-qwen-lora 整理进 Workspace 长期工作台和记忆库，并根据上游训练计划书完善本项目规范文档。

改动：
- 在 Workspace `00_Global/` 增强 WORKBENCH / COMPOUND_LOG / PITFALL_LOG / GLOBAL_SOP（用本项目真实经验充实）。
- 本项目根目录补齐 7 件套文档（README/REQUIREMENTS/TECH_STACK/DEV_LOG/PITFALL_LOG/SOP/RETROSPECTIVE）。
- 沉淀全局经验：MUSA 训练稳定基线、SDPA NaN、dtype 对齐、musify 迁移、MechQA 边界、git 代理。

决策：全局文档沿用 Workspace 既有的「英文文件名 + 中文内容」约定，不推倒重来；项目文档平铺根目录，与 `nxopen-auto-dimension` 一致。

验证：文档落盘；待用户确认是否 commit/push。

后续：把本项目文档纳入版本库；第二阶段继续在此追加。

## 2026-07-10 - 本地数据交付 v1 + GitHub 上传

背景：链路验证通过后，需把审校数据、配置、脚本打包成交付物，并上传 GitHub 供远程复现。

改动：
- 生成独立交付包 `mech-qwen-sft-v1/`：80 训练 + 20 评测 + 单卡配置 + 远程脚本 + README。
- 自验：`train=80 eval=20`，5 类配比正确，`duplicate=0`，`train/eval overlap=0`，`validation=PASS`。
- ZIP：`mech-qwen-sft-v1.zip`，SHA256 `FDC4B15CECA5AAF93ACD723188A2526B56A7919CC7BEFAC72AFD1A404EA6E433`。
- 上传 GitHub `bdpn22rr9r-lang/mechqa-qwen-lora`（首次 commit `3f3e51f`）。

决策：文件夹仅 88K，无大文件，直接走文件夹方式，不用压缩包。

验证：`git push -u origin main` 成功（本机走代理 `127.0.0.1:7897`）。

后续：远程 `git clone` + 跑脚本复现注册。

## 2026-07-10 - MechQA 评估与首批 80 条数据策略

背景：考虑用 MechQA 作为首批工业 SFT 数据来源。

结论（关键）：
- MechQA ≈20 万英文 QA，自动生成自论文，只覆盖 5 类材料力学性能（抗拉/屈服/断裂强度、杨氏模量、延性），是带上下文的抽取式 QA，**不覆盖**设计审查/工艺/故障诊断/装配/防松等核心工业任务。人工 F1≈86%（非零噪声）。
- **不从 MechQA 随机抽样直接训练**。首批 80 条里 MechQA 类只占 8 条，须人工核验 + 中文重写 + 保留文献上下文/适用条件；禁止把带工艺/温度/方向条件的实验值改写成无条件常数。
- 抽查发现系统性标注错误：DX54D 抗拉强度取相邻材料值；7075 杨氏模量误取抗拉强度 `572 MPa`（实际 `71.7 GPa`）；PU-C6 取了 PU-Pr 的值；把「性能相对提高量」当绝对值。
- MechQA 全量更适合独立材料性能抽取任务或 RAG 知识库。论文 CC BY 4.0、代码 GPL-3.0，商业使用前须单独确认许可。

决策：80 条配比 = 设计审查 24 / 工艺 20 / 故障诊断 20 / 安全边界 8 / 材料证据 8；另建 20 条评测集不参与训练。

验证：GitHub 官方示例数据 train_sample=18000、val_sample=2100，JSONL 结构。

后续：全量 MechQA 通过可信通道导入；每条候选人工核对实体/性能/数值/单位/条件/DOI。

## 2026-07-10 - huggingface.co 网络不可达，回退 GitHub

背景：容器内下载 MechQA 失败。

现象：`huggingface-cli download` / `hf download` 报 `[Errno 101] Network is unreachable`，访问 `huggingface.co:443` 失败。

决策：不装新软件、不改 Docker 网络、不用未确认镜像站；从作者 GitHub `https://github.com/mz-516/MechQA.git` 取代码及小样本，全量后续再导入。

## 2026-07-10 - 3-step 稳定冒烟训练 + 推理验证通过（第一阶段收尾）

背景：定位并解决 NaN 后，用稳定配置完整验证链路。

训练：`bf16 + flash_attn:disabled + lr 5e-5`，3 step：

```text
step1 loss=2.2123 grad_norm=1.839   step2 loss=1.9950 grad_norm=1.404   step3 loss=1.6004 grad_norm=1.070
```

loss 持续下降，梯度有限，无 NaN。adapter 权重扫描 `bad_tensor_count=0`。

推理：`--infer_dtype bfloat16 --flash_attn disabled` 加载合并，对未见问题（周期载荷螺栓松动）生成完整原因/排查/改进，无概率 NaN。

结论：模型下载→数据注册→LoRA 训练→权重保存→推理链路全部跑通。但 3 条样本不足以证明领域能力提升；回答主要体现基础模型能力，且存在工业质量边界（防松方案泛化、预紧力检测粗等）。

## 2026-07-10 - dtype 对齐：训练 bf16 / 推理 fp16 不一致致采样 NaN

背景：关闭 SDPA 后训练梯度恢复，但 eager adapter 推理第一个 token 仍报概率 NaN。

定位：日志显示训练 `compute dtype: torch.bfloat16`，推理却 `default dtype torch.float16`。fp16 动态范围小于 bf16，合并 adapter 后前向溢出。（`bf16:false` 也不等于 FP32，实际仍 fp16。）

解决：推理显式 `--infer_dtype bfloat16`，保留 `--flash_attn disabled`。验证通过。

沉淀：训练 dtype 必须与推理 dtype 对齐 → 全局 `COMPOUND_LOG.md` / `PITFALL_LOG.md`。

## 2026-07-10 - SDPA 一步诊断：关闭 flash_attn 恢复有限梯度（NaN 根因）

背景：安全版（降 lr + 关 bf16）仍全 NaN；保存的 adapter 392 个张量全部含 NaN，确认训练产物损坏。

诊断配置：`bf16:true + flash_attn:disabled + max_steps:1`，独立输出目录。结果 `loss=2.2123 grad_norm=1.839`（有限），权重 `bad_tensor_count=0`。

结论：**Torch SDPA 的 MUSA 反向计算是首要故障源**。后续训练/推理必须显式 `flash_attn: disabled`。

沉淀：→ 全局 `COMPOUND_LOG.md`（MUSA 稳定基线）、`PITFALL_LOG.md`（SDPA NaN）。

## 2026-07-09 - 安全版 LoRA 冒烟训练仍 NaN

背景：基础模型单独推理正常（未复现 NaN），判断问题在 3 条样本训出的 LoRA adapter。

改动：建 `qwen25_7b_mech_lora_sft_safe.yaml`——lr 从 `2.0e-4` 降到 `5.0e-5`，`bf16:false`，独立输出目录。

结果：训练完成，但日志仍 `grad_norm: nan`、后两步 `loss:0.0`；推理首 token 报概率 NaN；adapter 392 张量全含 NaN。

结论：降 lr + 关 bf16 没解决，需进一步定位 attention 实现。不扩大数据、不启 8 卡。

## 2026-07-09 - 单卡 LoRA 冒烟：链路通但 grad_norm nan

背景：环境就绪，首次端到端冒烟。

结果：3 样本 3 step，`train_loss=0.7511`，训练「完成」。但日志 `grad_norm: nan`。adapter 可加载合并，推理首 token 报 `RuntimeError: probability tensor contains inf, nan or element < 0`。

决策：因仅验证链路，`grad_norm: nan` 暂不作冒烟失败依据，但标记为必须解决的数值风险。

## 2026-07-09 - Llama-Factory MUSA 迁移（musify-text + 人工补丁）

背景：官方 `musify.sh` 在本机镜像不存在，需用底层 `musify-text` 手动迁移。

过程：
1. 官方 `musify-text` 缺依赖 → `pip install ahocorapy`（先在 `--rm` 临时容器验证，再装进长期容器 `mech-qwen-sft-official`）。
2. `musify-text -t` 预演模式有 `NameError: sys` 工具 bug → 改用「单文件临时副本 + `--inplace` + `diff`」预演。
3. 复制 `LlamaFactory_MUSA` 副本，批量 `musify-text --inplace`（`cuda→musa 12 处, nv→mt 16 处`），不动原版。
4. 验证发现 musify 不处理 `is_torch_cuda_available` 逻辑判断 → 人工补丁为 `is_torch_musa_available`（当前环境 cuda 不可用/musa 可用，transformers.utils 两者都提供）。
5. `pip install -e .` → `Successfully installed llamafactory-0.9.3`，`llamafactory-cli version` 正常，`get_current_device()` 返回 `musa:0`。

沉淀：迁移要点 → 全局 `COMPOUND_LOG.md`。

## 2026-07-09 - 环境搭建：容器 / 镜像 / 模型 / 数据注册

- 硬件确认：8×MTT S5000，单卡 80G，驱动 `3.3.5-server`，Docker 24.0.9。
- 镜像选择：候选中 `10.200.53.208/ci/nanhu-computing-framework:v2.1.6-rc1`（39.6G）验证 torch 2.7.1 + torch_musa + 8 卡可用，作第一阶段默认镜像。后改用官方 `musa-train` 镜像建长期容器 `mech-qwen-sft-official`（torch 2.5.0）。
- 容器保护：保留原 `mech-qwen-sft` 容器不动；所有环境修改只在新容器内做。
- 模型：`modelscope download Qwen/Qwen2.5-7B-Instruct` → 15G，4 分片完整。
- 数据注册：v0.9.3 副本缺 `data/dataset_info.json` → 创建最小注册文件，只注册 `mech_sft_demo`（`file_name` + `columns` 映射）。

## 2026-07-09 - 项目目录初始化

- 宿主机 `/home/mccxadmin/projects/mech-qwen-sft`，容器内 `/workspace/mech-qwen-sft`。
- 建标准子目录：`models / datasets/{raw,processed} / configs / outputs / logs / scripts / eval / docs`。
- 统一变量：`PROJECT_ROOT` / `CONTAINER_ROOT`。

---

## 8 卡训练与导出配置（第二阶段备用，已验证单卡后再用）

**8 卡 LoRA SFT**：

```bash
cd /workspace/mech-qwen-sft/third_party/LlamaFactory_MUSA
MUSA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
FORCE_TORCHRUN=1 NNODES=1 NPROC_PER_NODE=8 \
MASTER_ADDR=127.0.0.1 MASTER_PORT=29500 \
llamafactory-cli train /workspace/mech-qwen-sft/configs/qwen25_7b_mech_lora_sft_8gpu.yaml \
  2>&1 | tee /workspace/mech-qwen-sft/logs/8gpu_lora_sft.log
```

**合并导出**：

```bash
llamafactory-cli export /workspace/mech-qwen-sft/configs/export_qwen25_7b_mech_lora.yaml
# export_dir: /workspace/mech-qwen-sft/outputs/qwen25-7b-mech-merged, export_device: cpu
```

> 8 卡配置务必保留 `bf16: true` + `flash_attn: disabled`。
