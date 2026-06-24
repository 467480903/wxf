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

## 0. 2026-06-24 最新状态

现在 Gateway 已经为四个 yolo 总控会用到的动作补齐 live 能力：

```text
nav.goto_pose
head.set_pan_tilt
arm.move_named_pose
waist.move_named_pose
gripper.open
gripper.close
ee.relative_offset
```

也就是说，总控跑到手臂、腰部、夹爪、末端相对位移时，不会再因为
`mode live not advertised` 或 capability 还停在 dry-run 而中断。

但默认仍然不会真实动机器人：

```text
不设置 G2_WXF_GATEWAY_MODE=live      -> dry_run/mock
设置 G2_WXF_GATEWAY_MODE=live        -> 真实 live 请求
再设置 G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1 -> 允许发布 confirm_physical=true
```

现场第一次检查仍然先跑计划模式和 dry-run。确认现场安全后，才用本文第 15 节的
live 总控启动命令。

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

默认不会。

当前迁移目录默认是安全状态：

```text
运动类命令默认 mode=dry_run 或 mock
Gateway 返回 result.executed=false
不会真实动作
```

所以现在能验证：

```text
脚本能不能跑
路径能不能解析
参数能不能发出去
MQTT/Gateway 能不能收到并返回
总控步骤能不能串起来
```

但如果显式加上 live 环境变量，它就会通过 MQTT/Gateway 调真实 GDK live 后端：

```text
G2_WXF_GATEWAY_MODE=live
G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1
```

所以现场同事要记住：

```text
不加 live 变量 = 只验证
加 live 变量 = 真机可能动
```

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

如果没有设置 `G2_WXF_GATEWAY_MODE=live`，即使加了 `--execute`，也仍然是 dry-run/mock。

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

这里要特别说明：

```text
不加 live 环境变量时，它仍然只是 dry-run，不会真实导航。
加 live 环境变量后，Gateway 会在当前地图里解析 waypoint_index，再调用 Pnc.normal_navi。
```

2026-06-24 已经真机验证过 `move-pick2.py` 的 5 个点位：

```text
waypoint_index=11 -> waypoint_name=12 -> final_state=9
waypoint_index=13 -> waypoint_name=14 -> final_state=9
waypoint_index=14 -> waypoint_name=15 -> final_state=9
waypoint_index=15 -> waypoint_name=16 -> final_state=9
waypoint_index=17 -> waypoint_name=18 -> final_state=9
```

其它底盘点位脚本也走同一个 `nav.goto_pose` live 后端，但第一次跑前仍然要先做
plan/dry-run 和现场 preflight。

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
nav.goto_pose            # 底盘导航
camera.get_config        # 相机配置
camera.snapshot          # 相机截图
```

当前现场安全规则：

```text
只读命令用 mode=read_only
默认检查用 mode=dry_run
真机动作只通过 G2_WXF_GATEWAY_MODE=live + G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1 打开
```

不要在脚本源码里硬写 `mode="live"`。现场要 live 时，用环境变量打开，这样同一套脚本
可以安全地在 dry-run 和 live 之间切换。

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

没有设置 live 环境变量时就是安全 dry-run 状态。`executed=false` 表示没有真实动机器人，这是期望行为。

### 11.2 看到 `state=DONE` 但机器人没动，正常吗？

正常。

没有设置 live 环境变量时，只验证 MQTT/Gateway 调用链，不会真实动作。

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

只加 `--execute` 不会。

`--execute` 只是让总控执行新目录里的步骤。是否真实动作由环境变量决定：

```text
没有 G2_WXF_GATEWAY_MODE=live
  -> dry-run/mock

有 G2_WXF_GATEWAY_MODE=live 且有 G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1
  -> live 真机动作
```

### 11.6 以后要真实动作怎么办？

不要在脚本里私自改 live。

正确顺序是：

```text
1. 先跑计划模式确认路径
2. 再跑 dry-run/mock 确认 MQTT 调用链
3. 确认 Gateway backend=gdk-live 且 allow_live=true
4. 确认 capability 里对应 command 有 live
5. 现场做 read-only/preflight
6. David/现场负责人确认可以真实运动
7. 再加 live 环境变量执行
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

正式跑总控时，不建议现场手写底盘参数，直接用包装脚本：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_live_task.sh pick_b
```

如果只是单独验证 `BOX_528_1/move-pick2.py` 这个底盘脚本，才用下面命令。
它仍然只走 MQTT live，不跑旧 GDK 脚本：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/BOX_528_1

G2_WXF_GATEWAY_MODE=live \
G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1 \
G2_WXF_ALLOW_ESTOP_PEDAL_FAULT=1 \
G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S=45 \
G2_WXF_GATEWAY_PREFLIGHT=require \
python3 move-pick2.py
```

### 14.1 这条命令到底做了什么

这条命令不是直接调用 GDK，也不是跑原始脚本。

实际调用链是：

```text
新目录 move-pick2.py
  -> 新目录 robot_controller.py
  -> mqtt_common.RobotController.go(index)
  -> 发布 MQTT 任务 nav.goto_pose
  -> g2-industrial-gateway-mqtt.service
  -> g2-industrial-gateway.service
  -> Gateway 内部长期 GDK 会话
  -> Pnc.normal_navi(NaviReq)
```

所以脚本侧不会再做：

```text
import agibot_gdk
gdk_init()
gdk_release()
```

### 14.2 每个环境变量是什么意思

#### `G2_WXF_GATEWAY_MODE=live`

含义：

```text
告诉迁移脚本：这次要提交 live 真机任务，不是 dry_run。
```

如果不加这个变量，默认是：

```text
dry_run
```

dry-run 只验证 MQTT/Gateway 调用链，不会真实动底盘。

什么时候能加：

```text
现场人员已经确认机器人周围安全，可以真实运动。
Gateway 当前已经是 gdk-live。
Gateway capability 里 nav.goto_pose 支持 live。
```

什么时候不能加：

```text
只想检查脚本路径或 MQTT 是否通。
现场没人看机器人。
周围有人、障碍物、线缆、车架、托盘等不确定。
```

#### `G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1`

含义：

```text
这是第二道确认，明确告诉脚本：本次允许真实物理运动。
```

为什么需要它：

```text
G2_WXF_GATEWAY_MODE=live 只是选择 live 模式。
G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1 是现场运动确认。
两个都要有，脚本才会提交 confirm_physical=true。
```

如果没有这个变量：

```text
脚本会拒绝 live。
不会发布真实运动任务。
```

MQTT payload 里会变成：

```text
mode=live
confirm_physical=true
```

Gateway 也会检查这个字段。没有 `confirm_physical=true`，Gateway 会拦住 live 任务。

#### `G2_WXF_ALLOW_ESTOP_PEDAL_FAULT=1`

含义：

```text
允许当前已知的 emergency_stop_pedal_fault_state=1 继续通过导航 preflight。
```

这不是普通开关，不能随便加。

当前为什么要加：

```text
现场 preflight 读到:
emergency_stop_pedal_fault_state=1
emergency_stop_pedal_state=0

David 已确认现场可以运动，所以这次把这个已知项显式写进 MQTT payload。
```

它不会修改急停，也不会清故障：

```text
不改急停逻辑
不改控制器安全逻辑
不写硬件状态
只是告诉 Gateway：这个已知 preflight 项本次由现场人工确认接受
```

什么时候不能加：

```text
现场没有确认这个 fault 是已知可接受状态。
急停踏板实际被踩下。
机器人周围不安全。
不确定 emergency_stop_pedal_state 是不是 0。
```

如果不加它，而且 Gateway 读到 `emergency_stop_pedal_fault_state=1`：

```text
nav.preflight 会认为 ok=false
live 导航会被 Gateway 拦住
```

#### 底盘运行过程参数不用手写

底盘导航的普通等待时间、MQTT 客户端等待时间、进展判断阈值都保留代码默认值。
现场命令只暴露一个真正有用的保护项：`G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S=45`。

这个值不是固定等待时间。导航成功会马上结束，导航失败会马上失败。
只有 PNC 一直 RUNNING、但 SLAM/odom 连续 45 秒没有进展时，Gateway 才会取消当前导航并返回失败。

#### `G2_WXF_GATEWAY_PREFLIGHT=require`

含义：

```text
客户端发布任务前，必须先确认 Gateway MQTT retained topic 正常。
```

它会检查：

```text
Gateway ready topic
Gateway capabilities topic
nav.goto_pose 是否存在
nav.goto_pose 是否支持 live
```

如果检查不通过：

```text
客户端不会发布 live 任务。
```

