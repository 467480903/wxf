import agibot_gdk
import time
import math
import json
import os

# ─────────────────────────────────────────────
# 坐标系说明（左臂末端）：
#   X+  向前   Y+  向左   Z+  向上
# ─────────────────────────────────────────────

LEFT_NAME  = "arm_l_end_link"
RIGHT_NAME = "arm_r_end_link"

# ── 视觉↔机械臂 Y 轴线性映射标定参数 ──────────
#   标定点1: 视觉 x=308.67  →  臂 Y=0.1224
#   标定点2: 视觉 x=208.34  →  臂 Y=0.3123
CAL_VIS_X1, CAL_ARM_Y1 = 308.67, 0.1224
CAL_VIS_X2, CAL_ARM_Y2 = 208.34, 0.3123
VIS_TO_ARM_Y_SLOPE = (CAL_ARM_Y2 - CAL_ARM_Y1) / (CAL_VIS_X2 - CAL_VIS_X1)   # ≈ -0.001893 m/px

# ── 固定 X / Z / 姿态（无视觉对应关系，沿用标定参考值）──
REF_ARM_X   = 0.7048   # 前后方向（米）
REF_ARM_Z   = 0.8008   # 上下方向（米）
REF_ARM_ORI = [-0.4228, 0.5536, -0.5152, 0.4993]   # [x, y, z, w]

# ── 接近偏移 ──────────────────────────────────
APPROACH_OFFSET_X = 0.05   # 先后退 / 再距目标偏后 0.05 m

# ── 控制参数 ──────────────────────────────────
MAX_STEP_CM = 0.1    # 单步最大位移（厘米）
LIFETIME    = 0.02   # 指令生命周期（秒）
RATE_HZ     = 50.0   # 发送频率（Hz）

# ── 视觉文件路径 ──────────────────────────────
VISUAL_JSON_PATH = "/data/wxf/images/first_bottle_coordinate.json"


# ═══════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════

def load_visual_result(json_path: str) -> dict:
    """读取视觉解析 JSON，返回 first_bottle 字典"""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"视觉文件不存在: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    bottle = data.get("first_bottle")
    if bottle is None:
        raise ValueError("JSON 中未找到 'first_bottle' 字段")
    return bottle


def visual_to_arm_pose(visual_center_x: float) -> dict:
    """
    将视觉中心点 x 像素坐标转换为机械臂目标位姿。
    Y 轴通过线性插值计算，X / Z / 姿态使用参考值。
    """
    arm_y = CAL_ARM_Y1 + (visual_center_x - CAL_VIS_X1) * VIS_TO_ARM_Y_SLOPE
    return {
        "position":    [REF_ARM_X, arm_y, REF_ARM_Z],
        "orientation": list(REF_ARM_ORI),
    }


# ═══════════════════════════════════════════════════════════════
#  末端执行器控制器
# ═══════════════════════════════════════════════════════════════

