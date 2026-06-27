# G2A WXF MQTT Handoff 2026-06-27

## Resume First

Continue from this file for the current G2A WXF MQTT workspace. Do not restart
from the older scattered WXF directories.

Current truth source:

```text
Robot target:      agi@10.185.207.253
Jump host:         agi@10.185.207.160
Robot workspace:   /data/wxf/wxf/mqtt_gateway_workspace_20260624
Original sources:  /data/wxf/wxf/yolo
                   /data/wxf/wxf/BOX_528_1
                   /data/wxf/wxf/Robot
                   /data/wxf/wxf/positions
```

Do not store SSH passwords in handoff files or memory. Re-check the active
robot before any live motion.

## Completed Today

### `task_all_pick_a.py` MQTT Mode

The original customer script was converted into the MQTT workspace without
modifying the original source directory.

Original source:

```text
/data/wxf/wxf/yolo/task_all_pick_a.py
```

MQTT workspace wrapper:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo/task_all_pick_a.py
```

The active `TASK_SEQUENCE` is identical to the original script:

```text
original_len=19
mqtt_len=19
sequence_equal=True
```

Important flow detail:

```text
move-ready1.py stays omitted because it is commented out in the original.
move_arm_by_json_grab_delever.py stays after move-put1.py as original step 19.
```

The conversion only changes the execution layer. Supported child steps route
through MQTT/Gateway fast-inline calls, while camera/YOLO and the existing
navigation wrapper scripts remain in the same order. Arm speed remains aligned
with the original path through the runner default:

```text
G2_WXF_FAST_ARM_SPEED_RADPS=0.2
```

Validation:

```text
python3 -m py_compile /tmp/wxf_mqtt_task_all_pick_a_20260627/task_all_pick_a.py
python3 -m py_compile /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo/task_all_pick_a.py

/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_fast_live_script.sh yolo/task_all_pick_a.py
exit_code=0
log: /data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_103212_fast_live_script_yolo_task_all_pick_a.py_79393.log
```

No `--execute` was run for this new wrapper.

### `task_all_pick_b.py` MQTT Mode

The current original customer script was converted into the MQTT workspace,
replacing an older stale MQTT wrapper from 2026-06-25. The original source
directory was not modified.

Original source:

```text
/data/wxf/wxf/yolo/task_all_pick_b.py
```

MQTT workspace wrapper:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo/task_all_pick_b.py
```

Backup before overwrite:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/backups/task_all_pick_b_mqtt_20260627_1040
```

The active `TASK_SEQUENCE` is identical to the current original script:

```text
original_len=12
mqtt_len=12
sequence_equal=True
```

Important flow details:

```text
Commented-out camera/YOLO/TTS/body-pose lines stay omitted.
offset_move_push_grab_b.py is preserved as step 5.
move_whole_body_by_json.py ../positions/pick_standby.json remains final step 12.
```

Additional MQTT workspace alignment:

```text
BOX_528_1/offset_move_push_grab_b.py added as MQTT wrapper:
  left x=0.110m, right x=0.105m, matching original formula.

mqtt_common.py fast-inline mapping added:
  offset_move_push_grab_b.py -> left (0.110, 0, 0), right (0.105, 0, 0)

BOX_528_1/move-pick2.py updated to mirror original active nav calls:
  go(11), go(14), go(15), go_adjusted(32)
  go(13) stays omitted because it is commented out in the original.

BOX_528_1/move-put2.py updated to mirror original active nav calls:
  go(22), go_adjusted(23), go_adjusted(25)
  go(19), go(20), go(21) stay omitted because they are commented out.
