# 2WikiMultiHopQA — source code & data acquisition

## Code repository (frozen)
- URL: https://github.com/Alab-NII/2wikimultihop
- Commit: `13800e5be57df1b4040b9b1588c6c811779e69e9`
- Code license: Apache-2.0 (Copyright 2020 Xanh Ho) → see [../../licenses/2WIKIMULTIHOPQA_LICENSE.txt](../../licenses/2WIKIMULTIHOPQA_LICENSE.txt)
- Codeload zip sha256 (this commit): `2f27eb30af7c0989fe3c21e5cb0a23c7e22164a507b9947928b78dc140515b7b` (396096 B)

```bash
git clone https://github.com/Alab-NII/2wikimultihop.git
cd 2wikimultihop && git checkout 13800e5be57df1b4040b9b1588c6c811779e69e9
```

## Dataset archive
- File: `data_ids_april7.zip`
- URL: https://www.dropbox.com/s/ms2m13252h6xubs/data_ids_april7.zip?dl=1
- Archive sha256: `95df2bf56fdabe034e27aebc580e02264232203cf52552f9efe8a919e5529eef` (258968175 B)
- Integrity: `testzip` OK, **no path traversal**, 4 members
- Extracted:
  - `train.json` — 167454 records (train)
  - `dev.json` — 12576 records (**evaluation_only**)
  - `test.json` — 12576 records (**evaluation_only**)
  - `id_aliases.json` — JSONL alias map (**evaluation_only**)
- Dataset license: **UNCONFIRMED** (no license file inside archive) → **NOT training-eligible**

## Verify
```bash
python ../../scripts/verify_sha256.py data_ids_april7.zip --zip
python ../../scripts/count_records.py data_ids_april7.zip
```
