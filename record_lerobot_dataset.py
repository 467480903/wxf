#!/usr/bin/env python3
"""
Record AgiBot robot data into a LeRobot-style dataset layout.

This script captures:
- left/right arm joint positions from robot joint states
- RGB images from head, left-hand, and right-hand cameras

Output layout example:
<output_dir>/
  meta/
    info.json
    episodes.jsonl
    camera_intrinsics.json
  episodes/
    episode_000000/
      data.jsonl
      observation.images.head_color/
      observation.images.hand_left_color/
      observation.images.hand_right_color/
"""

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")


@dataclass(frozen=True)
class CameraSpec:
    key: str
    camera_type: int
    folder: str


CAMERAS: List[CameraSpec] = [
    CameraSpec(
        key="head_color",
        camera_type=agibot_gdk.CameraType.kHeadColor,
        folder="observation.images.head_color",
    ),
    CameraSpec(
        key="hand_left_color",
        camera_type=agibot_gdk.CameraType.kHandLeftColor,
        folder="observation.images.hand_left_color",
    ),
    CameraSpec(
        key="hand_right_color",
        camera_type=agibot_gdk.CameraType.kHandRightColor,
        folder="observation.images.hand_right_color",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record left/right arm + head/hand camera data to LeRobot-style format."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("lerobot_dataset"),
        help="Dataset root directory.",
    )
    parser.add_argument(
        "--episode-id",
        type=int,
        default=0,
        help="Episode index (used as episode_XXXXXX).",
    )
    parser.add_argument("--seconds", type=float, default=10.0, help="Recording duration.")
    parser.add_argument("--fps", type=float, default=10.0, help="Sampling rate.")
    parser.add_argument(
        "--robot-type",
        type=str,
        default="agibot",
        help="Robot type metadata for info.json.",
    )
    return parser.parse_args()


def ensure_dirs(output_dir: Path, episode_id: int) -> Tuple[Path, Path]:
    meta_dir = output_dir / "meta"
    episode_dir = output_dir / "episodes" / f"episode_{episode_id:06d}"
    meta_dir.mkdir(parents=True, exist_ok=True)
    episode_dir.mkdir(parents=True, exist_ok=True)
    for cam in CAMERAS:
        (episode_dir / cam.folder).mkdir(parents=True, exist_ok=True)
    return meta_dir, episode_dir


def extract_arm_positions(joint_states: Dict, arm_prefix: str) -> Dict[str, float]:
    """
    Extract ordered joint positions for one arm from get_joint_states() result.
    arm_prefix examples: 'arm_l', 'arm_r'
    """
    positions: Dict[str, float] = {}
    for state in joint_states.get("states", []):
        name = state.get("name", "")
        if name.startswith(arm_prefix):
            positions[name] = float(state.get("position", 0.0))
    return dict(sorted(positions.items()))


def write_camera_intrinsics(meta_dir: Path, camera: agibot_gdk.Camera) -> None:
    intrinsics: Dict[str, Dict] = {}
    for cam in CAMERAS:
        try:
            intrinsic = camera.get_camera_intrinsic(cam.camera_type)
            intrinsics[cam.key] = {
                "fx": float(intrinsic.intrinsic[0]),
                "fy": float(intrinsic.intrinsic[1]),
                "cx": float(intrinsic.intrinsic[2]),
                "cy": float(intrinsic.intrinsic[3]),
                "distortion": [float(v) for v in intrinsic.distortion],
            }
        except Exception as exc:  # pylint: disable=broad-except
            intrinsics[cam.key] = {"error": str(exc)}

    with (meta_dir / "camera_intrinsics.json").open("w", encoding="utf-8") as f:
        json.dump(intrinsics, f, ensure_ascii=False, indent=2)


def capture_images(
    camera: agibot_gdk.Camera,
    episode_dir: Path,
    frame_idx: int,
    timeout_ms: float = 1000.0,
) -> Tuple[Dict[str, Optional[str]], Dict[str, Optional[Tuple[int, int]]]]:
    paths: Dict[str, Optional[str]] = {}
    sizes: Dict[str, Optional[Tuple[int, int]]] = {}
    for cam in CAMERAS:
        rel_path = f"{cam.folder}/{frame_idx:06d}.jpg"
        abs_path = episode_dir / rel_path
        try:
            img = camera.get_latest_image(cam.camera_type, timeout_ms)
            if img is None:
                paths[cam.key] = None
                sizes[cam.key] = None
                continue
            with abs_path.open("wb") as f:
                f.write(img.data)
            paths[cam.key] = rel_path
            sizes[cam.key] = (int(img.height), int(img.width))
        except Exception:  # pylint: disable=broad-except
            paths[cam.key] = None
            sizes[cam.key] = None
    return paths, sizes


def write_info_json(
    meta_dir: Path,
    fps: float,
    robot_type: str,
    left_dim: int,
    right_dim: int,
    image_sizes: Dict[str, Optional[Tuple[int, int]]],
) -> None:
    features = {
        "observation.state.arm_left": {"dtype": "float32", "shape": [left_dim]},
        "observation.state.arm_right": {"dtype": "float32", "shape": [right_dim]},
    }
    for cam in CAMERAS:
        size = image_sizes.get(cam.key)
        if size is None:
            features[f"observation.images.{cam.key}"] = {"dtype": "image", "shape": None}
        else:
            h, w = size
            features[f"observation.images.{cam.key}"] = {
                "dtype": "image",
                "shape": [h, w, 3],
            }

    info = {
        "codebase_version": "v2.0",
        "robot_type": robot_type,
        "fps": fps,
        "features": features,
    }
    with (meta_dir / "info.json").open("w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)


def append_episode_index(
    meta_dir: Path,
    episode_id: int,
    length: int,
    duration_s: float,
    episode_rel_path: str,
) -> None:
    row = {
        "episode_index": episode_id,
        "length": length,
        "duration_s": duration_s,
        "data_path": f"{episode_rel_path}/data.jsonl",
    }
    with (meta_dir / "episodes.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    meta_dir, episode_dir = ensure_dirs(output_dir, args.episode_id)

    if args.fps <= 0:
        raise ValueError("--fps must be > 0")
    if args.seconds <= 0:
        raise ValueError("--seconds must be > 0")

    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        raise RuntimeError("GDK init failed")

    robot = agibot_gdk.Robot()
    camera = agibot_gdk.Camera()
    time.sleep(2.0)  # allow robot/camera streams to stabilize

    data_rows: List[Dict] = []
    first_image_sizes: Dict[str, Optional[Tuple[int, int]]] = {cam.key: None for cam in CAMERAS}
    num_steps = int(round(args.seconds * args.fps))
    dt = 1.0 / args.fps
    t0 = time.monotonic()

    try:
        write_camera_intrinsics(meta_dir, camera)
        print(f"Start recording episode {args.episode_id:06d}, steps={num_steps}, fps={args.fps}")

        for frame_idx in range(num_steps):
            step_start = time.monotonic()
            timestamp_ns = time.time_ns()

            joint_states = robot.get_joint_states()
            left_joints = extract_arm_positions(joint_states, "arm_l")
            right_joints = extract_arm_positions(joint_states, "arm_r")
            image_paths, image_sizes = capture_images(camera, episode_dir, frame_idx)

            for key, size in image_sizes.items():
                if first_image_sizes[key] is None and size is not None:
                    first_image_sizes[key] = size

            row = {
                "episode_index": args.episode_id,
                "frame_index": frame_idx,
                "timestamp_ns": timestamp_ns,
                "observation.state.arm_left": list(left_joints.values()),
                "observation.state.arm_right": list(right_joints.values()),
                "observation.state.arm_left_names": list(left_joints.keys()),
                "observation.state.arm_right_names": list(right_joints.keys()),
                "observation.images.head_color": image_paths["head_color"],
                "observation.images.hand_left_color": image_paths["hand_left_color"],
                "observation.images.hand_right_color": image_paths["hand_right_color"],
                "done": frame_idx == (num_steps - 1),
            }
            data_rows.append(row)

            elapsed = time.monotonic() - step_start
            sleep_time = max(0.0, dt - elapsed)
            time.sleep(sleep_time)

        with (episode_dir / "data.jsonl").open("w", encoding="utf-8") as f:
            for row in data_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        left_dim = len(data_rows[0]["observation.state.arm_left"]) if data_rows else 0
        right_dim = len(data_rows[0]["observation.state.arm_right"]) if data_rows else 0
        write_info_json(
            meta_dir=meta_dir,
            fps=args.fps,
            robot_type=args.robot_type,
            left_dim=left_dim,
            right_dim=right_dim,
            image_sizes=first_image_sizes,
        )
        append_episode_index(
            meta_dir=meta_dir,
            episode_id=args.episode_id,
            length=len(data_rows),
            duration_s=time.monotonic() - t0,
            episode_rel_path=f"episodes/episode_{args.episode_id:06d}",
        )

        print(f"Saved episode data to: {episode_dir}")
        print(f"Saved meta info to: {meta_dir}")

    finally:
        camera.close_camera()
        if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
            print("Warning: GDK release returned non-success")


if __name__ == "__main__":
    main()
