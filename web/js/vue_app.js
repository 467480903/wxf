// vue_app.js
// 主 Vue 应用入口

import { createApp } from 'vue';
import { UrdfViewer } from './urdf-viewer.js';
import { mqttClient } from './mqtt-client.js';
import TeachJoints  from './teach-joints.js';
import TeachCoords  from './teach-coords.js';
import ProgramView  from './program-view.js';
import MapView      from './map-view.js';


const App = {
    data() {
        return {
            currentMenu: 'joints',
            menus: [
                { id: 'joints',  label: '示教（角）' },
                { id: 'coords',  label: '示教（坐标）' },
                { id: 'program', label: '程序' },
                { id: 'map',     label: '地图' }
            ],
            urdfViewer: null,
            robotStatus: null   // 共享的机器人状态
        };
    },
    components: { TeachJoints, TeachCoords, ProgramView, MapView },
    provide() {
        return {
            getUrdfViewer: () => this.urdfViewer,
            getRobotStatus: () => this.robotStatus
        };
    },
    template: `
    <div>
        <canvas id="bg-canvas" ref="bgCanvas"></canvas>

        <nav id="toolbar">
            <span class="brand">G2 控制台</span>
            <button
                v-for="m in menus"
                :key="m.id"
                class="menu-btn"
                :class="{ active: currentMenu === m.id }"
                @click="toggleMenu(m.id)">
                {{ m.label }}
            </button>
        </nav>

        <main id="content" :class="{ 'content-hidden': !currentMenu }">
            <teach-joints  v-if="currentMenu === 'joints'"></teach-joints>
            <teach-coords  v-if="currentMenu === 'coords'"></teach-coords>
            <program-view  v-if="currentMenu === 'program'"></program-view>
            <map-view      v-if="currentMenu === 'map'"></map-view>
        </main>
    </div>
    `,
    methods: {
        toggleMenu(id) {
            this.currentMenu = this.currentMenu === id ? '' : id;
        },
        onStatus(data) {
            this.robotStatus = data;
            // 同步关节到 3D 模型
            if (data.joints && this.urdfViewer) {
                this.urdfViewer.setJointsFromStatus(data.joints);
            }
        }
    },
    mounted() {
        // 初始化背景 3D 模型
        this.urdfViewer = new UrdfViewer(this.$refs.bgCanvas);
        this.urdfViewer.loadUrdf('meshes/model.urdf');

        // 连接 MQTT，订阅机器人状态
        mqttClient.onStatus((data) => this.onStatus(data));
        mqttClient.connect();
    }
};

createApp(App).mount('#app');
