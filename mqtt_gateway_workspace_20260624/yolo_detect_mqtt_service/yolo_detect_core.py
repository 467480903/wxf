#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YOLO + depth raw detection core for the WXF MQTT vision service."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import math
import time

import cv2
import numpy as np


COMMON_DEPTH_SHAPES = (
    (400, 640),
    (480, 640),
    (480, 848),
    (360, 640),
    (720, 1280),
    (240, 424),
    (400, 848),
    (720, 960),
)


class DetectionError(RuntimeError):
    """Raised when the image/depth payload is valid but detection cannot finish."""


@dataclass(frozen=True)
class DetectionBox:
    label: str
    center_x: float
    center_y: float
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float

    @property
    def center(self) -> tuple[float, float]:
        return self.center_x, self.center_y


def load_depth_from_raw(raw_path: str | Path, shape: tuple[int, int] | None = None) -> np.ndarray:
    raw = Path(raw_path).read_bytes()
    if len(raw) % 2 != 0:
        raise DetectionError(f"depth raw size must be even uint16 bytes, got {len(raw)}")
    pixels = len(raw) // 2
    if shape is not None:
        height, width = int(shape[0]), int(shape[1])
        if height * width == pixels:
            return np.frombuffer(raw, dtype=np.uint16).reshape((height, width))
    for height, width in COMMON_DEPTH_SHAPES:
        if height * width == pixels:
            return np.frombuffer(raw, dtype=np.uint16).reshape((height, width))
    side = int(math.sqrt(pixels))
    if side * side == pixels:
        return np.frombuffer(raw, dtype=np.uint16).reshape((side, side))
    raise DetectionError(f"cannot infer depth shape from {len(raw)} bytes")


def get_depth_at_pixel(depth_raw: np.ndarray, x: int, y: int, search_radius: int = 10) -> float:
    height, width = depth_raw.shape[:2]
    if 0 <= x < width and 0 <= y < height:
        value = depth_raw[y, x]
        if value > 0:
            return float(value)
    for radius in range(1, search_radius + 1):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if abs(dx) + abs(dy) != radius:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    value = depth_raw[ny, nx]
                    if value > 0:
                        return float(value)
    return -1.0


def get_average_depth(depth_raw: np.ndarray, x: int, y: int, radius: int = 5) -> float:
    height, width = depth_raw.shape[:2]
    values: list[int] = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx * dx + dy * dy > radius * radius:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                value = int(depth_raw[ny, nx])
                if value > 0:
                    values.append(value)
    if not values:
        return -1.0
    return float(np.mean(values))


def _tensor_scalar(value: Any) -> float:
    try:
        return float(value)
    except TypeError:
        pass
    if hasattr(value, "item"):
        return float(value.item())
    return float(value[0])


def _xyxy_list(value: Any) -> list[float]:
    item = value[0]
    if hasattr(item, "cpu"):
        item = item.cpu()
    if hasattr(item, "numpy"):
        item = item.numpy()
    return [float(v) for v in item]


def collect_boxes(result: Any, wanted_labels: tuple[str, ...] = ("a", "b", "c", "d")) -> dict[str, list[DetectionBox]]:
    names = getattr(result, "names", {}) or {}
    label_by_id = {int(cid): str(name) for cid, name in dict(names).items()}
    boxes_by_label: dict[str, list[DetectionBox]] = {label: [] for label in wanted_labels}
    for box in getattr(result, "boxes", []) or []:
        class_id = int(_tensor_scalar(box.cls[0]))
        label = label_by_id.get(class_id, str(class_id))
        if label not in boxes_by_label:
            continue
        x1, y1, x2, y2 = _xyxy_list(box.xyxy)
        confidence = float(_tensor_scalar(box.conf[0]))
        boxes_by_label[label].append(
            DetectionBox(
                label=label,
                center_x=(x1 + x2) / 2.0,
                center_y=(y1 + y2) / 2.0,
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                confidence=confidence,
            )
        )
    for label in boxes_by_label:
        boxes_by_label[label].sort(key=lambda item: item.confidence, reverse=True)
    return boxes_by_label


def choose_line_points(boxes_by_label: dict[str, list[DetectionBox]]) -> tuple[DetectionBox, DetectionBox, str]:
    strategies = (
        ("a", "b", "highest confidence a and b"),
        ("b", "b", "two highest confidence b"),
        ("a", "a", "two highest confidence a"),
        ("c", "d", "highest confidence c and d"),
        ("c", "c", "two highest confidence c"),
        ("d", "d", "two highest confidence d"),
    )
    for first_label, second_label, reason in strategies:
        first_items = boxes_by_label.get(first_label, [])
        second_items = boxes_by_label.get(second_label, [])
        if first_label == second_label:
            if len(first_items) >= 2:
                return first_items[0], first_items[1], reason
        elif first_items and second_items:
            return first_items[0], second_items[0], reason
    counts = {label: len(items) for label, items in boxes_by_label.items()}
    raise DetectionError(f"not enough detection points for line calculation: {counts}")


