#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Submit the original 14-joint arm JSON as a gateway dry-run task."""

from __future__ import annotations

import argparse
import os

from gateway_compat import extract_values, load_json, pose_name_from_path, require_done, safe_motion_mode, submit_task


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
    parser.add_argument("json_path")
    parser.add_argument("--mode", default=os.environ.get("G2_YOLO_GATEWAY_MODE", "dry_run"))
    parser.add_argument("--timeout-s", type=float, default=20.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mode = safe_motion_mode(args.mode)
    data = load_json(args.json_path)
    left_arm = extract_values(data, LEFT_ARM_JOINT_KEYS)
    right_arm = extract_values(data, RIGHT_ARM_JOINT_KEYS)
    arm_positions = left_arm + right_arm

    result = submit_task(
        "arm.move_named_pose",
        {
            "pose": pose_name_from_path(args.json_path, "arm_json"),
            "source_json": args.json_path,
            "left_arm_joint_names": LEFT_ARM_JOINT_KEYS,
            "right_arm_joint_names": RIGHT_ARM_JOINT_KEYS,
            "left_arm_rad": left_arm,
            "right_arm_rad": right_arm,
            "joint_positions_rad": arm_positions,
            "joint_velocities_radps": [0.2] * 14,
            "time_scale_s": 2,
        },
        mode=mode,
        timeout_s=args.timeout_s,
    )
    require_done(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
