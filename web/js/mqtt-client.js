// mqtt-client.js
// MQTT 客户端封装，基于 paho-mqtt.min.js
// 连接本机 WebSocket 9001，订阅 /G2_minth_status 和 /G2_minth_cloud

const MQTT_BROKER = location.hostname || '10.2.236.6';
const MQTT_PORT   = 9001;
const STATUS_TOPIC = '/G2_minth_status';
const CLOUD_TOPIC  = '/G2_minth_cloud';
const CAMERAS_TOPIC = '/G2_minth_cameras';

class MqttClient {
    constructor() {
        this.client = null;
        this.connected = false;
        this.statusCallback = null;
        this.cloudCallbacks = [];
        this.cameraCallbacks = [];
    }

    connect() {
        const clientId = 'g2_web_' + Math.random().toString(16).substr(2, 8);
        this.client = new Paho.Client(MQTT_BROKER, MQTT_PORT, clientId);

        this.client.onConnectionLost = (responseObject) => {
            if (responseObject.errorCode !== 0) {
                console.error('[MQTT] 连接丢失:', responseObject.errorMessage);
            }
            this.connected = false;
            // 5 秒后重连
            setTimeout(() => this.connect(), 5000);
        };

        this.client.onMessageArrived = (message) => {
            try {
                const data = JSON.parse(message.payloadString);

                if (message.destinationName === STATUS_TOPIC && this.statusCallback) {
                    this.statusCallback(data);
                } else if (message.destinationName === CLOUD_TOPIC) {
                    // 分发给所有注册的点云回调
                    this.cloudCallbacks.forEach(cb => cb(data));
                } else if (message.destinationName === CAMERAS_TOPIC) {
                    // 分发给所有注册的相机回调
                    this.cameraCallbacks.forEach(cb => cb(data));
                }
            } catch (e) {
                console.error('[MQTT] JSON 解析失败:', e);
            }
        };

        this.client.connect({
            onSuccess: () => {
                console.log('[MQTT] 连接成功:', MQTT_BROKER + ':' + MQTT_PORT);
                this.connected = true;
                this.client.subscribe(STATUS_TOPIC, { qos: 0 });
                this.client.subscribe(CLOUD_TOPIC, { qos: 0 });
                this.client.subscribe(CAMERAS_TOPIC, { qos: 0 });
            },
            onFailure: (err) => {
                console.error('[MQTT] 连接失败:', err.errorMessage);
                setTimeout(() => this.connect(), 5000);
            },
            useSSL: false,
        });
    }

    onStatus(callback) {
        this.statusCallback = callback;
    }

    /**
     * 注册点云数据回调
     */
    addCloudCallback(callback) {
        if (!this.cloudCallbacks.includes(callback)) {
            this.cloudCallbacks.push(callback);
        }
    }

    /**
     * 移除点云数据回调
     */
    removeCloudCallback(callback) {
        this.cloudCallbacks = this.cloudCallbacks.filter(cb => cb !== callback);
    }

    /**
     * 注册相机数据回调
     */
    addCameraCallback(callback) {
        if (!this.cameraCallbacks.includes(callback)) {
            this.cameraCallbacks.push(callback);
        }
    }

    /**
     * 移除相机数据回调
     */
    removeCameraCallback(callback) {
        this.cameraCallbacks = this.cameraCallbacks.filter(cb => cb !== callback);
    }

    /**
     * 发布命令到指定 topic
     */
    publishToTopic(topic, payload) {
        if (!this.connected || !this.client) {
            console.warn('[MQTT] 未连接，无法发送:', topic);
            return;
        }
        const message = new Paho.Message(JSON.stringify(payload));
        message.destinationName = topic;
        message.qos = 0;
        this.client.send(message);
        console.log('[MQTT] 已发送到', topic, payload);
    }

    /**
     * 发布命令到 /G2_minth_app
     * @param {string} cmd - 命令名
     * @param {*} data - 命令数据
     */
    publishCommand(cmd, data) {
        this.publishToTopic('/G2_minth_app', { cmd, data });
    }

    /**
     * 发送相机控制命令
     */
    publishCameraControl(cmd) {
        this.publishToTopic('/G2_minth_camera', { cmd });
    }
}

export const mqttClient = new MqttClient();
