#!/usr/bin/env bash
set -euo pipefail

# One-command live launcher for the migrated WXF MQTT workspace.
#
# This script intentionally hides the long environment-variable list from
#现场 operators.  The underlying Python scripts still go through MQTT/Gateway;
# they do not import/release GDK themselves.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${ROOT_DIR}/wxf_run_logger.sh"

usage() {
  cat <<'EOF'
用法:
  cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
  ./run_live_task.sh pick_b

可选任务:
  pick_b      -> yolo/task_all_pick_b.py
  place_b     -> yolo/task_all_place_b.py
  all         -> yolo/task_all.py
  pull_car    -> yolo/task_all_pull_car.py

说明:
  这个脚本默认就是真机 live 模式，会让机器人运动。
  只在现场确认安全、机器人离开充电、运动区域清空后运行。
  每次运行会自动写日志到 run_logs/YYYYMMDD/。
  如果失败，运行 ./collect_debug_bundle.sh 打包日志给维护人员。

EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -ne 1 ]]; then
  usage
  exit 0
fi

case "$1" in
  pick_b|task_all_pick_b)
    TASK_SCRIPT="task_all_pick_b.py"
    TASK_LABEL="pick_b"
    ;;
  place_b|task_all_place_b)
    TASK_SCRIPT="task_all_place_b.py"
    TASK_LABEL="place_b"
    ;;
  all|task_all)
    TASK_SCRIPT="task_all.py"
    TASK_LABEL="all"
    ;;
  pull_car|task_all_pull_car)
    TASK_SCRIPT="task_all_pull_car.py"
    TASK_LABEL="pull_car"
    ;;
  *)
    echo "未知任务: $1" >&2
    usage >&2
    exit 2
    ;;
esac

# Keep only the parameters that are necessary for live execution or clearly
# useful at this site. Runtime tuning values stay inside mqtt_common.py/Gateway
# defaults so operators do not need to type or understand them.
export G2_WXF_GATEWAY_MODE="${G2_WXF_GATEWAY_MODE:-live}"
export G2_WXF_GATEWAY_CONFIRM_PHYSICAL="${G2_WXF_GATEWAY_CONFIRM_PHYSICAL:-1}"
export G2_WXF_GATEWAY_PREFLIGHT="${G2_WXF_GATEWAY_PREFLIGHT:-require}"

# Current现场 has emergency_stop_pedal_fault_state=1 but the actual pedal state
# was separately confirmed. This flag only acknowledges that known fault bit;
# it does not clear emergency stop or change controller safety logic.
export G2_WXF_ALLOW_ESTOP_PEDAL_FAULT="${G2_WXF_ALLOW_ESTOP_PEDAL_FAULT:-1}"

# The only chassis runtime guard exposed here: if PNC keeps RUNNING but the
# robot makes no SLAM/odom progress for this many seconds, Gateway cancels the
# current navigation task and reports failure. This is a stuck-protection value,
# not a fixed wait.
export G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S="${G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S:-45}"

wxf_log_init "${ROOT_DIR}" "live_task" "${TASK_LABEL}"

echo "# WXF MQTT live task: ${TASK_LABEL}"
echo "# workspace: ${ROOT_DIR}"
echo "# script: yolo/${TASK_SCRIPT}"
echo "# mode=${G2_WXF_GATEWAY_MODE}, preflight=${G2_WXF_GATEWAY_PREFLIGHT}, allow_estop_pedal_fault=${G2_WXF_ALLOW_ESTOP_PEDAL_FAULT}"
echo "# chassis no-progress guard: ${G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S}s"
echo "# run log: ${WXF_LOG_FILE}"

wxf_run_logged "${ROOT_DIR}/yolo" python3 "${TASK_SCRIPT}" --execute
