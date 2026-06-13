#!/usr/bin/env python3
"""
Web版相机显示应用（带保存图片功能）
在 camera_web_viewer.py 基础上，每个 RGB 相机卡片增加「保存图片」按钮，
按下后将该相机的当前 RGB 图片保存到 yolo/images 文件夹内。
"""

import time
import threading
import base64
import io
import numpy as np
import agibot_gdk
from typing import Optional, Dict, Any
import os
import json
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# 尝试导入Flask
try:
    from flask import Flask, render_template_string, jsonify, Response, request
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("⚠️ Flask未安装，将使用简化模式")

# 尝试导入OpenCV
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    print("⚠️ OpenCV未安装，将使用原始数据模式")


class WebCameraViewerWithSave:
    """Web版相机查看器（带保存图片功能）"""

    def __init__(self, host='0.0.0.0', port=5000):
        """初始化Web相机查看器"""
        self.camera = None
        self.host = host
        self.port = port
        self.current_image = None
        self.current_camera_index = 0
        self.is_running = False
        self.app = None
        self._cleanup_lock = threading.Lock()

        # 图像缓存
        self.image_cache = {}
        self.cache_timeout = 0.1
        self.last_image_timestamps = {}

        # 保存图片的目录
        self.save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
        os.makedirs(self.save_dir, exist_ok=True)

        # 保存解码后的图像供下载/保存按钮使用
        # {camera_type: decoded_numpy_array}
        self.decoded_images = {}

        self.setup_signal_handlers()

        self.camera_types = [
            # (agibot_gdk.CameraType.kHeadStereoLeft, "头部双目左相机"),
            # (agibot_gdk.CameraType.kHeadStereoRight, "头部双目右相机"),
            # (agibot_gdk.CameraType.kHandLeftColor, "左手彩色相机"),
            # (agibot_gdk.CameraType.kHandRightColor, "右手彩色相机"),
            (agibot_gdk.CameraType.kHeadDepth, "kHeadDepth"),
            (agibot_gdk.CameraType.kHeadColor, "kHeadColor"),
        ]

        # RGB 相机索引集合（有颜色信息的相机才显示保存按钮）
        self.rgb_camera_indices = set()
        for i, (ct, name) in enumerate(self.camera_types):
            # 深度相机和没有"彩色/双目"字样的不显示保存按钮
            if ct in (
                # agibot_gdk.CameraType.kHeadStereoLeft,
                # agibot_gdk.CameraType.kHeadStereoRight,
                # agibot_gdk.CameraType.kHandLeftColor,
                # agibot_gdk.CameraType.kHandRightColor,
                agibot_gdk.CameraType.kHeadColor,
            ):
                self.rgb_camera_indices.add(i)

        # 初始化相机
        self.init_camera()

        # 初始化Flask应用
        if HAS_FLASK:
            self.app = Flask(__name__)
            self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
            self.app.config['TEMPLATES_AUTO_RELOAD'] = False
            self.app.config['EXPLAIN_TEMPLATE_LOADING'] = False
            self.setup_routes()

    def setup_signal_handlers(self):
        """设置信号处理器"""
        self._cleanup_done = False

        def signal_handler(signum, frame):
            if self._cleanup_done:
                print(f"\n⚠️ 强制退出...")
                sys.exit(1)
            print(f"\n⚠️ 收到信号 {signum}，正在安全退出...")
            self._cleanup_done = True
            self.cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def cleanup(self):
        """清理资源"""
        with self._cleanup_lock:
            if hasattr(self, '_cleanup_done') and self._cleanup_done:
                return
            print("🧹 正在清理资源...")
            self.is_running = False
            if self.camera:
                try:
                    self.camera.close_camera()
                    print("✅ 相机已关闭")
                except Exception as e:
                    print(f"⚠️ 关闭相机时出错: {e}")
                finally:
                    self.camera = None
            self.current_image = None
            self.decoded_images.clear()
            time.sleep(0.1)
            print("✅ 资源清理完成")

    def init_camera(self):
        """初始化相机"""
        try:
            print("正在初始化相机...")
            self.camera = agibot_gdk.Camera()
            time.sleep(2)
            print("相机初始化完成！")
        except Exception as e:
            print(f"相机初始化失败: {e}")
            self.camera = None

    def decode_image_data(self, image) -> Optional[np.ndarray]:
        """解码图像数据"""
        if not hasattr(image, 'data') or image.data is None or len(image.data) == 0:
            return None
        try:
            if image.encoding == agibot_gdk.Encoding.JPEG:
                if HAS_OPENCV:
                    nparr = np.frombuffer(image.data, np.uint8)
                    decoded_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    return decoded_image
                else:
                    return image.data

            elif image.encoding == agibot_gdk.Encoding.PNG:
                if HAS_OPENCV:
                    nparr = np.frombuffer(image.data, np.uint8)
                    decoded_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    return decoded_image
                else:
                    return image.data

            elif image.encoding == agibot_gdk.Encoding.UNCOMPRESSED:
                if image.color_format == agibot_gdk.ColorFormat.RGB:
                    decoded_image = np.frombuffer(image.data, dtype=np.uint8)
                    decoded_image = decoded_image.reshape((image.height, image.width, 3))
                    if HAS_OPENCV:
                        decoded_image = cv2.cvtColor(decoded_image, cv2.COLOR_RGB2BGR)
                    return decoded_image
                elif image.color_format == agibot_gdk.ColorFormat.BGR:
                    decoded_image = np.frombuffer(image.data, dtype=np.uint8)
                    decoded_image = decoded_image.reshape((image.height, image.width, 3))
                    return decoded_image
                elif image.color_format == agibot_gdk.ColorFormat.GRAY8:
                    decoded_image = np.frombuffer(image.data, dtype=np.uint8)
                    decoded_image = decoded_image.reshape((image.height, image.width))
                    if HAS_OPENCV:
                        decoded_image = cv2.cvtColor(decoded_image, cv2.COLOR_GRAY2BGR)
                    return decoded_image
                elif image.color_format == agibot_gdk.ColorFormat.GRAY16:
                    decoded_image = np.frombuffer(image.data, dtype=np.uint16)
                    decoded_image = decoded_image.reshape((image.height, image.width))
                    decoded_image = (decoded_image / 256).astype(np.uint8)
                    if HAS_OPENCV:
                        decoded_image = cv2.cvtColor(decoded_image, cv2.COLOR_GRAY2BGR)
                    return decoded_image
                elif image.color_format == agibot_gdk.ColorFormat.RS2_FORMAT_Z16:
                    decoded_image = np.frombuffer(image.data, dtype=np.uint16)
                    decoded_image = decoded_image.reshape((image.height, image.width))
                    valid_mask = decoded_image > 0
                    if np.any(valid_mask):
                        min_depth = np.min(decoded_image[valid_mask])
                        max_depth = np.max(decoded_image[valid_mask])
                        if max_depth > min_depth and max_depth > 0:
                            normalized_depth = ((decoded_image - min_depth) / (max_depth - min_depth) * 255).astype(np.uint8)
                        else:
                            normalized_depth = np.zeros_like(decoded_image, dtype=np.uint8)
                    else:
                        normalized_depth = np.zeros_like(decoded_image, dtype=np.uint8)
                    if HAS_OPENCV:
                        colored_depth = cv2.applyColorMap(normalized_depth, cv2.COLORMAP_JET)
                        if np.any(valid_mask):
                            depth_text = f"Depth: {min_depth}-{max_depth}mm"
                            cv2.putText(colored_depth, depth_text, (10, 30),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        return colored_depth
                    else:
                        return normalized_depth

            return None

        except Exception as e:
            print(f"解码图像数据失败: {e}")
            return None

    def get_camera_info(self, camera_type) -> str:
        """获取相机信息"""
        if self.camera is None:
            return "相机未初始化"
        try:
            shape = self.camera.get_image_shape(camera_type)
            fps = self.camera.get_image_fps(camera_type)
            return f"尺寸: {shape[0]}x{shape[1]} | 帧率: {fps:.1f} FPS"
        except Exception as e:
            return f"获取信息失败: {e}"

    def get_cached_image(self, camera_type):
        """获取缓存的图像"""
        import time
        current_time = time.time()
        if camera_type in self.image_cache:
            cached_image, cache_timestamp, image_timestamp = self.image_cache[camera_type]
            if current_time - cache_timestamp < self.cache_timeout:
                return cached_image
        return None

    def cache_image(self, camera_type, image_b64, image_timestamp=None):
        """缓存图像"""
        import time
        if image_timestamp is None:
            image_timestamp = time.time()
        self.image_cache[camera_type] = (image_b64, time.time(), image_timestamp)

    def process_single_camera(self, camera_type, camera_name, index):
        """处理单个相机的图像"""
        try:
            image = self.camera.get_latest_image(camera_type, 1000.0)

            if image is not None:
                image_timestamp = getattr(image, 'timestamp', None)
                if image_timestamp is None:
                    image_timestamp = time.time()

                last_timestamp = self.last_image_timestamps.get(camera_type, 0)
                is_new_frame = image_timestamp > last_timestamp

                if not is_new_frame:
                    cached_image = self.get_cached_image(camera_type)
                    if cached_image:
                        info = self.get_camera_info(camera_type)
                        return {
                            'index': index,
                            'success': True,
                            'image': cached_image,
                            'info': info,
                            'available': True,
                            'cached': True
                        }

                decoded_image = self.decode_image_data(image)
                if decoded_image is not None:
                    # 保存解码后的图像，供保存按钮使用
                    self.decoded_images[camera_type] = decoded_image

                    image_b64 = self.image_to_base64(decoded_image, quality=75)
                    if image_b64:
                        self.last_image_timestamps[camera_type] = image_timestamp
                        self.cache_image(camera_type, image_b64, image_timestamp)
                        info = self.get_camera_info(camera_type)
                        return {
                            'index': index,
                            'success': True,
                            'image': image_b64,
                            'info': info,
                            'available': True,
                            'cached': False
                        }
                    else:
                        return {
                            'index': index,
                            'success': False,
                            'error': '图像编码失败',
                            'available': False
                        }
                else:
                    return {
                        'index': index,
                        'success': False,
                        'error': '图像解码失败',
                        'available': False
                    }
            else:
                cached_image = self.get_cached_image(camera_type)
                if cached_image:
                    info = self.get_camera_info(camera_type)
                    return {
                        'index': index,
                        'success': True,
                        'image': cached_image,
                        'info': info,
                        'available': True,
                        'cached': True
                    }
                return {
                    'index': index,
                    'success': False,
                    'error': '无法获取图像',
                    'available': False
                }
        except Exception as e:
            error_msg = f'相机 {camera_name} 错误: {str(e)}'
            print(f"⚠️ {error_msg}")
            return {
                'index': index,
                'success': False,
                'error': error_msg,
                'available': False
            }

    def image_to_base64(self, image_data, quality=85) -> str:
        """将图像数据转换为base64字符串"""
        try:
            if HAS_OPENCV and isinstance(image_data, np.ndarray):
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality, cv2.IMWRITE_JPEG_OPTIMIZE, 1]
                _, buffer = cv2.imencode('.jpg', image_data, encode_params)
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                return f"data:image/jpeg;base64,{img_base64}"
            elif isinstance(image_data, bytes):
                img_base64 = base64.b64encode(image_data).decode('utf-8')
                return f"data:image/jpeg;base64,{img_base64}"
            else:
                return None
        except Exception as e:
            print(f"图像转base64失败: {e}")
            return None

    def update_image(self):
        """更新当前图像"""
        if self.camera is None:
            return
        try:
            camera_type, camera_name = self.camera_types[self.current_camera_index]
            image = self.camera.get_latest_image(camera_type, 1000.0)
            if image is not None:
                decoded_image = self.decode_image_data(image)
                if decoded_image is not None:
                    self.current_image = decoded_image
        except Exception as e:
            print(f"更新图像失败: {e}")

    def setup_routes(self):
        """设置Flask路由"""

        # HTML模板 — 在 camera_web_viewer.py 基础上增加「保存图片」按钮
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Genie02 相机画面（支持保存图片）</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f0f0f0;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            color: #333;
        }
        .cameras-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .camera-card {
            border: 2px solid #ddd;
            border-radius: 10px;
            padding: 15px;
            background-color: #fafafa;
            text-align: center;
        }
        .camera-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        .camera-info {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }
        .camera-image {
            max-width: 100%;
            max-height: 300px;
            border: 1px solid #ccc;
            border-radius: 5px;
            background-color: #000;
        }
        .btn-save {
            display: inline-block;
            margin-top: 10px;
            padding: 8px 20px;
            font-size: 14px;
            font-weight: bold;
            color: #fff;
            background-color: #28a745;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .btn-save:hover {
            background-color: #218838;
        }
        .btn-save:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
        }
        .save-msg {
            margin-top: 5px;
            font-size: 12px;
            color: #28a745;
            min-height: 18px;
        }
        .status {
            text-align: center;
            margin-top: 20px;
            padding: 15px;
            background-color: #d4edda;
            border-radius: 5px;
            color: #155724;
            font-size: 16px;
        }
        .refresh-info {
            text-align: center;
            margin-bottom: 20px;
            color: #666;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 机器人相机查看器（支持保存图片）</h1>
            <p>每个 RGB 相机卡片下方有 📷 保存图片 按钮</p>
        </div>

        <div class="refresh-info">
            <p>🔄 所有相机图像每100ms自动刷新 (10fps)</p>
            <p>📁 图片保存到: <code>yolo/images/</code> 目录</p>
        </div>

        <div class="cameras-grid" id="cameras-grid">
            <!-- 相机卡片将通过JavaScript动态生成 -->
        </div>

        <div class="status">
            <p>状态: <span id="status">连接中...</span></p>
        </div>
    </div>

    <script>
        let availableCameras = [];

        // 获取可用相机列表
        function getAvailableCameras() {
            fetch('/get_available_cameras')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        availableCameras = data.cameras;
                        createCameraCards();
                        document.getElementById('status').textContent = `检测到 ${availableCameras.length} 个可用相机`;
                    } else {
                        document.getElementById('status').textContent = '获取相机列表失败: ' + data.error;
                    }
                })
                .catch(error => {
                    document.getElementById('status').textContent = '连接错误: ' + error;
                });
        }

        // 创建相机卡片（带保存按钮）
        function createCameraCards() {
            const grid = document.getElementById('cameras-grid');
            grid.innerHTML = '';

            if (availableCameras.length === 0) {
                grid.innerHTML = '<div style="text-align: center; padding: 50px; color: #666;">没有检测到可用的相机</div>';
                return;
            }

            availableCameras.forEach((camera) => {
                const isRgb = camera.is_rgb;  // 从后端判断
                const card = document.createElement('div');
                card.className = 'camera-card';
                card.innerHTML = `
                    <div class="camera-title">${camera.name}</div>
                    <div class="camera-info" id="info-${camera.index}">尺寸: ${camera.shape[0]}x${camera.shape[1]} | 帧率: ${camera.fps.toFixed(1)} FPS</div>
                    <img class="camera-image" id="image-${camera.index}" src="" alt="${camera.name}">
                    <div>
                        <button class="btn-save" id="save-btn-${camera.index}"
                                onclick="saveImage(${camera.index}, '${camera.name}')">
                            📷 保存图片
                        </button>
                    </div>
                    <div class="save-msg" id="save-msg-${camera.index}"></div>
                `;
                grid.appendChild(card);
            });
        }

        // 保存图片
        function saveImage(index, name) {
            const btn = document.getElementById(`save-btn-${index}`);
            const msg = document.getElementById(`save-msg-${index}`);
            btn.disabled = true;
            msg.textContent = '⏳ 保存中...';
            msg.style.color = '#007bff';

            fetch('/save_image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: index })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    msg.textContent = `✅ ${data.filename}`;
                    msg.style.color = '#28a745';
                } else {
                    msg.textContent = `❌ ${data.error}`;
                    msg.style.color = '#dc3545';
                }
            })
            .catch(error => {
                msg.textContent = `❌ 请求失败: ${error}`;
                msg.style.color = '#dc3545';
            })
            .finally(() => {
                btn.disabled = false;
                // 3秒后清除提示
                setTimeout(() => {
                    msg.textContent = '';
                }, 3000);
            });
        }

        // 更新所有相机图像
        function updateAllImages() {
            if (availableCameras.length === 0) return;

            fetch('/get_all_images')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        availableCameras.forEach((camera) => {
                            const imageData = data.images[camera.index];
                            const imgElement = document.getElementById(`image-${camera.index}`);
                            const infoElement = document.getElementById(`info-${camera.index}`);

                            if (imageData && imageData.success && imageData.image) {
                                imgElement.src = imageData.image;
                                infoElement.textContent = imageData.info || '图像正常';
                            } else {
                                imgElement.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuaXoOazleiDveWKoOi9vTwvdGV4dD48L3N2Zz4=';
                                infoElement.textContent = imageData ? imageData.error : '无法获取图像';
                            }
                        });
                        document.getElementById('status').textContent = `连接正常 - ${availableCameras.length} 个相机`;
                    }
                })
                .catch(error => {
                    document.getElementById('status').textContent = '连接错误: ' + error;
                });
        }

        // 初始化页面
        getAvailableCameras();
        setInterval(updateAllImages, 100);
    </script>
