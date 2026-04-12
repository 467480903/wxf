import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

robot = agibot_gdk.Robot()
time.sleep(2)  # 等待机器人初始化

# ================= 准备右夹爪 (right_tool) =================
joint_states_right = agibot_gdk.JointStates()
joint_states_right.group = "right_tool"
joint_states_right.target_type = "omnipicker"

joint_state_r = agibot_gdk.JointState()
# 【修改点】：张开夹爪的值改为 -0.785 (对应报错提示的下限)
joint_state_r.position = -0.785  
joint_states_right.states = [joint_state_r]
joint_states_right.nums = len(joint_states_right.states)

# ================= 准备左夹爪 (left_tool) =================
joint_states_left = agibot_gdk.JointStates()
joint_states_left.group = "left_tool"
joint_states_left.target_type = "omnipicker"

joint_state_l = agibot_gdk.JointState()
# 【修改点】：张开夹爪的值改为 -0.785
joint_state_l.position = -0.785  
joint_states_left.states = [joint_state_l]
joint_states_left.nums = len(joint_states_left.states)

# ================= 执行张开双手 =================
try:
    robot.move_ee_pos(joint_states_right)
    print("右夹爪张开成功")
    time.sleep(2.0)  # 等待动作完成
except Exception as e:
    print(f"右夹爪张开失败: {e}")

try:
    robot.move_ee_pos(joint_states_left)
    print("左夹爪张开成功")
except Exception as e:
    print(f"左夹爪张开失败: {e}")

time.sleep(1.0)

# ================= 执行闭合双手 =================
joint_state_r.position = 0  # 0 为闭合 (之前测试已成功)
joint_states_right.states = [joint_state_r]

joint_state_l.position = 0  # 0 为闭合
joint_states_left.states = [joint_state_l]

try:
    robot.move_ee_pos(joint_states_right)
    print("右夹爪闭合成功")
    time.sleep(1.0)  # 等待动作完成
except Exception as e:
    print(f"右夹爪闭合失败: {e}")    

try:
    robot.move_ee_pos(joint_states_left)
    print("左夹爪闭合成功")
except Exception as e:
    print(f"左夹爪闭合失败: {e}")  

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
else:
    print("GDK释放成功")