import agibot_gdk
import time

if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)

interaction = agibot_gdk.Interaction()
time.sleep(1)

# 获取ASR文本
while 2>1:
    try:
        asr_text = interaction.get_asr_text()
        print(f"识别到的文本: {asr_text}")
    except Exception as e:
        print(f"获取ASR文本失败: {e}")
    
    time.sleep(1)

agibot_gdk.gdk_release()