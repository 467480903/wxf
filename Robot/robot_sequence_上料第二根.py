#!/usr/bin/env python3
import agibot_gdk
import time
import json
import os
from pathlib import Path

# 配置区
POSITIONS_DIR = "/data/finalgys/wxf/positions"

# 全局变量
robot = None

# 辅助函数：获取关节位置，支持多种名称格式
def get_joint_position(pos_data, *possible_names):
    """尝试多种可能的关节名称，返回找到的位置值"""
    for name in possible_names:
        if name in pos_data:
            return pos_data[name]
    return 0.0

def move_waist(pos_data):
    """控制腰部和腿部运动"""
    global robot
    try:
        waist_positions = [
            get_joint_position(pos_data, "idx01_body_joint1", "body_joint1", "joint1", "Body_Joint1"),
            get_joint_position(pos_data, "idx02_body_joint2", "body_joint2", "joint2", "Body_Joint2"),
            get_joint_position(pos_data, "idx03_body_joint3", "body_joint3", "joint3", "Body_Joint3"),
            get_joint_position(pos_data, "idx04_body_joint4", "body_joint4", "joint4", "Body_Joint4"),
            get_joint_position(pos_data, "idx05_body_joint5", "body_joint5", "joint5", "Body_Joint5")
        ]
        waist_velocities = [0.9] * 5
        robot.move_waist_joint(waist_positions, waist_velocities)
        print("腰部运动完成")
    except Exception as e:
        print(f"腰部运动失败: {e}")
        raise

def move_arm(pos_data):
    """控制上肢运动"""
    global robot
    try:
        left_arm_pos = [
            get_joint_position(pos_data, "idx21_arm_l_joint1", "arm_l_joint1", "left_arm_joint1", "LArm_Joint1"),
            get_joint_position(pos_data, "idx22_arm_l_joint2", "arm_l_joint2", "left_arm_joint2", "LArm_Joint2"),
            get_joint_position(pos_data, "idx23_arm_l_joint3", "arm_l_joint3", "left_arm_joint3", "LArm_Joint3"),
            get_joint_position(pos_data, "idx24_arm_l_joint4", "arm_l_joint4", "left_arm_joint4", "LArm_Joint4"),
            get_joint_position(pos_data, "idx25_arm_l_joint5", "arm_l_joint5", "left_arm_joint5", "LArm_Joint5"),
            get_joint_position(pos_data, "idx26_arm_l_joint6", "arm_l_joint6", "left_arm_joint6", "LArm_Joint6"),
            get_joint_position(pos_data, "idx27_arm_l_joint7", "arm_l_joint7", "left_arm_joint7", "LArm_Joint7")
        ]
        right_arm_pos = [
            get_joint_position(pos_data, "idx61_arm_r_joint1", "arm_r_joint1", "right_arm_joint1", "RArm_Joint1"),
            get_joint_position(pos_data, "idx62_arm_r_joint2", "arm_r_joint2", "right_arm_joint2", "RArm_Joint2"),
            get_joint_position(pos_data, "idx63_arm_r_joint3", "arm_r_joint3", "right_arm_joint3", "RArm_Joint3"),
            get_joint_position(pos_data, "idx64_arm_r_joint4", "arm_r_joint4", "right_arm_joint4", "RArm_Joint4"),
            get_joint_position(pos_data, "idx65_arm_r_joint5", "arm_r_joint5", "right_arm_joint5", "RArm_Joint5"),
            get_joint_position(pos_data, "idx66_arm_r_joint6", "arm_r_joint6", "right_arm_joint6", "RArm_Joint6"),
            get_joint_position(pos_data, "idx67_arm_r_joint7", "arm_r_joint7", "right_arm_joint7", "RArm_Joint7")
        ]
        arm_positions = left_arm_pos + right_arm_pos
        arm_velocities = [0.2] * 14
        robot.move_arm_joint(arm_positions, arm_velocities, 2)
        print("上肢运动完成")
    except Exception as e:
        print(f"上肢运动失败: {e}")
        raise

def move_head(pos_data):
    """控制头部运动"""
    global robot
    try:
        head_positions = [
            get_joint_position(pos_data, "idx11_head_joint1", "head_joint1", "Head_Joint1"),
            get_joint_position(pos_data, "idx12_head_joint2", "head_joint2", "Head_Joint2"),
            get_joint_position(pos_data, "idx13_head_joint3", "head_joint3", "Head_Joint3")
        ]
        head_velocities = [0.3] * 3
        robot.move_head_joint(head_positions, head_velocities)
        print("头部运动完成")
    except Exception as e:
        print(f"头部运动失败: {e}")
        raise