def _label_color(label: str) -> tuple[int, int, int]:
    return {
        "a": (255, 0, 0),
        "b": (0, 255, 0),
        "c": (0, 0, 255),
        "d": (0, 165, 255),
    }.get(label, (128, 128, 128))


def _draw_detection(image: np.ndarray, point1: DetectionBox, point2: DetectionBox) -> dict[str, Any]:
    img_h, img_w = image.shape[:2]
    image_center_x = img_w / 2.0
    for point in (point1, point2):
        color = _label_color(point.label)
        cv2.rectangle(image, (int(point.x1), int(point.y1)), (int(point.x2), int(point.y2)), color, 2)
        cv2.putText(
            image,
            f"{point.label} {point.confidence:.2f}",
            (int(point.x1), int(point.y1) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )
        cv2.circle(image, (int(point.center_x), int(point.center_y)), 5, (0, 255, 255), -1)

    cv2.line(image, (int(point1.center_x), int(point1.center_y)), (int(point2.center_x), int(point2.center_y)), (0, 0, 255), 2)
    line_center_x = (point1.center_x + point2.center_x) / 2.0
    line_center_y = (point1.center_y + point2.center_y) / 2.0
    cv2.circle(image, (int(line_center_x), int(line_center_y)), 8, (255, 0, 0), -1)
    cv2.line(image, (int(image_center_x), 0), (int(image_center_x), img_h), (0, 255, 0), 1)
    cv2.line(image, (int(image_center_x), int(line_center_y)), (int(line_center_x), int(line_center_y)), (255, 255, 0), 2)

    horizontal_offset_px = line_center_x - image_center_x
    dx = point2.center_x - point1.center_x
    dy = point2.center_y - point1.center_y
    angle_rad = float(np.arctan2(dy, dx))
    slope = float("inf") if abs(dx) < 1e-6 else float(dy / dx)

    cv2.putText(
        image,
        f"h_offset: {horizontal_offset_px:.1f}px",
        (int(min(image_center_x, line_center_x)) + 5, int(line_center_y) - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 0),
        2,
    )
    cv2.putText(
        image,
        "slope: inf" if np.isinf(slope) else f"slope: {slope:.4f}",
        (max(int(line_center_x) - 80, 10), max(int(line_center_y) - 15, 20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 255),
        2,
    )
    cv2.putText(
        image,
        f"angle: {angle_rad:.4f} rad",
        (max(int(line_center_x) - 80, 10), max(int(line_center_y) + 20, 30)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 200),
        2,
    )

    return {
        "line_center": (line_center_x, line_center_y),
        "image_center_x": image_center_x,
        "horizontal_offset_px": horizontal_offset_px,
        "direction": "偏右" if horizontal_offset_px > 0 else ("偏左" if horizontal_offset_px < 0 else "居中"),
        "slope": slope,
        "angle_rad": angle_rad,
        "angle_deg": float(np.degrees(angle_rad)),
    }


def _save_depth_images(depth_raw: np.ndarray, output_dir: Path) -> np.ndarray:
    valid = depth_raw > 0
    if np.any(valid):
        min_depth = int(depth_raw[valid].min())
        max_depth = int(depth_raw[valid].max())
        if max_depth > min_depth:
            normalized = np.clip((depth_raw.astype(np.float32) - min_depth) / (max_depth - min_depth) * 255.0, 0, 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(depth_raw, dtype=np.uint8)
    else:
        normalized = np.zeros_like(depth_raw, dtype=np.uint8)
    colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
    cv2.imwrite(str(output_dir / "yolo_depth_depth.jpg"), colored)
    return colored


class YoloDepthDetector:
    def __init__(self, model_path: str | Path, device: str = "cpu", model: Any | None = None) -> None:
        self.model_path = str(model_path)
        self.device = device
        self.model = model if model is not None else self._load_model(model_path)

    @staticmethod
    def _load_model(model_path: str | Path) -> Any:
        from ultralytics import YOLO

        return YOLO(str(model_path))

    def detect(
        self,
        image_path: str | Path,
        depth_raw_path: str | Path,
        output_dir: str | Path,
        depth_shape: tuple[int, int] = (400, 640),
        depth_offset_px: int = 1,
        conf: float | None = None,
        imgsz: int | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        image_path = Path(image_path)
        depth_raw_path = Path(depth_raw_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        kwargs: dict[str, Any] = {"device": self.device, "verbose": False}
        if conf is not None:
            kwargs["conf"] = float(conf)
        if imgsz is not None:
            kwargs["imgsz"] = int(imgsz)
        results = self.model.predict(str(image_path), **kwargs)
        if not results:
            raise DetectionError("YOLO returned no result")
        result = results[0]
        try:
            result.save(filename=str(output_dir / "result.jpg"))
        except Exception:
            pass

        original = getattr(result, "orig_img", None)
        if original is None:
            original = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if original is None:
            raise DetectionError(f"cannot read image: {image_path}")
        image = original.copy()
        img_h, img_w = image.shape[:2]

        boxes_by_label = collect_boxes(result)
        point1, point2, strategy = choose_line_points(boxes_by_label)
        calc = _draw_detection(image, point1, point2)
        cv2.imwrite(str(output_dir / "yolo_depth_rgb.jpg"), image)

        depth_raw = load_depth_from_raw(depth_raw_path, depth_shape)
        actual_depth_shape = tuple(int(v) for v in depth_raw.shape[:2])

        sample_1_x = int(point1.center_x)
        sample_1_y = int(point1.center_y) + int(depth_offset_px)
        sample_2_x = int(point2.center_x)
        sample_2_y = int(point2.center_y) + int(depth_offset_px)
        center_x = int((point1.center_x + point2.center_x) / 2.0)
        center_y = int((point1.center_y + point2.center_y) / 2.0)

        depth_point1_center = get_depth_at_pixel(depth_raw, int(point1.center_x), int(point1.center_y))
        depth_point2_center = get_depth_at_pixel(depth_raw, int(point2.center_x), int(point2.center_y))
        depth_point1_offset = get_average_depth(depth_raw, sample_1_x, sample_1_y, radius=2)
        depth_point2_offset = get_average_depth(depth_raw, sample_2_x, sample_2_y, radius=2)
        depth_center = get_average_depth(depth_raw, center_x, center_y, radius=5)

        depth_colored = _save_depth_images(depth_raw, output_dir)
        image_with_depth = image.copy()
        for x, y, text, color in (
            (sample_1_x, sample_1_y, f"{point1.label}:{depth_point1_offset:.0f}mm", (255, 0, 255)),
            (sample_2_x, sample_2_y, f"{point2.label}:{depth_point2_offset:.0f}mm", (255, 255, 0)),
            (center_x, center_y, f"C:{depth_center:.0f}mm", (0, 255, 0)),
        ):
            cv2.circle(image_with_depth, (x, y), 5, color, -1)
            cv2.putText(image_with_depth, text, (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.circle(depth_colored, (x, y), 5, color, -1)
            cv2.putText(depth_colored, text, (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        cv2.imwrite(str(output_dir / "yolo_depth_rgb_with_depth.jpg"), image_with_depth)
        cv2.imwrite(str(output_dir / "yolo_depth_depth_marked.jpg"), depth_colored)

        output_files = [
            "yolo_depth_rgb.jpg",
            "yolo_depth_rgb_with_depth.jpg",
            "yolo_depth_depth.jpg",
            "yolo_depth_depth_marked.jpg",
            "result.jpg",
        ]
        payload = {
            "model_path": Path(self.model_path).name,
            "image_path": image_path.name,
            "depth_raw_path": depth_raw_path.name,
            "depth_offset_px": int(depth_offset_px),
            "depth_shape": [int(actual_depth_shape[0]), int(actual_depth_shape[1])],
            "image_size": {"height": int(img_h), "width": int(img_w)},
            "detection": {
                "point1": {"label": point1.label, "center": [round(point1.center_x, 2), round(point1.center_y, 2)]},
                "point2": {"label": point2.label, "center": [round(point2.center_x, 2), round(point2.center_y, 2)]},
                "strategy": strategy,
                "counts": {label: len(items) for label, items in boxes_by_label.items()},
            },
            "offset": {
                "line_center": [round(float(calc["line_center"][0]), 2), round(float(calc["line_center"][1]), 2)],
                "image_center_x": round(float(calc["image_center_x"]), 2),
                "horizontal_offset_px": round(float(calc["horizontal_offset_px"]), 2),
                "direction": calc["direction"],
            },
            "slope": {
                "slope": None if np.isinf(calc["slope"]) else round(float(calc["slope"]), 4),
                "angle_rad": round(float(calc["angle_rad"]), 4),
                "angle_deg": round(float(calc["angle_deg"]), 2),
            },
            "depth": {
                "point1_center_mm": round(float(depth_point1_center), 1),
                "point1_left_offset_mm": round(float(depth_point1_offset), 1),
                "point1_left_sample_pixel": [int(sample_1_x), int(sample_1_y)],
                "point2_center_mm": round(float(depth_point2_center), 1),
                "point2_right_offset_mm": round(float(depth_point2_offset), 1),
                "point2_right_sample_pixel": [int(sample_2_x), int(sample_2_y)],
                "center_mm": round(float(depth_center), 1),
                "center_sample_pixel": [int(center_x), int(center_y)],
            },
            "output_files": output_files,
            "latency_ms": round((time.monotonic() - started) * 1000.0, 2),
        }
        (output_dir / "yolo_depth_result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
