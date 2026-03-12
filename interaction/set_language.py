import agibot_gdk
import time

# 初始化GDK系统
if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
    print("GDK初始化失败")
    exit(1)
print("GDK初始化成功")

interaction = agibot_gdk.Interaction()
time.sleep(1)  # 等待初始化完成

# 设置语言为中文
try:
    interaction.set_language(agibot_gdk.Language.kLanguageChinese)
    print("设置语言成功")
except Exception as e:
    print(f"设置语言失败: {e}")

# 释放GDK系统资源
if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
    print("GDK释放失败")
    exit(1)
print("GDK释放成功")