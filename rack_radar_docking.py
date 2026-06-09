#!/usr/bin/env python3
"""
G2 料架前方雷达靠近控制类。

这个文件只封装已经实机验证稳定的一条链路：
  request_chassis_control(mode=0) + move_chassis(Twist) + 前方雷达 300mm 停车

使用前必须在机器人端加载 GDK 环境：
  source /home/agi/app/env.sh

典型调用方式：
  from rack_radar_docking import RackRadarDockingController

  with RackRadarDockingController(front_ids=(0, 1, 2, 3)) as dock:
      result = dock.approach_until_distance(
          stop_mm=300,
          speed_mps=0.05,
          max_duration_s=80,
          allow_estop_pedal_fault=True,
      )
      print(result)
"""

from dataclasses import dataclass
import statistics
import time

import agibot_gdk


INVALID_DISTANCE_MM = 65535


@dataclass(frozen=True)
class RadarSample:
    """一次雷达采样，用于 on_sample 回调实时打印/记录。"""

    # 本次靠近启动后的时间，单位秒。
    elapsed_s: float
    # 当前一帧里 front_ids 中的最小有效距离，单位 mm。
    min_mm: int
    # 最近 history_size 个 min_mm 的中位数，真正用于停车判断。
    filtered_mm: int
    # 本次有效雷达原始读数，例如 ((0, 285), (1, 523))。
    distances: tuple


@dataclass(frozen=True)
class DockingResult:
    """一次靠近动作的最终结果。"""

    # stopped/already_at_threshold/timeout/lost_radar 之一。
    status: str
    # 动作持续时间，单位秒。
    elapsed_s: float
    # 结束时最后一帧最小距离，单位 mm；丢雷达时为 None。
    min_mm: int | None
    # 结束时最后一次滤波距离，单位 mm；丢雷达时为 None。
    filtered_mm: int | None
    # 结束时最后一帧有效雷达原始读数。
    distances: tuple
    # 本次动作累计处理了多少帧有效雷达数据。
    samples: int


