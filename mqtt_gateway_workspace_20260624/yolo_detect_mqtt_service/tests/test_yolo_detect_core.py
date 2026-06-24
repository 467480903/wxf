#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from yolo_detect_core import YoloDepthDetector


class FakeTensor:
    def __init__(self, values):
        self.values = values

    def __getitem__(self, index):
        return self.values[index]

    def cpu(self):
        return self

    def numpy(self):
        return np.array(self.values, dtype=np.float32)


class FakeBox:
    def __init__(self, cls_id, conf, xyxy):
        self.cls = [cls_id]
        self.conf = [conf]
        self.xyxy = FakeTensor([xyxy])


class FakeResult:
    names = {0: "a", 1: "b"}

    def __init__(self, image):
        self.orig_img = image
        self.boxes = [
            FakeBox(0, 0.95, [200.0, 190.0, 250.0, 230.0]),
            FakeBox(1, 0.96, [410.0, 190.0, 455.0, 232.0]),
        ]

    def save(self, filename):
        cv2.imwrite(filename, self.orig_img)


class FakeModel:
    def predict(self, image_path, **kwargs):
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        return [FakeResult(image)]


class YoloDetectCoreTest(unittest.TestCase):
    def test_fake_model_detection_generates_expected_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = np.zeros((400, 640, 3), dtype=np.uint8)
            image_path = root / "head.jpg"
            depth_path = root / "head_depth.raw"
            output_dir = root / "out"
            cv2.imwrite(str(image_path), image)
            depth = np.full((400, 640), 1200, dtype=np.uint16)
            depth.tofile(str(depth_path))

            detector = YoloDepthDetector("fake.pt", device="cpu", model=FakeModel())
            result = detector.detect(image_path, depth_path, output_dir, depth_shape=(400, 640), depth_offset_px=1)

            self.assertEqual(result["image_size"], {"height": 400, "width": 640})
            self.assertEqual(result["detection"]["point1"]["label"], "a")
            self.assertEqual(result["detection"]["point2"]["label"], "b")
            self.assertEqual(result["depth_shape"], [400, 640])
            self.assertEqual(result["depth"]["center_mm"], 1200.0)
            self.assertTrue((output_dir / "yolo_depth_result.json").exists())
            self.assertTrue((output_dir / "yolo_depth_rgb_with_depth.jpg").exists())


if __name__ == "__main__":
    unittest.main()
