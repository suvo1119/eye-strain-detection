#!/usr/bin/env python3
"""
Flask API Backend for Eye Strain Detection
Wraps main.py functionality and exposes REST endpoints
"""
from dotenv import load_dotenv
load_dotenv()  # This line loads .env file
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import timedelta
import cv2
import numpy as np
import os
import urllib.request
import threading
import time
from collections import deque
from functools import wraps
import uuid

# MediaPipe Tasks will be imported lazily to avoid hard failures when
# optional native dependencies (tensorflow, etc.) are incompatible in the
# environment. The landmarker and related modules are initialized on demand.
base_options_lib = None
face_landmarker = None
mp_image = None
running_mode_lib = None
landmarker = None

# Local imports
from database import db, init_db, User
from auth_routes import auth_bp
from reports_routes import reports_bp, save_eye_strain_data

# Determine if running in production (check multiple platforms)
IS_PRODUCTION = (
    os.environ.get('RAILWAY_ENVIRONMENT') or 
    os.environ.get('RENDER') or 
    os.environ.get('FLASK_ENV') == 'production'
)

# Setup static folder for production (serving React build)
static_folder = 'dist' if IS_PRODUCTION else None
app = Flask(__name__, static_folder=static_folder, static_url_path='')

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-super-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///eye_strain.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-super-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# Initialize extensions
CORS(app)
jwt = JWTManager(app)
init_db(app)

def ensure_guest_user():
    """Ensure a default guest user exists (ID 1)"""
    with app.app_context():
        try:
            guest = User.query.get(1)
            if not guest:
                print("Creating Guest User (ID 1)...")
                guest = User(
                    id=1,
                    full_name='Guest User',
                    username='guest',
                    email='guest@example.com',
                    mobile='0000000000',
                    password_hash='dummy_hash'
                )
                db.session.add(guest)
                db.session.commit()
                print("Guest User created.")
        except Exception as e:
            print(f"Error checking guest user: {e}")

# Create guest user on startup
ensure_guest_user()

socketio = SocketIO(app, cors_allowed_origins="*")

# Register blueprints FIRST (before catch-all routes)
app.register_blueprint(auth_bp)
app.register_blueprint(reports_bp)

# Serve React App in production (only for non-API routes)
@app.route('/')
def serve_react():
    if IS_PRODUCTION and os.path.exists('dist/index.html'):
        return send_from_directory('dist', 'index.html')
    return jsonify({"message": "Eye Strain Detection API", "status": "running"})

@app.route('/<path:path>')
def serve_static(path):
    # Don't intercept API routes - let blueprints handle them
    if path.startswith('api/'):
        return jsonify({"error": "API endpoint not found"}), 404
    
    if IS_PRODUCTION:
        # Try to serve the file from dist folder
        if os.path.exists(os.path.join('dist', path)):
            return send_from_directory('dist', path)
        # For React Router - serve index.html for all routes
        return send_from_directory('dist', 'index.html')
    return jsonify({"error": "Not found"}), 404

# Model setup
MODEL_FILENAME = "face_landmarker_v2.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-assets/face_landmarker_v2.task"


def ensure_landmarker():
    """Lazily initialize MediaPipe FaceLandmarker. Returns True if ready."""
    global base_options_lib, face_landmarker, mp_image, running_mode_lib, landmarker

    if landmarker is not None:
        return True

    try:
        from mediapipe.tasks.python.core import base_options as base_options_lib_local
        from mediapipe.tasks.python.vision import face_landmarker as face_landmarker_mod
        from mediapipe.tasks.python.vision.core import image as mp_image_mod
        from mediapipe.tasks.python.vision.core import vision_task_running_mode as running_mode_lib_mod
    except Exception as e:
        print(f"MediaPipe import failed: {e}")
        return False

    base_options_lib = base_options_lib_local
    face_landmarker = face_landmarker_mod
    mp_image = mp_image_mod
    running_mode_lib = running_mode_lib_mod

    # Download model if missing
    if not os.path.exists(MODEL_FILENAME):
        try:
            print(f"Downloading {MODEL_FILENAME}...")
            urllib.request.urlretrieve(MODEL_URL, MODEL_FILENAME)
            print("Download complete.")
        except Exception as e:
            print(f"Failed to download model: {e}")
            return False

    try:
        base_options = base_options_lib.BaseOptions(model_asset_path=MODEL_FILENAME)
        options = face_landmarker.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=running_mode_lib.VisionTaskRunningMode.VIDEO,
            num_faces=5,
            min_face_detection_confidence=0.3,
            min_face_presence_confidence=0.3,
            min_tracking_confidence=0.3,
        )
        landmarker = face_landmarker.FaceLandmarker.create_from_options(options)
    except Exception as e:
        print(f"Failed to initialize FaceLandmarker: {e}")
        landmarker = None
        return False

    return True

