import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from .data_types import Landmark, PoseFrame
from pathlib import Path

def create_pose_tracker():
    model_path = Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_lite.task"

    options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(
            model_asset_path=str(model_path)
        ),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)
    print("MediaPipe Pose Landmarker loaded successfully!")
    return landmarker



def process_frame(frame, timestamp_ms, landmarker):
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )

    result = landmarker.detect_for_video(mp_image, timestamp_ms)

    landmark_data = {}
    tracking_valid = False

    if result.pose_landmarks:
        landmarks = result.pose_landmarks[0]
        height, width = frame.shape[:2]

        arm_indices = {
            "left": {
                "shoulder": 11,
                "elbow": 13,
                "wrist": 15
            },
            "right": {
                "shoulder": 12,
                "elbow": 14,
                "wrist": 16
            }
        }

        for side, joints in arm_indices.items():
            arm_valid = all(
                landmarks[index].visibility >= 0.6
                for index in joints.values()
            )

            if arm_valid:
                for joint, index in joints.items():
                    point = landmarks[index]

                    landmark_data[f"{side}_{joint}"] = Landmark(
                        x=float(point.x * width),
                        y=float(point.y * height),
                        visibility=float(point.visibility)
                    )

        tracking_valid = bool(landmark_data)

    return PoseFrame(
        timestamp_ms=timestamp_ms,
        valid=tracking_valid,
        landmarks=landmark_data
    )
