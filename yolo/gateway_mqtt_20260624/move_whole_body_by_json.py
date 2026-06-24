#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Submit the original whole-body JSON as gateway dry-run subtasks."""

from __future__ import annotations

import argparse
import os

from gateway_compat import (
    default_json_path,
    extract_values,
    load_json,
    pose_name_from_path,
    rad_to_deg,
    require_done,
    safe_motion_mode,
    submit_task,
)


HEAD_JOINT_KEYS = ["idx11_head_joint1", "idx12_head_joint2", "idx13_head_joint3"]
WAIST_JOINT_KEYS = [
    "idx01_body_joint1",
    "idx02_body_joint2",
    "idx03_body_joint3",
    "idx04_body_joint4",
    "idx05_body_joint5",
]
LEFT_ARM_JOINT_KEYS = [
    "idx21_arm_l_joint1",
    "idx22_arm_l_joint2",
    "idx23_arm_l_joint3",
    "idx24_arm_l_joint4",
    "idx25_arm_l_joint5",
    "idx26_arm_l_joint6",
    "idx27_arm_l_joint7",
]
RIGHT_ARM_JOINT_KEYS = [
    "idx61_arm_r_joint1",
    "idx62_arm_r_joint2",
    "idx63_arm_r_joint3",
    "idx64_arm_r_joint4",
    "idx65_arm_r_joint5",
    "idx66_arm_r_joint6",
    "idx67_arm_r_joint7",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", nargs="?", default=None)
    parser.add_argument("--sync", action="store_true", help="保留原参数；当前仍拆成网关子任务 dry-run")
    parser.add_argument("--mode", default=os.environ.get("G2_YOLO_GATEWAY_MODE", "dry_run"))
    parser.add_argument("--timeout-s", type=float, default=20.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mode = safe_motion_mode(args.mode)
    json_path = args.json_path or default_json_path("whole_body.json", "../positions/arm_default.json")
    data = load_json(json_path)

    head = extract_values(data, HEAD_JOINT_KEYS)
    waist = extract_values(data, WAIST_JOINT_KEYS)
    left_arm = extract_values(data, LEFT_ARM_JOINT_KEYS)
    right_arm = extract_values(data, RIGHT_ARM_JOINT_KEYS)
    pose = pose_name_from_path(json_path, "whole_body_json")

    results = [
        submit_task(
            "head.set_pan_tilt",
            {
                "yaw_deg": rad_to_deg(head[0]),
                "pitch_deg": rad_to_deg(head[1]),
                "head_joint_names": HEAD_JOINT_KEYS,
                "head_rad": head,
                "source_json": json_path,
                "sync_requested": bool(args.sync),
            },
            mode=mode,
            timeout_s=5.0,
        ),
        submit_task(
            "waist.move_named_pose",
            {
                "pose": f"{pose}_waist",
                "source_json": json_path,
                "waist_joint_names": WAIST_JOINT_KEYS,
                "joint_positions_rad": waist,
                "joint_velocities_radps": [0.3] * 5,
                "sync_requested": bool(args.sync),
            },
            mode=mode,
            timeout_s=15.0,
        ),
        submit_task(
            "arm.move_named_pose",
            {
                "pose": f"{pose}_arms",
                "source_json": json_path,
                "left_arm_joint_names": LEFT_ARM_JOINT_KEYS,
                "right_arm_joint_names": RIGHT_ARM_JOINT_KEYS,
                "left_arm_rad": left_arm,
                "right_arm_rad": right_arm,
                "joint_positions_rad": left_arm + right_arm,
                "joint_velocities_radps": [0.2] * 14,
                "time_scale_s": 2,
                "sync_requested": bool(args.sync),
            },
            mode=mode,
            timeout_s=args.timeout_s,
        ),
    ]
    for result in results:
        require_done(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