# Eye strain monitoring settings
WINDOW_SECONDS = 60
BLINK_EAR_THRESH = 0.22  # Increased for better detection over network (was 0.2)
PERCLOS_EAR_THRESH = 0.22  # Increased for better detection over network
MIN_BLINK_DURATION_MS = 30  # Reduced to catch faster blinks (was 50)
MAX_BLINK_DURATION_MS = 600  # Increased to allow for frame timing variance (was 500)

RIGHT_EYE = [362, 385, 387, 263, 373, 380]
LEFT_EYE = [33, 160, 158, 133, 153, 144]

# Global state
monitoring_active = False
# Set default user for no-auth mode
current_user_token = "guest_token"
current_user_id = 1
current_session_id = None  # UUID for current monitoring session
current_metrics = {
    "blinks_per_min": 0,
    "perclos": 0,
    "avg_ear": 0,
    "avg_blink_duration_ms": 0,
    "blinks_in_window": 0,
    "strain_level": "Waiting",
    "strain_color": "#00FF00",
    "faces_detected": 0,
    "image_quality": "Good"
}

# Buffers
frames_buffer = deque()
blink_events = deque()
blink_count = 0
current_blink_start = None
current_frame = None
frame_lock = threading.Lock()


def EAR(landmarks, eye):
    """Calculate Eye Aspect Ratio"""
    p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in eye]
    
    vertical = np.linalg.norm(
        np.array([p2.x, p2.y]) - np.array([p6.x, p6.y])
    )
    horizontal = np.linalg.norm(
        np.array([p1.x, p1.y]) - np.array([p4.x, p4.y])
    )
    
    return vertical / horizontal if horizontal != 0 else 0.0


def check_image_quality(frame):
    """Check image quality and return issues"""
    issues = []
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    brightness = np.mean(gray)
    if brightness < 50:
        issues.append("TOO_DARK")
    
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 100:
        issues.append("BLURRY")
    
    contrast = np.std(gray)
    if contrast < 30:
        issues.append("HAZY")
    
    return issues


def purge_old_entries(now):
    """Remove old entries from buffers"""
    while frames_buffer and frames_buffer[0][0] < now - WINDOW_SECONDS:
        frames_buffer.popleft()
    while blink_events and blink_events[0][0] < now - WINDOW_SECONDS:
        blink_events.popleft()


def compute_metrics():
    """Calculate eye strain metrics"""
    now = time.time()
    purge_old_entries(now)
    frames_len = len(frames_buffer)
    
    if frames_len == 0:
        return {
            "blinks_per_min": 0.0,
            "perclos": 0.0,
            "avg_ear": 0.0,
            "avg_blink_duration_ms": 0.0,
            "blinks_in_window": 0,
        }
    
    perclos = 100.0 * sum(1 for (_, _, closed) in frames_buffer if closed) / frames_len
    avg_ear = sum(v for (_, v, _) in frames_buffer) / frames_len
    blinks_in_window = len(blink_events)
    avg_blink_duration_ms = (
        sum(b[2] for b in blink_events) / blinks_in_window if blinks_in_window > 0 else 0.0
    )
    blinks_per_min = blinks_in_window * (60.0 / WINDOW_SECONDS)
    
    return {
        "blinks_per_min": blinks_per_min,
        "perclos": perclos,
        "avg_ear": avg_ear,
        "avg_blink_duration_ms": avg_blink_duration_ms,
        "blinks_in_window": blinks_in_window,
    }


def strain_level(metrics):
    """Determine strain level from metrics"""
    bpm = metrics["blinks_per_min"]
    per = metrics["perclos"]
    dur = metrics["avg_blink_duration_ms"]
    
    if bpm >= 12 and per < 10 and dur < 300:
        return "Low", "#00FF00"  # green
    if 8 <= bpm < 12 or 10 <= per < 20 or 300 <= dur < 400:
        return "Mild", "#00FFFF"  # yellow
    if bpm < 8 or per >= 20 or dur >= 400:
        return "High", "#0000FF"  # red
    return "Moderate", "#00A5FF"


