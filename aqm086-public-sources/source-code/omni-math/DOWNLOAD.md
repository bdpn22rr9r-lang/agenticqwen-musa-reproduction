# Omni-MATH — source code & data acquisition

## Code repository (frozen)
- URL: https://github.com/KbsdJames/Omni-MATH
- Commit: `23be225c8e268df51990f6c5c1448f34d3b56911`
- License: **NONE** in repository (no LICENSE/COPYING/NOTICE; README states no data terms) → UNCONFIRMED → see [../../licenses/OMNI_MATH_LICENSE.txt](../../licenses/OMNI_MATH_LICENSE.txt)
- Codeload zip sha256 (this commit): `da9033f3a6e344286ab2e6acf7b04309108ddbaa74d881da3ab514490415b0f6` (13359790 B)

```bash
git clone https://github.com/KbsdJames/Omni-MATH.git
cd Omni-MATH && git checkout 23be225c8e268df51990f6c5c1448f34d3b56911
```

## Data file
- File: `Omni-Math.jsonl`
- sha256: `7c87be8ee41ac7c7a597ef5a5500e84bd2b639a85a06db3da7f69bf9a32ef168`
- size: 7504961 B · lines/records: **4428** (matches README "4428 competition-level problems" → confirmed problem set, not an evaluation-output file)
- License: **UNCONFIRMED** → **NOT training-eligible**

### evaluation_only (model evaluation outputs — DO NOT train on)
- `GPT_eval/examples/meta_llama_3-1_70b_instruct_gpteval.jsonl`
- `GPT_eval/examples/qwen_2_5_MATH_72b_instruct_gpteval.jsonl`
- `Omni-Judge_eval/examples_infile/meta_llama_3-1_70b_infile.jsonl`
- `Omni-Judge_eval/examples_infile/qwen_2_5_MATH_72b_instruct_infile.jsonl`

## Verify
```bash
python ../../scripts/verify_sha256.py Omni-Math.jsonl \
  --expected 7c87be8ee41ac7c7a597ef5a5500e84bd2b639a85a06db3da7f69bf9a32ef168
python ../../scripts/count_records.py Omni-Math.jsonl
```

> Author also publishes on Hugging Face (KbsdJames/Omni-MATH); **not used** per AQM086 rule 1 (no HF as source).
