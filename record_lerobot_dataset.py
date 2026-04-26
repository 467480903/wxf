#!/usr/bin/env python3
"""
Record AgiBot robot data into a LeRobot-style dataset layout.

This script captures:
- left/right arm joint positions from robot joint states
- RGB images from head, left-hand, and right-hand cameras

Output layout example:
<output_dir>/
  meta/
    info.json
    episodes.jsonl
    camera_intrinsics.json
  episodes/
    episode_000000/
      data.jsonl
      observation.images.head_color/
      observation.images.hand_left_color/
      observation.images.hand_right_color/
"""

import argparse
import json
import os
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import paho.mqtt.client as mqtt

import agibot_gdk
import time

# MQTT配置
MQTT_BROKER = "10.20.15.236"
MQTT_PORT = 1883
MQTT_TOPIC = "/record_lerobot_dataset"
MQTT_LOG_TOPIC = "/record_lerobot_dataset/log"

# 录制状态
is_recording = False
record_thread = None
record_args = None

# 日志配置
log_enabled = True  # 默认开启日志
log_client = None   # MQTT日志客户端

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

def log_message(message):
    """输出日志，同时发送到MQTT和控制台"""
    if log_enabled:
        # 输出到控制台
        print(message)
        # 发送到MQTT
        if log_client and log_client.is_connected():
            try:
                log_client.publish(MQTT_LOG_TOPIC, message, qos=0)
            except Exception as e:
                print(f"Error publishing log to MQTT: {e}")


@dataclass(frozen=True)
class CameraSpec:
    key: str
    camera_type: int
    folder: str

CAMERAS: List[CameraSpec] = [
    CameraSpec(
        key="head_color",
        camera_type=agibot_gdk.CameraType.kHeadColor,
        folder="observation.images.head_color",
    ),
    CameraSpec(
        key="hand_right_color",
        camera_type=agibot_gdk.CameraType.kHandRightColor,
        folder="observation.images.hand_right_color",
    ),
]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record right arm + head/hand camera data to LeRobot-style format."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("lerobot_dataset"),
        help="Dataset root directory.",
    )
    parser.add_argument(
        "--episode-id",
        type=int,
        default=0,
        help="Episode index (used as episode_XXXXXX).",
    )
    parser.add_argument("--seconds", type=float, default=10.0, help="Recording duration.")
    parser.add_argument("--fps", type=float, default=10.0, help="Sampling rate.")
    parser.add_argument(
        "--robot-type",
        type=str,
        default="agibot",
        help="Robot type metadata for info.json.",
    )
    return parser.parse_args()


def get_next_episode_id(output_dir: Path) -> int:
    """
    从episodes.jsonl文件中读取最大的episode_index，返回下一个可用的索引。
    如果文件不存在或为空，返回0。
    """
    episodes_file = output_dir / "meta" / "episodes.jsonl"
    max_index = -1
    
    if episodes_file.exists():
        try:
            with episodes_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        episode = json.loads(line)
                        if "episode_index" in episode:
                            current_index = episode["episode_index"]
                            if current_index > max_index:
                                max_index = current_index
                    except json.JSONDecodeError:
                        log_message(f"警告: 无法解析episodes.jsonl中的行: {line}")
        except Exception as e:
            log_message(f"警告: 读取episodes.jsonl文件失败: {e}")
    
    return max_index + 1


def ensure_dirs(output_dir: Path, episode_id: int) -> Tuple[Path, Path]:
    meta_dir = output_dir / "meta"
    episode_dir = output_dir / "episodes" / f"episode_{episode_id:06d}"
    meta_dir.mkdir(parents=True, exist_ok=True)
    episode_dir.mkdir(parents=True, exist_ok=True)
    for cam in CAMERAS:
        (episode_dir / cam.folder).mkdir(parents=True, exist_ok=True)
    return meta_dir, episode_dir