```

Adjusted map-frame targets now preserved explicitly:

```text
go_adjusted(32): x=0.07965588715268747, y=-0.6056166148205059, yaw=-1.5499916324135872
go_adjusted(23): x=1.4891060183247533,  y=-3.9044867812030795, yaw=3.1155985098813317
go_adjusted(25): x=1.3796321001429732,  y=-3.9044867812030795, yaw=3.1155985098813317
```

Validation:

```text
python3 -m py_compile \
  /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo/task_all_pick_b.py \
  /data/wxf/wxf/mqtt_gateway_workspace_20260624/BOX_528_1/offset_move_push_grab_b.py \
  /data/wxf/wxf/mqtt_gateway_workspace_20260624/BOX_528_1/move-pick2.py \
  /data/wxf/wxf/mqtt_gateway_workspace_20260624/BOX_528_1/move-put2.py \
  /data/wxf/wxf/mqtt_gateway_workspace_20260624/mqtt_common/mqtt_common.py

/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_fast_live_script.sh yolo/task_all_pick_b.py
exit_code=0
log: /data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_104005_fast_live_script_yolo_task_all_pick_b.py_119409.log
```

Dry-run output confirmed:

```text
# steps=12, mode=dry-run plan
[05/12] fast_inline: python ../BOX_528_1/offset_move_push_grab_b.py
G2_WXF_FAST_ARM_SPEED_RADPS=0.2
```

Final audit before live:

```text
move_ee_pose_close_2.py fast-inline was corrected to match the original:
  right close target=0.0
  sleep 0.05s
  left close target=0.0

task_all_pick_b.py now forces the final whole-body split delay to 0.2s,
matching the original move_whole_body_by_json.py head -> waist -> arms sleeps.

task_all_pick_b.py also forces non-contact EE offsets back to the conservative
original pacing for this flow:
  G2_WXF_FAST_EE_NONCONTACT_MAX_STEP_M=0.001
  G2_WXF_FAST_EE_NONCONTACT_RATE_HZ=50

no-motion monkeypatch result for close_2:
  [('gripper.close', 'right', 0.0), ('gripper.close', 'left', 0.0)]

no-motion monkeypatch result for pick-B non-contact offsets:
  offset_move_up.py   max_step_m=0.001 rate_hz=50.0
  offset_move_pull.py max_step_m=0.001 rate_hz=50.0

latest dry-run after final audit:
  /data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_105122_fast_live_script_yolo_task_all_pick_b.py_176613.log
  exit_code=0
```

No `--execute` was run for this new wrapper.

### Navigation Poll Interval Patch

The low-risk navigation wait-loop optimization from the 2026-06-26 handoff was
applied in the MQTT workspace.

Changed file:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/mqtt_common/mqtt_common.py
```

Backup:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/backups/nav_poll_interval_20260627_1025/mqtt_common.py
```

Exact behavior change:

```text
G2_WXF_NAV_POLL_INTERVAL_S default: 0.5 -> 0.25
```

This changed only the client-side polling interval passed to `nav.goto_pose`.
It did not change chassis speed, acceleration, waypoint coordinates, safety
logic, or navigation controller parameters.

## Validation

Robot-side context checks:

```text
hostname: G2
robot date: Sat Jun 27 10:20:42 AM CST 2026
VERSION: 2026.06.24-mqtt-workspace-v2
g2-industrial-gateway-mqtt.service: active
mosquitto: active
```

Syntax checks:

```text
python3 -m py_compile /tmp/wxf_mqtt_nav_poll_patch_20260627/mqtt_common.py
python3 -m py_compile /data/wxf/wxf/mqtt_gateway_workspace_20260624/mqtt_common/mqtt_common.py
```

Remote diff confirmed the patch is exactly two default-value changes:

```text
poll_interval_s: env_float("G2_WXF_NAV_POLL_INTERVAL_S", 0.5)
poll_interval_s: env_float("G2_WXF_NAV_POLL_INTERVAL_S", 0.25)
```

Dry-run plan checks, no `--execute`:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_fast_live_script.sh yolo/task_all.py
exit_code=0
log: /data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_102505_fast_live_script_yolo_task_all.py_43526.log

/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_fast_live_script.sh yolo/task_all_place_a.py
exit_code=0
log: /data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_102516_fast_live_script_yolo_task_all_place_a.py_44442.log

/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_fast_live_script.sh yolo/task_all_place_b.py
exit_code=0
log: /data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_102516_fast_live_script_yolo_task_all_place_b.py_44567.log
```

