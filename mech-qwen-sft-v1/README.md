# mech-qwen-sft-v1

Qwen2.5-7B-Instruct mechanical engineering LoRA SFT draft dataset.

## Contents

- `datasets/mech_sft_v1_80.json`: 80 training samples.
- `eval/mech_eval_v1_20.json`: 20 held-out evaluation samples.
- `configs/qwen25_7b_mech_lora_sft_v1_80.yaml`: verified single-MUSA-GPU training configuration.
- `scripts/build_mech_dataset_v1.py`: regenerates, validates, copies and registers the dataset inside `/workspace/mech-qwen-sft`.

Training categories:

| Category | Count |
|---|---:|
| Mechanical design review | 24 |
| Manufacturing process planning | 20 |
| Equipment fault diagnosis | 20 |
| Safety and insufficient-information handling | 8 |
| Evidence-grounded material properties | 8 |

## Remote Server

After uploading this directory to the GitHub repository, run inside the existing `mech-qwen-sft-official` container:

```bash
cd /workspace/mech-qwen-sft
git clone https://github.com/bdpn22rr9r-lang/mechqa-qwen-lora.git imports/mechqa-qwen-lora
python imports/mechqa-qwen-lora/scripts/build_mech_dataset_v1.py
```

The script writes and registers:

```text
/workspace/mech-qwen-sft/datasets/processed/mech_sft_v1_80.json
/workspace/mech-qwen-sft/eval/mech_eval_v1_20.json
/workspace/mech-qwen-sft/configs/qwen25_7b_mech_lora_sft_v1_80.yaml
/workspace/mech-qwen-sft/third_party/LlamaFactory_MUSA/data/mech_sft_v1_80.json
```

Start single-GPU training only after reviewing the draft data:

```bash
MUSA_LAUNCH_BLOCKING=1 MUSA_VISIBLE_DEVICES=0 llamafactory-cli train /workspace/mech-qwen-sft/configs/qwen25_7b_mech_lora_sft_v1_80.yaml 2>&1 | tee /workspace/mech-qwen-sft/logs/mech_sft_v1_80.log
```

## Review Requirement

This is a training-validation draft, not a production-certified engineering corpus. A mechanical engineer should review every sample before the dataset is used for product claims, safety decisions, or standards compliance.
