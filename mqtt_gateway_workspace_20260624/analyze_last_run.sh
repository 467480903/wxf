#!/usr/bin/env bash
set -euo pipefail

# Classify the latest WXF MQTT run log without rerunning the failed task.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${1:-}"

if [[ -z "${LOG_FILE}" ]]; then
  LOG_FILE="$(
    find "${ROOT_DIR}/run_logs" \
      \( -path "${ROOT_DIR}/run_logs/debug_bundle_*" -o -path "${ROOT_DIR}/run_logs/preflight" \) -prune \
      -o -type f -name '*.log' -print 2>/dev/null | sort | tail -n 1 || true
  )"
fi

if [[ -z "${LOG_FILE}" || ! -f "${LOG_FILE}" ]]; then
  echo "NO_LOG_FOUND"
  echo "No run log found under ${ROOT_DIR}/run_logs"
  exit 2
fi

echo "# analyzing: ${LOG_FILE}"

classify() {
  local pattern="$1"
  if grep -Eiq "${pattern}" "${LOG_FILE}"; then
    return 0
  fi
  return 1
}

RESULT="UNKNOWN"
classify 'This is a template\. Copy it|return 2' && RESULT="TEMPLATE_NOT_EDITED"
[[ "${RESULT}" == "UNKNOWN" ]] && classify '子脚本不存在|No such file|FileNotFoundError|JSON file not found' && RESULT="SCRIPT_OR_FILE_PATH_ERROR"
[[ "${RESULT}" == "UNKNOWN" ]] && classify 'MQTT connect timed out|ConnectionRefused|No route to host|Name or service not known' && RESULT="MQTT_BROKER_OR_NETWORK_ERROR"
[[ "${RESULT}" == "UNKNOWN" ]] && classify 'timed out waiting for retained ready|gateway not ready|ready.*false' && RESULT="GATEWAY_NOT_READY"
[[ "${RESULT}" == "UNKNOWN" ]] && classify 'capability not advertised|mode .* not advertised|capability disabled|mode .* not allowed' && RESULT="CAPABILITY_OR_MODE_ERROR"
[[ "${RESULT}" == "UNKNOWN" ]] && classify 'safety gate rejected|BLOCKED|live motion requires confirm_physical|live mode disabled|out of range|missing required arg' && RESULT="SAFETY_GATE_BLOCKED"
[[ "${RESULT}" == "UNKNOWN" ]] && classify 'charge_plug_insert_state=1|charge_input_current|charging|插枪|充电' && RESULT="ROBOT_CHARGING_BLOCKER"
[[ "${RESULT}" == "UNKNOWN" ]] && classify 'preflight blocked|nav preflight blocked|arm preflight blocked|gripper preflight blocked|waist preflight blocked' && RESULT="ROBOT_PREFLIGHT_BLOCKED"
[[ "${RESULT}" == "UNKNOWN" ]] && classify 'no-progress|no progress|watchdog|cancel.*navigation' && RESULT="NAV_NO_PROGRESS_WATCHDOG"
[[ "${RESULT}" == "UNKNOWN" ]] && classify 'backend execution failed|step failed|Robot\.|Pnc\.|move_.* failed|Traceback|Exception' && RESULT="GDK_OR_BACKEND_ERROR"
[[ "${RESULT}" == "UNKNOWN" ]] && classify 'yolo|YOLO|cv2|torch|Ultralytics|image|camera|Frame is null' && RESULT="VISION_OR_CAMERA_ERROR"

