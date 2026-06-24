# WXF YOLO Detect MQTT Service

这个目录是独立的视觉 MQTT 服务，只做图片检测和深度计算，不直接控制机器人运动。

## 1. 先记住一句话

服务端负责长期运行：

```text
订阅 /yolo_detect/ -> 收 base64 图片 -> 保存文件 -> shelf.pt 推理 -> 发布 /yolo_detect_result
```

客户端负责发一次请求：

```text
读取 head.jpg + head_depth.raw -> 转 base64 -> 发到 /yolo_detect/ -> 等 /yolo_detect_result
```

这套服务不需要、也不应该在客户脚本里 `import agibot_gdk`。

## 2. 当前目录

机器人上目录：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service
```

关键文件：

```text
yolo_detect_server.py   # MQTT 服务端，常驻进程
yolo_detect_client.py   # 文件模式客户端，发一次 detect 请求
yolo_detect_core.py     # YOLO + depth raw 算法核心
run_server_cpu.sh       # 辉曦机器人本体 CPU 启动入口
run_server_gpu.sh       # 后续 4060 GPU 启动入口
run_client_files.sh     # 文件模式客户端启动入口
run_client_gateway.sh   # Gateway 实时抓拍客户端启动入口
shelf.pt                # 当前检测模型
head.jpg                # 测试 RGB 图片
head_depth.raw          # 测试 raw 深度，uint16，400x640
```

## 3. MQTT 报文

客户端发到 `/yolo_detect/`：

```json
{
  "cmd": "detect",
  "image": "base64-rgb-jpg",
  "depthimg": "base64-uint16-depth-raw"
}
```

实际客户端还会带这些辅助字段，方便匹配结果和调试：

```json
{
  "request_id": "detect-client-xxx",
  "model_path": "shelf.pt",
  "depth_shape": [400, 640],
  "depth_offset_px": 1
}
```

注意：

```text
depthimg 必须是 head_depth.raw 的 base64。
depthimg 不是 head_depth.jpg。
如果传的是深度伪彩色 JPG，只能看图，不能算毫米深度。
```

服务端发布到 `/yolo_detect_result`：

```json
{
  "status": "success",
  "request_id": "detect-client-xxx",
  "model_path": "shelf.pt",
  "image_path": "head.jpg",
  "depth_raw_path": "head_depth.raw",
  "detection": {},
  "offset": {},
  "slope": {},
  "depth": {},
  "output_files": []
}
```

失败时也会发结果：

```json
{
  "status": "error",
  "request_id": "detect-client-xxx",
  "error": "错误原因"
}
```

所以客户端不要只等成功，也要把 `status=error` 打出来。

## 4. 在机器人本体 CPU 启动服务端

打开一个终端，执行：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service
./run_server_cpu.sh
```

看到下面这些，表示服务端已经准备好：

```text
[server] loading model=shelf.pt device=cpu
[server] model loaded
[mqtt] connected broker=127.0.0.1:1883
[mqtt] subscribed /yolo_detect/
```

这个脚本会强制 CPU：

```text
CUDA_VISIBLE_DEVICES=""
device=cpu
```

原因是机器人本体不是 NVIDIA 4060，先按辉曦机器本体 CPU 模式跑，稳定优先。

## 4.1 开机自启动 systemd 服务

当前机器人上安装的常驻服务名：

```text
wxf-yolo-detect-mqtt.service
```

systemd unit 文件：

```text
/etc/systemd/system/wxf-yolo-detect-mqtt.service
```

服务配置文件：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service/yolo-detect-mqtt.env
```

查看服务是否开机自启动：

```bash
systemctl is-enabled wxf-yolo-detect-mqtt.service
```

查看服务是否正在运行：

```bash
systemctl is-active wxf-yolo-detect-mqtt.service
```

看最近日志：

```bash
journalctl -u wxf-yolo-detect-mqtt.service -n 100 --no-pager
```

实时跟日志：

```bash
journalctl -u wxf-yolo-detect-mqtt.service -f
```

重启服务：

```bash
sudo systemctl restart wxf-yolo-detect-mqtt.service
```

停止服务：

```bash
sudo systemctl stop wxf-yolo-detect-mqtt.service
```

## 5. 用文件客户端发一次测试请求

保持服务端终端不要关，另开一个终端执行：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service
./run_client_files.sh --timeout-s 180
```

成功时会打印完整 JSON，并写入：

```text
last_yolo_detect_result.json
```

当前样例已验证成功：

```text
status=success
device=cpu
latency_ms 约 1900
detection counts: a=1, b=1
horizontal_offset_px=-4.56
direction=偏左
```

