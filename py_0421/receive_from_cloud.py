#!/usr/bin/env python3
"""
Receive Large Zip Files via TCP with Resume Support

This script creates a TCP server that listens for incoming file transfers
and supports resuming interrupted downloads.
"""

import os
import socket
import threading
import time
from pathlib import Path

# Configuration
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 9009
BUFFER_SIZE = 8192
DOWNLOAD_DIR = "/data/wxf/wxf_421/downloads"
MAX_RETRIES = 5
RETRY_DELAY = 3  # seconds


class FileReceiver:
    """Handles receiving a single file with resume support."""
    
    def __init__(self, client_socket, client_address):
        self.client_socket = client_socket
        self.client_address = client_address
        self.file_name = None
        self.file_size = 0
        self.received_size = 0
        self.file_path = None
        self.start_time = None
        
    def parse_header(self):
        """Parse the file header sent by the client."""
        print(f"[{self.client_address}] Receiving header...")
        
        header_data = b""
        while True:
            chunk = self.client_socket.recv(BUFFER_SIZE)
            if not chunk:
                return False
                
            header_data += chunk
            if b"\n\n" in header_data:
                break
        
        try:
            # Decode header
            header_str = header_data.decode('utf-8')
            lines = header_str.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('FILE_SIZE:'):
                    self.file_size = int(line.split(':', 1)[1].strip())
                elif line.startswith('FILE_NAME:'):
                    self.file_name = line.split(':', 1)[1].strip()
            
            if not self.file_name or not self.file_size:
                print(f"[{self.client_address}] Invalid header: missing file name or size")
                return False
                
            print(f"[{self.client_address}] Received header:")
            print(f"[{self.client_address}]   File name: {self.file_name}")
            print(f"[{self.client_address}]   File size: {self.file_size / (1024 * 1024):.2f} MB")
            return True
            
        except Exception as e:
            print(f"[{self.client_address}] Error parsing header: {e}")
            return False
    
    def prepare_file(self):
        """Prepare the file for writing, check if resume is needed."""
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        self.file_path = os.path.join(DOWNLOAD_DIR, self.file_name)
        
        # Check if file exists and resume is possible
        if os.path.exists(self.file_path):
            existing_size = os.path.getsize(self.file_path)
            
            if existing_size == self.file_size:
                print(f"[{self.client_address}] File already exists and is complete: {self.file_path}")
                # Send resume position (file size means download complete)
                self.client_socket.sendall(f"RESUME_POS:{existing_size}\n\n".encode())
                return False
                
            elif existing_size < self.file_size:
                print(f"[{self.client_address}] Resuming download from {existing_size} bytes...")
                self.received_size = existing_size
                # Send resume position
                self.client_socket.sendall(f"RESUME_POS:{existing_size}\n\n".encode())
            else:
                print(f"[{self.client_address}] File exists but is larger than expected, starting over...")
                self.received_size = 0
                # Send resume position 0 (start from beginning)
                self.client_socket.sendall(f"RESUME_POS:0\n\n".encode())
        else:
            print(f"[{self.client_address}] Starting new download...")
            self.received_size = 0
            # Send resume position 0
            self.client_socket.sendall(f"RESUME_POS:0\n\n".encode())
        
        return True
    
    def receive_file(self):
        """Receive the file data."""
        self.start_time = time.time()
        
        try:
            # Open file in append mode if resuming, otherwise write mode
            mode = 'ab' if self.received_size > 0 else 'wb'
            
            with open(self.file_path, mode) as f:
                while self.received_size < self.file_size:
                    # Calculate how much data we need to receive
                    remaining = self.file_size - self.received_size
                    chunk_size = min(BUFFER_SIZE, remaining)
                    
                    # Receive data with retry logic
                    retries = 0
                    received_chunk = b""
                    
                    while retries < MAX_RETRIES:
                        try:
                            chunk = self.client_socket.recv(chunk_size)
                            if not chunk:
                                # Connection closed
                                print(f"[{self.client_address}] Connection closed unexpectedly")
                                return False
                            
                            received_chunk += chunk
                            if len(received_chunk) >= chunk_size:
                                break
                                
                        except socket.error as e:
                            retries += 1
                            if retries >= MAX_RETRIES:
                                print(f"[{self.client_address}] Network error after {MAX_RETRIES} retries: {e}")
                                return False
                            print(f"[{self.client_address}] Network error, retrying ({retries}/{MAX_RETRIES})...")
                            time.sleep(RETRY_DELAY)
                    
                    # Write the received chunk
                    f.write(received_chunk)
                    self.received_size += len(received_chunk)
                    
                    # Show progress every 50MB or at the end
                    if self.received_size % (50 * 1024 * 1024) == 0 or self.received_size >= self.file_size:
                        self.show_progress()
                        
            return True
            
        except Exception as e:
            print(f"[{self.client_address}] Error receiving file: {e}")
            return False
    
    def show_progress(self):
        """Show download progress."""
        elapsed_time = time.time() - self.start_time
        progress = (self.received_size / self.file_size) * 100
        
        if elapsed_time > 0:
            speed = self.received_size / (1024 * 1024) / elapsed_time  # MB/s
            print(f"[{self.client_address}] "
                  f"Progress: {self.received_size / (1024 * 1024):.2f} MB / {self.file_size / (1024 * 1024):.2f} MB "
                  f"({progress:.1f}%) - "
                  f"Speed: {speed:.2f} MB/s")
        else:
            print(f"[{self.client_address}] "
                  f"Progress: {self.received_size / (1024 * 1024):.2f} MB / {self.file_size / (1024 * 1024):.2f} MB "
                  f"({progress:.1f}%)")
    
    def complete(self):
        """Complete the download."""
        print(f"[{self.client_address}] Download completed!")
        print(f"[{self.client_address}] File saved to: {self.file_path}")
        print(f"[{self.client_address}] Total bytes received: {self.received_size:,}")
        
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            avg_speed = self.received_size / (1024 * 1024) / elapsed_time  # MB/s
            print(f"[{self.client_address}] Average speed: {avg_speed:.2f} MB/s")
            print(f"[{self.client_address}] Total time: {elapsed_time:.2f} seconds")
    
    def run(self):
        """Run the file receiver."""
        try:
            if not self.parse_header():
                return False
                
            if not self.prepare_file():
                return True  # File already complete
                
            if not self.receive_file():
                return False
                
            self.complete()
            return True
            
        finally:
            self.client_socket.close()


