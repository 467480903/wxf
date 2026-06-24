# G2 `/data/wxf/wxf` 全量脚本改 MQTT/Gateway 使用教程

本文档给现场同事使用。目标是把 `/data/wxf/wxf` 下面原来会直接调用
GDK/SDK 的脚本，迁移到我们的 MQTT/Gateway 服务调用方式，避免每个小脚本
反复 `import agibot_gdk`、`gdk_init()`、`gdk_release()`。

这次不是只改 `yolo` 一个目录，而是做了一个新的全量镜像目录：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624
```

原始目录没有改：

```text
/data/wxf/wxf/yolo
/data/wxf/wxf/BOX_528_1
/data/wxf/wxf/Robot
/data/wxf/wxf/positions
```

以后要测试 MQTT 版本，一律进入新目录；不要在原目录直接跑会动机器人的旧脚本。

---

## 1. 先回答最重要的问题

### 1.1 它们的脚本还需要 `import gdk` 吗？

不需要。

新目录里的迁移脚本不应该再出现：

```python
import agibot_gdk
gdk_init()
gdk_release()
```

原因很直接：如果脚本里还保留这些调用，那它运行时还是会初始化/释放 GDK，
就节省不了你要节省的那段时间。

### 1.2 它们的脚本是不是要连接我们的 MQTT 服务？

是。

新方式是：

```text
脚本 -> mqtt_common.submit_task() -> MQTT topic g2.task.v1 -> Gateway 服务 -> 返回结果
```

脚本只负责提交任务和等结果，不再自己初始化机器人 SDK。

### 1.3 现在会不会真实动机器人？

不会。

当前迁移目录默认是安全状态：

```text
运动类命令默认 mode=dry_run 或 mock
Gateway 返回 result.executed=false
live/motion 没有打开
```

所以现在能验证：

```text
脚本能不能跑
路径能不能解析
参数能不能发出去
MQTT/Gateway 能不能收到并返回
总控步骤能不能串起来
```

但不会真实执行底盘、机械臂、夹爪、腰部、头部动作。

---

## 2. 新目录结构

新目录：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
```

主要内容：

```text
yolo/          # 四个总控和视觉脚本的 MQTT 迁移副本
BOX_528_1/     # 上肢/底盘流程脚本的 MQTT 迁移副本
Robot/         # 夹爪/末端脚本的 MQTT 迁移副本
positions/     # 姿态 JSON 副本
mqtt_common/   # MQTT 通用调用库
gateway_mqtt_client.py
test_mqtt_migration.py
MIGRATION_REPORT.md
USAGE_GUIDE.md
```

注意：

```text
yolo/yolo-env -> /data/wxf/wxf/yolo/yolo-env
```

也就是说，新目录里的 YOLO 环境是软链接到原来的虚拟环境，避免复制很大的环境目录。

---

## 3. 四个总控在哪

四个总控都在新目录的 `yolo` 子目录里：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo

python3 task_all.py
python3 task_all_pick_b.py
python3 task_all_place_b.py
python3 task_all_pull_car.py
```

这四个命令默认是计划模式，只打印每一步，不执行步骤。

计划模式用于确认：

```text
每一步脚本路径是否能解析到新目录
有没有跑回原目录
有没有 blocked_external 或 blocked_unknown
```

这次检查结果：

```text
task_all.py           31 步，全部解析到新目录
task_all_pick_b.py    10 步，全部解析到新目录
task_all_place_b.py   29 步，全部解析到新目录
task_all_pull_car.py   7 步，全部解析到新目录
```

其中 `task_all_pull_car.py` 原来引用了：

```text
../BOX_528_1/move-gopullcar.py
../BOX_528_1/move-pullcar.py
```

但当前 `BOX_528_1` 里实际是下划线文件名：

```text
move_gopullcar.py
move_pullcar.py
```

新目录里已经补了连字符别名文件，只改新目录，不动原目录。

---

## 4. 第一次使用前必须做的 4 个检查

### 4.1 确认没有进错目录

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
pwd
```

期望输出：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624
```

如果输出是下面这些，就说明进错了：

```text
/data/wxf/wxf/yolo
/data/wxf/wxf/BOX_528_1
/data/wxf/wxf/Robot
```

进错目录时不要跑运动脚本，因为那会回到旧 GDK 调用方式。

### 4.2 检查新目录没有直接 GDK 入口

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
grep -RIn -E 'agibot_gdk|gdk_init|gdk_release' \
  --include='*.py' \
  --exclude-dir=yolo-env \
  --exclude-dir=__pycache__ \
  .
```

