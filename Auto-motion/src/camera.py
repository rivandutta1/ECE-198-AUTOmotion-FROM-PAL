
import cv2
import time
from .pose_tracker import create_pose_tracker, process_frame

def make_circle(landmark, frame):
    x = int(landmark.x)
    y = int(landmark.y)
    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)


def make_line(landmark1, landmark2, frame):
    x1, y1 = int(landmark1.x), int(landmark1.y)
    x2, y2 = int(landmark2.x), int(landmark2.y)

    cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

def run_camera():
    camera = cv2.VideoCapture(0)
    landmarker = None

    try:
        if not camera.isOpened():
            raise RuntimeError("ERROR: Camera Cannot Open")

        landmarker = create_pose_tracker()

        while True:
            success, frame = camera.read()

            if not success:
                raise RuntimeError("ERROR: Camera Disconnected")
            
            frame = cv2.flip(frame, 1)
            timestamp_ms = int(time.monotonic() * 1000)

            pose = process_frame(frame, timestamp_ms, landmarker)


            if pose.valid:
                for side in ("left", "right"):
                    shoulder = pose.landmarks.get(f"{side}_shoulder")
                    elbow = pose.landmarks.get(f"{side}_elbow")
                    wrist = pose.landmarks.get(f"{side}_wrist")

                    if shoulder is not None and elbow is not None and wrist is not None:
                        make_circle(shoulder, frame)
                        make_circle(elbow, frame)
                        make_circle(wrist, frame)

                        make_line(shoulder, elbow, frame)
                        make_line(elbow, wrist, frame)

            cv2.imshow("AUTO-MOTION", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            if cv2.getWindowProperty("AUTO-MOTION", cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()

        if landmarker is not None:
            landmarker.close()