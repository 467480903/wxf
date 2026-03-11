from ultralytics import YOLO

# 加载预训练模型
model = YOLO('yolov8n.pt')

# 目标检测
# results = model('test.png')
# results = model('/data/wxf/detect_results/raw_1773042480.jpg')
results = model('/data/wxf/images/head_color.jpg')

# 保存检测结果
results[0].save('result.jpg')  # 保存为图片
print("检测结果已保存为 result.jpg")