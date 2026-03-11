import agibot_gdk
import time
import json
import asyncio
import threading
import websockets
import http.server
import socketserver

# 常量定义
LEFT_NAME = "arm_l_end_link"
WS_PORT = 8767  # WebSocket端口
HTTP_PORT = 8082  # HTTP服务端口（用于提供网页）

# 全局变量：机器人实例和连接管理
robot = None
gdk_initialized = False
connected_clients = set()
pushing_data = False

class EndEffectorDataReader:
    """读取左臂末端坐标和姿态的核心功能"""
    def __init__(self, robot):
        self.robot = robot

    def get_left_arm_pose(self):
        """读取左臂末端坐标和姿态，返回字典格式数据"""
        try:
            status = self.robot.get_motion_control_status()
            
            for i, frame_name in enumerate(status.frame_names):
                if frame_name == LEFT_NAME:
                    pose = status.frame_poses[i]
                    return {
                        'success': True,
                        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                        'data': {
                            'position': {
                                'x': round(pose.position.x, 4),
                                'y': round(pose.position.y, 4),
                                'z': round(pose.position.z, 4)
                            },
                            'orientation': {
                                'x': round(pose.orientation.x, 4),
                                'y': round(pose.orientation.y, 4),
                                'z': round(pose.orientation.z, 4),
                                'w': round(pose.orientation.w, 4)
                            }
                        }
                    }
            return {
                'success': False,
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'error': f"未找到左臂末端帧: {LEFT_NAME}"
            }
        except Exception as e:
            return {
                'success': False,
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'error': f"读取数据失败: {str(e)}"
            }

class PlainTextHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """纯文本HTTP页面处理器"""
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            
            # 修复: WS_PORT 动态注入到 HTML，避免端口写死不一致
            html_content = f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>机器人左臂末端状态</title></head>
<body>
<pre>
=====================================
    机器人左臂末端实时数据显示
=====================================

WebSocket连接状态: <span id="wsStatus">连接中...</span>

===== 位置坐标 =====
X: <span id="posX">--</span> 米
Y: <span id="posY">--</span> 米
Z: <span id="posZ">--</span> 米

===== 姿态四元数 =====
X: <span id="oriX">--</span>
Y: <span id="oriY">--</span>
Z: <span id="oriZ">--</span>
W: <span id="oriW">--</span>

更新时间: <span id="updateTime">--</span>

-------------------------------------
(数据实时推送，每秒更新10次)
</pre>

<script>
var ws = new WebSocket("ws://" + window.location.hostname + ":{WS_PORT}");

ws.onopen = function() {{
    document.getElementById("wsStatus").innerHTML = "已连接";
    document.getElementById("wsStatus").style.color = "green";
}};

ws.onclose = function() {{
    document.getElementById("wsStatus").innerHTML = "已断开";
    document.getElementById("wsStatus").style.color = "red";
}};

ws.onerror = function() {{
    document.getElementById("wsStatus").innerHTML = "连接错误";
    document.getElementById("wsStatus").style.color = "red";
}};

ws.onmessage = function(event) {{
    var data = JSON.parse(event.data);
    if (data.success) {{
        document.getElementById("posX").innerHTML = data.data.position.x;
        document.getElementById("posY").innerHTML = data.data.position.y;
        document.getElementById("posZ").innerHTML = data.data.position.z;
        document.getElementById("oriX").innerHTML = data.data.orientation.x;
        document.getElementById("oriY").innerHTML = data.data.orientation.y;
        document.getElementById("oriZ").innerHTML = data.data.orientation.z;
        document.getElementById("oriW").innerHTML = data.data.orientation.w;
        document.getElementById("updateTime").innerHTML = data.timestamp;
    }} else {{
        console.log("数据读取失败:", data.error);
    }}
}};
</script>
</body>
</html>'''
            self.wfile.write(html_content.encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'404 Not Found')

    def log_message(self, format, *args):
        pass  # 屏蔽 HTTP 请求日志，保持终端整洁

async def data_push_loop():
    """数据推送循环，每秒推送10次"""
    global pushing_data
    pushing_data = True
    
    if not robot or not gdk_initialized:
        print("机器人未初始化，无法推送数据")
        return
    
    reader = EndEffectorDataReader(robot)
    
    while pushing_data:
        if connected_clients:
            data = reader.get_left_arm_pose()
            message = json.dumps(data, ensure_ascii=False)
            
            disconnected_clients = []
            tasks = []
            
            for client in connected_clients:
                try:
                    tasks.append(asyncio.create_task(client.send(message)))
                except:
                    disconnected_clients.append(client)
            
            for client in disconnected_clients:
                connected_clients.discard(client)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        await asyncio.sleep(0.1)

async def handle_client(websocket):
    """处理WebSocket客户端连接"""
    connected_clients.add(websocket)
    print(f"新客户端连接，当前连接数: {len(connected_clients)}")
    
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.discard(websocket)
        print(f"客户端断开，当前连接数: {len(connected_clients)}")

async def start_websocket_server():
    """启动WebSocket服务器"""
    global pushing_data
    try:
        async with websockets.serve(handle_client, "0.0.0.0", WS_PORT):
            print(f"WebSocket服务已启动，端口: {WS_PORT}")
            await data_push_loop()
    except Exception as e:
        print(f"WebSocket服务器错误: {e}")
    finally:
        pushing_data = False

def run_websocket_server():
    """在新线程中运行WebSocket服务器"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_websocket_server())
        loop.close()
    except Exception as e:
        print(f"WebSocket线程错误: {e}")

def run_http_server():
    """运行HTTP服务器"""
    try:
        # 修复1: allow_reuse_address=True，解决 Ctrl+C 后重启报 [Errno 98] Address already in use
        socketserver.TCPServer.allow_reuse_address = True
        handler = PlainTextHTTPHandler
        with socketserver.TCPServer(("0.0.0.0", HTTP_PORT), handler) as httpd:
            print(f"HTTP服务已启动，访问 http://<本机IP>:{HTTP_PORT} 查看实时数据")
            httpd.serve_forever()
    except Exception as e:
        print(f"HTTP服务器错误: {e}")

def init_robot():
    """初始化机器人和GDK"""
    global robot, gdk_initialized
    try:
        if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
            print("GDK初始化失败")
            return False
        robot = agibot_gdk.Robot()
        time.sleep(2)
        gdk_initialized = True
        print("机器人初始化成功")
        return True
    except Exception as e:
        print(f"机器人初始化失败: {e}")
        return False

def main():
    if not init_robot():
        print("机器人初始化失败，退出程序")
        return
    
    print("=====================================")
    print("机器人左臂末端数据WebSocket推送服务")
    print("=====================================")
    print(f"WebSocket端口: {WS_PORT}")
    print(f"HTTP网页端口:  {HTTP_PORT}")
    print(f"访问 http://<本机IP>:{HTTP_PORT} 查看实时数据")
    print("按 Ctrl+C 停止服务")
    print("=====================================")
    
    ws_thread = threading.Thread(target=run_websocket_server, daemon=True)
    ws_thread.start()
    
    time.sleep(1)
    
    try:
        run_http_server()
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        global pushing_data
        pushing_data = False
    except Exception as e:
        print(f"主程序错误: {e}")
    finally:
        try:
            if agibot_gdk.gdk_release() == agibot_gdk.GDKRes.kSuccess:
                print("GDK资源释放成功")
            else:
                print("GDK资源释放失败")
        except Exception as e:
            print(f"GDK资源释放异常: {e}")
        
        print("程序已停止")

if __name__ == "__main__":
    main()