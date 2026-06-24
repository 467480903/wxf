#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${YOLO_DETECT_PYTHON:-${ROOT_DIR}/../yolo/yolo-env/bin/python}"

cd "${ROOT_DIR}"

exec "${PYTHON}" yolo_detect_client.py \
  --broker "${YOLO_DETECT_BROKER:-127.0.0.1}" \
  --port "${YOLO_DETECT_PORT:-1883}" \
  --request-topic "${YOLO_DETECT_REQUEST_TOPIC:-/yolo_detect/}" \
  --result-topic "${YOLO_DETECT_RESULT_TOPIC:-/yolo_detect_result}" \
  --rgb-path "${YOLO_DETECT_RGB_PATH:-head.jpg}" \
  --depth-raw-path "${YOLO_DETECT_DEPTH_RAW_PATH:-head_depth.raw}" \
  --model-path "${YOLO_DETECT_MODEL:-shelf.pt}" \
  "$@"
