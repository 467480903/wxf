import agibot_gdk
import time
import math

# ─────────────────────────────────────────────
# 坐标系说明（末端）：
#   X+  向前   Y+  向左   Z+  向上
# ─────────────────────────────────────────────

LEFT_NAME  = "arm_l_end_link"
RIGHT_NAME = "arm_r_end_link"

# ── 控制参数 ──────────────────────────────────
MAX_STEP_CM = 0.1    # 单步最大位移（厘米）
LIFETIME    = 0.02   # 指令生命周期（秒）
RATE_HZ     = 50.0   # 发送频率（Hz）

class SymmetricMoveController:
    def __init__(self, robot):
        self.robot = robot

    # ── 数学与规划工具 ─────────────────────────────────────────────
    @staticmethod
    def slerp(q0, q1, t):
        """四元数球面线性插值 [x, y, z, w]"""
        dot = sum(q0[i] * q1[i] for i in range(4))
        if dot < 0.0:
            dot = -dot
            q1 = [-v for v in q1]
        dot = max(-1.0, min(1.0, dot))
        if dot > 0.9995:
            result = [q0[i] + t * (q1[i] - q0[i]) for i in range(4)]
            norm = math.sqrt(sum(v * v for v in result))
            return [v / norm for v in result] if norm > 0 else result
        theta_0 = math.acos(dot)
        sin_t0  = math.sin(theta_0)
        theta   = theta_0 * t
        s0 = math.cos(theta) - dot * math.sin(theta) / sin_t0
        s1 = math.sin(theta) / sin_t0
        return [s0 * q0[i] + s1 * q1[i] for i in range(4)]

    @staticmethod
    def distance(p1, p2):
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

    def _n_steps(self, start_pos, goal_pos):
        dist_cm = self.distance(start_pos, goal_pos) * 100.0
        return max(int(math.ceil(dist_cm / MAX_STEP_CM)), 1)

    def _plan(self, start_pose, goal_pose, n_steps):
        """生成直线运动的轨迹点序列"""
        traj = []
        for i in range(n_steps):
            t = float(i) / (n_steps - 1) if n_steps > 1 else 0.0
            pos = [start_pose["position"][j] + t * (goal_pose["position"][j] - start_pose["position"][j])
                   for j in range(3)]
            quat = self.slerp(start_pose["orientation"], goal_pose["orientation"], t)
            traj.append({"position": pos, "orientation": quat})
        return traj

    def _find_pose(self, status, name):
        """从状态数据中寻找指定 link 的当前位姿"""
        for i, frame_name in enumerate(status.frame_names):
            if frame_name == name:
                p = status.frame_poses[i]
                return {
                    "position":    [p.position.x, p.position.y, p.position.z],
                    "orientation": [p.orientation.x, p.orientation.y,
                                    p.orientation.z, p.orientation.w],
                }
        raise RuntimeError(f"帧名 '{name}' 未找到")

    # ── 运动执行（仅控制左臂） ─────────────────────────────────────────
    def _send_left_trajectory(self, traj):
        """发送单臂（左臂）的轨迹指令序列"""
        dt = 1.0 / RATE_HZ
        
        for i, wp in enumerate(traj):
            end_pose = agibot_gdk.EndEffectorPose()
            end_pose.life_time = LIFETIME
            # 明确指定只控制左臂
            end_pose.group = agibot_gdk.EndEffectorControlGroup.kLeftArm

            end_pose.left_end_effector_pose.position.x    = wp["position"][0]
            end_pose.left_end_effector_pose.position.y    = wp["position"][1]
            end_pose.left_end_effector_pose.position.z    = wp_position = wp["position"][2]
            end_pose.left_end_effector_pose.orientation.x = wp["orientation"][0]
            end_pose.left_end_effector_pose.orientation.y = wp["orientation"][1]
            end_pose.left_end_effector_pose.orientation.z = wp["orientation"][2]
            end_pose.left_end_effector_pose.orientation.w = wp["orientation"][3]

            try:
                ret = self.robot.end_effector_pose_control(end_pose)
                if ret != 0:
                    print(f"  [警告] 第 {i} 步指令返回非零: {ret}")
                    return False
            except Exception as e:
                print(f"  [错误] 第 {i} 步发送异常: {e}")
                return False

            time.sleep(dt)
        return True

    # ── 主流程 ───────────────────────────────────────────────
    def move_left_to_symmetric_right(self):
        """获取双臂当前位置，计算对称点，并移动左臂"""
        print("=" * 55)
        print("准备执行：左臂向右臂的对称位置移动...")
        
        # 1. 获取当前状态
        status = self.robot.get_motion_control_status()
        start_l = self._find_pose(status, LEFT_NAME)
        start_r = self._find_pose(status, RIGHT_NAME)

        print(f"  左手当前位置: {[round(v, 4) for v in start_l['position']]}")
        print(f"  右手当前位置: {[round(v, 4) for v in start_r['position']]}")

        # 2. 计算目标位姿
        # 位置：X和Z与右臂对齐，Y取反（右臂的Y是负的，取反就是正的，即左侧）
        target_pos_l = [
            start_r["position"][0],       # X 相同
            -start_r["position"][1],      # Y 对称取反 (例如 -0.0952 变成 0.0952)
            start_r["position"][2]        # Z 相同
        ]
        
        # 姿态：为了避免手腕乱转，直接沿用左臂当前的姿态
        target_ori_l = list(start_l["orientation"])

        target_l = {
            "position": target_pos_l,
            "orientation": target_ori_l
        }
        
        print(f"  左手目标位置: {[round(v, 4) for v in target_pos_l]}")

        # 3. 规划轨迹
        n_steps = self._n_steps(start_l["position"], target_l["position"])
        print(f"  规划步数: {n_steps} 步")
        traj_l = self._plan(start_l, target_l, n_steps)

        # 4. 执行轨迹 (因为 group 设为了 kLeftArm，右臂会默认保持原本的姿态维持不动)
        print("  正在执行...")
        success = self._send_left_trajectory(traj_l)
        
        if success:
            print("左臂对称移动完成！")
        else:
            print("左臂对称移动失败！")
        print("=" * 55)
        
        return success


def main():
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK 初始化失败")
        return
    print("GDK 初始化成功")

    robot = agibot_gdk.Robot()
    time.sleep(2)   # 等待机器人就绪同步状态

    try:
        controller = SymmetricMoveController(robot)
        
        # 执行对称移动
        controller.move_left_to_symmetric_right()

    except Exception as e:
        print(f"[运行错误] {e}")

    # 释放GDK系统资源
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("GDK释放失败")
    else:
        print("GDK释放成功")

if __name__ == "__main__":
    main()