为什么不要随便改成 `skip`：

```text
skip 会跳过 ready/capability 检查。
如果 Gateway 没切到 live，或者 MQTT adapter 还没刷新 capability，问题会到更后面才暴露。
现场更难判断到底卡在哪一层。
```

推荐：

```text
真机 live 一律用 require。
调试 retained topic 问题时才临时用 warn。
不要在现场运动时用 skip。
```

### 14.3 启动前注意事项

确认进的是新目录：

```bash
pwd
```

必须是：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/BOX_528_1
```

不能是：

```text
/data/wxf/wxf/BOX_528_1
```

确认 Gateway 是 live：

```bash
curl -s http://127.0.0.1:8767/api/runtime
```

要看到：

```text
backend=gdk-live
allow_live=true
```

确认 `nav.goto_pose` 支持 live：

```bash
curl -s http://127.0.0.1:8767/api/capabilities
```

`nav.goto_pose` 里要有：

```text
modes = ["mock", "dry_run", "live"]
```

先做只读 preflight：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 gateway_mqtt_client.py \
  --command nav.preflight \
  --mode read_only \
  --args-json '{}' \
  --timeout-s 10 \
  --preflight warn
```

重点看：

```text
map 是否 ok
odom 是否 ok
pnc_task 是否空闲或成功态
charge_plug_insert_state 是否 0
emergency_stop_pedal_state 是否 0
```

### 14.4 执行中怎么看结果

正常输出里，每个点都应该看到：

```text
"command": "nav.goto_pose"
"mode": "live"
"confirm_physical": true
"executed": true
"gdk_call": {"method": "Pnc.normal_navi"}
"final_state": 9
"state": "DONE"
```

这些字段的意思：

```text
mode=live
  这次不是 dry-run。

confirm_physical=true
  本次现场确认已经进入 MQTT payload。

executed=true
  Gateway 后端确实执行了真实 GDK/PNC 调用。

Pnc.normal_navi
  实际底盘导航 API。

final_state=9
  PNC 返回成功。

state=DONE
  Gateway 任务完成。
```

如果看到：

```text
executed=false
```

说明没有真实运动，通常是 dry-run/mock。

如果看到：

```text
state=FAILED
state=BLOCKED
```

不要继续跑后面的点，先看 `error` 字段。

### 14.5 跑完后注意事项

跑完后做只读任务状态检查：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 gateway_mqtt_client.py \
  --command gdk.read_task_state \
  --mode read_only \
  --args-json '{}' \
  --timeout-s 10 \
  --preflight warn
```

期望看到：

```text
state=DONE
result.task_state.state=9
```

如果 `task_state.state` 不是 9，要先确认机器人当前是否还在执行、失败、取消或暂停。

### 14.6 常见错误怎么判断

错误：

```text
live mode requires G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1
```

原因：

```text
设置了 G2_WXF_GATEWAY_MODE=live，但没有设置 G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1。
```

处理：

```text
确认现场可以真实运动后，再加 G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1。
```

错误：

```text
mode 'live' not advertised for nav.goto_pose
```

原因：

```text
Gateway 或 MQTT adapter 还没有暴露 nav.goto_pose live capability。
```

处理：

```text
检查 Gateway 是否是 gdk-live。
检查 g2-industrial-gateway-mqtt.service 是否已重启并刷新 retained capability。
```

错误：

```text
nav preflight blocked: emergency_stop_pedal_fault_state!=0
```

原因：

```text
Gateway preflight 发现急停踏板 fault 状态。
```

处理：

```text
如果现场确认这是已知可接受状态，才加 G2_WXF_ALLOW_ESTOP_PEDAL_FAULT=1。
如果没有确认，不要加，先处理现场状态。
```

错误：

```text
timed out waiting for MQTT result
```

可能原因：

```text
导航还没结束，客户端 timeout 太短。
Gateway/MQTT adapter 异常。
MQTT retained/result topic 没返回。
```

处理：

```text
先查 gdk.read_task_state。
再查 systemctl is-active g2-industrial-gateway.service g2-industrial-gateway-mqtt.service。
不要马上重复发同一个 live 导航，避免叠加任务。
```

错误：

```text
std::future_error: Broken promise
```

说明：

```text
这是 GDK Map RPC 偶发返回异常。Gateway 已给 Map.get_curr_map / Map.get_map 增加 retry。
如果再次出现，先做一次 nav.preflight 预热，再重试。
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

---

## 15. 四个 yolo 总控 live 真机怎么启动

四个总控都从新目录启动，不要回原目录：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
```

启动前先确认 Gateway 当前 live 能力：

```bash
curl -s http://127.0.0.1:8767/api/runtime
curl -s http://127.0.0.1:8767/api/capabilities
```

总控需要的这些 command 都必须包含 `live`：

```text
nav.goto_pose
head.set_pan_tilt
arm.move_named_pose
waist.move_named_pose
gripper.open
gripper.close
ee.relative_offset
```

2026-06-24 当前机器人已经确认：

```text
backend=gdk-live
allow_live=true
上述 7 个 command modes 都是 ["mock", "dry_run", "live"]
```

### 15.1 最简 live 启动方式

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_live_task.sh pick_b
```

其它三个总控只换最后的任务名：

```bash
./run_live_task.sh place_b
./run_live_task.sh all
./run_live_task.sh pull_car
```

这四个名字对应：

```text
pick_b    -> yolo/task_all_pick_b.py
place_b   -> yolo/task_all_place_b.py
all       -> yolo/task_all.py
pull_car  -> yolo/task_all_pull_car.py
```

### 15.2 单独跑子脚本怎么启动

正常现场跑任务优先用四个总控，不建议随便单独跑子脚本。

如果确实要单独验证某个子脚本，用这个通用启动器：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_live_script.sh 子脚本相对路径 [子脚本参数...]
```

例子：

```bash
# 单独跑底盘点位脚本
./run_live_script.sh BOX_528_1/move-pick2.py

# 单独跑手臂 JSON 姿态
./run_live_script.sh yolo/move_arm_by_json.py ../positions/pick_b_2.json

# 单独跑全身 JSON 姿态
./run_live_script.sh yolo/move_whole_body_by_json.py ../positions/pick_standby.json

# 单独跑夹爪关闭
./run_live_script.sh Robot/move_ee_pose_close_2.py
```

注意：

```text
1. 路径必须写新 MQTT 工作区里的相对路径，不要写 /data/wxf/wxf/yolo 这种原始目录路径。
2. 启动器会自动 cd 到子脚本所在目录再执行，所以子脚本参数里的 ../positions/xxx.json 仍然按原脚本习惯写。
3. 这个启动器默认就是 live，会让真机运动；只在现场确认安全时使用。
4. 单独跑子脚本会跳过总控前后顺序，可能导致姿态、夹爪、物料状态不符合预期；现场调试时要明确知道当前机器人姿态。
```

### 15.3 包装脚本里面默认带了什么

`run_live_task.sh` 和 `run_live_script.sh` 内部只保留必要项：

```text
G2_WXF_GATEWAY_MODE=live
G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1
G2_WXF_GATEWAY_PREFLIGHT=require
G2_WXF_ALLOW_ESTOP_PEDAL_FAULT=1
G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S=45
```

含义：

```text
G2_WXF_GATEWAY_MODE=live
  走 MQTT live 真机模式。

G2_WXF_GATEWAY_CONFIRM_PHYSICAL=1
  明确允许真实机器人运动。没有这个变量，迁移脚本会拒绝 live。

G2_WXF_GATEWAY_PREFLIGHT=require
  发布 MQTT 任务前必须看到 Gateway ready 和 capability 正常。真机 live 不建议跳过。

G2_WXF_ALLOW_ESTOP_PEDAL_FAULT=1
  只是在当前现场已确认 emergency_stop_pedal_fault_state=1 可接受时使用。
  它不会清急停，不会禁用急停，也不会改控制器安全逻辑。

G2_WXF_NAV_NO_PROGRESS_TIMEOUT_S=45
  底盘唯一暴露出来的运行保护参数。
  它不是固定等待时间；导航成功会马上结束，导航失败会马上失败。
  只有 PNC 一直 RUNNING、但 SLAM/odom 连续 45 秒没有进展时，Gateway 才会取消当前导航并返回 FAILED。
```

其它底盘判断阈值、MQTT client timeout、整套任务预算都保留代码默认值，现场人员不用在命令里写。

### 15.4 四个总控分别会做什么

```text
pick_b:
  底盘 nav.goto_pose
  头部 head.set_pan_tilt
  腰部 waist.move_named_pose
  手臂 arm.move_named_pose
  夹爪 gripper.close
  末端 ee.relative_offset

