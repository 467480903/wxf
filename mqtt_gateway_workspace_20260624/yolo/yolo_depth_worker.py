#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resident worker for yolo_depth.py used by the V4 runner.

The worker keeps the Ultralytics YOLO model objects alive between yolo_depth.py
requests. It deliberately reuses yolo_depth.py's existing functions and output
files so detection semantics, JSON shape, and downstream correction scripts stay
unchanged.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path
from types import ModuleType
from typing import Any


RESULT_PREFIX = "__G2_YOLO_WORKER_RESULT__ "


class YoloDepthWorker:
    def __init__(self) -> None:
        self._module: ModuleType | None = None
        self._module_path: Path | None = None
        self._model_cache: dict[str, Any] = {}

    def _load_module(self, script_path: Path) -> ModuleType:
        script_path = script_path.resolve()
        if self._module is not None and self._module_path == script_path:
            return self._module
        spec = importlib.util.spec_from_file_location("g2_wxf_yolo_depth_resident", script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load module from {script_path}")
        module = importlib.util.module_from_spec(spec)
        old_argv = sys.argv[:]
        sys.argv = [str(script_path)]
        try:
            spec.loader.exec_module(module)
        finally:
            sys.argv = old_argv
        self._module = module
        self._module_path = script_path
        return module

    def _install_cached_yolo_factory(self, module: ModuleType) -> None:
        original_yolo = getattr(module, "_G2_WXF_ORIGINAL_YOLO", None)
        if original_yolo is None:
            original_yolo = module.YOLO
            module._G2_WXF_ORIGINAL_YOLO = original_yolo

        def cached_yolo(model_path: str) -> Any:
            raw = Path(str(model_path))
            key = str(raw if raw.is_absolute() else (Path.cwd() / raw).resolve())
            if key not in self._model_cache:
                print(f"# yolo_resident_load_model: {model_path}")
                self._model_cache[key] = original_yolo(model_path)
            else:
                print(f"# yolo_resident_reuse_model: {model_path}")
            return self._model_cache[key]

        module.YOLO = cached_yolo

    def run_request(self, request: dict[str, Any]) -> dict[str, Any]:
        script_path = Path(str(request["script"])).resolve()
        args = [str(item) for item in request.get("args", [])]
        model_path = args[0] if args else "06131557.pt"
        depth_offset = int(args[1]) if len(args) > 1 else 12

        module = self._load_module(script_path)
        self._install_cached_yolo_factory(module)
        module.MODEL_PATH = model_path
        module.DEPTH_OFFSET = depth_offset
        module.RESULT_JSON_PATH = "yolo_depth_result.json"

        old_argv = sys.argv[:]
        sys.argv = [str(script_path), *args]
        started_at = time.time()
        try:
            rc = int(module.main())
        finally:
            sys.argv = old_argv

        return {
            "ok": True,
            "rc": rc,
            "elapsed_s": round(time.time() - started_at, 3),
            "model_path": model_path,
            "depth_offset": depth_offset,
            "cache_size": len(self._model_cache),
        }


def main() -> int:
    worker = YoloDepthWorker()
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            request = json.loads(raw_line)
            if request.get("command") == "shutdown":
                print(RESULT_PREFIX + json.dumps({"ok": True, "rc": 0, "shutdown": True}), flush=True)
                return 0
            response = worker.run_request(request)
        except BaseException as exc:
            traceback.print_exc()
            response = {"ok": False, "rc": 1, "error": f"{type(exc).__name__}: {exc}"}
        print(RESULT_PREFIX + json.dumps(response, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
