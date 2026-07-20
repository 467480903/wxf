#!/bin/bash
# 上传 lerobot/ 目录下所有 zip 文件到远程服务器
# 目标: 10.20.15.170 (admin1 / 123456)

REMOTE_HOST="10.20.15.170"
REMOTE_USER="admin1"
REMOTE_PASS="123456"
REMOTE_DIR="~/"

# 检查 sshpass 是否安装
if ! command -v sshpass &> /dev/null; then
    echo "错误: 需要安装 sshpass"
    echo "  Ubuntu/Debian: sudo apt install sshpass"
    echo "  CentOS/RHEL:   sudo yum install sshpass"
    exit 1
fi

# 查找所有 zip 文件
ZIP_FILES=$(ls *.zip 2>/dev/null)

if [ -z "$ZIP_FILES" ]; then
    echo "未找到任何 zip 文件"
    exit 1
fi

echo "找到以下 zip 文件，准备上传:"
echo "$ZIP_FILES"
echo "-----------------------------------"

for f in $ZIP_FILES; do
    echo "上传: $f"
    sshpass -p "$REMOTE_PASS" scp -o StrictHostKeyChecking=no "$f" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}"
    if [ $? -eq 0 ]; then
        echo "  成功: $f"
    else
        echo "  失败: $f"
    fi
done

echo "-----------------------------------"
echo "上传完成"
