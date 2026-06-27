#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Head RGB/depth capture for the migrated MQTT workspace.

This mirrors the original customer script /data/wxf/wxf/yolo/cam_get_head.py:
capture head color and head depth through agibot_gdk.Camera(), then write
head.jpg, head_depth.raw and head_depth.jpg in the current yolo directory.

The MQTT runner normally starts without the GDK Python environment. If
agibot_gdk is not importable, this wrapper re-executes itself once after
sourcing /home/agi/app/env.sh, so the visual input path matches the original
program while the rest of the task still runs through MQTT/Gateway.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

_DIRECT_FLAG = "--direct-gdk-camera"
_GDK_ENV = Path("/home/agi/app/env.sh")


def _reexec_with_gdk_env() -> int:
    script = Path(__file__).resolve()
    script_dir = script.parent
    if not _GDK_ENV.exists():
        raise RuntimeError(f"GDK env script not found: {_GDK_ENV}")
    command = (
        f"source {shlex.quote(str(_GDK_ENV))} >/dev/null 2>&1 && "
        f"cd {shlex.quote(str(script_dir))} && "
        f"exec python3 {shlex.quote(str(script))} {_DIRECT_FLAG}"
    )
    return subprocess.call(["bash", "-lc", command])


def _run_original_gdk_camera() -> int:
    import agibot_gdk
    import numpy as np

    camera = agibot_gdk.Camera()
    time.sleep(2)
    os.makedirs("images", exist_ok=True)

    try:
        color_type = agibot_gdk.CameraType.kHeadColor
        color_img = camera.get_latest_image(color_type, 1000.0)

        if color_img is not None:
            print(f"彩色相机：{color_img.width}x{color_img.height}")
            filename = "head.jpg"
            with open(filename, "wb") as f:
                f.write(color_img.data)
            print(f"彩色图已保存：{filename}")
        else:
            print("未获取到彩色图像")
            return 1

        depth_type = agibot_gdk.CameraType.kHeadDepth
        depth_img = camera.get_latest_image(depth_type, 1000.0)

        if depth_img is not None:
            print(f"深度相机：{depth_img.width}x{depth_img.height}, encoding={depth_img.encoding}")

            depth_raw_filename = "head_depth.raw"
            with open(depth_raw_filename, "wb") as f:
                f.write(depth_img.data)
            print(f"原始深度数据已保存：{depth_raw_filename}")

            try:
                import cv2

                depth_array = np.frombuffer(depth_img.data, dtype=np.uint16)
                depth_array = depth_array.reshape((depth_img.height, depth_img.width))

                valid_mask = depth_array > 0
                if np.any(valid_mask):
                    min_d = depth_array[valid_mask].min()
                    max_d = depth_array[valid_mask].max()
                    print(f"深度范围：{min_d} ~ {max_d} mm")
                else:
                    min_d, max_d = 0, 1
                    print("深度图全部为 0（无效）")

                if max_d > min_d:
                    normalized = ((depth_array - min_d) / (max_d - min_d) * 255).astype(np.uint8)
                else:
                    normalized = np.zeros_like(depth_array, dtype=np.uint8)
                depth_colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)

                depth_info = f"Depth: {min_d}-{max_d}mm"
                cv2.putText(
                    depth_colored,
                    depth_info,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

                depth_jpg_filename = "head_depth.jpg"
                cv2.imwrite(depth_jpg_filename, depth_colored)
                print(f"深度伪彩色图已保存：{depth_jpg_filename}")
            except ImportError:
                print("OpenCV 未安装，跳过深度图伪彩色保存")
            except Exception as exc:
                print(f"深度图处理失败：{exc}")
        else:
            print("未获取到深度图像")
            return 1
    finally:
        camera.close_camera()

    return 0


def main() -> int:
    if _DIRECT_FLAG in sys.argv:
        return _run_original_gdk_camera()
    try:
        import agibot_gdk  # noqa: F401
    except ModuleNotFoundError:
        return _reexec_with_gdk_env()
    return _run_original_gdk_camera()


if __name__ == "__main__":
    raise SystemExit(main())
