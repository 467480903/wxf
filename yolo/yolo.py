import cv2
import numpy as np
from ultralytics import YOLO

# 加载预训练模型
model = YOLO('06132022.pt')

# 目标检测
results = model('./head.jpg')

results[0].save(filename='result.jpg')

# 获取原始图像
img = results[0].orig_img.copy()
img_h, img_w = img.shape[:2]
print(f"图像尺寸: {img_h} x {img_w}")

# 图像垂直中线的 x 坐标
img_center_x = img_w / 2

# 公共辅助函数
def get_label(pt, boxes_a, boxes_b, boxes_c, boxes_d):
    """根据点所在的列表获取类别标签"""
    if pt in boxes_a:
        return 'a'
    elif pt in boxes_b:
        return 'b'
    elif pt in boxes_c:
        return 'c'
    elif pt in boxes_d:
        return 'd'
    return '?'

def get_label_color(label):
    """根据类别标签返回对应的 BGR 颜色"""
    colors = {'a': (255, 0, 0), 'b': (0, 255, 0), 'c': (0, 0, 255), 'd': (0, 165, 255)}
    return colors.get(label, (128, 128, 128))

# 获取所有检测框
boxes = results[0].boxes
names = results[0].names

print("检测到的所有类别:", names)
print(f"总检测框数: {len(boxes)}")

# ========== 按类别名称筛选框，并保留置信度 ==========
# 找到 'a' 和 'b' 对应的 class_id
class_id_a = None
class_id_b = None
for cid, cname in names.items():
    if cname == 'a':
        class_id_a = cid
    elif cname == 'b':
        class_id_b = cid

print(f"类别 'a' ID: {class_id_a}, 类别 'b' ID: {class_id_b}")

# 收集 'a' 框和 'b' 框，带置信度
boxes_a = []   # (center_x, center_y, x1, y1, x2, y2, conf)
boxes_b = []   # (center_x, center_y, x1, y1, x2, y2, conf)

for box in boxes:
    cls_id = int(box.cls[0])
    conf = float(box.conf[0])
    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2

    if cls_id == class_id_a:
        boxes_a.append((center_x, center_y, x1, y1, x2, y2, conf))
    elif cls_id == class_id_b:
        boxes_b.append((center_x, center_y, x1, y1, x2, y2, conf))

# 按置信度从高到低排序
boxes_a.sort(key=lambda x: x[6], reverse=True)
boxes_b.sort(key=lambda x: x[6], reverse=True)

print(f"检测到 {len(boxes_a)} 个 'a', {len(boxes_b)} 个 'b'")

# ========== 也收集 c 和 d 作为后备 ==========
class_id_c = None
class_id_d = None
for cid, cname in names.items():
    if cname == 'c':
        class_id_c = cid
    elif cname == 'd':
        class_id_d = cid

boxes_c = []   # (center_x, center_y, x1, y1, x2, y2, conf)
boxes_d = []   # (center_x, center_y, x1, y1, x2, y2, conf)

for box in boxes:
    cls_id = int(box.cls[0])
    conf = float(box.conf[0])
    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2

    if cls_id == class_id_c:
        boxes_c.append((center_x, center_y, x1, y1, x2, y2, conf))
    elif cls_id == class_id_d:
        boxes_d.append((center_x, center_y, x1, y1, x2, y2, conf))

boxes_c.sort(key=lambda x: x[6], reverse=True)
boxes_d.sort(key=lambda x: x[6], reverse=True)

print(f"检测到 {len(boxes_c)} 个 'c', {len(boxes_d)} 个 'd'")

# ========== 根据策略选择两个画线点 ==========
pt1 = None  # 第一个点 (cx, cy, x1, y1, x2, y2, conf, label)
pt2 = None  # 第二个点

if len(boxes_a) >= 1 and len(boxes_b) >= 1:
    # 策略1: 1个a + 1个b → 取最高置信度的a和b
    pt1 = boxes_a[0]
    pt2 = boxes_b[0]
    print("策略: 使用最高置信度的 a 和 b 画线")
elif len(boxes_b) >= 2:
    # 策略2: 2个及以上 b，无足够 a → 取最高置信度的2个b
    pt1 = boxes_b[0]
    pt2 = boxes_b[1]
    print("策略: 使用最高置信度的 2 个 b 画线")
