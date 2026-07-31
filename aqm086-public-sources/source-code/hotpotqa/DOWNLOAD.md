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
