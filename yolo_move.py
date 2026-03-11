#!/usr/bin/env python3
"""
完整抓取流程：
1. 拍摄头部彩色相机图片
2. YOLO检测第一个矿泉水瓶，获取中心x坐标
3. 根据视觉结果移动机械臂进行抓取
"""

import agibot_gdk
import time
import math
import json
import os
import numpy as np
import cv2
from ultralytics import YOLO

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
LIFT_OFFSET_X = 0.2        # 抬起时的向后偏移（米）
LIFT_OFFSET_Z = 0.1         # 抬起时的向上偏移（米）

# ── 控制参数 ──────────────────────────────────
MAX_STEP_CM = 0.1    # 单步最大位移（厘米）
LIFETIME    = 0.02   # 指令生命周期（秒）
RATE_HZ     = 50.0   # 发送频率（Hz）

# ── 视觉参数 ──────────────────────────────────
WATER_BOTTLE_CLASS_ID = 39  # 矿泉水瓶在COCO数据集中的类别ID
YOLO_MODEL_PATH = 'yolov8n.pt'  # YOLO模型路径
SAVE_DIR = "images"  # 图片保存目录
VISUAL_JSON_PATH = os.path.join(SAVE_DIR, "first_bottle_coordinate.json")  # 视觉结果保存路径


# ═══════════════════════════════════════════════════════════════
#  视觉识别模块
# ═══════════════════════════════════════════════════════════════

def decode_camera_image(image) -> np.ndarray:
    """将agibot_gdk的CameraImage对象解码为OpenCV格式的图像"""
    if not hasattr(image, 'data') or not image.data.any():
        raise ValueError("图像数据为空")
    
    # 处理最常见的JPEG编码
    if image.encoding == agibot_gdk.Encoding.JPEG:
        nparr = np.frombuffer(image.data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    # 兼容未压缩格式（备用）
    elif image.encoding == agibot_gdk.Encoding.UNCOMPRESSED:
        if image.color_format == agibot_gdk.ColorFormat.RGB:
            img = np.frombuffer(image.data, dtype=np.uint8).reshape((image.height, image.width, 3))
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)  # 转OpenCV默认的BGR格式
        elif image.color_format == agibot_gdk.ColorFormat.BGR:
            img = np.frombuffer(image.data, dtype=np.uint8).reshape((image.height, image.width, 3))
        else:
            raise ValueError(f"不支持的颜色格式: {image.color_format}")
    else:
        raise ValueError(f"不支持的编码格式: {image.encoding}")
    
    return img

def save_visual_result(bottle_data, img_info=None, save_path=VISUAL_JSON_PATH):
    """将第一个矿泉水瓶坐标保存为JSON格式文本文件"""
    # 构造完整的JSON数据结构
    json_data = {
        "timestamp": int(time.time()),
        "image_info": img_info if img_info else {"width": 0, "height": 0},
        "first_bottle": bottle_data
    }
    
    # 确保目录存在
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # 写入JSON文件（格式化输出，便于阅读和解析）
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n第一个矿泉水瓶坐标已保存到：{save_path}")
    return save_path

