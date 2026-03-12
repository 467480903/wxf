import agibot_gdk
import time

if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)

interaction = agibot_gdk.Interaction()
time.sleep(1)

# 设置音量为50
try:
    interaction.set_volume(100)
    print("设置音量成功")
except Exception as e:
    print(f"设置音量失败: {e}")

agibot_gdk.gdk_release()