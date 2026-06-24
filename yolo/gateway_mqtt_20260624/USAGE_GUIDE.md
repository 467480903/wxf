# G2 yolo 脚本 MQTT/Gateway 使用保姆级教程

本文档给现场同事使用。目标是把 `/data/wxf/wxf/yolo` 里原来直接调用
机器人 SDK/GDK 的脚本，切到我们的 MQTT/Gateway 服务上，避免每个脚本反复
`import agibot_gdk`、`gdk_init()`、`gdk_release()`。

## 0. 先记住一句话

以后不要在原目录直接跑会动机器人的旧脚本：

```bash
cd /data/wxf/wxf/yolo
python3 move_arm_by_json.py ../positions/pick_b_2.json
```

上面这种是旧路径，会继续走 GDK 初始化和释放。

要跑新适配脚本，必须进入新目录：

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
python3 move_arm_by_json.py ../positions/pick_b_2.json
```

新目录名字：

```text
/data/wxf/wxf/yolo/gateway_mqtt_20260624
```

原目录没有被修改：

```text
/data/wxf/wxf/yolo
```

## 1. 这套改动解决什么问题

旧方式：

```text
现场脚本 -> import agibot_gdk -> gdk_init -> Robot()/Camera() -> 动作/读相机 -> gdk_release
```

问题是每个脚本都重复初始化和释放 GDK，多个小脚本串起来时会浪费大量时间。

新方式：

```text
现场脚本 -> gateway_mqtt_client.py -> MQTT broker -> Gateway 服务 -> 统一执行/校验/返回结果
```

脚本本身不再直接碰 GDK。脚本只提交任务，网关统一处理。

当前安全状态：

```text
运动能力默认 dry_run/mock
真实动作 live 没有打开
测试结果里 executed=false 是正确现象
```

这意味着现在可以验证调用链、参数和任务拆分，但不会真实动机器人。

## 2. 新目录里有哪些重要文件

进入目录：

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
```

核心文件：

```text
gateway_mqtt_client.py      # 通用 MQTT 客户端，负责发任务、等结果
gateway_compat.py           # 给旧脚本用的兼容工具函数
gateway_sequence_runner.py  # 安全序列执行器，默认只打印计划
test_gateway_mqtt_migration.py
MIGRATION_REPORT.md
USAGE_GUIDE.md
```

已经适配成 MQTT/Gateway 的脚本：

```text
move_arm_by_json.py
move_whole_body_by_json.py
offset_move_common.py
move_ee_pose_open_05.py
move_ee_pose_right_half.py
correct_waist.py
cam_get_head.py
record_camera.py
camera_web_viewer.py
camera_web_viewer_with_save.py
00.py
all.py
task_all.py
task_all_pick_b.py
task_all_place_b.py
task_all_pull_car.py
```

仍然保留的纯视觉/旧 MQTT 脚本：

```text
yolo.py
yolo_depth.py
yolo_mqtt.py
listen_mqtt.py
```

这些脚本本身没有直接 GDK 初始化，所以没有强行改掉。注意：如果后面希望
`yolo_mqtt.py` 直接驱动机器人动作，也应该改成提交 `g2.task.v1` 到
Gateway，而不是继续用旧 topic 做动作触发。

## 3. 第一次使用前先做 3 个检查

### 3.1 确认进入的是新目录

```bash
pwd
```

期望输出：

```text
/data/wxf/wxf/yolo/gateway_mqtt_20260624
```

如果输出是：

```text
/data/wxf/wxf/yolo
```

那就是原目录，先不要跑运动脚本。

### 3.2 确认新脚本里没有直接 GDK 入口

```bash
grep -RIn -E 'agibot_gdk|gdk_init|gdk_release' --include='*.py' .
```

期望结果：

```text
无输出
```

也可以直接跑：

```bash
python3 test_gateway_mqtt_migration.py
```

期望输出：

```text
OK: top-level migrated python files compile and do not contain direct SDK init/release tokens
```

### 3.3 确认 MQTT/Gateway 通路可用

```bash
python3 gateway_mqtt_client.py \
  --command gdk.read_power_state \
  --mode read_only \
  --args-json '{}' \
  --timeout-s 10
```

期望看到 JSON 里有：

```text
"state": "DONE"
```

这一步是只读检查，不会动机器人。

## 4. 最常用命令

