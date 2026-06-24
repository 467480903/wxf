#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Submit the YOLO slope waist correction as a gateway dry-run task."""

from __future__ import annotations

import os

from gateway_compat import SCRIPT_DIR, load_json, require_done, safe_motion_mode, submit_task


def main() -> int:
    result_path = SCRIPT_DIR / "yolo_depth_result.json"
    data = load_json(result_path)
    target_delta = float(data["slope"]["angle_rad"])
    print(f"从 {result_path} 读取 slope/angle_rad = {target_delta:.4f} rad")

    result = submit_task(
        "waist.move_named_pose",
        {
            "pose": "yolo_correct_waist_delta",
            "source_result_json": str(result_path),
            "target_joint": "idx05_body_joint5",
            "delta_rad": -target_delta,
            "original_target_delta_rad": target_delta,
            "joint_velocities_radps": [0.3] * 5,
            "note": "旧脚本先读取当前腰部，再让 idx05_body_joint5 减去 target_delta；这里把动作表达成网关任务参数。",
        },
        mode=safe_motion_mode(os.environ.get("G2_YOLO_GATEWAY_MODE", "dry_run")),
        timeout_s=15.0,
    )
    require_done(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
