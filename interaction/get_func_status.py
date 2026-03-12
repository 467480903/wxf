import agibot_gdk
import time

if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)

interaction = agibot_gdk.Interaction()
time.sleep(1)

# 获取功能状态
try:
    func_status = interaction.get_func_status()
    print("功能状态信息:")
    print(f"  功能状态: {func_status.func_status}")
    print(f"  唤醒状态: {func_status.wakeup_status}")
    print(f"  请求者: {func_status.requester}")
    print(f"  唤醒功能启用: {func_status.wakeup_enabled}")
    print(f"  显示功能启用: {func_status.display_enabled}")
    print(f"  音频功能启用: {func_status.audio_enabled}")
    print(f"  中文设置 - 音量: {func_status.cn_settings.volume}, "
          f"语速: {func_status.cn_settings.speech_rate}, "
          f"音色: {func_status.cn_settings.voice_tone}")
    print(f"  英文设置 - 音量: {func_status.en_settings.volume}, "
          f"语速: {func_status.en_settings.speech_rate}, "
          f"音色: {func_status.en_settings.voice_tone}")
    print(f"  时间戳: {func_status.timestamp}")
except Exception as e:
    print(f"获取功能状态失败: {e}")

agibot_gdk.gdk_release()