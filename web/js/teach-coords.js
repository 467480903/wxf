// teach-coords.js
// 示教（坐标）组件：左右手末端坐标 XYZ + RX RY RZ

import { mqttClient } from './mqtt-client.js';

export default {
    name: 'TeachCoords',
    inject: ['getRobotStatus'],
    template: `
    <div class="panel">
        <h5>示教（坐标）- 末端位姿</h5>

        <div style="display:flex; gap:40px; flex-wrap:wrap;">

            <!-- 左手 -->
            <div style="flex:1; min-width:340px;">
                <h6 style="color:#6cf; margin-bottom:12px;">左手</h6>
                <div class="coord-row" v-for="ax in axes" :key="'L_'+ax">
                    <span class="axis-label">{{ ax.toUpperCase() }}</span>
                    <button class="minus" @click="step('left', ax, -stepSize)">−</button>
                    <span class="val">{{ format(left[ax]) }}</span>
                    <button class="plus"  @click="step('left', ax,  stepSize)">+</button>
                </div>
            </div>

            <!-- 右手 -->
            <div style="flex:1; min-width:340px;">
                <h6 style="color:#6cf; margin-bottom:12px;">右手</h6>
                <div class="coord-row" v-for="ax in axes" :key="'R_'+ax">
                    <span class="axis-label">{{ ax.toUpperCase() }}</span>
                    <button class="minus" @click="step('right', ax, -stepSize)">−</button>
                    <span class="val">{{ format(right[ax]) }}</span>
                    <button class="plus"  @click="step('right', ax,  stepSize)">+</button>
                </div>
            </div>
        </div>

        <div style="margin-top:14px; color:#888; font-size:13px;">
            步长:
            <input type="number" v-model.number="stepSize" step="0.01" min="0.001"
                   style="width:90px; background:#11151c; color:#6f6; border:1px solid #2a313c; padding:3px 6px; border-radius:4px;">
            <span style="margin-left:6px;">(XYZ:米, RX/RY/RZ:弧度)</span>
            <span style="margin-left:10px; color:#6f6;">● 已连接实时状态</span>
        </div>
    </div>
    `,
    data() {
        return {
            stepSize: 0.02,
            axes: ['x', 'y', 'z', 'rx', 'ry', 'rz'],
            left:  { x: 0, y: 0, z: 0, rx: 0, ry: 0, rz: 0 },
            right: { x: 0, y: 0, z: 0, rx: 0, ry: 0, rz: 0 },
            _unwatch: null
        };
    },
    methods: {
        step(side, axis, delta) {
            this[side][axis] += delta;
            // 发布 offset_move 命令
            this.publishOffset(side, axis, delta);
        },
        format(v) {
            return v.toFixed(3);
        },
        // 发布末端相对移动命令
        // side: 'left'/'right', axis: x/y/z/rx/ry/rz, delta: 步长
        publishOffset(side, axis, delta) {
            // XYZ 单位米 → 转毫米；RX/RY/RZ 单位弧度 → 乘1000作为微调
            const isTranslation = ['x', 'y', 'z'].includes(axis);
            const value_mm = isTranslation ? delta * 1000 : delta * 1000;
            const key = side === 'left' ? 'l' + axis : 'r' + axis;
            const data = { [key]: value_mm };
            mqttClient.publishCommand('offset_move', data);
        },
        // 从 MQTT 状态刷新末端坐标
        syncFromStatus(status) {
            if (!status) return;
            // 左手
            if (status.left_ee) {
                const p = status.left_ee.position || [];
                const o = status.left_ee.orientation || [];
                this.left.x  = p[0] || 0;
                this.left.y  = p[1] || 0;
                this.left.z  = p[2] || 0;
                this.left.rx = o[0] || 0;
                this.left.ry = o[1] || 0;
                this.left.rz = o[2] || 0;
            }
            // 右手
            if (status.right_ee) {
                const p = status.right_ee.position || [];
                const o = status.right_ee.orientation || [];
                this.right.x  = p[0] || 0;
                this.right.y  = p[1] || 0;
                this.right.z  = p[2] || 0;
                this.right.rx = o[0] || 0;
                this.right.ry = o[1] || 0;
                this.right.rz = o[2] || 0;
            }
        }
    },
    mounted() {
        this._unwatch = this.$watch(
            () => this.getRobotStatus(),
            (newStatus) => {
                this.syncFromStatus(newStatus);
            },
            { immediate: true }
        );
    },
    beforeUnmount() {
        if (this._unwatch) this._unwatch();
    }
};
