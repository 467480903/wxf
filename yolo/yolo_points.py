import cv2
import numpy as np
import json
import math
from ultralytics import YOLO

# load model
model = YOLO('points.pt')

# inference
results = model('./head.jpg')

results[0].save(filename='result_points.jpg')

# original image
img = results[0].orig_img.copy()
img_h, img_w = img.shape[:2]
print(f"图像尺寸: {img_h} x {img_w}")

# get boxes & names
boxes = results[0].boxes
names = results[0].names

print("检测到的所有类别:", names)
print(f"总检测框数: {len(boxes)}")

# find class ID for 'a' and 'b'
class_id_a = None
class_id_b = None
for cid, cname in names.items():
    if cname == 'a':
        class_id_a = cid
    elif cname == 'b':
        class_id_b = cid

# filter boxes
boxes_a = []
boxes_b = []

for box in boxes:
    cls_id = int(box.cls[0])
    conf = float(box.conf[0])
    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2

    if cls_id == class_id_a:
        boxes_a.append((center_x, center_y, x1, y1, x2, y2, conf, 'a'))
    elif cls_id == class_id_b:
        boxes_b.append((center_x, center_y, x1, y1, x2, y2, conf, 'b'))

# sort by confidence
boxes_a.sort(key=lambda x: x[6], reverse=True)
boxes_b.sort(key=lambda x: x[6], reverse=True)

print(f"检测到 {len(boxes_a)} 个 'a', {len(boxes_b)} 个 'b'")

pt1 = None
pt2 = None

if len(boxes_a) >= 1 and len(boxes_b) >= 1:
    pt1 = boxes_a[0]
    pt2 = boxes_b[0]
elif len(boxes_a) >= 2:
    pt1 = boxes_a[0]
    pt2 = boxes_a[1]
elif len(boxes_b) >= 2:
    pt1 = boxes_b[0]
    pt2 = boxes_b[1]
else:
    print("未检测到足够的 a 或 b 标签")


if pt1 is not None and pt2 is not None:
    cx1, cy1, x1_1, y1_1, x1_2, y1_2, conf1, label1 = pt1
    cx2, cy2, x2_1, y2_1, x2_2, y2_2, conf2, label2 = pt2

    # Draw boxes
    color1 = (255, 0, 0) if label1 == 'a' else (0, 255, 0)
    color2 = (255, 0, 0) if label2 == 'a' else (0, 255, 0)
    
    cv2.rectangle(img, (int(x1_1), int(y1_1)), (int(x1_2), int(y1_2)), color1, 2)
    cv2.rectangle(img, (int(x2_1), int(y2_1)), (int(x2_2), int(y2_2)), color2, 2)

    # Put labels
    cv2.putText(img, f'{label1} {conf1:.2f}', (int(x1_1), int(y1_1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color1, 2)
    cv2.putText(img, f'{label2} {conf2:.2f}', (int(x2_1), int(y2_1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color2, 2)

    # Draw line between a and b
    cv2.line(img, (int(cx1), int(cy1)), (int(cx2), int(cy2)), (0, 0, 255), 2)

    # Calculate middle point of line ab
    mid_x = (cx1 + cx2) / 2
    mid_y = (cy1 + cy2) / 2

    # Draw middle point
    cv2.circle(img, (int(mid_x), int(mid_y)), 6, (255, 0, 255), -1)

    # Draw vertical middle line of the image
    img_center_x = img_w / 2
    cv2.line(img, (int(img_center_x), 0), (int(img_center_x), img_h), (0, 255, 0), 2)

    # Calculate horizontal gap
    gap = mid_x - img_center_x
    print(f"Horizontal Gap between middle point and image center: {gap:.2f} px")

    # Calculate slope of line ab
    if cx2 != cx1:
        slope = (cy2 - cy1) / (cx2 - cx1)
    else:
        slope = float('inf') # Vertical line
    print(f"Slope of line ab: {slope:.4f}")

    # Calculate vertical gap
    vertical_gap = img_h - mid_y
    print(f"Vertical Gap between middle point and bottom: {vertical_gap:.2f} px")

    # Calculate rotation radians to make it horizontal
    if slope != float('inf'):
        rotation_radians = math.atan(slope)
    else:
        rotation_radians = math.pi / 2
    print(f"Rotation radians to make it horizontal: {rotation_radians:.4f} rad")

    # Draw horizontal gap line and text
    cv2.line(img, (int(img_center_x), int(mid_y)), (int(mid_x), int(mid_y)), (255, 255, 0), 2)
    cv2.putText(img, f'Gap: {gap:.2f}', (int(min(img_center_x, mid_x)), int(mid_y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    # Draw circles at centers
    cv2.circle(img, (int(cx1), int(cy1)), 5, (0, 255, 255), -1)
    cv2.circle(img, (int(cx2), int(cy2)), 5, (0, 255, 255), -1)

    cv2.imwrite('result_points_line.jpg', img)
    print("线段绘制完成，已保存到 result_points_line.jpg")

    # Save to JSON
    result_data = {
        "horizontal_gap": float(gap),
        "vertical_gap": float(vertical_gap),
        "slope": float(slope) if slope != float('inf') else 'inf',
        "rotation_radians": float(rotation_radians)
    }
    with open('yolo_points_result.json', 'w') as f:
        json.dump(result_data, f, indent=4)
    print("Results saved to yolo_points_result.json")
