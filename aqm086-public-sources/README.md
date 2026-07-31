# AQM086 — AgenticQwen B 组 100K 公开数据来源归档

> **状态：`SOURCE_ARCHIVE_ONLY` / `training_allowed = false`**
> 本目录登记**公开数据来源**的元数据（commit、SHA256、大小、记录数、许可证）。
> 原始数据文件不作为 git blob 提交（大文件走 Release asset，见 [release-assets/RELEASE_ASSETS.md](release-assets/RELEASE_ASSETS.md)）。
> **AQM086 尚未就绪启动 B 组训练**：HotpotQA 为 HF derived（破例，待相关方确认），2Wiki/Omni-MATH/SynthAgent 许可证仍 UNCONFIRMED。

- experiment_id: `AQM-20260731-086`
- 仓库: `bdpn22rr9r-lang/agenticqwen-musa-reproduction`
- 分支: `codex/aqm086-public-sources`（**不改动 main**）
- tag / release: `AQM086-public-sources-r1`（tag 已打；Release 因 harness 安全策略拒绝自动创建，**需手动运行**）

---

## 1. 来源总览

| 来源 | 类型 | commit | 记录数 | 大小 | SHA256 | 数据集许可证 | 许可证状态 | 可训练 | 下载 |
|---|---|---|---|---|---|---|---|---|---|
| HotpotQA (train) | reasoning_initial | `3635853` | **90,447** ✓ | 536 MB(derived) | `3d72f9fc…`(derived) | CC-BY-SA-4.0 | CONFIRMED | **是**(HF derived¹) | OK(via HF) |
| 2WikiMultiHopQA | reasoning_initial | `13800e5` | 167454 (train) | 247 MB(zip) | `95df2bf5…` | NOASSERTION | **UNCONFIRMED** | 否 | OK |
| Omni-MATH | reasoning_initial | `23be225` | 4428 | 7.5 MB | `7c87be8e…` | NOASSERTION | **UNCONFIRMED** | 否 | OK |
| SynthAgent | agentic_method | `bae3603` | 0 (CODE_ONLY) | 954 KB(code) | `6e639bc6…`(code) | NOASSERTION | **UNCONFIRMED** | 否 | OK(code only) |
| 现有 bastion 37,022 | — | — | 37022 | — | `a0a1578e…` | (已登记) | — | (已登记) | 不重下 |

¹ **HotpotQA 破例说明**：官方 CMU 源（`curtis.ml.cmu.edu`）在本网络不可达、官方 GitHub 仓库无数据，经**用户明确授权破例规则 1**，从 HuggingFace `hotpotqa/hotpot_qa`（distractor/train parquet）取得等价数据，并用 `scripts/hotpotqa_parquet_to_json.py` 转回原始格式 derived json（90,447 行与官方一致）。derived sha256 `3d72f9fc…` **字节级 ≠ CMU 原始** `26650cf5…`（内容等价）。HF 破例合规性需相关方最终确认。

**许可证确认 + 已获取的来源样本 = 127,469**（HotpotQA 90,447 + bastion 37,022），按来源计数已达 100K。
⚠️ 但 HotpotQA 为 HF derived（破例）；2Wiki/Omni-MATH/SynthAgent 许可证仍 UNCONFIRMED，未计入。距"可直接用于训练"仍有合规待办。

---

## 2. 目录结构

```
aqm086-public-sources/
├── README.md
├── manifests/                         # 每来源 + 总清单
├── licenses/                          # 原始许可证全文 + 说明
├── source-code/                       # 各来源冻结 commit + 下载说明 + upstream/ 原始 README(.gitattributes)
├── scripts/                           # verify_sha256 / count_records / build_aqm086_manifest / hotpotqa_parquet_to_json
├── release-assets/RELEASE_ASSETS.md   # 大文件 asset 清单 + 上传/复验指令
└── logs/hotpotqa-download-blocked.log # CMU 源下载失败 + HF derived 后续
```

---

## 3. evaluation_only 清单（**禁止混入训练集**）

- TAU-2 数据、BFCL 数据
- HotpotQA **dev / test**（distractor/fullwiki validation、fullwiki test —— 未使用）
- 2WikiMultiHopQA **dev.json / test.json**（12,576 + 12,576）、`id_aliases.json`
- Omni-MATH 评测输出：`GPT_eval/examples/*.jsonl`、`Omni-Judge_eval/examples_infile/*.jsonl`
- SynthAgent `configs/webarena.jsonl`（WebArena 评测配置）
- 现有 A/B/C/D 评测结果、模型输出日志、checkpoint
- 任何 API key / token / 访问凭据 / 私有日志

---

## 4. 阻塞项与待人工补充

| 阻塞 | 原因 | 解锁动作 |
|---|---|---|
| HotpotQA 官方 CMU 源 | `curtis.ml.cmu.edu` 不可达 | **已用 HF derived 替代**（用户破例授权，90,447 条已取得）；若需 CMU 原始字节，仍需换网络 |
| 2Wiki 训练资格 | 数据包内无 LICENSE，UNCONFIRMED | 向作者/官方确认数据集许可证 |
| Omni-MATH 训练资格 | 仓库无 LICENSE，README 也无数据许可条款 | 同上；并确认 benchmark 题作训练的 intended-use 合规 |
| SynthAgent 数据 | 公开任务/轨迹仅在 HF（规则禁用），无非 HF 镜像 | 与作者确认是否有非 HF 官方分发 |
| GitHub Release | 自动创建被 harness 安全策略拒绝（凭据探索+未授权状态变更） | 提供有 `repo` 权限的 PAT 或本机 `gh auth login`，手动运行 RELEASE_ASSETS.md 命令 |
| bastion 37,022 | 工作站不可达 `/workspace/...` | 仅按任务给定字段登记（不重下、不上传） |

---

## 5. 复现与验证

```bash
# HotpotQA derived（破例 HF 来源）
python scripts/hotpotqa_parquet_to_json.py p1.parquet p2.parquet -o hotpot_train_v1.1.derived.json
# 校验
python scripts/verify_sha256.py <file> [--expected <sha256>] [--zip]
python scripts/count_records.py <file>
python scripts/build_aqm086_manifest.py     # 重算总 manifest 的可计数字段
```

---

## 6. 约束遵守声明

- ✓ 不调用 OpenAI / Azure / Anthropic 等外部模型 API
- ✓ 不生成伪造数据，不复制 37,022 冒充 100K
- ✓ 不下载 BFCL / TAU-2 作训练数据
- ✓ 不上传模型权重 / checkpoint / 私有日志 / API key / token
- ✓ 大文件不作为普通 git blob（仅本地 + 计划 Release asset）
- ✓ 每来源最多 2 次官方下载尝试（HotpotQA CMU 第 2 次失败后转 HF derived，已记日志）
- ✓ 保留原始许可证或其链接
- ✓ 原始文件未修改；HotpotQA parquet→json 转换另存为 derived，记录转换脚本与输入哈希
- ✓ 训练数据与评测数据分离（dev/test/eval 输出均 evaluation_only）
- ⚠ **破例**：HotpotQA 经用户授权从 HuggingFace 取得（规则 1 的例外），已在 manifest/README/logs 完整披露，待相关方确认合规
