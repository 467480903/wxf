import sys
import agibot_gdk
import time

if len(sys.argv) < 2:
    print("用法: python interaction/play_tts_cli.py <要播放的文本>")
    exit(1)

text = " ".join(sys.argv[1:])

if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)

interaction = agibot_gdk.Interaction()
time.sleep(1)

try:
    interaction.play_tts(text)
    print(f"TTS播放成功: {text}")
    time.sleep(3)
except Exception as e:
    print(f"播放TTS失败: {e}")

agibot_gdk.gdk_release()
