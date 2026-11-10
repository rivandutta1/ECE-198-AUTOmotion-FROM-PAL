"""Download Google's free MediaPipe Pose Landmarker Lite model once."""
from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "pose_landmarker_lite.task"
URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"

MODEL.parent.mkdir(parents=True, exist_ok=True)
if MODEL.is_file() and MODEL.stat().st_size > 100_000:
    print(f"Model already available: {MODEL}")
else:
    print(f"Downloading from: {URL}")
    urlretrieve(URL, MODEL)
    if MODEL.stat().st_size < 100_000:
        MODEL.unlink(missing_ok=True)
        raise RuntimeError("Download too small; use the official model download page")
    print(f"Saved {MODEL} ({MODEL.stat().st_size:,} bytes)")