### 4.1 跑一个手臂 JSON 姿态 dry-run

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
python3 move_arm_by_json.py ../positions/pick_b_2.json
```

内部会提交：

```text
command = arm.move_named_pose
mode    = dry_run
```

期望结果：

```text
"state": "DONE"
"executed": false
```

说明：

- `DONE` 表示 MQTT/Gateway 调用链成功。
- `executed=false` 表示没有真实动机器人。
- `../positions/pick_b_2.json` 可以保持原来的写法，新兼容层会按原 yolo 目录语义解析。

### 4.2 跑一个全身 JSON 姿态 dry-run

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
python3 move_whole_body_by_json.py ../positions/pick_standby.json
```

内部会拆成 3 个 Gateway 任务：

```text
head.set_pan_tilt
waist.move_named_pose
arm.move_named_pose
```

每个任务都应该返回：

```text
"state": "DONE"
"executed": false
```

### 4.3 跑一个末端相对偏移 dry-run

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
python3 offset_move_forward_001.py
```

内部会走：

```text
offset_move_forward_001.py
  -> offset_move_common.run_offset(...)
  -> ee.relative_offset
```

左右手各提交一个 `ee.relative_offset` dry-run 任务。

常见 offset 脚本：

```text
offset_move_forward_001.py
offset_move_forward_002.py
offset_move_forward_006.py
offset_move_forward_009.py
offset_move_backward_002.py
offset_move_left_002.py
offset_move_left_025.py
offset_move_downward_002.py
offset_move_downward_004.py
offset_move_upward_002.py
offset_move_upward_015.py
offset_move_pull_back.py
offset_move_horizon.py
offset_move_vertical.py
offset_move_car_grab.py
```

### 4.4 跑夹爪打开 dry-run

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
python3 move_ee_pose_open_05.py
```

内部提交：

```text
gripper.open side=right
gripper.open side=left
```

右半开/左保持的旧脚本：

```bash
python3 move_ee_pose_right_half.py
```

### 4.5 跑腰部视觉校正 dry-run

前提是当前目录有 `yolo_depth_result.json`，并且里面有：

```json
{
  "slope": {
    "angle_rad": 0.123
  }
}
```

运行：

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
python3 correct_waist.py
```

内部提交：

```text
waist.move_named_pose
```

注意：旧脚本会读当前腰部关节再直接动 `idx05_body_joint5`。新脚本不会自己读/写 GDK，
只是把校正意图提交到 Gateway dry-run。

### 4.6 读取头部相机快照

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
python3 cam_get_head.py
```

新脚本不会本地打开 `agibot_gdk.Camera()`，而是读 Gateway HTTP：

```text
http://127.0.0.1:8767/api/cameras/head_rgb/snapshot.jpg
http://127.0.0.1:8767/api/cameras/head_depth/snapshot.jpg
```

输出文件：

```text
head.jpg
head_depth.jpg
```

如果深度相机没开，RGB 成功、深度失败也可以接受，脚本会打印原因。

### 4.7 查看相机配置

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
python3 camera_web_viewer.py --check
```

它会打印 Gateway UI 和相机接口配置。

## 5. 总控序列脚本怎么用

总控脚本包括：

```text
all.py
task_all.py
task_all_pick_b.py
task_all_place_b.py
task_all_pull_car.py
```

### 5.1 默认只打印计划，不执行

比如：

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
python3 task_all_pick_b.py
```

期望输出类似：

```text
# task_all_pick_b.py
# steps=10, mode=dry-run plan
[01/10] blocked_external: python ../BOX_528_1/move-pick2.py
[02/10] local_python: python move_whole_body_by_json.py ../positions/pick_b_watch.json
[03/10] local_python: python move_whole_body_by_json.py ../positions/pick_b_1.json
[04/10] local_python: python move_arm_by_json.py ../positions/pick_b_2.json
[05/10] blocked_external: python ../Robot/move_ee_pose_close_2.py
```

含义：

- `local_python`：新目录内的迁移脚本，可以通过 Gateway dry-run 执行。
- `vision_python`：视觉脚本，会用原 yolo 虚拟环境跑。
- `local_file_op`：本地 `cp` / `mv`。
- `blocked_external`：外部旧运动脚本，被拦截。

### 5.2 为什么会有 blocked_external

例如：

```text
python ../BOX_528_1/move-pick2.py
python ../Robot/move_ee_pose_close_2.py
```

这些脚本在新目录外面，里面可能仍然直接调 GDK。如果让总控继续执行这些路径，
就又绕回旧模式，时间也省不下来，还可能触发真实动作。

所以现在默认拦截它们是正确的。

### 5.3 什么时候可以用 --execute

命令：

```bash
python3 task_all_pick_b.py --execute
```

规则：

- 遇到 `local_python` 会执行新目录里的迁移脚本。
- 遇到 `vision_python` 会执行视觉脚本。
- 遇到 `local_file_op` 会执行本地 copy/move。
- 遇到 `blocked_external` 会停止，不会继续。

