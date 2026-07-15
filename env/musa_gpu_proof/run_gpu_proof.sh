#!/usr/bin/env bash
set -Eeuo pipefail

# Usage examples:
#   bash run_gpu_proof.sh
#   DURATION=120 GPU_LIST=0,1,2,3,4,5,6,7 bash run_gpu_proof.sh
#   DURATION=60 GPU_LIST=0 bash run_gpu_proof.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DURATION="${DURATION:-90}"
GPU_LIST="${GPU_LIST:-0,1,2,3,4,5,6,7}"
MONITOR_INTERVAL="${MONITOR_INTERVAL:-2}"

STAMP="$(date +%Y%m%d_%H%M%S)"
HOST="$(hostname -s 2>/dev/null || hostname)"
OUT_DIR="${SCRIPT_DIR}/proof_${HOST}_${STAMP}"
mkdir -p "${OUT_DIR}"

# Save all terminal output while still displaying it.
exec > >(tee -a "${OUT_DIR}/run.log") 2>&1

MONITOR_PID=""

cleanup() {
  if [[ -n "${MONITOR_PID}" ]] && kill -0 "${MONITOR_PID}" 2>/dev/null; then
    kill "${MONITOR_PID}" 2>/dev/null || true
    wait "${MONITOR_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "============================================================"
echo "MUSA GPU TRAINING PROOF"
echo "Start time : $(date --iso-8601=seconds 2>/dev/null || date)"
echo "Hostname   : $(hostname)"
echo "User       : ${USER:-unknown}"
echo "GPU list   : ${GPU_LIST}"
echo "Duration   : ${DURATION}s"
echo "Output dir : ${OUT_DIR}"
echo "============================================================"

{
  echo "### TIME"
  date --iso-8601=seconds 2>/dev/null || date
  echo
  echo "### HOST"
  hostname
  hostnamectl 2>/dev/null || true
  echo
  echo "### OS"
  uname -a
  cat /etc/os-release 2>/dev/null || true
  echo
  echo "### CPU AND MEMORY"
  lscpu 2>/dev/null || true
  free -h 2>/dev/null || true
  echo
  echo "### PYTHON"
  command -v python
  python --version
  echo
  echo "### PYTORCH / MUSA"
  python - <<'PY'
import json
import torch
info = {
    "torch_version": torch.__version__,
    "musa_available": bool(getattr(torch, "musa", None) and torch.musa.is_available()),
    "musa_device_count": int(torch.musa.device_count()) if getattr(torch, "musa", None) else 0,
}
try:
    import torch_musa
    info["torch_musa_version"] = getattr(torch_musa, "__version__", "unknown")
except Exception as exc:
    info["torch_musa_import"] = repr(exc)
print(json.dumps(info, ensure_ascii=False, indent=2))
PY
} > "${OUT_DIR}/environment.txt" 2>&1

echo
echo "---- Environment summary ----"
cat "${OUT_DIR}/environment.txt"

echo
echo "---- mthreads-gmi before training ----"
if command -v mthreads-gmi >/dev/null 2>&1; then
  mthreads-gmi | tee "${OUT_DIR}/mthreads_gmi_before.txt"
else
  echo "WARNING: mthreads-gmi not found." | tee "${OUT_DIR}/mthreads_gmi_before.txt"
fi

echo
echo "---- musaInfo ----"
if command -v musaInfo >/dev/null 2>&1; then
  musaInfo > "${OUT_DIR}/musaInfo.txt" 2>&1 || true
  head -n 120 "${OUT_DIR}/musaInfo.txt" || true
else
  echo "WARNING: musaInfo not found." | tee "${OUT_DIR}/musaInfo.txt"
fi

echo
echo "---- Starting GPU monitor ----"
(
  while true; do
    {
      echo
      echo "===== $(date --iso-8601=seconds 2>/dev/null || date) ====="
      mthreads-gmi 2>&1 || true
    } >> "${OUT_DIR}/gpu_monitor.log"
    sleep "${MONITOR_INTERVAL}"
  done
) &
MONITOR_PID=$!

echo
echo "---- Starting real training workload ----"
export MUSA_VISIBLE_DEVICES="${GPU_LIST}"
python "${SCRIPT_DIR}/musa_tiny_train.py" \
  --duration "${DURATION}" \
  --output-dir "${OUT_DIR}"

cleanup
MONITOR_PID=""

echo
echo "---- mthreads-gmi after training ----"
if command -v mthreads-gmi >/dev/null 2>&1; then
  mthreads-gmi | tee "${OUT_DIR}/mthreads_gmi_after.txt"
fi

echo
echo "---- Creating evidence checksums ----"
(
  cd "${OUT_DIR}"
  sha256sum ./* 2>/dev/null | grep -v 'SHA256SUMS.txt' > SHA256SUMS.txt || true
)

ARCHIVE="${OUT_DIR}.tar.gz"
tar -czf "${ARCHIVE}" -C "$(dirname "${OUT_DIR}")" "$(basename "${OUT_DIR}")"

echo
echo "============================================================"
echo "PROOF PACKAGE COMPLETED"
echo "Result directory: ${OUT_DIR}"
echo "Archive         : ${ARCHIVE}"
echo
echo "Key evidence:"
echo "  ${OUT_DIR}/run.log"
echo "  ${OUT_DIR}/environment.txt"
echo "  ${OUT_DIR}/mthreads_gmi_before.txt"
echo "  ${OUT_DIR}/gpu_monitor.log"
echo "  ${OUT_DIR}/training_summary.json"
echo "  ${OUT_DIR}/training_summary.csv"
echo "  ${OUT_DIR}/gpu_*.log"
echo "  ${OUT_DIR}/SHA256SUMS.txt"
echo "============================================================"
