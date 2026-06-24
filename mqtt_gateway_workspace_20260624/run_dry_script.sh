#!/usr/bin/env bash
set -euo pipefail

# Dry-run launcher for a single migrated WXF MQTT child script.
#
# This has the same path behavior as run_live_script.sh, but it always forces
# dry_run mode. Use it before every new script is allowed to run live.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${ROOT_DIR}/wxf_run_logger.sh"

usage() {
  cat <<'EOF'
用法:
  cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
  ./run_dry_script.sh 子脚本相对路径 [子脚本参数...]

例子:
  ./run_dry_script.sh yolo/my_new_script.py
  ./run_dry_script.sh yolo/move_arm_by_json.py ../positions/pick_b_2.json

说明:
  这个脚本强制 dry_run，不会让机器人运动。
  新写的 MQTT 子脚本，必须先用这个检查，再用 run_live_script.sh 真机运行。
  每次运行会自动写日志到 run_logs/YYYYMMDD/。
  如果失败，运行 ./collect_debug_bundle.sh 打包日志给维护人员。
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  usage
  exit 0
fi

SCRIPT_REL="$1"
shift

if [[ "${SCRIPT_REL}" = /* ]]; then
  echo "请使用相对路径，不要使用绝对路径: ${SCRIPT_REL}" >&2
  exit 2
fi

if [[ "${SCRIPT_REL}" != *.py ]]; then
  echo "只允许启动 .py 子脚本: ${SCRIPT_REL}" >&2
  exit 2
fi

SCRIPT_PATH="${ROOT_DIR}/${SCRIPT_REL}"
if [[ ! -f "${SCRIPT_PATH}" ]]; then
  echo "子脚本不存在: ${SCRIPT_REL}" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
SCRIPT_FILE="$(basename "${SCRIPT_PATH}")"

case "${SCRIPT_DIR}/" in
  "${ROOT_DIR}/"*) ;;
  *)
    echo "子脚本路径逃出了 MQTT 工作区: ${SCRIPT_REL}" >&2
    exit 2
    ;;
esac

export G2_WXF_GATEWAY_MODE="dry_run"
export G2_WXF_GATEWAY_CONFIRM_PHYSICAL="0"
export G2_WXF_GATEWAY_PREFLIGHT="${G2_WXF_GATEWAY_PREFLIGHT:-require}"

wxf_log_init "${ROOT_DIR}" "dry_script" "${SCRIPT_REL}"

echo "# WXF MQTT dry-run child script"
echo "# workspace: ${ROOT_DIR}"
echo "# cwd: ${SCRIPT_DIR}"
echo "# script: ${SCRIPT_REL}"
echo "# mode=${G2_WXF_GATEWAY_MODE}, preflight=${G2_WXF_GATEWAY_PREFLIGHT}"
echo "# run log: ${WXF_LOG_FILE}"

wxf_run_logged "${SCRIPT_DIR}" python3 "${SCRIPT_FILE}" "$@"
