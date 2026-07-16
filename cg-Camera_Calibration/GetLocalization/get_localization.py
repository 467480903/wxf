#!/usr/bin/env python3
"""
G2 机器人底盘定位修正脚本

流程：
  1. 调用 /data/wxf/wxf/yolo/cam_get_head_send.py，等待 /data/wxf/wxf/yolo/yolo_depth_result.json 更新
  2. 从 yolo_depth_result.json 读取 angle_deg, horizontal_offset_px
  3. 角度修正：|angle_deg| > 0.6 时，右转/左转 0.1rad，直到 |angle_deg| <= 0.6
  4. 横向修正：|horizontal_offset_px| > 30 时，向右/左移动 (horizontal_offset_px/1.86) mm，直到 |horizontal_offset_px| <= 30

通过 MQTT 向 /G2_minth_app 发布 go_rel 命令，订阅 /G2_minth_app_done 等待完成。
"""

import json
import os
import subprocess
import sys
import time
import threading

import paho.mqtt.client as mqtt

# ========== 路径配置 ==========
YOLO_DIR = "/data/wxf/wxf/yolo"
CAM_SCRIPT = os.path.join(YOLO_DIR, "cam_get_head_send.py")
RESULT_JSON = os.path.join(YOLO_DIR, "yolo_depth_result.json")

# ========== MQTT 配置 ==========
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_APP = "/G2_minth_app"
TOPIC_DONE = "/G2_minth_app_done"

# ========== 修正阈值 ==========
ANGLE_THRESHOLD = 1        # angle_deg 绝对值阈值
ROTATE_STEP_RAD = 0.1        # 每次旋转步长（rad）
OFFSET_THRESHOLD_PX = 30     # horizontal_offset_px 绝对值阈值
PX_TO_MM_COEFF = 0.5      # 像素到毫米换算系数
MAX_ITER = 20                # 单阶段最大迭代次数，防止死循环
# 把运动时间统一使用 MOVE_TIMEOUT 秒
MOVE_TIMEOUT = 3.0


