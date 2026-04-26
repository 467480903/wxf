#!/usr/bin/env python3
"""
Send lerobot_dataset to Cloud via TCP

This script compresses the entire lerobot_dataset folder into a zip file
and sends it via TCP to 20.24.172.33:9009.
"""

import os
import zipfile
import socket
import time
import tempfile
from pathlib import Path

# Configuration
DATASET_DIR = "/data/wxf/wxf_421/lerobot_dataset"
ZIP_OUTPUT_DIR = "/data/wxf/wxf_421/data_to_cloud"
SERVER_HOST = "20.24.172.33"
SERVER_PORT = 9009
BUFFER_SIZE = 8192  # Increased for better performance with large files
UPLOAD_DELAY = 3
MAX_RETRIES = 5
RETRY_DELAY = 3


def create_zip(dataset_path: str, zip_path: str) -> bool:
    """Create a zip file of the dataset."""
    try:
        print(f"Creating zip file from: {dataset_path}")
        print(f"Zip file will be saved to: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through the directory and add all files to zip
            dataset_abs = os.path.abspath(dataset_path)
            total_files = 0
            processed_files = 0
            
            # First count total files
            for root, _, files in os.walk(dataset_abs):
                total_files += len(files)
            
            print(f"Total files to compress: {total_files}")
            print("Compressing files...")
            
            # Add files to zip
            for root, _, files in os.walk(dataset_abs):
                for file in files:
                    # Get the full path to the file
                    file_path = os.path.join(root, file)
                    # Get the relative path for the zip
                    rel_path = os.path.relpath(file_path, os.path.dirname(dataset_abs))
                    # Add file to zip
                    zipf.write(file_path, rel_path)
                    
                    processed_files += 1
                    # Show progress every 100 files
                    if processed_files % 100 == 0 or processed_files == total_files:
                        print(f"Processed {processed_files}/{total_files} files")
            
        print(f"Zip file created successfully: {zip_path}")
        print(f"Zip file size: {os.path.getsize(zip_path) / (1024 * 1024):.2f} MB")
        return True
        
    except Exception as e:
        print(f"Error creating zip file: {e}")
        return False


def send_file(file_path: str, host: str, port: int) -> bool:
    """Send the file via TCP to the specified host and port with resume support."""
    try:
        print(f"\nConnecting to {host}:{port}...")
        
        # Create socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Connect to server
            s.connect((host, port))
            print(f"Connected to {host}:{port}")
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Send file information
            s.sendall(f"FILE_SIZE:{file_size}\n".encode())
            s.sendall(f"FILE_NAME:{os.path.basename(file_path)}\n".encode())
            s.sendall(b"\n")  # End of header
            
            print(f"Sending file: {os.path.basename(file_path)}")
            print(f"File size: {file_size / (1024 * 1024):.2f} MB")
            
            # Receive resume position from server
            resume_pos = 0
            header_data = b""
            
            print("Waiting for server response...")
            while True:
                chunk = s.recv(BUFFER_SIZE)
                if not chunk:
                    print("Connection closed unexpectedly")
                    return False
                
                header_data += chunk
                if b"\n\n" in header_data:
                    break
            
            try:
                header_str = header_data.decode('utf-8')
                for line in header_str.split('\n'):
                    line = line.strip()
                    if line.startswith('RESUME_POS:'):
                        resume_pos = int(line.split(':', 1)[1].strip())
                        break
                
                if resume_pos < 0 or resume_pos > file_size:
                    print(f"Invalid resume position: {resume_pos}")
                    return False
                    
                if resume_pos == file_size:
                    print("Server already has the complete file")
                    return True
                    
            except Exception as e:
                print(f"Error parsing server response: {e}")
                return False
            
            # Send file data with resume support
            sent_bytes = resume_pos
            start_time = time.time()
            
            print(f"Starting from position: {resume_pos} bytes")
            print("Sending file...")
            
            with open(file_path, 'rb') as f:
                # Seek to resume position if needed
                if resume_pos > 0:
                    f.seek(resume_pos)
                
                while sent_bytes < file_size:
                    # Calculate how much data to send in this chunk
                    remaining = file_size - sent_bytes
                    chunk_size = min(BUFFER_SIZE, remaining)
                    
                    data = f.read(chunk_size)
                    if not data:
                        break
                    
                    # Send data with retry logic
                    retries = 0
                    while retries < MAX_RETRIES:
                        try:
                            s.sendall(data)
                            break
                        except socket.error as e:
                            retries += 1
                            if retries >= MAX_RETRIES:
                                print(f"Network error after {MAX_RETRIES} retries: {e}")
                                return False
                            print(f"Network error, retrying ({retries}/{MAX_RETRIES})...")
                            time.sleep(RETRY_DELAY)
                    
                    sent_bytes += len(data)
                    
                    # Show progress every 10MB or at the end
                    if sent_bytes % (10 * 1024 * 1024) == 0 or sent_bytes >= file_size:
                        progress = (sent_bytes / file_size) * 100
                        print(f"Sent {sent_bytes / (1024 * 1024):.2f} MB ({progress:.1f}%)")
            
            end_time = time.time()
            duration = end_time - start_time
            
            if duration > 0:
                speed = sent_bytes / (1024 * 1024) / duration  # MB/s
                print(f"\nFile sent successfully!")
                print(f"Total bytes sent: {sent_bytes:,}")
                print(f"Transfer time: {duration:.2f} seconds")
                print(f"Transfer speed: {speed:.2f} MB/s")
            else:
                print(f"\nFile sent successfully!")
                print(f"Total bytes sent: {sent_bytes:,}")
            
            return True
            
    except socket.error as e:
        print(f"Socket error: {e}")
        return False
    except Exception as e:
        print(f"Error sending file: {e}")
        return False


def main():
    """Main function."""
    print("=== LeRobot Dataset Upload Tool ===")
    print(f"Dataset directory: {DATASET_DIR}")
    print(f"Zip output directory: {ZIP_OUTPUT_DIR}")
    print(f"Upload destination: {SERVER_HOST}:{SERVER_PORT}")
    print()
    
    # Check if dataset exists
    if not os.path.exists(DATASET_DIR):
        print(f"Error: Dataset directory not found: {DATASET_DIR}")
        return False
    
    # Create output directory if it doesn't exist
    os.makedirs(ZIP_OUTPUT_DIR, exist_ok=True)
    
    # Generate zip filename with timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    zip_filename = f"lerobot_dataset_{timestamp}.zip"
    zip_file_path = os.path.join(ZIP_OUTPUT_DIR, zip_filename)
    
    try:
        # Create zip file
        if not create_zip(DATASET_DIR, zip_file_path):
            return False
        
        # Wait for the specified delay before uploading
        print(f"\nWaiting {UPLOAD_DELAY} seconds before uploading...")
        time.sleep(UPLOAD_DELAY)
        
        # Send the zip file
        if not send_file(zip_file_path, SERVER_HOST, SERVER_PORT):
            return False
        
        print("\n=== Upload completed successfully! ===")
        print(f"Zip file saved at: {zip_file_path}")
        return True
        
    except KeyboardInterrupt:
        print("\nUpload cancelled by user")
        return False
    except Exception as e:
        print(f"\nError during execution: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)