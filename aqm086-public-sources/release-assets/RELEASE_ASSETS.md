# AQM086 — Release Assets

Release / tag: **`AQM086-public-sources-r1`** on branch **`codex/aqm086-public-sources`**

## Status: NOT_CREATED (auto-creation blocked by environment policy)

The local credential store DOES contain a usable `github.com` token, and the raw
data files exist in a local temp dir (`%TEMP%/aqm086_dl/`). However, automatic
Release creation was **blocked by the agent harness's security policy** —
extracting a PAT from the credential store and creating an external resource is
treated as credential use + unauthorized persistent state change without the
user's explicit authorization. (This is a safety guardrail, not bypassed.)

The raw data files are **intentionally NOT committed as git blobs** (AQM086
rule 6: large files must use Release asset or Git LFS).

→ **A human must run the commands below** (preferred: install `gh` and
`gh auth login`, or use the REST API with your own PAT). HotpotQA asset is
additionally blocked on download (source host unreachable from this network).

## Planned assets

| asset | size (B) | sha256 | local source | status |
|---|---|---|---|---|
| `AQM086-hotpotqa-hotpot_train_v1.1.json` | ~566 MB | `26650cf50234ef5fb2e664ed70bbecdfd87815e6bffc257e068efea5cf7cd316` (expected, **unverified**) | not downloaded | **BLOCKED** |
| `AQM086-2wiki-data_ids_april7.zip` | 258968175 | `95df2bf56fdabe034e27aebc580e02264232203cf52552f9efe8a919e5529eef` | `%TEMP%/aqm086_dl/2wiki_data.zip` | READY |
| `AQM086-omni-math-Omni-Math.jsonl` | 7504961 | `7c87be8ee41ac7c7a597ef5a5500e84bd2b639a85a06db3da7f69bf9a32ef168` | `%TEMP%/aqm086_dl/omnimath_extracted/.../Omni-Math.jsonl` | READY |

> HotpotQA asset is blocked on download (source host unreachable); even after a
> token is provided it cannot be uploaded until the file is obtained & verified.

## Upload (once a token is available)

Choose one:

**A) `gh` CLI**
```bash
# install gh, then:
gh auth login
# rename local files to the asset names above, then:
gh release create AQM086-public-sources-r1 \
  --target codex/aqm086-public-sources \
  --title "AQM086-public-sources-r1" \
  --notes "Public source archive for AQM086 (SOURCE_ARCHIVE_ONLY). See manifests/." \
  AQM086-2wiki-data_ids_april7.zip AQM086-omni-math-Omni-Math.jsonl
# add HotpotQA later, after its download is unblocked:
# gh release upload AQM086-public-sources-r1 AQM086-hotpotqa-hotpot_train_v1.1.json
```

**B) REST API + PAT** (needs a token with `repo` scope)
```bash
export GH_TOKEN=<your_PAT>
# 1. create release on the branch/tag
# 2. upload each asset to https://uploads.github.com/repos/<owner>/<repo>/releases/<id>/assets?name=<asset>
```

## Post-upload verification (AQM086 §8.10–11)
```bash
gh release download AQM086-public-sources-r1 --dir ./redownloaded
python ../scripts/verify_sha256.py ./redownloaded/AQM086-2wiki-data_ids_april7.zip --zip
python ../scripts/verify_sha256.py ./redownloaded/AQM086-omni-math-Omni-Math.jsonl \
  --expected 7c87be8ee41ac7c7a597ef5a5500e84bd2b639a85a06db3da7f69bf9a32ef168
# hashes must match the table above
```

After a successful download + verify, update:
- `manifests/hotpotqa-train.manifest.json` (`download_status`, `sha256_status`, real `byte_size`/`record_count`)
- `manifests/AQM086-public-sources.manifest.json` (`release.status`, `acceptance.release_asset_*`)
