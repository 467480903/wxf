import agibot_gdk
import time
import sys


def open_gripper(robot):
    print("正在张开夹爪...")
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

    try:
        robot.move_ee_pos(joint_states_right)
        print("右夹爪张开成功")
    except Exception as e:
        print(f"右夹爪张开失败: {e}")
        return False

    try:
        robot.move_ee_pos(joint_states_left)
        print("左夹爪张开成功")
    except Exception as e:
        print(f"左夹爪张开失败: {e}")
        return False

    return True


def close_gripper(robot):
    print("正在闭合夹爪...")
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

    try:
        robot.move_ee_pos(joint_states_right)
        print("右夹爪闭合成功")
    except Exception as e:
        print(f"右夹爪闭合失败: {e}")
        return False

    try:
        robot.move_ee_pos(joint_states_left)
        print("左夹爪闭合成功")
    except Exception as e:
        print(f"左夹爪闭合失败: {e}")
        return False

    return True


def main():
    if len(sys.argv) < 2:
        print("用法: python gripper_control.py [open|close]")
        print("  open  - 张开夹爪")
        print("  close - 闭合夹爪")
        sys.exit(1)

    action = sys.argv[1].lower()
    if action not in ["open", "close"]:
        print("错误: 参数必须是 open 或 close")
        sys.exit(1)

    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK初始化失败")
        sys.exit(1)
    print("GDK初始化成功")

    robot = agibot_gdk.Robot()
    time.sleep(2)

    if action == "open":
        open_gripper(robot)
    else:
        close_gripper(robot)

    time.sleep(0.5)

    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("GDK释放失败")
    else:
        print("GDK释放成功")


if __name__ == "__main__":
    main()
