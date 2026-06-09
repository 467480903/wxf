#!/usr/bin/env python3
"""
机器人执行序列脚本 v2
=====================
按顺序执行指定的动作序列
"""

import agibot_gdk
import time
import json
import os
import sys

# 添加路径以导入自定义模块
sys.path.insert(0, "/data/bengtian/wxf/BOX_528_1")
from end_effector_controller import EndEffectorController
from robot_controller import RobotController


def init_gdk():
    """初始化 GDK 系统"""
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK初始化失败")
        exit(1)
    print("✅ GDK初始化成功")
    return agibot_gdk.Robot()


def release_gdk():
    """释放 GDK 系统资源"""
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK释放失败")
    else:
        print("✅ GDK释放成功")


def move_ee_pose_open_2(robot):
    """执行 move_ee_pose_open_2.py 的逻辑"""
    print("\n=== move_ee_pose_open_2 ===")
    
    # 准备右夹爪 (right_tool)
    joint_states_right = agibot_gdk.JointStates()
    joint_states_right.group = "right_tool"
    joint_states_right.target_type = "omnipicker"
    joint_state_r = agibot_gdk.JointState()
    joint_state_r.position = -0.785
    joint_states_right.states = [joint_state_r]
    joint_states_right.nums = len(joint_states_right.states)
    
    # 准备左夹爪 (left_tool)
    joint_states_left = agibot_gdk.JointStates()
    joint_states_left.group = "left_tool"
    joint_states_left.target_type = "omnipicker"
    joint_state_l = agibot_gdk.JointState()
    joint_state_l.position = -0.785
    joint_states_left.states = [joint_state_l]
    joint_states_left.nums = len(joint_states_left.states)
    
    # 执行张开双手
    try:
        robot.move_ee_pos(joint_states_right)
        print("✅ 右夹爪张开成功")
        time.sleep(0.05)
    except Exception as e:
        print(f"❌ 右夹爪张开失败: {e}")
    
    try:
        robot.move_ee_pos(joint_states_left)
        print("✅ 左夹爪张开成功")
    except Exception as e:
        print(f"❌ 左夹爪张开失败: {e}")
    
    time.sleep(0.05)


def move_arm_by_json_grab_above_1(robot):
    """执行 move_arm_by_json_grab_above_1.py 的逻辑"""
    print("\n=== move_arm_by_json_grab_above_1 ===")
    
    JSON_FILE_PATH = "/data/bengtian/wxf/positions/arm_position_to_grab_1.json"
    
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ 找不到文件: {JSON_FILE_PATH}")
        return
    
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            pos_data = json.load(f)
        print("✅ JSON 配置读取成功")
    except Exception as e:
        print(f"❌ 解析 JSON 文件失败: {e}")
        return
    
    # 提取左臂 7 个关节数据
    left_arm_pos = [
        pos_data.get("idx21_arm_l_joint1", 0.0),
        pos_data.get("idx22_arm_l_joint2", 0.0),
        pos_data.get("idx23_arm_l_joint3", 0.0),
        pos_data.get("idx24_arm_l_joint4", 0.0),
        pos_data.get("idx25_arm_l_joint5", 0.0),
        pos_data.get("idx26_arm_l_joint6", 0.0),
        pos_data.get("idx27_arm_l_joint7", 0.0)
    ]
    
    # 提取右臂 7 个关节数据
    right_arm_pos = [
        pos_data.get("idx61_arm_r_joint1", 0.0),
        pos_data.get("idx62_arm_r_joint2", 0.0),
        pos_data.get("idx63_arm_r_joint3", 0.0),
        pos_data.get("idx64_arm_r_joint4", 0.0),
        pos_data.get("idx65_arm_r_joint5", 0.0),
        pos_data.get("idx66_arm_r_joint6", 0.0),
        pos_data.get("idx67_arm_r_joint7", 0.0)
    ]
    
    # 合并为14个关节的数组
    arm_positions = left_arm_pos + right_arm_pos
    
    # 设置速度 (14个关节)
    arm_velocities = [0.2] * 14
    
    try:
        print(f"准备发送手臂位置控制指令...")
        result = robot.move_arm_joint(arm_positions, arm_velocities, 2)
        print("✅ 手臂控制成功")
    except Exception as e:
        print(f"❌ 手臂控制失败: {e}")


