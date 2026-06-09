#!/usr/bin/env python3
"""
关节控制服务
- 以30Hz频率发布所有关节数据到/joints_read
- 监听/joint_set主题接收关节控制命令
- 实际从机器人获取关节数据
"""

import time
import json
import paho.mqtt.client as mqtt
import threading
import agibot_gdk

# MQTT配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_JOINTS_READ = "/joints_read"
TOPIC_JOINT_SET = "/joint_set"

# 机器人对象
robot = None

# 机器人关节列表（实际关节名称）
JOINT_LIST = [
    # 身体关节（腰部相关）
    "idx01_body_joint1", "idx02_body_joint2", "idx03_body_joint3",
    "idx04_body_joint4", "idx05_body_joint5",
    # 头部关节
    "idx11_head_joint1", "idx12_head_joint2", "idx13_head_joint3",
    # 左臂关节
    "idx21_arm_l_joint1", "idx22_arm_l_joint2", "idx23_arm_l_joint3",
    "idx24_arm_l_joint4", "idx25_arm_l_joint5", "idx26_arm_l_joint6",
    "idx27_arm_l_joint7",
    # 右臂关节
    "idx61_arm_r_joint1", "idx62_arm_r_joint2", "idx63_arm_r_joint3",
    "idx64_arm_r_joint4", "idx65_arm_r_joint5", "idx66_arm_r_joint6",
    "idx67_arm_r_joint7"
]

# 关节数据存储
joint_data = {joint: 0.0 for joint in JOINT_LIST}

# 发布频率（Hz）
PUBLISH_FREQUENCY = 30
PUBLISH_INTERVAL = 1.0 / PUBLISH_FREQUENCY

# 标志位
running = True


def on_connect(client, userdata, flags, rc):
    """MQTT连接回调"""
    print(f"Connected with result code {rc}")
    # 订阅关节控制主题
    client.subscribe(TOPIC_JOINT_SET)


def on_message(client, userdata, msg):
    """MQTT消息回调"""
    try:
        payload = json.loads(msg.payload.decode())
        joint_name = payload.get("joint_name")
        position = payload.get("position")
        velocity = payload.get("velocity", 0.3)  # 默认速度0.3弧度/秒
        
        if joint_name and position is not None:
            if joint_name in joint_data:
                # 更新关节位置
                joint_data[joint_name] = position
                print(f"Updated joint {joint_name} to {position} with velocity {velocity}")
                
                # 根据关节名称确定控制方式
                try:
                    if robot is not None:
                        if joint_name.startswith("idx11_head") or joint_name.startswith("idx12_head") or joint_name.startswith("idx13_head"):
                            # 头部关节控制
                            # 获取所有头部关节当前位置
                            head_joints = [
                                "idx11_head_joint1",
                                "idx12_head_joint2",
                                "idx13_head_joint3"
                            ]
                            head_positions = [joint_data[joint] for joint in head_joints]
                            head_velocities = [velocity] * 3
                            print(f"head_positions: {head_positions}, head_velocities: {head_velocities}")
                            robot.move_head_joint(head_positions, head_velocities)
                            print(f"Controlled head joint {joint_name}")
                        elif joint_name.startswith("idx01_body") or joint_name.startswith("idx02_body") or joint_name.startswith("idx03_body") or \
                             joint_name.startswith("idx04_body") or joint_name.startswith("idx05_body"):
                            # 腰部关节控制
                            # 获取所有腰部关节当前位置
                            waist_joints = [
                                "idx01_body_joint1",
                                "idx02_body_joint2",
                                "idx03_body_joint3",
                                "idx04_body_joint4",
                                "idx05_body_joint5"
                            ]
                            waist_positions = [joint_data[joint] for joint in waist_joints]
                            waist_velocities = [velocity] * 5
                            robot.move_waist_joint(waist_positions, waist_velocities)
                            print(f"Controlled waist joint {joint_name}")
                        elif joint_name.startswith("idx21_arm_l") or joint_name.startswith("idx22_arm_l") or joint_name.startswith("idx23_arm_l") or \
                             joint_name.startswith("idx24_arm_l") or joint_name.startswith("idx25_arm_l") or joint_name.startswith("idx26_arm_l") or \
                             joint_name.startswith("idx27_arm_l") or joint_name.startswith("idx61_arm_r") or joint_name.startswith("idx62_arm_r") or \
                             joint_name.startswith("idx63_arm_r") or joint_name.startswith("idx64_arm_r") or joint_name.startswith("idx65_arm_r") or \
                             joint_name.startswith("idx66_arm_r") or joint_name.startswith("idx67_arm_r"):
                            # 手臂关节控制
                            # 获取所有手臂关节当前位置
                            arm_joints = [
                                # 左臂关节
                                "idx21_arm_l_joint1", "idx22_arm_l_joint2", "idx23_arm_l_joint3",
                                "idx24_arm_l_joint4", "idx25_arm_l_joint5", "idx26_arm_l_joint6",
                                "idx27_arm_l_joint7",
                                # 右臂关节
                                "idx61_arm_r_joint1", "idx62_arm_r_joint2", "idx63_arm_r_joint3",
                                "idx64_arm_r_joint4", "idx65_arm_r_joint5", "idx66_arm_r_joint6",
                                "idx67_arm_r_joint7"
                            ]
                            arm_positions = [joint_data[joint] for joint in arm_joints]
                            arm_velocities = [velocity] * 14
                            # 参数2表示控制左臂和右臂
                            robot.move_arm_joint(arm_positions, arm_velocities, 2)
                            print(f"Controlled arm joint {joint_name}")
                except Exception as e:
                    print(f"Error controlling joint {joint_name}: {e}")
            else:
                print(f"Unknown joint: {joint_name}")
    except json.JSONDecodeError:
        print("Failed to decode message payload")


