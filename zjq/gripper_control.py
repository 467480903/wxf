import agibot_gdk
import time

def open_gripper(robot):
    joint_states_right = agibot_gdk.JointStates()
    joint_states_right.group = "right_tool"
    joint_states_right.target_type = "omnipicker"
    joint_state_r = agibot_gdk.JointState()
    joint_state_r.position = -0.785
    joint_states_right.states = [joint_state_r]
    joint_states_right.nums = len(joint_states_right.states)

    joint_states_left = agibot_gdk.JointStates()
    joint_states_left.group = "left_tool"
    joint_states_left.target_type = "omnipicker"
    joint_state_l = agibot_gdk.JointState()
    joint_state_l.position = -0.785
    joint_states_left.states = [joint_state_l]
    joint_states_left.nums = len(joint_states_left.states)

    robot.move_ee_pos(joint_states_right)
    print("右夹爪张开")
    time.sleep(0.05)
    robot.move_ee_pos(joint_states_left)
    print("左夹爪张开")

def close_gripper(robot):
    joint_states_right = agibot_gdk.JointStates()
    joint_states_right.group = "right_tool"
    joint_states_right.target_type = "omnipicker"
    joint_state_r = agibot_gdk.JointState()
    joint_state_r.position = 0
    joint_states_right.states = [joint_state_r]
    joint_states_right.nums = len(joint_states_right.states)

    joint_states_left = agibot_gdk.JointStates()
    joint_states_left.group = "left_tool"
    joint_states_left.target_type = "omnipicker"
    joint_state_l = agibot_gdk.JointState()
    joint_state_l.position = 0
    joint_states_left.states = [joint_state_l]
    joint_states_left.nums = len(joint_states_left.states)

    robot.move_ee_pos(joint_states_right)
    print("右夹爪闭合")
    time.sleep(0.05)
    robot.move_ee_pos(joint_states_left)
    print("左夹爪闭合")

def main():
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK初始化失败")
        exit(1)
    print("GDK初始化成功")

    robot = agibot_gdk.Robot()
    time.sleep(2)

    print("开始夹爪张开关闭3次...")
    for i in range(3):
        print(f"\n=== 第 {i+1} 次 ===")
        open_gripper(robot)
        time.sleep(0.5)
        close_gripper(robot)
        time.sleep(0.5)

    print("\n完成！")

    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("GDK释放失败")
    else:
        print("GDK释放成功")

if __name__ == "__main__":
    main()