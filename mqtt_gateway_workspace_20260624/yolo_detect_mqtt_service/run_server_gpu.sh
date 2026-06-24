#!/usr/bin/env bash
set -euo pipefail

# GPU server launcher for the same MQTT YOLO detect service.
#
# Use this on the future 4060 machine, not on the Huixi robot body.
# The CPU launcher intentionally exports CUDA_VISIBLE_DEVICES="" so it can
# never use a GPU by accident. This launcher keeps CUDA visible and defaults
# the inference device to cuda:0.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${YOLO_DETECT_PYTHON:-python3}"

cd "${ROOT_DIR}"

exec "${PYTHON}" yolo_detect_server.py \
  --broker "${YOLO_DETECT_BROKER:-127.0.0.1}" \
  --port "${YOLO_DETECT_PORT:-1883}" \
  --request-topic "${YOLO_DETECT_REQUEST_TOPIC:-/yolo_detect/}" \
  --result-topic "${YOLO_DETECT_RESULT_TOPIC:-/yolo_detect_result}" \
  --model "${YOLO_DETECT_MODEL:-shelf.pt}" \
  --device "${YOLO_DETECT_DEVICE:-cuda:0}" \
  --work-dir "${YOLO_DETECT_WORK_DIR:-runs}" \
  "$@"
