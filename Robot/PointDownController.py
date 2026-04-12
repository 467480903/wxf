import agibot_gdk
import time
import math

# ─────────────────────────────────────────────
# 辅助数学工具：欧拉角与四元数互转
# ─────────────────────────────────────────────

def quaternion_to_euler(x, y, z, w):
    """四元数转欧拉角 (Roll, Pitch, Yaw) 返回弧度"""
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)

    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return roll, pitch, yaw

def euler_to_quaternion(roll, pitch, yaw):
    """欧拉角转四元数 返回 [x, y, z, w]"""
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    return [x, y, z, w]

# ─────────────────────────────────────────────
# 机器人控制类
# ─────────────────────────────────────────────

class PointDownController:
    def __init__(self, robot):
        self.robot = robot

    def _find_pose(self, status, name):
        """从状态数据中寻找指定 link 的当前位姿"""
        for i, frame_name in enumerate(status.frame_names):
            if frame_name == name:
                p = status.frame_poses[i]
                return {
                    "position":    [p.position.x, p.position.y, p.position.z],
                    "orientation": [p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w],
                }
        raise RuntimeError(f"帧名 '{name}' 未找到")

    def move_end_effector_down(self, arm_name="arm_l_end_link", group=agibot_gdk.EndEffectorControlGroup.kLeftArm):
        """让指定的机械臂末端垂直向下"""
        print("=" * 55)
        print(f"准备执行：让 {arm_name} 末端垂直向下...")
        
        # 1. 获取当前状态
        status = self.robot.get_motion_control_status()
        current_pose = self._find_pose(status, arm_name)
        
        cur_pos = current_pose["position"]
        cur_ori = current_pose["orientation"]

        print(f"  当前位置: {[round(v, 4) for v in cur_pos]}")
        
        # 2. 计算目标姿态 (将四元数转为欧拉角)
        r, p, y = quaternion_to_euler(cur_ori[0], cur_ori[1], cur_ori[2], cur_ori[3])
        
        # 【关键设定】：保持 Yaw 不变，Roll 归零，Pitch 设为 90度 或 -90度
        # 注意：如果机械臂执行后指向了正上方，请将这里的 math.pi / 2 改为 -math.pi / 2
        target_roll = 0.0
        target_pitch = math.pi / 2  # 90度 (或 -90度)
        target_yaw = y              # 保持当前的偏航角，防止手腕乱转

        # 转回目标四元数
        target_quat = euler_to_quaternion(target_roll, target_pitch, target_yaw)
        print(f"  目标欧拉角(度): [Roll: 0, Pitch: 90, Yaw: {math.degrees(target_yaw):.2f}]")

        # 3. 构造并发送指令 (直接原地改变姿态，不需要分步插值，除非角度变化非常大)
        end_pose = agibot_gdk.EndEffectorPose()
        end_pose.life_time = 0.5  # 给予0.5秒的运动时间
        end_pose.group = group

        if group == agibot_gdk.EndEffectorControlGroup.kLeftArm:
            end_pose.left_end_effector_pose.position.x = cur_pos[0]
            end_pose.left_end_effector_pose.position.y = cur_pos[1]
            end_pose.left_end_effector_pose.position.z = cur_pos[2]
            end_pose.left_end_effector_pose.orientation.x = target_quat[0]
            end_pose.left_end_effector_pose.orientation.y = target_quat[1]
            end_pose.left_end_effector_pose.orientation.z = target_quat[2]
            end_pose.left_end_effector_pose.orientation.w = target_quat[3]
        else:
            end_pose.right_end_effector_pose.position.x = cur_pos[0]
            end_pose.right_end_effector_pose.position.y = cur_pos[1]
            end_pose.right_end_effector_pose.position.z = cur_pos[2]
            end_pose.right_end_effector_pose.orientation.x = target_quat[0]
            end_pose.right_end_effector_pose.orientation.y = target_quat[1]
            end_pose.right_end_effector_pose.orientation.z = target_quat[2]
            end_pose.right_end_effector_pose.orientation.w = target_quat[3]

        try:
            ret = self.robot.end_effector_pose_control(end_pose)
            if ret == 0:
                print("  姿态调整指令发送成功！")
            else:
                print(f"  [警告] 指令返回非零: {ret}")
        except Exception as e:
            print(f"  [错误] 发送异常: {e}")

        print("=" * 55)

# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

def main():
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK 初始化失败")
        return
    print("GDK 初始化成功")

    robot = agibot_gdk.Robot()
    time.sleep(2)  # 等待底层状态同步

    try:
        controller = PointDownController(robot)
        
        # 默认控制左手垂直向下
        controller.move_end_effector_down(
            arm_name="arm_l_end_link", 
            group=agibot_gdk.EndEffectorControlGroup.kLeftArm
        )
        
        # 如果你想控制右手，取消下面两行的注释：
        # controller.move_end_effector_down(
        #     arm_name="arm_r_end_link", 
        #     group=agibot_gdk.EndEffectorControlGroup.kRightArm
        # )

    except Exception as e:
        print(f"[运行错误] {e}")

    # 给机器人一点时间执行动作
    time.sleep(1)

    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("GDK释放失败")
    else:
        print("GDK释放成功")

if __name__ == "__main__":
    main()