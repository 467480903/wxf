import paho.mqtt.client as mqtt
import time

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# 当连接成功时的回调函数
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    # 订阅主题
    client.subscribe("test")
    print("订阅主题: test")

# 当收到消息时的回调函数
def on_message(client, userdata, msg):
    print(f"收到消息: {msg.topic} -> {msg.payload.decode()}")

# 创建MQTT客户端
client = mqtt.Client()

# 设置回调函数
client.on_connect = on_connect
client.on_message = on_message

# 连接到MQTT broker
try:
    print(f"尝试连接到MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    print(f"连接到MQTT broker成功: {MQTT_BROKER}:{MQTT_PORT}")
except Exception as e:
    print(f"连接MQTT broker失败: {e}")
    exit(1)

# 开始循环
print("进入消息循环...")
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("用户中断，退出程序")
except Exception as e:
    print(f"发生错误: {e}")
finally:
    print("程序退出")
