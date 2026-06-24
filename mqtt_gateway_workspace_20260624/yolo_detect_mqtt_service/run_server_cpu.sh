#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${YOLO_DETECT_PYTHON:-${ROOT_DIR}/../yolo/yolo-env/bin/python}"

cd "${ROOT_DIR}"
export CUDA_VISIBLE_DEVICES=""

exec "${PYTHON}" yolo_detect_server.py \
  --broker "${YOLO_DETECT_BROKER:-127.0.0.1}" \
  --port "${YOLO_DETECT_PORT:-1883}" \
  --request-topic "${YOLO_DETECT_REQUEST_TOPIC:-/yolo_detect/}" \
  --result-topic "${YOLO_DETECT_RESULT_TOPIC:-/yolo_detect_result}" \
  --model "${YOLO_DETECT_MODEL:-shelf.pt}" \
  --device "${YOLO_DETECT_DEVICE:-cpu}" \
  --work-dir "${YOLO_DETECT_WORK_DIR:-runs}" \
  "$@"
