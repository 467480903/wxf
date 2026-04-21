#!/usr/bin/env python3
"""
测试WebSocket连接到MQTT代理
"""

import websocket
import json
import time
import threading

# WebSocket连接配置
WS_URL = "ws://localhost:9001/mqtt"
TOPIC = "/joints_read"
TEST_DURATION = 30  # 测试持续时间（秒）

# 连接状态
connected = False
received_messages = 0


def on_open(ws):
    """连接打开回调"""
    global connected
    print(f"✅ WebSocket连接已打开: {WS_URL}")
    connected = True
    
    # 订阅主题 - 使用标准MQTT WebSocket格式
    # 使用MQTT.js兼容的WebSocket消息格式
    subscribe_msg = json.dumps({
        "cmd": "subscribe",
        "topic": TOPIC,
        "qos": 1
    })
    print(f"📤 发送订阅消息: {subscribe_msg}")
    ws.send(subscribe_msg)
    print(f"🔍 开始监听主题: {TOPIC}")


def on_message(ws, message):
    """接收消息回调"""
    global received_messages
    received_messages += 1
    try:
        # 解析消息
        msg_obj = json.loads(message)
        if isinstance(msg_obj, dict) and "topic" in msg_obj and "payload" in msg_obj:
            print(f"📥 收到主题 [{msg_obj['topic']}] 的消息 (#{received_messages})")
            # 尝试解析payload
            try:
                payload = json.loads(msg_obj['payload'])
                print(f"   消息内容: {json.dumps(payload, indent=2)}")
            except json.JSONDecodeError:
                print(f"   原始payload: {msg_obj['payload']}")
        else:
            print(f"📥 收到未知格式消息 (#{received_messages}): {message}")
    except Exception as e:
        print(f"❌ 解析消息失败: {e}")
        print(f"   原始消息: {message}")


def on_error(ws, error):
    """连接错误回调"""
    print(f"❌ WebSocket错误: {error}")


def on_close(ws, close_status_code, close_msg):
    """连接关闭回调"""
    global connected
    print(f"🔒 WebSocket连接已关闭: {close_status_code}, {close_msg}")
    connected = False


def on_ping(ws, ping_data):
    """Ping回调"""
    print(f"🏓 收到Ping: {ping_data}")


def on_pong(ws, pong_data):
    """Pong回调"""
    print(f"🏓 发送Pong: {pong_data}")


def auto_close(ws, duration):
    """自动关闭连接"""
    print(f"⏰ 将在 {duration} 秒后自动关闭连接...")
    time.sleep(duration)
    ws.close()
    print("✅ 测试完成")


def main():
    """主函数"""
    print("🚀 开始测试WebSocket连接...")
    print(f"📝 测试配置: URL={WS_URL}, TOPIC={TOPIC}, DURATION={TEST_DURATION}s")
    
    # 创建WebSocket客户端
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_ping=on_ping,
        on_pong=on_pong
    )
    
    # 启动自动关闭线程
    close_thread = threading.Thread(target=auto_close, args=(ws, TEST_DURATION))
    close_thread.daemon = True
    close_thread.start()
    
    # 运行WebSocket客户端
    try:
        ws.run_forever(ping_interval=10, ping_timeout=5)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        ws.close()
    
    # 打印测试结果
    print(f"\n📊 测试结果:")
    print(f"   连接状态: {'成功' if connected else '已关闭'}")
    print(f"   收到消息数: {received_messages}")
    print(f"   测试时长: {TEST_DURATION}秒")
    
    if received_messages > 0:
        print("✅ WebSocket通信正常！")
    else:
        print("❌ 未收到任何消息，请检查配置或网络连接")


if __name__ == "__main__":
    main()