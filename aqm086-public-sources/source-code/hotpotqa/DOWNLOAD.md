# HotpotQA — source code & data acquisition

## Code repository (frozen)
- URL: https://github.com/hotpotqa/hotpot
- Commit: `3635853403a8735609ee997664e1528f4480762a`
- Code license: Apache-2.0 (Copyright 2018 Zhilin Yang, Peng Qi, Saizheng Zhang) → see [../../licenses/HOTPOTQA_LICENSE.txt](../../licenses/HOTPOTQA_LICENSE.txt)
- Codeload zip sha256 (this commit): `b8cfef6df3af609bbd14bc3c684acae96a764a925687e1861384b230f54bf1da` (24847 B)

```bash
git clone https://github.com/hotpotqa/hotpot.git
cd hotpot && git checkout 3635853403a8735609ee997664e1528f4480762a
```

## Dataset (TRAIN ONLY)
- File: `hotpot_train_v1.1.json`
- URL: https://curtis.ml.cmu.edu/datasets/hotpot/hotpot_train_v1.1.json
- Dataset license: **CC-BY-SA-4.0**
- Expected sha256: `26650cf50234ef5fb2e664ed70bbecdfd87815e6bffc257e068efea5cf7cd316`
- Size: ~566 MB · records: ~90K
- **STATUS: BLOCKED** in this run — `curtis.ml.cmu.edu` unreachable (proxy + direct, 2 attempts). See [../../logs/hotpotqa-download-blocked.log](../../logs/hotpotqa-download-blocked.log)
- Do **NOT** download `hotpot_dev_distractor.json` / test (evaluation_only).

## Acquisition (once network is reachable)
```bash
curl -L -o hotpot_train_v1.1.json https://curtis.ml.cmu.edu/datasets/hotpot/hotpot_train_v1.1.json
python ../../scripts/verify_sha256.py hotpot_train_v1.1.json \
  --expected 26650cf50234ef5fb2e664ed70bbecdfd87815e6bffc257e068efea5cf7cd316
python ../../scripts/count_records.py hotpot_train_v1.1.json   # json-array -> record count
```

## ACTUAL acquisition used (HF-derived, user-authorized exception to rule 1)

The official CMU host was unreachable, so **equivalent** data was obtained from
HuggingFace (explicitly authorized by the user, 2026-07-31):

- Dataset: https://huggingface.co/datasets/hotpotqa/hotpot_qa  (commit `1908d6af`)
- Split: `distractor/train` (2 parquet shards)
- Input shards + sha256:
  - `distractor/train-00000-of-00002.parquet` — 165624177 B — `76d3bb3048a7cc73c1958107c0c5872a00d7e7d00c105b81e92f6769e7822e68`
  - `distractor/train-00001-of-00002.parquet` — 166162479 B — `713661628434fbb19fff7392e2e321e4ed107e3c7c7784d0690946e5f722763f`
- Conversion to original json schema:
  ```bash
  python ../../scripts/hotpotqa_parquet_to_json.py \
    train-00000-of-00002.parquet train-00001-of-00002.parquet \
    -o hotpot_train_v1.1.derived.json
  ```
- Derived json: **561873108 B**, **90,447 rows**, sha256 `3d72f9fcff621eb9ea59383e13608611d046568a8757951da853e6a6577d5d76`
  — content-equivalent to CMU (rows match) but **NOT byte-identical** to the official `26650cf5…`.