期望结果：

```text
无输出
```

也可以跑自动检查：

```bash
python3 test_mqtt_migration.py
```

期望输出：

```text
OK: all migrated python files compile and do not contain direct SDK init/release tokens
```

### 4.3 检查 MQTT/Gateway 通路

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 gateway_mqtt_client.py \
  --command gdk.read_power_state \
  --mode read_only \
  --args-json '{}' \
  --timeout-s 10
```

期望看到：

```text
"state": "DONE"
```

这是只读检查，不会动机器人。

### 4.4 检查四个总控只做计划

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo

python3 task_all.py
python3 task_all_pick_b.py
python3 task_all_place_b.py
python3 task_all_pull_car.py
```

这一步不加 `--execute`，只看计划。

如果看到某一步类型是：

```text
local_python
vision_python
local_file_op
```

说明它会在新目录内解析。

如果看到：

```text
blocked_external
blocked_unknown
```

不要继续，需要先修路径。

当前我已经验证这四个总控都没有 `blocked_external` 或 `blocked_unknown`。

---

## 5. 总控脚本怎么跑

### 5.1 只看计划，不跑步骤

这是默认方式，也是现场第一次最应该跑的方式：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 task_all_pick_b.py
```

含义：

```text
读取 task_all_pick_b.py 里的步骤
解析每一步脚本
打印计划
不执行任何一步
```

### 5.2 执行迁移后的步骤，但仍然是 dry-run/mock

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 task_all_pick_b.py --execute
```

含义：

```text
执行新目录里的迁移脚本
运动命令提交到 MQTT/Gateway
Gateway 按 dry_run/mock 返回
result.executed=false
不会真实动机器人
```

注意：

```text
--execute 不是 live 真实动作开关
--execute 只是让总控真正调用新目录里的每个步骤
```

当前 live 真实动作没有打开。

---

## 6. 常用单步脚本怎么跑

### 6.1 手臂 JSON 姿态

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 move_arm_by_json.py ../positions/pick_b_2.json
```

内部提交：

```text
command = arm.move_named_pose
mode    = dry_run
```

期望：

```text
"state": "DONE"
"executed": false
```

同样，`BOX_528_1` 里的手臂 JSON 脚本也可以直接跑：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/BOX_528_1
python3 move_arm_by_json_grab_delever.py
```

这次已验证：

```text
command = arm.move_named_pose
state   = DONE
executed=false
JSON 解析到新目录 positions/arm_position_to_grab_2.json
```

### 6.2 全身 JSON 姿态

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 move_whole_body_by_json.py ../positions/pick_standby.json
```

内部拆成：

```text
head.set_pan_tilt
waist.move_named_pose
arm.move_named_pose
```

每个任务都是 dry-run。

### 6.3 夹爪开合

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/Robot
python3 move_ee_pose_close_2.py
```

内部提交：

```text
gripper.close
```

这次已验证：

```text
left/right gripper.close
state=DONE
executed=false
```

打开夹爪同理：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/Robot
python3 move_ee_pose_open_2.py
```

### 6.4 末端相对偏移

示例：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 offset_move_forward_001.py
```

内部提交：

```text
ee.relative_offset
```

常见脚本：

```text
offset_move_forward_001.py
offset_move_forward_002.py
offset_move_forward_006.py
offset_move_forward_009.py
offset_move_backward_002.py
offset_move_left_002.py
offset_move_left_025.py
offset_move_downward_002.py
offset_move_push.py
offset_move_push_grab.py
```

### 6.5 旧 `RobotController.go(index)` 底盘点位

例如：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/BOX_528_1
python3 move-pick2.py
```

这次已验证它会提交多个 dry-run 任务：

```text
nav.goto_pose waypoint_index=11
nav.goto_pose waypoint_index=13
nav.goto_pose waypoint_index=14
nav.goto_pose waypoint_index=15
nav.goto_pose waypoint_index=17
```

但这里要特别说明：

```text
当前 Gateway 还没有真正绑定旧 RobotController.go(index) 的点位表
所以新脚本只是 dry-run placeholder
x/y/yaw 暂时是 0.0
metadata 里保留 waypoint_index
```

也就是说：

```text
现在能确认旧脚本有哪些点位调用
还不能用它真实导航到底盘点位
```

后面如果要真实替换底盘动作，需要把旧点位 index 和实际地图 pose 绑定到
Gateway 后端，然后再单独做 live 审核。

---

## 7. 相机和 YOLO 怎么处理

### 7.1 相机脚本

新相机脚本不直接 import GDK，而是走 Gateway HTTP：

```text
http://127.0.0.1:8767
```

检查相机配置：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 camera_web_viewer.py --check
```

