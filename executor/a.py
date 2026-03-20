import paho.mqtt.client as mqtt
import os
import sys
import threading

# ── 跨平台 pty 处理 ────────────────────────────────────────
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from winpty import PtyProcess
else:
    import pty, select, subprocess

# ── MQTT 配置 ──────────────────────────────────────────────
MQTT_BROKER = "localhost"
MQTT_PORT   = 1883
TOPIC       = "testtopic"

# ── 全局状态 ───────────────────────────────────────────────
pty_proc   = None   # Windows: PtyProcess 对象 / Linux: master_fd
c_process  = None   # Linux only: subprocess.Popen 对象


# ── 输出监听线程 ───────────────────────────────────────────
def monitor_output_windows(proc):
    """Windows: 从 PtyProcess 持续读取输出"""
    while proc.isalive():
        try:
            data = proc.read()
            if data:
                print(data, end="", flush=True)
        except EOFError:
            break
        except Exception as e:
            print(f"\n[monitor] 异常: {e}")
            break
    print("\n[monitor] c.py 输出监听结束")


def monitor_output_linux(master_fd):
    """Linux: 从 pty master_fd 持续读取输出"""
    while True:
        try:
            readable, _, _ = select.select([master_fd], [], [], 0.5)
            if readable:
                data = os.read(master_fd, 4096)
                if not data:
                    break
                print(data.decode("utf-8", errors="replace"), end="", flush=True)
        except OSError:
            break
        except Exception as e:
            print(f"\n[monitor] 异常: {e}")
            break
    print("\n[monitor] c.py 输出监听结束")


# ── 向 c.py stdin 写入数据 ─────────────────────────────────
def send_to_c(data: str):
    global pty_proc, c_process

    if IS_WINDOWS:
        if pty_proc is None or not pty_proc.isalive():
            print("[a.py] c.py 尚未启动，无法发送命令")
            return
        try:
            pty_proc.write(data)
            print(f"[a.py] 已发送: {repr(data)}")
        except Exception as e:
            print(f"[a.py] 发送失败: {e}")
    else:
        if pty_proc is None:
            print("[a.py] c.py 尚未启动，无法发送命令")
            return
        try:
            os.write(pty_proc, data.encode())
            print(f"[a.py] 已发送: {repr(data)}")
        except OSError as e:
            print(f"[a.py] 发送失败: {e}")


# ── 启动 c.py ──────────────────────────────────────────────
def start_c():
    global pty_proc, c_process

    if IS_WINDOWS:
        if pty_proc and pty_proc.isalive():
            print("[a.py] c.py 已在运行，忽略")
            return
        pty_proc = PtyProcess.spawn(
            [sys.executable, "-u", "c.py"]
        )
        print(f"[a.py] c.py 已启动 (Windows PtyProcess)")
        threading.Thread(
            target=monitor_output_windows,
            args=(pty_proc,),
            daemon=True,
        ).start()

    else:
        if c_process and c_process.poll() is None:
            print("[a.py] c.py 已在运行，忽略")
            return
        master_fd, slave_fd = pty.openpty()
        c_process = subprocess.Popen(
            [sys.executable, "-u", "c.py"],
            stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)
        pty_proc = master_fd
        print(f"[a.py] c.py 已启动，PID={c_process.pid}")
        threading.Thread(
            target=monitor_output_linux,
            args=(master_fd,),
            daemon=True,
        ).start()


# ── MQTT 回调 ──────────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] 连接成功，rc={rc}")
    client.subscribe(TOPIC)
    print(f"[MQTT] 已订阅: {TOPIC}")


def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    print(f"\n[MQTT] {msg.topic} -> {payload!r}")

    if payload == "1":
        start_c()

    elif payload == "2":
        print("[a.py] 发送 pdb 命令: n (next)")
        send_to_c("n\r\n")

    elif payload == "3":
        print("[a.py] 发送回车（重复上一条 pdb 命令）")
        send_to_c("\r\n")

    else:
        print(f"[a.py] 未知指令: {payload!r}，忽略")


# ── 主程序 ─────────────────────────────────────────────────
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    print(f"[MQTT] 连接 {MQTT_BROKER}:{MQTT_PORT} ...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
except Exception as e:
    print(f"[MQTT] 连接失败: {e}")
    exit(1)

print("[a.py] 开始监听 MQTT 消息")
print("  发送 1 → 启动 c.py")
print("  发送 2 → pdb next (n)")
print("  发送 3 → 回车（重复上一条命令）")

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\n[a.py] 用户中断，退出")