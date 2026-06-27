# G2A WXF MQTT Run Monitor - 2026-06-27 14:08 CST

Scope: read-only monitoring of David's live run on `agi@10.185.207.253`.
Codex did not execute robot motion commands in this monitoring pass.

Workspace:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624
```

## Overall Result

Latest monitored full chain:

```text
14:08:16-14:10:08  yolo/task_all_pick_a.py   exit_code=0  failed_lines=0  steps=19/19
14:10:12-14:11:11  yolo/task_all_place_a.py  exit_code=0  failed_lines=0  steps=21/21
14:11:33-14:13:16  yolo/task_all_pick_b.py   exit_code=0  failed_lines=0  steps=12/12
14:13:20-14:14:30  yolo/task_all_place_b.py  exit_code=0  failed_lines=0  steps=29/29
```

No `step failed`, `Traceback`, `TimeoutError`, `RuntimeError`,
`"state": "FAILED"`, or `exit_code: 1` was found in these four latest logs.

Latest logs:

```text
run_logs/20260627/20260627_140816_fast_live_script_yolo_task_all_pick_a.py_1180604.log
run_logs/20260627/20260627_141012_fast_live_script_yolo_task_all_place_a.py_1189643.log
run_logs/20260627/20260627_141133_fast_live_script_yolo_task_all_pick_b.py_1195984.log
run_logs/20260627/20260627_141320_fast_live_script_yolo_task_all_place_b.py_1204105.log
```

## Gripper Evidence

The latest pick flows did not miss either gripper side.

```text
pick_a open:  requested=both calls=[right:0@-0.785, left:0@-0.785]
pick_a close: requested=both calls=[right:0@0.0, left:0@0.0]

pick_b open:  requested=both calls=[right:0@-0.785, left:0@-0.785]
pick_b close: requested=both calls=[right:0@0.0, left:0@0.0]
```

The place flows include the expected single-side and both-side open commands.
All returned `result=0`.

```text
place_a open right: calls=[right:0@-0.05]
place_a open left:  calls=[left:0@0.0]
place_a open both:  calls=[right:0@-0.05, left:0@-0.05]
place_a open both:  calls=[right:0@-0.785, left:0@-0.785]