def handle_client(client_socket, client_address):
    """Handle a single client connection."""
    print(f"[{client_address}] New connection established")
    
    receiver = FileReceiver(client_socket, client_address)
    success = receiver.run()
    
    if success:
        print(f"[{client_address}] Connection closed (success)")
    else:
        print(f"[{client_address}] Connection closed (failed)")


def start_server():
    """Start the TCP server."""
    print("=== LeRobot File Receiver Server ===")
    print(f"Listening on: {HOST}:{PORT}")
    print(f"Download directory: {DOWNLOAD_DIR}")
    print(f"Buffer size: {BUFFER_SIZE} bytes")
    print(f"Max retries: {MAX_RETRIES}")
    print(f"Retry delay: {RETRY_DELAY} seconds")
    print()
    
    # Create download directory if it doesn't exist
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Create socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Allow reuse of address
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # Bind and listen
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        
        print("Server started, waiting for connections...")
        print("Press Ctrl+C to stop the server")
        print()
        
        while True:
            # Accept client connection
            client_socket, client_address = server_socket.accept()
            
            # Handle client in a new thread
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address),
                daemon=True
            )
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\nServer stopping...")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server_socket.close()
        print("Server stopped")


def main():
    """Main function."""
    start_server()


if __name__ == "__main__":
    main()