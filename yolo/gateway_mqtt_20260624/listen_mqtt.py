#!/usr/bin/env python3
"""
监听 MQTT topic /pick_standby/caculate_offset/
实时打印收到的偏移量计算结果
"""

import paho.mqtt.client as mqtt
import json

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "/pick_standby/caculate_offset/"
MQTT_CLIENT_ID = "yolo_offset_listener"


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[MQTT] 已连接到 {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC, qos=2)
        print(f"[MQTT] 已订阅: {MQTT_TOPIC}")
        print("等待接收消息...")
        print("-" * 60)
    else:
        print(f"[MQTT] 连接失败，返回码: {rc}")


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
        print(f"[收到消息] topic: {msg.topic}")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("-" * 60)
    except Exception as e:
        print(f"[解析失败] {e}")
        print(f"原始消息: {msg.payload}")


# 创建 MQTT 客户端（使用 v2 API 避免 DeprecationWarning）
mqtt_client = mqtt.Client(
    client_id=MQTT_CLIENT_ID,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_client.loop_forever()
except KeyboardInterrupt:
    print("\n[退出] 用户中断")
    mqtt_client.disconnect()
except Exception as e:
    print(f"[错误] {e}")
