import agibot_gdk
import time

if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)

interaction = agibot_gdk.Interaction()
time.sleep(1)

# 播放视频文件，循环1次
try:
    interaction.play_video("/path/to/video.mp4", 1)
    print("视频播放成功")
    time.sleep(10)  # 等待播放完成
except Exception as e:
    print(f"播放视频失败: {e}")

# 无限循环播放
try:
    interaction.play_video("/path/to/video.mp4", -1)
    print("视频开始循环播放")
except Exception as e:
    print(f"播放视频失败: {e}")

agibot_gdk.gdk_release()