def detect_bottle_with_yolo():
    """
    使用YOLO检测第一个矿泉水瓶
    返回: (成功标志, 视觉中心x坐标, 完整bottle数据)
    """
    print("=" * 55)
    print("开始视觉识别流程")
    print("=" * 55)
    
    # 初始化相机
    camera = agibot_gdk.Camera()
    time.sleep(2)
    
    # 只使用头部彩色相机
    cam_type = agibot_gdk.CameraType.kHeadColor
    
    # 加载预训练模型
    print(f"加载YOLO模型: {YOLO_MODEL_PATH}")
    model = YOLO(YOLO_MODEL_PATH)
    
    try:
        # 1. 获取相机图像
        img = camera.get_latest_image(cam_type, 1000.0)

        if img is not None:
            print(f"拍摄成功：{img.width}x{img.height}")

            # 创建保存目录
            os.makedirs(SAVE_DIR, exist_ok=True)
            
            # 2. 保存原始图片
            raw_filename = os.path.join(SAVE_DIR, "head_color.jpg")
            with open(raw_filename, "wb") as f:
                f.write(img.data)
            print(f"原始图片已保存：{raw_filename}")

            # 3. 解码图像为YOLO可处理的格式
            cv_img = decode_camera_image(img)
            
            # 4. YOLO目标检测（筛选矿泉水瓶）
            results = model(cv_img)
            
            # 存储第一个矿泉水瓶的数据
            first_bottle = None
            
            # 遍历检测结果，找到第一个矿泉水瓶
            for r in results:
                for box in r.boxes:
                    class_id = int(box.cls[0])
                    class_name = model.names[class_id]
                    if class_id == WATER_BOTTLE_CLASS_ID or class_name.lower() == "bottle":
                        # 获取边界框坐标（x1,y1:左上角；x2,y2:右下角）
                        x1, y1, x2, y2 = map(float, box.xyxy[0])
                        # 计算中心点坐标
                        center_x = round((x1 + x2) / 2, 2)
                        center_y = round((y1 + y2) / 2, 2)
                        # 计算宽高
                        width = round(x2 - x1, 2)
                        height = round(y2 - y1, 2)
                        # 置信度
                        confidence = round(float(box.conf[0]), 2)
                        
                        # 构造第一个瓶子的数据（只取第一个）
                        first_bottle = {
                            "bbox": {  # 边界框坐标（左上角/右下角）
                                "x1": round(x1, 2),
                                "y1": round(y1, 2),
                                "x2": round(x2, 2),
                                "y2": round(y2, 2)
                            },
                            "center": {  # 中心点坐标
                                "x": center_x,
                                "y": center_y
                            },
                            "size": {  # 瓶子框的宽高
                                "width": width,
                                "height": height
                            },
                            "confidence": confidence  # 检测置信度
                        }
                        # 找到第一个后立即退出循环
                        break
                # 找到第一个后退出外层循环
                if first_bottle is not None:
                    break
            
            # 5. 保存检测结果图片（带标注框）
            result_filename = os.path.join(SAVE_DIR, "result.jpg")
            if len(results) > 0:
                results[0].save(result_filename)
                print(f"检测结果图片已保存：{result_filename}")
            
            # 6. 处理检测结果
            img_info = {"width": img.width, "height": img.height}
            
            if first_bottle is not None:
                print("\n检测到第一个矿泉水瓶，坐标信息：")
                print(f"  边界框（x1,y1,x2,y2）: {first_bottle['bbox']['x1']}, {first_bottle['bbox']['y1']}, {first_bottle['bbox']['x2']}, {first_bottle['bbox']['y2']}")
                print(f"  中心点（x,y）: {first_bottle['center']['x']}, {first_bottle['center']['y']}")
                print(f"  置信度: {first_bottle['confidence']}")
                
                # 保存到JSON文件
                save_visual_result(first_bottle, img_info)
                
                # 返回中心x坐标用于机械臂控制
                return True, first_bottle['center']['x'], first_bottle
            else:
                print("\n未检测到矿泉水瓶")
                # 保存空数据到JSON
                empty_data = {"status": "未检测到矿泉水瓶"}
                save_visual_result(empty_data, img_info)
                return False, None, None
        else:
            print("未获取到图像")
            return False, None, None

    except Exception as e:
        print(f"视觉识别出错：{e}")
        return False, None, None

    finally:
        # 确保相机关闭
        camera.close_camera()
        print("相机已关闭")


# ═══════════════════════════════════════════════════════════════
#  工具函数（机械臂模块）
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
            "position":    [target_pose["position"][0] - LIFT_OFFSET_X,
                            target_pose["position"][1],
                            target_pose["position"][2] + LIFT_OFFSET_Z],
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
#  主流程：视觉识别 + 机械臂抓取
# ═══════════════════════════════════════════════════════════════

def main():
    # 初始化GDK
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK 初始化失败")
        return
    print("GDK 初始化成功")
    
    # 第一步：视觉识别获取瓶子位置
    print("\n" + "=" * 55)
    print("第一步：视觉识别")
    print("=" * 55)
    
    success, vis_center_x, bottle_data = detect_bottle_with_yolo()
    
    if not success or vis_center_x is None:
        print("视觉识别失败，无法继续抓取流程")
        agibot_gdk.gdk_release()
        return
    
    print(f"\n视觉识别成功，瓶子中心x坐标: {vis_center_x} px")
    print("将使用此坐标进行机械臂抓取")
    
    # 第二步：机械臂抓取
    print("\n" + "=" * 55)
    print("第二步：机械臂抓取")
    print("=" * 55)
    
    # 创建机器人对象
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