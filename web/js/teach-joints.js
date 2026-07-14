// teach-joints.js
// 示教（角）组件：通过 +/- 按钮调整各关节角度
// 关节名与 URDF / g2_minth_status_publisher 对齐

import { mqttClient } from './mqtt-client.js';

export default {
    name: 'TeachJoints',
    inject: ['getUrdfViewer', 'getRobotStatus'],
    template: `
    <div class="panel">
        <h5>示教（角）- 关节角度</h5>

        <!-- 头部 -->
        <div class="joint-row" v-for="j in headJoints" :key="j.name">
            <span class="label">{{ j.label }}</span>
            <button class="minus" @click="step(j, -stepSize)">−</button>
            <span class="angle">{{ format(j.value) }}°</span>
            <button class="plus"  @click="step(j,  stepSize)">+</button>
        </div>

        <hr style="border-color:#2a313c; margin:10px 0;">

        <!-- 手臂：左右并列 -->
        <div style="display:flex; gap:30px; flex-wrap:wrap;">
            <div style="flex:1; min-width:280px;">
                <div class="joint-row" v-for="j in leftArmJoints" :key="j.name">
                    <span class="side">左</span>
                    <span class="label">{{ j.label }}</span>
                    <button class="minus" @click="step(j, -stepSize)">−</button>
                    <span class="angle">{{ format(j.value) }}°</span>
                    <button class="plus"  @click="step(j,  stepSize)">+</button>
                </div>
            </div>
            <div style="flex:1; min-width:280px;">
                <div class="joint-row" v-for="j in rightArmJoints" :key="j.name">
                    <span class="side">右</span>
                    <span class="label">{{ j.label }}</span>
                    <button class="minus" @click="step(j, -stepSize)">−</button>
                    <span class="angle">{{ format(j.value) }}°</span>
                    <button class="plus"  @click="step(j,  stepSize)">+</button>
                </div>
            </div>
        </div>

        <hr style="border-color:#2a313c; margin:10px 0;">

        <!-- 腰部 -->
        <div class="joint-row" v-for="j in waistJoints" :key="j.name">
            <span class="label">{{ j.label }}</span>
            <button class="minus" @click="step(j, -stepSize)">−</button>
            <span class="angle">{{ format(j.value) }}°</span>
            <button class="plus"  @click="step(j,  stepSize)">+</button>
        </div>

        <hr style="border-color:#2a313c; margin:10px 0;">

        <!-- 腿部 -->
        <div style="display:flex; gap:30px; flex-wrap:wrap;">
            <div class="joint-row" v-for="j in legJoints" :key="j.name">
                <span class="label">{{ j.label }}</span>
                <button class="minus" @click="step(j, -stepSize)">−</button>
                <span class="angle">{{ format(j.value) }}°</span>
                <button class="plus"  @click="step(j,  stepSize)">+</button>
            </div>
        </div>

        <div style="margin-top:14px; color:#888; font-size:13px;">
            步长（度）:
            <input type="number" v-model.number="stepSize" step="0.5" min="0.1"
                   style="width:80px; background:#11151c; color:#6f6; border:1px solid #2a313c; padding:3px 6px; border-radius:4px;">
            <span style="margin-left:10px; color:#6f6;">● 已连接实时状态</span>
        </div>
    </div>
    `,
    data() {
        return {
            stepSize: 1.0,
            headJoints: [
                { name: 'idx11_head_joint1', label: '头仰', value: 0, urdfName: 'idx11_head_joint1' },
                { name: 'idx12_head_joint2', label: '头侧', value: 0, urdfName: 'idx12_head_joint2' },
                { name: 'idx13_head_joint3', label: '头转', value: 0, urdfName: 'idx13_head_joint3' }
            ],
            leftArmJoints: [
                { name: 'idx21_arm_l_joint1', label: '1', value: 0, urdfName: 'idx21_arm_l_joint1' },
                { name: 'idx22_arm_l_joint2', label: '2', value: 0, urdfName: 'idx22_arm_l_joint2' },
                { name: 'idx23_arm_l_joint3', label: '3', value: 0, urdfName: 'idx23_arm_l_joint3' },
                { name: 'idx24_arm_l_joint4', label: '4', value: 0, urdfName: 'idx24_arm_l_joint4' },
                { name: 'idx25_arm_l_joint5', label: '5', value: 0, urdfName: 'idx25_arm_l_joint5' },
                { name: 'idx26_arm_l_joint6', label: '6', value: 0, urdfName: 'idx26_arm_l_joint6' },
                { name: 'idx27_arm_l_joint7', label: '7', value: 0, urdfName: 'idx27_arm_l_joint7' }
            ],
            rightArmJoints: [
                { name: 'idx61_arm_r_joint1', label: '1', value: 0, urdfName: 'idx61_arm_r_joint1' },
                { name: 'idx62_arm_r_joint2', label: '2', value: 0, urdfName: 'idx62_arm_r_joint2' },
                { name: 'idx63_arm_r_joint3', label: '3', value: 0, urdfName: 'idx63_arm_r_joint3' },
                { name: 'idx64_arm_r_joint4', label: '4', value: 0, urdfName: 'idx64_arm_r_joint4' },
                { name: 'idx65_arm_r_joint5', label: '5', value: 0, urdfName: 'idx65_arm_r_joint5' },
                { name: 'idx66_arm_r_joint6', label: '6', value: 0, urdfName: 'idx66_arm_r_joint6' },
                { name: 'idx67_arm_r_joint7', label: '7', value: 0, urdfName: 'idx67_arm_r_joint7' }
            ],
            waistJoints: [
                { name: 'idx01_body_joint1', label: '腰转', value: 0, urdfName: 'idx01_body_joint1' },
                { name: 'idx02_body_joint2', label: '腰仰', value: 0, urdfName: 'idx02_body_joint2' },
                { name: 'idx03_body_joint3', label: '腰侧', value: 0, urdfName: 'idx03_body_joint3' }
            ],
            legJoints: [
                { name: 'idx04_body_joint4', label: '腿1', value: 0, urdfName: 'idx04_body_joint4' },
                { name: 'idx05_body_joint5', label: '腿2', value: 0, urdfName: 'idx05_body_joint5' }
            ],
            _unwatch: null
        };
    },
    methods: {
        step(j, delta) {
            j.value += delta;
            // 发布 move_whole_body_by_json 命令
            // 3D 模型由 MQTT 状态自动刷新，无需手动同步
            this.publishJoints();
        },
        format(v) {
            return v.toFixed(1);
        },
        // 收集当前所有关节角（弧度），发布到服务端
        publishJoints() {
            const joints = {};
            const allGroups = [this.headJoints, this.leftArmJoints, this.rightArmJoints, this.waistJoints, this.legJoints];
            allGroups.forEach(group => {
                group.forEach(joint => {
                    joints[joint.name] = joint.value * Math.PI / 180;
                });
            });
            mqttClient.publishCommand('move_whole_body_by_json', joints);
        },
        // 从 MQTT 状态刷新角度显示
        syncFromStatus(status) {
            if (!status || !status.joints) return;
            const j = status.joints;
            const allGroups = [this.headJoints, this.leftArmJoints, this.rightArmJoints, this.waistJoints, this.legJoints];
            allGroups.forEach(group => {
                group.forEach(joint => {
                    if (j[joint.name] !== undefined) {
                        joint.value = j[joint.name] * 180 / Math.PI;
                    }
                });
            });
        }
    },
    mounted() {
        // 监听父组件 robotStatus 变化
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
