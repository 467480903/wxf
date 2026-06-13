#!/bin/bash
# 监听 MQTT topic /pick_standby/caculate_offset/
# 需要先安装 mosquitto_sub: sudo apt install mosquitto-clients

MQTT_BROKER="localhost"
MQTT_PORT=1883
MQTT_TOPIC="/pick_standby/caculate_offset/"

echo "正在监听 MQTT topic: ${MQTT_TOPIC}"
echo "Broker: ${MQTT_BROKER}:${MQTT_PORT}"
echo "----------------------------------------"

mosquitto_sub -h "${MQTT_BROKER}" -p "${MQTT_PORT}" -t "${MQTT_TOPIC}" -q 2
