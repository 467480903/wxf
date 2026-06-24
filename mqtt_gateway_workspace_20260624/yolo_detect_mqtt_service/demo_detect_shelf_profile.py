#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the shelf guard with a named profile.

Default profile:

    observe_only

This demo is no-motion. It is meant to show how a total-control script should
block or continue based on profile validation.
"""
from __future__ import annotations

import argparse
import json

from yolo_detect_shelf_api import ShelfDetectError, detect_shelf_with_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="observe_only")
    parser.add_argument("--profile-path", default="shelf_guard_profiles.json")
    parser.add_argument("--allow-unconfirmed-profile", action="store_true")
    parser.add_argument("--gateway-url", default="http://127.0.0.1:8767")
    parser.add_argument("--broker", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--http-timeout-s", type=float, default=15.0)
    parser.add_argument("--timeout-s", type=float, default=180.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = detect_shelf_with_profile(
            args.profile,
            profile_path=args.profile_path,
            allow_unconfirmed_profile=args.allow_unconfirmed_profile,
            gateway_url=args.gateway_url,
            broker=args.broker,
            port=args.port,
            http_timeout_s=args.http_timeout_s,
            timeout_s=args.timeout_s,
            raise_on_error=True,
            verbose=False,
        )
    except ShelfDetectError as exc:
        print("SHELF_PROFILE_OK=false")
        print(f"PROFILE={args.profile}")
        print(f"STOP_REASON={exc}")
        print(json.dumps(exc.summary, ensure_ascii=False, indent=2))
        return 1
    except Exception as exc:  # noqa: BLE001 - demo boundary should print operator-friendly error
        print("SHELF_PROFILE_OK=false")
        print(f"PROFILE={args.profile}")
        print(f"CONFIG_OR_RUNTIME_ERROR={type(exc).__name__}: {exc}")
        return 2

    print("SHELF_PROFILE_OK=true")
    print(f"profile={summary.get('profile_name')}")
    print(f"profile_description={summary.get('profile_description')}")
    print(f"request_id={summary.get('request_id')}")
    print(f"horizontal_offset_px={summary.get('horizontal_offset_px')}")
    print(f"direction={summary.get('direction')}")
    print(f"angle_deg={summary.get('angle_deg')}")
    print(f"center_depth_mm={summary.get('center_depth_mm')}")
    print("NEXT_STEP_ALLOWED=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