elif len(boxes_a) >= 2:
    # 策略3: 2个及以上 a，无足够 b → 取最高置信度的2个a
    pt1 = boxes_a[0]
    pt2 = boxes_a[1]
    print("策略: 使用最高置信度的 2 个 a 画线")
elif len(boxes_c) >= 1 and len(boxes_d) >= 1:
    # 策略4: a/b 都不够，用1个c + 1个d
    pt1 = boxes_c[0]
    pt2 = boxes_d[0]
    print("策略: 使用最高置信度的 c 和 d 画线（a/b 不足）")
elif len(boxes_c) >= 2:
    # 策略5: 2个及以上 c
    pt1 = boxes_c[0]
    pt2 = boxes_c[1]
    print("策略: 使用最高置信度的 2 个 c 画线（a/b 不足）")
elif len(boxes_d) >= 2:
    # 策略6: 2个及以上 d
    pt1 = boxes_d[0]
    pt2 = boxes_d[1]
    print("策略: 使用最高置信度的 2 个 d 画线（a/b 不足）")
else:
    print(f"无法满足任何画线条件: a={len(boxes_a)}, b={len(boxes_b)}, c={len(boxes_c)}, d={len(boxes_d)}")

# ========== 如果能找到两个点，执行画线和计算 ==========
if pt1 is not None and pt2 is not None:
    cx1, cy1, x1_1, y1_1, x1_2, y1_2, conf1 = pt1
    cx2, cy2, x2_1, y2_1, x2_2, y2_2, conf2 = pt2
    label1 = get_label(pt1, boxes_a, boxes_b, boxes_c, boxes_d)
    label2 = get_label(pt2, boxes_a, boxes_b, boxes_c, boxes_d)

    print(f"点1: label={label1}, conf={conf1:.4f}, center=({cx1:.1f}, {cy1:.1f})")
    print(f"点2: label={label2}, conf={conf2:.4f}, center=({cx2:.1f}, {cy2:.1f})")

    # 画两个目标框（根据类别用不同颜色）
    color1 = get_label_color(label1)
    color2 = get_label_color(label2)
    cv2.rectangle(img, (int(x1_1), int(y1_1)), (int(x1_2), int(y1_2)), color1, 2)
    cv2.rectangle(img, (int(x2_1), int(y2_1)), (int(x2_2), int(y2_2)), color2, 2)

    # 标注类别标签+置信度
    cv2.putText(img, f'{label1} {conf1:.2f}',
                (int(x1_1), int(y1_1) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color1, 2)
    cv2.putText(img, f'{label2} {conf2:.2f}',
                (int(x2_1), int(y2_1) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color2, 2)

    # 以两个中心点画一条线（红色）
    cv2.line(img, (int(cx1), int(cy1)), (int(cx2), int(cy2)), (0, 0, 255), 2)

    # 计算这条线的中心点
    line_center_x = (cx1 + cx2) / 2
    line_center_y = (cy1 + cy2) / 2

    # 标出线的中心点
    cv2.circle(img, (int(line_center_x), int(line_center_y)), 8, (255, 0, 0), -1)
    cv2.putText(img, f'({line_center_x:.1f}, {line_center_y:.1f})',
                (int(line_center_x) + 10, int(line_center_y) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # 标出两个中心点
    cv2.circle(img, (int(cx1), int(cy1)), 5, (0, 255, 255), -1)
    cv2.circle(img, (int(cx2), int(cy2)), 5, (0, 255, 255), -1)

    # ===== 计算图像垂直中线到线段中心点的水平偏移量 =====
    h_offset = line_center_x - img_center_x
    print(f"线段中心点: ({line_center_x:.2f}, {line_center_y:.2f})")
    print(f"图像垂直中线 x: {img_center_x:.2f}")
    print(f"水平偏移量: {h_offset:.2f} px ({'偏右' if h_offset > 0 else '偏左' if h_offset < 0 else '居中'})")

    # 画出图像垂直中线（绿色虚线）
    cv2.line(img, (int(img_center_x), 0), (int(img_center_x), img_h), (0, 255, 0), 1)

    # 画出水平偏移量线
    cv2.line(img, (int(img_center_x), int(line_center_y)),
             (int(line_center_x), int(line_center_y)), (255, 255, 0), 2)

    cv2.circle(img, (int(img_center_x), int(line_center_y)), 5, (0, 255, 0), -1)

    cv2.putText(img, f'h_offset: {h_offset:.1f}px',
                (int(min(img_center_x, line_center_x)) + 5, int(line_center_y) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    # ===== 计算斜率线的斜率 & 与水平线的弧度差 =====
    dx = cx2 - cx1
    dy = cy2 - cy1
    angle_rad = np.arctan2(dy, dx)
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
                (max(int((cx1 + cx2) / 2) - 80, 10), max(int((cy1 + cy2) / 2) - 15, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    ref_len = np.sqrt(dx**2 + dy**2)
    cv2.line(img, (int(cx1), int(cy1)),
             (int(cx1 + ref_len), int(cy1)), (180, 180, 180), 1)
    cv2.putText(img, angle_text,
                (max(int((cx1 + cx2) / 2) - 80, 10), max(int((cy1 + cy2) / 2) + 20, 30)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 200), 2)

    # ========== r2.jpg: 示意图 ==========
    margin = 60
    schematic = np.ones((img_h + 2 * margin, img_w + 2 * margin, 3), dtype=np.uint8) * 255

    def to_schematic(x, y):
        return int(x + margin), int(y + margin)

    cv2.rectangle(schematic,
                  to_schematic(0, 0),
                  to_schematic(img_w, img_h),
                  (200, 200, 200), 1)

    cv2.line(schematic,
             to_schematic(img_center_x, 0),
             to_schematic(img_center_x, img_h),
             (0, 200, 0), 1)
    cv2.putText(schematic, 'vertical center',
                (to_schematic(img_center_x, 0)[0] + 5, to_schematic(img_center_x, 0)[1] + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 0), 2)

    cv2.line(schematic,
             to_schematic(cx1, cy1),
             to_schematic(cx2, cy2),
             (0, 0, 255), 2)

    cv2.circle(schematic, to_schematic(cx1, cy1), 6, (0, 255, 255), -1)
    label_color1 = get_label_color(label1)
    cv2.putText(schematic, f'{label1}({conf1:.2f})',
                (to_schematic(cx1, cy1)[0] - 30, to_schematic(cx1, cy1)[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, label_color1, 2)
    cv2.circle(schematic, to_schematic(cx2, cy2), 6, (0, 255, 255), -1)
    label_color2 = get_label_color(label2)
    cv2.putText(schematic, f'{label2}({conf2:.2f})',
                (to_schematic(cx2, cy2)[0] - 30, to_schematic(cx2, cy2)[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, label_color2, 2)

    cv2.circle(schematic, to_schematic(line_center_x, line_center_y), 8, (255, 0, 0), -1)
    cv2.putText(schematic, f'line_center ({line_center_x:.1f}, {line_center_y:.1f})',
                (to_schematic(line_center_x, line_center_y)[0] + 12,
                 to_schematic(line_center_x, line_center_y)[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    cv2.line(schematic,
             to_schematic(img_center_x, line_center_y),
             to_schematic(line_center_x, line_center_y),
             (0, 200, 255), 2)
    cv2.circle(schematic, to_schematic(img_center_x, line_center_y), 5, (0, 200, 0), -1)
    h_dir = 'right' if h_offset > 0 else 'left' if h_offset < 0 else 'center'
    cv2.putText(schematic, f'h_offset: {h_offset:.1f}px ({h_dir})',
                (to_schematic(min(img_center_x, line_center_x), line_center_y)[0],
                 to_schematic(min(img_center_x, line_center_x), line_center_y)[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 255), 2)

    cv2.putText(schematic, slope_text,
                (max(to_schematic((cx1 + cx2) / 2, 0)[0] - 80, 10),
                 max(to_schematic(0, (cy1 + cy2) / 2)[1] - 15, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.putText(schematic, 'Horizontal Offset & Slope Schematic',
                (margin, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    cv2.imwrite('r2.jpg', schematic)
    print("示意图已保存为 r2.jpg")

else:
    print(f"无法找到足够的目标点，跳过画线计算")

# 保存r1结果
cv2.imwrite('r1.jpg', img)
print("结果已保存为 r1.jpg")
