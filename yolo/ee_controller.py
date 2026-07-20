import agibot_gdk
import time
import math

LEFT_NAME  = "arm_l_end_link"
RIGHT_NAME = "arm_r_end_link"

MAX_STEP_CM = 0.1
LIFETIME    = 0.02
RATE_HZ     = 50.0


class EndEffectorController:

    def __init__(self, robot):
        self.robot = robot

    @staticmethod
    def slerp(q0, q1, t):
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
        raise RuntimeError(f"Frame '{name}' not found")

    def _send_dual_trajectory(self, traj_left, traj_right):
        dt = 1.0 / RATE_HZ
        steps = len(traj_left)

        for i in range(steps):
            wp_l = traj_left[i]
            wp_r = traj_right[i]

            end_pose_l = agibot_gdk.EndEffectorPose()
            end_pose_l.life_time = LIFETIME
            end_pose_l.group     = agibot_gdk.EndEffectorControlGroup.kLeftArm

            end_pose_l.left_end_effector_pose.position.x    = wp_l["position"][0]
            end_pose_l.left_end_effector_pose.position.y    = wp_l["position"][1]
            end_pose_l.left_end_effector_pose.position.z    = wp_l["position"][2]
            end_pose_l.left_end_effector_pose.orientation.x = wp_l["orientation"][0]
            end_pose_l.left_end_effector_pose.orientation.y = wp_l["orientation"][1]
            end_pose_l.left_end_effector_pose.orientation.z = wp_l["orientation"][2]
            end_pose_l.left_end_effector_pose.orientation.w = wp_l["orientation"][3]

            end_pose_r = agibot_gdk.EndEffectorPose()
            end_pose_r.life_time = LIFETIME
            end_pose_r.group     = agibot_gdk.EndEffectorControlGroup.kRightArm

            end_pose_r.right_end_effector_pose.position.x    = wp_r["position"][0]
            end_pose_r.right_end_effector_pose.position.y    = wp_r["position"][1]
            end_pose_r.right_end_effector_pose.position.z    = wp_r["position"][2]
            end_pose_r.right_end_effector_pose.orientation.x = wp_r["orientation"][0]
            end_pose_r.right_end_effector_pose.orientation.y = wp_r["orientation"][1]
            end_pose_r.right_end_effector_pose.orientation.z = wp_r["orientation"][2]
            end_pose_r.right_end_effector_pose.orientation.w = wp_r["orientation"][3]

            try:
                ret_l = self.robot.end_effector_pose_control(end_pose_l)
                time.sleep(0.002)
                ret_r = self.robot.end_effector_pose_control(end_pose_r)

                if ret_l != 0 or ret_r != 0:
                    print(f"  [WARN] step {i}: left={ret_l}, right={ret_r}")
                    return False
            except Exception as e:
                print(f"  [ERROR] step {i}: {e}")
                return False

            time.sleep(max(0.0, dt - 0.002))

        return True

    def adjust_arms_relative(self, offset_l=(0.0, 0.0, 0.0), offset_r=(0.0, 0.0, 0.0)) -> bool:
        print("=" * 55)
        print(f"adjust_arms_relative:")
        print(f"  left  (X, Y, Z): {offset_l}")
        print(f"  right (X, Y, Z): {offset_r}")

        status = self.robot.get_motion_control_status()
        start_l = self._find_pose(status, LEFT_NAME)
        start_r = self._find_pose(status, RIGHT_NAME)

        target_l = {
            "position": [
                start_l["position"][0] + offset_l[0],
                start_l["position"][1] + offset_l[1],
                start_l["position"][2] + offset_l[2]
            ],
            "orientation": list(start_l["orientation"])
        }

        target_r = {
            "position": [
                start_r["position"][0] + offset_r[0],
                start_r["position"][1] + offset_r[1],
                start_r["position"][2] + offset_r[2]
            ],
            "orientation": list(start_r["orientation"])
        }

        n_l = self._n_steps(start_l["position"], target_l["position"])
        n_r = self._n_steps(start_r["position"], target_r["position"])
        n_steps = max(n_l, n_r)

        if n_steps <= 1:
            print("  target too close, skip.")
            return True

        print(f"  steps: {n_steps}")

        traj_l = self._plan(start_l, target_l, n_steps)
        traj_r = self._plan(start_r, target_r, n_steps)

        print("  executing...")
        success = self._send_dual_trajectory(traj_l, traj_r)

        if success:
            print("done")
        else:
            print("failed")
        print("=" * 55)

        return success


def init_gdk():
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK init failed")
        return None, None
    print("GDK init ok")
    robot = agibot_gdk.Robot()
    time.sleep(2)
    return robot, agibot_gdk


def release_gdk():
    if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
        print("GDK release failed")
    else:
        print("GDK release ok")