The wrapper exports live-capable environment variables, but the three top-level
`task_all*.py` wrappers only print a dry-run plan unless `--execute` is passed.
No real robot motion was triggered by this validation.

## Latest B Status

Latest observed B live log from yesterday:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260626/20260626_201714_fast_live_script_yolo_task_all_place_b.py_305104.log
finished_at: 2026-06-26 20:18:21 CST
exit_code: 0
```

Read-only log scan:

```text
ERROR: none found
traceback: none found
step_timing entries: 29/29 done
```

This only proves the script layer completed. It does not prove the physical B
placement is acceptable. Keep B placement marked open until the onsite operator
confirms the workpiece actually inserts correctly.

## Live Commands Need Confirmation

These commands physically move the robot and require explicit onsite approval:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all.py --execute
./run_fast_live_script.sh yolo/task_all_pick_a.py --execute
./run_fast_live_script.sh yolo/task_all_pick_b.py --execute
./run_fast_live_script.sh yolo/task_all_place_a.py --execute
./run_fast_live_script.sh yolo/task_all_place_b.py --execute
```

Use `task_all.py --execute` first if the next goal is to measure the navigation
poll interval effect in the chassis-heavy path. Do not tune B further without
fresh onsite feedback from the latest B run.

## 2026-06-27 task_all_pick_a Live Failure And Patch

David ran:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_a.py --execute
```

Observed live log:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_105528_fast_live_script_yolo_task_all_pick_a.py_197576.log
exit_code=1
```

The run completed:

```text
[01/19] move_ee_pose_open_2.py, duration_s=1.469
[02/19] move_arm_by_json_grab_delever.py, duration_s=0.989, gdk velocities=[0.2]*14
```

It failed in:

```text
[03/19] move-pick1.py
RuntimeError: nav preflight blocked: pnc_task_state_not_idle=2,id=3
```

Post-failure audit found and fixed two MQTT wrapper deviations from the original:

```text
move-pick1.py:
  original active: 2 -> 3
  old MQTT:        1 -> 2 -> 3
  fixed MQTT:      2 -> 3

move-put1.py:
  original active: 9 -> 10 -> adjusted 12
  old MQTT:        7 -> 8 -> 9 -> 10 -> adjusted 11 -> adjusted 12
  fixed MQTT:      9 -> 10 -> adjusted 12
```

Also patched `mqtt_common.run_nav_waypoints()` with a narrow PNC-busy retry for
the observed transient backend preflight race:

```text
retry only when error contains:
  pnc_task_state_not_idle
  PNC task is not idle

defaults:
  G2_WXF_NAV_BUSY_RETRIES=6
  G2_WXF_NAV_BUSY_RETRY_DELAY_S=0.5
```

This retry does not cancel PNC tasks and does not change waypoints, chassis
speed, arm speed, gripper targets, or EE offsets.

Robot-side backups:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/backups/move_pick1_align_20260627_1104/move-pick1.py
/data/wxf/wxf/mqtt_gateway_workspace_20260624/backups/move_put1_align_20260627_1100/move-put1.py
/data/wxf/wxf/mqtt_gateway_workspace_20260624/backups/nav_busy_retry_20260627_1102/mqtt_common.py
```

Validation after patch:

```text
python3 -m py_compile mqtt_common/mqtt_common.py BOX_528_1/move-pick1.py BOX_528_1/move-put1.py yolo/task_all_pick_a.py
exit_code=0

PNC busy monkeypatch:
  calls 2
  sleeps [0.5]
  retry_ok True

dry-run, no --execute:
  /data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_110319_fast_live_script_yolo_task_all_pick_a.py_235562.log
  exit_code=0
```

Codex did not execute real motion after applying these patches.

## 2026-06-27 Follow-up: A status, B point audit, gripper sync

Current A status:

```text
task_all_pick_a.py is code-fixed and validated by py_compile, dry-run, and
no-motion monkeypatch checks.

