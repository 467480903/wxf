// camera-view.js
// 相机视图：显示 4 个相机画面 + 开启/关闭控制 + 计算功能

import { mqttClient } from './mqtt-client.js';

export default {
    name: 'CameraView',
    template: `
    <div class="panel">
        <h5>相机</h5>

        <!-- 4 个相机画面 -->
        <div class="camera-grid">
            <div class="camera-cell" v-for="cam in cameras" :key="cam.key">
                <div class="camera-title">{{ cam.name }}</div>
                <img v-if="images[cam.key]" :src="'data:image/jpeg;base64,' + images[cam.key]" class="camera-img" />
                <div v-else class="camera-placeholder">等待画面...</div>
            </div>
        </div>

        <!-- 开启 / 关闭 -->
        <div style="text-align:center; margin-top:16px;">
            <button class="cam-btn" :class="{ active: streaming }" @click="startStream" :disabled="streaming">开启</button>
            <button class="cam-btn" :class="{ active: !streaming }" @click="stopStream" :disabled="!streaming">关闭</button>
        </div>

        <!-- 关闭时显示的计算按钮组 -->
        <div v-if="!streaming" style="margin-top:20px;">
            <hr style="border-color:#2a313c; margin:10px 0;">
            <h6 style="color:#fc6; margin-bottom:10px;">计算功能</h6>
            <div style="display:flex; gap:12px; justify-content:center; flex-wrap:wrap;">
                <button class="calc-btn" @click="runCompute('head_2point')">头部2点识别</button>
                <button class="calc-btn" @click="runCompute('head_qr')">头部二维码标定</button>
                <button class="calc-btn" @click="runCompute('left_touch')">左手腕碰触检测</button>
                <button class="calc-btn" @click="runCompute('right_touch')">右手腕碰触检测</button>
            </div>

            <!-- 计算结果图片 -->
            <div style="margin-top:16px; text-align:center;">
                <h6 style="color:#fc6; margin-bottom:8px;">计算结果</h6>
                <img v-if="resultImage" :src="'data:image/jpeg;base64,' + resultImage" class="result-img" />
                <div v-else class="camera-placeholder" style="height:200px; max-width:480px; margin:0 auto;">点击上方按钮执行计算</div>
                <div v-if="resultText" style="margin-top:8px; color:#6f6; font-family:monospace;">{{ resultText }}</div>
            </div>
        </div>
    </div>
    `,
    data() {
        return {
            streaming: false,
            images: {},
            resultImage: null,
            resultText: '',
            cameras: [
                { key: 'head_color', name: '头部RGB' },
                { key: 'head_depth', name: '头部深度' },
                { key: 'left_wrist', name: '左手腕' },
                { key: 'right_wrist', name: '右手腕' },
            ],
            _onCamera: null
        };
    },
    mounted() {
        this._onCamera = (data) => {
            if (!data) return;
            // 更新各相机图片
            for (const cam of this.cameras) {
                if (data[cam.key]) {
                    this.images[cam.key] = data[cam.key];
                }
            }
        };
        mqttClient.addCameraCallback(this._onCamera);
    },
    beforeUnmount() {
        if (this._onCamera) {
            mqttClient.removeCameraCallback(this._onCamera);
        }
        // 离开页面时自动关闭
        if (this.streaming) {
            mqttClient.publishCameraControl('stop');
        }
    },
    methods: {
        startStream() {
            this.streaming = true;
            mqttClient.publishCameraControl('start');
        },
        stopStream() {
            this.streaming = false;
            mqttClient.publishCameraControl('stop');
        },
        runCompute(type) {
            // 发送计算命令到 app 服务
            this.resultText = `执行中: ${type} ...`;
            this.resultImage = null;
            mqttClient.publishCommand('cam_head', type);
            // 模拟结果（实际应由服务端返回）
            setTimeout(() => {
                this.resultText = `${type} 完成（等待服务端接入）`;
            }, 1000);
        }
    }
};