def move_to_pose(file_name):
    """移动到指定姿态"""
    file_path = os.path.join(POSITIONS_DIR, f"{file_name}.json")
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在: {file_path}")
        return False
    
    print(f"开始执行: {file_name}.json")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            pos_data = json.load(f)
        
        if "states" in pos_data and isinstance(pos_data["states"], list):
            joint_data = {}
            for state in pos_data["states"]:
                if "name" in state and "motor_position" in state:
                    joint_data[state["name"]] = state["motor_position"]
            pos_data = joint_data
        
        move_waist(pos_data)
        time.sleep(0.2)# 等待腰部运动完成
        
        move_arm(pos_data)
        time.sleep(0.2)# 等待手臂运动完成
        
       #move_head(pos_data)
       #time.sleep(0.2)# 等待头部运动完成
        
        print(f"完成: {file_name}.json")
        return True
        
    except Exception as e:
        print(f"执行失败: {file_name}.json - {e}")
        return False

def close_gripper():
    """闭合夹爪"""
    global robot
    try:
        joint_states_right = agibot_gdk.JointStates()
        joint_states_right.group = "right_tool"
        joint_states_right.target_type = "omnipicker"
        joint_state_r = agibot_gdk.JointState()
        joint_state_r.position = 0  # 闭合夹爪的值为0
        joint_states_right.states = [joint_state_r]
        joint_states_right.nums = len(joint_states_right.states)
        
        joint_states_left = agibot_gdk.JointStates()
        joint_states_left.group = "left_tool"
        joint_states_left.target_type = "omnipicker"
        joint_state_l = agibot_gdk.JointState()
        joint_state_l.position = 0  # 闭合夹爪的值为0
        joint_states_left.states = [joint_state_l]
        joint_states_left.nums = len(joint_states_left.states)
        
        robot.move_ee_pos(joint_states_right)
        print("右夹爪闭合成功")
        time.sleep(0.1)
        
        robot.move_ee_pos(joint_states_left)
        print("左夹爪闭合成功")
        
        print("夹爪闭合完成")
        return True
    except Exception as e:
        print(f"夹爪闭合失败: {e}")
        return False

def open_gripper():
    """张开夹爪"""
    global robot
    try:
        joint_states_right = agibot_gdk.JointStates()
        joint_states_right.group = "right_tool"
        joint_states_right.target_type = "omnipicker"
        joint_state_r = agibot_gdk.JointState()
        joint_state_r.position = -0.785  # 张开夹爪的值为-0.785
        joint_states_right.states = [joint_state_r]
        joint_states_right.nums = len(joint_states_right.states)
        
        joint_states_left = agibot_gdk.JointStates()
        joint_states_left.group = "left_tool"
        joint_states_left.target_type = "omnipicker"
        joint_state_l = agibot_gdk.JointState()
        joint_state_l.position = -0.785  # 张开夹爪的值为-0.785
        joint_states_left.states = [joint_state_l]
        joint_states_left.nums = len(joint_states_left.states)
        
        robot.move_ee_pos(joint_states_right)
        print("右夹爪张开成功")
        time.sleep(0.1)
        
        robot.move_ee_pos(joint_states_left)
        print("左夹爪张开成功")
        
        print("夹爪张开完成")
        return True
    except Exception as e:
        print(f"夹爪张开失败: {e}")
        return False

def main():
    global robot
    print("开始执行机器人操作序列...")
    
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK初始化失败")
        return
    
    robot = agibot_gdk.Robot()
    time.sleep(2)
    print("机器人初始化成功")
    
    sequence = [
        

        
        ("OPEN_GRIPPER", "张开夹爪"),
        ("上料P2", "姿态P2"),
        ("上料P3", "姿态P3"),
        ("上料P4", "姿态P4"),
        ("上料P5", "姿态P5"),
        ("CLOSE_GRIPPER", "闭合夹爪"),
        ("上料P6", "姿态P6"),
        ("上料P7", "姿态P7"),
        ("上料P8", "姿态P8"),
        ("上料P9", "姿态P9"),
        ("上料P10", "姿态P10"),
        ("上料P11", "姿态P11"),
        ("上料P12", "姿态P12"),
        ("上料P13", "姿态P13"),
        ("OPEN_GRIPPER", "张开夹爪"),
        ("上料P14", "姿态P14"),
        ("上料P15", "姿态P15"),
        ("上料P16", "姿态P16")
        
        

        
    ]
    
    for step, description in sequence:
        print(f"\n{'='*50}")
        print(f"步骤: {description}")
        print(f"{'='*50}")
        
        success = False
        if step == "CLOSE_GRIPPER":
            success = close_gripper()
        elif step == "OPEN_GRIPPER":
            success = open_gripper()
        else:
            success = move_to_pose(step)
        
        if success:
            print(f"✓ {description} 执行成功")
            time.sleep(1)
        else:
            print(f"✗ {description} 执行失败")
            break
    
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("GDK释放失败")
    else:
        print("GDK资源已释放")
    
    print("\n操作序列执行完成")

if __name__ == "__main__":
    main()
