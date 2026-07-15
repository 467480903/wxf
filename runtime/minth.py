#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minth 机器人控制类库

通过 MQTT 向 g2_minth_app_service 发送命令，并同步等待执行完成。

用法：
    from minth import Minth

    robot = Minth.G2()
    robot.GO(9)                 # 导航到地图点位 9
    robot.WBC("hold")           # 执行全身关节动作 hold.json
    robot.TTS("你好")           # 语音播报
    robot.REL({"x": 0.3})       # 底盘前进 0.3 米
    robot.OFFSET({"lx": 20})    # 左末端相对移动 20mm
    robot.GRIPPER({"left": 0.5, "right": 0.5})
    robot.YOLO("7.14.pt")       # YOLO 目标检测
    robot.YOLO("wxf.pt")        # 使用 wxf.pt 模型检测
    robot.close()

    # X2 型号（预留）
    # x2 = Minth.X2()
"""

import json
import threading

import paho.mqtt.client as mqtt


# ── MQTT 配置 ─────────────────────────────────────────────
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
CMD_TOPIC = "/G2_minth_app"
DONE_TOPIC = "/G2_minth_app_done"
CAMERA_TOPIC = "/minth/g2/camera"

# 默认超时时间（秒）
DEFAULT_TIMEOUT = 15


class _RobotBase:
    """机器人基类：封装 MQTT 通信和同步等待逻辑"""

    def __init__(self, broker=MQTT_BROKER, port=MQTT_PORT, timeout=DEFAULT_TIMEOUT, client_id=None):
        self.broker = broker
        self.port = port
        self.timeout = timeout
        self._done_event = threading.Event()
        self._connected = False
        cid = client_id or f"minth_{self.__class__.__name__}_{id(self)}"
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=cid,
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.connect(broker, port)
        self._client.loop_start()
        # 等待连接建立
        for _ in range(50):
            if self._connected:
                break
            threading.Event().wait(0.1)
        if not self._connected:
            raise ConnectionError(f"无法连接到 MQTT broker {broker}:{port}")

    # ── MQTT 回调 ──────────────────────────────────────────
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            client.subscribe(DONE_TOPIC, qos=2)
            self._connected = True
        else:
            raise ConnectionError(f"MQTT 连接失败，返回码: {rc}")

    def _on_message(self, client, userdata, msg):
        if msg.topic == DONE_TOPIC:
            self._done_event.set()

    # ── 核心：发送命令并等待完成 ────────────────────────────
    def _send_and_wait(self, cmd, data=None):
        """发送命令到 CMD_TOPIC，等待 DONE_TOPIC 回复或超时"""
        payload = {"cmd": cmd}
        if data is not None:
            payload["data"] = data

        self._done_event.clear()
        msg_str = json.dumps(payload, ensure_ascii=False)
        self._client.publish(CMD_TOPIC, msg_str, qos=2)
        print(f"[Minth] → {cmd}: {data}")

        done = self._done_event.wait(timeout=self.timeout)
        if done:
            print(f"[Minth] ✓ {cmd} 执行完成")
        else:
            print(f"[Minth] ✗ {cmd} 超时 ({self.timeout}s)")
        return done

    # ── 释放资源 ──────────────────────────────────────────
    def close(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None

    def __del__(self):
        self.close()


class G2(_RobotBase):
    """Minth G2 机器人控制类

    所有方法均为同步阻塞调用：发送 MQTT 命令后等待 /G2_minth_app_done 回复，
    收到后返回 True；15 秒超时返回 False。
    """

    def GO(self, num):
        """导航到指定地图点位
        Args:
            num: 导航点索引（整数），如 9
        Returns:
            bool: True=执行完成，False=超时
        """
        return self._send_and_wait("go", num)

    def WBC(self, name):
        """全身关节运动
        Args:
            name: 动作名称字符串，对应 datas/joints/WBC/{name}.json
                  例如 "hold"
        Returns:
            bool
        """
        return self._send_and_wait("WBC", name)

    def OFFSET(self, data):
        """末端执行器相对移动
        Args:
            data: dict，单位毫米，如 {"lx": 20, "ly": 0, "lz": 0,
                  "rx": 0, "ry": 0, "rz": 0}
        Returns:
            bool
        """
        return self._send_and_wait("offset_move", data)

    def REL(self, data):
        """底盘相对运动
        Args:
            data: dict，单位米，如 {"x": 0.3, "y": 0, "yaw_rad": 0}
                  x: 前进(+)/后退(-)
                  y: 左(+)/右(-)
                  yaw_rad: 左转(+)/右转(-)
        Returns:
            bool
        """
        return self._send_and_wait("go_rel", data)

    def TTS(self, text):
        """语音播报
        Args:
            text: 要播报的文本字符串
        Returns:
            bool
        """
        return self._send_and_wait("tts", text)

    def GRIPPER(self, data):
        """夹爪控制
        Args:
            data: dict，如 {"left": 0.5, "right": 0.5}
                  负值=张开，正值=闭合
        Returns:
            bool
        """
        return self._send_and_wait("grab", data)

    def YOLO(self, model="wxf.pt"):
        """YOLO 目标检测

        拍摄头部彩色+深度图，发送给 YOLO 服务进行检测，等待完成后返回。

        通过 MQTT 向 /minth/g2/camera 发送 {"cmd":"detect","yolo":"<model>"}，
        camera.py 执行完毕后会向 /G2_minth_app_done 发送 {"cmd":"done"}。

        Args:
            model: YOLO 模型文件名，如 "wxf.pt"、"7.14.pt"
        Returns:
            bool: True=检测完成，False=超时
        """
        payload = {"cmd": "detect", "yolo": model}
        self._done_event.clear()
        msg_str = json.dumps(payload, ensure_ascii=False)
        self._client.publish(CAMERA_TOPIC, msg_str, qos=2)
        print(f"[Minth] → YOLO: model={model}")

        # YOLO 检测耗时较长，使用较长超时
        done = self._done_event.wait(timeout=120)
        if done:
            print(f"[Minth] ✓ YOLO 检测完成")
        else:
            print(f"[Minth] ✗ YOLO 超时 (120s)")
        return done


class X2(_RobotBase):
    """Minth X2 机器人控制类（预留）

    后续实现时，在此添加 X2 专属方法。
    """
    pass


class Minth:
    """Minth 机器人命名空间

    用法：
        robot = Minth.G2()
        robot.GO(9)

        # X2（预留）
        # robot = Minth.X2()
    """
    G2 = G2
    X2 = X2
