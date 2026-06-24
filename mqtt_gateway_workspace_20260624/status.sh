#!/usr/bin/env bash
set -euo pipefail

# One-screen no-motion status summary for the WXF MQTT workspace.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "# WXF MQTT workspace status"
echo "# workspace: ${ROOT_DIR}"
echo "# captured_at: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo

echo "## services"
systemctl is-active mosquitto g2-industrial-gateway.service g2-industrial-gateway-mqtt.service 2>&1 || true
echo

echo "## ports"
ss -ltnp 2>/dev/null | grep -E ':(8767|1883)' || true
echo

echo "## gateway ready/runtime summary"
python3 - <<'PY'
import json
from urllib.request import urlopen


def get_json(path: str) -> dict:
    with urlopen(f"http://127.0.0.1:8767{path}", timeout=3) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else {}


try:
    ready = get_json("/api/ready")
    runtime = get_json("/api/runtime")
    caps = get_json("/api/capabilities").get("capabilities", [])
except Exception as exc:
    print(f"gateway_status=ERROR {type(exc).__name__}: {exc}")
    raise SystemExit(0)

backend = runtime.get("backend", {})
live_commands = backend.get("live_commands", []) if isinstance(backend, dict) else []
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
missing = sorted(required - cap_live)
print(f"ready_ok={ready.get('ok')}")
print(f"backend={ready.get('backend')}")
print(f"gdk_connected={ready.get('gdk_connected')}")
print(f"allow_live={runtime.get('allow_live')}")
print(f"queue_depth={runtime.get('queue_depth')}")
print(f"current_task={'yes' if runtime.get('current_task') else 'none'}")
print(f"live_commands={','.join(live_commands)}")
print(f"required_live_capabilities={'OK' if not missing else 'MISSING ' + ','.join(missing)}")
PY
echo

echo "## latest run"
if [[ -f "${ROOT_DIR}/run_logs/runs.jsonl" ]]; then
  tail -n 5 "${ROOT_DIR}/run_logs/runs.jsonl"
else
  echo "no run index yet: ${ROOT_DIR}/run_logs/runs.jsonl"
fi
echo

echo "## latest log"
latest_log="$(
  find "${ROOT_DIR}/run_logs" \
    \( -path "${ROOT_DIR}/run_logs/debug_bundle_*" -o -path "${ROOT_DIR}/run_logs/preflight" \) -prune \
    -o -type f -name '*.log' -print 2>/dev/null | sort | tail -n 1 || true
)"
if [[ -n "${latest_log}" ]]; then
  echo "${latest_log}"
else
  echo "no run log yet"
fi