def extract_arm_positions(joint_states: Dict, arm_prefix: str) -> Dict[str, float]:
    """
    Extract ordered joint positions for one arm from get_joint_states() result.
    arm_prefix examples: 'arm_l', 'arm_r'
    For right arm, extracts exactly joints 1-7 in order using the format from positions_plastic_box_pick_down.json.
    """
    positions: Dict[str, float] = {}
    
    # 从positions_plastic_box_pick_down.json获取的精确关节命名格式
    expected_joint_names = [
        "idx61_arm_r_joint1",  # 右臂关节1
        "idx62_arm_r_joint2",  # 右臂关节2
        "idx63_arm_r_joint3",  # 右臂关节3
        "idx64_arm_r_joint4",  # 右臂关节4
        "idx65_arm_r_joint5",  # 右臂关节5
        "idx66_arm_r_joint6",  # 右臂关节6
        "idx67_arm_r_joint7"   # 右臂关节7
    ]
    
    # 只处理右臂
    if arm_prefix != "arm_r":
        log_message(f"警告: 当前只支持右臂关节采集，请求的是{arm_prefix}")
        return positions
    
    all_joints = joint_states.get("states", [])
    
    # 将所有关节状态转换为字典，便于查找
    joint_dict = {state.get("name", ""): float(state.get("position", 0.0)) for state in all_joints}
    
    # 按照预期顺序提取关节值
    for joint_name in expected_joint_names:
        if joint_name in joint_dict:
            positions[joint_name] = joint_dict[joint_name]
            log_message(f"成功获取关节: {joint_name}, 值: {joint_dict[joint_name]:.3f}")
        else:
            log_message(f"警告: 未找到关节: {joint_name}")
            # 为缺失的关节设置默认值
            positions[joint_name] = 0.0
    
    return positions


def write_camera_intrinsics(meta_dir: Path, camera: agibot_gdk.Camera) -> None:
    intrinsics: Dict[str, Dict] = {}
    for cam in CAMERAS:
        try:
            intrinsic = camera.get_camera_intrinsic(cam.camera_type)
            intrinsics[cam.key] = {
                "fx": float(intrinsic.intrinsic[0]),
                "fy": float(intrinsic.intrinsic[1]),
                "cx": float(intrinsic.intrinsic[2]),
                "cy": float(intrinsic.intrinsic[3]),
                "distortion": [float(v) for v in intrinsic.distortion],
            }
        except Exception as exc:  # pylint: disable=broad-except
            intrinsics[cam.key] = {"error": str(exc)}

    with (meta_dir / "camera_intrinsics.json").open("w", encoding="utf-8") as f:
        json.dump(intrinsics, f, ensure_ascii=False, indent=2)


def capture_images(
    camera: agibot_gdk.Camera,
    episode_dir: Path,
    frame_idx: int,
    timeout_ms: float = 2000.0,  # 增加超时时间
) -> Tuple[Dict[str, Optional[str]], Dict[str, Optional[Tuple[int, int]]]]:
    paths: Dict[str, Optional[str]] = {}
    sizes: Dict[str, Optional[Tuple[int, int]]] = {}
    
    for cam in CAMERAS:
        rel_path = f"{cam.folder}/{frame_idx:06d}.jpg"
        abs_path = episode_dir / rel_path
        
        try:
            # 确保目录存在
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 获取图片
            log_message(f"正在获取{cam.key}相机的图片...")
            img = camera.get_latest_image(cam.camera_type, timeout_ms)
            
            if img is None:
                log_message(f"警告: {cam.key}相机获取图片失败，返回None")
                paths[cam.key] = None
                sizes[cam.key] = None
                continue
            
            # 检查图片数据
            if not hasattr(img, 'data') or img.data is None or len(img.data) == 0:
                log_message(f"警告: {cam.key}相机图片数据为空")
                paths[cam.key] = None
                sizes[cam.key] = None
                continue
            
            # 保存图片
            log_message(f"正在保存{cam.key}图片到: {abs_path}")
            with abs_path.open("wb") as f:
                f.write(img.data)
            
            # 检查文件大小
            file_size = abs_path.stat().st_size
            if file_size == 0:
                log_message(f"警告: {cam.key}图片保存失败，文件大小为0字节")
                paths[cam.key] = None
                sizes[cam.key] = None
                abs_path.unlink()  # 删除空文件
                continue
            
            # 记录成功信息
            paths[cam.key] = rel_path
            sizes[cam.key] = (int(img.height), int(img.width))
            log_message(f"成功保存{cam.key}图片: {rel_path}, 尺寸: {img.width}x{img.height}, 大小: {file_size}字节")
            
        except Exception as e:
            log_message(f"错误: 处理{cam.key}相机时发生异常: {e}")
            paths[cam.key] = None
            sizes[cam.key] = None
            # 清理可能的空文件
            if abs_path.exists() and abs_path.stat().st_size == 0:
                abs_path.unlink()
    
    return paths, sizes