It has not yet been revalidated by a full live A end-to-end run after the latest
PNC idle and gripper sync changes.
```

Because the previous A live run had already completed the pick/pull path and
failed at step 18, use the resume wrapper instead of restarting from step 1 if
the robot is still carrying A:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_a_resume_after_move_put1_fail.py --execute
```

The resume wrapper runs only:

```text
1. python ../BOX_528_1/move-put1.py
2. python ../BOX_528_1/move_arm_by_json_grab_delever.py
```

B point audit:

```text
Original move-pick2.py:
  robot.go(11)
  # robot.go(13)
  robot.go(14)
  robot.go(15)
  robot.go_adjusted(32)

MQTT move-pick2.py:
  11 -> 14 -> 15 -> adjusted 32
```

So B `move-pick2.py` is not missing map point 13; point 13 is commented out in
the original. The other B navigation wrappers also match the original active
lines:

```text
move-adjust2.py:
  15 -> 14

move-put2.py:
  22 -> adjusted 23 -> adjusted 25
  go(19), go(20), go(21) are commented out in the original
```

PNC stable-idle fix:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/mqtt_common/mqtt_common.py
/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_fast_live_script.sh

G2_WXF_NAV_IDLE_WAIT_POLL_S=0.25
G2_WXF_NAV_IDLE_STABLE_S=1.0
```

This avoids submitting the next nav waypoint after a single stale `state=9`
read. The wrapper now waits for PNC idle state to remain stable before the next
`nav.goto_pose`.

Gripper sync fix:

```text
Robot/move_ee_pose_open_2.py:
  gripper.open side=both, target=-0.785, inter_side_delay_s=0.0

Robot/move_ee_pose_close_2.py:
  gripper.close side=both, target=0.0, inter_side_delay_s=0.0

run_fast_live_script.sh:
  G2_WXF_FAST_GRIPPER_INTER_SIDE_DELAY_S=0
```

This removes the old WXF MQTT behavior where open/close was split into two
separate serialized MQTT tasks. Gateway internals still call GDK
`Robot.move_ee_pos()` once per tool group for `side=both`, but now it happens
inside one gateway task with zero inter-side delay.

Validation:

```text
python3 -m py_compile mqtt_common/mqtt_common.py BOX_528_1/move-pick2.py BOX_528_1/move-adjust2.py BOX_528_1/move-put2.py yolo/task_all_pick_b.py yolo/task_all_pick_a.py yolo/task_all_pick_a_resume_after_move_put1_fail.py
exit_code=0

no-motion nav stable-idle monkeypatch:
  state=2 -> stable state=9 -> submit nav.goto_pose

no-motion gripper monkeypatch:
  open_2: one gripper.open side=both task
  close_2: one gripper.close side=both task

dry-run:
  ./run_fast_live_script.sh yolo/task_all_pick_b.py
  exit_code=0
  log=/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_112436_fast_live_script_yolo_task_all_pick_b.py_343710.log
```

Latest read-only state after B failure:

```text
PNC task_state: state=9, id=10
odom velocity/ang_vel: 0
```

No real robot motion was executed by Codex for these follow-up validations.

## Latest Update: A waist correction failure fixed

David reran full A from step 1 and it progressed past the earlier navigation
race. It failed at step 7:

```text
log=/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_112854_fast_live_script_yolo_task_all_pick_a.py_364881.log
[07/19] python correct_waist.py
waist.move_named_pose failed
idx05_body_joint5 value is out of range
raw slope.angle_rad=3.092
sent delta_rad before fix=-3.092
```

Root cause: YOLO returned the two holes in the opposite order, so the same
shallow line was represented as `177.16 deg` instead of `-2.84 deg`. MQTT now
normalizes the line angle to the smallest equivalent value before applying the
same original waist semantics (`idx05 -= target_delta`).

Patched robot-side file:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/mqtt_common/mqtt_common.py
```

Backup:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/backups/waist_angle_normalize_/mqtt_common.py
```

No-motion validation:

```text
python3 -m py_compile mqtt_common/mqtt_common.py yolo/correct_waist.py
raw=3.092000 normalized=-0.049593 delta_to_send=0.049593

cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
G2_WXF_GATEWAY_MODE=mock G2_WXF_GATEWAY_PREFLIGHT=skip python3 correct_waist.py
mode=mock executed=false state=DONE delta_rad=0.049592653589793034
```

New recovery wrapper:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo/task_all_pick_a_resume_after_correct_waist_fail.py
```

Dry-run plan:

```text
./run_fast_live_script.sh yolo/task_all_pick_a_resume_after_correct_waist_fail.py
exit_code=0
steps=13
```

If the robot/workpiece/camera result has not moved since the failed run, resume
from the corrected waist step:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_a_resume_after_correct_waist_fail.py --execute
```

If the scene changed or the YOLO result is stale, run full A again:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_a.py --execute
```

Full live A completion is still pending after this waist-angle patch.

## Latest Update: gripper side=both now starts both sides in parallel

After A completed once, David reported a physical gripper mismatch: the right
gripper clamped but the left gripper did not clamp as expected. The MQTT
workspace was already sending one `side=both` gripper task for same-target
left/right commands, which is the desired service-mode surface. The bug was
below that surface in the live Gateway backend.

Confirmed source comparison:

```text
Original place A:
  /data/wxf/wxf/yolo/task_all_place_a.py calls:
    move_ee_pose_open_05.py
    ../Robot/move_ee_pose_open_2.py

MQTT workspace:
  /data/wxf/wxf/mqtt_gateway_workspace_20260624/mqtt_common/mqtt_common.py
  run_gripper() sends one task when targets match:
    side=both
```

Gateway fix:

```text
patched:
  /data/g2_industrial_gateway/current/g2_industrial_gateway/gdk_live_backend.py

backup:
  /data/g2_industrial_gateway/backups/gripper_parallel_both_20260627_115054/gdk_live_backend.py
```

New live backend behavior:

```text
side=both:
  prepare left_tool and right_tool JointStates
  start both Robot.move_ee_pos calls with one threading.Event
  return a single Gateway result with:
    gripper.execution_mode=parallel_both
    gdk_call.parallel_both=true
```

Service reload completed:

```text
echo 1 | sudo -S systemctl restart g2-industrial-gateway.service g2-industrial-gateway-mqtt.service

g2-industrial-gateway.service active since 2026-06-27 11:52:42 CST, PID 488856
g2-industrial-gateway-mqtt.service active since 2026-06-27 11:52:42 CST, PID 488857
```

No physical gripper test was run by Codex. Next operator run should be the
normal A command, and the gripper log should show `execution_mode=parallel_both`
for same-target open/close tasks.

## Latest Update: post-restart preflight first-status retry

David reran A after the gripper parallel patch and hit a new failure before any
motion:

```text
log=/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_115505_fast_live_script_yolo_task_all_pick_a.py_503022.log
step=01/19 Robot/move_ee_pose_open_2.py
command=gripper.open side=both
error=gripper preflight blocked: whole_body_unavailable=RuntimeError: Failed to get whole body status
```

Cause: after a Gateway restart, GDK initializes lazily on the first task. The
first `get_whole_body_status()` may run before DDS/HAL has delivered the first
whole-body status frame. The journal showed `No whole body status message
found` at the first failed task timestamp.

Patched:

```text
/data/g2_industrial_gateway/current/g2_industrial_gateway/gdk_readonly_backend.py
```

Backup:

```text
/data/g2_industrial_gateway/backups/preflight_read_retry_20260627_121130/gdk_readonly_backend.py
```

Behavior:

```text
_safe_raw_read() retries passive status reads before returning a preflight read
failure.

Defaults:
  G2_GATEWAY_SAFE_RAW_READ_ATTEMPTS=12
  G2_GATEWAY_SAFE_RAW_READ_RETRY_DELAY_S=0.25
```

This is not a preflight bypass. Real error fields still block motion; missing
status still fails closed if it does not appear inside the retry window.

Reload and read-only validation completed:

