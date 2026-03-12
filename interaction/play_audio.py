import agibot_gdk
import time

if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)

interaction = agibot_gdk.Interaction()
time.sleep(1)

# 播放音频文件
try:
    interaction.play_audio("/data/wxf/interaction/tts.wav")
    print("音频播放成功")
    time.sleep(5)  # 等待播放完成
except Exception as e:
    print(f"播放音频失败: {e}")

agibot_gdk.gdk_release()