def write_info_json(
    meta_dir: Path,
    fps: float,
    robot_type: str,
    right_dim: int,
    image_sizes: Dict[str, Optional[Tuple[int, int]]],
) -> None:
    features = {
        "observation.state.arm_right": {"dtype": "float32", "shape": [right_dim]},
        "observation.state.right_tool": {"dtype": "float32", "shape": [1]},  # 夹爪位置 (弧度)
    }
    for cam in CAMERAS:
        size = image_sizes.get(cam.key)
        if size is None:
            features[f"observation.images.{cam.key}"] = {"dtype": "image", "shape": None}
        else:
            h, w = size
            features[f"observation.images.{cam.key}"] = {
                "dtype": "image",
                "shape": [h, w, 3],
            }

    info = {
        "codebase_version": "v2.0",
        "robot_type": robot_type,
        "fps": fps,
        "features": features,
    }
    with (meta_dir / "info.json").open("w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)


def append_episode_index(
    meta_dir: Path,
    episode_id: int,
    length: int,
    duration_s: float,
    episode_rel_path: str,
) -> None:
    row = {
        "episode_index": episode_id,
        "length": length,
        "duration_s": duration_s,
        "data_path": f"{episode_rel_path}/data.jsonl",
    }
    with (meta_dir / "episodes.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def record_thread_function(args):
    """录制线程函数，执行实际的录制逻辑"""
    global is_recording
    output_dir = args.output_dir.resolve()
    meta_dir, episode_dir = ensure_dirs(output_dir, args.episode_id)

    if args.fps <= 0:
        log_message("Error: --fps must be > 0")
        is_recording = False
        return

    robot = agibot_gdk.Robot()
    camera = agibot_gdk.Camera()
    time.sleep(2.0)  # allow robot/camera streams to stabilize

    data_rows: List[Dict] = []
    first_image_sizes: Dict[str, Optional[Tuple[int, int]]] = {cam.key: None for cam in CAMERAS}
    dt = 1.0 / args.fps
    t0 = time.monotonic()
    frame_idx = 0
    last_log_second = -1

    try:
        write_camera_intrinsics(meta_dir, camera)
        log_message(f"开始录制 episode {args.episode_id:06d}, fps={args.fps}")

        while is_recording:
            step_start = time.monotonic()
            timestamp_ns = time.time_ns()
            
            # 计算当前录制秒数
            current_second = int(time.monotonic() - t0)
            
            # 每秒输出一次录制时长日志
            if current_second > last_log_second:
                log_message(f"录制中: {current_second} 秒，已录制 {frame_idx} 帧")
                last_log_second = current_second

            joint_states = robot.get_joint_states()
            right_joints = extract_arm_positions(joint_states, "arm_r")
            image_paths, image_sizes = capture_images(camera, episode_dir, frame_idx)

            for key, size in image_sizes.items():
                if first_image_sizes[key] is None and size is not None:
                    first_image_sizes[key] = size

            # 获取末端执行器状态 - 只记录position
            right_tool_position = 0.0
            
            try:
                end_state = robot.get_end_state()
                if "right_end_state" in end_state:
                    right_end = end_state["right_end_state"]
                    if right_end.get("end_states"):
                        # 取第一个关节作为夹爪状态（omnipicker通常只有一个关节）
                        joint_state = right_end["end_states"][0]
                        right_tool_position = float(joint_state.get("position", 0.0))
            except Exception as e:
                log_message(f"获取末端执行器状态失败: {e}")
            
            row = {
                "episode_index": args.episode_id,
                "frame_index": frame_idx,
                "timestamp_ns": timestamp_ns,
                "observation.state.arm_right": list(right_joints.values()),
                "observation.state.right_tool": [right_tool_position],
                "observation.images.head_color": image_paths["head_color"],
                "observation.images.hand_right_color": image_paths["hand_right_color"],
                "done": False,  # 持续录制，直到收到stop命令
            }
            data_rows.append(row)
            frame_idx += 1

            elapsed = time.monotonic() - step_start
            sleep_time = max(0.0, dt - elapsed)
            time.sleep(sleep_time)

        # 录制结束，更新最后一帧的done标志
        if data_rows:
            data_rows[-1]["done"] = True
            total_duration = time.monotonic() - t0

            with (episode_dir / "data.jsonl").open("w", encoding="utf-8") as f:
                for row in data_rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

            right_dim = len(data_rows[0]["observation.state.arm_right"]) if data_rows else 0
            write_info_json(
                meta_dir=meta_dir,
                fps=args.fps,
                robot_type=args.robot_type,
                right_dim=right_dim,
                image_sizes=first_image_sizes,
            )
            append_episode_index(
                meta_dir=meta_dir,
                episode_id=args.episode_id,
                length=len(data_rows),
                duration_s=total_duration,
                episode_rel_path=f"episodes/episode_{args.episode_id:06d}",
            )

            log_message(f"录制完成! 总时长: {total_duration:.2f} 秒, 总帧数: {len(data_rows)}")
            log_message(f"数据保存到: {episode_dir}")
            log_message(f"元数据保存到: {meta_dir}")

    finally:
        camera.close_camera()
        log_message("录制已停止")


def on_connect(client, userdata, flags, rc):
    """MQTT连接成功回调"""
    global log_client
    if rc == 0:
        log_message(f"已连接到MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC, qos=1)
        log_message(f"已订阅主题: {MQTT_TOPIC}")
        # 设置日志客户端
        log_client = client
    else:
        log_message(f"连接MQTT broker失败，错误码: {rc}")


def on_disconnect(client, userdata, rc):
    """MQTT断开连接回调"""
    global log_client
    log_message(f"与MQTT broker断开连接，错误码: {rc}")
    log_client = None


def on_message(client, userdata, msg):
    """MQTT消息接收回调"""
    global is_recording, record_thread, record_args, log_enabled
    
    log_message(f"收到消息: 主题={msg.topic}, 内容={msg.payload.decode()}")
    
    try:
        payload = json.loads(msg.payload.decode())
        cmd = payload.get("cmd")
        
        if cmd == "start":
            if is_recording:
                log_message("已经在录制中，请先停止")
                return
                
            log_message("开始录制...")
            is_recording = True
            
            # 获取输出目录
            output_dir = Path(payload.get("output_dir", "lerobot_dataset"))
            
            # 确定episode_id
            episode_id = payload.get("episode_id")
            if episode_id is None:
                # 如果没有指定episode_id，自动计算下一个可用索引
                episode_id = get_next_episode_id(output_dir)
                log_message(f"自动分配episode_id: {episode_id}")
            else:
                # 确保episode_id是整数
                try:
                    episode_id = int(episode_id)
                except ValueError:
                    log_message(f"无效的episode_id: {episode_id}，自动分配索引")
                    episode_id = get_next_episode_id(output_dir)
            
            # 使用默认参数或从payload中获取参数
            record_args = argparse.Namespace(
                output_dir=output_dir,
                episode_id=episode_id,
                seconds=payload.get("seconds", 10.0),  # 这个参数现在不再用于控制录制时长
                fps=payload.get("fps", 10.0),
                robot_type=payload.get("robot_type", "agibot")
            )
            
            # 启动录制线程
            record_thread = threading.Thread(target=record_thread_function, args=(record_args,))
            record_thread.daemon = True
            record_thread.start()
            
        elif cmd == "stop":
            if not is_recording:
                log_message("没有在录制中，无法停止")
                return
                
            log_message("停止录制...")
            is_recording = False
            
            # 等待录制线程结束
            if record_thread:
                record_thread.join()
                record_thread = None
                
        elif cmd == "enable_log":
            log_enabled = True
            log_message("日志已开启")
            
        elif cmd == "disable_log":
            log_enabled = False
            # 直接输出一条关闭日志的信息
            print("日志已关闭")
            # 同时发送到MQTT
            try:
                client.publish(MQTT_LOG_TOPIC, "日志已关闭", qos=0)
            except Exception as e:
                print(f"发送日志关闭消息失败: {e}")
                
        else:
            log_message(f"未知命令: {cmd}")
            
    except json.JSONDecodeError:
        log_message("收到无效的JSON格式消息")
    except Exception as e:
        log_message(f"处理消息时发生错误: {e}")


def main() -> None:
    """主函数，初始化MQTT客户端并保持运行"""
    # 创建MQTT客户端
    client = mqtt.Client(client_id="record_lerobot_dataset_server", clean_session=True)
    
    # 设置回调函数
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    try:
        # 连接到MQTT broker
        log_message(f"正在连接到MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        
        # 启动MQTT消息循环
        log_message("启动MQTT消息循环...")
        log_message(f"正在监听主题: {MQTT_TOPIC} 上的命令")
        client.loop_forever()
        
    except KeyboardInterrupt:
        log_message("\n服务被用户停止")
        # 停止录制（如果正在进行）
        global is_recording
        if is_recording:
            is_recording = False
            if record_thread:
                record_thread.join()
    except Exception as e:
        log_message(f"错误: {e}")
    finally:
        # 释放资源
        if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
            log_message("警告: GDK资源释放失败")
        client.disconnect()
        log_message("已与MQTT broker断开连接")


if __name__ == "__main__":
    main()