```text
python3 -m py_compile g2_industrial_gateway/gdk_readonly_backend.py g2_industrial_gateway/gdk_live_backend.py
echo 1 | sudo -S systemctl restart g2-industrial-gateway.service g2-industrial-gateway-mqtt.service

ee.preflight side=both:
  state=DONE
  ok=true
  problems=[]

gdk.read_whole_body_status:
  state=DONE
  right_end_model=omnipicker
  left_end_model=omnipicker
  right_end_error=0
  left_end_error=0
```

No physical gripper or robot motion was executed by Codex for this validation.
The next operator action can be rerunning normal A.

## Latest Update: parallel gripper path is rejected; restored original right-left timing

David later observed the same physical gripper mismatch again: the Gateway JSON
could report both gripper calls as successful, but one real gripper did not
close. Treat that field observation as the source of truth. The threaded
`parallel_both` implementation is therefore not acceptable for the WXF demo.

Rechecked original WXF code showed the gripper scripts were never a true single
simultaneous GDK call:

```text
Robot/move_ee_pose_close_2.py:
  right_tool target 0.0
  sleep 0.05
  left_tool target 0.0

Robot/move_ee_pose_open_2.py:
  right_tool target -0.785
  sleep 0.02
  left_tool target -0.785

yolo/move_ee_pose_open_05.py:
  right_tool target -0.05
  sleep 0.02
  left_tool target -0.05
```

Final deployed behavior now matches that original order while keeping the MQTT
service model:

```text
same-target open/close:
  still one MQTT task with side=both
  Gateway executes right_tool first
  Gateway waits the script's original delay
  Gateway executes left_tool second
  result gripper.execution_mode=sequential_original

close_2 delay=0.05
open_2 delay=0.02
open_05 delay=0.02
right_half delay=0.02
```

Patched:

```text
/data/g2_industrial_gateway/current/g2_industrial_gateway/gdk_live_backend.py
/data/wxf/wxf/mqtt_gateway_workspace_20260624/mqtt_common/mqtt_common.py
```

Backups:

```text
/data/g2_industrial_gateway/backups/gripper_original_right_left_20260627_122050/gdk_live_backend.py
/data/wxf/wxf/mqtt_gateway_workspace_20260624/backups/gripper_original_right_left_20260627_122100/mqtt_common.py
```

Validated without live motion:

```text
py_compile passed on deployed Gateway and MQTT wrapper files.

mock Robot/move_ee_pose_close_2.py:
  mode=mock
  side=both
  inter_side_delay_s=0.05
  executed=false

mock Robot/move_ee_pose_open_2.py:
  mode=mock
  side=both
  inter_side_delay_s=0.02
  executed=false

gdk.read_whole_body_status:
  state=DONE
  right_end_model=omnipicker
  left_end_model=omnipicker
  right_end_error=0
  left_end_error=0

ee.preflight side=both:
  state=DONE
  ok=true
  problems=[]
```

Gateway services are restarted and active. Do not re-enable `parallel_both` for
the demo unless a real dual-gripper GDK batch API is found and physically
validated.

## Live Validation: A full run after gripper original-order fix

David reran A from the beginning after the gripper fix.

```text
command:
  cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
  ./run_fast_live_script.sh yolo/task_all_pick_a.py --execute

log:
  /data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/20260627/20260627_122626_fast_live_script_yolo_task_all_pick_a.py_680143.log

finished_at:
  2026-06-27 12:28:12 CST

exit_code:
  0
```

Key gripper evidence:

```text
step 01 open:
  command=gripper.open
  side=both
  inter_side_delay_s=0.02
  execution_mode=sequential_original
  parallel_both=false
  calls=[right:right_tool:0,left:left_tool:0]

step 13 close:
  command=gripper.close
  side=both
  inter_side_delay_s=0.05
  execution_mode=sequential_original
  parallel_both=false
  calls=[right:right_tool:0,left:left_tool:0]
```

Other key action evidence:

```text
waist correction:
  state=DONE
  delta_rad=-0.006992653589793285

nav waypoints observed:
  waypoint 2 DONE final_state=9
  waypoint 3 DONE final_state=9
  waypoint 5 DONE final_state=9
  waypoint 6 DONE final_state=9
  waypoint 9 DONE final_state=9
  waypoint 10 DONE final_state=9
  final move-put1 internal nav entry DONE final_state=9
```