def publish_joint_data(client):
    """发布关节数据"""
    while running:
        try:
            if robot is not None:
                # 从机器人获取关节状态
                joint_states = robot.get_joint_states()
                
                # 更新关节数据
                if 'states' in joint_states:
                    for state in joint_states['states']:
                        joint_name = state['name']
                        position = round(state['position'], 3)
                        
                        if joint_name in joint_data:
                            joint_data[joint_name] = position
            
            # 发布关节数据
            client.publish(TOPIC_JOINTS_READ, json.dumps(joint_data), qos=1)
            
            time.sleep(PUBLISH_INTERVAL)
        except Exception as e:
            print(f"Error publishing joint data: {e}")
            time.sleep(PUBLISH_INTERVAL)


def main():
    """主函数"""
    global running, robot
    
    # 初始化GDK系统
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK初始化失败")
        return 1
    print("GDK初始化成功")
    
    # 创建机器人对象
    robot = agibot_gdk.Robot()
    time.sleep(2)  # 等待机器人初始化
    print("机器人初始化完成")
    
    # 创建MQTT客户端
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    # 连接MQTT代理
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
    # 启动MQTT循环
    client.loop_start()
    
    try:
        # 启动发布线程
        publish_thread = threading.Thread(target=publish_joint_data, args=(client,))
        publish_thread.start()
        
        print("Joint control service started")
        print(f"Publishing joint data to {TOPIC_JOINTS_READ} at {PUBLISH_FREQUENCY}Hz")
        print(f"Listening for joint commands on {TOPIC_JOINT_SET}")
        
        # 保持程序运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        running = False
        
        # 停止发布线程
        if 'publish_thread' in locals():
            publish_thread.join()
        
        # 停止MQTT循环
        client.loop_stop()
        client.disconnect()
        
        # 释放GDK系统资源
        if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
            print("GDK释放失败")
        else:
            print("GDK释放成功")
        
        print("Joint control service stopped")
    
    return 0


if __name__ == "__main__":
    main()