place_b:
  头部 head.set_pan_tilt
  腰部 waist.move_named_pose
  手臂 arm.move_named_pose
  夹爪 gripper.open
  末端 ee.relative_offset
  相机快照和 YOLO 本地视觉脚本
  本地 cp/mv 文件操作

all:
  底盘、夹爪、手臂、腰部、末端偏移、相机和 YOLO。
  这个总控步骤最多，现场第一次跑建议先单步确认关键动作，再跑完整总控。

pull_car:
  底盘 nav.goto_pose
  头部 head.set_pan_tilt
  腰部 waist.move_named_pose
  手臂 arm.move_named_pose
  末端 ee.relative_offset
```

### 15.5 跑前最小检查清单

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 test_mqtt_migration.py

python3 gateway_mqtt_client.py \
  --command gdk.read_power_state \
  --mode read_only \
  --args-json '{}' \
  --timeout-s 15 \
  --preflight require
```

再看四个总控计划：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 task_all.py
python3 task_all_pick_b.py
python3 task_all_place_b.py
python3 task_all_pull_car.py
```

确认没有 `blocked_external`、`blocked_unknown`、`missing_local` 后，再回到工作区根目录用
`./run_live_task.sh 任务名` 跑 live。

### 15.6 当前现场状态提醒

如果只读 preflight 里看到：

```text
charge_plug_insert_state=1
charge_input_current>0.5
```

说明机器人还在充电或插枪状态。这个状态下不要跑 live 总控，Gateway 也会挡住
`nav.goto_pose`。需要现场确认充电断开、`charge_plug_insert_state=0` 后再跑。

### 15.7 如果跑到一半失败

先不要重复启动同一个总控。先查最后一个任务：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 gateway_mqtt_client.py \
  --command gdk.read_task_state \
  --mode read_only \
  --args-json '{}' \
  --timeout-s 10 \
  --preflight warn
```

再看服务：

```bash
systemctl is-active g2-industrial-gateway.service
systemctl is-active g2-industrial-gateway-mqtt.service
```

如果错误是 capability 没有 live，说明 MQTT adapter retained capability 没刷新或 Gateway 没重启。
这次已重启并验证，正常情况下不会再卡在 arm/waist/gripper/ee live 未开放。

---

## 16. 新建 MQTT 脚本标准流程

新脚本不要放回原始目录里改。统一放在新 MQTT 工作区：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624
```

新脚本必须遵守：

```text
1. 不在子脚本里 import 机器人 GDK 包。
2. 不在子脚本里初始化或释放 GDK。
3. 子脚本只调用 mqtt_common 里的 helper。
4. Gateway 服务内部负责长期 GDK 会话。
5. 新脚本先 dry-run，再 live。
```

一句话理解：

```text
它们以后写脚本，不是“脚本自己连机器人底层 SDK”，而是“脚本调用 mqtt_common，
mqtt_common 通过 MQTT 把任务发给 Gateway，Gateway 再用长期会话去动机器人”。
```

### 16.0 先记住三条命令

新建脚本：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
cp templates/new_mqtt_child_script.py yolo/my_new_script.py
```

先 dry-run：

```bash
./run_dry_script.sh yolo/my_new_script.py
```

确认安全后 live：

```bash
./run_live_script.sh yolo/my_new_script.py
```

这三条就是它们以后创建和运行新 MQTT 子脚本的主流程。

### 16.1 复制模板创建新脚本

例如要新建一个 yolo 子脚本：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
cp templates/new_mqtt_child_script.py yolo/my_new_script.py
```

然后编辑：

```bash
vim yolo/my_new_script.py
```

模板文件是：

```text
templates/new_mqtt_child_script.py
```

模板默认不会动机器人。复制以后，把 `main()` 改成真实动作。

### 16.2 新脚本里面怎么写

模板里已经写了很多注释。它们真正要改的地方只有 `main()`。

保留模板顶部这段自动寻找 `mqtt_common` 的代码，不要删：

```python
for _parent in Path(__file__).resolve().parents:
    _common = _parent / "mqtt_common"
    if _common.is_dir():
        sys.path.insert(0, str(_common))
        break
else:
    raise RuntimeError("mqtt_common not found; put this script under the MQTT workspace")
```

这段的作用：

```text
无论新脚本放在 yolo/、BOX_528_1/、Robot/，还是以后新建的子目录里，
它都能自动找到 mqtt_common。
```

常用 helper：

```text
run_nav_waypoints(...)      底盘走旧 waypoint index
run_head_named(...)         头部姿态
run_whole_body_json(...)    头、腰、双臂整体 JSON 姿态
run_arm_json(...)           双臂 JSON 姿态
run_waist_json(...)         腰部 JSON 姿态
run_gripper("open", ...)    打开夹爪
run_gripper("close", ...)   关闭夹爪
run_ee_offsets(...)         末端相对偏移
```

### 16.2.1 创建一个完整 demo 子脚本

下面这个例子创建一个 demo，动作是：

```text
1. 先到 pick_standby 全身姿态。
2. 再到 pick_b_2 手臂姿态。
3. 最后关闭夹爪。
```

创建文件：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
cp templates/new_mqtt_child_script.py yolo/demo_pick_close.py
vim yolo/demo_pick_close.py
```

把 `main()` 改成这样：

```python
def main() -> int:
    run_whole_body_json("../positions/pick_standby.json", SOURCE_SCRIPT)
    run_arm_json("../positions/pick_b_2.json", SOURCE_SCRIPT)
    run_gripper("close", SOURCE_SCRIPT)
    return 0
```

保存后先检查：

```bash
python3 test_mqtt_migration.py
./run_dry_script.sh yolo/demo_pick_close.py
```

dry-run 输出 `state=DONE` 后，现场确认安全，再 live：

```bash
./run_live_script.sh yolo/demo_pick_close.py
```

如果 dry-run 失败，不要 live。先看报错，通常是路径写错、JSON 不存在、Gateway capability 没 ready。

### 16.2.2 只写一个底盘点位脚本

如果要走底盘点位：

```python
def main() -> int:
    run_nav_waypoints(SOURCE_SCRIPT, [{"index": 11, "high_precision": False}])
    return 0
```

运行：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_dry_script.sh yolo/my_nav_test.py
./run_live_script.sh yolo/my_nav_test.py
```

注意：

```text
底盘 live 前必须确认:
- 机器人不在充电/插枪状态。
- 路径上没有人、线、障碍物。
- 当前 map 和 waypoint index 是对的。
```

### 16.2.3 只写一个末端小偏移脚本

如果要做小的末端偏移：

```python
def main() -> int:
    run_ee_offsets(
        SOURCE_SCRIPT,
        offset_l=(0.0, 0.0, 0.01),
        offset_r=(0.0, 0.0, 0.01),
    )
    return 0
```

这里 `0.01` 是 1 厘米。新脚本第一次验证时，末端偏移尽量写小，不要一上来写大偏移。

### 16.3 新脚本创建后先检查

先跑迁移检查，确认没有直接 SDK 初始化/释放代码：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 test_mqtt_migration.py
```

然后 dry-run 新脚本：

```bash
./run_dry_script.sh yolo/my_new_script.py
```

dry-run 的意义：

```text
1. 检查 Python 能不能运行。
2. 检查 mqtt_common helper 能不能发任务。
3. 检查 Gateway ready/capability 是否正常。
4. 不让真机运动。
```

如果脚本需要参数，参数直接跟在后面：

```bash
./run_dry_script.sh yolo/my_new_script.py 参数1 参数2
```

dry-run 通过以后，再 live：

```bash
./run_live_script.sh yolo/my_new_script.py
```

带参数 live：

```bash
./run_live_script.sh yolo/my_new_script.py 参数1 参数2
```

live 的意义：

```text
1. 会让真实机器人运动。
2. run_live_script.sh 会自动带 live、物理确认、preflight。
3. 底盘会带 45 秒无进展保护。
4. 其它运行过程参数不需要现场手写。
```

### 16.4 子脚本路径怎么写

统一从工作区根目录写相对路径：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624

./run_dry_script.sh yolo/my_new_script.py
./run_live_script.sh yolo/my_new_script.py
```

不要这样写：

```bash
./run_live_script.sh /data/wxf/wxf/yolo/my_new_script.py
```

原因：

```text
绝对路径可能跑到原始目录。
原始目录里的脚本可能还会直接调 GDK。
新 MQTT 工作区才是迁移后的安全入口。
```

正确和错误对比：

```text
正确:
./run_live_script.sh yolo/demo_pick_close.py
./run_live_script.sh BOX_528_1/move-pick2.py
./run_live_script.sh Robot/move_ee_pose_close_2.py

