#!/usr/bin/env python3
"""Standalone G2 gripper open/close control helper.

This tool is intentionally conservative:

* By default it is a dry-run planner and does not move the robot.
* Real gripper movement requires --execute.
* Live execution expects to run inside the WXF MQTT workspace, where the
  existing mqtt_common package can submit tasks to the 4090/G2 gateway.

Typical robot-side usage:

    cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
    source /home/agi/app/env.sh
    python3 tools/g2_gripper_control.py --action open --side both
    python3 tools/g2_gripper_control.py --action open --side both --execute
    python3 tools/g2_gripper_control.py --action close --side both --execute

The gateway returning DONE only proves the command path completed. It is not a
physical readback of the gripper position. Use visual confirmation or a future
readback hook before relying on this for closed-loop recovery logic.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


OPEN_POSITION = -0.785
HALF_OPEN_POSITION = -0.05
CLOSE_POSITION = 0.0
DEFAULT_TARGET_TYPE = "omnipicker"
DEFAULT_TIMEOUT_S = 15.0


@dataclass(frozen=True)
class GripperTask:
    command: str
    args: dict
    timeout_s: float


def _find_workspace_root(start: Path) -> Path | None:
    """Find a parent directory that contains the WXF mqtt_common package."""
    for parent in [start, *start.parents]:
        if (parent / "mqtt_common").is_dir():
            return parent
    return None


def _load_mqtt_common(workspace: Path | None):
    """Import submit_task/require_done from the deployed WXF workspace."""
    if workspace is None:
        workspace = _find_workspace_root(Path(__file__).resolve().parent)

    if workspace is not None:
        workspace_str = str(workspace)
        if workspace_str not in sys.path:
            sys.path.insert(0, workspace_str)

    try:
        from mqtt_common import require_done, submit_task  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on robot workspace
        searched = str(workspace) if workspace else "parents of this script"
        raise RuntimeError(
            "Cannot import mqtt_common. Run this script from the WXF MQTT "
            "workspace or pass --workspace /data/wxf/wxf/mqtt_gateway_workspace_20260624. "
            f"Searched: {searched}. Import error: {exc}"
        ) from exc

    return submit_task, require_done


def _position_for_action(action: str, position: float | None) -> float:
    if action == "open":
        return OPEN_POSITION
    if action == "half":
        return HALF_OPEN_POSITION
    if action == "close":
        return CLOSE_POSITION
    if action == "set":
        if position is None:
            raise ValueError("--position is required when --action set")
        return float(position)
    raise ValueError(f"unsupported action: {action}")


def _command_for_action(action: str, target_position: float) -> str:
    if action == "close":
        return "gripper.close"
    if action in {"open", "half"}:
        return "gripper.open"
    return "gripper.close" if target_position >= -0.001 else "gripper.open"


def _parse_order(order: str) -> list[str]:
    sides = [part.strip() for part in order.split(",") if part.strip()]
    if sorted(sides) != ["left", "right"]:
        raise ValueError("--order must contain exactly left and right, for example right,left")
    return sides


def build_tasks(args: argparse.Namespace) -> list[GripperTask]:
    target_position = _position_for_action(args.action, args.position)
    command = _command_for_action(args.action, target_position)

    base_args = {
        "target_position": target_position,
        "target_type": args.target_type,
        "source_script": "tools/g2_gripper_control.py",
        "fast_demo_path": True,
        "post_wait_s": args.post_wait_s,
    }

    if args.side == "both" and not args.split_both:
        task_args = {
            **base_args,
            "side": "both",
            "single_mqtt_task_for_both_grippers": True,
            "inter_side_delay_s": args.inter_side_delay_s,
        }
        return [GripperTask(command=command, args=task_args, timeout_s=args.timeout_s)]

    if args.side == "both":
        sides: Iterable[str] = _parse_order(args.order)
    else:
        sides = [args.side]

    tasks: list[GripperTask] = []
    for side in sides:
        task_args = {
            **base_args,
            "side": side,
            "single_mqtt_task_for_both_grippers": False,
            "inter_side_delay_s": args.inter_side_delay_s,
        }
        tasks.append(GripperTask(command=command, args=task_args, timeout_s=args.timeout_s))
    return tasks


def print_plan(tasks: list[GripperTask], *, mode: str, execute: bool) -> None:
    print(
        json.dumps(
            {
                "schema": "g2.gripper_control.plan.v1",
                "mode": mode,
                "execute": execute,
                "task_count": len(tasks),
                "tasks": [
                    {
                        "command": task.command,
                        "args": task.args,
                        "timeout_s": task.timeout_s,
                    }
                    for task in tasks
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def execute_tasks(args: argparse.Namespace, tasks: list[GripperTask]) -> int:
    workspace = Path(args.workspace).expanduser().resolve() if args.workspace else None
    submit_task, require_done = _load_mqtt_common(workspace)

    # Make the physical boundary explicit for the existing mqtt_common helpers.
    os.environ["G2_WXF_GATEWAY_MODE"] = "live"
    os.environ["G2_WXF_GATEWAY_CONFIRM_PHYSICAL"] = "1"

    for index, task in enumerate(tasks, start=1):
        print(f"[{index}/{len(tasks)}] submit {task.command} side={task.args.get('side')}")
        result = submit_task(
            task.command,
            task.args,
            mode="live",
            timeout_s=task.timeout_s,
        )
        require_done(result)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

        post_wait_s = float(task.args.get("post_wait_s") or 0.0)
        if post_wait_s > 0:
            time.sleep(post_wait_s)

        if args.inter_task_delay_s > 0 and index < len(tasks):
            time.sleep(args.inter_task_delay_s)

    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Control G2 omnipicker gripper open/close through the WXF MQTT gateway.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--action",
        choices=("open", "close", "half", "set"),
        required=True,
        help="Gripper action. set requires --position.",
    )
    parser.add_argument(
        "--side",
        choices=("left", "right", "both"),
        default="both",
        help="Which gripper to control.",
    )
    parser.add_argument(
        "--position",
        type=float,
        help="Target gripper position for --action set. open is negative, close is 0.0.",
    )
    parser.add_argument(
        "--target-type",
        default=DEFAULT_TARGET_TYPE,
        help="End-effector target type passed to the gateway.",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        help="Gateway task timeout.",
    )
    parser.add_argument(
        "--post-wait-s",
        type=float,
        default=0.8,
        help="Wait after each completed gripper task to let the physical gripper settle.",
    )
    parser.add_argument(
        "--inter-side-delay-s",
        type=float,
        default=0.05,
        help="Delay hint for sequential left/right commands.",
    )
    parser.add_argument(
        "--inter-task-delay-s",
        type=float,
        default=0.05,
        help="Local delay between split tasks.",
    )
    parser.add_argument(
        "--split-both",
        action="store_true",
        help="When side=both, submit right and left as separate tasks instead of one both-side task.",
    )
    parser.add_argument(
        "--order",
        default="right,left",
        help="Sequential order used only with --side both --split-both.",
    )
    parser.add_argument(
        "--workspace",
        help="Path to WXF MQTT workspace if this script is not run from inside it.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually submit live gripper tasks. Without this flag, only prints the plan.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        tasks = build_tasks(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    mode = "live" if args.execute else "dry-run"
    print_plan(tasks, mode=mode, execute=args.execute)

    if not args.execute:
        print("dry-run only: add --execute to submit live gripper motion.")
        return 0

    return execute_tasks(args, tasks)


if __name__ == "__main__":
    raise SystemExit(main())
