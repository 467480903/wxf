1.调用/data/wxf/wxf/yolo/cam_get_head_send.py，等待/data/wxf/wxf/yolo/yolo_depth_result.json更新
2.从/data/wxf/wxf/yolo/yolo_depth_result.json读取line_center, horizontal_offset_px, direction, slope, angle_rad, angle_deg, depth
3.读取angle_deg，大于0.6右转0.1rad，小于-0.6左转0.1rad，让其在-0.6到0.6中间为止
4.读取horizontal_offset_px，大于30向右移动（horizontal_offset_px/1.86）mm，小于-30向左移动（horizontal_offset_px/0.5）mm
在本文件夹中创建一个python脚本，实现以上流程


统一用mqtt报文控制机器人运动：

G2 Minth App 服务程序

监听 MQTT topic /G2_minth_app，根据收到的 JSON 命令执行对应动作：
  - WBC                     : 从 datas/joints/WBC/  读取 JSON，控制全身关节
  - arms                    : 从 datas/joints/arms/ 读取 JSON，仅控制双臂
  - left                    : 从 datas/joints/left/ 读取 JSON，仅控制左臂
  - right                   : 从 datas/joints/right/读取 JSON，仅控制右臂
  - head                    : 从 datas/joints/head/ 读取 JSON，仅控制头部
  - waist                   : 从 datas/joints/waist/读取 JSON，仅控制腰部
  - tts                     : TTS 语音播报
  - offset_move             : 末端执行器相对移动（单位：毫米）
  - grab                    : 控制左右夹爪开合
  - cam_head                : 拍摄头部相机并通过 TCP 发送给检测服务
  - go                      : 导航到指定地图点位（nav.go）
  - go_rel                  : 底盘相对运动（nav.go_rel）
  - joint                   : 单关节控制（增量微调或直接运动到角度）

注意：数据保存（save_joints / save_position）已转移到 g2_minth_data_service.py

状态管理：
  - 任意时刻只能执行一个命令，执行期间 state="busy"，新命令将被拒绝
  - 命令执行完成后，state 恢复为 "idle"
  - 每条命令执行完成后，都会向 /G2_minth_app_done 发布 {"cmd": "done"}

命令格式示例：
  {"cmd": "WBC",   "data": "hold"}          # 加载 datas/joints/WBC/hold.json
  {"cmd": "arms",  "data": "hold"}          # 加载 datas/joints/arms/hold.json
  {"cmd": "left",  "data": "hold"}          # 加载 datas/joints/left/hold.json
  {"cmd": "WBC",   "data": {"idx11_head_joint1": 0.1, ...}}  # 内联关节角（实时示教）
  {"cmd": "save_joints", "type": "WBC", "name": "hold", "data": {"idx11_head_joint1": 0.1, ...}}
  {"cmd": "tts",                     "data": "你好，我是精灵G2"}
  {"cmd": "offset_move",             "data": {"lx": 20, "ly": 0, "lz": 0, "rx": 0, "ry": 0, "rz": 0}}
  {"cmd": "grab",                    "data": {"left": 0.5, "right": 0.5}}
  {"cmd": "cam_head"}
  {"cmd": "go",                      "data": 9}
  {"cmd": "go_rel",                  "data": {"x": 1, "y": 1, "yaw_rad": 0.1}}
  {"cmd": "joint", "data": {"name": "idx11_head_joint1", "offset": 0.01}}   # 增量微调
  {"cmd": "joint", "data": {"name": "idx11_head_joint1", "value": 0.0}}     # 运动到指定角度