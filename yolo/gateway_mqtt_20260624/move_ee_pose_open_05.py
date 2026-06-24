#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Submit the old double gripper-open command through gateway dry-run."""

from gateway_compat import require_done, safe_motion_mode, submit_task


def main() -> int:
    results = []
    for side in ("right", "left"):
        results.append(
            submit_task(
                "gripper.open",
                {
                    "side": side,
                    "target_position": -0.05,
                    "target_type": "omnipicker",
                    "source_script": "move_ee_pose_open_05.py",
                },
                mode=safe_motion_mode(),
                timeout_s=5.0,
            )
        )
    for result in results:
        require_done(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
