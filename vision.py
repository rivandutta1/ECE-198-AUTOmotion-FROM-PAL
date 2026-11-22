"""MediaPipe Pose Landmarker (Tasks VIDEO API) wrapper.

Only this module imports mediapipe: geometry/rules/serial can be tested offline.
"""
from pathlib import Path

import cv2
import mediapipe as mp

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode


class VisionTracker:
    def __init__(self, model_path: Path):
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Missing model: {model_path}. See the repository README for setup"
            )
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.detector = PoseLandmarker.create_from_options(options)

    def process(self, frame, timestamp_ms: int):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.detector.detect_for_video(image, timestamp_ms)
        return result.pose_landmarks[0] if result.pose_landmarks else None

    def close(self):
        self.detector.close()
