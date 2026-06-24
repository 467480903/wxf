# 4060 GPU deployment for WXF YOLO Detect MQTT

This folder is a deployment template for running the YOLO detect server on a
separate 4060 machine.

Recommended production topology:

```text
G2 robot
  Gateway HTTP camera endpoints
  run_client_gateway.sh / detect_once()
      |
      | MQTT to 4060_IP:1883
      v
4060 machine
  mosquitto vision broker
  wxf-yolo-detect-mqtt-gpu.service
  yolo_detect_server.py with YOLO_DETECT_DEVICE=cuda:0
```

The robot still captures RGB and raw depth through the Gateway. The 4060 only
does inference and publishes the result. The 4060 service must not import GDK
and must not publish motion commands.

## 1. Copy files to the 4060

Example target path:

```bash
/opt/wxf/yolo_detect_mqtt_service
```

Copy this whole service directory to that path and place the model here:

```bash
/opt/wxf/yolo_detect_mqtt_service/shelf.pt
```

## 2. Prepare Python on the 4060

Use a Python environment that already has CUDA-capable PyTorch and the project
dependencies installed:

```text
ultralytics
opencv-python
numpy
paho-mqtt
```

Do not hard-code a PyTorch install command without checking the CUDA driver and
CUDA runtime on the actual 4060 machine.

## 3. Run a manual smoke test first

Start or verify a Mosquitto broker on the 4060, then run:

```bash
cd /opt/wxf/yolo_detect_mqtt_service

YOLO_DETECT_PYTHON=/opt/wxf/yolo-env/bin/python \
YOLO_DETECT_BROKER=127.0.0.1 \
YOLO_DETECT_PORT=1883 \
YOLO_DETECT_REQUEST_TOPIC=/yolo_detect_gpu_test/ \
YOLO_DETECT_RESULT_TOPIC=/yolo_detect_gpu_test_result \
YOLO_DETECT_MODEL=/opt/wxf/yolo_detect_mqtt_service/shelf.pt \
YOLO_DETECT_DEVICE=cuda:0 \
YOLO_DETECT_WORK_DIR=/data/wxf_yolo_detect/runs \
./run_server_gpu.sh --traceback-on-error
```

From the robot, test against the 4060 broker:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service

YOLO_DETECT_BROKER=<4060_IP> \
YOLO_DETECT_REQUEST_TOPIC=/yolo_detect_gpu_test/ \
YOLO_DETECT_RESULT_TOPIC=/yolo_detect_gpu_test_result \
./run_client_gateway.sh --timeout-s 180 --http-timeout-s 15
```

## 4. Production topics

After the test topic works, production can use the standard topics:

```text
/yolo_detect/
/yolo_detect_result
```

Robot command:

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service

YOLO_DETECT_BROKER=<4060_IP> \
./run_client_gateway.sh --timeout-s 180 --http-timeout-s 15
```

Python business scripts should pass the 4060 broker:

```python
from yolo_detect_gateway_client import detect_once

result = detect_once(
    gateway_url="http://127.0.0.1:8767",
    broker="<4060_IP>",
    port=1883,
    timeout_s=180,
    http_timeout_s=15,
    raise_on_error=False,
)
```

## 5. systemd template

Edit these two files before installing:

```text
deploy_4060/yolo-detect-mqtt-gpu.env
deploy_4060/systemd/wxf-yolo-detect-mqtt-gpu.service.example
```

At minimum, check:

```text
User=
EnvironmentFile=
WorkingDirectory=
YOLO_DETECT_PYTHON
YOLO_DETECT_MODEL
YOLO_DETECT_WORK_DIR
```

Then install on the 4060:

```bash
sudo cp deploy_4060/systemd/wxf-yolo-detect-mqtt-gpu.service.example /etc/systemd/system/wxf-yolo-detect-mqtt-gpu.service
sudo cp deploy_4060/yolo-detect-mqtt-gpu.env /opt/wxf/yolo_detect_mqtt_service/yolo-detect-mqtt-gpu.env
sudo systemctl daemon-reload
sudo systemctl enable --now wxf-yolo-detect-mqtt-gpu.service
```

Check logs:

```bash
systemctl is-active wxf-yolo-detect-mqtt-gpu.service
journalctl -u wxf-yolo-detect-mqtt-gpu.service -n 100 --no-pager
```

## 6. Boundary rules

- Keep robot motion Gateway and 4060 vision broker logically separate.
- Do not run both the robot CPU YOLO service and the 4060 GPU YOLO service on
  the same production topic unless you intentionally want duplicate consumers.
- Use test topics first, then switch production topics after one successful
  end-to-end run.
- If the robot cannot reach `<4060_IP>:1883`, fix network/firewall/broker bind
  first. Do not fall back to GDK inside the business script.
