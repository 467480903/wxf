import agibot_gdk
import time

if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)

interaction = agibot_gdk.Interaction()
time.sleep(1)

# 开启通话模式
try:
    interaction.set_call_mode(True)
    print("开启通话模式成功")
except Exception as e:
    print(f"开启通话模式失败: {e}")

# 关闭通话模式
try:
    interaction.set_call_mode(False)
    print("关闭通话模式成功")
except Exception as e:
    print(f"关闭通话模式失败: {e}")

agibot_gdk.gdk_release()