错误:
python3 /data/wxf/wxf/yolo/demo_pick_close.py
python3 /data/wxf/wxf/BOX_528_1/move-pick2.py
./run_live_script.sh /data/wxf/wxf/yolo/demo_pick_close.py
```

### 16.5 如果新建的是总控脚本

总控脚本不要自己用 `subprocess` 到处跑外部命令。按现有四个总控的方式写：

```python
from mqtt_common import run_sequence

TASK_SEQUENCE = [
    "python ../BOX_528_1/move-pick2.py",
    "python move_whole_body_by_json.py ../positions/pick_standby.json",
    "python move_arm_by_json.py ../positions/pick_b_2.json",
]

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    return run_sequence(
        "yolo/my_new_task.py",
        TASK_SEQUENCE,
        Path(__file__).resolve().parent,
        execute=args.execute,
    )
```

先看计划，不运动：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624/yolo
python3 my_new_task.py
```

确认没有：

```text
blocked_external
blocked_unknown
missing_local
```

再用 live 子脚本启动器执行：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_live_script.sh yolo/my_new_task.py --execute
```

如果这个新总控以后要变成正式入口，再把它加到 `run_live_task.sh` 里取一个短名字。

总控脚本里的 `TASK_SEQUENCE` 只能写这些类型：

```text
python 本工作区里的 .py 脚本
python3 本工作区里的 .py 脚本
yolo-env/bin/python 本工作区里的视觉脚本
cp 本工作区里的文件 本工作区里的文件
mv 本工作区里的文件 本工作区里的文件
```

不要写：

```text
绝对路径到原始目录
shell 管道
sudo
systemctl
删除目录
外部网络命令
任何直接控制机器人底层服务的命令
```

### 16.6 新脚本上线前检查清单

```text
1. 文件在 /data/wxf/wxf/mqtt_gateway_workspace_20260624 里面。
2. 没有直接 import 机器人 GDK 包。
3. 没有 SDK 初始化/释放代码。
4. 所有姿态 JSON 路径指向新工作区 positions 或迁移后的相对路径。
5. main() 最后 return 0。
6. 先跑 python3 test_mqtt_migration.py。
7. 先跑 ./run_dry_script.sh。
8. dry-run 输出 state=DONE 后，现场确认安全，再跑 ./run_live_script.sh。
9. 如果包含底盘，确认机器人已经离开充电状态。
10. 如果现场没有确认 emergency_stop_pedal_fault_state=1 可接受，不要 live。
11. 如果单独跑夹爪，确认物料不会掉落。
12. 如果单独跑末端偏移，先用很小的偏移量。
```

---

## 17. 我们这套 MQTT/Gateway 服务到底是什么

这一节给脚本提供方、现场调试人员、后续维护人员看。

先用一句话讲清楚：

```text
它们写的 Python 脚本不再自己连接机器人底层 SDK。
脚本只把“我要做什么动作”通过 MQTT 发给我们的 Gateway。
Gateway 是常驻服务，它统一做 ready/capability 检查、安全门、排队、GDK 调用、结果回传和日志落盘。
```

### 17.1 当前真实服务分层

机器人上现在有三层常驻服务：

```text
1. Mosquitto MQTT Broker
   - 提供 MQTT 消息通道
   - 监听 127.0.0.1:1883

2. G2 Industrial Gateway HTTP/UI Service
   - systemd: g2-industrial-gateway.service
   - 监听 0.0.0.0:8767
   - 真正持有长期 GDK live 会话
   - 所有机器人动作最后都由它执行

3. G2 Industrial Gateway MQTT Adapter
   - systemd: g2-industrial-gateway-mqtt.service
   - 连接 MQTT broker
   - 订阅 g2/gateway/task/request
   - 把 MQTT 请求转成 HTTP 请求发给 Gateway
   - 把 Gateway 的 status/result 再发回 MQTT
```

当前真实进程形态：

```text
mosquitto
  -> 127.0.0.1:1883

python3 -m g2_industrial_gateway.server
  -> 0.0.0.0:8767
  -> backend=gdk-live
  -> allow_live=true
  -> owns GDK live session

python3 -m g2_industrial_gateway.mqtt_service
  -> broker=127.0.0.1:1883
  -> target=http
  -> gateway-url=http://127.0.0.1:8767
  -> does not own GDK session
```

注意：

```text
MQTT broker 当前只监听机器人本机 127.0.0.1:1883。
也就是说，普通现场脚本建议在机器人本机运行。
外部电脑如果要直接连 MQTT，需要另做 broker 外网监听或 SSH tunnel，不要随便改现场 broker 配置。

HTTP/UI Gateway 监听 0.0.0.0:8767，所以同网段电脑可以打开:
http://10.185.207.186:8767
```

### 17.2 代码和配置路径

Gateway 服务代码：

```text
/data/g2_industrial_gateway/current
```

当前它是一个软链接：

```text
/data/g2_industrial_gateway/current
  -> /data/g2_industrial_gateway/releases/g2_gateway_20260624_nav_live_mqtt
```

核心 Python 包：

```text
/data/g2_industrial_gateway/current/g2_industrial_gateway
```

关键文件：

```text
server.py
  HTTP/UI 服务入口。
  提供 /api/runtime、/api/ready、/api/capabilities、/api/tasks 等接口。

mqtt_service.py
  MQTT Adapter 入口。
  生产现场用 --target http，把 MQTT 请求转发给 HTTP Gateway。

mqtt_bridge.py
  MQTT topic 订阅、发布、ready/capabilities retained 消息、task result 回传。

gateway.py
  工业 Gateway 核心。
  负责 capability registry、安全门、任务队列、任务状态机、journal 落盘。

models.py
  TaskRequest、TaskRecord、TaskState、Capability 数据结构。

safety.py
  安全门。
  检查 command 是否存在、mode 是否允许、live 是否允许、confirm_physical 是否有、参数范围是否合法。

capabilities.py
  能力清单。
  定义哪些 command 支持 mock/dry_run/read_only/live。

gdk_live_backend.py
  live 真机后端。
  真正调用 Robot/Pnc/GDK，例如 nav.goto_pose、arm.move_named_pose、gripper.open。

gdk_readonly_backend.py
  只读 GDK 后端。
  读取电源、PNC task、关节、odom、预检等，不发运动命令。
```

WXF 脚本迁移工作区：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624
```

关键文件：

```text
run_live_task.sh
  四个正式总控的一条命令启动器。

run_live_script.sh
  单独跑某个子脚本的 live 启动器。

run_dry_script.sh
  单独跑某个子脚本的 dry-run 启动器。

gateway_mqtt_client.py
  一次性 MQTT 调试客户端。

mqtt_common/mqtt_common.py
  WXF 脚本调用 MQTT/Gateway 的通用库。
  run_arm_json、run_nav_waypoints、run_gripper 等 helper 都在这里。

templates/new_mqtt_child_script.py
  新建 MQTT 子脚本模板。

USAGE_GUIDE.md
  这份保姆级教程。

yolo/
  四个总控和视觉/姿态脚本的 MQTT 迁移副本。

BOX_528_1/
  底盘、上肢流程脚本的 MQTT 迁移副本。

Robot/
  夹爪、末端相关脚本的 MQTT 迁移副本。

positions/
  姿态 JSON。
```

原始脚本目录仍然在：

```text
/data/wxf/wxf/yolo
/data/wxf/wxf/BOX_528_1
/data/wxf/wxf/Robot
/data/wxf/wxf/positions
```

但这套 MQTT 改造要求：

```text
现场测试 MQTT 版本时，不直接跑原始目录脚本。
只跑 /data/wxf/wxf/mqtt_gateway_workspace_20260624 里的迁移副本。
```

### 17.3 systemd 服务文件

HTTP/GDK Gateway：

```text
/etc/systemd/system/g2-industrial-gateway.service
```

当前内容核心是：

