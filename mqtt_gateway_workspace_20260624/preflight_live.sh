#!/usr/bin/env bash
set -euo pipefail

# No-motion live readiness preflight for WXF MQTT runs.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${ROOT_DIR}/run_logs/preflight"
STAMP="$(date '+%Y%m%d_%H%M%S')"
REPORT="${OUT_DIR}/preflight_live_${STAMP}.log"
RAW_DIR="${OUT_DIR}/preflight_live_${STAMP}_raw"
mkdir -p "${OUT_DIR}"
mkdir -p "${RAW_DIR}"

exec > >(tee -a "${REPORT}") 2>&1

echo "# WXF live preflight"
echo "# workspace: ${ROOT_DIR}"
echo "# captured_at: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "# report: ${REPORT}"
echo "# raw_json_dir: ${RAW_DIR}"
echo

blockers=0
warn() { echo "WARN: $*"; }
block() { echo "BLOCKED: $*"; blockers=$((blockers + 1)); }
pass() { echo "PASS: $*"; }

echo "## services"
for service in mosquitto g2-industrial-gateway.service g2-industrial-gateway-mqtt.service; do
  state="$(systemctl is-active "${service}" 2>/dev/null || true)"
  enabled="$(systemctl is-enabled "${service}" 2>/dev/null || true)"
  echo "${service}: active=${state}, enabled=${enabled}"
  [[ "${state}" == "active" ]] || block "${service} is not active"
  [[ "${enabled}" == "enabled" ]] || warn "${service} is not enabled"
done
echo

echo "## ports"
ports_plain="$(ss -ltn 2>/dev/null || true)"
ports_with_process="$(ss -ltnp 2>/dev/null || true)"
printf '%s\n' "${ports_with_process}" | grep -E ':(8767|1883)' || true
printf '%s\n' "${ports_plain}" | grep -Eq '127\.0\.0\.1:1883[[:space:]]' || block "MQTT broker is not listening on 127.0.0.1:1883"
printf '%s\n' "${ports_plain}" | grep -Eq '0\.0\.0\.0:8767[[:space:]]' || warn "Gateway HTTP is not visibly listening on 0.0.0.0:8767"
echo

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

curl -sS --max-time 5 http://127.0.0.1:8767/api/ready > "${tmpdir}/ready.json" || block "cannot read /api/ready"
curl -sS --max-time 5 http://127.0.0.1:8767/api/runtime > "${tmpdir}/runtime.json" || block "cannot read /api/runtime"
curl -sS --max-time 5 http://127.0.0.1:8767/api/capabilities > "${tmpdir}/capabilities.json" || block "cannot read /api/capabilities"

echo "## gateway summary"
python3 - "${tmpdir}/ready.json" "${tmpdir}/runtime.json" "${tmpdir}/capabilities.json" <<'PY' || blockers=$((blockers + 1))
import json
import sys

ready_path, runtime_path, cap_path = sys.argv[1:]
ready = json.load(open(ready_path, encoding="utf-8"))
runtime = json.load(open(runtime_path, encoding="utf-8"))
caps = json.load(open(cap_path, encoding="utf-8")).get("capabilities", [])
required = {
    "nav.goto_pose",
    "head.set_pan_tilt",
    "arm.move_named_pose",
    "waist.move_named_pose",
    "gripper.open",
    "gripper.close",
    "ee.relative_offset",
}
cap_live = {
    item.get("name")
    for item in caps
    if isinstance(item, dict) and "live" in item.get("modes", [])
}
backend = runtime.get("backend", {})
live_commands = set(backend.get("live_commands", [])) if isinstance(backend, dict) else set()
problems = []
if ready.get("ok") is not True:
    problems.append(f"ready.ok={ready.get('ok')}")
if ready.get("backend") != "gdk-live":
    problems.append(f"backend={ready.get('backend')}")
if ready.get("gdk_connected") is not True:
    problems.append(f"gdk_connected={ready.get('gdk_connected')}")
if runtime.get("allow_live") is not True:
    problems.append(f"allow_live={runtime.get('allow_live')}")
missing_caps = sorted(required - cap_live)
if missing_caps:
    problems.append("missing live capabilities: " + ",".join(missing_caps))
missing_backend = sorted(required - live_commands)
if missing_backend:
    problems.append("missing backend live_commands: " + ",".join(missing_backend))
print(f"ready_ok={ready.get('ok')}")
print(f"backend={ready.get('backend')}")
print(f"gdk_connected={ready.get('gdk_connected')}")
print(f"allow_live={runtime.get('allow_live')}")
print(f"queue_depth={runtime.get('queue_depth')}")
print(f"current_task={'yes' if runtime.get('current_task') else 'none'}")
if problems:
    for problem in problems:
        print("BLOCKED:", problem)
    raise SystemExit(1)
print("PASS: gateway live readiness")
PY
echo

echo "## mqtt retained topics"
if command -v mosquitto_sub >/dev/null 2>&1; then
  timeout 5 mosquitto_sub -h 127.0.0.1 -p 1883 -t g2/gateway/state/ready -C 1 > "${tmpdir}/mqtt_ready.json" || block "missing retained MQTT ready topic"
  timeout 5 mosquitto_sub -h 127.0.0.1 -p 1883 -t g2/gateway/capabilities -C 1 > "${tmpdir}/mqtt_capabilities.json" || block "missing retained MQTT capabilities topic"
  [[ -s "${tmpdir}/mqtt_ready.json" ]] && pass "MQTT ready retained topic exists"
  [[ -s "${tmpdir}/mqtt_capabilities.json" ]] && pass "MQTT capabilities retained topic exists"
