#!/usr/bin/env python3
import agibot_gdk
import time
import json
import os
import threading
import paho.mqtt.client as mqtt
from pathlib import Path

# --- 配置区 ---
POSITIONS_DIR = "/data/ggyss/wxf/positions"
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
        
        # 检查数据格式 - 兼容两种格式：简单字典格式和完整状态格式
        if "states" in pos_data and isinstance(pos_data["states"], list):
            # 完整状态格式，提取motor_position
            joint_data = {}
            for state in pos_data["states"]:
                if "name" in state and "motor_position" in state:
                    joint_data[state["name"]] = state["motor_position"]
            pos_data = joint_data
        # 否则假设已经是简单字典格式 {joint_name: position}
        
        # 打印可用的关节数据进行调试
        print(f"可用关节数据: {list(pos_data.keys())}")
        
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

# --- 辅助函数：获取关节位置，支持多种名称格式 ---
def get_joint_position(pos_data, *possible_names):
    """尝试多种可能的关节名称，返回找到的位置值"""
    for name in possible_names:
        if name in pos_data:
            return pos_data[name]
    # 如果都没找到，返回0.0
    return 0.0

# --- 运动控制函数 ---
def move_waist(pos_data):
    """控制腰部和腿部运动"""
    try:
        # 提取腰部关节数据，支持多种名称格式
        waist_positions = [
            get_joint_position(pos_data, "idx01_body_joint1", "body_joint1", "joint1", "Body_Joint1"),
            get_joint_position(pos_data, "idx02_body_joint2", "body_joint2", "joint2", "Body_Joint2"),
            get_joint_position(pos_data, "idx03_body_joint3", "body_joint3", "joint3", "Body_Joint3"),
            get_joint_position(pos_data, "idx04_body_joint4", "body_joint4", "joint4", "Body_Joint4"),
            get_joint_position(pos_data, "idx05_body_joint5", "body_joint5", "joint5", "Body_Joint5")
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
        # 提取左臂关节数据，支持多种名称格式
        left_arm_pos = [
            get_joint_position(pos_data, "idx21_arm_l_joint1", "arm_l_joint1", "left_arm_joint1", "LArm_Joint1"),
            get_joint_position(pos_data, "idx22_arm_l_joint2", "arm_l_joint2", "left_arm_joint2", "LArm_Joint2"),
            get_joint_position(pos_data, "idx23_arm_l_joint3", "arm_l_joint3", "left_arm_joint3", "LArm_Joint3"),
            get_joint_position(pos_data, "idx24_arm_l_joint4", "arm_l_joint4", "left_arm_joint4", "LArm_Joint4"),
            get_joint_position(pos_data, "idx25_arm_l_joint5", "arm_l_joint5", "left_arm_joint5", "LArm_Joint5"),
            get_joint_position(pos_data, "idx26_arm_l_joint6", "arm_l_joint6", "left_arm_joint6", "LArm_Joint6"),
            get_joint_position(pos_data, "idx27_arm_l_joint7", "arm_l_joint7", "left_arm_joint7", "LArm_Joint7")
        ]
        
        # 提取右臂关节数据，支持多种名称格式
        right_arm_pos = [
            get_joint_position(pos_data, "idx61_arm_r_joint1", "arm_r_joint1", "right_arm_joint1", "RArm_Joint1"),
            get_joint_position(pos_data, "idx62_arm_r_joint2", "arm_r_joint2", "right_arm_joint2", "RArm_Joint2"),
            get_joint_position(pos_data, "idx63_arm_r_joint3", "arm_r_joint3", "right_arm_joint3", "RArm_Joint3"),
            get_joint_position(pos_data, "idx64_arm_r_joint4", "arm_r_joint4", "right_arm_joint4", "RArm_Joint4"),
            get_joint_position(pos_data, "idx65_arm_r_joint5", "arm_r_joint5", "right_arm_joint5", "RArm_Joint5"),
            get_joint_position(pos_data, "idx66_arm_r_joint6", "arm_r_joint6", "right_arm_joint6", "RArm_Joint6"),
            get_joint_position(pos_data, "idx67_arm_r_joint7", "arm_r_joint7", "right_arm_joint7", "RArm_Joint7")
        ]
        
        # 合并为机器人接口所需的 14 个关节数组
        arm_positions = left_arm_pos + right_arm_pos
        arm_velocities = [0.2] * 14
        
        # 打印调试信息
        print(f"左臂关节位置：{left_arm_pos}")
        print(f"右臂关节位置：{right_arm_pos}")
        
        # 检查是否所有关节位置都是 0
        if all(p == 0.0 for p in left_arm_pos) and all(p == 0.0 for p in right_arm_pos):
            print("警告：所有手臂关节位置都是 0，可能关节名称不匹配")
        
        # 执行手臂运动（添加超时参数2，与move_arm_joint.py一致）
        robot.move_arm_joint(arm_positions, arm_velocities, 2)
        print("上肢运动完成")
        
    except Exception as e:
        print(f"上肢运动失败: {e}")
        raise

def move_head(pos_data):
    """控制头部运动"""
    try:
        # 提取头部关节数据，支持多种名称格式
        head_positions = [
            get_joint_position(pos_data, "idx11_head_joint1", "head_joint1", "Head_Joint1"),
            get_joint_position(pos_data, "idx12_head_joint2", "head_joint2", "Head_Joint2"),
            get_joint_position(pos_data, "idx13_head_joint3", "head_joint3", "Head_Joint3")
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
            client.publish(topic, json.dumps(payload), qos=1)
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