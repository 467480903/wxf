import agibot_gdk
import time

if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)

interaction = agibot_gdk.Interaction()
time.sleep(1)

# 播放TTS
try:
    interaction.play_tts("你好，我是精灵G2")
    time.sleep(3)
    # interaction.play_tts("こんにちは、ホンダのお客様、これは工業応用シーンで、自動車のインテリア部品の加工を展示しています")
    # time.sleep(10)    
    interaction.play_tts("No such file or directory")
    print("TTS播放成功")
    time.sleep(3)  # 等待播放完成
except Exception as e:
    print(f"播放TTS失败: {e}")

agibot_gdk.gdk_release()