import pdb
import time

# 主程序
print("c.py 开始执行")
print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

pdb.set_trace()


# 第一个断点
print("断点 1")
print(1)

# 第二个断点
print("断点 2")
print(2)

# 第三个断点
print("断点 3")
print(3)

# 第四个断点
print("断点 4")
print(3)

# 第五个断点
print("断点 5")
print(5)

print("c.py 执行完成")
print(f"完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

