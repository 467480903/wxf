#!/usr/bin/env python3
"""
显示机器人底盘直线速度（支持后台运行）
使用agibot_gdk的Slam接口获取里程计信息

使用方式：
1. 直接运行: python3 show_chassis_speed.py
2. 在其他脚本中导入使用:
    from show_chassis_speed import ChassisSpeedMonitor
    
    monitor = ChassisSpeedMonitor()
    monitor.start()  # 启动后台监控
    
    # ... 其他代码 ...
    
    monitor.stop()   # 停止监控
"""

import time
import threading
import agibot_gdk


class ChassisSpeedMonitor:
    """底盘速度监控器 - 可在后台线程运行"""
    
    def __init__(self, update_freq=10.0, verbose=True):
        """
        参数:
            update_freq: 更新频率 (Hz)，默认10Hz
            verbose: 是否打印速度信息，默认True
        """
        self.update_freq = update_freq
        self.verbose = verbose
        self.running = False
        self.thread = None
        self.slam = None
        
        # 存储最新速度数据
        self.latest_vx = 0.0
        self.latest_vy = 0.0
        self.latest_speed = 0.0
        self.lock = threading.Lock()
    
    def _init_slam(self):
        """初始化SLAM对象"""
        if self.slam is None:
            try:
                self.slam = agibot_gdk.Slam()
                time.sleep(2)
                if self.verbose:
                    print("✅ SLAM初始化完成")
                return True
            except Exception as e:
                if self.verbose:
                    print(f"❌ SLAM初始化失败: {e}")
                return False
        return True
    
    def _monitor_loop(self):
        """监控循环 - 在后台线程中运行"""
        if not self._init_slam():
            return
        
        count = 0
        interval = 1.0 / self.update_freq
        
        while self.running:
            count += 1
            start_time = time.time()
            
            try:
                # 获取里程计信息
                odom_info = self.slam.get_odom_info()
                
                # 提取速度信息
                vx = odom_info.velocity_body.x  # 前进/后退速度 (m/s)
                vy = odom_info.velocity_body.y  # 侧向速度 (m/s)
                linear_speed = (vx**2 + vy**2)**0.5
                
                # 更新最新速度数据（线程安全）
                with self.lock:
                    self.latest_vx = vx
                    self.latest_vy = vy
                    self.latest_speed = linear_speed
                
                # 打印速度信息
                if self.verbose:
                    print(f"\r[{count}] 底盘速度: vx={vx:.3f} m/s, vy={vy:.3f} m/s, 合成速度={linear_speed:.3f} m/s", 
                          end="", flush=True)
                
            except Exception as e:
                if self.verbose:
                    print(f"\r[{count}] 获取速度失败: {e}", end="", flush=True)
            
            # 控制更新频率
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)
    
    def start(self):
        """启动后台监控线程"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            if self.verbose:
                print("🚀 底盘速度监控已启动")
    
    def stop(self):
        """停止后台监控线程"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=2)
            if self.verbose:
                print("\n🛑 底盘速度监控已停止")
    
    def get_speed(self):
        """获取当前速度数据（线程安全）"""
        with self.lock:
            return {
                'vx': self.latest_vx,
                'vy': self.latest_vy,
                'linear_speed': self.latest_speed
            }


def main():
    """独立运行时的主函数"""
    print("=== 机器人底盘直线速度显示程序 ===")
    print("按 Ctrl+C 停止")
    print()
    
    monitor = ChassisSpeedMonitor(update_freq=10.0, verbose=True)
    monitor.start()
    
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        monitor.stop()
        print("\n程序已退出")


if __name__ == "__main__":
    main()