```ini
[Unit]
Description=G2 Industrial Gateway HTTP/UI Service
After=network-online.target genie_app.service
Wants=network-online.target

[Service]
Type=simple
User=agi
Group=agi
EnvironmentFile=/data/g2_industrial_gateway/g2-industrial-gateway.env
WorkingDirectory=/data/g2_industrial_gateway/current
ExecStart=/bin/bash -lc 'source /home/agi/app/env.sh; if [ "${G2_GATEWAY_ALLOW_LIVE:-0}" = "1" ]; then live_flag=--allow-live; else live_flag=; fi; if [ "${G2_GATEWAY_ENABLE_CAMERA_SNAPSHOTS:-0}" = "1" ]; then camera_flag=--enable-camera-snapshots; else camera_flag=; fi; exec /usr/bin/python3 -m g2_industrial_gateway.server --host "$G2_GATEWAY_HTTP_HOST" --port "$G2_GATEWAY_HTTP_PORT" --journal-dir "$G2_GATEWAY_JOURNAL_DIR/http" --backend "$G2_GATEWAY_BACKEND" $live_flag $camera_flag'
Restart=on-failure
RestartSec=2
TimeoutStopSec=10
KillSignal=SIGINT
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

MQTT Adapter：

```text
/etc/systemd/system/g2-industrial-gateway-mqtt.service
```

当前内容核心是：

```ini
[Unit]
Description=G2 Industrial Gateway MQTT Adapter
After=network-online.target genie_app.service g2-industrial-gateway.service
Wants=network-online.target

[Service]
Type=simple
User=agi
Group=agi
EnvironmentFile=/data/g2_industrial_gateway/g2-industrial-gateway.env
WorkingDirectory=/data/g2_industrial_gateway/current
ExecStart=/bin/bash -lc 'source /home/agi/app/env.sh; exec /usr/bin/python3 -m g2_industrial_gateway.mqtt_service --target http --gateway-url "$G2_GATEWAY_HTTP_URL" --broker "$G2_GATEWAY_MQTT_BROKER" --port "$G2_GATEWAY_MQTT_PORT" --client-id "$G2_GATEWAY_MQTT_CLIENT_ID" --journal-dir "$G2_GATEWAY_JOURNAL_DIR/mqtt" --heartbeat-interval-s "$G2_GATEWAY_MQTT_HEARTBEAT_INTERVAL_S" --qos "$G2_GATEWAY_MQTT_QOS"'
Restart=on-failure
RestartSec=2
TimeoutStopSec=10
KillSignal=SIGINT
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

Mosquitto broker：

```text
/lib/systemd/system/mosquitto.service
```

核心启动命令：

```ini
ExecStart=/usr/sbin/mosquitto -c /etc/mosquitto/mosquitto.conf
```

### 17.4 环境文件

环境文件路径：

```text
/data/g2_industrial_gateway/g2-industrial-gateway.env
```

当前关键配置：

```bash
G2_GATEWAY_APP_DIR=/data/g2_industrial_gateway/current
G2_GATEWAY_JOURNAL_DIR=/data/g2_industrial_gateway/journal

G2_GATEWAY_BACKEND=gdk-live

G2_GATEWAY_HTTP_HOST=0.0.0.0
G2_GATEWAY_HTTP_PORT=8767
G2_GATEWAY_HTTP_URL=http://127.0.0.1:8767

G2_GATEWAY_MQTT_BROKER=127.0.0.1
G2_GATEWAY_MQTT_PORT=1883
G2_GATEWAY_MQTT_CLIENT_ID=g2-industrial-gateway
G2_GATEWAY_MQTT_QOS=1
G2_GATEWAY_MQTT_HEARTBEAT_INTERVAL_S=1.0

G2_GATEWAY_ENABLE_CAMERA_SNAPSHOTS=1
G2_GATEWAY_ALLOW_LIVE=1
```

这些值的意思：

```text
G2_GATEWAY_BACKEND=gdk-live
  HTTP Gateway 使用 live GDK 后端。

G2_GATEWAY_ALLOW_LIVE=1
  systemd 启动 HTTP Gateway 时加 --allow-live。
  这只是打开 Gateway live 总开关，不代表任何脚本都能随便动。
  每个 live 任务仍然必须 mode=live 且 confirm_physical=true。

G2_GATEWAY_HTTP_HOST=0.0.0.0
  HTTP/UI 对外监听，现场电脑可以打开网页。

G2_GATEWAY_HTTP_PORT=8767
  HTTP/UI 端口。

G2_GATEWAY_HTTP_URL=http://127.0.0.1:8767
  MQTT Adapter 在机器人本机访问 HTTP Gateway 的地址。

G2_GATEWAY_MQTT_BROKER=127.0.0.1
  MQTT Adapter 连接本机 broker。

G2_GATEWAY_MQTT_PORT=1883
  MQTT broker 端口。

G2_GATEWAY_MQTT_HEARTBEAT_INTERVAL_S=1.0
  MQTT Adapter 每 1 秒发布 heartbeat/ready 状态。

G2_GATEWAY_ENABLE_CAMERA_SNAPSHOTS=1
  HTTP Gateway 启用相机 snapshot 接口。
```

### 17.5 实际启动顺序

系统启动后大概是：

```text
1. network-online.target
2. genie_app.service
3. mosquitto.service
4. g2-industrial-gateway.service
5. g2-industrial-gateway-mqtt.service
```

`g2-industrial-gateway.service` 启动时会：

```text
1. 读取 /data/g2_industrial_gateway/g2-industrial-gateway.env。
2. cd /data/g2_industrial_gateway/current。
3. source /home/agi/app/env.sh。
4. 根据 G2_GATEWAY_ALLOW_LIVE 决定是否加 --allow-live。
5. 根据 G2_GATEWAY_ENABLE_CAMERA_SNAPSHOTS 决定是否加 --enable-camera-snapshots。
6. 启动:
   python3 -m g2_industrial_gateway.server ...
7. server.py 创建 IndustrialGateway。
8. backend=gdk-live 时创建 GdkLiveBackend。
9. GdkLiveBackend 连接并持有长期 GDK 会话。
10. HTTP 开始监听 0.0.0.0:8767。
```

`g2-industrial-gateway-mqtt.service` 启动时会：

```text
1. 读取同一个 env 文件。
2. cd /data/g2_industrial_gateway/current。
3. source /home/agi/app/env.sh。
4. 启动:
   python3 -m g2_industrial_gateway.mqtt_service --target http ...
5. mqtt_service.py 连接 127.0.0.1:1883。
6. 创建 GatewayMqttHttpBridge。
7. 订阅 task/request、task/cancel、action/request。
8. 发布 retained ready/capabilities/heartbeat。
9. 收到 MQTT task 后转发到 http://127.0.0.1:8767/api/tasks。
```

重要点：

```text
MQTT Adapter 不直接调 GDK。
它只是交通层，把 MQTT 消息转给 HTTP Gateway。
这样 GDK 长期会话只有一份，避免每个脚本重复连接/释放。
```

### 17.6 当前端口

查看命令：

```bash
ss -ltnp | grep -E ':(8767|1883)'
```

当前状态：

```text
127.0.0.1:1883
  Mosquitto MQTT broker，只监听本机。

0.0.0.0:8767
  HTTP/UI Gateway，对外监听。
```

当前进程命令形态：

```text
/usr/bin/python3 -m g2_industrial_gateway.server \
  --host 0.0.0.0 \
  --port 8767 \
  --journal-dir /data/g2_industrial_gateway/journal/http \
  --backend gdk-live \
  --allow-live \
  --enable-camera-snapshots

/usr/bin/python3 -m g2_industrial_gateway.mqtt_service \
  --target http \
  --gateway-url http://127.0.0.1:8767 \
  --broker 127.0.0.1 \
  --port 1883 \
  --client-id g2-industrial-gateway \
  --journal-dir /data/g2_industrial_gateway/journal/mqtt \
  --heartbeat-interval-s 1.0 \
  --qos 1
```

### 17.7 MQTT topic

主要任务 topic：

```text
g2/gateway/task/request
  客户端发布任务请求。

g2/gateway/task/cancel
  客户端请求取消任务。

g2/gateway/task/status
  Gateway/MQTT Adapter 发布任务状态变化。

g2/gateway/task/result
  Gateway/MQTT Adapter 发布终态结果。

g2/gateway/event/fault
  MQTT payload 错误、HTTP 转发错误、未知 topic 等故障事件。
```

状态 retained topic：

```text
g2/gateway/state/heartbeat
  retained。
  周期发布 runtime 状态，默认 1 秒一次。

g2/gateway/state/ready
  retained。
  客户端启动前先看它，ok=true 才继续。

g2/gateway/capabilities
  retained。
  客户端启动前先看它，确认 command 存在、mode 被允许。
```

动作 topic：

```text
g2/gateway/action/request
g2/gateway/action/result
```

WXF 迁移脚本主要用的是：

```text
g2/gateway/task/request
g2/gateway/task/status
g2/gateway/task/result
g2/gateway/state/ready
g2/gateway/capabilities
g2/gateway/event/fault
```

