#!/usr/bin/env python3
"""
底盘数据采集程序
===============
用于记录底盘电机和关节数据，包括：
  - 电机输出功率
  - 电机电流/电压
  - 关节角度/速度
  - 里程计数据
  - 时间戳和采样频率

运行方式：
  source /home/agi/app/env.sh
  python3 chassis_data_recorder.py --duration 60 --output data.csv
"""

import agibot_gdk
import time
import csv
import argparse
from datetime import datetime


class ChassisDataRecorder:
    def __init__(self):
        """初始化 GDK 和数据采集器"""
        self._running = False
        
        # 初始化 GDK
        if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
            raise RuntimeError("GDK 初始化失败")
        
        # 获取传感器接口
        self._pnc = agibot_gdk.Pnc()
        self._slam = agibot_gdk.Slam()
        self._motor = agibot_gdk.Motor()
        self._robot = agibot_gdk.Robot()
        
        time.sleep(1.0)
        print("✅ 数据采集器初始化完成")

    def release(self):
        """释放资源"""
        self._running = False
        agibot_gdk.gdk_release()
        print("✅ GDK 资源已释放")

    def _collect_data(self):
        """采集一帧数据"""
        timestamp = datetime.now().isoformat()
        data = {
            'timestamp': timestamp,
            'elapsed_ms': int((datetime.now() - self._start_time).total_seconds() * 1000)
        }
        
        # 里程计数据
        try:
            odom = self._slam.get_odom_info()
            data.update({
                'odom_x': odom.pose.pose.position.x,
                'odom_y': odom.pose.pose.position.y,
                'odom_z': odom.pose.pose.position.z,
                'odom_qx': odom.pose.pose.orientation.x,
                'odom_qy': odom.pose.pose.orientation.y,
                'odom_qz': odom.pose.pose.orientation.z,
                'odom_qw': odom.pose.pose.orientation.w,
                'vel_x': odom.velocity.x,
                'vel_y': odom.velocity.y,
                'vel_z': odom.velocity.z,
                'loc_state': odom.loc_state,
                'loc_confidence': odom.loc_confidence
            })
        except Exception as e:
            print(f"⚠️  获取里程计数据失败: {e}")
        
        # 电机状态数据
        try:
            motor_states = self._motor.get_motor_states()
            for i, state in enumerate(motor_states):
                data.update({
                    f'motor_{i}_id': state.motor_id,
                    f'motor_{i}_position': state.position,
                    f'motor_{i}_velocity': state.velocity,
                    f'motor_{i}_current': state.current,
                    f'motor_{i}_voltage': state.voltage,
                    f'motor_{i}_temperature': state.temperature,
                    f'motor_{i}_status': state.status
                })
        except Exception as e:
            print(f"⚠️  获取电机数据失败: {e}")
        
        # 关节状态数据
        try:
            joint_states = self._robot.get_joint_states()
            for i, joint in enumerate(joint_states):
                data.update({
                    f'joint_{i}_name': joint.name,
                    f'joint_{i}_position': joint.position,
                    f'joint_{i}_velocity': joint.velocity,
                    f'joint_{i}_effort': joint.effort
                })
        except Exception as e:
            print(f"⚠️  获取关节数据失败: {e}")
        
        # 底盘状态
        try:
            chassis_state = self._pnc.get_chassis_state()
            data.update({
                'chassis_mode': chassis_state.mode,
                'chassis_status': chassis_state.status,
                'battery_voltage': chassis_state.battery_voltage,
                'battery_current': chassis_state.battery_current
            })
        except Exception as e:
            print(f"⚠️  获取底盘状态失败: {e}")
        
        return data

    def start_recording(self, output_file, duration=-1, hz=10):
        """开始数据采集"""
        self._start_time = datetime.now()
        self._running = True
        self._hz = hz
        self._interval = 1.0 / hz
        
        print(f"📊 开始数据采集...")
        print(f"   输出文件: {output_file}")
        print(f"   采样频率: {hz} Hz")
        print(f"   采集时长: {'无限' if duration < 0 else f'{duration}秒'}")
        print(f"   按 Ctrl+C 停止采集")
        
        try:
            first_data = self._collect_data()
            headers = list(first_data.keys())
            
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                
                start = time.time()
                sample_count = 0
                
                while self._running:
                    if duration > 0 and time.time() - start >= duration:
                        break
                    
                    data = self._collect_data()
                    writer.writerow(data)
                    f.flush()
                    
                    sample_count += 1
                    elapsed = time.time() - start
                    actual_hz = sample_count / elapsed if elapsed > 0 else 0
                    
                    print(f"\r   已采集: {sample_count} 帧 | 频率: {actual_hz:.1f} Hz | 耗时: {elapsed:.1f}s", end='', flush=True)
                    
                    time.sleep(self._interval)
                
                print(f"\n✅ 采集完成，共 {sample_count} 帧数据")
                
        except KeyboardInterrupt:
            print("\n⏹️  用户中断，停止采集")
        finally:
            self._running = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.release()


def main():
    parser = argparse.ArgumentParser(description='底盘数据采集程序')
    parser.add_argument('--output', '-o', default='chassis_data.csv',
                        help='输出文件路径（CSV格式）')
    parser.add_argument('--duration', '-d', type=int, default=-1,
                        help='采集时长（秒），-1表示无限采集')
    parser.add_argument('--hz', '-f', type=int, default=10,
                        help='采样频率（Hz），默认10')
    
    args = parser.parse_args()
    
    with ChassisDataRecorder() as recorder:
        recorder.start_recording(
            output_file=args.output,
            duration=args.duration,
            hz=args.hz
        )


if __name__ == '__main__':
    main()
