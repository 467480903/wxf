#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest
from unittest import mock
import tempfile
from pathlib import Path
import json

import yolo_detect_shelf_api as shelf_api


SUCCESS_RESULT = {
    "status": "success",
    "request_id": "ok-1",
    "detection": {
        "point1": {"label": "a", "center": [225.19, 185.84]},
        "point2": {"label": "b", "center": [413.13, 186.91]},
    },
    "offset": {
        "line_center": [319.16, 186.38],
        "horizontal_offset_px": -0.84,
        "direction": "偏左",
    },
    "slope": {"angle_deg": 0.33},
    "depth": {"center_mm": 1539.1},
    "server": {"latency_ms": 732.87, "work_dir": "/tmp/run"},
}


class ShelfApiTests(unittest.TestCase):
    def test_summarize_success_result(self) -> None:
        summary = shelf_api.summarize_detection_result(SUCCESS_RESULT)

        self.assertTrue(summary["ok"])
        self.assertEqual(summary["point1"]["label"], "a")
        self.assertEqual(summary["point2"]["label"], "b")
        self.assertEqual(summary["horizontal_offset_px"], -0.84)
        self.assertEqual(summary["center_depth_mm"], 1539.1)

    def test_detect_error_becomes_guard_failure(self) -> None:
        raw = {"status": "error", "error": "not enough points", "request_id": "err-1"}

        summary = shelf_api.summarize_detection_result(raw)
        shelf_api.validate_summary(summary)

        self.assertFalse(summary["ok"])
        self.assertIn("not enough points", summary["reason"])

    def test_threshold_failure_blocks_continue(self) -> None:
        summary = shelf_api.summarize_detection_result(SUCCESS_RESULT)

        shelf_api.validate_summary(summary, max_abs_offset_px=0.5)

        self.assertFalse(summary["ok"])
        self.assertIn("abs(horizontal_offset_px)", summary["reason"])

    def test_detect_shelf_raises_guard_error(self) -> None:
        with mock.patch.object(shelf_api, "detect_once", return_value={"status": "error", "error": "bad view"}):
            with self.assertRaises(shelf_api.ShelfDetectError) as ctx:
                shelf_api.detect_shelf()

        self.assertIn("bad view", str(ctx.exception))
        self.assertFalse(ctx.exception.summary["ok"])

    def test_detect_shelf_returns_summary_without_raise(self) -> None:
        with mock.patch.object(shelf_api, "detect_once", return_value=SUCCESS_RESULT):
            summary = shelf_api.detect_shelf(raise_on_error=False)

        self.assertTrue(summary["ok"])
        self.assertEqual(summary["direction"], "偏左")

    def test_load_guard_profile_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "profiles.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "profiles": {
                            "draft": {
                                "confirmed_for_motion": False,
                                "thresholds": {"max_abs_offset_px": 10.0},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "not confirmed_for_motion"):
                shelf_api.load_guard_profile("draft", profile_path=profile_path)

            profile = shelf_api.load_guard_profile("draft", profile_path=profile_path, allow_unconfirmed_profile=True)

        self.assertEqual(profile["thresholds"]["max_abs_offset_px"], 10.0)

    def test_detect_shelf_with_profile_applies_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "profiles.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "profiles": {
                            "tight": {
                                "confirmed_for_motion": True,
                                "thresholds": {"max_abs_offset_px": 0.5},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(shelf_api, "detect_once", return_value=SUCCESS_RESULT):
                summary = shelf_api.detect_shelf_with_profile(
                    "tight",
                    profile_path=profile_path,
                    raise_on_error=False,
                )

        self.assertFalse(summary["ok"])
        self.assertIn("abs(horizontal_offset_px)", summary["reason"])
        self.assertEqual(summary["profile_name"], "tight")


if __name__ == "__main__":
    unittest.main()