CPU 推理速度会受机器负载、模型大小、图片大小影响，后续现场不要把 1.9 秒当成固定 SLA。

## 5.1 用 Gateway 实时抓拍并检测

这个方式不需要客户脚本 import GDK。客户端只通过 HTTP 调 Gateway：

```text
GET /api/cameras/head_rgb/snapshot.jpg
GET /api/cameras/head_depth/raw
```

然后客户端把 RGB JPG 和 raw depth 转 base64，发到 `/yolo_detect/`。

运行：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service
./run_client_gateway.sh --timeout-s 180
```

如果 Gateway 不在本机：

```bash
YOLO_DETECT_GATEWAY_URL=http://机器人IP:8767 \
./run_client_gateway.sh --timeout-s 180
```

抓拍文件会保存到：

```text
captures/YYYYMMDD_HHMMSS_request_id/
```

里面有：

```text
head.jpg
head_depth.raw
capture_meta.json
```

注意：

```text
/api/cameras/head_depth/raw 必须可用。
如果返回 503，先看 g2-industrial-gateway.service 是否启用了 camera snapshots。
```

## 5.2 客户脚本最短 Python 调用

对接方现在只需要最简单的 MQTT 调用方式：业务脚本调用 `detect_once()`，
由这个函数完成实时抓拍、base64 编码、发送 `/yolo_detect/`、等待 `/yolo_detect_result`。

这个调用不会 import GDK，也不会初始化或释放 GDK。GDK 只在常驻 Gateway 服务里使用一次，
客户脚本只走 HTTP + MQTT，所以不会在每个业务脚本里反复消耗 GDK 启停时间。

推荐写法：

```python
from yolo_detect_gateway_client import detect_once

result = detect_once(
    gateway_url="http://127.0.0.1:8767",
    broker="127.0.0.1",
    port=1883,
    http_timeout_s=15,
    timeout_s=180,
    # 推荐设置 False：检测失败时返回完整 error JSON，业务脚本自己决定怎么停。
    raise_on_error=False,
)

if result["status"] != "success":
    print("YOLO_DETECT_FAILED:", result.get("error"))
    raise SystemExit(1)

print(result["offset"]["horizontal_offset_px"])
print(result["offset"]["direction"])
```

原始 JSON demo：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service
./demo_detect_once.py
```

如果只想用命令行跑一遍实时链路：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service
./run_client_gateway.sh --timeout-s 180 --http-timeout-s 15
```

注意：

```text
detect_once() 默认遇到 status=error 会抛 RuntimeError。
如果业务脚本想自己处理 error JSON，调用时加 raise_on_error=False。
当前画面没有 a/b/c/d 目标时，服务会返回 status=error，这是正常业务结果，不是 MQTT 断了。
业务动作脚本不要直接忽略 status=error，必须停止后续动作。
```

## 5.3 可选内部备用：detect_shelf / profile / guard

这部分当前对接方不需要。不要把 `detect_shelf()`、`shelf_guard_profiles.json`
或 `demo_detect_shelf_profile.py` 当成他们必须接入的流程。

这些文件只是内部备用能力：以后如果工艺负责人明确要把偏移、角度、深度阈值固化成视觉门禁，
再启用 profile/guard 层。默认对外说明只讲 `detect_once()`。

保留的内部备用文件：

```text
yolo_detect_shelf_api.py
shelf_guard_profiles.json
demo_detect_shelf_guard.py
demo_detect_shelf_profile.py
business_guard_template.py
```


## 6. 输出文件在哪里

每次请求单独保存到：

```text
runs/requests/YYYYMMDD_HHMMSS_request_id/
```

里面包含：

```text
head.jpg
head_depth.raw
request_meta.json
yolo_depth_rgb.jpg
yolo_depth_rgb_with_depth.jpg
yolo_depth_depth.jpg
yolo_depth_depth_marked.jpg
result.jpg
yolo_depth_result.json
mqtt_result.json
```

排查问题优先看：

```text
mqtt_result.json        # MQTT 返回给客户端的最终结果
request_meta.json       # 收到的图片字节数、字段列表
result.jpg              # RGB 检测标注图
yolo_depth_result.json  # 算法核心原始结果
```

## 7. 常用参数

切 broker：

```bash
YOLO_DETECT_BROKER=127.0.0.1 ./run_client_files.sh --timeout-s 180
```

切 topic：

```bash
YOLO_DETECT_REQUEST_TOPIC=/yolo_detect/ \
YOLO_DETECT_RESULT_TOPIC=/yolo_detect_result \
./run_client_files.sh --timeout-s 180
```

切输入文件：

```bash
YOLO_DETECT_RGB_PATH=/path/to/head.jpg \
YOLO_DETECT_DEPTH_RAW_PATH=/path/to/head_depth.raw \
./run_client_files.sh --timeout-s 180
```

指定模型：

```bash
YOLO_DETECT_MODEL=/data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service/shelf.pt \
./run_server_cpu.sh
```

## 8. 迁移到 4060 怎么做

推荐生产架构：

```text
机器人本体:
  Gateway 提供 RGB + raw depth HTTP 接口
  run_client_gateway.sh / detect_once() 负责抓拍和发 MQTT
      |
      | MQTT: <4060_IP>:1883
      v