def process_frame(frame):
    """Process a single frame and return metrics"""
    global blink_count, current_blink_start, current_metrics, current_frame
    
    # Store frame for video streaming
    with frame_lock:
        current_frame = frame.copy()
    # Ensure the MediaPipe landmarker is available
    if not ensure_landmarker():
        current_metrics["strain_level"] = "Mediapipe Unavailable"
        current_metrics["strain_color"] = "#FFA500"
        current_metrics["image_quality"] = "Unavailable"
        current_metrics["faces_detected"] = 0
        return current_metrics

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_img = mp_image.Image(image_format=mp_image.ImageFormat.SRGB, data=rgb)

    now = time.time()
    detection_result = landmarker.detect_for_video(mp_img, int(now * 1000))
    
    # Check image quality
    quality_issues = check_image_quality(frame)
    current_metrics["image_quality"] = "Poor: " + ", ".join(quality_issues) if quality_issues else "Good"
    current_metrics["faces_detected"] = len(detection_result.face_landmarks)
    
    if detection_result.face_landmarks:
        if len(detection_result.face_landmarks) > 1:
            current_metrics["strain_level"] = "Multiple Faces"
            current_metrics["strain_color"] = "#0000FF"
            return current_metrics
        
        landmarks = detection_result.face_landmarks[0]
        ear_left = EAR(landmarks, LEFT_EYE)
        ear_right = EAR(landmarks, RIGHT_EYE)
        ear = (ear_left + ear_right) / 2.0
        
        is_closed = ear < PERCLOS_EAR_THRESH
        
        frames_buffer.append((now, ear, is_closed))
        
        # Blink detection
        if ear < BLINK_EAR_THRESH:
            if current_blink_start is None:
                current_blink_start = now
        else:
            if current_blink_start is not None:
                duration_ms = (now - current_blink_start) * 1000.0
                if MIN_BLINK_DURATION_MS <= duration_ms <= MAX_BLINK_DURATION_MS:
                    blink_events.append((current_blink_start, now, duration_ms))
                    blink_count += 1
                current_blink_start = None
        
        metrics = compute_metrics()
        level_text, level_color = strain_level(metrics)
        
        current_metrics.update({
            "blinks_per_min": round(metrics["blinks_per_min"], 2),
            "perclos": round(metrics["perclos"], 2),
            "avg_ear": round(metrics["avg_ear"], 4),
            "avg_blink_duration_ms": round(metrics["avg_blink_duration_ms"], 1),
            "blinks_in_window": metrics["blinks_in_window"],
            "strain_level": level_text,
            "strain_color": level_color,
            "total_blinks": blink_count,
        })
    else:
        current_metrics["strain_level"] = "No Face"
        current_metrics["strain_color"] = "#FF0000"
    
    return current_metrics


def monitor_webcam():
    """Monitor webcam in background and emit updates"""
    global monitoring_active
    # Ensure mediapipe landmarker is initialized before opening webcam
    if not ensure_landmarker():
        print("Cannot start monitoring: MediaPipe not available or failed to initialize.")
        socketio.emit('error', {'message': 'MediaPipe not available on server environment.'})
        monitoring_active = False
        return

    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Cannot open webcam")
        monitoring_active = False
        socketio.emit('error', {'message': 'Cannot open webcam. Check permissions.'})
        return
    
    # Set camera properties for better performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30.0
    
    print(f"Webcam opened successfully at {fps} FPS")
    frame_idx = 0
    last_save_time = time.time()
    
    try:
        while monitoring_active:
            ret, frame = cap.read()
            if not ret:
                print("Error: Cannot read frame")
                break
            
            metrics = process_frame(frame)
            
            # Emit metrics to all connected clients
            socketio.emit('metrics_update', metrics)
            
            # Save metrics every 30 seconds for authenticated user
            current_time = time.time()
            if current_user_id and current_user_token and (current_time - last_save_time) >= 30:
                try:
                    with app.app_context():
                        save_eye_strain_data(current_user_id, metrics, current_session_id)
                    last_save_time = current_time
                except Exception as e:
                    print(f"Error saving metrics: {e}")
            
            frame_idx += 1
            time.sleep(0.033)  # ~30 FPS
    except Exception as e:
        print(f"Error during monitoring: {e}")
        socketio.emit('error', {'message': f'Monitoring error: {str(e)}'})
    finally:
        cap.release()
        monitoring_active = False
        print("Webcam released")


# Routes
@app.route("/")
def index():
    return jsonify({"status": "Eye Strain Detection API Running"})


@app.route("/api/status")
def get_status():
    """Get current monitoring status"""
    return jsonify({
        "monitoring": monitoring_active,
        "metrics": current_metrics
    })


@app.route("/api/start")
def start_monitoring():
    """Start webcam monitoring"""
    global monitoring_active
    
    if monitoring_active:
        return jsonify({"status": "Already monitoring"}), 400
    
    monitoring_active = True
    thread = threading.Thread(target=monitor_webcam, daemon=True)
    thread.start()
    
    return jsonify({"status": "Monitoring started"})


