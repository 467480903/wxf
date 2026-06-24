#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Template for placing shelf detection before a business step.

This template does not execute any robot motion. Copy the pattern into a new
business script and put the actual next step only after the guard succeeds.
"""
from __future__ import annotations

from yolo_detect_shelf_api import ShelfDetectError, detect_shelf_with_profile


def main() -> int:
    try:
        summary = detect_shelf_with_profile("observe_only")
    except ShelfDetectError as exc:
        print(f"STOP: shelf vision guard failed: {exc}")
        return 1

    print("Shelf vision guard passed.")
    print(f"offset_px={summary.get('horizontal_offset_px')}")
    print(f"direction={summary.get('direction')}")

    # Put the later business step here after process-owner review.
    # Do not continue to a motion step when the guard raises ShelfDetectError.
    print("NEXT_STEP_PLACEHOLDER=no motion executed by this template")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
