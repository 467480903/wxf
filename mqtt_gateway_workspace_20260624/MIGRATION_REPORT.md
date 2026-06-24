# WXF MQTT/Gateway workspace

Remote target directory:

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624
```

Original source directory was copied from:

```text
/data/wxf/wxf
```

Original files were not modified.

## First checks

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 test_mqtt_migration.py
python3 gateway_mqtt_client.py --command gdk.read_power_state --mode read_only --args-json '{}' --timeout-s 10
```

## Four yolo controllers

Plan only:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 task_all.py
python3 task_all_pick_b.py
python3 task_all_place_b.py
python3 task_all_pull_car.py
```

Execute only migrated dry-run wrappers:

```bash
python3 task_all_pick_b.py --execute
```

All motion-like wrappers default to Gateway `dry_run/mock`; live mode is rejected in this workspace.

## Converted files

- `BOX_528_1/_chassis_retreat.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/_chassis_rotate.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/chassis_controller.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/chassis_data_recorder.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/clean_navi.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/end_effector_controller.py`: ee_controller_shim - offset dry-run class
- `BOX_528_1/get_chassis_speed.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/move copy.py`: nav_forward - (2.0, 1.0)
- `BOX_528_1/move-adjust1.py`: nav_waypoints - [{"index": 5, "high_precision": false}, {"index": 6, "high_precision": false}]
- `BOX_528_1/move-adjust2.py`: nav_waypoints - [{"index": 15, "high_precision": false}, {"index": 14, "high_precision": false}]
- `BOX_528_1/move-back.py`: nav_waypoints - [{"index": 9, "high_precision": false}, {"index": 8, "high_precision": false}, {"index": 6, "high_precision": false}, {"index": 0, "high_precision": false}]
- `BOX_528_1/move-back1.py`: nav_waypoints - [{"index": 11, "high_precision": false}, {"index": 10, "high_precision": false}, {"index": 9, "high_precision": false}, {"index": 13, "high_precision": false}, {"index": 0, "high_precision": false}]
- `BOX_528_1/move-pick1.py`: nav_waypoints - [{"index": 1, "high_precision": false}, {"index": 2, "high_precision": false}, {"index": 3, "high_precision": false}]
- `BOX_528_1/move-pick2.py`: nav_waypoints - [{"index": 11, "high_precision": false}, {"index": 13, "high_precision": false}, {"index": 14, "high_precision": false}, {"index": 15, "high_precision": false}, {"index": 17, "high_precision": false}]
- `BOX_528_1/move-put1.py`: nav_waypoints - [{"index": 7, "high_precision": false}, {"index": 8, "high_precision": false}, {"index": 9, "high_precision": false}, {"index": 10, "high_precision": false}, {"index": 11, "high_precision": false}, {"index": 12, "high_precision": false}]
- `BOX_528_1/move-put2.py`: nav_waypoints - [{"index": 19, "high_precision": false}, {"index": 20, "high_precision": false}, {"index": 21, "high_precision": false}, {"index": 22, "high_precision": false}, {"index": 23, "high_precision": false}, {"index": 25, "high_precision": false}]
- `BOX_528_1/move-ready1.py`: nav_waypoints - [{"index": 0, "high_precision": false}]
- `BOX_528_1/move.py`: nav_waypoints - [{"index": 8, "high_precision": false}, {"index": 8, "high_precision": true}]
- `BOX_528_1/move_arm_by_json_default.py`: arm_json - /data/wxf/wxf/positions/arm_default.json
- `BOX_528_1/move_arm_by_json_grab_1st.py`: arm_json - ../positions/arm_position_to_grab_1.json
- `BOX_528_1/move_arm_by_json_grab_above_2.py`: arm_json - /data/hondagys/wxf/positions/arm_position_to_grab_2.json
- `BOX_528_1/move_arm_by_json_grab_above_第一根.py`: arm_json - /data/hondagys/wxf/positions/arm_position_to_grab_第一根.json
- `BOX_528_1/move_arm_by_json_grab_above_第七根.py`: arm_json - /data/wxf/wxf/positions/arm_position_to_grab_第七根.json
- `BOX_528_1/move_arm_by_json_grab_above_第三根.py`: arm_json - /data/wxf/wxf/positions/arm_position_to_grab_第三根.json
- `BOX_528_1/move_arm_by_json_grab_above_第二根.py`: arm_json - /data/wxf/wxf/positions/arm_position_to_grab_第二根.json
- `BOX_528_1/move_arm_by_json_grab_above_第五根.py`: arm_json - /data/wxf/wxf/positions/arm_position_to_grab_第五根.json
- `BOX_528_1/move_arm_by_json_grab_above_第六根.py`: arm_json - /data/wxf/wxf/positions/arm_position_to_grab_第六根.json
- `BOX_528_1/move_arm_by_json_grab_above_第四根.py`: arm_json - /data/wxf/wxf/positions/arm_position_to_grab_第四根.json
- `BOX_528_1/move_arm_by_json_grab_delever.py`: arm_json - ../positions/arm_position_to_grab_2.json
- `BOX_528_1/move_arm_by_json_grab_推车.py`: arm_json - /data/本田现场gys/wxf/bengtian_backup_20260608_081250/wxf/positions/arm_position_to_grab_推车.json
- `BOX_528_1/move_arm_by_json_grab_放.py`: arm_json - ../positions/arm_position_to_grab_放.json
- `BOX_528_1/move_ee_pose_close_2.py`: gripper - close
- `BOX_528_1/move_ee_pose_open_2.py`: gripper - open
- `BOX_528_1/move_gopullcar.py`: nav_waypoints - [{"index": 25, "high_precision": false}, {"index": 23, "high_precision": false}, {"index": 21, "high_precision": false}, {"index": 0, "high_precision": false}, {"index": 1, "high_precision": false}, {"index": 29, "high_precision": false}, {"index": 27, "high_precision": false}, {"index": 26, "high_precision": false}]
- `BOX_528_1/move_pullcar.py`: nav_waypoints - [{"index": 26, "high_precision": false}, {"index": 27, "high_precision": false}, {"index": 28, "high_precision": false}, {"index": 29, "high_precision": false}, {"index": 30, "high_precision": false}, {"index": 31, "high_precision": false}]
- `BOX_528_1/move_waist_by_json_default.py`: waist_json - /data/wxf/wxf/positions/arm_default.json
- `BOX_528_1/move_waist_by_json_down.py`: waist_json - /data/bengtian/wxf/positions/waist_position_to_down.json
- `BOX_528_1/move_waist_by_json_up.py`: waist_json - /data/wxf/wxf/positions/waist_position_to_up.json
- `BOX_528_1/normal_navi.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/offset_move_.py`: ee_offset - ((0.0, -0.03, 0.0), (0.0, 0.03, 0.0))
- `BOX_528_1/offset_move_down.py`: ee_offset - ((0.0, 0.0, -0.14), (0.0, 0.0, -0.14))
- `BOX_528_1/offset_move_pull.py`: ee_offset - ((-0.16, 0.0, 0.0), (-0.16, 0.0, 0.0))
- `BOX_528_1/offset_move_pull小车.py`: ee_offset - ((0.0, -0.04, 0.0), (0.0, 0.04, 0.0))
- `BOX_528_1/offset_move_pull推车.py`: ee_offset - ((0.0, -0.04, 0.0), (0.0, 0.04, 0.0))
- `BOX_528_1/offset_move_push_grab.py`: ee_offset - ((0.09, 0.0, 0.0), (0.09, 0.0, 0.0))
- `BOX_528_1/offset_move_up.py`: ee_offset - ((0.0, 0.0, 0.2), (0.0, 0.0, 0.2))
- `BOX_528_1/pnc_example.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/rack_hybrid_docking_package/rack_hybrid_docking.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/rack_hybrid_docking_package/rack_lidar_docking.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/rack_hybrid_docking_package/rack_radar_docking.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/robot_controller.py`: robot_controller_shim - nav dry-run class
- `BOX_528_1/set_chassis_speed.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/show_chassis_speed.py`: blocked_unsupported - direct SDK source replaced
- `BOX_528_1/本田现场总控.py`: sequence - 13 steps
- `BOX_528_1/本田现场总控第一根.py`: sequence - 9 steps
- `Robot/PointDownController.py`: blocked_unsupported - direct SDK source replaced
- `Robot/SymmetricMove.py`: blocked_unsupported - direct SDK source replaced
- `Robot/current_postion_up.py`: blocked_unsupported - direct SDK source replaced
- `Robot/end_effector_pose_control.py`: blocked_unsupported - direct SDK source replaced
- `Robot/end_effector_pose_control_2.py`: blocked_unsupported - direct SDK source replaced
- `Robot/end_effector_pose_control_3.py`: blocked_unsupported - direct SDK source replaced
- `Robot/end_effector_pose_control_4.py`: blocked_unsupported - direct SDK source replaced
- `Robot/end_effector_pose_control_5.py`: blocked_unsupported - direct SDK source replaced
- `Robot/get_chassis_power_state.py`: read_only - gdk.read_power_state
- `Robot/get_chest_power_state.py`: read_only - gdk.read_power_state
- `Robot/get_end_state.py`: read_only - ee.preflight
- `Robot/get_joint_states.py`: read_only - gdk.read_joint_states
- `Robot/get_motion_control_status.py`: read_only - gdk.read_motion_status
- `Robot/get_whole_body_status.py`: read_only - gdk.read_whole_body_status
- `Robot/mc_example.py`: blocked_unsupported - direct SDK source replaced
- `Robot/move_arm_by_json.py`: arm_json - /data/wxf/wxf/positions.json
- `Robot/move_arm_joint.py`: arm_named - fixed list
- `Robot/move_arm_joint_box_above.py`: arm_named - fixed list
- `Robot/move_arm_joint_box_grab.py`: arm_named - fixed list
- `Robot/move_arm_joint_default.py`: arm_named - fixed list
- `Robot/move_ee_pose.py`: blocked_unsupported - direct SDK source replaced
- `Robot/move_ee_pose_close_2.py`: gripper - close
- `Robot/move_ee_pose_open_2.py`: gripper - open
- `Robot/move_head_joint.py`: head - fixed list
- `Robot/move_waist_joint.py`: waist_named - fixed list
- `Robot/move_waist_joint_box.py`: waist_named - fixed list
- `Robot/move_waist_joint_default.py`: waist_named - fixed list
- `Robot/move_with_yolo.py`: blocked_unsupported - direct SDK source replaced
- `Robot/offset_move.py`: ee_offset - ((0.0, 0.0, -0.01), (0.0, 0.0, -0.01))
- `Robot/relative_move.py`: blocked_unsupported - direct SDK source replaced
- `Robot/right_to_left.py`: arm_named - fixed list
- `Robot/robot_p_r.py`: blocked_unsupported - direct SDK source replaced
- `Robot/yolo_move.py`: blocked_unsupported - direct SDK source replaced
- `yolo/00.py`: ee_offset - demo down 0.02
- `yolo/all.py`: sequence - 16 steps
- `yolo/cam_get_head.py`: camera_http - snapshot
- `yolo/camera_web_viewer.py`: camera_http - viewer shim
- `yolo/camera_web_viewer_with_save.py`: camera_http - viewer shim
- `yolo/correct_waist.py`: waist_correction - yolo_depth_result
- `yolo/move_arm_by_json.py`: arm_json - argv json
- `yolo/move_ee_pose_open_05.py`: gripper - open -0.05
- `yolo/move_ee_pose_right_half.py`: gripper - right -0.05 left 0
- `yolo/move_whole_body_by_json.py`: whole_body_json - head/waist/arms
- `yolo/offset_move_common.py`: ee_offset_common - dynamic offset helper
- `yolo/record_camera.py`: camera_http - record
- `yolo/task_all.py`: sequence - 31 steps
- `yolo/task_all_pick_b.py`: sequence - 10 steps
- `yolo/task_all_place_b.py`: sequence - 29 steps
- `yolo/task_all_pull_car.py`: sequence - 7 steps
- `BOX_528_1/move-gopullcar.py`: alias - from move_gopullcar.py
- `BOX_528_1/move-pullcar.py`: alias - from move_pullcar.py
