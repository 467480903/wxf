#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智元 G2：同时闭合左右两个夹爪

适配当前 SDK：
  robot.move_ee_pos() 需要 agibot_gdk.JointStates
  不能传 dict

运行：
  /usr/bin/python /data/wxf/wxf/mqtt_gateway_workspace_20260624/G2_test/close_both_grippers.py

参数：
  --pos 0.6              默认闭合位置，保守闭合
  --pos 1.0              更紧闭合
  --target-type omnipicker
"""

import argparse
import time
import traceback
import agibot_gdk


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pos",
        type=float,
        default=-0.78,
        help="夹爪目标开合度。保守闭合用 -0.78，更紧可试 1.0"
    )
    parser.add_argument(
        "--target-type",
        type=str,
        default="omnipicker",
        choices=["omnipicker", "ctek90d", "dahuan"],
        help="末端类型。单关节夹爪通常先试 omnipicker"
    )
    return parser.parse_args()


def print_end_state(robot, title):
    print(f"\n========== {title} ==========")
    try:
        end_state = robot.get_end_state()

        for side_cn, key in [("左", "left_end_state"), ("右", "right_end_state")]:
            state = end_state.get(key, {})
            print(f"\n{side_cn}执行器:")
            print(f"  controlled: {state.get('controlled')}")
            print(f"  type: {state.get('type')}")
            print(f"  names: {state.get('names')}")

            end_states = state.get("end_states", [])
            if not end_states:
                print("  未读取到 end_states")
                continue

            for i, joint in enumerate(end_states):
                print(
                    f"  joint[{i}]: "
                    f"position={joint.get('position')}, "
                    f"velocity={joint.get('velocity')}, "
                    f"current={joint.get('current')}, "
                    f"err_code={joint.get('err_code')}"
                )

    except Exception as e:
        print(f"⚠️ 读取末端状态失败: {e}")


def make_joint_state(position):
    js = agibot_gdk.JointState()
    js.position = float(position)
    return js


def close_both_grippers(robot, target_pos, target_type):
    """
    双夹爪控制：
      group = dual_tool
      target_type = omnipicker / ctek90d / dahuan
      states[0] = 左夹爪
      states[1] = 右夹爪
    """
    dual = agibot_gdk.JointStates()
    dual.group = "dual_tool"
    dual.target_type = target_type

    left_state = make_joint_state(target_pos)
    right_state = make_joint_state(target_pos)

    dual.states = [left_state, right_state]
    dual.nums = len(dual.states)

    print("\n准备发送双夹爪闭合命令:")
    print(f"  group: {dual.group}")
    print(f"  target_type: {dual.target_type}")
    print(f"  左夹爪目标: {target_pos}")
    print(f"  右夹爪目标: {target_pos}")
    print(f"  nums: {dual.nums}")

    result = robot.move_ee_pos(dual)
    print(f"\n✅ move_ee_pos 返回值: {result}")


def main():
    args = parse_args()

    print("正在初始化 GDK...")
    ret = agibot_gdk.gdk_init()
    if ret != agibot_gdk.GDKRes.kSuccess:
        print(f"❌ GDK 初始化失败: {ret}")
        return 1

    robot = None

    try:
        print("✅ GDK 初始化成功")
        print("正在创建 Robot 对象...")
        robot = agibot_gdk.Robot()
        time.sleep(2.0)
        print("✅ Robot 对象已创建")

        print_end_state(robot, "闭合前末端状态")

        print("\n⚠️ 即将实际控制两个夹爪。")
        print("请确认夹爪附近没有手、线缆、易碎物。")
        input("确认安全后按 Enter 执行；取消请按 Ctrl+C：")

        close_both_grippers(
            robot=robot,
            target_pos=args.pos,
            target_type=args.target_type,
        )

        time.sleep(1.0)

        print_end_state(robot, "闭合后末端状态")

        return 0

    except KeyboardInterrupt:
        print("\n用户取消")
        return 130

    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        traceback.print_exc()
        return 1

    finally:
        print("\n正在释放 GDK...")
        release_ret = agibot_gdk.gdk_release()
        if release_ret == agibot_gdk.GDKRes.kSuccess:
            print("✅ GDK 释放成功")
        else:
            print(f"⚠️ GDK 释放失败: {release_ret}")


if __name__ == "__main__":
    raise SystemExit(main())