</body>
</html>
        """

        @self.app.route('/')
        def index():
            return render_template_string(html_template)

        @self.app.route('/get_image')
        def get_image():
            try:
                self.update_image()
                if self.current_image is not None:
                    image_b64 = self.image_to_base64(self.current_image)
                    if image_b64:
                        camera_type, camera_name = self.camera_types[self.current_camera_index]
                        info = self.get_camera_info(camera_type)
                        return jsonify({
                            'success': True,
                            'image': image_b64,
                            'info': info
                        })
                return jsonify({'success': False, 'error': '无法获取图像'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/get_available_cameras')
        def get_available_cameras():
            """获取可用的相机列表（标记是否为RGB相机）"""
            try:
                available_cameras = []
                for i, (camera_type, camera_name) in enumerate(self.camera_types):
                    try:
                        shape = self.camera.get_image_shape(camera_type)
                        fps = self.camera.get_image_fps(camera_type)
                        available_cameras.append({
                            'index': i,
                            'type': str(camera_type),
                            'name': camera_name,
                            'shape': shape,
                            'fps': fps,
                            'available': True,
                            'is_rgb': i in self.rgb_camera_indices,
                        })
                    except Exception as e:
                        print(f"⚠️ 相机 {camera_name} 不可用: {e}")
                        continue
                return jsonify({'success': True, 'cameras': available_cameras})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/get_all_images')
        def get_all_images():
            import time
            start_time = time.time()
            try:
                all_images = [None] * len(self.camera_types)
                with ThreadPoolExecutor(max_workers=2) as executor:
                    future_to_index = {
                        executor.submit(self.process_single_camera, camera_type, camera_name, i): i
                        for i, (camera_type, camera_name) in enumerate(self.camera_types)
                    }
                    for future in as_completed(future_to_index):
                        result = future.result()
                        all_images[result['index']] = result

                processing_time = (time.time() - start_time) * 1000
                cached_count = sum(1 for img in all_images if img and img.get('cached', False))
                new_frame_count = sum(1 for img in all_images if img and not img.get('cached', False) and img.get('success', False))
                error_count = sum(1 for img in all_images if img and not img.get('success', False))
                print(f"📊 处理耗时: {processing_time:.1f}ms | 新帧: {new_frame_count} | 缓存: {cached_count} | 错误: {error_count}")

                return jsonify({
                    'success': True,
                    'images': all_images,
                    'processing_time_ms': round(processing_time, 1),
                    'cached_count': cached_count
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/save_image', methods=['POST'])
        def save_image():
            """
            保存指定相机的当前 RGB 图像到 yolo/images/ 目录。
            请求体: {"index": <相机索引>}
            """
            try:
                data = request.get_json()
                index = data.get('index', 0)
                if not (0 <= index < len(self.camera_types)):
                    return jsonify({'success': False, 'error': '无效的相机索引'})

                camera_type, camera_name = self.camera_types[index]

                # 优先从缓存中取解码后的图像
                decoded_img = self.decoded_images.get(camera_type)

                if decoded_img is None:
                    # 缓存中没有，重新获取一帧
                    image = self.camera.get_latest_image(camera_type, 1000.0)
                    if image is None:
                        return jsonify({'success': False, 'error': '无法获取图像帧'})
                    decoded_img = self.decode_image_data(image)
                    if decoded_img is None:
                        return jsonify({'success': False, 'error': '图像解码失败'})
                    self.decoded_images[camera_type] = decoded_img

                # 生成文件名
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                # 从相机名称中提取简短标识
                short_name = camera_name.replace("相机", "").strip()
                filename = f"{short_name}_{timestamp}.jpg"
                filepath = os.path.join(self.save_dir, filename)

                # 保存图像
                if HAS_OPENCV and isinstance(decoded_img, np.ndarray):
                    cv2.imwrite(filepath, decoded_img)
                else:
                    with open(filepath, "wb") as f:
                        f.write(decoded_img)

                print(f"✅ 保存图片: {filepath}")
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'filepath': filepath,
                    'camera_name': camera_name,
                })

            except Exception as e:
                print(f"❌ 保存图片失败: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/switch_camera', methods=['POST'])
        def switch_camera():
            try:
                data = request.get_json()
                index = data.get('index', 0)
                if 0 <= index < len(self.camera_types):
                    self.current_camera_index = index
                    self.update_image()
                    camera_type, camera_name = self.camera_types[index]
                    info = self.get_camera_info(camera_type)
                    return jsonify({
                        'success': True,
                        'camera_name': camera_name,
                        'info': info
                    })
                return jsonify({'success': False, 'error': '无效的相机索引'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

    def run(self):
        """运行Web服务器"""
        if not HAS_FLASK:
            print("❌ Flask未安装，无法启动Web服务器")
            print("请运行: pip install flask")
            return

        if self.camera is None:
            print("❌ 相机未初始化，无法启动")
            return

        print("🌐 Web版相机查看器启动（支持保存图片）")
        print("=" * 60)
        print("📷 支持的相机类型:")
        for i, (_, name) in enumerate(self.camera_types):
            marker = " 📷" if i in self.rgb_camera_indices else ""
            print(f"  {i+1}: {name}{marker}")
        print(f"\n📁 图片保存目录: {self.save_dir}")
        print(f"🌐 访问地址: http://{self.host}:{self.port}")
        print("💡 每个 RGB 相机卡片下方有「保存图片」按钮")
        print("=" * 60)

        try:
            self.is_running = True
            self.app.run(host=self.host, port=self.port, debug=False, threaded=True)
        except KeyboardInterrupt:
            print("\n⚠️ 用户中断程序")
        except Exception as e:
            print(f"❌ Web服务器启动失败: {e}")
        finally:
            if not hasattr(self, '_cleanup_done') or not self._cleanup_done:
                self.cleanup()


def main():
    """主函数"""
    print("🤖 Web版机器人相机查看器（支持保存图片）")
    print("=" * 50)

    if HAS_FLASK:
        print("✅ Flask已安装")
    else:
        print("❌ Flask未安装")
        print("请运行: pip install flask")
        return

    if HAS_OPENCV:
        print(f"✅ OpenCV版本: {cv2.__version__}")
    else:
        print("⚠️ OpenCV未安装，将使用原始数据模式")

    try:
        import agibot_gdk
        print("✅ agibot_gdk已导入")
    except ImportError:
        print("❌ 错误: agibot_gdk未安装或未正确配置")
        return

    viewer = WebCameraViewerWithSave()
    viewer.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
    finally:
        print("👋 程序已退出")
        os._exit(0)
