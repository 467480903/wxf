#!/usr/bin/env bash
set -euo pipefail

# Clean old WXF run logs. Default is dry-run; add --execute to delete.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_ROOT="${ROOT_DIR}/run_logs"
DAYS="${G2_WXF_LOG_RETENTION_DAYS:-30}"
KEEP_BUNDLES="${G2_WXF_KEEP_DEBUG_BUNDLES:-100}"
EXECUTE=0

if [[ "${1:-}" == "--execute" ]]; then
  EXECUTE=1
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<EOF
用法:
  ./cleanup_run_logs.sh          # 只预览，不删除
  ./cleanup_run_logs.sh --execute

默认保留:
  最近 ${DAYS} 天日志
  最新 ${KEEP_BUNDLES} 个 debug bundle

可通过环境变量覆盖:
  G2_WXF_LOG_RETENTION_DAYS=45
  G2_WXF_KEEP_DEBUG_BUNDLES=200
EOF
  exit 0
fi

mkdir -p "${LOG_ROOT}"
echo "# cleanup run logs"
echo "# log_root=${LOG_ROOT}"
echo "# retention_days=${DAYS}"
echo "# keep_debug_bundles=${KEEP_BUNDLES}"
echo "# mode=$([[ "${EXECUTE}" -eq 1 ]] && echo execute || echo dry-run)"
echo

echo "## old .log files"
if [[ "${EXECUTE}" -eq 1 ]]; then
  find "${LOG_ROOT}" -type f -name '*.log' -mtime "+${DAYS}" -print -delete
else
  find "${LOG_ROOT}" -type f -name '*.log' -mtime "+${DAYS}" -print
fi
echo

echo "## old debug bundle staging directories"
if [[ "${EXECUTE}" -eq 1 ]]; then
  find "${LOG_ROOT}" -maxdepth 1 -type d -name 'debug_bundle_*' -mtime "+${DAYS}" -print -exec rm -rf {} +
else
  find "${LOG_ROOT}" -maxdepth 1 -type d -name 'debug_bundle_*' -mtime "+${DAYS}" -print
fi
echo

echo "## old preflight raw directories"
if [[ "${EXECUTE}" -eq 1 ]]; then
  find "${LOG_ROOT}/preflight" -maxdepth 1 -type d -name 'preflight_live_*_raw' -mtime "+${DAYS}" -print -exec rm -rf {} + 2>/dev/null || true
else
  find "${LOG_ROOT}/preflight" -maxdepth 1 -type d -name 'preflight_live_*_raw' -mtime "+${DAYS}" -print 2>/dev/null || true
fi
echo

echo "## old debug bundles beyond keep count"
mapfile -t old_bundles < <(
  python3 - "${LOG_ROOT}" "${KEEP_BUNDLES}" <<'PY'
import sys
from pathlib import Path

log_root = Path(sys.argv[1])
keep = max(0, int(sys.argv[2]))
bundles = sorted(log_root.glob("debug_bundle_*.tar.gz"))
if keep:
    bundles = bundles[:-keep]
for item in bundles:
    print(item)
PY
)
for bundle in "${old_bundles[@]}"; do
  [[ -n "${bundle}" ]] || continue
  echo "${bundle}"
  [[ "${EXECUTE}" -eq 1 ]] && rm -f -- "${bundle}"
done
echo

echo "done"
