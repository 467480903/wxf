#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break

from mqtt_common import block_unsupported



def main() -> int:
    return block_unsupported("BOX_528_1/chassis_data_recorder.py", 'No audited MQTT/Gateway mapping was inferred for this original script.')


if __name__ == "__main__":
    raise SystemExit(main())
