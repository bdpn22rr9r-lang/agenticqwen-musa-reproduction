# AQM086 — AgenticQwen B 组 100K 公开数据来源归档

> **状态：`SOURCE_ARCHIVE_ONLY` / `training_allowed = false`**
> 本目录只登记**公开数据来源**的元数据（commit、SHA256、大小、记录数、许可证），
> **不包含任何原始数据文件**（大文件走 Release asset，见 [release-assets/RELEASE_ASSETS.md](release-assets/RELEASE_ASSETS.md)）。
> **AQM086 尚未达到 100K，B 组训练未启动，也不允许启动。**

- experiment_id: `AQM-20260731-086`
- 仓库: `bdpn22rr9r-lang/agenticqwen-musa-reproduction`
- 分支: `codex/aqm086-public-sources`（**不改动 main**）
- tag / release: `AQM086-public-sources-r1`（tag 已打；Release 因无 token **尚未创建**）

---

## 1. 来源总览

| 来源 | 类型 | commit | 记录数 | 大小 | SHA256 | 数据集许可证 | 许可证状态 | 可训练 | 下载 |
|---|---|---|---|---|---|---|---|---|---|
| HotpotQA (train) | reasoning_initial | `3635853` | ~90K (待核) | ~566 MB | `26650cf5…`¹ | CC-BY-SA-4.0 | CONFIRMED | 条件² | **BLOCKED** |
| 2WikiMultiHopQA | reasoning_initial | `13800e5` | 167454 (train) | 247 MB(zip) | `95df2bf5…` | NOASSERTION | **UNCONFIRMED** | 否 | OK |
| Omni-MATH | reasoning_initial | `23be225` | 4428 | 7.5 MB | `7c87be8e…` | NOASSERTION | **UNCONFIRMED** | 否 | OK |
| SynthAgent | agentic_method | `bae3603` | 0 (CODE_ONLY) | 954 KB(code) | `6e639bc6…`(code) | NOASSERTION | **UNCONFIRMED** | 否 | OK(code only) |
| 现有 bastion 37,022 | — | — | 37022 | — | `a0a1578e…` | (已登记) | — | (已登记) | 不重下 |

¹ HotpotQA 的 SHA256 来自任务规格，**因文件未下到尚未实测验证**。
² HotpotQA 数据集许可证 CC-BY-SA-4.0 允许训练，但**前提是先成功下载并校验 SHA256**；当前下载 BLOCKED，计为 0。

**当前可计入训练的公开样本 = 0**（bastion 的 37,022 是既有效据，单独登记，不计入本次新增）。距 100K 目标仍差 62,978。

---

## 2. 目录结构

```
aqm086-public-sources/
├── README.md                          # 本文件
├── manifests/                         # 每来源 + 总清单
│   ├── hotpotqa-train.manifest.json
│   ├── 2wikimultihopqa.manifest.json
│   ├── omni-math.manifest.json
│   ├── synthagent.manifest.json
│   └── AQM086-public-sources.manifest.json
├── licenses/                          # 原始许可证全文 + 说明
│   ├── HOTPOTQA_LICENSE.txt           # Apache-2.0(code) + CC-BY-SA-4.0(dataset)
│   ├── 2WIKIMULTIHOPQA_LICENSE.txt    # Apache-2.0(code); dataset UNCONFIRMED
│   ├── OMNI_MATH_LICENSE.txt          # 仓库无 LICENSE -> UNCONFIRMED
│   └── SYNTHAGENT_LICENSE.txt         # 仓库无 LICENSE -> UNCONFIRMED
├── source-code/                       # 各来源冻结 commit + 下载说明(不嵌入完整代码)
│   ├── hotpotqa/DOWNLOAD.md
│   ├── 2wikimultihop/DOWNLOAD.md
│   ├── omni-math/DOWNLOAD.md
│   └── synthagent/DOWNLOAD.md
├── scripts/                           # 校验/计数/汇总工具
│   ├── verify_sha256.py
│   ├── count_records.py
│   └── build_aqm086_manifest.py
├── release-assets/
│   └── RELEASE_ASSETS.md              # 大文件 asset 清单 + 上传/复验指令
└── logs/
    └── hotpotqa-download-blocked.log  # HotpotQA 下载失败日志
```

---

## 3. evaluation_only 清单（**禁止混入训练集**）

按 AQM086 第六节，以下内容明确标记 `evaluation_only`，**绝不可进入训练**：

- TAU-2 数据
- BFCL 数据
- HotpotQA **dev / test**（本次未下载，仅 train 被登记）
- 2WikiMultiHopQA **dev.json / test.json**（12,576 + 12,576 条）
- 2Wiki `id_aliases.json`（别名映射，非训练数据）
- Omni-MATH **评测输出**：`GPT_eval/examples/*.jsonl`、`Omni-Judge_eval/examples_infile/*.jsonl`
- SynthAgent `configs/webarena.jsonl`（WebArena 评测配置）
- 现有 A/B/C/D 评测结果、模型输出日志、checkpoint
- 任何 API key / token / 访问凭据 / 私有日志

---

## 4. 阻塞项与待人工补充

| 阻塞 | 原因 | 解锁动作 |
|---|---|---|
| HotpotQA 566MB 下载 | `curtis.ml.cmu.edu` 走代理 + 直连均连不上（2 次失败） | 从可达网络重下，校验 `26650cf5…`，再上 Release asset |
| 2Wiki 训练资格 | 数据包内无 LICENSE，数据集许可证 UNCONFIRMED | 向作者/官方确认数据集许可证后再计入训练 |
| Omni-MATH 训练资格 | 仓库无 LICENSE，README 也无数据许可条款 | 同上；并确认 benchmark 题作训练的 intended-use 合规 |
| SynthAgent 数据 | 公开任务/轨迹仅在 HF（规则禁用 HF），无非 HF 镜像 | 与作者确认是否有非 HF 官方分发；否则不计入 |
| GitHub Release | 本环境无 token / `gh` | 提供有 `repo` 权限的 PAT，或本机 `gh auth login` |
| bastion 37,022 | 工作站不可达 `/workspace/...` | 仅按任务给定字段登记（不重下、不上传） |

---

## 5. 复现与验证

```bash
# 校验任意文件 SHA256（含 zip 每个成员）
python scripts/verify_sha256.py <file> [--expected <sha256>] [--zip]
# 统计记录数（jsonl / json-array / zip）
python scripts/count_records.py <file>
# 从各来源 manifest 重新汇总总 manifest
python scripts/build_aqm086_manifest.py
```

验收记录见 [manifests/AQM086-public-sources.manifest.json](manifests/AQM086-public-sources.manifest.json) 的 `acceptance` 字段。

---

## 6. 约束遵守声明

- ✗ 不使用 Hugging Face 作堡垒机下载入口（SynthAgent 因此未取数据）
- ✗ 不调用 OpenAI / Azure / Anthropic 等外部模型 API
- ✗ 不生成伪造数据，不复制 37,022 冒充 100K
- ✗ 不下载 BFCL / TAU-2 作训练数据
- ✗ 不上传模型权重 / checkpoint / 私有日志 / API key / token
- ✓ 大文件不作为普通 git blob（仅本地 + 计划 Release asset）
- ✓ 每来源最多 2 次下载尝试（HotpotQA 第 2 次失败后 BLOCKED，保留日志）
- ✓ 保留原始许可证或其链接
- ✓ 原始文件未修改；本次未做 derived 转换
- ✓ 训练数据与评测数据分离（dev/test/eval 输出均 evaluation_only）
