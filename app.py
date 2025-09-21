"""
Enhanced Marine Surveillance Flask System
==========================================

This Flask application creates a real-time marine surveillance dashboard with:
- PC laptop camera integration (Camera 1) - Clean feed with advanced diagnostics
- Simulated underwater camera (Camera 2) 
- Automatic LiDAR with point.csv loading and hidden map data
- Real-time detection tracking
- Live video streaming
- Interactive dashboard with statistics
- Camera diagnostic and automatic recovery system
- Hidden LiDAR mapping and data visualization

Prerequisites:
- Flask
- OpenCV (cv2)
- NumPy

Installation:
pip install flask opencv-python numpy

Usage:
python app.py

Access:
- Dashboard: http://localhost:5002
- LiDAR Hidden Map: http://localhost:5002/lidar/hidden
"""

from flask import Flask, render_template, jsonify, Response, request
from datetime import datetime, timedelta
import random
import cv2
import threading
import time
import numpy as np
import atexit
import os
import platform
import subprocess
import sys
import json
import csv
from io import StringIO

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'marine-surveillance-secret-key-2024'

class EnhancedCameraManager:
    """
    Enhanced Camera Manager for marine surveillance system
    - Manages PC webcam integration (clean feed for YOLO integration)
    - Provides simulated underwater camera feed
    - Handles video streaming and image capture
    - Automatic diagnostics and error recovery
    """
    
    def __init__(self):
        self.cameras = {}
        self.camera_stats = {
            'pc_camera': {'frames_captured': 0, 'errors': 0, 'start_time': time.time()},
            'underwater_camera': {'frames_captured': 0, 'errors': 0, 'start_time': time.time()}
        }
        self.mock_camera_active = False
        self.last_reconnect_attempt = 0
        self.reconnect_interval = 30  # Reconnection attempt every 30 seconds
        
        # Launch diagnostics and initialization
        self.run_comprehensive_diagnostics()
        self.init_cameras_with_fallbacks()
    
    def run_comprehensive_diagnostics(self):
        """Comprehensive system diagnostics for camera issues"""
        print("🔍 CAMERA SYSTEM DIAGNOSTICS")
        print("=" * 50)
        
        # 1. Check OpenCV installation
        print(f"📦 OpenCV Version: {cv2.__version__}")
        
        # 2. Check operating system
        os_info = platform.system()
        print(f"💻 Operating System: {os_info} {platform.release()}")
        print(f"🐍 Python Version: {sys.version.split()[0]}")
        
        # 3. List available camera devices
        available_cameras = self.scan_available_cameras()
        
        # 4. Check camera permissions (important on macOS/Linux)
        if os_info == "Darwin":  # macOS
            print("🍎 macOS detected - checking camera permissions...")
            print("   If camera fails, check: System Preferences > Security & Privacy > Camera")
        elif os_info == "Linux":
            print("🐧 Linux detected - checking camera permissions...")
            print("   Camera devices should be in /dev/video*")
            try:
                video_devices = subprocess.check_output("ls /dev/video* 2>/dev/null || echo 'No video devices found'", shell=True).decode().strip()
                print(f"   Available devices: {video_devices}")
            except:
                print("   Unable to check video devices")
        elif os_info == "Windows":
            print("🪟 Windows detected - checking DirectShow devices...")
        
        # 5. Check processes that might be using the camera
        self.check_camera_conflicts()
        
        print("=" * 50)
    
    def check_camera_conflicts(self):
        """Check potential conflicts with other applications"""
        print("🔍 Checking application conflicts...")
        
        common_camera_apps = [
            'zoom', 'skype', 'teams', 'discord', 'obs', 'streamlabs',
            'chrome', 'firefox', 'safari', 'facetime', 'photobooth'
        ]
        
        try:
            if platform.system() == "Windows":
                import psutil
                running_processes = [p.name().lower() for p in psutil.process_iter(['name'])]
            else:
                running_processes = subprocess.check_output("ps aux", shell=True).decode().lower()
            
            conflicts = [app for app in common_camera_apps if app in str(running_processes)]
            
            if conflicts:
                print(f"   ⚠️  Potentially conflicting applications detected: {', '.join(conflicts)}")
                print("   💡 Close these applications if camera doesn't work")
            else:
                print("   ✅ No application conflicts detected")
                
        except Exception as e:
            print(f"   ℹ️  Unable to check conflicts: {e}")
    
    def scan_available_cameras(self):
        """Detect all available camera indices"""
        print("📹 Scanning available cameras...")
        available_cameras = []
        
        # Test camera indices 0-5 (usually sufficient)
        for index in range(6):
            try:
                cap = cv2.VideoCapture(index)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        height, width = frame.shape[:2]
                        available_cameras.append({
                            'index': index,
                            'resolution': f"{width}x{height}",
                            'working': True
                        })
                        print(f"   ✅ Camera {index}: Available ({width}x{height})")
                    else:
                        print(f"   ⚠️  Camera {index}: Detected but cannot read frames")
                    cap.release()
                else:
                    if index <= 2:  # Show message only for main cameras
                        print(f"   ❌ Camera {index}: Not available")
            except Exception as e:
                if index == 0:  # Show error only for main camera
                    print(f"   ❌ Camera {index} error: {e}")
        
        if not available_cameras:
            print("   🚨 NO CAMERAS DETECTED!")
            print("   Possible solutions:")
            print("   • Check camera is connected and not used by another app")
            print("   • Try different camera indices (0, 1, 2...)")
            print("   • Restart the application")
            print("   • Check camera drivers")
        
        return available_cameras
    
    def init_cameras_with_fallbacks(self):
        """Camera initialization with multiple recovery strategies"""
        print("\n🎥 ENHANCED CAMERA INITIALIZATION")
        print("=" * 50)
        
        # Strategy 1: Try default camera (index 0)
        success = self.try_camera_with_index(0)
        
        if not success:
            # Strategy 2: Try other common indices
            print("🔄 Trying alternative camera indices...")
            for index in [1, 2, -1]:  # -1 is auto-detection on some systems
                if self.try_camera_with_index(index):
                    success = True
                    break
        
        if not success:
            # Strategy 3: Try different backends
            print("🔄 Trying different camera backends...")
            backends = [
                (cv2.CAP_DSHOW, "DirectShow (Windows)"),
                (cv2.CAP_V4L2, "Video4Linux2 (Linux)"),
                (cv2.CAP_AVFOUNDATION, "AVFoundation (macOS)"),
                (cv2.CAP_GSTREAMER, "GStreamer"),
                (cv2.CAP_ANY, "Auto-detection")
            ]
            
            for backend_id, backend_name in backends:
                try:
                    print(f"   Trying {backend_name}...")
                    cap = cv2.VideoCapture(0, backend_id)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            self.cameras['pc_camera'] = cap
                            print(f"   ✅ Camera initialized with backend: {backend_name}")
                            self.configure_camera_settings()
                            success = True
                            break
                        cap.release()
                except Exception as e:
                    continue
        
        if not success:
            # Strategy 4: Create simulated camera for testing
            print("⚠️  All camera initialization attempts failed")
            print("🎭 Initializing simulated camera for testing...")
            self.cameras['pc_camera'] = None
            self.mock_camera_active = True
        
        # Always initialize underwater camera (simulated)
        self.cameras['underwater_camera'] = True
        print("🌊 Underwater camera simulation ready")
        
        print("=" * 50)
    
    def try_camera_with_index(self, index):
        """Try initializing camera with specific index"""
        try:
            print(f"📹 Trying camera index {index}...")
            cap = cv2.VideoCapture(index)
            
            if not cap.isOpened():
                print(f"   ❌ Failed to open camera {index}")
                return False
            
            # Test frame capture
            ret, frame = cap.read()
            if not ret or frame is None:
                print(f"   ❌ Camera {index} opened but cannot read frames")
                cap.release()
                return False
            
            # Success!
            self.cameras['pc_camera'] = cap
            print(f"   ✅ Camera {index} initialized successfully!")
            self.configure_camera_settings()
            return True
            
        except Exception as e:
            print(f"   ❌ Exception with camera {index}: {e}")
            return False
    
    def configure_camera_settings(self):
        """Configure camera with optimal settings"""
        if self.cameras.get('pc_camera') is None:
            return
            
        camera = self.cameras['pc_camera']
        
        try:
            # Set optimal resolution and frame rate
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera.set(cv2.CAP_PROP_FPS, 30)
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
            
            # Additional parameters for better performance
            camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            
            print("   ⚙️  Camera configured: 640x480 @ 30fps")
        except Exception as e:
            print(f"   ⚠️  Camera configuration error: {e}")
    
    def get_pc_camera_frame(self):
        """Enhanced PC camera frame capture with recoveries"""
        # If real camera available
        if self.cameras.get('pc_camera') is not None:
            try:
                ret, frame = self.cameras['pc_camera'].read()
                if not ret or frame is None:
                    print("⚠️  Camera read failed, attempting reconnection...")
                    self.attempt_camera_reconnection()
                    return self.create_placeholder_frame('pc')
                
                # Process and return clean image
                return self.process_clean_pc_frame(frame)
                
            except Exception as e:
                print(f"❌ PC camera capture error: {e}")
                self.camera_stats['pc_camera']['errors'] += 1
                self.attempt_camera_reconnection()
                return self.create_placeholder_frame('pc')
        
        # If simulated camera mode
        elif self.mock_camera_active:
            return self.create_mock_pc_frame()
        
        # Fallback to placeholder
        else:
            return self.create_placeholder_frame('pc')
    
    def process_clean_pc_frame(self, frame):
        """Process real PC camera frame (clean for YOLO)"""
        # Clean image processing
        height, width = frame.shape[:2]
        
        # Minimal overlay
        cv2.rectangle(frame, (0, 0), (width, 25), (0, 0, 0), -1)
        cv2.putText(frame, f'PC Camera - {datetime.now().strftime("%H:%M:%S")}', 
                   (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # YOLO ready indicator
        cv2.putText(frame, 'YOLO Ready', (width-100, 18), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        # Connection status indicator
        status_color = (0, 255, 0)  # Green for connected
        cv2.circle(frame, (width-20, 35), 5, status_color, -1)
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        self.camera_stats['pc_camera']['frames_captured'] += 1
        return buffer.tobytes()
    
    def create_mock_pc_frame(self):
        """Create simulated PC camera frame for testing"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Create test pattern
        frame[:] = (30, 30, 30)  # Dark gray background
        
        # Add moving test objects
        current_time = time.time()
        for i in range(3):
            x = int(100 + i * 200 + 50 * np.sin(current_time + i))
            y = int(200 + 30 * np.cos(current_time * 1.5 + i))
            
            # Test object
            color = [(0, 150, 255), (255, 150, 0), (150, 255, 0)][i]
            cv2.rectangle(frame, (x-25, y-20), (x+25, y+20), color, -1)
            cv2.putText(frame, f'TEST-{i+1}', (x-20, y+5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Add test grid
        for i in range(0, 640, 80):
            cv2.line(frame, (i, 0), (i, 480), (50, 50, 50), 1)
        for i in range(0, 480, 60):
            cv2.line(frame, (0, i), (640, i), (50, 50, 50), 1)
        
        # Simulated camera overlay
        height, width = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (width, 25), (0, 0, 0), -1)
        cv2.putText(frame, f'SIMULATED PC CAMERA - {datetime.now().strftime("%H:%M:%S")}', 
                   (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)
        cv2.putText(frame, 'TEST MODE', (width-100, 18), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 100, 100), 1)
        
        # Simulated status indicator
        cv2.circle(frame, (width-20, 35), 5, (255, 200, 0), -1)  # Orange for simulated
        
        _, buffer = cv2.imencode('.jpg', frame)
        self.camera_stats['pc_camera']['frames_captured'] += 1
        return buffer.tobytes()
    
    def attempt_camera_reconnection(self):
        """Camera reconnection attempt with rate limiting"""
        current_time = time.time()
        
        # Limit reconnection attempts
        if current_time - self.last_reconnect_attempt < self.reconnect_interval:
            return
        
        self.last_reconnect_attempt = current_time
        print("🔄 Attempting camera reconnection...")
        
        if self.cameras.get('pc_camera'):
            self.cameras['pc_camera'].release()
            self.cameras['pc_camera'] = None
        
        # Wait a moment
        time.sleep(2)
        
        # Try to reinitialize
        success = self.try_camera_with_index(0)
        if not success:
            success = self.try_camera_with_index(1)
        
        if not success:
            print("❌ Camera reconnection failed - switching to simulated mode")
            self.mock_camera_active = True
        else:
            print("✅ Camera reconnection successful")
            self.mock_camera_active = False
    
    def get_underwater_camera_frame(self):
        """Generate simulated underwater camera feed with marine life effects"""
        try:
            # Create underwater base scene (blue-green background)
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (40, 60, 20)  # Dark blue-green underwater color
            
            # Add animated "bubbles" and marine particles
            current_time = time.time()
            for i in range(15):
                # Animated bubbles rising
                x = int(50 + i * 40 + 20 * np.sin(current_time * 2 + i))
                y = int(400 - (current_time * 50 + i * 30) % 480)
                bubble_size = random.randint(2, 6)
                cv2.circle(frame, (x, y), bubble_size, (200, 255, 200), -1)
            
            # Add simulated fish detection boxes
            fish_types = ['Fish', 'Shark', 'Turtle', 'Jellyfish', 'Ray']
            for i in range(3):
                fish_x = int(200 + i * 150 + 50 * np.sin(current_time + i))
                fish_y = int(200 + 50 * np.cos(current_time * 1.5 + i))
                
                # Fish detection box
                detection_color = (0, 255, 255) if i % 2 == 0 else (255, 255, 0)
                cv2.rectangle(frame, (fish_x-30, fish_y-20), (fish_x+30, fish_y+20), detection_color, 2)
                
                fish_type = fish_types[i % len(fish_types)]
                confidence = random.randint(85, 98)
                cv2.putText(frame, f'{fish_type} {confidence}%', (fish_x-25, fish_y-25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, detection_color, 1)
            
            # Add floating particles
            for i in range(20):
                particle_x = int(random.randint(0, 640))
                particle_y = int(random.randint(0, 480))
                cv2.circle(frame, (particle_x, particle_y), 1, (100, 150, 100), -1)
            
            # Underwater camera overlay
            height, width = frame.shape[:2]
            cv2.rectangle(frame, (0, 0), (width, 30), (0, 0, 0), -1)
            cv2.putText(frame, f'Underwater Camera - {datetime.now().strftime("%H:%M:%S")}', 
                       (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            # Depth and clarity indicators
            depth = f"Depth: {random.randint(12, 18)}.{random.randint(0, 9)}m"
            clarity = f"Clarity: {random.randint(70, 90)}%"
            cv2.putText(frame, depth, (10, height-30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
            cv2.putText(frame, clarity, (10, height-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
            
            # Encode image
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            self.camera_stats['underwater_camera']['frames_captured'] += 1
            return buffer.tobytes()
            
        except Exception as e:
            print(f"❌ Underwater image generation error: {e}")
            self.camera_stats['underwater_camera']['errors'] += 1
            return self.create_placeholder_frame('underwater')
    
    def create_placeholder_frame(self, camera_type):
        """Create placeholder image when camera unavailable"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Colored background according to camera type
        if camera_type == 'pc':
            frame[:] = (50, 50, 150)  # Red-purple
            message_lines = [
                "PC CAMERA",
                "NOT AVAILABLE",
                "Check connection",
                "or permissions"
            ]
            color = (255, 255, 255)
        else:
            frame[:] = (50, 100, 100)  # Blue-green
            message_lines = [
                "UNDERWATER CAMERA", 
                "SIMULATION ERROR",
                "Restarting..."
            ]
            color = (200, 255, 200)
        
        # Error messages
        y_offset = 180
        for i, line in enumerate(message_lines):
            cv2.putText(frame, line, (50, y_offset + i * 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # Timestamp
        cv2.putText(frame, datetime.now().strftime("%H:%M:%S"), (270, 350), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1)
        
        # Auto-reconnection indicator
        if camera_type == 'pc':
            next_attempt = int(self.reconnect_interval - (time.time() - self.last_reconnect_attempt))
            if next_attempt > 0:
                cv2.putText(frame, f"Reconnecting in: {next_attempt}s", (150, 400), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()
    
    def generate_camera_stream(self, camera_type):
        """Generator for camera streaming"""
        print(f"🎬 Starting camera stream {camera_type}...")
        
        frame_count = 0
        while True:
            try:
                if camera_type == 'pc':
                    frame = self.get_pc_camera_frame()
                elif camera_type == 'underwater':
                    frame = self.get_underwater_camera_frame()
                else:
                    frame = self.create_placeholder_frame('unknown')
                
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                
                frame_count += 1
                
                # Auto-reconnection attempt every 1000 frames if in simulated mode
                if camera_type == 'pc' and self.mock_camera_active and frame_count % 1000 == 0:
                    threading.Thread(target=self.attempt_camera_reconnection, daemon=True).start()
                
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"❌ Stream error for {camera_type}: {e}")
                time.sleep(1)
    
    def get_camera_statistics(self, camera_type):
        """Get detailed statistics for specific camera"""
        if camera_type not in self.camera_stats:
            return None
            
        stats = self.camera_stats[camera_type]
        uptime = time.time() - stats['start_time']
        
        base_stats = {
            'frames_captured': stats['frames_captured'],
            'errors': stats['errors'],
            'uptime_seconds': int(uptime),
            'fps_average': round(stats['frames_captured'] / max(uptime, 1), 2),
            'error_rate': round(stats['errors'] / max(stats['frames_captured'], 1) * 100, 2)
        }
        
        # Add specific info according to type
        if camera_type == 'pc_camera':
            base_stats.update({
                'connection_status': 'real' if self.cameras.get('pc_camera') else 'mock' if self.mock_camera_active else 'disconnected',
                'last_reconnect': int(time.time() - self.last_reconnect_attempt) if self.last_reconnect_attempt > 0 else 'never',
                'next_reconnect_in': max(0, int(self.reconnect_interval - (time.time() - self.last_reconnect_attempt))) if self.mock_camera_active else 'n/a'
            })
        
        return base_stats
    
    def get_diagnostic_info(self):
        """Get comprehensive diagnostic information"""
        return {
            'opencv_version': cv2.__version__,
            'platform': f"{platform.system()} {platform.release()}",
            'python_version': sys.version.split()[0],
            'pc_camera_status': 'connected' if self.cameras.get('pc_camera') else 'mock' if self.mock_camera_active else 'unavailable',
            'underwater_camera_status': 'simulated',
            'available_cameras': self.scan_available_cameras(),
            'camera_stats': {
                'pc_camera': self.get_camera_statistics('pc_camera'),
                'underwater_camera': self.get_camera_statistics('underwater_camera')
            },
            'system_info': {
                'mock_mode': self.mock_camera_active,
                'last_reconnect': self.last_reconnect_attempt,
                'reconnect_interval': self.reconnect_interval
            }
        }
    
    def release_cameras(self):
        """Clean shutdown of all cameras"""
        print("📹 Releasing camera resources...")
        if self.cameras.get('pc_camera'):
            self.cameras['pc_camera'].release()
        cv2.destroyAllWindows()
        print("✅ Cameras released successfully")

class EnhancedLiDARSystem:
    """
    Enhanced LiDAR System with hidden mapping capabilities
    - Manages LiDAR data collection and processing
    - Provides hidden map visualization
    - Simulates real-world marine scanning
    """
    
    def __init__(self):
        self.hidden_map_data = self.generate_hidden_map_data()
        self.scan_history = []
        self.classified_objects = []
        self.generate_initial_scan_data()
    
    def generate_hidden_map_data(self):
        """Generate comprehensive hidden map data for the area"""
        # Generate a realistic underwater topography map
        map_data = {
            'bathymetry': [],  # Depth measurements
            'structures': [],  # Underwater structures
            'hazards': [],     # Navigation hazards
            'wildlife_zones': [], # Known wildlife areas
            'scan_grid': []    # Regular scanning grid
        }
        
        # Generate bathymetry data (depth measurements)
        for i in range(-100, 101, 10):  # 200m x 200m area
            for j in range(-100, 101, 10):
                depth = abs(20 + 15 * np.sin(i/50) + 10 * np.cos(j/30) + random.uniform(-3, 3))
                map_data['bathymetry'].append({
                    'x': i, 'y': j, 'depth': round(depth, 1),
                    'sediment_type': random.choice(['sand', 'rock', 'coral', 'mud']),
                    'last_scan': datetime.now() - timedelta(minutes=random.randint(1, 120))
                })
        
        # Generate underwater structures
        structures = [
            {'x': -45, 'y': 30, 'type': 'shipwreck', 'size': 'large', 'classification': 'historical'},
            {'x': 20, 'y': -60, 'type': 'coral_reef', 'size': 'medium', 'classification': 'biological'},
            {'x': 80, 'y': 40, 'type': 'artificial_reef', 'size': 'small', 'classification': 'human-made'},
            {'x': -70, 'y': -20, 'type': 'rock_formation', 'size': 'large', 'classification': 'geological'},
            {'x': 10, 'y': 85, 'type': 'underwater_cable', 'size': 'linear', 'classification': 'infrastructure'}
        ]
        
        for struct in structures:
            struct.update({
                'confidence': random.randint(85, 98),
                'last_detected': datetime.now() - timedelta(hours=random.randint(1, 24)),
                'threat_level': random.choice(['none', 'low', 'medium', 'high']),
                'hidden_details': f"Classified data for {struct['type']}"
            })
        
        map_data['structures'] = structures
        
        # Generate hazards
        hazards = [
            {'x': -30, 'y': -80, 'type': 'shallow_water', 'severity': 'high'},
            {'x': 60, 'y': 20, 'type': 'strong_current', 'severity': 'medium'},
            {'x': -15, 'y': 70, 'type': 'debris_field', 'severity': 'medium'},
            {'x': 90, 'y': -40, 'type': 'magnetic_anomaly', 'severity': 'low'}
        ]
        
        for hazard in hazards:
            hazard.update({
                'first_detected': datetime.now() - timedelta(days=random.randint(1, 30)),
                'last_confirmed': datetime.now() - timedelta(hours=random.randint(1, 48)),
                'status': random.choice(['active', 'monitored', 'archived'])
            })
        
        map_data['hazards'] = hazards
        
        # Generate wildlife zones
        wildlife_zones = [
            {'x': 25, 'y': 55, 'species': 'dolphin_pod', 'population': 12, 'activity': 'feeding'},
            {'x': -40, 'y': 15, 'species': 'sea_turtle', 'population': 3, 'activity': 'nesting'},
            {'x': 70, 'y': -25, 'species': 'shark', 'population': 2, 'activity': 'patrolling'},
            {'x': -10, 'y': -50, 'species': 'fish_school', 'population': 150, 'activity': 'schooling'}
        ]
        
        for zone in wildlife_zones:
            zone.update({
                'monitoring_priority': random.choice(['low', 'medium', 'high']),
                'last_sighting': datetime.now() - timedelta(minutes=random.randint(5, 180)),
                'behavior_pattern': f"Regular {zone['activity']} behavior observed",
                'conservation_status': random.choice(['stable', 'protected', 'endangered'])
            })
        
        map_data['wildlife_zones'] = wildlife_zones
        
        # Generate scan grid
        for i in range(-90, 91, 30):
            for j in range(-90, 91, 30):
                scan_point = {
                    'x': i, 'y': j,
                    'last_scan': datetime.now() - timedelta(minutes=random.randint(1, 60)),
                    'scan_quality': random.randint(75, 98),
                    'anomalies_detected': random.randint(0, 3),
                    'classification': 'routine'
                }
                if random.random() < 0.1:  # 10% chance of interesting findings
                    scan_point['classification'] = 'anomaly_detected'
                    scan_point['hidden_notes'] = f"Classified anomaly at {i},{j}"
                
                map_data['scan_grid'].append(scan_point)
        
        return map_data
    
    def generate_initial_scan_data(self):
        """Generate initial LiDAR scan data"""
        # Generate recent scan history
        for i in range(50):
            scan_time = datetime.now() - timedelta(minutes=i*2)
            scan_data = {
                'timestamp': scan_time,
                'objects_detected': random.randint(3, 12),
                'max_range_used': f"{random.randint(120, 200)}m",
                'scan_resolution': f"{random.uniform(0.08, 0.15):.2f}°",
                'quality_score': random.randint(88, 98),
                'anomalies': []
            }
            
            # Add some anomalies
            if random.random() < 0.3:  # 30% chance
                anomaly_types = ['unidentified_object', 'unusual_reflection', 'signal_interference', 'multiple_targets']
                scan_data['anomalies'].append({
                    'type': random.choice(anomaly_types),
                    'confidence': random.randint(70, 95),
                    'requires_investigation': random.choice([True, False])
                })
            
            self.scan_history.append(scan_data)
        
        # Generate classified objects
        classified_objects = [
            {'id': 'OBJ-001', 'type': 'Commercial Vessel', 'distance': '145.2m', 'bearing': '045°', 'speed': '12 knots', 'classification': 'civilian'},
            {'id': 'OBJ-002', 'type': 'Submarine Contact', 'distance': '890.5m', 'bearing': '270°', 'speed': '8 knots', 'classification': 'military'},
            {'id': 'OBJ-003', 'type': 'Floating Debris', 'distance': '67.1m', 'bearing': '180°', 'speed': '2 knots', 'classification': 'hazard'},
            {'id': 'OBJ-004', 'type': 'Whale Pod', 'distance': '234.8m', 'bearing': '320°', 'speed': '5 knots', 'classification': 'marine_life'},
            {'id': 'OBJ-005', 'type': 'Research Buoy', 'distance': '423.6m', 'bearing': '090°', 'speed': '0 knots', 'classification': 'scientific'}
        ]
        
        for obj in classified_objects:
            obj.update({
                'first_detected': datetime.now() - timedelta(minutes=random.randint(5, 120)),
                'last_updated': datetime.now() - timedelta(seconds=random.randint(1, 60)),
                'confidence': random.randint(85, 98),
                'threat_assessment': random.choice(['none', 'low', 'medium', 'high']),
                'tracking_status': random.choice(['active', 'passive', 'lost']),
                'hidden_intel': f"Classified information for {obj['id']}"
            })
        
        self.classified_objects = classified_objects
    
    def get_hidden_map_data(self):
        """Return comprehensive hidden map data"""
        return {
            'map_data': self.hidden_map_data,
            'current_scan': self.get_current_scan_data(),
            'classified_objects': self.classified_objects,
            'scan_statistics': self.get_scan_statistics(),
            'threat_assessment': self.get_threat_assessment()
        }
    
    def get_current_scan_data(self):
        """Generate current real-time scan data"""
        return {
            'active_scan_sector': f"{random.randint(0, 359)}° - {random.randint(0, 359)}°",
            'scan_range': f"{random.randint(150, 200)}m",
            'resolution': f"{random.uniform(0.08, 0.15):.2f}°",
            'rotation_speed': f"{random.randint(8, 12)} RPM",
            'data_points_per_second': f"{random.randint(50000, 80000):,}",
            'current_targets': random.randint(5, 15),
            'signal_strength': f"{random.randint(85, 98)}%",
            'interference_level': f"{random.randint(2, 8)}%"
        }
    
    def get_scan_statistics(self):
        """Generate scanning statistics"""
        return {
            'total_scans_today': random.randint(400, 600),
            'objects_tracked': random.randint(25, 45),
            'anomalies_detected': random.randint(8, 18),
            'classification_accuracy': f"{random.uniform(92, 97):.1f}%",
            'system_uptime': f"{random.uniform(98, 99.5):.1f}%",
            'data_processed_gb': f"{random.uniform(45, 85):.1f} GB",
            'false_positive_rate': f"{random.uniform(2, 5):.1f}%"
        }
    
    def get_threat_assessment(self):
        """Generate current threat assessment"""
        threat_levels = ['GREEN', 'YELLOW', 'ORANGE', 'RED']
        current_threat = random.choice(threat_levels[:3])  # Avoid RED for demo
        
        return {
            'overall_threat_level': current_threat,
            'active_threats': random.randint(0, 3),
            'monitored_contacts': random.randint(5, 12),
            'restricted_zones': random.randint(2, 5),
            'last_threat_update': datetime.now() - timedelta(minutes=random.randint(1, 15)),
            'next_assessment': datetime.now() + timedelta(minutes=30),
            'classification_confidence': f"{random.randint(88, 96)}%"
        }

class MarineDetectionSystem:
    """
    Marine Detection and Tracking System
    - Manages object detection data
    - Provides real-time activity logging
    - Simulates marine life and vessel detection
    """
    
    def __init__(self):
        self.detections = [
            {
                'id': 'UW-002',
                'source': 'Underwater',
                'type': 'Fish School',
                'distance': '12.7m',
                'confidence': 96,
                'status': 'Tracking',
                'timestamp': datetime.now().strftime('%H:%M:%S')
            },
            {
                'id': 'L1-003',
                'source': 'LiDAR',
                'type': 'Vessel',
                'distance': '120.1m',
                'confidence': 89,
                'status': 'Monitoring',
                'timestamp': datetime.now().strftime('%H:%M:%S')
            },
            {
                'id': 'UW-004',
                'source': 'Underwater',
                'type': 'Debris',
                'distance': '8.3m',
                'confidence': 78,
                'status': 'Alert',
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
        ]
        
        # Helper function to safely subtract minutes from current time
        now = datetime.now()
        
        self.activity_log = [
            {
                'time': now.strftime('%H:%M:%S'),
                'icon': 'fish',
                'type': 'underwater',
                'title': 'Fish school identified',
                'description': 'Large school detected underwater',
                'details': 'Distance: 12.7m, Count: ~50 fish',
                'priority': 'low'
            },
            {
                'time': (now - timedelta(minutes=3)).strftime('%H:%M:%S'),
                'icon': 'ship',
                'type': 'lidar',
                'title': 'Vessel approaching',
                'description': 'Large vessel detected by LiDAR',
                'details': 'Distance: 120.1m, Speed: 15 knots',
                'priority': 'high'
            },
            {
                'time': (now - timedelta(minutes=5)).strftime('%H:%M:%S'),
                'icon': 'exclamation-triangle',
                'type': 'alert',
                'title': 'Debris alert',
                'description': 'Floating debris detected',
                'details': 'Navigation hazard identified',
                'priority': 'high'
            },
            {
                'time': (now - timedelta(minutes=7)).strftime('%H:%M:%S'),
                'icon': 'radar',
                'type': 'system',
                'title': 'System calibration',
                'description': 'Auto-calibration completed',
                'details': 'All sensors operational',
                'priority': 'low'
            }
        ]
        
        self.system_stats = {
            'total_detections_today': 185,
            'session_detections': 67,
            'active_alerts': 2,
            'system_uptime': 99.2,
            'last_updated': datetime.now()
        }
    
    def get_updated_detections(self):
        """Get real-time updated detection data with dynamic changes"""
        updated_detections = []
        
        for detection in self.detections:
            updated_detection = detection.copy()
            
            # Simulate dynamic distance changes
            base_distance = float(detection['distance'][:-1])
            distance_variation = random.uniform(-1.5, 1.5)
            new_distance = max(0.1, base_distance + distance_variation)
            updated_detection['distance'] = f"{new_distance:.1f}m"
            
            # Simulate confidence fluctuations
            base_confidence = detection['confidence']
            confidence_variation = random.randint(-5, 3)
            new_confidence = max(70, min(99, base_confidence + confidence_variation))
            updated_detection['confidence'] = new_confidence
            
            # Update timestamp
            updated_detection['timestamp'] = datetime.now().strftime('%H:%M:%S')
            
            # Occasionally change status
            if random.random() < 0.1:  # 10% chance
                statuses = ['Active', 'Tracking', 'Monitoring', 'Alert']
                updated_detection['status'] = random.choice(statuses)
            
            updated_detections.append(updated_detection)
        
        return updated_detections

# Initialize system components
camera_manager = EnhancedCameraManager()
detection_system = MarineDetectionSystem()
lidar_system = EnhancedLiDARSystem()

# ===============================
# FLASK ROUTES
# ===============================

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/video_feed/<camera_type>')
def video_feed(camera_type):
    """
    Live video streaming endpoint
    Supports: 'pc' for laptop camera, 'underwater' for simulated camera
    """
    if camera_type in ['pc', 'underwater']:
        return Response(
            camera_manager.generate_camera_stream(camera_type),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    else:
        return "Invalid camera type", 404

@app.route('/lidar')
def lidar_viewer():
    """LiDAR 3D viewer page"""
    return render_template('lidar_viewer.html')

@app.route('/lidar/hidden')
def hidden_lidar_map():
    """Hidden LiDAR map and classified data viewer"""
    return render_template('hidden_lidar_map.html')

# ===============================
# API ENDPOINTS
# ===============================

@app.route('/api/time')
def api_current_time():
    """Get current system time"""
    return jsonify({
        'time': datetime.now().strftime('%H:%M:%S'),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/stats')
def api_system_stats():
    """Get overall system statistics"""
    stats = detection_system.system_stats.copy()
    
    # Dynamic updates
    stats['total_detections_today'] += random.randint(-2, 5)
    stats['session_detections'] += random.randint(-1, 3)
    stats['active_alerts'] = max(0, stats['active_alerts'] + random.randint(-1, 1))
    stats['system_uptime'] = round(random.uniform(98.5, 99.9), 1)
    stats['last_updated'] = datetime.now().isoformat()
    
    return jsonify(stats)

@app.route('/api/detections')
def api_detections():
    """Get current active detections"""
    return jsonify(detection_system.get_updated_detections())

@app.route('/api/activity')
def api_activity_log():
    """Get recent system activity log"""
    return jsonify(detection_system.activity_log[:20])

@app.route('/api/camera/<int:camera_id>/stats')
def api_camera_stats(camera_id):
    """Get detailed statistics for specific camera"""
    if camera_id == 1:  # PC Camera
        pc_camera_connected = camera_manager.cameras.get('pc_camera') is not None
        pc_camera_mock = camera_manager.mock_camera_active
        
        if pc_camera_connected:
            status = 'Online'
            connection_type = 'Hardware'
        elif pc_camera_mock:
            status = 'Simulated'
            connection_type = 'Simulated'
        else:
            status = 'Offline'
            connection_type = 'Disconnected'
        
        base_stats = {
            'camera_name': 'PC Laptop Camera',
            'camera_type': connection_type,
            'connected': pc_camera_connected or pc_camera_mock,
            'resolution': '640x480',
            'fps_target': 30,
            'status': status
        }
        
        detailed_stats = camera_manager.get_camera_statistics('pc_camera')
        if detailed_stats:
            base_stats.update({
                'active_objects': random.randint(0, 5) if pc_camera_connected else 3,
                'accuracy': round(random.uniform(88, 96), 1) if pc_camera_connected else 95.0,
                'frames_processed': detailed_stats['frames_captured'],
                'uptime_seconds': detailed_stats['uptime_seconds'],
                'error_rate': detailed_stats['error_rate'],
                'connection_status': detailed_stats.get('connection_status', 'unknown'),
                'next_reconnect_in': detailed_stats.get('next_reconnect_in', 'n/a')
            })
        else:
            base_stats.update({
                'active_objects': 0,
                'accuracy': 0,
                'frames_processed': 0,
                'uptime_seconds': 0,
                'error_rate': 100
            })
            
        return jsonify(base_stats)
        
    elif camera_id == 2:  # Underwater camera
        underwater_stats = camera_manager.get_camera_statistics('underwater_camera')
        return jsonify({
            'camera_name': 'Underwater Camera',
            'camera_type': 'Simulated',
            'connected': True,
            'resolution': '640x480',
            'fps_target': 30,
            'status': 'Simulation Active',
            'active_objects': random.randint(2, 8),
            'accuracy': round(random.uniform(89, 95), 1),
            'frames_processed': underwater_stats['frames_captured'] if underwater_stats else 0,
            'uptime_seconds': underwater_stats['uptime_seconds'] if underwater_stats else 0,
            'error_rate': underwater_stats['error_rate'] if underwater_stats else 0,
            'depth': f"{random.randint(12, 18)}.{random.randint(0, 9)}m",
            'water_clarity': f"{random.randint(70, 90)}%",
            'temperature': f"{random.randint(8, 14)}°C"
        })
    else:
        return jsonify({'error': 'Camera not found'}), 404

@app.route('/api/cameras/status')
def api_all_cameras_status():
    """Get status overview of all cameras"""
    pc_real = camera_manager.cameras.get('pc_camera') is not None
    pc_mock = camera_manager.mock_camera_active
    pc_status = 'online' if pc_real else 'mock' if pc_mock else 'offline'
    
    return jsonify({
        'total_cameras': 2,
        'active_cameras': 2,
        'cameras': {
            'pc_camera': {
                'id': 1,
                'name': 'PC Laptop Camera',
                'status': pc_status,
                'type': 'hardware' if pc_real else 'simulated',
                'location': 'Surface',
                'mode': 'real' if pc_real else 'mock' if pc_mock else 'disconnected'
            },
            'underwater_camera': {
                'id': 2,
                'name': 'Underwater Camera',
                'status': 'simulated',
                'type': 'simulated',
                'location': 'Underwater',
                'mode': 'simulation'
            }
        }
    })

@app.route('/api/camera/diagnostics')
def api_camera_diagnostics():
    """Get comprehensive camera diagnostic information"""
    return jsonify(camera_manager.get_diagnostic_info())

@app.route('/api/lidar')
def api_lidar_stats():
    """Get LiDAR system statistics"""
    return jsonify({
        'system_name': 'Marine LiDAR Scanner',
        'status': 'Active',
        'objects_detected': random.randint(8, 18),
        'max_range': '200m',
        'current_range': f"{random.randint(120, 180)}m",
        'scan_rate': '10 Hz',
        'resolution': '0.1°',
        'accuracy': f"{random.uniform(95, 99):.1f}%",
        'power_consumption': f"{random.uniform(45, 55):.1f}W",
        'temperature': f"{random.randint(35, 42)}°C",
        'last_calibration': (datetime.now() - timedelta(hours=2)).strftime('%H:%M:%S')
    })

@app.route('/api/lidar/hidden')
def api_hidden_lidar_data():
    """Get comprehensive hidden LiDAR map data - CLASSIFIED ACCESS"""
    # Simulate access control
    access_key = request.args.get('access_key', '')
    if access_key != 'MARINE_CLASSIFIED_2024':
        return jsonify({'error': 'Unauthorized access', 'code': 'ACCESS_DENIED'}), 403
    
    return jsonify(lidar_system.get_hidden_map_data())

@app.route('/api/lidar/classified_objects')
def api_classified_objects():
    """Get classified object tracking data"""
    access_key = request.args.get('access_key', '')
    if access_key != 'MARINE_CLASSIFIED_2024':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    # Add some dynamic changes to classified objects
    classified_objects = []
    for obj in lidar_system.classified_objects:
        updated_obj = obj.copy()
        
        # Update distances and bearings slightly
        base_distance = float(obj['distance'][:-1])
        new_distance = base_distance + random.uniform(-5, 5)
        updated_obj['distance'] = f"{max(10, new_distance):.1f}m"
        
        # Update timestamp
        updated_obj['last_updated'] = datetime.now() - timedelta(seconds=random.randint(1, 30))
        updated_obj['last_updated'] = updated_obj['last_updated'].strftime('%H:%M:%S')
        
        classified_objects.append(updated_obj)
    
    return jsonify(classified_objects)

@app.route('/api/system/health')
def api_system_health():
    """Get overall system health status"""
    camera_diagnostics = camera_manager.get_diagnostic_info()
    
    # Calculate health score
    health_score = 100
    if camera_diagnostics['pc_camera_status'] == 'mock':
        health_score -= 20
    elif camera_diagnostics['pc_camera_status'] == 'unavailable':
        health_score -= 40
    
    # Add error statistics
    pc_stats = camera_diagnostics['camera_stats']['pc_camera']
    if pc_stats and pc_stats['error_rate'] > 5:
        health_score -= min(30, pc_stats['error_rate'] * 2)
    
    status = 'Excellent' if health_score >= 90 else 'Good' if health_score >= 70 else 'Degraded' if health_score >= 50 else 'Critical'
    
    return jsonify({
        'overall_health': health_score,
        'status': status,
        'components': {
            'pc_camera': {
                'status': camera_diagnostics['pc_camera_status'],
                'health': 100 if camera_diagnostics['pc_camera_status'] == 'connected' else 60 if camera_diagnostics['pc_camera_status'] == 'mock' else 0
            },
            'underwater_camera': {
                'status': 'simulated',
                'health': 100
            },
            'lidar_system': {
                'status': 'active',
                'health': random.randint(95, 100)
            },
            'detection_system': {
                'status': 'active',
                'health': random.randint(92, 98)
            }
        },
        'uptime': int(time.time() - camera_diagnostics['camera_stats']['pc_camera']['uptime_seconds']) if camera_diagnostics['camera_stats']['pc_camera'] else 0,
        'last_check': datetime.now().isoformat()
    })

# ===============================
# ERROR HANDLERS
# ===============================

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Page not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ===============================
# SHUTDOWN HANDLERS
# ===============================

def cleanup_resources():
    """Clean up all system resources on shutdown"""
    print("🧹 Cleaning up system resources...")
    camera_manager.release_cameras()
    print("✅ Cleanup completed")

# Register cleanup function
atexit.register(cleanup_resources)

# ===============================
# MAIN APPLICATION ENTRY POINT
# ===============================

if __name__ == '__main__':
    print("🌊 ENHANCED MARINE SURVEILLANCE SYSTEM")
    print("=" * 60)
    
    # Display camera diagnostics
    print("\n📊 CAMERA DIAGNOSTICS:")
    diagnostics = camera_manager.get_diagnostic_info()
    print(f"OpenCV Version: {diagnostics['opencv_version']}")
    print(f"Platform: {diagnostics['platform']}")
    print(f"Python Version: {diagnostics['python_version']}")
    print(f"PC Camera Status: {diagnostics['pc_camera_status']}")
    print(f"Underwater Camera Status: {diagnostics['underwater_camera_status']}")
    
    if diagnostics['pc_camera_status'] == 'mock':
        print("⚠️  PC CAMERA IN SIMULATED MODE - Auto-reconnection attempts enabled")
    elif diagnostics['pc_camera_status'] == 'connected':
        print("✅ PC CAMERA CONNECTED - Ready for YOLO integration")
    
    print(f"\nDetected available cameras: {len(diagnostics['available_cameras'])}")
    for cam in diagnostics['available_cameras']:
        print(f"   • Index {cam['index']}: {cam['resolution']}")
    
    print("\n🚀 Starting Flask application...")
    print("📍 Dashboard: http://localhost:5002")
    print("📹 PC Camera Feed: http://localhost:5002/video_feed/pc")
    print("🌊 Underwater Feed: http://localhost:5002/video_feed/underwater")
    print("🎯 LiDAR Viewer: http://localhost:5002/lidar")
    print("🔒 Hidden LiDAR Map: http://localhost:5002/lidar/hidden")
    print("📊 API Endpoints:")
    print("   • /api/stats - System statistics")
    print("   • /api/detections - Active detections")
    print("   • /api/activity - Activity log")
    print("   • /api/cameras/status - Camera status")
    print("   • /api/camera/diagnostics - Detailed diagnostics")
    print("   • /api/system/health - System health status")
    print("   • /api/lidar/hidden - Hidden map data (requires access key)")
    print("   • /api/lidar/classified_objects - Classified tracking data")
    print("=" * 60)
    
    try:
        # Launch Flask application
        app.run(
            debug=True,          # Enable debug mode for development
            host='0.0.0.0',      # Allow connections from any IP
            port=5002,           # Port number
            threaded=True,       # Enable threading for concurrent requests
            use_reloader=False   # Disable reloader to avoid camera issues
        )
    except KeyboardInterrupt:
        print("\n🛑 Shutdown signal received...")
        cleanup_resources()
        print("👋 Marine Surveillance System stopped")
    except Exception as e:
        print(f"❌ Application error: {e}")
        cleanup_resources()