def move_waist_by_json_down(robot):
    """执行 move_waist_by_json_down.py 的逻辑"""
    print("\n=== move_waist_by_json_down ===")
    
    JSON_FILE_PATH = "/data/bengtian/wxf/positions/waist_position_to_down.json"
    
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ 找不到文件: {JSON_FILE_PATH}")
        return
    
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            pos_data = json.load(f)
        print("✅ JSON 配置读取成功")
    except Exception as e:
        print(f"❌ 解析 JSON 文件失败: {e}")
        return
    
    waist_positions = [
        pos_data.get("idx01_body_joint1", 0.0),
        pos_data.get("idx02_body_joint2", 0.0),
        pos_data.get("idx03_body_joint3", 0.0),
        pos_data.get("idx04_body_joint4", 0.0),
        pos_data.get("idx05_body_joint5", 0.0)
    ]
    
    waist_velocities = [0.3, 0.3, 0.3, 0.3, 0.3]
    
    try:
        print(f"准备发送腰部位置控制指令")
        result = robot.move_waist_joint(waist_positions, waist_velocities)
        print("✅ 腰部控制成功")
    except Exception as e:
        print(f"❌ 腰部控制失败: {e}")


def move_ee_pose_close_2(robot):
    """执行 move_ee_pose_close_2.py 的逻辑"""
    print("\n=== move_ee_pose_close_2 ===")
    
    # 准备右夹爪 (right_tool)
    joint_states_right = agibot_gdk.JointStates()
    joint_states_right.group = "right_tool"
    joint_states_right.target_type = "omnipicker"
    joint_state_r = agibot_gdk.JointState()
    joint_state_r.position = 0
    joint_states_right.states = [joint_state_r]
    joint_states_right.nums = len(joint_states_right.states)
    
    # 准备左夹爪 (left_tool)
    joint_states_left = agibot_gdk.JointStates()
    joint_states_left.group = "left_tool"
    joint_states_left.target_type = "omnipicker"
    joint_state_l = agibot_gdk.JointState()
    joint_state_l.position = 0
    joint_states_left.states = [joint_state_l]
    joint_states_left.nums = len(joint_states_left.states)
    
    # 执行闭合双手
    try:
        robot.move_ee_pos(joint_states_right)
        print("✅ 右夹爪闭合成功")
        time.sleep(0.05)
    except Exception as e:
        print(f"❌ 右夹爪闭合失败: {e}")
    
    try:
        robot.move_ee_pos(joint_states_left)
        print("✅ 左夹爪闭合成功")
    except Exception as e:
        print(f"❌ 左夹爪闭合失败: {e}")
    
    time.sleep(0.05)


def offset_move_pull(robot):
    """执行 offset_move_pull.py 的逻辑"""
    print("\n=== offset_move_pull ===")
    
    try:
        controller = EndEffectorController(robot)
        controller.adjust_arms_relative(offset_l=(-0.15, 0, 0.01), offset_r=(-0.15, 0, 0.01))
        print("✅ 双臂拉取动作完成")
    except Exception as e:
        print(f"❌ 拉取动作失败: {e}")


def move_waist_by_json_default(robot):
    """执行 move_waist_by_json_default.py 的逻辑"""
    print("\n=== move_waist_by_json_default ===")
    
    JSON_FILE_PATH = "/data/wxf/wxf/positions/arm_default.json"
    
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ 找不到文件: {JSON_FILE_PATH}")
        return
    
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            pos_data = json.load(f)
        print("✅ JSON 配置读取成功")
    except Exception as e:
        print(f"❌ 解析 JSON 文件失败: {e}")
        return
    
    waist_positions = [
        pos_data.get("idx01_body_joint1", 0.0),
        pos_data.get("idx02_body_joint2", 0.0),
        pos_data.get("idx03_body_joint3", 0.0),
        pos_data.get("idx04_body_joint4", 0.0),
        pos_data.get("idx05_body_joint5", 0.0)
    ]
    
    waist_velocities = [0.3, 0.3, 0.3, 0.3, 0.3]
    
    try:
        print(f"准备发送腰部位置控制指令")
        result = robot.move_waist_joint(waist_positions, waist_velocities)
        print("✅ 腰部复位成功")
    except Exception as e:
        print(f"❌ 腰部复位失败: {e}")