place_b close both: calls=[right:0@0.0, left:0@0.0]
place_b open right: calls=[right:0@-0.05]
place_b open left:  calls=[left:0@0.0]
place_b open both:  calls=[right:0@-0.05, left:0@-0.05]
place_b open both:  calls=[right:0@-0.785, left:0@-0.785]
```

Important note: the gateway result still reports
`execution_mode=sequential_original`, so this is a single MQTT task with both
sides requested, but the backend executes the two low-level GDK calls in
original right/left order rather than by parallel threads. If the physical
motion still appears visibly unsynchronized, the next fix should target that
backend execution strategy, not MQTT delivery or timeout handling.

## Vision And Correction

`task_all_pick_a.py`:

```text
first vision:  detected a=3,b=0,c=0,d=0  offset=-0.01 px  angle=3.1113 rad
second vision: detected a=2,b=0,c=0,d=0  offset= 8.12 px  angle=-0.0033 rad
```

`task_all_place_a.py`:

```text
first vision:  detected a=1,b=1,c=0,d=0  offset=-15.38 px  angle=-0.0248 rad
second vision: detected a=1,b=1,c=0,d=0  offset= -7.47 px  angle=-0.0086 rad
```

`task_all_place_b.py`:

```text
first vision:  detected a=1,b=1,c=0,d=0  offset=-1.82 px  angle=-0.0009 rad
second vision: detected a=1,b=1,c=0,d=0  offset=-1.59 px  angle= 0.0003 rad
```

`task_all_pick_b.py` does not run YOLO in the current task sequence; it uses
the scripted pick/place navigation and arm/EE motions.

## Step Timing

### `task_all_pick_a.py`

```text
01  0.525s  Robot/move_ee_pose_open_2.py
02  1.002s  BOX_528_1/move_arm_by_json_grab_delever.py
03 23.091s  BOX_528_1/move-pick1.py
04  1.972s  interaction/play_tts_cli.py
05  3.181s  cam_get_head.py
06  9.101s  yolo_depth.py holes.pt 1
07  1.169s  correct_waist.py
08  3.132s  cam_get_head.py
09  8.641s  yolo_depth.py holes.pt 1
10  3.618s  BOX_528_1/move_arm_by_json_grab_1st.py
11  4.012s  BOX_528_1/offset_move_push_grab.py
12  2.009s  interaction/play_tts_cli.py
13  1.002s  Robot/move_ee_pose_close_2.py
14  4.010s  BOX_528_1/offset_move_up.py
15  2.008s  BOX_528_1/offset_move_pull.py
16  7.067s  BOX_528_1/move-adjust1.py
17  2.979s  interaction/play_tts_cli.py
18 30.161s  BOX_528_1/move-put1.py
19  3.824s  BOX_528_1/move_arm_by_json_grab_delever.py
```

### `task_all_place_a.py`

```text
01  3.866s  move_whole_body_by_json.py ../positions/pick_standby.json
02  2.012s  interaction/play_tts_cli.py
03  3.182s  cam_get_head.py
04  8.792s  yolo_depth.py shelf.pt
05  1.090s  correct_waist.py
06  3.168s  cam_get_head.py
07  8.655s  yolo_depth.py shelf.pt
08  1.238s  move_ee_pose_right_half.py
09  4.204s  move_arm_by_json.py ../positions/place_1.json
10  2.815s  move_arm_by_json.py ../positions/place_2.json
11  2.009s  offset_move_horizon.py
12  2.005s  offset_move_downward_004.py
13  1.003s  move_ee_pose_open_05.py
14  1.003s  offset_move_downward_002.py
15  1.005s  offset_move_forward_001.py
16  2.005s  offset_move_vertical.py
17  1.004s  offset_move_downward_004.py
18  1.003s  offset_move_downward_004.py
19  1.006s  Robot/move_ee_pose_open_2.py
20  2.004s  offset_move_pull_back.py
21  6.415s  move_whole_body_by_json.py ../positions/pick_standby.json
```

### `task_all_pick_b.py`

```text
01 34.738s  BOX_528_1/move-pick2.py
02  0.976s  Robot/move_ee_pose_open_2.py
03  2.639s  BOX_528_1/move_arm_by_json_grab_1st.py
04  1.003s  BOX_528_1/offset_move_downpickb.py
05  4.024s  BOX_528_1/offset_move_push_grab_b.py
06  1.004s  Robot/move_ee_pose_close_2.py
07  5.017s  BOX_528_1/offset_move_up.py
08  4.018s  BOX_528_1/offset_move_pull.py
09  3.007s  interaction/play_tts_cli.py
10  8.068s  BOX_528_1/move-adjust2.py
11 32.244s  BOX_528_1/move-put2.py
12  5.886s  move_whole_body_by_json.py ../positions/pick_standby.json
```

### `task_all_place_b.py`

```text
01  0.676s  Robot/move_ee_pose_close_2.py
02  3.017s  move_whole_body_by_json.py ../positions/pick_standby.json
03  2.009s  interaction/play_tts_cli.py
04  3.152s  cam_get_head.py
05  8.733s  yolo_depth.py shelf.pt 1
06  0.001s  cp yolo_depth_result.json yolo_depth_result_2.json
07  1.211s  correct_waist.py
08  3.208s  cam_get_head.py
09  9.190s  yolo_depth.py shelf.pt 1
10  0.002s  cp yolo_depth_result.json yolo_depth_result_3.json
11  1.721s  move_ee_pose_right_half.py
12  7.264s  move_whole_body_by_json.py ../positions/place_b_2.json
13  5.644s  move_whole_body_by_json.py ../positions/place_b_3.json
14  0.001s  mv yolo_depth_result_2.json yolo_depth_result.json
15  1.005s  correct_waist.py
16  2.554s  move_arm_by_json.py ../positions/place_b_4.json
17  1.006s  offset_move_left_002.py
18  2.535s  move_arm_by_json.py ../positions/place_b_5.json
19  0.001s  mv yolo_depth_result_3.json yolo_depth_result.json
20  1.007s  offset_move_horizon_b.py
21  2.010s  offset_move_vertical_b.py
22  2.010s  offset_move_downward_002.py
23  1.006s  offset_move_downward_002.py
24  1.006s  move_ee_pose_open_05.py
25  1.005s  offset_move_downward_002.py
26  1.005s  offset_move_downward_002.py
27  1.011s  Robot/move_ee_pose_open_2.py
28  2.008s  offset_move_pull_back.py
29  5.364s  move_whole_body_by_json.py ../positions/pick_standby.json
```

## Observations

- MQTT task execution is no longer showing HTTP timeout failures in these
  latest runs.
- Timeline rows in the logs say `task accepted by gateway`, confirming the new
  embedded MQTT service path is active.
- Chassis navigation dominates the pick timing:
  - A pick `move-pick1.py`: 23.091s
  - A pick `move-put1.py`: 30.161s
  - B pick `move-pick2.py`: 34.738s
  - B pick `move-put2.py`: 32.244s
- Arm and EE fast inline actions are mostly 1-5s and stayed consistent with
  the configured demo speeds (`arm=0.2`, `waist=0.3`, `head=0.3`).
- No evidence of dropped MQTT result or PNC read timeout was found in these
  four latest logs.