如果需要看 Gateway 端的相机接口，先用浏览器或 curl 看：

```text
http://127.0.0.1:8767/api/cameras
```

### 7.2 YOLO 视觉脚本

`yolo.py`、`yolo_depth.py` 这类视觉脚本本身不是直接 GDK 动作入口，所以没有强行改成 motion wrapper。

总控里如果看到：

```text
yolo-env/bin/python ...
```

新序列执行器会识别为：

```text
vision_python
```

并且在新工作区内通过软链接环境运行。

---

## 8. 新脚本以后应该怎么写

以后如果他们要写一个新的动作脚本，不要再写：

```python
import agibot_gdk

gdk_init()
try:
    ...
finally:
    gdk_release()
```

应该写成：

```python
from mqtt_common import submit_task

result = submit_task(
    command="arm.move_named_pose",
    mode="dry_run",
    args={
        "pose_file": "/data/wxf/wxf/mqtt_gateway_workspace_20260624/positions/example.json",
    },
)
print(result)
```

常见 command：

```text
gdk.read_power_state     # 只读
arm.move_named_pose      # 手臂 JSON 姿态
head.set_pan_tilt        # 头部姿态
waist.move_named_pose    # 腰部姿态
ee.relative_offset       # 末端相对偏移
gripper.open             # 夹爪打开
gripper.close            # 夹爪关闭
nav.goto_pose            # 底盘导航 dry-run placeholder
camera.get_config        # 相机配置
camera.snapshot          # 相机截图
```

当前现场安全规则：

```text
只读命令用 mode=read_only
运动类命令用 mode=dry_run
不要自己写 mode=live
```

如果要进 live，必须先由 Gateway 后端补齐真实动作绑定、权限锁、审计日志、
急停/状态检查，然后再现场确认。

---

## 9. MQTT 调用链是什么

脚本发任务：

```text
topic: g2.task.v1
payload:
{
  "task_id": "...",
  "command": "arm.move_named_pose",
  "mode": "dry_run",
  "args": {...}
}
```

Gateway 返回结果：

```text
topic: g2.task.result.v1
payload:
{
  "task_id": "...",
  "state": "DONE",
  "result": {
    "executed": false
  }
}
```

新脚本正常情况下不用自己拼 MQTT payload，直接用：

```python
from mqtt_common import submit_task
```

只有调试 MQTT 本身时才直接跑：

```bash
python3 gateway_mqtt_client.py \
  --command gdk.read_power_state \
  --mode read_only \
  --args-json '{}' \
  --timeout-s 10
```

---

## 10. 环境变量

默认配置已经够本机使用。

如果 MQTT broker 不在默认地址，可以临时指定：

```bash
export G2_MQTT_HOST=127.0.0.1
export G2_MQTT_PORT=1883
```

如果 Gateway HTTP 不在默认地址：

```bash
export G2_GATEWAY_HTTP=http://127.0.0.1:8767
```

如果想关闭 ready/capabilities 预检查：

```bash
export G2_MQTT_SKIP_READY=1
```

一般现场不需要改这些环境变量。

---

## 11. 常见问题

### 11.1 看到 `executed=false` 是失败吗？

不是。

当前就是安全 dry-run 状态。`executed=false` 表示没有真实动机器人，这是期望行为。

### 11.2 看到 `state=DONE` 但机器人没动，正常吗？

正常。

当前只验证 MQTT/Gateway 调用链，live 动作没打开。

### 11.3 为什么不直接把原目录改掉？

因为现场原始脚本可能还要保留对照，也可能有人正在用。为了不破坏他们更新后的代码，
这次只在新目录创建迁移副本：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624
```

### 11.4 原脚本还能不能跑？

能，但不建议用于这套 MQTT 测试。

原脚本如果直接跑，还是会按旧方式 import/init/release GDK。

### 11.5 总控 `--execute` 会不会真实动？

不会。

`--execute` 只是让总控执行新目录里的步骤。运动步骤仍然是 dry-run/mock。

### 11.6 以后要真实动作怎么办？

不要在脚本里私自改 live。

正确顺序是：

```text
1. Gateway 后端补齐真实动作 binding
2. 每个 command 增加安全检查和审计
3. 点位 index 映射实际地图 pose
4. 现场做 read-only/preflight
5. David 明确批准真实动作
6. 再打开单项 live 测试
```

---

## 12. 我这次已经做过的验证

新目录：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624
```