def move_arm_by_json_grab_above_2(robot):
    """执行 move_arm_by_json_grab_above_2.py 的逻辑"""
    print("\n=== move_arm_by_json_grab_above_2 ===")
    
    JSON_FILE_PATH = "/data/bengtian/wxf/positions/arm_position_to_grab_2.json"
    
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ 找不到文件: {JSON_FILE_PATH}")
        return
    
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            pos_data = json.load(f)
        print("✅ JSON 配置读取成功")
    except Exception as e:
        print(f"❌ 解析 JSON 文件失败: {e}")
        return
    
    # 提取左臂 7 个关节数据
    left_arm_pos = [
        pos_data.get("idx21_arm_l_joint1", 0.0),
        pos_data.get("idx22_arm_l_joint2", 0.0),
        pos_data.get("idx23_arm_l_joint3", 0.0),
        pos_data.get("idx24_arm_l_joint4", 0.0),
        pos_data.get("idx25_arm_l_joint5", 0.0),
        pos_data.get("idx26_arm_l_joint6", 0.0),
        pos_data.get("idx27_arm_l_joint7", 0.0)
    ]
    
    # 提取右臂 7 个关节数据
    right_arm_pos = [
        pos_data.get("idx61_arm_r_joint1", 0.0),
        pos_data.get("idx62_arm_r_joint2", 0.0),
        pos_data.get("idx63_arm_r_joint3", 0.0),
        pos_data.get("idx64_arm_r_joint4", 0.0),
        pos_data.get("idx65_arm_r_joint5", 0.0),
        pos_data.get("idx66_arm_r_joint6", 0.0),
        pos_data.get("idx67_arm_r_joint7", 0.0)
    ]
    
    # 合并为14个关节的数组
    arm_positions = left_arm_pos + right_arm_pos
    
    # 设置速度 (14个关节)
    arm_velocities = [0.2] * 14
    
    try:
        print(f"准备发送手臂位置控制指令...")
        result = robot.move_arm_joint(arm_positions, arm_velocities, 2)
        print("✅ 手臂控制成功")
    except Exception as e:
        print(f"❌ 手臂控制失败: {e}")


def offset_move_down(robot):
    """执行 offset_move_down.py 的逻辑"""
    print("\n=== offset_move_down ===")
    
    try:
        controller = EndEffectorController(robot)
        controller.adjust_arms_relative(offset_l=(0, 0, -0.08), offset_r=(0, 0, -0.08))
        print("✅ 双臂下移动作完成")
    except Exception as e:
        print(f"❌ 下移动作失败: {e}")


def move_arm_by_json_default(robot):
    """执行 move_arm_by_json_default.py 的逻辑"""
    print("\n=== move_arm_by_json_default ===")
    
    JSON_FILE_PATH = "/data/wxf/wxf/positions/arm_default.json"
    
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ 找不到文件: {JSON_FILE_PATH}")
        return
    
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            pos_data = json.load(f)
        print("✅ JSON 配置读取成功")
    except Exception as e:
        print(f"❌ 解析 JSON 文件失败: {e}")
        return
    
    # 提取左臂 7 个关节数据
    left_arm_pos = [
        pos_data.get("idx21_arm_l_joint1", 0.0),
        pos_data.get("idx22_arm_l_joint2", 0.0),
        pos_data.get("idx23_arm_l_joint3", 0.0),
        pos_data.get("idx24_arm_l_joint4", 0.0),
        pos_data.get("idx25_arm_l_joint5", 0.0),
        pos_data.get("idx26_arm_l_joint6", 0.0),
        pos_data.get("idx27_arm_l_joint7", 0.0)
    ]
    
    # 提取右臂 7 个关节数据
    right_arm_pos = [
        pos_data.get("idx61_arm_r_joint1", 0.0),
        pos_data.get("idx62_arm_r_joint2", 0.0),
        pos_data.get("idx63_arm_r_joint3", 0.0),
        pos_data.get("idx64_arm_r_joint4", 0.0),
        pos_data.get("idx65_arm_r_joint5", 0.0),
        pos_data.get("idx66_arm_r_joint6", 0.0),
        pos_data.get("idx67_arm_r_joint7", 0.0)
    ]
    
    # 合并为14个关节的数组
    arm_positions = left_arm_pos + right_arm_pos
    
    # 设置速度 (14个关节)
    arm_velocities = [0.2] * 14
    
    try:
        print(f"准备发送手臂位置控制指令...")
        result = robot.move_arm_joint(arm_positions, arm_velocities, 2)
        print("✅ 手臂复位成功")
    except Exception as e:
        print(f"❌ 手臂复位失败: {e}")


