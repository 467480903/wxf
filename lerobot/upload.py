#!/usr/bin/env python3
import os
import shutil
import datetime
import subprocess
import paho.mqtt.client as mqtt
import zipfile
import json
from pathlib import Path

# --- 配置区 ---
DATASET_DIR = "lerobotDataset"
MAX_ZIP_SIZE = 500 * 1024 * 1024  # 500MB
REMOTE_USER = "admin1"
REMOTE_HOST = "10.20.15.175"
REMOTE_BASE_DIR = "/home/admin1/upload"
MACHINE_PREFIX = "1010"
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
MQTT_TOPIC = "/upload_status"

# --- MQTT 功能 ---
def send_mqtt_message(message):
    """发送MQTT消息"""
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.publish(MQTT_TOPIC, json.dumps(message), qos=0)
        client.disconnect()
        print(f"MQTT消息发送成功: {message}")
    except Exception as e:
        print(f"MQTT消息发送失败: {e}")

# --- 分卷压缩功能 ---
def create_split_zip(source_dir, max_size):
    """创建分卷zip文件"""
    if not os.path.exists(source_dir):
        print(f"错误: 源目录 {source_dir} 不存在")
        return []
    
    # 创建压缩文件的临时目录
    temp_dir = f"{source_dir}_temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    zip_files = []
    current_zip_index = 0
    current_zip_size = 0
    
    # 遍历所有文件
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            
            # 如果单个文件大于max_size，无法压缩
            if file_size > max_size:
                print(f"警告: 文件 {file_path} 大小({file_size} bytes)超过最大限制，跳过压缩")
                continue
            
            # 如果当前zip文件加上这个文件超过限制，创建新的zip文件
            if current_zip_size + file_size > max_size:
                current_zip_index += 1
                current_zip_size = 0
            
            # 创建或打开zip文件
            zip_filename = f"{source_dir}_part_{current_zip_index:02d}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'a', zipfile.ZIP_DEFLATED) as zf:
                # 计算相对路径，保持目录结构
                rel_path = os.path.relpath(file_path, source_dir)
                zf.write(file_path, rel_path)
            
            # 更新当前zip文件大小
            current_zip_size += file_size
            
            # 如果是新创建的zip文件，添加到列表
            if zip_path not in zip_files:
                zip_files.append(zip_path)
    
    print(f"分卷压缩完成，共创建 {len(zip_files)} 个文件")
    return zip_files

# --- SCP上传功能 ---
def upload_files(zip_files):
    """使用scp上传文件到远程服务器"""
    if not zip_files:
        print("没有文件需要上传")
        return False
    
    # 生成时间戳目录
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_dir = f"{REMOTE_BASE_DIR}/{MACHINE_PREFIX}/{timestamp}"
    
    # 创建远程目录
    try:
        subprocess.run(
            ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", "mkdir", "-p", remote_dir],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"远程目录创建成功: {remote_dir}")
    except subprocess.CalledProcessError as e:
        print(f"远程目录创建失败: {e}")
        return False
    
    # 上传所有zip文件
    for zip_file in zip_files:
        try:
            filename = os.path.basename(zip_file)
            remote_path = f"{REMOTE_USER}@{REMOTE_HOST}:{remote_dir}/{filename}"
            
            print(f"正在上传 {filename}...")
            subprocess.run(
                ["scp", zip_file, remote_path],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"{filename} 上传成功")
        except subprocess.CalledProcessError as e:
            print(f"{os.path.basename(zip_file)} 上传失败: {e}")
            return False
    
    return True

# --- 主函数 ---
def main():
    print("开始执行上传任务...")
    
    # 1. 创建分卷zip文件
    zip_files = create_split_zip(DATASET_DIR, MAX_ZIP_SIZE)
    
    if not zip_files:
        print("没有生成任何压缩文件，上传任务取消")
        return
    
    # 2. 上传文件到远程服务器
    upload_success = upload_files(zip_files)
    
    if upload_success:
        # 3. 发送MQTT消息
        mqtt_message = {
            "total_file_count": len(zip_files),
            "machine_name": MACHINE_PREFIX
        }
        send_mqtt_message(mqtt_message)
        print("上传任务完成！")
    else:
        print("上传任务失败")
    
    # 4. 清理临时文件
    temp_dir = f"{DATASET_DIR}_temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        print(f"临时目录 {temp_dir} 已清理")

if __name__ == "__main__":
    main()