当前建议：

```text
先不要把 task_all*.py 当完整真实流程跑。
先用默认计划模式检查序列。
外部旧脚本迁移完以后，再考虑 --execute。
```

## 6. 如果他们要写新的脚本，应该怎么写

不要写：

```python
import agibot_gdk

agibot_gdk.gdk_init()
robot = agibot_gdk.Robot()
robot.move_arm_joint(...)
agibot_gdk.gdk_release()
```

应该写成：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gateway_compat import require_done, safe_motion_mode, submit_task


def main() -> int:
    result = submit_task(
        "ee.relative_offset",
        {
            "side": "left",
            "dx_m": 0.01,
            "dy_m": 0.0,
            "dz_m": 0.0,
            "frame": "tool",
        },
        mode=safe_motion_mode(),
        timeout_s=10.0,
    )
    require_done(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

如果要提交手臂姿态：

```python
from gateway_compat import require_done, submit_task

result = submit_task(
    "arm.move_named_pose",
    {
        "pose": "my_pose",
        "joint_positions_rad": [0.0] * 14,
        "joint_velocities_radps": [0.2] * 14,
    },
    mode="dry_run",
    timeout_s=20.0,
)
require_done(result)
```

如果要直接用通用 CLI 提交：

```bash
python3 gateway_mqtt_client.py \
  --command ee.relative_offset \
  --mode dry_run \
  --args-json '{"side":"left","dx_m":0.01,"dy_m":0.0,"dz_m":0.0}' \
  --timeout-s 10
```

## 7. MQTT 任务格式是什么

脚本最终发出去的 payload 类似：

```json
{
  "schema": "g2.task.v1",
  "task_id": "arm-move_named_pose-xxx",
  "command": "arm.move_named_pose",
  "mode": "dry_run",
  "args": {
    "pose": "arm_json_pick_b_2",
    "joint_positions_rad": [1.4, -1.5]
  },
  "confirm_physical": false,
  "submitted_by": "yolo-gateway-mqtt",
  "timeout_s": 20.0
}
```

MQTT topic：

```text
request:      g2/gateway/task/request
status:       g2/gateway/task/status
result:       g2/gateway/task/result
ready:        g2/gateway/state/ready
capabilities: g2/gateway/capabilities
fault:        g2/gateway/event/fault
```

脚本会先等：

```text
g2/gateway/state/ready
g2/gateway/capabilities
```

再检查：

```text
这个 command 是否存在
这个 mode 是否被允许
```

通过后才发布 request。

## 8. 环境变量

正常不用改。默认值如下：

```bash
export G2_GATEWAY_MQTT_BROKER=127.0.0.1
export G2_GATEWAY_MQTT_PORT=1883
export G2_GATEWAY_HTTP_URL=http://127.0.0.1:8767
export G2_YOLO_GATEWAY_MODE=dry_run
export G2_YOLO_GATEWAY_PREFLIGHT=require
export G2_YOLO_GATEWAY_TIMEOUT_S=15
```

说明：

- `G2_GATEWAY_MQTT_BROKER`：MQTT broker 地址，机器人本机默认 `127.0.0.1`。
- `G2_GATEWAY_MQTT_PORT`：MQTT 端口，默认 `1883`。
- `G2_GATEWAY_HTTP_URL`：Gateway HTTP/UI 地址，默认 `http://127.0.0.1:8767`。
- `G2_YOLO_GATEWAY_MODE`：新迁移脚本默认 `dry_run`。
- `G2_YOLO_GATEWAY_PREFLIGHT`：默认 `require`，会要求 ready/capabilities retained 消息存在。
- `G2_YOLO_GATEWAY_TIMEOUT_S`：默认等待结果超时时间。

不要这样做：

```bash
export G2_YOLO_GATEWAY_MODE=live
```

当前迁移目录会拒绝 `live`，因为真实动作还没有在 Gateway live binding 里完成审计。

## 9. 怎么确认服务还活着

只读检查：

```bash
systemctl is-active mosquitto
systemctl is-active g2-industrial-gateway-mqtt.service
systemctl is-active g2-industrial-gateway.service
```

HTTP 检查：

```bash
curl -s http://127.0.0.1:8767/api/health
curl -s http://127.0.0.1:8767/api/capabilities
curl -s http://127.0.0.1:8767/api/cameras
```

MQTT/Gateway 一步检查：

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
python3 gateway_mqtt_client.py --command gdk.read_power_state --mode read_only --args-json '{}'
```

## 10. 常见问题和处理

### 10.1 `MQTT connect timed out`

含义：脚本连不上 MQTT broker。

检查：

```bash
systemctl is-active mosquitto
```

如果 broker 不在本机，临时指定：

```bash
G2_GATEWAY_MQTT_BROKER=机器人IP python3 gateway_mqtt_client.py \
  --command gdk.read_power_state \
  --mode read_only \
  --args-json '{}'
```

### 10.2 `timed out waiting for retained ready topic`

含义：MQTT broker 能连上，但 Gateway MQTT bridge 没有发布 ready retained 消息。

检查：

```bash
systemctl is-active g2-industrial-gateway-mqtt.service
systemctl is-active g2-industrial-gateway.service
```

不要急着用 `--preflight skip`。`skip` 只能临时排查，正常现场流程应该保持 `require`。

### 10.3 `capability not advertised by gateway`

含义：脚本提交的 command 网关还没注册。

例如脚本提交：

```text
arm.some_new_command
```

但 `/api/capabilities` 没有这个能力，就会失败。

处理方式：

```bash
curl -s http://127.0.0.1:8767/api/capabilities
```

确认 command 名字是否存在。

### 10.4 `mode 'live' not advertised`

含义：这个能力当前不支持 live。

现在运动相关能力大多只有：

```text
mock
dry_run
```

所以用：

```bash
python3 xxx.py
```

不要强制 live。

### 10.5 `找不到 JSON 文件`

确认你在新目录：

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
```

再跑：

```bash
python3 move_arm_by_json.py ../positions/pick_b_2.json
```

新兼容层会按以下顺序找相对路径：

```text
当前工作目录
gateway_mqtt_20260624
原 yolo 目录
```

如果还找不到，说明文件本身不存在或路径拼错。

### 10.6 `blocked_external`

这是总控序列脚本故意拦截旧外部脚本，不是 bug。

例如：

```text
python ../BOX_528_1/move-pick2.py
```

如果让它执行，就可能回到旧 GDK 脚本。正确处理是把对应外部脚本也迁移成 Gateway
wrapper，放进新目录或新增 Gateway capability。

### 10.7 返回 `DONE` 但 `executed=false`

这是当前正确结果。

含义：

```text
Gateway 收到任务
参数通过检查
dry-run backend 处理完成
没有真实动作
```

## 11. 什么时候才能真实动作

当前不要把这套脚本当成真实动作执行入口。

要进入真实动作，至少需要同时满足：

1. Gateway 后端已经为对应 command 补齐 audited live binding。
2. `/api/capabilities` 里对应 command 的 `modes` 包含 `live`。
3. Gateway 和 runner 的 motion/live 开关被现场确认后打开。
4. David 明确批准具体命令和风险。
5. 机器人已完成现场安全检查，机械臂回 home，急停/障碍/人员位置确认。

在这些条件之前，新目录只用于：

```text
验证参数
验证 MQTT/Gateway 通路
验证序列拆分
确认脚本不再直接调用 GDK
```

## 12. 给现场同事的最短操作流程

每天第一次用：

```bash
cd /data/wxf/wxf/yolo/gateway_mqtt_20260624
pwd
python3 test_gateway_mqtt_migration.py
python3 gateway_mqtt_client.py --command gdk.read_power_state --mode read_only --args-json '{}'
```

看一个序列会做什么：

```bash
python3 task_all_pick_b.py
```

单独测试手臂 JSON：

```bash
python3 move_arm_by_json.py ../positions/pick_b_2.json
```

单独测试全身 JSON：

```bash
python3 move_whole_body_by_json.py ../positions/pick_standby.json
```

单独测试末端偏移：

```bash
python3 offset_move_forward_001.py
```

看相机接口：

```bash
python3 camera_web_viewer.py --check
```

只要还没进入 live 审计和现场批准阶段，看到 `executed=false` 就是正确结果。

## 13. 本次已验证结果

已经在机器人上验证过：

```text
python3 test_gateway_mqtt_migration.py
结果: OK

python3 gateway_mqtt_client.py --command gdk.read_power_state --mode read_only --args-json '{}' --timeout-s 10
结果: DONE

python3 offset_move_forward_001.py
结果: left/right ee.relative_offset DONE, executed=false

python3 move_arm_by_json.py ../positions/pick_b_2.json
结果: arm.move_named_pose DONE, executed=false

python3 move_whole_body_by_json.py ../positions/pick_standby.json
结果: head/waist/arm 三个子任务 DONE, executed=false

python3 camera_web_viewer.py --check
结果: /api/cameras 返回配置
```

结论：

```text
新目录脚本已经不再直接 import/init/release GDK。
脚本后续应通过 MQTT/Gateway 调用。
当前只验证 dry-run/mock，不执行真实机器人动作。
```
