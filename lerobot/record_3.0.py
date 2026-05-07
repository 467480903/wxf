#!/usr/bin/env python3
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
import numpy as np
import cv2

# --- 配置区 ---
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
MQTT_TOPIC = "/record_lerobot_dataset"
MQTT_LOG_TOPIC = "/record_lerobot_dataset/log"

# --- 全局状态 ---
is_recording = False
record_thread = None
log_enabled = True
log_client = None

@dataclass(frozen=True)
class CameraSpec:
    key: str
    camera_type: int
    video_name: str 

CAMERAS: List[CameraSpec] = [
    CameraSpec(
        key="head_color", 
        camera_type=agibot_gdk.CameraType.kHeadColor, 
        video_name="observation.images.head_color"
    ),
    CameraSpec(
        key="hand_right_color", 
        camera_type=agibot_gdk.CameraType.kHandRightColor, 
        video_name="observation.images.hand_right_color"
    ),
]

def log_message(message):
    """输出日志并发送至 MQTT"""
    if log_enabled:
        print(message)
        if log_client and log_client.is_connected():
            try:
                log_client.publish(MQTT_LOG_TOPIC, message, qos=0)
            except:
                pass

def get_next_episode_id(output_dir: Path) -> int:
    episodes_file = output_dir / "meta" / "episodes.jsonl"
    max_index = -1
    if episodes_file.exists():
        with episodes_file.open("r") as f:
            for line in f:
                try:
                    episode = json.loads(line)
                    max_index = max(max_index, episode.get("episode_index", -1))
                except: continue
    return max_index + 1

def ensure_dirs_v3(output_dir: Path, episode_id: int) -> Tuple[Path, Path, Path]:
    meta_dir = output_dir / "meta"
    episode_dir = output_dir / "episodes" / f"episode_{episode_id:06d}"
    video_dir = output_dir / "videos"
    meta_dir.mkdir(parents=True, exist_ok=True)
    episode_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir, episode_dir, video_dir

def write_info_json_v3(meta_dir: Path, fps: float, robot_type: str, state_dim: int, joint_names: List[str]):
    features = {
        "observation.state": {"dtype": "float32", "shape": [state_dim], "names": joint_names},
        "action": {"dtype": "float32", "shape": [state_dim], "names": joint_names}
    }
    for cam in CAMERAS:
        features[cam.video_name] = {
            "dtype": "video",
            "shape": [3, 480, 640],
            "video_codec": "mp4v",
            "fps": fps,
            "video_path": f"videos/{cam.key}_episode_{{episode_index:06d}}.mp4"
        }
    info = {"codebase_version": "3.0", "robot_type": robot_type, "fps": fps, "features": features}
    with (meta_dir / "info.json").open("w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

def record_thread_function(args):
    global is_recording
    meta_dir, episode_dir, video_dir = ensure_dirs_v3(args.output_dir, args.episode_id)
    
    robot = agibot_gdk.Robot()
    camera = agibot_gdk.Camera()
    time.sleep(2.0)

    video_writers = {}
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    for cam in CAMERAS:
        v_path = video_dir / f"{cam.key}_episode_{args.episode_id:06d}.mp4"
        video_writers[cam.key] = cv2.VideoWriter(str(v_path), fourcc, args.fps, (640, 480))

    data_rows = []
    dt = 1.0 / args.fps
    t0 = time.monotonic()
    frame_idx = 0
    joint_names = [
        "idx61_arm_r_joint1", "idx62_arm_r_joint2", "idx63_arm_r_joint3",
        "idx64_arm_r_joint4", "idx65_arm_r_joint5", "idx66_arm_r_joint6", "idx67_arm_r_joint7"
    ]

    log_message(f"开始录制 Episode {args.episode_id}...")

    try:
        while is_recording:
            step_start = time.monotonic()
            
            # 1. 状态采集
            js = robot.get_joint_states()
            # 增加安全检查：确保 js 不是 None 且包含 states
            if js and "states" in js:
                states_map = {s['name']: s['position'] for s in js.get("states", [])}
                current_state = [states_map.get(name, 0.0) for name in joint_names]
            else:
                current_state = [0.0] * len(joint_names)

            # 2. 视频采集
            for cam in CAMERAS:
                img = camera.get_latest_image(cam.camera_type, 1000)
                
                # --- 修复点：修改判断逻辑，避免直接判断 numpy 数组的真值 ---
                if img is not None and hasattr(img, 'data') and img.data is not None:
                    # 检查 data 是否为空（字节长度）
                    if len(img.data) > 0:
                        nparr = np.frombuffer(img.data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            # 确保尺寸一致
                            if (frame.shape[1], frame.shape[0]) != (640, 480):
                                frame = cv2.resize(frame, (640, 480))
                            video_writers[cam.key].write(frame)
                        else:
                            log_message(f"警告: {cam.key} 解码失败")
                else:
                    log_message(f"警告: 无法获取 {cam.key} 图像数据")

            # 3. 数据记录
            data_rows.append({
                "observation.state": current_state,
                "episode_index": args.episode_id,
                "frame_index": frame_idx,
                "timestamp_ns": time.time_ns(),
                "done": False
            })

            frame_idx += 1
            elapsed = time.monotonic() - step_start
            time.sleep(max(0, dt - elapsed))

        # 3. 后处理：构建 Action (Shift 1)
        if len(data_rows) > 1:
            for i in range(len(data_rows) - 1):
                data_rows[i]["action"] = data_rows[i+1]["observation.state"]
            data_rows[-1]["action"] = data_rows[-1]["observation.state"]
            data_rows[-1]["done"] = True

            with (episode_dir / "data.jsonl").open("w") as f:
                for row in data_rows:
                    f.write(json.dumps(row) + "\n")

            write_info_json_v3(meta_dir, args.fps, args.robot_type, len(joint_names), joint_names)
            
            # 更新 episodes.jsonl
            with (meta_dir / "episodes.jsonl").open("a") as f:
                entry = {"episode_index": args.episode_id, "length": len(data_rows)}
                f.write(json.dumps(entry) + "\n")

            log_message(f"录制保存成功: {len(data_rows)} 帧")
    except Exception as e:
        log_message(f"录制异常: {e}")
    finally:
        for w in video_writers.values(): w.release()
        camera.close_camera()

# --- MQTT 消息回调 ---
def on_message(client, userdata, msg):
    global is_recording, record_thread
    try:
        payload = json.loads(msg.payload.decode())
        cmd = payload.get("cmd")
        if cmd == "start":
            if is_recording: return
            out_dir = Path(payload.get("output_dir", "lerobot_dataset"))
            args = argparse.Namespace(
                output_dir=out_dir,
                episode_id=payload.get("episode_id") or get_next_episode_id(out_dir),
                fps=payload.get("fps", 10.0),
                robot_type="agibot"
            )
            is_recording = True
            record_thread = threading.Thread(target=record_thread_function, args=(args,))
            record_thread.start()
        elif cmd == "stop":
            is_recording = False
            if record_thread: record_thread.join()
    except Exception as e:
        log_message(f"MQTT消息处理失败: {e}")

def main():
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK初始化失败")
        return

    client = mqtt.Client()
    client.on_message = on_message
    client.on_connect = lambda c, u, f, rc: c.subscribe(MQTT_TOPIC)
    
    global log_client
    log_client = client

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"服务已启动，监听主题: {MQTT_TOPIC}")
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    finally:
        agibot_gdk.gdk_release()

if __name__ == "__main__":
    main()