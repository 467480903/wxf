#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mqtt_mp3.py — 通过 MQTT 下发 MP3 播放命令

等价于：
    mosquitto_pub -h 192.168.0.10 -p 1883 -u <user> -P <pass> \
                  -t /playMP3 -m '{"cmd":"play","file":"JPCH6.mp3"}'

用法示例：
    # 基本用法（使用默认 broker 和账号）
    python3 mqtt_mp3.py --file JPCH6.mp3

    # 指定 cmd
    python3 mqtt_mp3.py --cmd stop --file JPCH6.mp3

    # 直接下发完整 JSON 报文
    python3 mqtt_mp3.py --message '{"cmd":"play","file":"JPCH6.mp3","vol":80}'

    # 覆盖 broker / 账号
    python3 mqtt_mp3.py --host 192.168.0.10 -u admin -P 123456 \
                        --file JPCH6.mp3

    # 从环境变量读取账号（避免命令行暴露密码）
    export MQTT_USER=admin
    export MQTT_PASSWORD=123456
    python3 mqtt_mp3.py --file JPCH6.mp3

依赖：
    pip install paho-mqtt
"""

import argparse
import json
import os
import sys

import paho.mqtt.client as mqtt


# ══════════════════════════════════════════════════
#  默认参数
# ══════════════════════════════════════════════════
DEFAULT_HOST     = "192.168.0.10"
DEFAULT_PORT     = 1883
DEFAULT_TOPIC    = "/playMP3"
DEFAULT_CMD      = "play"
DEFAULT_USER     = os.environ.get("MQTT_USER", "")        # 可由环境变量传入
DEFAULT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")


def build_payload(args) -> str:
    """根据参数构造 JSON 报文"""
    if args.message:
        # 直接使用用户传入的完整 JSON（顺便校验格式）
        try:
            obj = json.loads(args.message)
            return json.dumps(obj, ensure_ascii=False)
        except json.JSONDecodeError as e:
            print(f"❌ --message 不是合法 JSON: {e}", file=sys.stderr)
            sys.exit(1)

    payload = {"cmd": args.cmd}
    if args.file:
        payload["file"] = args.file
    if args.vol is not None:
        payload["vol"] = args.vol
    # 允许追加任意额外键值（key=value 形式）
    for kv in args.extra or []:
        if "=" not in kv:
            print(f"❌ --extra 格式应为 key=value，收到: {kv}", file=sys.stderr)
            sys.exit(1)
        k, v = kv.split("=", 1)
        # 尝试转成数字/布尔
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            pass
        payload[k] = v
    return json.dumps(payload, ensure_ascii=False)


def publish(host, port, user, password, topic, payload,
            qos=0, keepalive=60, verbose=True):
    """连接 broker 并发布消息"""
    client = mqtt.Client(client_id=f"mqtt_mp3_{os.getpid()}", protocol=mqtt.MQTTv311)
    if user:
        client.username_pw_set(user, password)

    if verbose:
        client.on_connect = lambda c, u, f, rc: print(
            f"✅ 已连接 broker {host}:{port} (rc={rc})"
            if rc == 0 else f"❌ 连接失败 rc={rc}"
        )
        client.on_publish = lambda c, u, mid: print(f"✅ 已发布 mid={mid}")

    client.connect(host, port, keepalive=keepalive)
    client.loop_start()
    info = client.publish(topic, payload, qos=qos)
    info.wait_for_publish()
    client.loop_stop()
    client.disconnect()
    return info.rc


def main():
    ap = argparse.ArgumentParser(
        description="通过 MQTT 下发 MP3 播放命令",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # --- broker 连接参数 ---
    ap.add_argument("--host", default=DEFAULT_HOST, help="MQTT broker 地址")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help="MQTT broker 端口")
    ap.add_argument("-u", "--user", default=DEFAULT_USER, help="用户名（默认读 $MQTT_USER）")
    ap.add_argument("-P", "--password", default=DEFAULT_PASSWORD,
                    help="密码（默认读 $MQTT_PASSWORD）")
    ap.add_argument("-t", "--topic", default=DEFAULT_TOPIC, help="主题")
    ap.add_argument("--qos", type=int, default=0, choices=[0, 1, 2])

    # --- 报文内容参数（二选一） ---
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--message", metavar="JSON",
                   help="直接下发完整 JSON 报文，如 '{\"cmd\":\"play\",\"file\":\"x.mp3\"}'")
    g.add_argument("--file", metavar="NAME", help="MP3 文件名，如 JPCH6.mp3")

    ap.add_argument("--cmd", default=DEFAULT_CMD, help="命令，如 play/stop/pause")
    ap.add_argument("--vol", type=int, help="音量（可选）")
    ap.add_argument("--extra", nargs="*", metavar="KEY=VALUE",
                    help="追加任意额外字段，如 --extra loop=true src=local")

    ap.add_argument("-v", "--verbose", action="store_true", help="打印详细日志")
    args = ap.parse_args()

    # 校验：用 --message 之外的方式时，至少要有 --file
    if not args.message and not args.file:
        print("❌ 请至少提供 --file 或 --message", file=sys.stderr)
        ap.print_help(sys.stderr)
        sys.exit(2)

    payload = build_payload(args)

    if args.verbose:
        print(f"→ 目标: {args.host}:{args.port}  主题: {args.topic}")
        print(f"→ 报文: {payload}")

    rc = publish(
        host=args.host, port=args.port,
        user=args.user, password=args.password,
        topic=args.topic, payload=payload,
        qos=args.qos, verbose=args.verbose,
    )

    if rc != mqtt.MQTT_ERR_SUCCESS:
        print(f"❌ 发布失败 rc={rc}", file=sys.stderr)
        sys.exit(1)
    if args.verbose:
        print("🎉 完成")


if __name__ == "__main__":
    main()
