#!/bin/bash
# 压缩 lerobot_dataset 文件夹，分段 500MB
# 用法: bash zip_dataset.sh [输出前缀]

DATASET_DIR="lerobot_dataset"
OUTPUT_PREFIX="${1:-lerobot_dataset}"

if [ ! -d "$DATASET_DIR" ]; then
    echo "错误: 目录 $DATASET_DIR 不存在"
    exit 1
fi

echo "开始压缩 $DATASET_DIR ..."
echo "输出文件: ${OUTPUT_PREFIX}.zip, ${OUTPUT_PREFIX}.z01, ${OUTPUT_PREFIX}.z02, ..."

# 使用 zip 的分卷功能，每卷 500MB
zip -r -s 500m "${OUTPUT_PREFIX}.zip" "$DATASET_DIR"

if [ $? -eq 0 ]; then
    echo "压缩完成"
    ls -lh ${OUTPUT_PREFIX}.zip ${OUTPUT_PREFIX}.z* 2>/dev/null
else
    echo "压缩失败"
    exit 1
fi
