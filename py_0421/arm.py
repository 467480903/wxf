#!/usr/bin/env python3
"""
机械臂末端控制服务
- 以30Hz频率发布左右臂末端坐标到/arms_read
- 监听/arm_set主题接收机械臂末端控制命令
- 发布夹爪状态到/end_effector_read
- 监听/end_effector_set主题接收夹爪控制命令
"""

import time
import json
import paho.mqtt.client as mqtt
import threading
import math

# MQTT配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_ARMS_READ = "/arms_read"
TOPIC_ARM_SET = "/arm_set"
TOPIC_END_EFFECTOR_READ = "/end_effector_read"
TOPIC_END_EFFECTOR_SET = "/end_effector_set"

# 机械臂数据存储
arm_data = {
    "left": {
        "position": {"x": 0.3, "y": 0.3, "z": 0.8},
        "orientation": {"rx": 0.0, "ry": 0.0, "rz": 0.0},
        "quaternion": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
    },
    "right": {
        "position": {"x": 0.3, "y": -0.3, "z": 0.8},
        "orientation": {"rx": 0.0, "ry": 0.0, "rz": 0.0},
        "quaternion": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
    }
}

# 夹爪状态存储
end_effector_data = {
    "left": "open",
    "right": "open"
}

# 发布频率（Hz）
PUBLISH_FREQUENCY = 30
PUBLISH_INTERVAL = 1.0 / PUBLISH_FREQUENCY

# 标志位
running = True


def on_connect(client, userdata, flags, rc):
    """MQTT连接回调"""
    print(f"Connected with result code {rc}")
    # 订阅控制主题
    client.subscribe(TOPIC_ARM_SET)
    client.subscribe(TOPIC_END_EFFECTOR_SET)


def on_message(client, userdata, msg):
    """MQTT消息回调"""
    try:
        payload = json.loads(msg.payload.decode())
        
        if msg.topic == TOPIC_ARM_SET:
            # 处理机械臂末端控制命令
            arm = payload.get("arm")
            x = payload.get("x")
            y = payload.get("y")
            z = payload.get("z")
            rx = payload.get("rx")
            ry = payload.get("ry")
            rz = payload.get("rz")
            
            if arm in arm_data:
                # 更新位置
                if x is not None:
                    arm_data[arm]["position"]["x"] = x
                if y is not None:
                    arm_data[arm]["position"]["y"] = y
                if z is not None:
                    arm_data[arm]["position"]["z"] = z
                
                # 更新RPY姿态
                if rx is not None:
                    arm_data[arm]["orientation"]["rx"] = rx
                if ry is not None:
                    arm_data[arm]["orientation"]["ry"] = ry
                if rz is not None:
                    arm_data[arm]["orientation"]["rz"] = rz
                
                # 计算四元数（简单转换，实际应用中应使用更精确的转换方法）
                arm_data[arm]["quaternion"] = rpy_to_quaternion(rx, ry, rz)
                
                print(f"Updated {arm} arm pose:")
                print(f"  Position: x={x:.3f}, y={y:.3f}, z={z:.3f}")
                print(f"  RPY: rx={rx:.3f}, ry={ry:.3f}, rz={rz:.3f}")
            else:
                print(f"Unknown arm: {arm}")
                
        elif msg.topic == TOPIC_END_EFFECTOR_SET:
            # 处理夹爪控制命令
            arm = payload.get("arm")
            action = payload.get("action")
            
            if arm in end_effector_data and action in ["open", "close"]:
                end_effector_data[arm] = action
                print(f"Set {arm} gripper to {action}")
            else:
                print(f"Invalid arm or action: arm={arm}, action={action}")
                
    except json.JSONDecodeError:
        print("Failed to decode message payload")
    except Exception as e:
        print(f"Error processing message: {e}")


def rpy_to_quaternion(rx, ry, rz):
    """将RPY角度转换为四元数"""
    # 简单的转换实现，实际应用中应使用更精确的转换
    cr = math.cos(rx * 0.5)
    sr = math.sin(rx * 0.5)
    cp = math.cos(ry * 0.5)
    sp = math.sin(ry * 0.5)
    cy = math.cos(rz * 0.5)
    sy = math.sin(rz * 0.5)
    
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    
    return {"x": x, "y": y, "z": z, "w": w}


def publish_arm_data(client):
    """发布机械臂数据"""
    while running:
        try:
            # 模拟机械臂数据变化（实际应用中应从机器人获取）
            for arm in arm_data:
                # 这里可以替换为实际的机器人末端数据读取
                pass
            
            # 发布机械臂数据
            client.publish(TOPIC_ARMS_READ, json.dumps(arm_data), qos=1)
            
            # 发布夹爪状态
            client.publish(TOPIC_END_EFFECTOR_READ, json.dumps(end_effector_data), qos=1)
            
            time.sleep(PUBLISH_INTERVAL)
        except Exception as e:
            print(f"Error publishing arm data: {e}")
            time.sleep(PUBLISH_INTERVAL)


def main():
    """主函数"""
    global running
    
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
        publish_thread = threading.Thread(target=publish_arm_data, args=(client,))
        publish_thread.start()
        
        print("Arm control service started")
        print(f"Publishing arm data to {TOPIC_ARMS_READ} at {PUBLISH_FREQUENCY}Hz")
        print(f"Publishing end effector data to {TOPIC_END_EFFECTOR_READ} at {PUBLISH_FREQUENCY}Hz")
        print(f"Listening for arm commands on {TOPIC_ARM_SET}")
        print(f"Listening for end effector commands on {TOPIC_END_EFFECTOR_SET}")
        
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
        
        print("Arm control service stopped")


if __name__ == "__main__":
    main()