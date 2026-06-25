#!/usr/bin/env bash
set -euo pipefail

# Fast live launcher for a single migrated WXF MQTT child script.
#
# Use this only for scripts inside /data/wxf/wxf/mqtt_gateway_workspace_20260624.
# The launcher changes into the child script's own directory before running it,
# so existing relative arguments such as ../positions/foo.json keep working.
#
# Compared with run_live_script.sh, this keeps the same live execution path but
# skips the expensive service snapshot and pre/post robot read-only snapshots by
# default. Failure diagnostics are still appended if the child script exits
# non-zero.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${ROOT_DIR}/wxf_run_logger.sh"

usage() {
  cat <<'EOF'
用法:
  cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
  ./run_fast_live_script.sh 子脚本相对路径 [子脚本参数...]

例子:
  ./run_fast_live_script.sh BOX_528_1/move-pick2.py
  ./run_fast_live_script.sh yolo/move_arm_by_json.py ../positions/pick_b_2.json
  ./run_fast_live_script.sh yolo/move_whole_body_by_json.py ../positions/pick_standby.json
  ./run_fast_live_script.sh Robot/move_ee_pose_close_2.py

说明:
  这个脚本默认就是真机 live 模式，会让机器人运动。
  只能跑新 MQTT 工作区里面的 .py 子脚本，不能用来跑原始目录脚本。
  这个 fast 版本默认跳过 service snapshot 和前后 robot readonly snapshot。
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

export G2_WXF_GATEWAY_MODE="${G2_WXF_GATEWAY_MODE:-live}"
export G2_WXF_GATEWAY_CONFIRM_PHYSICAL="${G2_WXF_GATEWAY_CONFIRM_PHYSICAL:-1}"
export G2_WXF_GATEWAY_PREFLIGHT="${G2_WXF_GATEWAY_PREFLIGHT:-require}"
export G2_WXF_ALLOW_ESTOP_PEDAL_FAULT="${G2_WXF_ALLOW_ESTOP_PEDAL_FAULT:-1}"
export G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S="${G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S:-45}"
export G2_WXF_SKIP_SERVICE_SNAPSHOT="${G2_WXF_SKIP_SERVICE_SNAPSHOT:-1}"
export G2_WXF_SKIP_RUN_SNAPSHOTS="${G2_WXF_SKIP_RUN_SNAPSHOTS:-1}"

wxf_log_init "${ROOT_DIR}" "fast_live_script" "${SCRIPT_REL}"

echo "# WXF MQTT fast live child script"
echo "# workspace: ${ROOT_DIR}"
echo "# cwd: ${SCRIPT_DIR}"
echo "# script: ${SCRIPT_REL}"
echo "# mode=${G2_WXF_GATEWAY_MODE}, preflight=${G2_WXF_GATEWAY_PREFLIGHT}, allow_estop_pedal_fault=${G2_WXF_ALLOW_ESTOP_PEDAL_FAULT}"
echo "# chassis no-progress guard: ${G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S}s"
echo "# skip_service_snapshot=${G2_WXF_SKIP_SERVICE_SNAPSHOT}, skip_run_snapshots=${G2_WXF_SKIP_RUN_SNAPSHOTS}"
echo "# run log: ${WXF_LOG_FILE}"

wxf_run_logged "${SCRIPT_DIR}" python3 "${SCRIPT_FILE}" "$@"
