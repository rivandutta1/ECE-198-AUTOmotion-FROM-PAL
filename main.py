"""AUTO-MOTION Tuesday demo: live one-person shoulder-press lean warning.

Python performs ALL pose estimation, calibration and decisions.
Arduino UNO R4 Minima ONLY displays GOOD / BAD / CANNOT ASSESS.
"""
import argparse
from pathlib import Path
import sys
import time

import cv2

from src.form_rules import FormMonitor, UNKNOWN
from src.geometry import SIDE_INDEX, measure_pose
from src.serial_link import SerialLink
from src.vision import VisionTracker

ROOT = Path(__file__).resolve().parent


def draw_overlay(frame, landmarks, side, decision, baseline):
    h, w = frame.shape[:2]
    colors = {"GOOD": (0, 190, 0), "BAD": (0, 0, 230), "UNKNOWN": (135, 135, 135)}
    color = colors[decision.status]

    if landmarks:
        shoulder, elbow, wrist, hip = SIDE_INDEX[side]
        ids = (hip, shoulder, elbow, wrist)
        points = []
        for i in ids:
            lm = landmarks[i]
            p = (int(lm.x * w), int(lm.y * h))
            points.append(p)
            cv2.circle(frame, p, 6, (240, 195, 0), -1)
        for p0, p1 in zip(points, points[1:]):
            cv2.line(frame, p0, p1, (240, 195, 0), 3)

    cv2.rectangle(frame, (0, 0), (w, 132), (23, 26, 30), -1)
    display_status = "CANNOT ASSESS" if decision.status == UNKNOWN else decision.status
    cv2.putText(frame, f"AUTO-MOTION: {display_status}", (15, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.76, color, 2, cv2.LINE_AA)
    cv2.putText(frame, decision.detail[:55], (15, 72),
                cv2.FONT_HERSHEY_SIMPLEX, 0.53, (235, 235, 235), 1, cv2.LINE_AA)
    cv2.putText(frame, f"SIDE: {side.upper()} | BASELINE: {baseline:.1f} deg" if baseline is not None else f"SIDE: {side.upper()} | BASELINE: NOT SET",
                (15, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.46,
                (190, 195, 205), 1, cv2.LINE_AA)
    if decision.deviation_deg is not None:
        cv2.putText(frame, f"Torso change: {decision.deviation_deg:.1f} degrees",
                    (max(10, w - 260), 72), cv2.FONT_HERSHEY_SIMPLEX, 0.43,
                    (205, 210, 215), 1, cv2.LINE_AA)
    cv2.putText(frame, "C=CALIBRATE (upright, arm DOWN)   Q=QUIT", (15, 123),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (190, 195, 205), 1, cv2.LINE_AA)
    return frame


def main():
    parser = argparse.ArgumentParser(description="3-state shoulder-press camera demo")
    parser.add_argument("--side", choices=("left", "right"), default="left",
                        help="which arm/torso side is visible to the camera")
    parser.add_argument("--camera", type=int, default=0, help="OpenCV camera index")
    parser.add_argument("--port", default=None,
                        help="Arduino serial port (COM3 on Windows, /dev/cu... on macOS); omit for camera-only")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        sys.exit("ERROR: Camera unavailable. Close Teams/Zoom, check privacy permissions, try --camera 1")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    tracker = None
    link = None
    try:
        tracker = VisionTracker(ROOT / "models" / "pose_landmarker_lite.task")
        link = SerialLink(args.port)
        monitor = FormMonitor()
        start = time.monotonic()
        last_ts = -1
        last_send = 0.0
        print("READY. Face sideways to camera; include head, shoulder, hip and raised wrist.")
        print("Press C while standing upright, arm DOWN; stay still for 2 seconds.")
        print("Then raise arm for shoulder press; deliberately lean to test RED. Q exits.")
        while True:
            ok, frame = cap.read()
            if not ok:
                print("ERROR: Webcam stopped providing frames")
                break
            timestamp_ms = max(int((time.monotonic() - start) * 1000), last_ts + 1)
            last_ts = timestamp_ms
            landmarks = tracker.process(frame, timestamp_ms)
            h, w = frame.shape[:2]
            sample = measure_pose(landmarks, w, h, side=args.side)
            decision = monitor.evaluate(sample, timestamp_ms)
            draw_overlay(frame, landmarks, args.side, decision, monitor.baseline_deg)
            cv2.imshow("AUTO-MOTION Shoulder Press", frame)

            # Refresh status even when unchanged; firmware times out after 1.2 s.
            now = time.monotonic()
            if now - last_send >= 0.2:
                try:
                    link.send(decision.status)
                except Exception as exc:
                    print(f"Arduino serial error: {exc}. Running camera-only.")
                    link.close()
                    link = SerialLink(None)
                last_send = now
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("c"):
                monitor.start_calibration()
                print("CALIBRATING: Stand upright, arm DOWN, hold still for 2 seconds.")
    finally:
        if link is not None:
            link.close()
        if tracker is not None:
            tracker.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