### 17.8 MQTT 任务 payload 格式

所有任务都是 JSON object，schema 是：

```json
{
  "schema": "g2.task.v1",
  "task_id": "unique-task-id",
  "command": "arm.move_named_pose",
  "mode": "dry_run",
  "args": {},
  "timeout_s": 20.0,
  "confirm_physical": false,
  "priority": 50,
  "submitted_by": "wxf-mqtt-workspace"
}
```

字段含义：

```text
schema
  固定 g2.task.v1。

task_id
  唯一任务 ID。mqtt_common 会自动生成。

command
  要执行的能力名，例如 nav.goto_pose、arm.move_named_pose、gripper.close。

mode
  mock / dry_run / read_only / live。

args
  command 参数。

timeout_s
  客户端/任务等待时间。

confirm_physical
  live 真实运动必须是 true。

priority
  当前保留字段，默认 50。

submitted_by
  谁提交的任务，WXF 脚本默认 wxf-mqtt-workspace。
```

live 运动任务必须同时满足：

```text
1. Gateway 环境 G2_GATEWAY_ALLOW_LIVE=1。
2. Gateway 以 --allow-live 启动。
3. capability 里该 command 的 modes 包含 live。
4. MQTT payload 里 mode=live。
5. MQTT payload 里 confirm_physical=true。
6. command 参数通过 safety.py 检查。
7. GDK live backend 自己的 preflight 通过。
```

少一个都会被挡住。

### 17.9 任务状态机

任务状态大概会这样走：

```text
RECEIVED
  HTTP Gateway 收到任务。

VALIDATING
  Gateway 正在做 capability 和 safety gate 检查。

QUEUED
  进入队列，等待串行执行。

RUNNING
  后端正在执行。

VERIFYING
  后端执行完，Gateway 准备收尾。

DONE
  成功终态。
```

失败/停止终态：

```text
FAILED
  执行失败，例如 GDK 调用失败、preflight 失败、导航无进展 watchdog 触发。

BLOCKED
  safety gate 拦住，例如 live 没有 confirm_physical、mode 不允许、参数越界。

CANCELED
  被取消。
```

MQTT 客户端等待的是：

```text
DONE / FAILED / BLOCKED / CANCELED
```

所以脚本不会只发不管，它会等终态结果。

### 17.10 当前已开放的 live command

当前 Gateway runtime 里 live command 是：

```text
head.set_pan_tilt
arm.move_named_pose
waist.move_named_pose
gripper.open
gripper.close
ee.relative_offset
nav.goto_pose
```

对应真实后端大概是：

```text
nav.goto_pose
  -> GdkLiveBackend._move_nav_goto_pose
  -> Pnc.normal_navi / Pnc.high_precision_navi
  -> 等 PNC task state
  -> 无进展 watchdog

head.set_pan_tilt
  -> Robot.move_head_joint

arm.move_named_pose
  -> Robot.move_arm_joint

waist.move_named_pose
  -> Robot.move_waist_joint

gripper.open / gripper.close
  -> Robot.move_ee_pos

ee.relative_offset
  -> Robot.end_effector_pose_control
```

只读 command：

```text
gdk.read_status
gdk.read_power_state
gdk.read_motion_status
gdk.read_whole_body_status
gdk.read_joint_states
gdk.read_task_state
gdk.read_odom
gdk.read_ultrasonic
nav.preflight
arm.preflight
ee.preflight
```

### 17.11 WXF 脚本怎么接入服务

WXF 子脚本不自己拼 raw MQTT，一般走：

```text
run_live_task.sh / run_live_script.sh / run_dry_script.sh
  -> python3 子脚本
  -> 子脚本 import mqtt_common helper
  -> mqtt_common.build_payload()
  -> mqtt_common.GatewayMqttClient
  -> publish g2/gateway/task/request
  -> wait g2/gateway/task/result
```

`mqtt_common` 客户端做了这些事：

```text
1. 连接 127.0.0.1:1883。
2. 订阅:
   - g2/gateway/state/ready
   - g2/gateway/capabilities
   - g2/gateway/task/status
   - g2/gateway/task/result
   - g2/gateway/event/fault
3. preflight=require 时，先要求 ready.ok=true。
4. 再检查 capability 里有没有 command，以及 mode 是否允许。
5. 发布 task/request。
6. 等待同一个 task_id 的 result。
7. 如果 result 不是 DONE，脚本退出码失败。
```

所以它们新写脚本时，不需要自己懂 MQTT topic 细节。只需要调用 helper：

```python
run_nav_waypoints(...)
run_whole_body_json(...)
run_arm_json(...)
run_waist_json(...)
run_gripper(...)
run_ee_offsets(...)
```

### 17.12 启动、停止、重启命令

只看状态：

```bash
systemctl is-active mosquitto
systemctl is-active g2-industrial-gateway.service
systemctl is-active g2-industrial-gateway-mqtt.service
```

看完整状态：

```bash
systemctl status mosquitto --no-pager -l
systemctl status g2-industrial-gateway.service --no-pager -l
systemctl status g2-industrial-gateway-mqtt.service --no-pager -l
```

启动：

```bash
sudo systemctl start mosquitto
sudo systemctl start g2-industrial-gateway.service
sudo systemctl start g2-industrial-gateway-mqtt.service
```

重启本项目服务：

```bash
sudo systemctl restart g2-industrial-gateway.service
sudo systemctl restart g2-industrial-gateway-mqtt.service
```

如果只改了 env 文件：

```bash
sudo systemctl restart g2-industrial-gateway.service g2-industrial-gateway-mqtt.service
```

如果改了 systemd unit 文件：

```bash
sudo systemctl daemon-reload
sudo systemctl restart g2-industrial-gateway.service g2-industrial-gateway-mqtt.service
```

重要边界：

```text
不要随便重启 genie_app.service。
不要随便重启 driver/controller/GDK core runtime/hardware service。
我们这套 MQTT/Gateway 原型正常只需要重启:
- g2-industrial-gateway.service
- g2-industrial-gateway-mqtt.service
```

### 17.13 日志怎么看

HTTP/GDK Gateway 日志：

```bash
journalctl -u g2-industrial-gateway.service -n 200 --no-pager
journalctl -u g2-industrial-gateway.service -f
```

MQTT Adapter 日志：

```bash
journalctl -u g2-industrial-gateway-mqtt.service -n 200 --no-pager
journalctl -u g2-industrial-gateway-mqtt.service -f
```

Mosquitto 日志：

```bash
journalctl -u mosquitto -n 100 --no-pager
```

任务 journal 落盘目录：

```text
/data/g2_industrial_gateway/journal/http/events.jsonl
/data/g2_industrial_gateway/journal/http/tasks/
```

每个 task 会有一个 JSON 快照，例如：

```text
/data/g2_industrial_gateway/journal/http/tasks/<task_id>.json
```

这些文件里能看到：

```text
task_id
command
mode
args
state
result
error
timeline
```

### 17.14 怎么确认服务健康

在机器人本机执行：

```bash
curl -s http://127.0.0.1:8767/api/runtime
curl -s http://127.0.0.1:8767/api/ready
curl -s http://127.0.0.1:8767/api/capabilities
```

当前正常时应该看到：

```text
/api/ready:
ok=true
backend=gdk-live
accepting_tasks=true
gdk_connected=true

/api/runtime:
backend.backend=gdk-live
allow_live=true
queue_depth=0
current_task=null

/api/capabilities:
nav.goto_pose modes 包含 live
arm.move_named_pose modes 包含 live
waist.move_named_pose modes 包含 live
gripper.open / gripper.close modes 包含 live
ee.relative_offset modes 包含 live
head.set_pan_tilt modes 包含 live
```

MQTT 通路 smoke：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 gateway_mqtt_client.py \
  --command gdk.read_power_state \
  --mode read_only \
  --args-json '{}' \
  --timeout-s 15 \
  --preflight require
```

成功时应该返回：

```text
state=DONE
source=gdk
```

迁移脚本检查：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 test_mqtt_migration.py
```

成功时应该返回：

```text
OK: migrated workspace python files compile and contain no direct SDK init/release tokens
```

### 17.15 如果 MQTT 没返回，按这个顺序查

第一步，看 broker：

```bash
systemctl is-active mosquitto
ss -ltnp | grep 1883
```

第二步，看 HTTP Gateway：

```bash
systemctl is-active g2-industrial-gateway.service
curl -s http://127.0.0.1:8767/api/ready
```

第三步，看 MQTT Adapter：

```bash
systemctl is-active g2-industrial-gateway-mqtt.service
journalctl -u g2-industrial-gateway-mqtt.service -n 100 --no-pager
```