文件数量：

```text
134 个 Python 文件
目录大小约 73M
```

静态检查：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 test_mqtt_migration.py
```

结果：

```text
OK: all migrated python files compile and do not contain direct SDK init/release tokens
```

GDK 入口检查：

```bash
grep -RIn -E 'agibot_gdk|gdk_init|gdk_release' \
  --include='*.py' \
  --exclude-dir=yolo-env \
  --exclude-dir=__pycache__ \
  .
```

结果：

```text
无输出
```

四个总控计划检查：

```text
task_all.py           全部解析到新目录
task_all_pick_b.py    全部解析到新目录
task_all_place_b.py   全部解析到新目录
task_all_pull_car.py  全部解析到新目录
```

MQTT read-only：

```text
gdk.read_power_state -> state=DONE
```

代表性 dry-run：

```text
yolo/move_arm_by_json.py ../positions/pick_b_2.json
  -> arm.move_named_pose
  -> state=DONE
  -> executed=false

BOX_528_1/move_arm_by_json_grab_delever.py
  -> arm.move_named_pose
  -> state=DONE
  -> executed=false

BOX_528_1/move-pick2.py
  -> nav.goto_pose waypoint_index=11/13/14/15/17
  -> state=DONE
  -> executed=false

Robot/move_ee_pose_close_2.py
  -> gripper.close
  -> state=DONE
  -> executed=false
```

没有执行真实机器人动作。

---

## 13. 现场最短操作流程

第一次只做检查：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 test_mqtt_migration.py
python3 gateway_mqtt_client.py --command gdk.read_power_state --mode read_only --args-json '{}' --timeout-s 10
```

看四个总控计划：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 task_all.py
python3 task_all_pick_b.py
python3 task_all_place_b.py
python3 task_all_pull_car.py
```

执行一个安全 dry-run 单步：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 move_arm_by_json.py ../positions/pick_b_2.json
```

执行一个安全 dry-run 总控：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 task_all_pick_b.py --execute
```

看到 `executed=false` 是正常的。

---

## 14. MQTT live 底盘导航怎么跑

2026-06-24 已经给 Gateway 补了 `nav.goto_pose` live binding，并在真机上验证过
`BOX_528_1/move-pick2.py` 的 MQTT 版本。

当前 Gateway live 状态：

```text
G2_GATEWAY_BACKEND=gdk-live
G2_GATEWAY_ALLOW_LIVE=1
nav.goto_pose modes = mock / dry_run / live
```

只走 MQTT live，不跑旧 GDK 脚本：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/BOX_528_1

G2_WXF_GATEWAY_MODE=live \
G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1 \
G2_WXF_ALLOW_ESTOP_PEDAL_FAULT=1 \
G2_WXF_NAV_TIMEOUT_S=120 \
G2_WXF_NAV_CLIENT_TIMEOUT_S=150 \
G2_WXF_GATEWAY_PREFLIGHT=require \
python3 move-pick2.py
```

含义：

```text
G2_WXF_GATEWAY_MODE=live
  让迁移脚本提交 live MQTT 任务。

G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1
  live 模式必须有这个确认，否则脚本会拒绝提交。

G2_WXF_ALLOW_ESTOP_PEDAL_FAULT=1
  当前现场确认 emergency_stop_pedal_fault_state=1 可接受时才打开。

G2_WXF_GATEWAY_PREFLIGHT=require
  客户端必须先看到 Gateway ready/capabilities retained topic。
```

这次已验证结果：

```text
waypoint_index=11 -> waypoint_name=12, executed=true, final_state=9
waypoint_index=13 -> waypoint_name=14, executed=true, final_state=9
waypoint_index=14 -> waypoint_name=15, executed=true, final_state=9
waypoint_index=15 -> waypoint_name=16, executed=true, final_state=9
waypoint_index=17 -> waypoint_name=18, executed=true, final_state=9
```

收尾检查：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 gateway_mqtt_client.py \
  --command gdk.read_task_state \
  --mode read_only \
  --args-json '{}' \
  --timeout-s 10 \
  --preflight warn
```

期望：

```text
state=DONE
result.task_state.state=9
```