Step timing:

```text
01 0.489s  Robot/move_ee_pose_open_2.py
02 1.018s  BOX_528_1/move_arm_by_json_grab_delever.py
03 17.206s BOX_528_1/move-pick1.py
04 2.004s  intro TTS
05 3.281s  cam_get_head.py
06 8.493s  yolo_depth.py
07 0.757s  correct_waist.py
08 3.119s  cam_get_head.py
09 8.569s  yolo_depth.py
10 2.612s  BOX_528_1/move_arm_by_json_grab_1st.py
11 4.047s  BOX_528_1/offset_move_push_grab.py
12 2.024s  TTS 抓取工件
13 1.026s  Robot/move_ee_pose_close_2.py
14 4.031s  BOX_528_1/offset_move_up.py
15 2.025s  BOX_528_1/offset_move_pull.py
16 7.178s  BOX_528_1/move-adjust1.py
17 1.971s  TTS 将运行到A件的放置位
18 33.413s BOX_528_1/move-put1.py
19 2.797s  BOX_528_1/move_arm_by_json_grab_delever.py
```

Codex only monitored logs during this validation. David performed the live run.

## Live Monitor: full A/B place-pick cycle and MQTT adapter timeout fix

David then ran the broader flow while Codex monitored only logs.

Main successful logs observed:

```text
20260627_122626_fast_live_script_yolo_task_all_pick_a.py_680143.log  exit_code=0
20260627_122824_fast_live_script_yolo_task_all_place_a.py_691856.log exit_code=0
20260627_122936_fast_live_script_yolo_task_all_pick_b.py_699046.log  exit_code=0
20260627_123120_fast_live_script_yolo_task_all_place_b.py_709785.log exit_code=0
20260627_123242_fast_live_script_yolo_task_all_pick_a.py_717841.log  exit_code=0
20260627_123504_fast_live_script_yolo_task_all_pick_a.py_731261.log  exit_code=0
20260627_123714_fast_live_script_yolo_task_all_place_a.py_742172.log exit_code=0
20260627_123841_fast_live_script_yolo_task_all_pick_a.py_749068.log  exit_code=0
20260627_124337_fast_live_script_yolo_task_all_pick_a.py_772966.log  exit_code=0
20260627_124520_fast_live_script_yolo_task_all_place_a.py_781299.log exit_code=0
20260627_124759_fast_live_script_yolo_task_all_pick_a.py_793673.log  exit_code=0
20260627_125005_fast_live_script_yolo_task_all_place_a.py_803841.log exit_code=0
```

Gripper evidence across the monitored runs:

```text
same-target open:
  side=both
  delay=0.02
  execution_mode=sequential_original
  parallel_both=false
  calls=[right:right_tool:0,left:left_tool:0]

same-target close:
  side=both
  delay=0.05
  execution_mode=sequential_original
  parallel_both=false
  calls=[right:right_tool:0,left:left_tool:0]
```

No later monitored run showed the old threaded `parallel_both=true` gripper
path.

Failures observed and handled:

```text
20260627_124105_fast_live_script_yolo_task_all_pick_a.py_760536.log
  failed at step 07 correct_waist.py
  MQTT result error:
    {"event": "http_gateway_runtime_error", "error": "TimeoutError: timed out"}

  HTTP gateway task inspection showed the real waist task later completed DONE:
    task_id=waist-move_named_pose-760605-1782535301843-e0c7c0f0
    started_at=2026-06-27T04:41:41.849032+00:00
    finished_at=2026-06-27T04:41:48.495992+00:00
    elapsed about 6.65s

  Root cause:
    MQTT adapter's HTTP client had a fixed 5.0s socket timeout while the WXF
    task timeout was 15.0s. The adapter reported failure before the HTTP gateway
    finished the task.

20260627_124230_fast_live_script_yolo_task_all_pick_a.py_767104.log
  failed at move-pick1.py
  nav waypoint 2 error:
    RuntimeError: navigation did not start: state=7, message=Task State

  Later reruns passed this same section.
```

