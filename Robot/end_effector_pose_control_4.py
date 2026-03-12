import agibot_gdk
import time
import math


# 常量定义
LEFT_NAME = "arm_l_end_link"
RIGHT_NAME = "arm_r_end_link"

# 控制参数
MAX_STEP_CM = 0.1  # 最大步长（厘米）
LIFETIME = 0.02    # 生命周期（秒）
RATE_HZ = 50.0     # 发送频率（Hz）
MOVE_UP_DISTANCE = 0.05  # 向上移动的距离（米）


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

            # 四元数SLERP插值（此处姿态不变，插值结果也不变）
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
            
            # 设置控制组（只控制左臂）
            end_pose.group = agibot_gdk.EndEffectorControlGroup.kLeftArm

            # 设置左臂位姿
            if left_goal is not None:
                end_pose.left_end_effector_pose.position.x = traj_left[i]['position'][0]
                end_pose.left_end_effector_pose.position.y = traj_left[i]['position'][1]
                end_pose.left_end_effector_pose.position.z = traj_left[i]['position'][2]
                end_pose.left_end_effector_pose.orientation.x = traj_left[i]['orientation'][0]
                end_pose.left_end_effector_pose.orientation.y = traj_left[i]['orientation'][1]
                end_pose.left_end_effector_pose.orientation.z = traj_left[i]['orientation'][2]
                end_pose.left_end_effector_pose.orientation.w = traj_left[i]['orientation'][3]

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

    def move_left_up(self, distance=MOVE_UP_DISTANCE, hold_final=True):
        """
        左臂在当前位姿基础上向上移动指定距离，保持姿态不变
        distance: 向上移动的距离（米），默认0.05米
        hold_final: 是否保持最终位姿
        """
        print(f"\n执行左臂向上移动{distance}米...")
        
        # 获取当前状态和左臂当前位姿
        status = self.robot.get_motion_control_status()
        current_pose = self.find_pose_by_name(status, LEFT_NAME)
        
        # 构建目标位姿（只修改Z轴位置，姿态保持不变）
        goal_pose = {
            'position': [
                current_pose['position'][0]-distance,  # X轴位置不变
                current_pose['position'][1],  # Y轴位置不变
                current_pose['position'][2]   # Z轴位置增加指定距离
            ],
            'orientation': current_pose['orientation']  # 姿态完全不变
        }
        
        print(f"左臂当前位置: {current_pose['position']}")
        print(f"左臂目标位置: {goal_pose['position']}")
        
        return self.move_to_pose(left_goal=goal_pose, right_goal=None, hold_final=hold_final)

    def execute_sequence(self):
        """执行顺序运动序列"""
        print("=" * 50)
        print("开始执行运动序列")
        print("=" * 50)
        
        # 只执行左臂向上移动的动作
        self.move_left_up()
        time.sleep(1.0)
        
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
        
        # 执行预设的运动序列（只动左臂向上移动）
        controller.execute_sequence()
        
        # 也可以单独调用：
        # controller.move_left_up(distance=0.05)

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