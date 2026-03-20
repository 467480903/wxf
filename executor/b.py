import time
import os
import sys

# 信号文件路径
SIGNAL_FILE = 'step_signal.txt'

# 检查是否存在信号文件，如果存在则删除
if os.path.exists(SIGNAL_FILE):
    os.remove(SIGNAL_FILE)

def wait_for_step():
    """等待执行下一步的信号"""
    print(f"等待执行下一步...")
    start_time = time.time()
    while not os.path.exists(SIGNAL_FILE):
        time.sleep(0.1)
        # 超时检查
        if time.time() - start_time > 60:
            print("等待超时，退出程序")
            break
    # 删除信号文件
    if os.path.exists(SIGNAL_FILE):
        os.remove(SIGNAL_FILE)
        print(f"收到执行信号，继续执行")

# 主程序
print("b.py 开始执行")
print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# 第一个断点
print("断点 1")
wait_for_step()
print(1)

# 第二个断点
print("断点 2")
wait_for_step()
print(1)

# 第三个断点
print("断点 3")
wait_for_step()
print(1)

# 第四个断点
print("断点 4")
wait_for_step()
print(1)

# 第五个断点
print("断点 5")
wait_for_step()
print(1)

print("b.py 执行完成")
print(f"完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")


