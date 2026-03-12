import agibot_gdk
import time

if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)

interaction = agibot_gdk.Interaction()
time.sleep(1)

# 开启音频功能
try:
    interaction.set_audio_switch(True)
    print("开启音频功能成功")
except Exception as e:
    print(f"设置音频开关失败: {e}")

agibot_gdk.gdk_release()