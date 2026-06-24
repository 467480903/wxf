#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo guard for using shelf detection before any business action.

This demo is intentionally no-motion. It only prints whether a later business
script should continue.
"""
from __future__ import annotations

import json

from yolo_detect_shelf_api import ShelfDetectError, detect_shelf


def main() -> int:
    try:
        summary = detect_shelf(
            gateway_url="http://127.0.0.1:8767",
            broker="127.0.0.1",
            port=1883,
            http_timeout_s=15,
            timeout_s=180,
            # These thresholds are examples. Set them only when the process
            # owner has confirmed the acceptable vision window for that step.
            max_abs_offset_px=None,
            max_abs_angle_deg=None,
            min_center_depth_mm=None,
            max_center_depth_mm=None,
            raise_on_error=True,
            verbose=False,
        )
    except ShelfDetectError as exc:
        print("SHELF_DETECT_OK=false")
        print(f"STOP_REASON={exc}")
        print(json.dumps(exc.summary, ensure_ascii=False, indent=2))
        return 1

    print("SHELF_DETECT_OK=true")
    print(f"request_id={summary.get('request_id')}")
    print(f"horizontal_offset_px={summary.get('horizontal_offset_px')}")
    print(f"direction={summary.get('direction')}")
    print(f"angle_deg={summary.get('angle_deg')}")
    print(f"center_depth_mm={summary.get('center_depth_mm')}")
    print(f"server_latency_ms={summary.get('server_latency_ms')}")
    print("NEXT_STEP_ALLOWED=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
