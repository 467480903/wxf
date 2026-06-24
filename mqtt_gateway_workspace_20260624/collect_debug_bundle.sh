#!/usr/bin/env bash
set -euo pipefail

# Collect a no-motion debug bundle for WXF MQTT/Gateway troubleshooting.
#
# This script is read-only with respect to the robot. It does not publish live
# tasks and does not restart services. It only captures logs and status files.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date '+%Y%m%d_%H%M%S')"
BUNDLE_ROOT="${ROOT_DIR}/run_logs/debug_bundle_${STAMP}"
BUNDLE_TAR="${BUNDLE_ROOT}.tar.gz"

mkdir -p "${BUNDLE_ROOT}/recent_run_logs"

write_cmd() {
  local out="$1"
  shift
  {
    echo "# command: $*"
    echo "# captured_at: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    "$@" 2>&1 || true
  } > "${BUNDLE_ROOT}/${out}"
}

write_shell() {
  local out="$1"
  shift
  {
    echo "# command: $*"
    echo "# captured_at: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    bash -lc "$*" 2>&1 || true
  } > "${BUNDLE_ROOT}/${out}"
}

{
  echo "bundle_created_at=$(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "workspace=${ROOT_DIR}"
  echo "user=$(id -un 2>/dev/null || true)"
  echo "host=$(hostname 2>/dev/null || true)"
  echo "pwd=$(pwd)"
} > "${BUNDLE_ROOT}/README.txt"

write_cmd "systemctl_is_active.txt" systemctl is-active mosquitto g2-industrial-gateway.service g2-industrial-gateway-mqtt.service
write_cmd "systemctl_is_enabled.txt" systemctl is-enabled mosquitto g2-industrial-gateway.service g2-industrial-gateway-mqtt.service
write_cmd "systemctl_status_gateway.txt" systemctl status g2-industrial-gateway.service --no-pager -l
write_cmd "systemctl_status_mqtt.txt" systemctl status g2-industrial-gateway-mqtt.service --no-pager -l
write_cmd "systemctl_status_mosquitto.txt" systemctl status mosquitto --no-pager -l
write_cmd "systemctl_cat_gateway.txt" systemctl cat g2-industrial-gateway.service g2-industrial-gateway-mqtt.service
write_cmd "gateway_env.txt" cat /data/g2_industrial_gateway/g2-industrial-gateway.env
write_shell "ports.txt" "ss -ltnp | grep -E ':(8767|1883)' || true"
write_cmd "gateway_ready.json" curl -sS --max-time 5 http://127.0.0.1:8767/api/ready
write_cmd "gateway_runtime.json" curl -sS --max-time 5 http://127.0.0.1:8767/api/runtime
write_cmd "gateway_capabilities.json" curl -sS --max-time 5 http://127.0.0.1:8767/api/capabilities
write_cmd "gateway_tasks.json" curl -sS --max-time 5 http://127.0.0.1:8767/api/tasks
write_cmd "journal_gateway_tail.txt" journalctl -u g2-industrial-gateway.service -n 300 --no-pager
write_cmd "journal_mqtt_tail.txt" journalctl -u g2-industrial-gateway-mqtt.service -n 300 --no-pager
write_cmd "journal_mosquitto_tail.txt" journalctl -u mosquitto -n 160 --no-pager
write_shell "workspace_tree.txt" "find '${ROOT_DIR}' -maxdepth 3 -type f | sort | sed -n '1,500p'"

if [[ -x "${ROOT_DIR}/status.sh" ]]; then
  write_cmd "workspace_status.txt" "${ROOT_DIR}/status.sh"
fi

if [[ -x "${ROOT_DIR}/analyze_last_run.sh" ]]; then
  write_cmd "last_run_analysis.txt" "${ROOT_DIR}/analyze_last_run.sh"
fi

if [[ -f "${ROOT_DIR}/VERSION" ]]; then
  cp "${ROOT_DIR}/VERSION" "${BUNDLE_ROOT}/VERSION"
fi

if [[ -f "${ROOT_DIR}/RELEASE_NOTES.md" ]]; then
  cp "${ROOT_DIR}/RELEASE_NOTES.md" "${BUNDLE_ROOT}/RELEASE_NOTES.md"
fi

if [[ -f "${ROOT_DIR}/run_logs/runs.jsonl" ]]; then
  cp "${ROOT_DIR}/run_logs/runs.jsonl" "${BUNDLE_ROOT}/runs.jsonl"
fi

if command -v mosquitto_sub >/dev/null 2>&1; then
  write_cmd "mqtt_ready_retained.json" timeout 5 mosquitto_sub -h 127.0.0.1 -p 1883 -t g2/gateway/state/ready -C 1
  write_cmd "mqtt_capabilities_retained.json" timeout 5 mosquitto_sub -h 127.0.0.1 -p 1883 -t g2/gateway/capabilities -C 1
else
  echo "mosquitto_sub not found" > "${BUNDLE_ROOT}/mqtt_retained_not_available.txt"
fi

if [[ -d "${ROOT_DIR}/run_logs" ]]; then
  find "${ROOT_DIR}/run_logs" \
    \( -path "${ROOT_DIR}/run_logs/debug_bundle_*" -o -path "${ROOT_DIR}/run_logs/preflight" \) -prune \
    -o -type f -name '*.log' -print | sort | tail -n 30 > "${BUNDLE_ROOT}/recent_run_logs_index.txt"
  while IFS= read -r log_file; do
    [[ -n "${log_file}" ]] || continue
    cp "${log_file}" "${BUNDLE_ROOT}/recent_run_logs/$(basename "${log_file}")" || true
  done < "${BUNDLE_ROOT}/recent_run_logs_index.txt"
fi

if [[ -d "${ROOT_DIR}/run_logs/preflight" ]]; then
  mkdir -p "${BUNDLE_ROOT}/preflight"
  find "${ROOT_DIR}/run_logs/preflight" -maxdepth 1 -type f -name 'preflight_live_*.log' \
    | sort | tail -n 10 > "${BUNDLE_ROOT}/preflight_logs_index.txt"
  while IFS= read -r preflight_log; do
    [[ -n "${preflight_log}" ]] || continue
    cp "${preflight_log}" "${BUNDLE_ROOT}/preflight/$(basename "${preflight_log}")" || true
  done < "${BUNDLE_ROOT}/preflight_logs_index.txt"
  find "${ROOT_DIR}/run_logs/preflight" -maxdepth 1 -type d -name 'preflight_live_*_raw' \
    | sort | tail -n 3 > "${BUNDLE_ROOT}/preflight_raw_dirs_index.txt"
  while IFS= read -r raw_dir; do
    [[ -n "${raw_dir}" ]] || continue
    cp -a "${raw_dir}" "${BUNDLE_ROOT}/preflight/" || true
  done < "${BUNDLE_ROOT}/preflight_raw_dirs_index.txt"
fi

tar -C "${ROOT_DIR}/run_logs" -czf "${BUNDLE_TAR}" "$(basename "${BUNDLE_ROOT}")"
ln -sfn "$(basename "${BUNDLE_TAR}")" "${ROOT_DIR}/run_logs/latest_debug_bundle.tar.gz"
rm -rf "${BUNDLE_ROOT}"
echo "debug bundle: ${BUNDLE_TAR}"
echo "latest bundle: ${ROOT_DIR}/run_logs/latest_debug_bundle.tar.gz"
