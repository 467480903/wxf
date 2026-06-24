import cv2
import numpy as np
from ultralytics import YOLO
import paho.mqtt.client as mqtt
import json

# ========== MQTT 配置 ==========
MQTT_BROKER = "localhost"       # MQTT Broker 地址，请根据实际修改
MQTT_PORT = 1883                # MQTT 端口
MQTT_TOPIC = "/pick_standby/caculate_offset/"
MQTT_CLIENT_ID = "yolo_offset_publisher"

# ========== MQTT 发布函数 ==========
def publish_result(mqtt_client, data: dict):
    """将结果以 JSON 格式发布到 MQTT topic"""
    payload = json.dumps(data, ensure_ascii=False)
    result = mqtt_client.publish(MQTT_TOPIC, payload, qos=2)
    print(f"[MQTT] 已发布到 {MQTT_TOPIC}")
    print(f"[MQTT] Payload: {payload}")
    return result

# ========== 加载预训练模型 ==========
model = YOLO('0613.pt')

# ========== 目标检测 ==========
results = model('./head.jpg')

# 获取原始图像
img = results[0].orig_img.copy()
img_h, img_w = img.shape[:2]
print(f"图像尺寸: {img_h} x {img_w}")

# 图像垂直中线的 x 坐标
img_center_x = img_w / 2

# 获取所有检测框
boxes = results[0].boxes

# 筛选类别为 'b' 的检测框（根据实际类别ID修改）
# 假设 'b' 的类别ID已知，例如 class_id = 0，请根据实际情况修改
target_class_id = None

# 找到类别名称对应的ID
names = results[0].names
for class_id, class_name in names.items():
    if class_name == 'b':
        target_class_id = class_id
        break

# 筛选目标框
target_boxes = []
if target_class_id is not None:
    for box in boxes:
        if int(box.cls[0]) == target_class_id:
            # xyxy格式: [x1, y1, x2, y2]
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            # 计算框的中心点
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            target_boxes.append((center_x, center_y, x1, y1, x2, y2))

# ========== 准备 MQTT 连接 ==========
mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID)
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_connected = True
    print(f"[MQTT] 已连接到 {MQTT_BROKER}:{MQTT_PORT}")
except Exception as e:
    print(f"[MQTT] 连接失败: {e}")
    mqtt_connected = False

