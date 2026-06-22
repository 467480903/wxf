#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过ROS获取底盘运动速度

功能：
1. 订阅ROS里程计话题获取实际速度
2. 实时显示底盘线速度和角速度

ROS话题说明：
- /odom: 里程计数据，包含机器人实际运动速度
- /cmd_vel: 速度命令，可能包含期望速度

使用方法：
    python3 get_ros_speed.py
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist


class ChassisSpeedMonitor(Node):
    def __init__(self):
        super().__init__('chassis_speed_monitor')
        
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.wx = 0.0
        self.wy = 0.0
        self.wz = 0.0
        
        self.cmd_vx = 0.0
        self.cmd_vy = 0.0
        self.cmd_wz = 0.0
        
        self.odom_sub = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )
        
        self.cmd_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_callback,
            10
        )
        
    def odom_callback(self, msg):
        self.vx = msg.twist.twist.linear.x
        self.vy = msg.twist.twist.linear.y
        self.vz = msg.twist.twist.linear.z
        self.wx = msg.twist.twist.angular.x
        self.wy = msg.twist.twist.angular.y
        self.wz = msg.twist.twist.angular.z
        
    def cmd_callback(self, msg):
        self.cmd_vx = msg.linear.x
        self.cmd_vy = msg.linear.y
        self.cmd_wz = msg.angular.z


def main(args=None):
    print("📊 底盘速度监控 (ROS)")
    print("=" * 60)
    print("按 Ctrl+C 退出")
    print("-" * 60)
    
    rclpy.init(args=args)
    monitor = ChassisSpeedMonitor()
    
    print("✅ ROS节点启动成功，开始监控底盘速度...\n")
    
    try:
        while rclpy.ok():
            rclpy.spin_once(monitor, timeout_sec=0.1)
            
            print(f"\r实际速度: vx={monitor.vx:+.4f} m/s  vy={monitor.vy:+.4f} m/s  wz={monitor.wz:+.4f} rad/s"
                  f" | 命令速度: vx={monitor.cmd_vx:+.4f} m/s  wz={monitor.cmd_wz:+.4f} rad/s", end='')
            
    except KeyboardInterrupt:
        print("\n\n👋 退出监控")
    finally:
        monitor.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