echo "classification=${RESULT}"
echo
echo "# exit code line"
grep -E 'exit_code:' "${LOG_FILE}" | tail -n 3 || true
echo
echo "# likely error lines"
case "${RESULT}" in
  TEMPLATE_NOT_EDITED)
    line_pattern='This is a template|Copy it|source_script=|exit_code:'
    ;;
  SCRIPT_OR_FILE_PATH_ERROR)
    line_pattern='子脚本不存在|No such file|FileNotFoundError|JSON file not found|path|路径|exit_code:'
    ;;
  MQTT_BROKER_OR_NETWORK_ERROR)
    line_pattern='MQTT connect timed out|ConnectionRefused|No route to host|Name or service not known|1883|mosquitto|exit_code:'
    ;;
  GATEWAY_NOT_READY)
    line_pattern='timed out waiting for retained ready|gateway not ready|ready.*false|/api/ready|g2-industrial-gateway|exit_code:'
    ;;
  CAPABILITY_OR_MODE_ERROR)
    line_pattern='capability not advertised|mode .* not advertised|capability disabled|mode .* not allowed|capabilities|exit_code:'
    ;;
  SAFETY_GATE_BLOCKED)
    line_pattern='safety_decision|safety gate rejected|BLOCKED|live motion requires confirm_physical|live mode disabled|out of range|missing required arg|exit_code:'
    ;;
  ROBOT_CHARGING_BLOCKER)
    line_pattern='charge_plug_insert_state|charge_input_current|charging|插枪|充电|exit_code:'
    ;;
  ROBOT_PREFLIGHT_BLOCKED)
    line_pattern='preflight|nav.preflight|arm.preflight|gripper.preflight|waist.preflight|problems|BLOCKED|exit_code:'
    ;;
  NAV_NO_PROGRESS_WATCHDOG)
    line_pattern='no-progress|no progress|watchdog|cancel.*navigation|PNC|pnc|exit_code:'
    ;;
  GDK_OR_BACKEND_ERROR)
    line_pattern='FAILED|BLOCKED|ERROR|Error|Exception|Traceback|backend execution failed|step failed|Robot\.|Pnc\.|move_.* failed|exit_code:'
    ;;
  VISION_OR_CAMERA_ERROR)
    line_pattern='yolo|YOLO|cv2|torch|Ultralytics|image|camera|Frame is null|LatestImage failed|exit_code:'
    ;;
  *)
    line_pattern='FAILED|BLOCKED|ERROR|Error|Exception|Traceback|timed out|blocked|not found|No such|exit_code:'
    ;;
esac
grep -Ein "${line_pattern}" "${LOG_FILE}" | tail -n 40 || true
echo
echo "# suggested next step"
case "${RESULT}" in
  TEMPLATE_NOT_EDITED)
    echo "Copy the template to a real script and replace main(); do not run the template itself."
    ;;
  SCRIPT_OR_FILE_PATH_ERROR)
    echo "Check script path and JSON/positions path. Use paths inside mqtt_gateway_workspace_20260624."
    ;;
  MQTT_BROKER_OR_NETWORK_ERROR)
    echo "Check: systemctl is-active mosquitto; ss -ltnp | grep 1883."
    ;;
  GATEWAY_NOT_READY)
    echo "Check: systemctl is-active g2-industrial-gateway.service; curl /api/ready."
    ;;
  CAPABILITY_OR_MODE_ERROR)
    echo "Check /api/capabilities and whether the command supports the requested mode."
    ;;
  SAFETY_GATE_BLOCKED)
    echo "Read the safety_decision/error in the log; do not bypass live safety gates."
    ;;
  ROBOT_CHARGING_BLOCKER)
    echo "Unplug/leave charging state, then rerun read-only preflight before live."
    ;;
  ROBOT_PREFLIGHT_BLOCKED)
    echo "Read preflight problems in the log and correct robot/site state before live."
    ;;
  NAV_NO_PROGRESS_WATCHDOG)
    echo "Robot did not make progress; inspect route, obstacles, map, odom, and PNC state."
    ;;
  GDK_OR_BACKEND_ERROR)
    echo "Inspect Gateway journal tail and GDK result in the log; send debug bundle."
    ;;
  VISION_OR_CAMERA_ERROR)
    echo "Check camera snapshot/YOLO model/input files and vision script output."
    ;;
  *)
    echo "Run ./collect_debug_bundle.sh and send the generated tar.gz."
    ;;
esac
