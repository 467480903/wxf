import agibot_gdk
import time
import math


# 常量定义
LEFT_NAME = "arm_l_end_link"
RIGHT_NAME = "arm_r_end_link"

# 第一组目标位姿（位置和四元数）
TARGET1_LEFT_POSITION = [0.516, 0.433, 1.081]
TARGET1_LEFT_ORIENTATION = [0.382, -0.146, 0.663, 0.626]
TARGET1_RIGHT_POSITION = [0.579, -0.306, 1.158]
TARGET1_RIGHT_ORIENTATION = [0.320, 0.655, 0.651, 0.206]

# 第二组目标位姿
TARGET2_LEFT_POSITION = [0.516, 0.433, 1.0]
TARGET2_LEFT_ORIENTATION = [0.382, -0.146, 0.663, 0.626]
TARGET2_RIGHT_POSITION = [0.579, -0.306, 1.0]
TARGET2_RIGHT_ORIENTATION = [0.320, 0.655, 0.651, 0.206]

# 控制参数
MAX_STEP_CM = 0.1  # 最大步长（厘米）
LIFETIME = 0.02    # 生命周期（秒）
RATE_HZ = 50.0     # 发送频率（Hz）


class EndEffectorController:
    def __init__(self, robot):
        self.robot = robot

    def slerp(self, q0, q1, t):
        """
        四元数球面线性插值
        q0, q1: 四元数 [x, y, z, w]
        t: 插值参数 [0, 1]
        返回: 插值后的四元数 [x, y, z, w]
        """
        # 计算点积
        dot = q0[0]*q1[0] + q0[1]*q1[1] + q0[2]*q1[2] + q0[3]*q1[3]

        # 如果点积为负，取反q1以确保最短路径
        if dot < 0.0:
            dot = -dot
            q1_neg = [-q1[0], -q1[1], -q1[2], -q1[3]]
            result = [q0[i] + t * (q1_neg[i] - q0[i]) for i in range(4)]
        else:
            result = [q0[i] + t * (q1[i] - q0[i]) for i in range(4)]

        # 限制点积范围
        dot = max(-1.0, min(1.0, dot))

        if dot > 0.9995:
            # 线性插值
            norm = math.sqrt(sum(r*r for r in result))
            if norm > 0.0:
                result = [r / norm for r in result]
        else:
            # 球面线性插值
            theta_0 = math.acos(dot)
            sin_theta_0 = math.sin(theta_0)
            theta = theta_0 * t
            sin_theta = math.sin(theta)
            s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
            s1 = sin_theta / sin_theta_0

            result = [s0 * q0[i] + s1 * q1[i] for i in range(4)]

        return result

    def distance_between_points(self, p1, p2):
        """计算两点之间的距离"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)

    def calculate_n_steps(self, start_pos, goal_pos, max_step_cm):
        """计算需要的步数"""
        dist_cm = self.distance_between_points(start_pos, goal_pos) * 100.0
        return max(int(math.ceil(dist_cm / max_step_cm)), 1)

    def plan_trajectory(self, start_pose, goal_pose, n_steps):
        """
        规划轨迹
        start_pose, goal_pose: 包含position和orientation的字典
        n_steps: 步数
        返回: 轨迹列表
        """
        trajectory = []

        for i in range(n_steps):
            t = float(i) / (n_steps - 1) if n_steps > 1 else 0.0

            # 位置线性插值
            pos = [
                start_pose['position'][0] + t * (goal_pose['position'][0] - start_pose['position'][0]),
                start_pose['position'][1] + t * (goal_pose['position'][1] - start_pose['position'][1]),
                start_pose['position'][2] + t * (goal_pose['position'][2] - start_pose['position'][2])
            ]

            # 四元数SLERP插值
            q0 = start_pose['orientation']
            q1 = goal_pose['orientation']
            quat = self.slerp(q0, q1, t)

            trajectory.append({
                'position': pos,
                'orientation': quat
            })

        return trajectory

    def find_pose_by_name(self, status, target_name):
        """根据名称查找位姿"""
        for i, frame_name in enumerate(status.frame_names):
            if frame_name == target_name:
                pose = status.frame_poses[i]
                # 提取位置和四元数
                position = [pose.position.x, pose.position.y, pose.position.z]
                orientation = [pose.orientation.x, pose.orientation.y,
                              pose.orientation.z, pose.orientation.w]
                return {'position': position, 'orientation': orientation}
        raise RuntimeError(f"Frame name {target_name} not found")

    def move_to_pose(self, left_goal=None, right_goal=None, hold_final=False):
        """
        通用移动函数
        left_goal: 左臂目标位姿字典，如果为None则左臂不动
        right_goal: 右臂目标位姿字典，如果为None则右臂不动
        hold_final: 是否保持最终位姿
        """
        if left_goal is None and right_goal is None:
            print("没有指定任何目标位姿")
            return

        # 获取当前状态
        status = self.robot.get_motion_control_status()
        
        # 获取起始位姿
        start_left_pose = None
        start_right_pose = None
        
        if left_goal is not None:
            start_left_pose = self.find_pose_by_name(status, LEFT_NAME)
            print(f"左臂当前位置: {start_left_pose['position']}")
            print(f"左臂目标位置: {left_goal['position']}")
        
        if right_goal is not None:
            start_right_pose = self.find_pose_by_name(status, RIGHT_NAME)
            print(f"右臂当前位置: {start_right_pose['position']}")
            print(f"右臂目标位置: {right_goal['position']}")

        # 计算步数
        n_left = 1
        n_right = 1
        
        if left_goal is not None:
            n_left = self.calculate_n_steps(start_left_pose['position'],
                                           left_goal['position'],
                                           MAX_STEP_CM)
        
        if right_goal is not None:
            n_right = self.calculate_n_steps(start_right_pose['position'],
                                            right_goal['position'],
                                            MAX_STEP_CM)
        
        n_steps = max(n_left, n_right)
        
        print(f"左臂步数: {n_left}, 右臂步数: {n_right}, 总步数: {n_steps}")

        # 规划轨迹
        traj_left = None
        traj_right = None
        
        if left_goal is not None:
            traj_left = self.plan_trajectory(start_left_pose, left_goal, n_steps)
        
        if right_goal is not None:
            traj_right = self.plan_trajectory(start_right_pose, right_goal, n_steps)

        # 执行轨迹
        dt = 1.0 / RATE_HZ
        for i in range(n_steps):
            # 创建末端执行器位姿控制请求
            end_pose = agibot_gdk.EndEffectorPose()
            end_pose.life_time = LIFETIME
            
            # 设置控制组
            if left_goal is not None and right_goal is not None:
                end_pose.group = agibot_gdk.EndEffectorControlGroup.kBothArms
            elif left_goal is not None:
                end_pose.group = agibot_gdk.EndEffectorControlGroup.kLeftArm
            else:
                end_pose.group = agibot_gdk.EndEffectorControlGroup.kRightArm

            # 设置左臂位姿
            if left_goal is not None:
                end_pose.left_end_effector_pose.position.x = traj_left[i]['position'][0]
                end_pose.left_end_effector_pose.position.y = traj_left[i]['position'][1]
                end_pose.left_end_effector_pose.position.z = traj_left[i]['position'][2]
                end_pose.left_end_effector_pose.orientation.x = traj_left[i]['orientation'][0]
                end_pose.left_end_effector_pose.orientation.y = traj_left[i]['orientation'][1]
                end_pose.left_end_effector_pose.orientation.z = traj_left[i]['orientation'][2]
                end_pose.left_end_effector_pose.orientation.w = traj_left[i]['orientation'][3]

            # 设置右臂位姿
            if right_goal is not None:
                end_pose.right_end_effector_pose.position.x = traj_right[i]['position'][0]
                end_pose.right_end_effector_pose.position.y = traj_right[i]['position'][1]
                end_pose.right_end_effector_pose.position.z = traj_right[i]['position'][2]
                end_pose.right_end_effector_pose.orientation.x = traj_right[i]['orientation'][0]
                end_pose.right_end_effector_pose.orientation.y = traj_right[i]['orientation'][1]
                end_pose.right_end_effector_pose.orientation.z = traj_right[i]['orientation'][2]
                end_pose.right_end_effector_pose.orientation.w = traj_right[i]['orientation'][3]

            try:
                result = self.robot.end_effector_pose_control(end_pose)
                if result != 0:
                    print(f"控制命令发送失败，步数: {i}")
                    return False
            except Exception as e:
                print(f"控制命令发送异常，步数: {i}, 错误: {e}")
                return False

            time.sleep(dt)
        
        return True

    def left_movel(self, target_position, target_orientation, hold_final=False):
        """
        左臂直线运动（MoveL）
        target_position: 目标位置 [x, y, z]
        target_orientation: 目标姿态四元数 [x, y, z, w]
        hold_final: 是否保持最终位姿
        """
        print(f"\n执行左臂MoveL运动...")
        goal_pose = {
            'position': target_position,
            'orientation': target_orientation
        }
        return self.move_to_pose(left_goal=goal_pose, right_goal=None, hold_final=hold_final)

    def right_movel(self, target_position, target_orientation, hold_final=False):
        """
        右臂直线运动（MoveL）
        target_position: 目标位置 [x, y, z]
        target_orientation: 目标姿态四元数 [x, y, z, w]
        hold_final: 是否保持最终位姿
        """
        print(f"\n执行右臂MoveL运动...")
        goal_pose = {
            'position': target_position,
            'orientation': target_orientation
        }
        return self.move_to_pose(left_goal=None, right_goal=goal_pose, hold_final=hold_final)

    def both_movel(self, left_target, right_target, hold_final=False):
        """
        双臂同时直线运动
        left_target: (position, orientation) 左臂目标
        right_target: (position, orientation) 右臂目标
        hold_final: 是否保持最终位姿
        """
        print(f"\n执行双臂MoveL运动...")
        left_goal = {
            'position': left_target[0],
            'orientation': left_target[1]
        }
        right_goal = {
            'position': right_target[0],
            'orientation': right_target[1]
        }
        return self.move_to_pose(left_goal=left_goal, right_goal=right_goal, hold_final=hold_final)

    def execute_sequence(self):
        """执行顺序运动序列"""
        print("=" * 50)
        print("开始执行运动序列")
        print("=" * 50)
        
        # 1. 左臂移动到第一组位置
        print("\n[步骤1] 左臂移动到第一组位置")
        self.left_movel(TARGET1_LEFT_POSITION, TARGET1_LEFT_ORIENTATION, hold_final=True)
        time.sleep(1.0)
        self.left_movel(TARGET2_LEFT_POSITION, TARGET2_LEFT_ORIENTATION, hold_final=True)
        time.sleep(1.0)
        
        # 2. 右臂移动到第一组位置
        print("\n[步骤2] 右臂移动到第一组位置")
        self.right_movel(TARGET1_RIGHT_POSITION, TARGET1_RIGHT_ORIENTATION, hold_final=True)
        time.sleep(1.0)
        self.right_movel(TARGET2_RIGHT_POSITION, TARGET2_RIGHT_ORIENTATION, hold_final=True)
        time.sleep(1.0)        
        
        # 3. 双臂同时移动到第二组位置
        # print("\n[步骤3] 双臂同时移动到第二组位置")
        # left_target = (TARGET2_LEFT_POSITION, TARGET2_LEFT_ORIENTATION)
        # right_target = (TARGET2_RIGHT_POSITION, TARGET2_RIGHT_ORIENTATION)
        # self.both_movel(left_target, right_target, hold_final=True)
        # time.sleep(1.0)
        
        # # 4. 双臂同时移动回第一组位置
        # print("\n[步骤4] 双臂同时移动回第一组位置")
        # left_target = (TARGET1_LEFT_POSITION, TARGET1_LEFT_ORIENTATION)
        # right_target = (TARGET1_RIGHT_POSITION, TARGET1_RIGHT_ORIENTATION)
        # self.both_movel(left_target, right_target, hold_final=True)
        
        print("\n" + "=" * 50)
        print("运动序列执行完成")
        print("=" * 50)


def main():
    # 初始化GDK系统
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK初始化失败")
        return

    print("GDK初始化成功")

    try:
        robot = agibot_gdk.Robot()
        time.sleep(2)  # 等待机器人初始化

        controller = EndEffectorController(robot)
        
        # 方式1：执行预设的运动序列
        controller.execute_sequence()
        
        # 方式2：单独调用MoveL函数
        # controller.left_movel(TARGET1_LEFT_POSITION, TARGET1_LEFT_ORIENTATION, hold_final=True)
        # time.sleep(1.0)
        # controller.right_movel(TARGET1_RIGHT_POSITION, TARGET1_RIGHT_ORIENTATION, hold_final=True)
        
        # 方式3：双臂同时运动
        # left_target = (TARGET2_LEFT_POSITION, TARGET2_LEFT_ORIENTATION)
        # right_target = (TARGET2_RIGHT_POSITION, TARGET2_RIGHT_ORIENTATION)
        # controller.both_movel(left_target, right_target, hold_final=True)

    except Exception as e:
        print(f"执行过程中发生错误: {e}")
    finally:
        # 释放GDK系统资源
        if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
            print("GDK释放失败")
        else:
            print("GDK释放成功")


if __name__ == "__main__":
    main()