#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${YOLO_DETECT_PYTHON:-${ROOT_DIR}/../yolo/yolo-env/bin/python}"

cd "${ROOT_DIR}"

exec "${PYTHON}" yolo_detect_gateway_client.py \
  --gateway-url "${YOLO_DETECT_GATEWAY_URL:-http://127.0.0.1:8767}" \
  --broker "${YOLO_DETECT_BROKER:-127.0.0.1}" \
  --port "${YOLO_DETECT_PORT:-1883}" \
  --request-topic "${YOLO_DETECT_REQUEST_TOPIC:-/yolo_detect/}" \
  --result-topic "${YOLO_DETECT_RESULT_TOPIC:-/yolo_detect_result}" \
  --model-path "${YOLO_DETECT_MODEL:-shelf.pt}" \
  "$@"
