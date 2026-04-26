#!/usr/bin/env python3
"""
Send Last Image from Dataset to MQTT and Handle Delete Commands

This script reads the latest image from the head camera in the lerobot dataset
and publishes it as base64 encoded data to the /lerobot_last_images MQTT topic.
It also listens for delete commands on /lerobot_last_images_delete and removes
corresponding episode folders.
"""

import os
import base64
import json
import glob
import re
import time
import shutil
from pathlib import Path
import threading

import paho.mqtt.client as mqtt

# MQTT Configuration
MQTT_BROKER = "10.20.15.236"
MQTT_PORT = 1883
MQTT_TOPIC = "/lerobot_last_images"
MQTT_DELETE_TOPIC = "/lerobot_last_images_delete"

# Dataset Configuration
DATASET_DIR = Path("/data/wxf/wxf_421/lerobot_dataset")
EPISODE_PREFIX = "episode_"
CAMERA_FOLDER = "observation.images.head_color"
IMAGE_PATTERN = "*.jpg"

# Global variables
mqtt_client = None
should_run = True

def find_latest_episode(dataset_dir: Path) -> str:
    """Find the latest episode index by looking at the episode folders."""
    if not dataset_dir.exists() or not dataset_dir.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    
    # Get all episode folders
    episode_folders = [
        f for f in dataset_dir.glob("episodes/" + EPISODE_PREFIX + "*")
        if f.is_dir()
    ]
    
    if not episode_folders:
        raise FileNotFoundError(f"No episode folders found in: {dataset_dir}/episodes")
    
    # Extract index from folder names and find the maximum
    episode_indices = []
    for folder in episode_folders:
        match = re.match(f"{EPISODE_PREFIX}(\\d+)", folder.name)
        if match:
            episode_indices.append(int(match.group(1)))
    
    if not episode_indices:
        raise ValueError("Could not extract episode indices from folder names")
    
    latest_index = max(episode_indices)
    return f"{EPISODE_PREFIX}{latest_index:06d}"

def find_largest_image(images_dir: Path) -> Path:
    """Find the image with the largest filename (by numerical value) in the given directory."""
    if not images_dir.exists() or not images_dir.is_dir():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    
    # Get all JPG files
    image_files = list(images_dir.glob(IMAGE_PATTERN))
    
    if not image_files:
        raise FileNotFoundError(f"No images found in: {images_dir}")
    
    # Extract numerical part from filenames and find the maximum
    image_nums = []
    for file in image_files:
        match = re.match(r"(\d+)\.jpg$", file.name)
        if match:
            image_nums.append((int(match.group(1)), file))
    
    if not image_nums:
        raise ValueError("Could not extract numerical values from image filenames")
    
    # Return the file with the largest numerical value
    _, largest_file = max(image_nums)
    return largest_file

def image_to_base64(image_path: Path) -> str:
    """Convert image file to base64 string."""
    with open(image_path, "rb") as f:
        encoded_bytes = base64.b64encode(f.read())
        encoded_string = encoded_bytes.decode("utf-8")
    return encoded_string

def delete_episode_folder(episode_index: int) -> bool:
    """Delete the episode folder with the given index."""
    episode_name = f"{EPISODE_PREFIX}{episode_index:06d}"
    episode_dir = DATASET_DIR / "episodes" / episode_name
    
    if not episode_dir.exists():
        print(f"Episode folder not found: {episode_dir}")
        return False
    
    try:
        shutil.rmtree(episode_dir)
        print(f"Successfully deleted episode folder: {episode_dir}")
        return True
    except Exception as e:
        print(f"Error deleting episode folder {episode_dir}: {e}")
        return False

