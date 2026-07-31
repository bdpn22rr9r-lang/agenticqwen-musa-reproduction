#!/usr/bin/env bash
# Create the AQM086-public-sources-r1 GitHub Release and upload all 3 assets.
#
# AUTH (pick one):
#   1) Install GitHub CLI and log in:  winget install GitHub.cli && gh auth login
#   2) OR export a PAT with `repo` scope:  export GH_TOKEN=ghp_xxx
# This script uses `gh` only. It does NOT read the OS credential store.
#
# ASSETS: place the 3 files in $ASSET_DIR (default = directory of this script).
# Expected SHA256 is verified before upload (aborts on mismatch):
#   AQM086-2wiki-data_ids_april7.zip              95df2bf5...e5529eef
#   AQM086-omni-math-Omni-Math.jsonl              7c87be8e...32ef168
#   AQM086-hotpotqa-hotpot_train_v1.1.derived.json 3d72f9fc...577d5d76
set -euo pipefail

TAG=AQM086-public-sources-r1
BRANCH=codex/aqm086-public-sources
REPO=bdpn22rr9r-lang/agenticqwen-musa-reproduction
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSET_DIR="${ASSET_DIR:-$SCRIPT_DIR}"

ASSETS=(
  "AQM086-2wiki-data_ids_april7.zip"
  "AQM086-omni-math-Omni-Math.jsonl"
  "AQM086-hotpotqa-hotpot_train_v1.1.derived.json"
)

expected_sha() {
  case "$1" in
    AQM086-2wiki-data_ids_april7.zip)               echo 95df2bf56fdabe034e27aebc580e02264232203cf52552f9efe8a919e5529eef ;;
    AQM086-omni-math-Omni-Math.jsonl)               echo 7c87be8ee41ac7c7a597ef5a5500e84bd2b639a85a06db3da7f69bf9a32ef168 ;;
    AQM086-hotpotqa-hotpot_train_v1.1.derived.json) echo 3d72f9fcff621eb9ea59383e13608611d046568a8757951da853e6a6577d5d76 ;;
    *) echo "" ;;
  esac
}

command -v gh >/dev/null 2>&1 || { echo "ERROR: gh CLI not found. Install it and 'gh auth login', or set GH_TOKEN."; exit 1; }

echo "Asset dir: $ASSET_DIR"
# 1. preflight: presence + sha256
for a in "${ASSETS[@]}"; do
  f="$ASSET_DIR/$a"
  [ -f "$f" ] || { echo "MISSING: $f"; exit 1; }
  exp=$(expected_sha "$a")
  got=$(sha256sum "$f" | awk '{print $1}')
  if [ "$exp" != "$got" ]; then
    echo "SHA MISMATCH $a"; echo "  expected: $exp"; echo "  got:      $got"; exit 1
  fi
  echo "  OK  $a  ($got)"
done

# 2. create release if missing
if gh release view "$TAG" -R "$REPO" >/dev/null 2>&1; then
  echo "Release $TAG already exists; uploading assets."
else
  gh release create "$TAG" --target "$BRANCH" -R "$REPO" \
    --title "$TAG" \
    --notes "AQM086 public source archive (SOURCE_ARCHIVE_ONLY). Meta in aqm086-public-sources/manifests/. Assets: 2Wiki zip, Omni-MATH jsonl, HotpotQA HF-derived json."
fi

# 3. upload (overwrite if rerun)
for a in "${ASSETS[@]}"; do
  gh release upload "$TAG" "$ASSET_DIR/$a" -R "$REPO" --clobber
  echo "  uploaded $a"
done

echo "Done. Inspect:  gh release view $TAG -R $REPO"
