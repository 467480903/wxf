#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
底盘速度控制工具

功能：
1. 设置底盘线速度和角速度
2. 支持手动输入速度值
3. 提供预设速度模式

使用方法：
    python3 set_chassis_speed.py --help
    python3 set_chassis_speed.py --vx 0.5 --wz 0.3
    python3 set_chassis_speed.py --mode slow
"""

import argparse
import time
import agibot_gdk


def set_speed(vx=0.0, vy=0.0, wz=0.0, duration=3.0):
    """
    设置底盘速度
    
    Parameters:
        vx: 线速度（前进/后退），单位m/s
        vy: 横向速度（侧移），单位m/s
        wz: 角速度（旋转），单位rad/s
        duration: 持续时间，单位秒
    """
    print(f"🚗 设置底盘速度: vx={vx} m/s, vy={vy} m/s, wz={wz} rad/s")
    print(f"⏱️  持续时间: {duration}秒")
    
    # 初始化GDK
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("❌ GDK初始化失败")
        return False
    
    try:
        pnc = agibot_gdk.Pnc()
        time.sleep(1.0)
        
        # 创建速度指令
        twist = agibot_gdk.Twist()
        twist.linear = agibot_gdk.Vector3()
        twist.angular = agibot_gdk.Vector3()
        
        twist.linear.x = vx
        twist.linear.y = vy
        twist.linear.z = 0.0
        
        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = wz
        
        # 发送速度指令
        pnc.move_with_twist(twist)
        
        # 持续指定时间
        start_time = time.time()
        while time.time() - start_time < duration:
            time.sleep(0.1)
        
        # 停止底盘
        print("🛑 停止底盘")
        twist.linear.x = 0.0
        twist.linear.y = 0.0
        twist.angular.z = 0.0
        pnc.move_with_twist(twist)
        
        return True
        
    finally:
        agibot_gdk.gdk_release()


def interactive_mode():
    """交互式模式"""
    print("\n🎮 交互式底盘速度控制")
    print("-------------------------")
    
    while True:
        try:
            vx = float(input("请输入线速度vx (m/s): "))
            vy = float(input("请输入横向速度vy (m/s): "))
            wz = float(input("请输入角速度wz (rad/s): "))
            duration = float(input("请输入持续时间 (秒): "))
            
            set_speed(vx, vy, wz, duration)
            
            choice = input("继续控制? (y/n): ")
            if choice.lower() != 'y':
                break
                
        except ValueError:
            print("❌ 请输入有效的数字")
        except KeyboardInterrupt:
            print("\n👋 退出")
            break


def main():
    parser = argparse.ArgumentParser(description="底盘速度控制工具")
    
    # 速度参数
    parser.add_argument("--vx", type=float, default=0.0, 
                        help="线速度（前进/后退），单位m/s，范围[-1.0, 1.0]")
    parser.add_argument("--vy", type=float, default=0.0, 
                        help="横向速度（侧移），单位m/s，范围[-1.0, 1.0]")
    parser.add_argument("--wz", type=float, default=0.0, 
                        help="角速度（旋转），单位rad/s，范围[-2.0, 2.0]")
    parser.add_argument("--duration", type=float, default=3.0, 
                        help="持续时间，单位秒")
    
    # 预设模式
    parser.add_argument("--mode", type=str, choices=['slow', 'normal', 'fast', 'spin', 'stop'],
                        help="预设速度模式")
    
    # 交互模式
    parser.add_argument("--interactive", action="store_true",
                        help="进入交互式控制模式")
    
    args = parser.parse_args()
    
    # 处理预设模式
    mode_settings = {
        'slow':   {'vx': 0.2, 'vy': 0.0, 'wz': 0.1},
        'normal': {'vx': 0.5, 'vy': 0.0, 'wz': 0.3},
        'fast':   {'vx': 0.8, 'vy': 0.0, 'wz': 0.5},
        'spin':   {'vx': 0.0, 'vy': 0.0, 'wz': 1.0},
        'stop':   {'vx': 0.0, 'vy': 0.0, 'wz': 0.0}
    }
    
    if args.mode and args.mode in mode_settings:
        settings = mode_settings[args.mode]
        args.vx = settings['vx']
        args.vy = settings['vy']
        args.wz = settings['wz']
        print(f"📋 使用预设模式: {args.mode}")
    
    # 交互式模式
    if args.interactive:
        interactive_mode()
        return
    
    # 执行速度设置
    set_speed(args.vx, args.vy, args.wz, args.duration)


if __name__ == "__main__":
    main()
