#!/usr/bin/env python3
"""
使用paho-mqtt库测试MQTT over WebSocket
"""

import paho.mqtt.client as mqtt
import json
import time

# 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 9001  # WebSocket端口
MQTT_TOPIC = "/joints_read"
CLIENT_ID = "test_websocket_client"
TEST_DURATION = 15  # 测试持续时间（秒）

# 统计信息
message_count = 0
start_time = None


def on_connect(client, userdata, flags, rc):
    """连接回调"""
    global start_time
    print(f"✅ 连接成功，返回码: {rc}")
    print(f"🔍 订阅主题: {MQTT_TOPIC}")
    client.subscribe(MQTT_TOPIC, qos=1)
    start_time = time.time()


def on_message(client, userdata, msg):
    """消息回调"""
    global message_count
    message_count += 1
    try:
        payload = json.loads(msg.payload.decode())
        print(f"📥 收到消息 #{message_count} 来自主题 [{msg.topic}]")
        # 打印前几个关节数据
        first_joints = {k: v for k, v in list(payload.items())[:3]}
        print(f"   部分数据: {json.dumps(first_joints, indent=2)}")
        print(f"   总关节数: {len(payload)}个")
    except json.JSONDecodeError:
        print(f"📥 收到消息 #{message_count} 来自主题 [{msg.topic}]")
        print(f"   原始数据: {msg.payload.decode()}")
    except Exception as e:
        print(f"❌ 解析消息失败: {e}")


def on_subscribe(client, userdata, mid, granted_qos):
    """订阅回调"""
    print(f"✅ 订阅确认，QoS: {granted_qos}")


def on_disconnect(client, userdata, rc):
    """断开连接回调"""
    print(f"🔒 连接断开，返回码: {rc}")


def main():
    """主函数"""
    print("🚀 开始测试MQTT over WebSocket...")
    print(f"📝 配置: 代理={MQTT_BROKER}, 端口={MQTT_PORT}, 主题={MQTT_TOPIC}")
    print(f"⏰ 测试将持续 {TEST_DURATION} 秒")
    
    # 创建MQTT客户端，指定使用WebSocket
    client = mqtt.Client(client_id=CLIENT_ID, transport="websockets")
    
    # 设置回调函数
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    
    try:
        # 连接到MQTT代理
        print("🔄 正在连接到MQTT代理...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # 启动客户端循环
        client.loop_start()
        
        # 等待测试结束
        time.sleep(TEST_DURATION)
        
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
    finally:
        # 清理资源
        client.loop_stop()
        client.disconnect()
    
    # 打印测试结果
    print("\n📊 测试结果:")
    print(f"   收到消息数: {message_count}")
    if message_count > 0 and start_time:
        duration = time.time() - start_time
        print(f"   平均频率: {message_count / duration:.2f} Hz")
    print(f"   测试时长: {TEST_DURATION} 秒")
    
    if message_count > 0:
        print("✅ MQTT over WebSocket通信正常！")
    else:
        print("❌ 未收到任何消息，请检查配置")


if __name__ == "__main__":
    main()