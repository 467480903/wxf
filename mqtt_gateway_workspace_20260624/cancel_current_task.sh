#!/usr/bin/env bash
set -euo pipefail

# Controlled Gateway task cancel helper.
#
# Default mode is read-only: show the current task and exit.
# To cancel the current Gateway task, pass --confirm-cancel.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIRM=0
if [[ "${1:-}" == "--confirm-cancel" ]]; then
  CONFIRM=1
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
用法:
  ./cancel_current_task.sh
      只查看当前 Gateway task，不取消。

  ./cancel_current_task.sh --confirm-cancel
      取消当前 Gateway task。只在现场确认需要停止当前任务时使用。

说明:
  这个脚本不直接调用 PNC cancel_task，不直接写 GDK。
  它只调用 Gateway 的 HTTP cancel 接口。
EOF
  exit 0
fi

python3 - "${CONFIRM}" <<'PY'
import json
import sys
from urllib.request import Request, urlopen

confirm = sys.argv[1] == "1"

def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        f"http://127.0.0.1:8767{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))

try:
    runtime = request("GET", "/api/runtime")
except Exception as exc:
    print(f"Gateway runtime unavailable: {type(exc).__name__}: {exc}")
    print("No cancel was sent.")
    raise SystemExit(2)
current = runtime.get("current_task")
if not current:
    print("No current Gateway task.")
    raise SystemExit(0)

task_id = current.get("task_id")
print(json.dumps({"current_task": current}, ensure_ascii=False, indent=2))
if not confirm:
    print()
    print("Read-only mode. Add --confirm-cancel to cancel this Gateway task.")
    raise SystemExit(0)

if not task_id:
    print("Current task has no task_id; cannot cancel.")
    raise SystemExit(2)

result = request("POST", f"/api/tasks/{task_id}/cancel", {})
print(json.dumps({"cancel_result": result}, ensure_ascii=False, indent=2))
PY