第四步，看 retained topic 是否存在：

```bash
mosquitto_sub -h 127.0.0.1 -p 1883 -t 'g2/gateway/state/ready' -C 1
mosquitto_sub -h 127.0.0.1 -p 1883 -t 'g2/gateway/capabilities' -C 1
```

第五步，跑只读 smoke：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
python3 gateway_mqtt_client.py \
  --command gdk.read_power_state \
  --mode read_only \
  --args-json '{}' \
  --timeout-s 15 \
  --preflight require
```

### 17.16 它们最容易误解的点

```text
误解 1:
MQTT Adapter 会直接调 GDK。

实际:
MQTT Adapter 只转发到 HTTP Gateway。真正调 GDK 的是 HTTP Gateway 的 gdk-live backend。
```

```text
误解 2:
G2_GATEWAY_ALLOW_LIVE=1 后，所有 live 都能随便跑。

实际:
每个 live 任务还必须 capability 允许 live、payload 里 mode=live、confirm_physical=true，
并且通过 safety.py 和 live backend preflight。
```

```text
误解 3:
新脚本需要自己连接 MQTT topic。

实际:
新 WXF 子脚本一般不需要自己写 MQTT 发布/订阅，直接调用 mqtt_common helper。
```

```text
误解 4:
可以从原始目录直接 python3 跑旧脚本。

实际:
那样可能又回到每个脚本自己连接/释放底层 SDK 的旧方式。
MQTT 测试必须从 /data/wxf/wxf/mqtt_gateway_workspace_20260624 跑。
```

```text
误解 5:
MQTT broker 对外开放。

实际:
当前 broker 只监听 127.0.0.1:1883。机器人本机脚本能连；外部电脑不能直接连，除非另做配置或 tunnel。
```

### 17.17 给它们看的最短解释

如果只给脚本团队讲 1 分钟，就这么说：

```text
机器人上有一个常驻 HTTP Gateway 服务和一个 MQTT Adapter 服务。
HTTP Gateway 是真正持有 GDK live 会话的进程，端口是 8767。
MQTT Adapter 连接本机 mosquitto，端口是 1883，它只负责把 MQTT 请求转发给 HTTP Gateway。
你们的新脚本不要再 import/初始化/释放底层 SDK，只复制模板，调用 mqtt_common helper。
写完后先 python3 test_mqtt_migration.py，再 ./run_dry_script.sh，最后现场确认安全后 ./run_live_script.sh。
正式四个总控用 ./run_live_task.sh pick_b/place_b/all/pull_car。
```

---

## 18. 运行日志和问题收集

这一节是为了避免“出了问题只能复现一次给维护人员看”。

现在三个启动器都会自动记录日志：

```text
run_live_task.sh
run_live_script.sh
run_dry_script.sh
```

每次运行都会生成一个独立日志文件：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/YYYYMMDD/
```

日志文件名大概长这样：

```text
20260624_132501_live_task_pick_b_12345.log
20260624_132610_dry_script_yolo_demo_pick_close.py_12346.log
20260624_132733_live_script_BOX_528_1_move-pick2.py_12347.log
```

### 18.1 每次日志里有什么

每个运行日志会记录：

```text
1. started_at / finished_at
2. run_id
3. mode: dry_script / live_script / live_task
4. workspace
5. cwd
6. 实际执行命令
7. 当前用户和主机名
8. 关键环境变量:
   - G2_WXF_*
   - G2_GATEWAY_*
9. 服务状态:
   - mosquitto
   - g2-industrial-gateway.service
   - g2-industrial-gateway-mqtt.service
10. 端口监听:
   - 1883
   - 8767
11. Gateway /api/ready
12. Gateway /api/runtime
13. 子脚本完整 stdout/stderr 输出
14. exit_code
```

如果脚本失败，日志还会额外追加：

```text
1. Gateway /api/ready
2. Gateway /api/tasks
3. 最近 120 行 g2-industrial-gateway.service 日志
4. 最近 120 行 g2-industrial-gateway-mqtt.service 日志
5. 最近 80 行 mosquitto 日志
```

这样维护人员通常不用复现，就能看到：

```text
是脚本路径错了
还是 MQTT broker 没起来
还是 Gateway 不 ready
还是 capability 不支持
还是 safety gate 拦住
还是 GDK live backend preflight 拦住
还是真实动作执行失败
```

### 18.2 怎么看最近一次日志

进入工作区：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
```

列出最近日志：

```bash
find run_logs -type f -name '*.log' | sort | tail -n 10
```

看最近一个日志：

```bash
latest_log="$(find run_logs -type f -name '*.log' | sort | tail -n 1)"
echo "$latest_log"
tail -n 200 "$latest_log"
```

如果想实时看当前运行输出，启动器本身已经会在终端输出，同时也会写入日志。

### 18.3 出问题后不要马上反复重跑

如果某个 live 任务失败，先不要连续重跑。

正确做法：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./collect_debug_bundle.sh
```

它会生成一个压缩包，例如：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/debug_bundle_20260624_133000.tar.gz
```

把这个压缩包发给维护人员。

### 18.4 debug bundle 里有什么

`collect_debug_bundle.sh` 只做只读收集，不会让机器人运动，不会重启服务。

它会收集：

```text
README.txt
  本次 bundle 的时间、主机、工作区。

recent_run_logs/
  最近 30 个 run_logs 运行日志。

systemctl_is_active.txt
  三个服务当前是否 active。

systemctl_is_enabled.txt
  三个服务是否开机自启动。

systemctl_status_gateway.txt
  HTTP/GDK Gateway 服务状态。

systemctl_status_mqtt.txt
  MQTT Adapter 服务状态。

systemctl_status_mosquitto.txt
  MQTT broker 状态。

systemctl_cat_gateway.txt
  Gateway 和 MQTT Adapter 的 systemd unit 内容。

gateway_env.txt
  /data/g2_industrial_gateway/g2-industrial-gateway.env。

ports.txt
  1883 和 8767 端口监听情况。

gateway_ready.json
  /api/ready。

gateway_runtime.json
  /api/runtime。

gateway_capabilities.json
  /api/capabilities。

gateway_tasks.json
  /api/tasks。

mqtt_ready_retained.json
  MQTT retained ready topic。

mqtt_capabilities_retained.json
  MQTT retained capabilities topic。

journal_gateway_tail.txt
  g2-industrial-gateway.service 最近日志。

journal_mqtt_tail.txt
  g2-industrial-gateway-mqtt.service 最近日志。

journal_mosquitto_tail.txt
  mosquitto 最近日志。

workspace_tree.txt
  当前 MQTT 工作区文件列表。
```

### 18.5 维护人员优先看哪些

收到 bundle 后，优先看：

```text
1. recent_run_logs/ 里最新的 .log
2. gateway_ready.json
3. gateway_runtime.json
4. gateway_capabilities.json
5. gateway_tasks.json
6. journal_gateway_tail.txt
7. journal_mqtt_tail.txt
```

如果是脚本自己失败，通常最新 `.log` 里已经有完整错误。

如果是服务问题，看：

```text
systemctl_status_gateway.txt
systemctl_status_mqtt.txt
journal_gateway_tail.txt
journal_mqtt_tail.txt
```

如果是 MQTT 连接问题，看：

```text
systemctl_status_mosquitto.txt
ports.txt
mqtt_ready_retained.json
mqtt_capabilities_retained.json
```

如果是 live 被挡住，看：

```text
gateway_capabilities.json
gateway_tasks.json
最新 .log 里的 safety_decision / error / preflight
```

### 18.6 日志不会替代安全确认

日志是为了快速排查问题，不是为了自动绕过安全。

以下情况仍然不要 live：

```text
机器人还在充电/插枪。
运动区域有人或障碍物。
当前姿态不确定。
夹爪里有没有物料不确定。
现场没有确认 emergency_stop_pedal_fault_state=1 是可接受的已知状态。
```

日志会帮助我们知道问题在哪里，但不会替现场判断安全。

## 19. 这次新增的优化工具怎么用

这一节是给现场人员和维护人员看的。

核心原则：

```text
正常运行：
  用 run_live_task.sh 或 run_live_script.sh。

运行前检查：
  用 preflight_live.sh。

出问题后：
  先 analyze_last_run.sh，再 collect_debug_bundle.sh。

不要反复重跑失败的 live 任务。
```

### 19.1 一屏查看当前系统状态：status.sh

命令：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./status.sh
```

它不会让机器人运动。

它会显示：

