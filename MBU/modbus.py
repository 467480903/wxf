#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modbus TCP 周期性读取
连接到 Modbus TCP Server (10.42.1.11)，使用功能码 0x03 (读保持寄存器)
读取地址 40100，每隔 1 秒读取一次。

地址说明：
  40100 属于保持寄存器（4xxxx 区），实际寄存器地址为 100（0-based: 99）
  这里使用 1-based 地址 100，pymodbus 会自动处理。

依赖：
  pip install pymodbus
"""

import sys
import time
import signal

from pymodbus.client import ModbusTcpClient


# ═══════════════════════════════════════════════════════════════
#  配置参数
# ═══════════════════════════════════════════════════════════════

SERVER_IP   = "10.42.1.11"
SERVER_PORT = 502

FUNCTION_CODE = 0x03        # 读保持寄存器 (Read Holding Registers)
ADDRESS       = 40310      # 寄存器地址（40100 → 4区，地址100）
COUNT         = 1           # 读取寄存器数量
INTERVAL      = 1.0         # 读取周期（秒）


# ═══════════════════════════════════════════════════════════════
#  主循环
# ═══════════════════════════════════════════════════════════════

def main():
    print("#" * 60)
    print(f"#  Modbus 周期读取 - 开始")
    print(f"#  服务器 : {SERVER_IP}:{SERVER_PORT}")
    print(f"#  功能码 : 0x{FUNCTION_CODE:02X} (读保持寄存器)")
    print(f"#  地址   : {ADDRESS}")
    print(f"#  周期   : {INTERVAL} 秒")
    print("#" * 60)

    # ── 创建 Modbus TCP 客户端 ──────────────────────────────
    client = ModbusTcpClient(SERVER_IP, port=SERVER_PORT, timeout=3)

    # ── 连接服务器 ──────────────────────────────────────────
    if not client.connect():
        print(f"❌ 无法连接到 Modbus 服务器 {SERVER_IP}:{SERVER_PORT}")
        sys.exit(1)
    print(f"✅ 已连接到 {SERVER_IP}:{SERVER_PORT}")

    # ── 优雅退出处理 ────────────────────────────────────────
    running = [True]

    def signal_handler(sig, frame):
        print("\n⚠️  收到退出信号，正在停止...")
        running[0] = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # ── 周期性读取 ──────────────────────────────────────────
    read_count = 0
    try:
        while running[0]:
            try:
                # 功能码 0x03 = read_holding_registers
                # 40100 → 实际寄存器地址 100（减去 40000 偏移，1-based）
                result = client.read_holding_registers(
                    address=ADDRESS - 40000,
                    count=COUNT,
                    slave=1
                )

                read_count += 1
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

                if result.isError():
                    print(f"[{timestamp}] #{read_count} ❌ 读取错误: {result}")
                else:
                    values = result.registers
                    print(f"[{timestamp}] #{read_count} ✅ 地址 {ADDRESS} 值: {values}")

            except Exception as e:
                print(f"❌ 读取异常: {e}")

            # 等待下一次读取
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    finally:
        client.close()
        print("🔌 Modbus 连接已关闭")
        print("#        Modbus 周期读取 - 已停止        #")


if __name__ == "__main__":
    main()
