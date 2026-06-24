# WXF MQTT Workspace Release Notes

## 2026.06.24-mqtt-workspace-v2

- Added one-screen no-motion status check: `./status.sh`.
- Added no-motion live readiness preflight: `./preflight_live.sh`.
- Added latest-run classifier: `./analyze_last_run.sh`.
- Added controlled Gateway cancel helper: `./cancel_current_task.sh`.
- Added dry-run log cleanup helper: `./cleanup_run_logs.sh`.
- Added run index: `run_logs/runs.jsonl`.
- Added before/after read-only robot snapshots to every launcher run log.
- Extended debug bundles with workspace status, latest-run analysis, `runs.jsonl`, version, and release notes.
- Added focused templates:
  - `templates/new_nav_script.py`
  - `templates/new_arm_pose_script.py`
  - `templates/new_sequence_task.py`

Safety notes:

- These changes do not modify the original WXF scripts.
- These tools do not open the MQTT broker to the external network.
- There is no automatic live retry. A failed live run must be inspected before rerunning.
