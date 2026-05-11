#!/usr/bin/env python3
import agibot_gdk
import time
import json
import os
import threading
import paho.mqtt.client as mqtt
from pathlib import Path

# --- 配置区 ---
POSITIONS_DIR = "positions"
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
TOPIC_CONTROL_FILE = "/whold_body_control_file"
TOPIC_CONTROL_STATUS = "/whole_body_control"
TOPIC_CONTROL_REQUEST = "/whole_body_control_request"
TOPIC_CONTROL_RESPONSE = "/whole_body_control_response"

# --- 全局变量 ---
robot = None
client = None
is_moving = False

# --- MQTT 消息回调 ---
def on_message(client, userdata, msg):
    """处理收到的MQTT消息"""
    try:
        payload = json.loads(msg.payload.decode())
        
        if msg.topic == TOPIC_CONTROL_FILE:
            # 处理控制文件消息
            handle_control_file(payload)
        elif msg.topic == TOPIC_CONTROL_REQUEST:
            # 处理控制请求
            handle_control_request(payload)
            
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
    except Exception as e:
        print(f"消息处理失败: {e}")

# --- 处理控制文件消息 ---
def handle_control_file(payload):
    """处理控制文件消息"""
    global is_moving
    
    if is_moving:
        print("机器人正在运动中，无法执行新的命令")
        return
    
    file_name = payload.get("name")
    if not file_name:
        print("错误: 消息中缺少 'name' 字段")
        return
    
    # 构建文件路径
    file_path = os.path.join(POSITIONS_DIR, f"{file_name}.json")
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在: {file_path}")
        return
    
    print(f"开始执行全身控制: {file_name}.json")
    
    try:
        # 读取JSON文件
        with open(file_path, "r", encoding="utf-8") as f:
            pos_data = json.load(f)
        
        # 发送开始运动的状态
        publish_message(TOPIC_CONTROL_STATUS, {"states": "running"})
        is_moving = True
        
        # 启动三个线程同时控制
        threads = []
        
        # 腿部腰部线程
        thread_waist = threading.Thread(target=move_waist, args=(pos_data,))
        threads.append(thread_waist)
        
        # 上肢线程
        thread_arm = threading.Thread(target=move_arm, args=(pos_data,))
        threads.append(thread_arm)
        
        # 头部线程
        thread_head = threading.Thread(target=move_head, args=(pos_data,))
        threads.append(thread_head)
        
        # 启动所有线程
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 发送运动完成的状态
        publish_message(TOPIC_CONTROL_STATUS, {"states": "done"})
        print(f"全身控制执行完成: {file_name}.json")
        
    except Exception as e:
        print(f"全身控制执行失败: {e}")
        publish_message(TOPIC_CONTROL_STATUS, {"states": "error", "message": str(e)})
    finally:
        is_moving = False

# --- 处理控制请求 ---
def handle_control_request(payload):
    """处理控制请求"""
    command = payload.get("command")
    
    if command == "read_file_list":
        # 读取文件列表
        try:
            if not os.path.exists(POSITIONS_DIR):
                os.makedirs(POSITIONS_DIR)
                
            # 获取所有.json文件
            json_files = [f[:-5] for f in os.listdir(POSITIONS_DIR) if f.endswith(".json")]
            json_files.sort()
            
            # 发送文件列表
            publish_message(TOPIC_CONTROL_RESPONSE, {
                "command": "file_list",
                "files": json_files
            })
            
            print(f"已读取文件列表: {json_files}")
            
        except Exception as e:
            print(f"读取文件列表失败: {e}")
            publish_message(TOPIC_CONTROL_RESPONSE, {
                "command": "file_list",
                "files": [],
                "error": str(e)
            })