```text
1. 当前工作区路径
2. 三个服务是否 active:
   - mosquitto
   - g2-industrial-gateway.service
   - g2-industrial-gateway-mqtt.service
3. 1883 / 8767 端口监听情况
4. Gateway ready/runtime 摘要
5. live capability 是否齐全
6. 最近几次 runs.jsonl 运行索引
7. 最近一个 run log 路径
```

什么时候用：

```text
1. 现场说“脚本连不上 MQTT”时。
2. 现场说“Gateway 不 ready”时。
3. 每次大任务前想快速看服务状态时。
```

### 19.2 live 前只读预检：preflight_live.sh

命令：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./preflight_live.sh
```

它不会让机器人运动。

它会检查：

```text
1. mosquitto 是否 active。
2. HTTP Gateway 是否 active。
3. MQTT Adapter 是否 active。
4. 1883 / 8767 端口是否正常。
5. /api/ready 是否 ok。
6. /api/runtime 是否是 gdk-live。
7. /api/capabilities 是否包含现场需要的 live 能力。
8. MQTT retained ready/capabilities topic 是否存在。
9. 机器人只读 power/task 状态。
10. nav.preflight。
11. arm.preflight。
```

终端只显示摘要，完整 JSON 会保存到：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/preflight/preflight_live_时间_raw/
```

如果维护人员需要看完整机器人只读返回值，就看这个 `raw_json_dir`。

结果只有两类：

```text
FINAL: PASS
  说明服务、Gateway、capability、只读预检通过。
  这不等于可以无脑运动，仍然要现场确认安全。

FINAL: BLOCKED
  说明有明确阻塞项。
  不要 live，先看它打印的 BLOCKED 行。
```

注意：

```text
preflight_live.sh 是“运行前拦截明显问题”，不是“保证动作一定成功”。
它不会替代现场人员看周围是否有人、是否有障碍物、夹爪是否夹物料。
```

### 19.3 每次运行自动生成 runs.jsonl

所有启动器都会写：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/runs.jsonl
```

每一行是一条 JSON，里面有：

```text
run_id
mode
label
started_at
finished_at
exit_code
cwd
command
log_file
```

看最近 10 次：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
tail -n 10 run_logs/runs.jsonl
```

这有什么用：

```text
以前现场说“刚才失败了”，维护人员还要猜是哪次。
现在直接看 runs.jsonl，就能定位到那次 log_file。
```

### 19.4 自动分析最近一次失败：analyze_last_run.sh

命令：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./analyze_last_run.sh
```

指定某个日志：

```bash
./analyze_last_run.sh run_logs/20260624/某个日志.log
```

它不会让机器人运动。

它会给一个分类，例如：

```text
TEMPLATE_NOT_EDITED
SCRIPT_OR_FILE_PATH_ERROR
MQTT_BROKER_OR_NETWORK_ERROR
GATEWAY_NOT_READY
CAPABILITY_OR_MODE_ERROR
SAFETY_GATE_BLOCKED
ROBOT_CHARGING_BLOCKER
ROBOT_PREFLIGHT_BLOCKED
NAV_NO_PROGRESS_WATCHDOG
GDK_OR_BACKEND_ERROR
VISION_OR_CAMERA_ERROR
UNKNOWN
```

现场人员看到分类后怎么做：

```text
TEMPLATE_NOT_EDITED:
  你跑的是模板本身。先复制模板，改 main()，再跑复制出来的脚本。

SCRIPT_OR_FILE_PATH_ERROR:
  脚本路径或 JSON 路径错了。检查是否在 MQTT 工作区里。

MQTT_BROKER_OR_NETWORK_ERROR:
  先跑 ./status.sh，看 mosquitto 和 1883。

GATEWAY_NOT_READY:
  先跑 ./status.sh，看 Gateway ready/runtime。

CAPABILITY_OR_MODE_ERROR:
  这个命令当前 Gateway 没开放对应模式，需要维护人员看 capabilities。

SAFETY_GATE_BLOCKED:
  安全门挡住了，不要绕过。看日志里的 safety_decision/error。

ROBOT_CHARGING_BLOCKER:
  机器人还在充电或插枪状态。退出充电状态后重新 preflight。

ROBOT_PREFLIGHT_BLOCKED:
  nav/arm/gripper/waist 预检有问题，先处理现场状态。

NAV_NO_PROGRESS_WATCHDOG:
  底盘任务启动后没有进展。检查路线、障碍物、地图、里程计、PNC 状态。

GDK_OR_BACKEND_ERROR:
  Gateway 或 GDK live backend 报错。打 debug bundle 发维护人员。

VISION_OR_CAMERA_ERROR:
  相机、YOLO、模型、图片输入或视觉脚本有问题。
```

### 19.5 一键打包问题现场：collect_debug_bundle.sh

命令：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./collect_debug_bundle.sh
```

它不会让机器人运动，不会重启服务。

现在 bundle 会额外包含：

```text
workspace_status.txt
  ./status.sh 输出。

last_run_analysis.txt
  ./analyze_last_run.sh 输出。

runs.jsonl
  每次运行索引。

VERSION
  当前 MQTT 工作区版本。

RELEASE_NOTES.md
  当前版本做过哪些优化。

preflight/
  最近几次 preflight_live.sh 的摘要日志和原始 JSON。
```

现场人员只需要把最后打印的 `.tar.gz` 发给维护人员。

脚本还会更新一个固定入口：

```text
/data/wxf/wxf/mqtt_gateway_workspace_20260624/run_logs/latest_debug_bundle.tar.gz
```

如果不想找最新文件名，也可以直接发这个软链接指向的压缩包。

### 19.6 清理旧日志：cleanup_run_logs.sh

默认只预览，不删除：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./cleanup_run_logs.sh
```

确认要删旧日志时：

```bash
./cleanup_run_logs.sh --execute
```

默认策略：

```text
保留最近 30 天 .log。
保留最新 100 个 debug bundle。
```

想改保留时间：

```bash
G2_WXF_LOG_RETENTION_DAYS=45 \
G2_WXF_KEEP_DEBUG_BUNDLES=200 \
./cleanup_run_logs.sh --execute
```

注意：

```text
不要手工 rm -rf run_logs。
如果现场出过问题，先 collect_debug_bundle.sh，再清理。
```

### 19.7 查看或取消当前 Gateway task：cancel_current_task.sh

只查看，不取消：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./cancel_current_task.sh
```

现场确认必须取消当前 Gateway task 时：

```bash
./cancel_current_task.sh --confirm-cancel
```

注意：

```text
默认不取消。
加 --confirm-cancel 才会调用 Gateway cancel 接口。
它不直接写底层控制器，不直接改安全逻辑。
```

### 19.8 新建脚本时优先用这些模板

现在有四个模板：

```text
templates/new_mqtt_child_script.py
  综合模板，包含所有 helper 示例。

templates/new_nav_script.py
  只做底盘导航的新脚本模板。

templates/new_arm_pose_script.py
  只做头、腰、双臂、夹爪、末端小偏移的新脚本模板。

templates/new_sequence_task.py
  新总控模板，把多个已经迁移好的子脚本串起来。
```

新建一个底盘脚本：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
cp templates/new_nav_script.py yolo/my_nav_task.py
python3 test_mqtt_migration.py
./run_dry_script.sh yolo/my_nav_task.py
```

确认 `dry_run` 没问题，现场安全确认后：

```bash
./run_live_script.sh yolo/my_nav_task.py
```

新建一个姿态脚本：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
cp templates/new_arm_pose_script.py yolo/my_pose_task.py
python3 test_mqtt_migration.py
./run_dry_script.sh yolo/my_pose_task.py
```

现场安全确认后：

```bash
./run_live_script.sh yolo/my_pose_task.py
```

新建一个总控：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
cp templates/new_sequence_task.py yolo/my_sequence.py
cd yolo
python3 my_sequence.py
```

上面只打印计划，不执行。

确认计划没问题后，可以通过根目录启动器 live：

```bash
cd /data/wxf/wxf/mqtt_gateway_workspace_20260624
./run_live_script.sh yolo/my_sequence.py --execute
```

### 19.9 这次明确不做的事情

为了现场稳定，这次没有做这些事：

```text
1. 没有修改原始目录脚本。
2. 没有把 MQTT broker 开放到外网。
3. 没有做 live 失败自动重试。
4. 没有让子脚本重新连接底层机器人 SDK。
5. 没有改急停、torque、velocity、joint limit、安全门等底层安全逻辑。
```

原因：

```text
live 自动重试在工业现场风险很高。
第一次失败后，必须先看日志、看 preflight、看现场，再决定是否重跑。
```
