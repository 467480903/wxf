# yolo gateway MQTT migration

Directory name on robot: `gateway_mqtt_20260624`

This directory is a copied-and-adapted version of the top-level Python scripts
from `/data/wxf/wxf/yolo`. The original scripts were not modified.

## What changed

- Motion wrappers no longer import the robot SDK directly.
- `move_arm_by_json.py`, `move_whole_body_by_json.py`, `offset_move_common.py`,
  `move_ee_pose_open_05.py`, `move_ee_pose_right_half.py`, and `correct_waist.py`
  submit `g2.task.v1` requests to `g2/gateway/task/request`.
- Default motion mode is `dry_run`; `live` is intentionally rejected in this
  migrated folder.
- Camera capture scripts read gateway HTTP camera snapshot endpoints instead of
  opening a camera object locally.
- Sequence scripts default to plan-only mode. With `--execute`, they run only
  local migrated scripts and local file copy/move operations. External
  `../BOX_528_1` and `../Robot` commands are blocked.

## How to call

Read-only smoke:

```bash
python3 gateway_mqtt_client.py --command gdk.read_power_state --mode read_only --args-json '{}'
```

Dry-run movement wrapper:

```bash
python3 offset_move_forward_001.py
python3 move_arm_by_json.py ../positions/pick_b_2.json
python3 move_whole_body_by_json.py ../positions/pick_standby.json
```

Sequence plan only:

```bash
python3 task_all_pick_b.py
```

Sequence execution through migrated local wrappers only:

```bash
python3 task_all_pick_b.py --execute
```

## Important boundary

These scripts save the repeated local SDK init/release time because the field
scripts only submit gateway tasks. Real robot motion still requires audited live
capabilities in the gateway and explicit field approval before enabling live
mode.