# --- 运动控制函数 ---
def move_waist(pos_data):
    """控制腰部和腿部运动"""
    try:
        # 提取腰部关节数据
        waist_positions = [
            pos_data.get("idx01_body_joint1", 0.0),
            pos_data.get("idx02_body_joint2", 0.0),
            pos_data.get("idx03_body_joint3", 0.0),
            pos_data.get("idx04_body_joint4", 0.0),
            pos_data.get("idx05_body_joint5", 0.0)
        ]
        
        waist_velocities = [0.3] * 5
        
        # 执行腰部运动
        robot.move_waist_joint(waist_positions, waist_velocities)
        print("腰部运动完成")
        
    except Exception as e:
        print(f"腰部运动失败: {e}")
        raise

def move_arm(pos_data):
    """控制上肢运动"""
    try:
        # 提取左臂关节数据
        left_arm_pos = [
            pos_data.get("idx21_arm_l_joint1", 0.0),
            pos_data.get("idx22_arm_l_joint2", 0.0),
            pos_data.get("idx23_arm_l_joint3", 0.0),
            pos_data.get("idx24_arm_l_joint4", 0.0),
            pos_data.get("idx25_arm_l_joint5", 0.0),
            pos_data.get("idx26_arm_l_joint6", 0.0),
            pos_data.get("idx27_arm_l_joint7", 0.0)
        ]
        
        # 提取右臂关节数据
        right_arm_pos = [
            pos_data.get("idx61_arm_r_joint1", 0.0),
            pos_data.get("idx62_arm_r_joint2", 0.0),
            pos_data.get("idx63_arm_r_joint3", 0.0),
            pos_data.get("idx64_arm_r_joint4", 0.0),
            pos_data.get("idx65_arm_r_joint5", 0.0),
            pos_data.get("idx66_arm_r_joint6", 0.0),
            pos_data.get("idx67_arm_r_joint7", 0.0)
        ]
        
        # 合并为机器人接口所需的 14 个关节数组
        arm_positions = left_arm_pos + right_arm_pos
        arm_velocities = [0.2] * 14
        
        # 执行手臂运动
        robot.move_arm_joint(arm_positions, arm_velocities)
        print("上肢运动完成")
        
    except Exception as e:
        print(f"上肢运动失败: {e}")
        raise

def move_head(pos_data):
    """控制头部运动"""
    try:
        # 提取头部关节数据
        head_positions = [
            pos_data.get("idx11_head_joint1", 0.0),
            pos_data.get("idx12_head_joint2", 0.0),
            pos_data.get("idx13_head_joint3", 0.0)
        ]
        
        head_velocities = [0.3] * 3
        
        # 执行头部运动
        robot.move_head_joint(head_positions, head_velocities)
        print("头部运动完成")
        
    except Exception as e:
        print(f"头部运动失败: {e}")
        raise

# --- MQTT 发布消息 ---
def publish_message(topic, payload):
    """发布MQTT消息"""
    if client and client.is_connected():
        try:
            message = mqtt.MQTTMessage()
            message.payload = json.dumps(payload).encode()
            message.topic = topic
            client.publish(message)
            print(f"已发布消息到主题 {topic}: {payload}")
        except Exception as e:
            print(f"发布消息失败: {e}")

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
        c.subscribe([
            (TOPIC_CONTROL_FILE, 0),
            (TOPIC_CONTROL_REQUEST, 0)
        ])
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
    print("启动全身关节控制服务...")
    
    # 确保positions目录存在
    if not os.path.exists(POSITIONS_DIR):
        os.makedirs(POSITIONS_DIR)
        print(f"已创建目录: {POSITIONS_DIR}")
    
    # 初始化机器人
    if not init_robot():
        return
    
    # 初始化MQTT客户端
    if not init_mqtt():
        agibot_gdk.gdk_release()
        return
    
    print(f"服务已启动，监听主题:")
    print(f"  - {TOPIC_CONTROL_FILE}")
    print(f"  - {TOPIC_CONTROL_REQUEST}")
    print("等待控制命令...")
    
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