class EndEffectorController:

    def __init__(self, robot):
        self.robot = robot

    # ── 数学工具 ─────────────────────────────────────────────

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
        traj = []
        for i in range(n_steps):
            t = float(i) / (n_steps - 1) if n_steps > 1 else 0.0
            pos = [start_pose["position"][j] + t * (goal_pose["position"][j] - start_pose["position"][j])
                   for j in range(3)]
            quat = self.slerp(start_pose["orientation"], goal_pose["orientation"], t)
            traj.append({"position": pos, "orientation": quat})
        return traj

    def _find_pose(self, status, name):
        for i, frame_name in enumerate(status.frame_names):
            if frame_name == name:
                p = status.frame_poses[i]
                return {
                    "position":    [p.position.x, p.position.y, p.position.z],
                    "orientation": [p.orientation.x, p.orientation.y,
                                    p.orientation.z, p.orientation.w],
                }
        raise RuntimeError(f"帧名 '{name}' 未找到")

    # ── 运动执行 ─────────────────────────────────────────────

    def _send_trajectory(self, traj_left):
        """发送左臂轨迹指令序列"""
        dt = 1.0 / RATE_HZ
        for i, wp in enumerate(traj_left):
            end_pose = agibot_gdk.EndEffectorPose()
            end_pose.life_time = LIFETIME
            end_pose.group     = agibot_gdk.EndEffectorControlGroup.kLeftArm

            end_pose.left_end_effector_pose.position.x    = wp["position"][0]
            end_pose.left_end_effector_pose.position.y    = wp["position"][1]
            end_pose.left_end_effector_pose.position.z    = wp["position"][2]
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

    def left_movel(self, target_pose: dict, label: str = "") -> bool:
        """左臂直线运动到 target_pose（含插值）"""
        tag = f"[{label}] " if label else ""
        status = self.robot.get_motion_control_status()
        start  = self._find_pose(status, LEFT_NAME)
        n      = self._n_steps(start["position"], target_pose["position"])
        traj   = self._plan(start, target_pose, n)

        print(f"  {tag}起点: {[round(v,4) for v in start['position']]}")
        print(f"  {tag}终点: {[round(v,4) for v in target_pose['position']]}")
        print(f"  {tag}步数: {n}")

        return self._send_trajectory(traj)

    # ── 夹爪控制 ─────────────────────────────────────────────

    def control_gripper(self, position: float, label: str = ""):
        """
        控制左夹爪
        position: 0 = 张开, 1 = 闭合
        """
        tag = f"[{label}] " if label else ""
        joint_states_left = agibot_gdk.JointStates()
        joint_states_left.group = "left_tool"
        joint_states_left.target_type = "omnipicker"

        joint_state = agibot_gdk.JointState()
        joint_state.position = position  # 取值范围 [0, 1]
        joint_states_left.states = [joint_state]
        joint_states_left.nums = len(joint_states_left.states)

        try:
            result = self.robot.move_ee_pos(joint_states_left)
            print(f"{tag}夹爪控制成功，位置: {position}")
            return True
        except Exception as e:
            print(f"{tag}夹爪控制失败: {e}")
            return False

    # ── 主流程 ───────────────────────────────────────────────

    def fetch_from_visual(self, visual_json_path: str = VISUAL_JSON_PATH):
        """
        根据视觉解析结果执行抓取运动：
          1. 张开爪子
          2. 当前位置 → 向后退 0.05 m（X 减小）
          3. 后退位置 → 目标偏后 0.05 m（X 减小）
          4. 目标偏后 → 目标位置 C（抓取点）
          5. 合拢爪子
          6. 目标位置 C → 抬起位置 E（向上+向后）
          7. 张开爪子
        """
        print("=" * 55)
        print("读取视觉解析文件 …")
        bottle    = load_visual_result(visual_json_path)
        vis_cx    = bottle["center"]["x"]
        vis_cy    = bottle["center"]["y"]
        conf      = bottle.get("confidence", 0.0)
        print(f"  视觉中心: x={vis_cx:.2f} px, y={vis_cy:.2f} px, 置信度={conf:.2f}")

        # 计算目标位姿
        target_pose = visual_to_arm_pose(vis_cx)
        print(f"  映射臂坐标: {[round(v,4) for v in target_pose['position']]}")
        print("=" * 55)

        # ── 获取当前左臂位姿 ──────────────────────────────────
        status       = self.robot.get_motion_control_status()
        current_pose = self._find_pose(status, LEFT_NAME)
        cur_pos      = current_pose["position"]
        cur_ori      = current_pose["orientation"]

        # ── 定义路径点 ────────────────────────────────────────
        # 点 A：当前位置向后退 0.05 m
        pose_A = {
            "position":    [cur_pos[0] - APPROACH_OFFSET_X,
                            cur_pos[1],
                            cur_pos[2]],
            "orientation": list(cur_ori),
        }
        # 点 B：目标偏后 0.05 m（姿态已切换为目标姿态）
        pose_B = {
            "position":    [target_pose["position"][0] - APPROACH_OFFSET_X,
                            target_pose["position"][1],
                            target_pose["position"][2]],
            "orientation": list(target_pose["orientation"]),
        }
        # 点 C：目标位置（抓取点）
        pose_C = target_pose
        
        # 点 E：抓取后抬起位置（向上+向后）
        pose_E = {
            "position":    [target_pose["position"][0] - APPROACH_OFFSET_X*4,
                            target_pose["position"][1],
                            target_pose["position"][2] + APPROACH_OFFSET_X*1],
            "orientation": list(target_pose["orientation"]),
        }

        # ── 步骤 1: 张开爪子 ──────────────────────────────────
        print("\n[步骤 1/7]  张开爪子")
        if not self.control_gripper(0, "张开"):
            print("  夹爪控制失败，中止")
            return False
        time.sleep(0.5)

        # ── 步骤 2: 当前位置 → 向后退 0.05 m ──────────────────
        print("\n[步骤 2/7]  当前位置 → 向后退 0.05 m")
        if not self.left_movel(pose_A, "退后"):
            print("  运动失败，中止")
            return False
        time.sleep(0.5)

        # ── 步骤 3: 退后位置 → 目标偏后 0.05 m（对齐 Y / Z） ──
        print("\n[步骤 3/7]  退后位置 → 目标偏后 0.05 m（对齐 Y / Z）")
        if not self.left_movel(pose_B, "对齐"):
            print("  运动失败，中止")
            return False
        time.sleep(0.5)

        # ── 步骤 4: 目标偏后 → 目标位置 C（向前插入抓取） ─────
        print("\n[步骤 4/7]  目标偏后 → 目标位置 C（抓取点）")
        if not self.left_movel(pose_C, "插入抓取"):
            print("  运动失败，中止")
            return False
        time.sleep(0.5)

        # ── 步骤 5: 合拢爪子（抓取） ──────────────────────────
        print("\n[步骤 5/7]  合拢爪子（抓取）")
        if not self.control_gripper(1, "闭合"):
            print("  夹爪控制失败，中止")
            return False
        time.sleep(0.5)

        # ── 步骤 6: 目标位置 C → 抬起位置 E（向上+向后） ──────
        print("\n[步骤 6/7]  目标位置 C → 抬起位置 E（向上+向后）")
        if not self.left_movel(pose_E, "抬起"):
            print("  运动失败，中止")
            return False
        time.sleep(0.5)

        # ── 步骤 7: 张开爪子（释放） ──────────────────────────
        print("\n[步骤 7/7]  张开爪子（释放）")
        if not self.control_gripper(0, "张开释放"):
            print("  夹爪控制失败，中止")
            return False

        print("\n" + "=" * 55)
        print("抓取任务完成")
        print("=" * 55)
        return True


# ═══════════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════════

def main():
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK 初始化失败")
        return
    print("GDK 初始化成功")

    robot = agibot_gdk.Robot()
    time.sleep(2)   # 等待机器人就绪

    try:
        controller = EndEffectorController(robot)
        controller.fetch_from_visual(VISUAL_JSON_PATH)

    except FileNotFoundError as e:
        print(f"[文件错误] {e}")
    except ValueError as e:
        print(f"[数据错误] {e}")
    except Exception as e:
        print(f"[运行错误] {e}")

    # 释放GDK系统资源
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("GDK释放失败")
    else:
        print("GDK释放成功")

if __name__ == "__main__":
    main()