# MQTT Callback Functions
def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker."""
    if rc == 0:
        print(f"Connected to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_DELETE_TOPIC, qos=1)
        print(f"Subscribed to topic: {MQTT_DELETE_TOPIC}")
    else:
        print(f"Failed to connect to MQTT broker, error code: {rc}")

def on_disconnect(client, userdata, rc):
    """Callback when disconnected from MQTT broker."""
    if rc != 0:
        print(f"Unexpected disconnection from MQTT broker, error code: {rc}")
    else:
        print("Disconnected from MQTT broker")

def on_message(client, userdata, msg):
    """Callback when message is received."""
    print(f"Received message: {msg.topic} -> {msg.payload.decode()}")
    
    if msg.topic == MQTT_DELETE_TOPIC:
        try:
            payload = json.loads(msg.payload.decode())
            episode_index = payload.get("episode_index")
            
            if episode_index is not None:
                delete_episode_folder(episode_index)
                
                # After deleting, resend the updated image list
                send_image_list()
            else:
                print("Invalid delete command: missing episode_index")
                
        except json.JSONDecodeError:
            print("Invalid JSON in delete command")
        except Exception as e:
            print(f"Error processing delete command: {e}")

def send_image_list():
    """Send the list of latest images from all episodes to MQTT."""
    try:
        # Step 1: Get all episode folders
        print("Finding all episode folders...")
        episodes_dir = DATASET_DIR / "episodes"
        episode_folders = [
            f for f in episodes_dir.glob(EPISODE_PREFIX + "*")
            if f.is_dir()
        ]
        
        if not episode_folders:
            print(f"No episode folders found in: {episodes_dir}")
            # Publish empty list
            if mqtt_client and mqtt_client.is_connected():
                mqtt_client.publish(MQTT_TOPIC, json.dumps([]), qos=1)
            return
        
        print(f"Found {len(episode_folders)} episodes")
        
        # Step 2: Process each episode
        data = []
        for episode_folder in episode_folders:
            # Extract episode index
            match = re.match(f"{EPISODE_PREFIX}(\\d+)", episode_folder.name)
            if not match:
                print(f"Skipping invalid episode folder: {episode_folder.name}")
                continue
            
            episode_index = int(match.group(1))
            
            try:
                # Find images directory
                images_dir = episode_folder / CAMERA_FOLDER
                if not images_dir.exists():
                    print(f"No head_color folder in episode {episode_index}")
                    continue
                
                # Find largest image in the directory
                largest_image = find_largest_image(images_dir)
                print(f"Episode {episode_index}: Found latest image - {largest_image.name}")
                
                # Convert image to base64
                base64_image = image_to_base64(largest_image)
                
                # Add to data list
                data.append({
                    "episode_index": episode_index,
                    "image": base64_image
                })
                
            except Exception as e:
                print(f"Error processing episode {episode_index}: {e}")
        
        if not data:
            print("No images found in any episode")
            data = []
        
        print(f"Processed {len(data)} episodes with valid images")
        
        # Step 3: Publish to MQTT
        print(f"Publishing to MQTT topic {MQTT_TOPIC}...")
        if mqtt_client and mqtt_client.is_connected():
            json_data = json.dumps(data)
            result = mqtt_client.publish(MQTT_TOPIC, json_data, qos=1)
            result.wait_for_publish()
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Successfully published to {MQTT_TOPIC}")
            else:
                print(f"Failed to publish: {mqtt.error_string(result.rc)}")
        else:
            print("MQTT client not connected, cannot publish")
            
    except Exception as e:
        print(f"Error sending image list: {e}")
        import traceback
        traceback.print_exc()

def mqtt_client_loop():
    """Run MQTT client loop."""
    global mqtt_client
    
    # Create MQTT client
    mqtt_client = mqtt.Client(client_id="send_last_image", clean_session=True)
    
    # Set callbacks
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    
    try:
        # Connect to MQTT broker
        print(f"Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT}...")
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        
        # Start the loop
        mqtt_client.loop_forever()
        
    except KeyboardInterrupt:
        print("MQTT client loop stopped by user")
    except Exception as e:
        print(f"MQTT client error: {e}")
    finally:
        if mqtt_client:
            mqtt_client.disconnect()

def main():
    """Main function to start MQTT client and send initial image list."""
    global should_run
    
    try:
        # Start MQTT client thread
        mqtt_thread = threading.Thread(target=mqtt_client_loop)
        mqtt_thread.daemon = True
        mqtt_thread.start()
        
        # Wait for MQTT client to connect
        print("Waiting for MQTT connection...")
        time.sleep(2)
        
        # Send initial image list
        send_image_list()
        
        # Keep running to listen for delete commands
        print("Listening for delete commands...")
        print("Press Ctrl+C to exit")
        
        while should_run:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
        should_run = False
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        should_run = False

if __name__ == "__main__":
    main()