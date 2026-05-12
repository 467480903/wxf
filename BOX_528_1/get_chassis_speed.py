#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取底盘运动速度工具

功能：
1. 尝试通过任务状态获取底盘速度信息
2. 显示任务执行状态

使用方法：
    python3 get_chassis_speed.py
"""

import time
import agibot_gdk


def get_chassis_speed():
    """获取并显示底盘当前速度"""
    print("📊 底盘状态监控")
    print("=" * 60)
    print("按 Ctrl+C 退出")
    print("-" * 60)
    
    # 初始化GDK
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK初始化失败")
        return
    
    try:
        pnc = agibot_gdk.Pnc()
        time.sleep(1.0)
        
        print("✅ 初始化成功，开始监控底盘状态...\n")
        
        while True:
            try:
                # 获取任务状态
                ts = pnc.get_task_state()
                
                print(f"\r状态: {ts.state:2d}  任务ID: {ts.id:4d}  消息: {ts.message}", end='')
                
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                print("\n\n👋 退出监控")
                break
            except Exception as e:
                print(f"\n❌ 获取状态失败: {e}")
                time.sleep(1.0)
                
    finally:
        agibot_gdk.gdk_release()


def main():
    get_chassis_speed()


if __name__ == "__main__":
    main()
