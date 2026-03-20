import time

# 创建一个测试文件
with open('test.txt', 'w') as f:
    f.write('test started at ' + time.strftime('%Y-%m-%d %H:%M:%S'))
print('test.py started')
