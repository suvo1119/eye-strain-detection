#!/usr/bin/env python3
"""Production startup script for Render/Railway"""
import os
import sys

# Add web-app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask_api import app, socketio

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    print(f"Starting Eye Strain Detection API on port {port}...")
    print(f"Production mode: {os.environ.get('FLASK_ENV', 'development')}")
    # Use eventlet for WebSocket support
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
