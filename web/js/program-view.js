// program-view.js
// 程序视图：显示一个 Python 代码文件，右下角有启动/停止按钮

export default {
    name: 'ProgramView',
    template: `
    <div class="panel">
        <h5>程序 - g2_minth_app_service.py</h5>

        <div class="code-block" v-text="code"></div>

        <button
            class="floating-btn"
            :class="running ? 'stop' : 'run'"
            @click="toggle">
            {{ running ? '停止' : '启动' }}
        </button>
    </div>
    `,
    data() {
        return {
            code: '// 加载中...',
            running: false
        };
    },
    mounted() {
        // 加载源代码（同源 fetch）
        fetch('../yolo/g2_minth_app_service.py')
            .then(r => r.text())
            .then(t => { this.code = t; })
            .catch(e => { this.code = '// 加载失败: ' + e; });
    },
    methods: {
        toggle() {
            this.running = !this.running;
            this.$root.$emit('program-toggle', this.running);
        }
    }
};
