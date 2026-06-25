import agibot_gdk
import time

if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)

interaction = agibot_gdk.Interaction()
# 遍历并输出 interaction 对象中的所有接口函数
print("\n=== Interaction 对象的接口函数 ===")
for attr_name in dir(interaction):
    # 跳过以双下划线开头的特殊方法（如 __init__, __str__ 等）
    if attr_name.startswith('__'):
        continue
    
    try:
        attr = getattr(interaction, attr_name)
        if callable(attr):
            # 获取方法的参数签名（如果有的话）
            import inspect
            try:
                sig = inspect.signature(attr)
                print(f"  {attr_name}{sig}")
            except:
                print(f"  {attr_name}()")
    except Exception as e:
        print(f"  {attr_name} - 无法访问: {e}")


# 播放视频文件，循环1次
try:
    interaction.play_audio("/home/agi/media_pack/tts.wav")
    print("视频播放成功")
    time.sleep(10)  # 等待播放完成
except Exception as e:
    print(f"播放视频失败: {e}")

# # 无限循环播放
# try:
#     interaction.play_video("/path/to/video.mp4", -1)
#     print("视频开始循环播放")
# except Exception as e:
#     print(f"播放视频失败: {e}")

agibot_gdk.gdk_release()