4060:
  独立视觉 Mosquitto broker
  yolo_detect_server.py + shelf.pt + cuda:0
```

这样机器人业务脚本仍然不 import GDK，也不跑 CPU YOLO。
4060 只做视觉推理，不发任何机器人运动命令。

为什么推荐 4060 上单独跑视觉 broker：

```text
1. 不需要把机器人动作 Gateway 的 MQTT broker 暴露给外部机器。
2. 视觉 MQTT 和动作 MQTT 边界清楚。
3. 机器人 CPU YOLO 服务可以继续保留为备用，但不会收到发往 4060 broker 的请求。
4. 对接方脚本只需要把 broker 改成 4060 IP。
```

4060 上准备：

```bash
cd /opt/wxf/yolo_detect_mqtt_service

YOLO_DETECT_PYTHON=/opt/wxf/yolo-env/bin/python \
YOLO_DETECT_BROKER=127.0.0.1 \
YOLO_DETECT_PORT=1883 \
YOLO_DETECT_MODEL=/opt/wxf/yolo_detect_mqtt_service/shelf.pt \
YOLO_DETECT_DEVICE=cuda:0 \
YOLO_DETECT_WORK_DIR=/data/wxf_yolo_detect/runs \
./run_server_gpu.sh --traceback-on-error
```

先用测试 topic，不影响正式链路：

```bash
cd /opt/wxf/yolo_detect_mqtt_service

YOLO_DETECT_PYTHON=/opt/wxf/yolo-env/bin/python \
YOLO_DETECT_BROKER=127.0.0.1 \
YOLO_DETECT_REQUEST_TOPIC=/yolo_detect_gpu_test/ \
YOLO_DETECT_RESULT_TOPIC=/yolo_detect_gpu_test_result \
YOLO_DETECT_MODEL=/opt/wxf/yolo_detect_mqtt_service/shelf.pt \
YOLO_DETECT_DEVICE=cuda:0 \
YOLO_DETECT_WORK_DIR=/data/wxf_yolo_detect/runs \
./run_server_gpu.sh --traceback-on-error
```

机器人侧测试 4060：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service

YOLO_DETECT_BROKER=4060机器IP \
YOLO_DETECT_REQUEST_TOPIC=/yolo_detect_gpu_test/ \
YOLO_DETECT_RESULT_TOPIC=/yolo_detect_gpu_test_result \
./run_client_gateway.sh --timeout-s 180 --http-timeout-s 15
```

测试通过后切正式 topic：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo_detect_mqtt_service

YOLO_DETECT_BROKER=4060机器IP \
./run_client_gateway.sh --timeout-s 180 --http-timeout-s 15
```

业务 Python 脚本只需要改 broker：

```python
from yolo_detect_gateway_client import detect_once

result = detect_once(
    gateway_url="http://127.0.0.1:8767",
    broker="4060机器IP",
    port=1883,
    http_timeout_s=15,
    timeout_s=180,
    raise_on_error=False,
)
```

4060 常驻服务模板在：

```text
deploy_4060/
```

里面包含：

```text
deploy_4060/README.md
deploy_4060/yolo-detect-mqtt-gpu.env
deploy_4060/systemd/wxf-yolo-detect-mqtt-gpu.service.example
```

注意：

```text
如果机器人 CPU YOLO 服务和 4060 GPU YOLO 服务订阅同一个 broker/topic，会产生重复消费者。
推荐 4060 使用独立 broker；机器人客户端通过 YOLO_DETECT_BROKER=4060机器IP 指过去。
如果必须共用机器人 broker，先用测试 topic，正式切换时要停掉或改走机器人 CPU YOLO 服务。
```

## 9. 安全边界

这个目录里的 YOLO detect 服务：

```text
不发布机器人运动命令。
不调用 GDK。
不初始化或释放 GDK。
不改急停、力矩、速度、关节限位。
不修改原始 /data/wxf/wxf/yolo 或 BOX_528_1 脚本。
```

它只做 MQTT、文件保存、YOLO 推理、深度计算和结果发布。
