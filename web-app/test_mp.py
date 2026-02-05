import cv2
import numpy as np

try:
    import mediapipe as mp
    print("MediaPipe imported successfully")
    print(f"Version: {mp.__version__}")
except ImportError as e:
    print(f"MediaPipe ImportError: {e}")
except Exception as e:
    print(f"MediaPipe Generic Error: {e}")

try:
    from mediapipe.tasks.python.vision import face_landmarker
    print("FaceLandmarker imported successfully")
except Exception as e:
    print(f"FaceLandmarker Error: {e}")
