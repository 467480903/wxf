#!/usr/bin/env python3
import agibot_gdk
import time
import json
import paho.mqtt.client as mqtt
from pathlib import Path

# --- 配置区 ---
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
MQTT_TOPIC = "/save_joint_states"

# --- 全局变量 ---
robot = None
client = None

# --- MQTT 消息回调 ---
def on_message(client, userdata, msg):
    """处理收到的MQTT消息"""
    try:
        payload = json.loads(msg.payload.decode())
        save_name = payload.get("name")
        
        if not save_name:
            print("错误: 消息中缺少 'name' 字段")
            return
        
        print(f"收到保存关节状态的请求，保存名称: {save_name}")
        save_joint_states(save_name)
        
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
    except Exception as e:
        print(f"消息处理失败: {e}")

# --- 保存关节状态函数 ---
def save_joint_states(save_name):
    """保存关节状态到JSON文件"""
    if not robot:
        print("错误: 机器人未初始化")
        return
    
    try:
        # 获取关节状态
        joint_states = robot.get_joint_states()
        
        if not joint_states or "states" not in joint_states:
            print("错误: 无法获取关节状态")
            return
        
        # 准备要保存的数据
        data_to_save = {
            "timestamp": joint_states.get("timestamp"),
            "nums": joint_states.get("nums"),
            "states": []
        }
        
        # 收集所有关节的详细数据
        for state in joint_states["states"]:
            joint_data = {
                "name": state["name"],
                "position": round(state["position"], 6),
                "velocity": round(state["velocity"], 6),
                "effort": round(state["effort"], 6),
                "motor_position": round(state["motor_position"], 6),
                "motor_current": round(state["motor_current"], 6),
                "error_code": state["error_code"]
            }
            data_to_save["states"].append(joint_data)
        
        # 定义保存目录为 wxf 文件夹下的 positions 文件夹
        save_dir = "/data/ggyss/wxf/positions"
        
        # 确保保存目录存在
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        filename = f"{save_dir}/{save_name}.json"
        
        # 保存为JSON文件
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        
        print(f"✅ 关节状态已成功保存到 {filename} 中")
        
    except Exception as e:
        print(f"❌ 保存关节状态失败: {e}")

# --- 初始化函数 ---
def init_robot():
    """初始化机器人"""
    global robot
    
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK初始化失败")
        return False
    
    robot = agibot_gdk.Robot()
    time.sleep(2)  # 等待机器人初始化
    
    print("机器人初始化成功")
    return True

# --- 初始化MQTT客户端 ---
def init_mqtt():
    """初始化MQTT客户端"""
    global client
    
    client = mqtt.Client()
    client.on_message = on_message
    client.on_connect = lambda c, u, f, rc: (
        print(f"MQTT连接成功，返回码: {rc}"),
        c.subscribe(MQTT_TOPIC)
    )
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"MQTT客户端已连接到 {MQTT_BROKER}:{MQTT_PORT}")
        return True
    except Exception as e:
        print(f"MQTT连接失败: {e}")
        return False

# --- 主函数 ---
def main():
    print("启动关节状态保存服务...")
    
    # 初始化机器人
    if not init_robot():
        return
    
    # 初始化MQTT客户端
    if not init_mqtt():
        agibot_gdk.gdk_release()
        return
    
    print(f"服务已启动，监听主题: {MQTT_TOPIC}")
    print("等待保存关节状态的请求...")
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        # 释放资源
        if client:
            client.disconnect()
        
        if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
            print("GDK释放失败")
        else:
            print("GDK资源已释放")

if __name__ == "__main__":
    main()