else
  warn "mosquitto_sub not found; retained topic check skipped"
fi
echo

echo "## robot read-only preflights"
allow_estop="false"
if [[ "${G2_WXF_ALLOW_ESTOP_PEDAL_FAULT:-1}" == "1" ]]; then
  allow_estop="true"
fi

summarize_readonly() {
  local command="$1"
  local outfile="$2"
  python3 - "${command}" "${outfile}" <<'PY'
import json
import sys
from pathlib import Path

command, path = sys.argv[1:]
text = Path(path).read_text(encoding="utf-8", errors="replace")
try:
    payload = json.loads(text)
except Exception:
    print("raw_output_tail:")
    print(text[-4000:])
    raise SystemExit(0)

result = payload.get("result", {})
if not isinstance(result, dict):
    result = {}

print(f"state={payload.get('state')} error={payload.get('error')}")

if command == "gdk.read_power_state":
    power = result.get("chassis_power", {})
    if not isinstance(power, dict):
        power = {}
    socs = []
    for item in power.get("battery_states", []):
        if isinstance(item, dict) and "battery_soc" in item:
            socs.append(item.get("battery_soc"))
    print(f"charge_plug_insert_state={power.get('charge_plug_insert_state')}")
    print(f"emergency_stop_pedal_fault_state={power.get('emergency_stop_pedal_fault_state')}")
    print(f"emergency_stop_pedal_state={power.get('emergency_stop_pedal_state')}")
    print(f"battery_soc={socs}")
elif command == "gdk.read_task_state":
    print(f"task_state={result.get('task_state')}")
elif command.endswith(".preflight"):
    print(f"ok={result.get('ok')}")
    print(f"problems={result.get('problems', [])}")
    readings = result.get("readings", {})
    if isinstance(readings, dict):
        pnc = readings.get("pnc_task", {})
        if isinstance(pnc, dict):
            print(f"pnc_task={pnc.get('value')}")
        whole_body = readings.get("whole_body", {})
        if isinstance(whole_body, dict):
            print(f"whole_body_ok={whole_body.get('ok')}")
else:
    print(json.dumps(result, ensure_ascii=False, sort_keys=True)[:2000])
PY
}

run_readonly() {
  local command="$1"
  local args_json="${2-}"
  if [[ -z "${args_json}" ]]; then
    args_json='{}'
  fi
  local outfile="${tmpdir}/${command//./_}.json"
  echo "# ${command}"
  if timeout 18 python3 "${ROOT_DIR}/gateway_mqtt_client.py" \
    --command "${command}" \
    --mode read_only \
    --args-json "${args_json}" \
    --timeout-s 12 \
    --preflight warn > "${outfile}" 2>&1; then
    cp "${outfile}" "${RAW_DIR}/${command//./_}.json" || true
    summarize_readonly "${command}" "${outfile}"
  else
    cp "${outfile}" "${RAW_DIR}/${command//./_}.txt" || true
    summarize_readonly "${command}" "${outfile}"
    block "${command} failed"
  fi
  echo
}

run_readonly gdk.read_power_state
run_readonly gdk.read_task_state
run_readonly nav.preflight "{\"allow_estop_pedal_fault\": ${allow_estop}}"
run_readonly arm.preflight

python3 - "${tmpdir}/nav_preflight.json" "${tmpdir}/arm_preflight.json" "${allow_estop}" <<'PY' || blockers=$((blockers + 1))
import json
import sys

allow_estop = sys.argv[3].lower() == "true"
for name, path in (("nav.preflight", sys.argv[1]), ("arm.preflight", sys.argv[2])):
    try:
        payload = json.load(open(path, encoding="utf-8"))
    except Exception as exc:
        print(f"BLOCKED: cannot parse {name}: {type(exc).__name__}: {exc}")
        raise SystemExit(1)
    result = payload.get("result", {})
    if not isinstance(result, dict):
        result = payload
    ok = result.get("ok")
    problems = result.get("problems", [])
    accepted = []
    if name == "nav.preflight" and allow_estop and isinstance(problems, list):
        remaining = []
        for problem in problems:
            text = str(problem)
            if text.startswith("emergency_stop_pedal_fault_state"):
                accepted.append(text)
            else:
                remaining.append(problem)
        problems = remaining
    if ok is False:
        if not problems and accepted:
            print(f"PASS: {name} only has accepted known problems={accepted}")
            continue
        print(f"BLOCKED: {name} problems={problems}")
        if accepted:
            print(f"accepted_known_problems={accepted}")
        raise SystemExit(1)
    print(f"PASS: {name} ok={ok}")
PY

echo
if [[ "${blockers}" -eq 0 ]]; then
  echo "FINAL: PASS - live readiness checks passed. Still requires现场 safety confirmation before motion."
  exit 0
fi

echo "FINAL: BLOCKED - ${blockers} blocker(s). Do not run live until fixed."
exit 1
