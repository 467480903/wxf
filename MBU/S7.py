import snap7

PLC_IP = "10.42.1.11"
RACK = 0
SLOT = 1

try:
    # 创建客户端
    client = snap7.client.Client()

    # 连接PLC
    client.connect(PLC_IP, RACK, SLOT)

    if client.get_connected():
        print("PLC 连接成功")
    else:
        print("PLC 连接失败")
        exit()

    # 读取 DB18 的 BYTE0
    data = client.read_area(
        snap7.type.Areas.DB,   # DB区
        8,                    # DB号
        0,                     # 起始字节
        1                      # 读取1字节
    )

    value = data[0]

    print("DB18.DBB0 =", value)

except Exception as e:
    print("发生错误：", e)

finally:
    try:
        client.disconnect()
    except:
        pass