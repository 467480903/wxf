#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path


for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break

from mqtt_common import require_done, safe_motion_mode, submit_task


def main() -> int:
    parser = argparse.ArgumentParser(description="MQTT/Gateway TTS wrapper for interaction/play_tts_cli.py")
    parser.add_argument("text", nargs="+", help="text to play through the Gateway persistent GDK session")
    parser.add_argument("--wait-s", type=float, default=0.0, help="optional wait after submitting TTS, default 0")
    parser.add_argument("--timeout-s", type=float, default=8.0)
    args = parser.parse_args()

    text = " ".join(args.text).strip()
    if not text:
        raise SystemExit("text is required")

    result = submit_task(
        "interaction.play_tts",
        {
            "text": text,
            "post_play_wait_s": float(args.wait_s),
            "source_script": "interaction/play_tts_cli.py",
        },
        mode=safe_motion_mode(),
        timeout_s=float(args.timeout_s),
    )
    require_done(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
