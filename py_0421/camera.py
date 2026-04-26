#!/usr/bin/env python3
"""
Camera MJPEG Streaming Server

This script reads camera data from the head and right wrist cameras
and publishes them as MJPEG streams that can be used by lerobot.html
"""

import io
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import agibot_gdk

# Camera types
CAMERA_TYPES = {
    "head_color": agibot_gdk.CameraType.kHeadColor,
    "hand_right_color": agibot_gdk.CameraType.kHandRightColor
}

# Camera images buffer
camera_images = {
    "head_color": None,
    "hand_right_color": None
}

# Camera lock for thread safety
camera_lock = threading.Lock()

# Server settings
HOST = '0.0.0.0'
PORT = 8000

class MJPEGHandler(BaseHTTPRequestHandler):
    """Handler for MJPEG streaming requests"""
    
    def do_GET(self):
        """Handle GET requests for camera streams"""
        if self.path == '/head_color':
            self.send_mjpeg_stream('head_color')
        elif self.path == '/hand_right_color':
            self.send_mjpeg_stream('hand_right_color')
        else:
            self.send_error(404, "Not Found")
    
    def send_mjpeg_stream(self, camera_name):
        """Send MJPEG stream for the specified camera"""
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Pragma', 'no-cache')
        self.end_headers()
        
        try:
            while True:
                with camera_lock:
                    image_data = camera_images.get(camera_name)
                
                if image_data is not None:
                    # Send the image as part of the MJPEG stream
                    self.wfile.write(b'--frame\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(f'Content-Length: {len(image_data)}\r\n'.encode())
                    self.wfile.write(b'\r\n')
                    self.wfile.write(image_data)
                    self.wfile.write(b'\r\n')
                
                # Sleep briefly to control frame rate
                time.sleep(0.05)  # ~20 FPS
                
        except (ConnectionResetError, BrokenPipeError):
            # Client disconnected
            pass

def camera_capture_thread():
    """Thread to continuously capture camera images"""
    print("Initializing camera...")
    
    # Initialize GDK system
    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK initialization failed")
        return
    
    # Initialize camera
    camera = agibot_gdk.Camera()
    time.sleep(2.0)  # Allow camera to stabilize
    
    try:
        print("Starting camera capture...")
        
        while True:
            for name, cam_type in CAMERA_TYPES.items():
                try:
                    # Get the latest image
                    img = camera.get_latest_image(cam_type, 1000.0)
                    
                    if img is not None and hasattr(img, 'data') and img.data is not None:
                        with camera_lock:
                            # Convert numpy array to bytes if needed
                            if hasattr(img.data, 'tobytes'):
                                camera_images[name] = img.data.tobytes()
                            else:
                                camera_images[name] = img.data
                except Exception as e:
                    print(f"Error capturing {name} image: {e}")
            
            # Sleep briefly to control capture rate - after capturing all cameras
            time.sleep(0.05)  # ~20 FPS
            
    except KeyboardInterrupt:
        print("Camera capture stopped by user")
    except Exception as e:
        print(f"Camera capture error: {e}")
    finally:
        camera.close_camera()
        agibot_gdk.gdk_release()
        print("Camera resources released")

def main():
    """Main function to start the server"""
    # Start camera capture thread
    capture_thread = threading.Thread(target=camera_capture_thread)
    capture_thread.daemon = True
    capture_thread.start()
    
    # Wait a moment for camera to initialize
    time.sleep(1.0)
    
    # Start HTTP server
    print(f"Starting MJPEG server on {HOST}:{PORT}")
    print("Streams available at:")
    print(f"  http://{HOST}:{PORT}/head_color")
    print(f"  http://{HOST}:{PORT}/hand_right_color")
    
    server = HTTPServer((HOST, PORT), MJPEGHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    finally:
        server.server_close()
        print("Server resources released")

if __name__ == "__main__":
    main()