def chassis_move_backward(distance=1.0):
    """底盘向后移动"""
    print(f"\n=== 向后移动 {distance} 米 ===")
    try:
        from chassis_controller import ChassisController
        with ChassisController() as ctrl:
            state = ctrl.move_backward(distance)
            print(f"✅ 向后移动完成, state={state}")
    except Exception as e:
        print(f"❌ 向后移动失败: {e}")


def main():
    """主执行函数"""
    print("=" * 60)
    print("机器人执行序列 v2 开始")
    print("=" * 60)
    
    # 初始化 GDK
    robot = init_gdk()
    time.sleep(2)
    
    # 初始化 RobotController 用于导航
    robot_ctrl = RobotController(verbose=True)
    
    try:
        # 1. move-ready1.py (导航到点0)
        print("\n=== move-ready1 ===")
        robot_ctrl.go(0)
        time.sleep(1)
        
        # 2. move_ee_pose_open_2.py
        move_ee_pose_open_2(robot)
        time.sleep(1)
        
        # 3. move_arm_by_json_grab_above_1.py
        move_arm_by_json_grab_above_1(robot)
        time.sleep(2)
        
        # 4. move_waist_by_json_down.py
        move_waist_by_json_down(robot)
        time.sleep(2)
        
        # 5. move-pick1.py (导航到点1和2)
        print("\n=== move-pick1 ===")
        robot_ctrl.go(1)
        robot_ctrl.go(2)
        time.sleep(1)
        
        # 6. move_ee_pose_close_2.py
        move_ee_pose_close_2(robot)
        time.sleep(1)
        
        # 7. offset_move_pull.py
        offset_move_pull(robot)
        time.sleep(1)
        
        # 8. move-adjust1.py (导航到点3)
        print("\n=== move-adjust1 ===")
        robot_ctrl.go(3)
        time.sleep(1)
        
        # 9. move_waist_by_json_default.py
        move_waist_by_json_default(robot)
        time.sleep(2)
        
        # 10. move_arm_by_json_grab_above_2.py
        move_arm_by_json_grab_above_2(robot)
        time.sleep(2)
        
        # 11. move-put1.py (导航到点4和5)
        print("\n=== move-put1 ===")
        robot_ctrl.go(4)
        robot_ctrl.go(5)
        time.sleep(1)
        
        # 12. offset_move_down.py
        offset_move_down(robot)
        time.sleep(1)
        
        # 13. move_ee_pose_open_2.py
        move_ee_pose_open_2(robot)
        time.sleep(1)
        
        # 14. offset_move_pull.py
        offset_move_pull(robot)
        time.sleep(1)
        
        # 15. 向后退1m
        chassis_move_backward(1.0)
        time.sleep(1)
        
        # 16. move_arm_by_json_default.py
        move_arm_by_json_default(robot)
        time.sleep(2)
        
        # 17. move-ready1.py (导航到点0)
        print("\n=== move-ready1 ===")
        robot_ctrl.go(0)
        time.sleep(1)
        
        print("\n" + "=" * 60)
        print("机器人执行序列 v2 完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 执行过程中发生错误: {e}")
    finally:
        # 释放 GDK 资源
        release_gdk()


if __name__ == "__main__":
    main()