@app.route("/api/stop")
def stop_monitoring():
    """Stop webcam monitoring"""
    global monitoring_active
    monitoring_active = False
    return jsonify({"status": "Monitoring stopped"})


@app.route("/api/reset")
def reset_metrics():
    """Reset all metrics"""
    global blink_count, current_blink_start
    global frames_buffer, blink_events
    
    blink_count = 0
    current_blink_start = None
    frames_buffer.clear()
    blink_events.clear()
    
    return jsonify({"status": "Metrics reset"})


def generate_frames():
    """Generate MJPEG stream of video frames"""
    while True:
        try:
            with frame_lock:
                if current_frame is None:
                    # Send a blank frame if no camera is active
                    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    ret, buffer = cv2.imencode('.jpg', blank_frame)
                else:
                    ret, buffer = cv2.imencode('.jpg', current_frame)
            
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n'
                       + frame_bytes + b'\r\n')
            
            time.sleep(0.033)  # ~30 FPS
        except Exception as e:
            print(f"Error generating frames: {e}")
            time.sleep(0.1)


@app.route("/video_feed")
def video_feed():
    """Video streaming route"""
    return app.response_class(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


# WebSocket events
@socketio.on('connect')
def handle_connect():
    print("Client connected")
    emit('connection_response', {'data': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")


@socketio.on('start_monitoring')
def handle_start_monitoring(data=None):
    """SocketIO: Start monitoring"""
    global monitoring_active, current_user_id, current_user_token, current_session_id
    
    # Generate a new session ID for this monitoring session
    current_session_id = str(uuid.uuid4())
    
    # Extract user_id from data if provided
    if data and isinstance(data, dict):
        user_id = data.get('user_id')
        token = data.get('token')
        browser_camera = data.get('browser_camera', False)
        if user_id:
            current_user_id = user_id
        if token:
            current_user_token = token
        
        # If using browser camera, don't start webcam thread
        if browser_camera:
            monitoring_active = True
            emit('monitoring_started', {'status': 'Monitoring started', 'user_id': current_user_id, 'session_id': current_session_id})
            return
    
    if not monitoring_active:
        monitoring_active = True
        thread = threading.Thread(target=monitor_webcam, daemon=True)
        thread.start()
    
    emit('monitoring_started', {'status': 'Monitoring started', 'user_id': current_user_id, 'session_id': current_session_id})


# Track last save time for browser camera mode
browser_last_save_time = 0

@socketio.on('process_frame')
def handle_process_frame(data):
    """SocketIO: Process frame from browser camera"""
    global current_metrics, browser_last_save_time, current_user_id, current_session_id
    
    if not monitoring_active:
        return
    
    try:
        # Ensure landmarker is initialized
        if not ensure_landmarker():
            emit('error', {'message': 'Face detection not available'})
            return
        
        # Decode base64 image
        frame_data = data.get('frame', '')
        if not frame_data:
            return
        
        # Remove data URL prefix if present
        if ',' in frame_data:
            frame_data = frame_data.split(',')[1]
        
        import base64
        img_bytes = base64.b64decode(frame_data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            return
        
        # Flip horizontally (mirror) to match browser preview
        frame = cv2.flip(frame, 1)
        
        # Process the frame
        metrics = process_frame(frame)
        current_metrics = metrics
        
        # Emit metrics back to client immediately
        emit('metrics_update', metrics)
        
        # Save metrics every 30 seconds for authenticated user
        current_time = time.time()
        if current_user_id and (current_time - browser_last_save_time) >= 30:
            try:
                with app.app_context():
                    save_eye_strain_data(current_user_id, metrics, current_session_id)
                browser_last_save_time = current_time
            except Exception as e:
                print(f"Error saving metrics: {e}")
                
    except Exception as e:
        print(f"Error processing frame: {e}")


@socketio.on('stop_monitoring')
def handle_stop_monitoring():
    """SocketIO: Stop monitoring"""
    global monitoring_active
    monitoring_active = False
    
    emit('monitoring_stopped', {'status': 'Monitoring stopped'})


@socketio.on('get_metrics')
def handle_get_metrics(data):
    """SocketIO: Get current metrics"""
    emit('metrics_update', current_metrics)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    debug = not IS_PRODUCTION
    print("Starting Eye Strain Detection API Server...")
    print(f"Server running at http://localhost:{port}")
    print(f"Production mode: {IS_PRODUCTION}")
    socketio.run(app, debug=debug, host="0.0.0.0", port=port)

