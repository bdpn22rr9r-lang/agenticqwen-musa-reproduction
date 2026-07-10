# 项目踩坑记录

> 本项目专属踩坑。多数已同时沉淀到全局 `00_Global/logs/PITFALL_LOG.md`（跨项目可复用）；此处保留项目上下文与远程具体路径。日志倒序（新→旧）。

---

## 2026-07-10 - 本机 git push GitHub 超时（不走系统代理）

症状：`git push` 报 `Failed to connect to github.com port 443 after 21064 ms`。

原因：本机系统代理 `127.0.0.1:7897` 已开，但 git 不读系统代理。

解决：`HTTPS_PROXY=http://127.0.0.1:7897 HTTP_PROXY=http://127.0.0.1:7897 git push`，或持久化 `git config --global http(s).proxy`。

预防：本机所有 git 网络操作带代理。详见全局 `PITFALL_LOG.md`。

## 2026-07-10 - MUSA Torch SDPA 反向传播产出全 NaN（核心坑）

症状：LoRA SFT 第一步 `grad_norm: nan`，后续 `loss:0.0`；adapter 392 张量全含 NaN；推理首 token 报概率 NaN。

原因：当前 Torch-MUSA 的 SDPA 反向数值异常。

解决：训练配置 `flash_attn: disabled`（vanilla attention）；一步诊断（`max_steps:1`）确认梯度有限 + 权重 `bad_tensor_count=0` 后再正式训。

预防：MUSA 训练/推理配置固定显式 `flash_attn: disabled`；训后先扫权重 NaN 再推理。详见全局 `PITFALL_LOG.md` / `COMPOUND_LOG.md`。

## 2026-07-10 - 训练 bf16 / 推理 fp16 不一致致采样 NaN

症状：关 SDPA 后训练正常，但推理首 token 仍概率 NaN；日志显示推理 `default dtype torch.float16`。

原因：fp16 动态范围小，合并 adapter 前向溢出；`bf16:false` 也不等于 FP32。

解决：推理 `--infer_dtype bfloat16`，与训练 dtype 对齐。

预防：训练 dtype == 推理 dtype，写进检查清单。

## 2026-07-10 - musify-text 缺 ahocorapy / 不处理 is_torch_cuda_available

症状：`musify-text` 报 `No module named 'ahocorapy'`；迁移后框架仍因 CUDA 不可用跳过 MUSA 分支。

原因：musify-text 依赖 ahocorapy 需手装；它只做文本替换，不处理逻辑判断函数。

解决：`pip install ahocorapy`；迁移后人工补丁 `is_torch_cuda_available → is_torch_musa_available`（只改 `LlamaFactory_MUSA` 副本）。

预防：迁移后 grep 残留 `cuda`/`is_torch_cuda_available`，区分文本 vs 逻辑。

## 2026-07-10 - musify-text -t 预演模式工具自身报错

症状：`musify-text -t` 报 `NameError: name 'sys' is not defined`。

解决：不修工具本体；改用「单文件临时副本 + `--inplace` + `diff`」预演。

预防：批量 `--inplace` 前永远先临时副本预演。

## 2026-07-10 - LlamaFactory_MUSA 缺 data/dataset_info.json

症状：注册数据集报 `FileNotFoundError: data/dataset_info.json`。

原因：v0.9.3 副本无默认 `dataset_info.json`。

解决：先 `find` 只读定位；确认缺失后创建最小 `data/dataset_info.json`，只注册本项目数据集。

预防：注册前先确认 `dataset_dir`（默认 `./data`）下有无该文件，不硬编码路径。

## 2026-07-10 - huggingface.co 远程不可达

症状：容器内下载 MechQA 报 `[Errno 101] Network is unreachable`。

解决：从作者 GitHub 取小样本；全量后续走可信通道。不装新软件、不改 Docker 网络。

预防：远程下载大数据前先测网络，备好离线/镜像回退。

## 2026-07-10 - MechQA 自动标注系统性噪声

症状：数值串行（取相邻材料值）、单位/性能类型错（抗拉强度当杨氏模量）、把相对提高量当绝对值、忽略温度/方向/应变率条件。

解决：每条候选人工核对实体/性能/数值/单位/条件/DOI，不合格直接淘汰；不随机抽样直接训。

预防：用任何自动标注数据集前先抽样人工审查 + 建固定评测集。详见全局 `PITFALL_LOG.md`。

## 2026-07-09 - 远程 /home 容量不足

症状：`/home` 用 96%，放大文件易撑爆。

解决：训练文件放 `/data`、`/datassd`、`/nhssd` 等大容量盘；项目目录也建在 `/home` 下但模型/checkpoint/日志指向大盘。

预防：登服务器先 `df -h`。

## 2026-07-09 - 宿主机 nvidia-smi 不存在

症状：`nvidia-smi: command not found`。

原因：摩尔线程 GPU 工具是 `mthreads-gmi`，不是 nvidia-smi。

解决：用 `mthreads-gmi` 查 GPU；进容器验证 `torch.musa.device_count()`。

预防：先确认 GPU 厂商再找对应工具。