# ========== 如果有2个b目标框 ==========
if len(target_boxes) == 2:
    b1_cx, b1_cy, b1_x1, b1_y1, b1_x2, b1_y2 = target_boxes[0]
    b2_cx, b2_cy, b2_x1, b2_y1, b2_x2, b2_y2 = target_boxes[1]

    # 画两个目标框
    cv2.rectangle(img, (int(b1_x1), int(b1_y1)), (int(b1_x2), int(b1_y2)), (0, 255, 0), 2)
    cv2.rectangle(img, (int(b2_x1), int(b2_y1)), (int(b2_x2), int(b2_y2)), (0, 255, 0), 2)

    # 以2个b的中心点画一条线
    cv2.line(img, (int(b1_cx), int(b1_cy)), (int(b2_cx), int(b2_cy)), (0, 0, 255), 2)

    # 计算这条线的中心点
    line_center_x = (b1_cx + b2_cx) / 2
    line_center_y = (b1_cy + b2_cy) / 2

    # 标出这条线的中心点
    cv2.circle(img, (int(line_center_x), int(line_center_y)), 8, (255, 0, 0), -1)
    cv2.putText(img, f'({line_center_x:.1f}, {line_center_y:.1f})',
                (int(line_center_x) + 10, int(line_center_y) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # 标出两个b的中心点
    cv2.circle(img, (int(b1_cx), int(b1_cy)), 5, (0, 255, 255), -1)
    cv2.circle(img, (int(b2_cx), int(b2_cy)), 5, (0, 255, 255), -1)

    # ===== 计算图像垂直中线到线段中心点的水平偏移量 =====
    h_offset = line_center_x - img_center_x  # 正值=偏右，负值=偏左
    print(f"线段中心点: ({line_center_x:.2f}, {line_center_y:.2f})")
    print(f"图像垂直中线 x: {img_center_x:.2f}")
    print(f"水平偏移量: {h_offset:.2f} px ({'偏右' if h_offset > 0 else '偏左' if h_offset < 0 else '居中'})")

    # 画出图像垂直中线（绿色虚线）
    cv2.line(img, (int(img_center_x), 0), (int(img_center_x), img_h), (0, 255, 0), 1)

    # 画出水平偏移量线：从垂直中线到线段中心点（青黄色）
    cv2.line(img, (int(img_center_x), int(line_center_y)),
             (int(line_center_x), int(line_center_y)), (255, 255, 0), 2)

    # 在垂直中线端点画小圆
    cv2.circle(img, (int(img_center_x), int(line_center_y)), 5, (0, 255, 0), -1)

    # 显示水平偏移量文字
    cv2.putText(img, f'h_offset: {h_offset:.1f}px',
                (int(min(img_center_x, line_center_x)) + 5, int(line_center_y) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    # ===== 计算斜率线的斜率 & 与水平线的弧度差 =====
    dx = b2_cx - b1_cx
    dy = b2_cy - b1_cy
    # 计算斜率线与水平线的夹角（弧度）
    angle_rad = np.arctan2(dy, dx)  # 范围 [-pi, pi]
    print(f"斜率线与水平线的夹角: {angle_rad:.4f} rad ({np.degrees(angle_rad):.2f} deg)")
    angle_text = f'angle: {angle_rad:.4f} rad ({np.degrees(angle_rad):.1f} deg)'

    if abs(dx) < 1e-6:
        slope = float('inf')
        slope_text = 'slope: inf (vertical)'
        print(f"线的斜率: 无穷大（垂直线）")
    else:
        slope = dy / dx
        slope_text = f'slope: {slope:.2f}'
        print(f"线的斜率: {slope:.4f}")
    cv2.putText(img, slope_text,
                (max(int((b1_cx + b2_cx) / 2) - 80, 10), max(int((b1_cy + b2_cy) / 2) - 15, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # 画出水平参考线（与斜率线同起点，用于显示角度）
    ref_len = np.sqrt(dx**2 + dy**2)  # 与斜率线等长
    cv2.line(img, (int(b1_cx), int(b1_cy)),
             (int(b1_cx + ref_len), int(b1_cy)), (180, 180, 180), 1)
    # 显示弧度值
    cv2.putText(img, angle_text,
                (max(int((b1_cx + b2_cx) / 2) - 80, 10), max(int((b1_cy + b2_cy) / 2) + 20, 30)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 200), 2)

    # ========== 构造 MQTT 发送数据（所有数值均转 Python 原生类型） ==========
    result_data = {
        "status": "success",
        "image_size": {"width": int(img_w), "height": int(img_h)},
        "b1_center": {"x": float(round(b1_cx, 2)), "y": float(round(b1_cy, 2))},
        "b2_center": {"x": float(round(b2_cx, 2)), "y": float(round(b2_cy, 2))},
        "line_center": {"x": float(round(line_center_x, 2)), "y": float(round(line_center_y, 2))},
        "horizontal_offset": {
            "value_px": float(round(h_offset, 2)),
            "direction": "right" if h_offset > 0 else "left" if h_offset < 0 else "center"
        },
        "angle": {
            "value_rad": float(round(float(angle_rad), 6)),
            "value_deg": float(round(float(np.degrees(angle_rad)), 2))
        },
        "slope": float(round(slope, 4)) if slope != float('inf') else None
    }

    # ========== 发布 MQTT 消息 ==========
    if mqtt_connected:
        publish_result(mqtt_client, result_data)
    else:
        print("[MQTT] 未连接，跳过发布")

    # ========== r2.jpg: 仅包含水平偏移量 + 斜率线的示意图 ==========
    # 创建白色背景示意图
    margin = 60
    schematic = np.ones((img_h + 2 * margin, img_w + 2 * margin, 3), dtype=np.uint8) * 255

    # 偏移函数：将原图坐标映射到示意图坐标
    def to_schematic(x, y):
        return int(x + margin), int(y + margin)

    # 画出原图边框（灰色参考框）
    cv2.rectangle(schematic,
                  to_schematic(0, 0),
                  to_schematic(img_w, img_h),
                  (200, 200, 200), 1)

    # 1. 图像垂直中线（绿色虚线）
    cv2.line(schematic,
             to_schematic(img_center_x, 0),
             to_schematic(img_center_x, img_h),
             (0, 200, 0), 1)
    cv2.putText(schematic, 'vertical center',
                (to_schematic(img_center_x, 0)[0] + 5, to_schematic(img_center_x, 0)[1] + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 0), 2)

    # 2. 斜率线：两个b的中心点连线（红色）
    cv2.line(schematic,
             to_schematic(b1_cx, b1_cy),
             to_schematic(b2_cx, b2_cy),
             (0, 0, 255), 2)

    # 标出两个b的中心点（黄色）
    cv2.circle(schematic, to_schematic(b1_cx, b1_cy), 6, (0, 255, 255), -1)
    cv2.putText(schematic, 'b1', (to_schematic(b1_cx, b1_cy)[0] - 20,
                                   to_schematic(b1_cx, b1_cy)[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 150, 200), 2)
    cv2.circle(schematic, to_schematic(b2_cx, b2_cy), 6, (0, 255, 255), -1)
    cv2.putText(schematic, 'b2', (to_schematic(b2_cx, b2_cy)[0] - 20,
                                   to_schematic(b2_cx, b2_cy)[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 150, 200), 2)

    # 3. 线的中心点（蓝色）
    cv2.circle(schematic, to_schematic(line_center_x, line_center_y), 8, (255, 0, 0), -1)
    cv2.putText(schematic, f'line_center ({line_center_x:.1f}, {line_center_y:.1f})',
                (to_schematic(line_center_x, line_center_y)[0] + 12,
                 to_schematic(line_center_x, line_center_y)[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # 4. 水平偏移量线：垂直中线 -> 线中心点（青黄色水平线）
    cv2.line(schematic,
             to_schematic(img_center_x, line_center_y),
             to_schematic(line_center_x, line_center_y),
             (0, 200, 255), 2)
    # 垂直中线上的端点（绿色小圆）
    cv2.circle(schematic, to_schematic(img_center_x, line_center_y), 5, (0, 200, 0), -1)
    # 偏移量文字
    h_dir = 'right' if h_offset > 0 else 'left' if h_offset < 0 else 'center'
    cv2.putText(schematic, f'h_offset: {h_offset:.1f}px ({h_dir})',
                (to_schematic(min(img_center_x, line_center_x), line_center_y)[0],
                 to_schematic(min(img_center_x, line_center_x), line_center_y)[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 255), 2)

    # 5. 斜率文字（红色）
    cv2.putText(schematic, slope_text,
                (max(to_schematic((b1_cx + b2_cx) / 2, 0)[0] - 80, 10),
                 max(to_schematic(0, (b1_cy + b2_cy) / 2)[1] - 15, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # 6. 标题
    cv2.putText(schematic, 'Horizontal Offset & Slope Schematic',
                (margin, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # 保存 r2.jpg
    cv2.imwrite('r2.jpg', schematic)
    print("示意图已保存为 r2.jpg")

else:
    print(f"检测到 {len(target_boxes)} 个b目标框，需要恰好2个才能执行后续计算")
    # 即使检测不到2个，也发送 MQTT 消息通知
    if mqtt_connected:
        publish_result(mqtt_client, {
            "status": "error",
            "message": f"检测到 {len(target_boxes)} 个b目标框，需要恰好2个",
            "detected_count": len(target_boxes)
        })

# ========== 断开 MQTT 连接 ==========
if mqtt_connected:
    mqtt_client.disconnect()
    print("[MQTT] 已断开连接")

# 保存r1结果
cv2.imwrite('r1.jpg', img)
print("结果已保存为 r1.jpg")