# ========== MQTT 控制器 ==========
class MqttController:
    def __init__(self):
        self.client = mqtt.Client()
        self._done_event = threading.Event()
        self._connected = threading.Event()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(TOPIC_DONE, qos=0)
            self._connected.set()
        else:
            print(f"[MQTT] 连接失败，rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if payload.get("cmd") == "done":
                self._done_event.set()
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    def start(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        self.client.loop_start()
        if not self._connected.wait(timeout=5.0):
            print("[MQTT] 连接超时")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def go_rel(self, x=0.0, y=0.0, yaw_rad=0.0, timeout=30.0):
        """发布 go_rel 命令并等待 done"""
        self._done_event.clear()
        payload = {"cmd": "go_rel", "data": {"x": x, "y": y, "yaw_rad": yaw_rad}}
        self.client.publish(TOPIC_APP, json.dumps(payload), qos=0)
        ok = self._done_event.wait(timeout=timeout)
        if not ok:
            print(f"[MQTT] go_rel 超时: {payload}")
        return ok

    def arms(self, name, timeout=30.0):
        """发布 arms 命令，加载 datas/joints/arms/<name>.json"""
        self._done_event.clear()
        payload = {"cmd": "arms", "data": name}
        self.client.publish(TOPIC_APP, json.dumps(payload), qos=0)
        ok = self._done_event.wait(timeout=timeout)
        if not ok:
            print(f"[MQTT] arms 超时: {payload}")
        return ok

    def grab(self, left=0.5, right=0.5, timeout=30.0):
        """发布 grab 命令控制夹爪开合（0=夹紧, 1=张开，具体取决于硬件定义）"""
        self._done_event.clear()
        payload = {"cmd": "grab", "data": {"left": left, "right": right}}
        self.client.publish(TOPIC_APP, json.dumps(payload), qos=0)
        ok = self._done_event.wait(timeout=timeout)
        if not ok:
            print(f"[MQTT] grab 超时: {payload}")
        return ok

    def offset_move(self, lx=0.0, ly=0.0, lz=0.0, rx=0.0, ry=0.0, rz=0.0, timeout=30.0):
        """发布 offset_move 命令，末端执行器相对移动（单位：毫米）"""
        self._done_event.clear()
        payload = {"cmd": "offset_move",
                   "data": {"lx": lx, "ly": ly, "lz": lz, "rx": rx, "ry": ry, "rz": rz}}
        self.client.publish(TOPIC_APP, json.dumps(payload), qos=0)
        ok = self._done_event.wait(timeout=timeout)
        if not ok:
            print(f"[MQTT] offset_move 超时: {payload}")
        return ok


# ========== 调用相机检测 ==========
def call_detection():
    """调用 cam_get_head_send.py，等待结果更新后返回数据 dict"""
    # 记录旧修改时间，用于判断更新
    old_mtime = os.path.getmtime(RESULT_JSON) if os.path.exists(RESULT_JSON) else 0

    print("\n[检测] 调用 cam_get_head_send.py ...")
    try:
        subprocess.run(
            [sys.executable, CAM_SCRIPT, "7.14.pt"],
            cwd=YOLO_DIR,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print("[检测] cam_get_head_send.py 执行超时")
        return None

    # 等待结果文件更新
    for _ in range(30):
        try:
            new_mtime = os.path.getmtime(RESULT_JSON)
            if new_mtime > old_mtime:
                break
        except OSError:
            pass
        time.sleep(0.5)
    else:
        print("[检测] 结果文件未更新")
        return None

    # 读取结果
    try:
        with open(RESULT_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (OSError, json.JSONDecodeError) as e:
        print(f"[检测] 读取结果失败: {e}")
        return None


# ========== 抓取 ==========
_ctrl = None  # 由 main() 设置

def catch():
    '''
    1, 双手跑到 datas/joints/arms/befocatch.json 位置
    2, 双手跑到 datas/joints/arms/catch3.json 位置
    3, 双手夹紧
    '''
    print("[抓取] 1/3 移动到 befocatch 位置")
    _ctrl.arms("befocatch")
    time.sleep(MOVE_TIMEOUT)

    print("[抓取] 2/3 移动到 catch3 位置")
    _ctrl.arms("catch3")
    time.sleep(MOVE_TIMEOUT)

    print("[抓取] 3/3 双手夹紧")
    _ctrl.grab(left=0.0, right=0.0)
    time.sleep(0.5)
    print("[抓取] 完成")
    # 使用offset_move向z方向移动 0.1m
    print("[抓取] 抬升 0.1m")
    _ctrl.offset_move(lz=100.0, rz=100.0)
    time.sleep(MOVE_TIMEOUT)
    # 再向 -x 移动 0.25m
    print("[抓取] 后退 0.25m")
    _ctrl.offset_move(lx=-250.0, rx=-250.0)
    time.sleep(MOVE_TIMEOUT)



# ========== 底盘定位修正 ==========

def fix_angle(data):
    """角度修正：|angle_deg| > 阈值时右转/左转 0.1rad，直到收敛"""
    print("\n===== 角度修正 =====")
    for i in range(MAX_ITER):
        angle_deg = data.get("angle_deg")
        if angle_deg is None:
            print("[错误] 缺少 angle_deg 字段")
            return False, data

        if angle_deg > ANGLE_THRESHOLD:
            # 右转 0.1rad（yaw_rad 负=右转）
            print(f"[角度 {i+1}] angle_deg={angle_deg:.3f} > {ANGLE_THRESHOLD}，右转 {ROTATE_STEP_RAD}rad")
            _ctrl.go_rel(yaw_rad=-ROTATE_STEP_RAD)
            time.sleep(MOVE_TIMEOUT)  # 运动完成后等待5s再发下一条指令
            data = call_detection()
            if not data:
                return False, None
        elif angle_deg < -ANGLE_THRESHOLD:
            # 左转 0.1rad（yaw_rad 正=左转）
            print(f"[角度 {i+1}] angle_deg={angle_deg:.3f} < -{ANGLE_THRESHOLD}，左转 {ROTATE_STEP_RAD}rad")
            _ctrl.go_rel(yaw_rad=ROTATE_STEP_RAD)
            time.sleep(MOVE_TIMEOUT)
            data = call_detection()
            if not data:
                return False, None
        else:
            print(f"[角度] 已收敛，angle_deg={angle_deg:.3f} ∈ [-{ANGLE_THRESHOLD}, {ANGLE_THRESHOLD}]")
            return True, data
    else:
        print(f"[角度] 达到最大迭代次数 {MAX_ITER}")

    return True, data


def fix_horizontal_offset(data):
    """横向偏移修正：|offset_px| > 阈值时移动，直到收敛"""
    print("\n===== 横向偏移修正 =====")
    for i in range(MAX_ITER):
        offset_px = data.get("horizontal_offset_px")
        if offset_px is None:
            print("[错误] 缺少 horizontal_offset_px 字段")
            return False

        if abs(offset_px) <= OFFSET_THRESHOLD_PX:
            print(f"[横向] 已收敛，horizontal_offset_px={offset_px:.2f} "
                  f"∈ [-{OFFSET_THRESHOLD_PX}, {OFFSET_THRESHOLD_PX}]")
            return True

        # 统一公式：move_mm = offset_px / 1.86，向右为正
        # go_rel y 轴：正=左，负=右 → y = -move_mm/1000
        move_mm = offset_px / PX_TO_MM_COEFF
        y_meters = -move_mm / 1000.0
        direction = "右" if offset_px > 0 else "左"
        print(f"[横向 {i+1}] offset_px={offset_px:.2f}，向{direction}移动 {abs(move_mm):.2f}mm")

        _ctrl.go_rel(y=y_meters)
        time.sleep(MOVE_TIMEOUT)
        data = call_detection()
        if not data:
            print("[错误] 检测失败，终止")
            return False
    else:
        print(f"[横向] 达到最大迭代次数 {MAX_ITER}")

    return True


def localize():
    """底盘定位主流程：初始检测 → 角度修正 → 横向修正"""
    # ===== 初始检测 =====
    data = call_detection()
    if not data:
        print("[错误] 初始检测失败，退出")
        return False

    print(f"[初始] angle_deg={data.get('angle_deg')}, "
          f"horizontal_offset_px={data.get('horizontal_offset_px')}")

    # ===== 角度修正 =====
    ok, data = fix_angle(data)
    if not ok:
        return False

    # ===== 横向偏移修正 =====
    if not fix_horizontal_offset(data):
        return False

    print("\n[完成] 定位修正结束")
    return True


# ========== 主流程 ==========
def main():
    global _ctrl
    ctrl = MqttController()
    _ctrl = ctrl
    ctrl.start()
    time.sleep(0.5)

    try:
        # 底盘定位
        if not localize():
            print("[错误] 定位失败，终止")
            return
        catch()
    finally:
        ctrl.stop()


if __name__ == "__main__":
    main()
