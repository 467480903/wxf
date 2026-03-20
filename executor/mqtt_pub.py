import paho.mqtt.client as mqtt

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# 发送消息的函数
def publish_message(topic, message):
    # 创建MQTT客户端
    client = mqtt.Client()
    
    # 连接到MQTT broker
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"连接到MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"连接MQTT broker失败: {e}")
        return
    
    # 发送消息
    result = client.publish(topic, message)
    status = result[0]
    if status == 0:
        print(f"消息发送成功: {topic} -> {message}")
    else:
        print(f"消息发送失败: {topic}")
    
    # 断开连接
    client.disconnect()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("用法: python mqtt_pub.py <topic> <message>")
        print("示例: python mqtt_pub.py testtopic 1")
        sys.exit(1)
    
    topic = sys.argv[1]
    message = sys.argv[2]
    publish_message(topic, message)
