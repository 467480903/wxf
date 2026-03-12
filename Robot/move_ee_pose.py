import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# 控制左夹爪（omnipicker类型，需要1个关节）
joint_states_left = agibot_gdk.JointStates()
joint_states_left.group = "left_tool"
joint_states_left.target_type = "omnipicker"

joint_state = agibot_gdk.JointState()
joint_state.position = 1  # 取值范围 [0, 1]  
joint_states_left.states = [joint_state]
joint_states_left.nums = len(joint_states_left.states)



try:
    result = robot.move_ee_pos(joint_states_left)
    print("左夹爪控制成功")
except Exception as e:
    print(f"左夹爪控制失败: {e}")

time.sleep(2.0)

joint_state.position = 0  # 取值范围 [0, 1]  
joint_states_left.states = [joint_state]
joint_states_left.nums = len(joint_states_left.states)

try:
    result = robot.move_ee_pos(joint_states_left)
    print("左夹爪控制成功")
except Exception as e:
    print(f"左夹爪控制失败: {e}")    

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")