class RackRadarDockingController:
    """
    低速靠近料架，并在前方雷达达到阈值时自动停车。

    这台 G2 上已经验证过的控制约定：
      - 前方雷达 ID：0, 1, 2, 3
      - 底盘控制模式：mode=0
      - Twist.linear.x 为正时，机器人朝当前车头方向前进
      - 当前料架靠近任务使用 stop_mm=300
      - speed_mps=0.05 已实机验证，能稳定停在约 300mm 附近
    """

    def __init__(
        self,
        front_ids=(0, 1, 2, 3),
        min_valid_mm=50,
        control_mode=0,
        init_gdk=True,
        init_wait_s=0.5,
    ):
        """
        创建控制器并初始化 GDK 对象。

        front_ids:
            面向料架的前方雷达 ID。现场已确认前方是 0,1,2,3。
        min_valid_mm:
            小于这个值的距离认为无效，避免异常近距离噪声。
        control_mode:
            传给 pnc.request_chassis_control() 的底盘模式。官方 move_chassis
            demo 默认用 0，现场验证 mode=0 才是这套前进靠近链路。
        init_gdk:
            True 表示类内部调用 agibot_gdk.gdk_init()/gdk_release()。
            如果你的主程序已经统一初始化 GDK，可以传 False。
        init_wait_s:
            初始化后等待 DDS/GDK 连接稳定的时间。
        """
        if not front_ids:
            raise ValueError("front_ids must not be empty")

        self.front_ids = tuple(front_ids)
        self.min_valid_mm = min_valid_mm
        self.control_mode = control_mode
        self._init_gdk = init_gdk
        self._closed = False

        if init_gdk:
            result = agibot_gdk.gdk_init()
            gdk_res = getattr(agibot_gdk, "GDKRes", None)
            if gdk_res is not None and result not in (None, gdk_res.kSuccess):
                raise RuntimeError(f"GDK init failed: {result}")

        self.radar = agibot_gdk.UltrasonicRadar()
        self.robot = agibot_gdk.Robot()
        self.pnc = agibot_gdk.Pnc()
        time.sleep(init_wait_s)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self):
        """释放资源。会先发零速度，再取消占用底盘的远控任务。"""
        if self._closed:
            return
        try:
            self.stop()
        except Exception:
            pass
        time.sleep(0.1)
        try:
            self.cancel_blocking_task()
        except Exception:
            pass
        try:
            self.radar.close_ultrasonic_radar()
        except Exception:
            pass
        if self._init_gdk:
            try:
                agibot_gdk.gdk_release()
            except Exception:
                pass
        self._closed = True

    def check_motion_safety(self, allow_estop_pedal_fault=False):
        """
        检查靠近前的底盘安全状态。

        返回 (problems, warnings)：
          - problems 非空时拒绝运动
          - warnings 只是提示，例如这台机器的已知急停踏板硬件故障
        """
        problems = []
        warnings = []
        power = self.robot.get_chassis_power_state()
        motion = self.robot.get_motion_control_status()

        if getattr(motion, "error_code", 0) != 0:
            problems.append(f"motion_control_error={motion.error_code}")
        if getattr(power, "charge_plug_insert_state", 0) != 0:
            problems.append("charge_plug_insert_state=1")
        if getattr(power, "emergency_stop_pedal_fault_state", 0) != 0:
            if allow_estop_pedal_fault:
                warnings.append("emergency_stop_pedal_fault_state=1 allowed")
            else:
                problems.append("emergency_stop_pedal_fault_state=1")
        if getattr(power, "chassis_ultrasonic_radar_power_state", 0) != 1:
            problems.append("chassis_ultrasonic_radar_power_state!=1")

        return problems, warnings

    def selected_distances(self):
        """读取 front_ids 中所有有效雷达距离，返回 ((id, distance_mm), ...)。"""
        data = self.radar.get_latest_ultrasonic_radar()
        distances = []
        for row in data.get("ultrasonic_radar_datas", []):
            radar_id = row.get("id")
            distance_mm = row.get("distance_mm")
            fault_state = row.get("fault_state")
            if radar_id not in self.front_ids:
                continue
            if fault_state != 0:
                continue
            if self.min_valid_mm <= distance_mm < INVALID_DISTANCE_MM:
                distances.append((radar_id, distance_mm))
        return tuple(distances)

    def read_min_distance(self):
        """读取前方最小有效距离，返回 (min_mm, distances)。"""
        distances = self.selected_distances()
        if not distances:
            return None, distances
        return min(distance for _, distance in distances), distances

    def cancel_blocking_task(self):
        """取消 PNC 中未结束的旧任务，释放底盘控制权。"""
        task = self.pnc.get_task_state()
        if task.state not in (0, 3, 7, 9):
            self.pnc.cancel_task(task.id)
            time.sleep(0.3)

    def request_chassis_control_ready(self):
        """先清旧任务，再请求底盘远控；如果第一次失败，会清理后重试一次。"""
        self.cancel_blocking_task()
        try:
            return self.pnc.request_chassis_control(self.control_mode)
        except RuntimeError:
            self.cancel_blocking_task()
            time.sleep(0.5)
            return self.pnc.request_chassis_control(self.control_mode)

    def send_velocity(self, speed_mps):
        """
        发送底盘速度。

        speed_mps > 0：向当前车头方向前进，也就是靠近前方料架。
        speed_mps = 0：停车。
        这个类不发送 lateral/rotation，避免靠近料架时产生横移或转向。
        """
        twist = agibot_gdk.Twist()
        twist.linear = agibot_gdk.Vector3()
        twist.angular = agibot_gdk.Vector3()
        twist.linear.x = speed_mps
        twist.linear.y = 0.0
        twist.linear.z = 0.0
        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = 0.0
        self.pnc.move_chassis(twist)

    def stop(self):
        """发送零速度停车。"""
        self.send_velocity(0.0)

    def approach_until_distance(
        self,
        stop_mm=300,
        speed_mps=0.02,
        max_duration_s=70.0,
        hz=10.0,
        history_size=3,
        lost_radar_timeout_s=1.0,
        allow_estop_pedal_fault=False,
        on_sample=None,
    ):
        """
        核心调用方法：向前靠近，直到前方雷达滤波距离 <= stop_mm。

        参数说明：
          stop_mm:
              停车阈值，单位 mm。料架前 0.3m 停车就填 300。
          speed_mps:
              前进速度，单位 m/s。现场验证：
                0.02 比较慢，适合第一次调试；
                0.05 是已经验证过的正常速度。
          max_duration_s:
              最长运行时间。到时间还没到 stop_mm，会停车并返回 timeout。
          hz:
              控制和雷达检查频率。10Hz 已实机验证稳定。
          history_size:
              中位数滤波窗口。3 表示最近 3 个 min_mm 取中位数判断停车，
              可以抑制单帧雷达跳变。
          lost_radar_timeout_s:
              如果运行中某一帧没有有效前方雷达，类会立即发零速度等待恢复；
              持续超过这个时间仍没有雷达，返回 lost_radar。
          allow_estop_pedal_fault:
              这台 G2 的 emergency_stop_pedal_fault_state=1 是官方确认的
              已知硬件问题。现场有人看护并确认可运行时填 True。
          on_sample:
              可选回调函数。每次有有效雷达数据时会调用 on_sample(sample)，
              适合打印日志或写文件。

        返回 DockingResult：
          status="stopped":
              达到 stop_mm，已自动停车。
          status="already_at_threshold":
              启动时已经在阈值内，没有前进。
          status="timeout":
              到 max_duration_s 还没到阈值，已停车。
          status="lost_radar":
              连续丢失前方有效雷达超过 lost_radar_timeout_s，已停车。
        """
        if speed_mps <= 0.0:
            raise ValueError("speed_mps must be positive for front-rack approach")
        if stop_mm < self.min_valid_mm:
            raise ValueError("stop_mm must be >= min_valid_mm")
        if hz <= 0.0:
            raise ValueError("hz must be positive")
        if history_size <= 0:
            raise ValueError("history_size must be positive")
        if lost_radar_timeout_s < 0.0:
            raise ValueError("lost_radar_timeout_s must be >= 0")

        problems, warnings = self.check_motion_safety(
            allow_estop_pedal_fault=allow_estop_pedal_fault
        )
        if problems:
            raise RuntimeError("Refusing to move: " + ", ".join(problems))
        for warning in warnings:
            print("WARNING:", warning)

        min_mm, distances = self.read_min_distance()
        if min_mm is None:
            raise RuntimeError(f"No valid front radar distances for {self.front_ids}")
        if min_mm <= stop_mm:
            return DockingResult(
                status="already_at_threshold",
                elapsed_s=0.0,
                min_mm=min_mm,
                filtered_mm=min_mm,
                distances=distances,
                samples=1,
            )

        self.request_chassis_control_ready()
        time.sleep(0.3)

        interval_s = 1.0 / hz
        history = []
        samples = 0
        start = time.time()
        latest_min_mm = min_mm
        latest_filtered_mm = min_mm
        latest_distances = distances
        lost_radar_since = None

        try:
            while time.time() - start < max_duration_s:
                min_mm, distances = self.read_min_distance()
                elapsed_s = time.time() - start
                if min_mm is None:
                    self.stop()
                    if lost_radar_since is None:
                        lost_radar_since = elapsed_s
                    if elapsed_s - lost_radar_since >= lost_radar_timeout_s:
                        return DockingResult(
                            status="lost_radar",
                            elapsed_s=elapsed_s,
                            min_mm=None,
                            filtered_mm=None,
                            distances=distances,
                            samples=samples,
                        )
                    time.sleep(interval_s)
                    continue
                lost_radar_since = None

                history.append(min_mm)
                history = history[-history_size:]
                filtered_mm = int(statistics.median(history))
                samples += 1

                latest_min_mm = min_mm
                latest_filtered_mm = filtered_mm
                latest_distances = distances

                sample = RadarSample(
                    elapsed_s=elapsed_s,
                    min_mm=min_mm,
                    filtered_mm=filtered_mm,
                    distances=distances,
                )
                if on_sample is not None:
                    on_sample(sample)

                if len(history) >= history_size and filtered_mm <= stop_mm:
                    self.stop()
                    return DockingResult(
                        status="stopped",
                        elapsed_s=elapsed_s,
                        min_mm=min_mm,
                        filtered_mm=filtered_mm,
                        distances=distances,
                        samples=samples,
                    )

                self.send_velocity(speed_mps)
                time.sleep(interval_s)

            self.stop()
            return DockingResult(
                status="timeout",
                elapsed_s=time.time() - start,
                min_mm=latest_min_mm,
                filtered_mm=latest_filtered_mm,
                distances=latest_distances,
                samples=samples,
            )
        finally:
            try:
                self.stop()
            except Exception:
                pass
            time.sleep(0.1)
            try:
                self.cancel_blocking_task()
            except Exception:
                pass