Patch deployed for the MQTT adapter timeout:

```text
remote file:
  /data/g2_industrial_gateway/current/g2_industrial_gateway/mqtt_bridge.py

backup:
  /data/g2_industrial_gateway/backups/mqtt_http_task_timeout_20260627_124623/mqtt_bridge.py

local source also patched:
  g2_industrial_gateway/mqtt_bridge.py
```

Patch behavior:

```text
HttpGatewayClient.submit_task(payload) now uses payload["timeout_s"] + 5.0s
for the HTTP socket timeout, while retaining the old 5.0s minimum for short
requests.
```

Validation:

```text
python3 -m py_compile /tmp/g2_mqtt_bridge.py
python3 -m py_compile /data/g2_industrial_gateway/current/g2_industrial_gateway/mqtt_bridge.py
python3 -m py_compile g2_industrial_gateway/mqtt_bridge.py

Restarted only:
  g2-industrial-gateway-mqtt.service

Did not restart:
  g2-industrial-gateway.service
  GDK live HTTP gateway process/session

Post-restart:
  g2-industrial-gateway.service active
  g2-industrial-gateway-mqtt.service active

Mock validation:
  G2_WXF_GATEWAY_MODE=mock G2_WXF_GATEWAY_PREFLIGHT=skip python3 yolo/correct_waist.py
  state=DONE
  mode=mock
  executed=false
```

The monitor script was stopped after no new `task_all_*` logs appeared for
several heartbeat intervals. Codex did not execute any live robot motion; David
ran the live scripts.

## 2026-06-27 13:30 CST Update: pick_a step 01 MQTT result timeout repaired

Latest failing command from David:

```text
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_fast_live_script.sh yolo/task_all_pick_a.py --execute
```

Observed failure:

```text
step 01 Robot/move_ee_pose_open_2.py
TimeoutError: timed out waiting for MQTT result for gripper-open-994873-1782538245218-75569e00
TimeoutError: timed out waiting for MQTT result for gripper-open-996762-1782538267302-67da10f7
```

Read-only backend task state showed this was not a failed gripper command.
Both HTTP tasks completed DONE with:

```text
requested_side=both
execution_mode=sequential_original
parallel_both=false
calls=[right:right_tool:0,left:left_tool:0]
```

Root cause:

```text
WXF script-side gripper MQTT wait timeout was fixed at 5.0s. The backend did
finish the gripper task, but the caller could time out first when the gateway
queue/result path took longer than 5 seconds.
```

Patch:

```text
remote:
  /data/wxf/wxf/mqtt_gateway_workspace_20260624/mqtt_common/mqtt_common.py

backup:
  /data/wxf/wxf/mqtt_gateway_workspace_20260624/backups/gripper_mqtt_timeout_20260627_1336/mqtt_common.py

change:
  run_gripper() now uses env G2_WXF_FAST_GRIPPER_TIMEOUT_S, default 15.0s.
```

Important behavior retained:

```text
same-target left/right gripper commands still submit one MQTT task:
  side=both
  single_mqtt_task_for_both_grippers=true

Gateway still executes original WXF order:
  right then left

It is not using threaded parallel_both.
```

Validation:

```text
python3 -m py_compile /data/wxf/wxf/mqtt_gateway_workspace_20260624/mqtt_common/mqtt_common.py

G2_WXF_GATEWAY_MODE=mock G2_WXF_GATEWAY_PREFLIGHT=skip \
  python3 Robot/move_ee_pose_open_2.py

mock validation result:
  state=DONE
  mode=mock
  executed=false
  request.timeout_s=15.0
  args.side=both
  args.inter_side_delay_s=0.02
```

Next live operator action:

```text
David can rerun task_all_pick_a.py from the top.
Monitor the first gripper step. If it fails again, inspect the HTTP task_id
before changing gripper semantics; the last two failures were caller wait
timeouts while the backend command itself completed DONE.
```

Codex did not execute live robot motion for this repair.
