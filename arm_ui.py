"""AutoMotion: a minimal dark, mouse-first interface for two arm exercises.

Metro Nova is used only if already licensed and installed locally. The app
never ships or downloads any font files. Pillow renders UI typography because
cv2.putText cannot render real font families. Camera stays mirrored only for
preview; anatomical LEFT/RIGHT and measurements use unmirrored landmarks.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from arm_exercises import JOINTS, Feedback, _quality
from app_modes import EXERCISE_NAMES

WIDTH, HEIGHT = 1600, 900
WINDOW_TITLE = "AutoMotion"

# Colors below are RGB, not OpenCV BGR.
BG = (16, 19, 25)
SURFACE = (29, 34, 42)
SURFACE_RAISED = (37, 43, 52)
BORDER = (53, 60, 70)
TEXT = (241, 244, 247)
MUTED = (163, 174, 186)
SOFT = (118, 132, 145)
MINT = (178, 231, 210)
LAVENDER = (209, 199, 248)
ROSE = (245, 177, 185)
AMBER = (252, 214, 158)
PANEL_DARK = (19, 23, 29)
WHITE = (255, 255, 255)

VIDEO_RECT = (28, 194, 1096, 780)
STATUS_RECT = (1114, 194, 1572, 780)
DETAILS_RECT = (1138, 578, 1548, 690)  # measurement grid inside STATUS_RECT


@dataclass(frozen=True)
class Button:
    action: str
    text: str
    rect: tuple[int, int, int, int]

    def contains(self, x: int, y: int) -> bool:
        x1, y1, x2, y2 = self.rect
        return x1 <= x < x2 and y1 <= y < y2


@lru_cache(maxsize=1)
def controls():
    """Mouse targets are intentionally large for accessible, no-terminal use."""
    return (
        Button("mode:curl", "Bicep curl", (28, 106, 335, 170)),
        Button("mode:pushdown", "Tricep pushdown", (347, 106, 672, 170)),
        Button("side:right", "Right arm", (1108, 106, 1328, 170)),
        Button("side:left", "Left arm", (1340, 106, 1572, 170)),
        Button("calibrate", "Calibrate", (1141, 706, 1545, 766)),
        Button("reset", "Reset reps", (28, 808, 225, 873)),
        Button("mirror", "Mirror on", (238, 808, 431, 873)),
        Button("camera", "Camera", (444, 808, 639, 873)),
        Button("arduino", "Connect Arduino", (652, 808, 878, 873)),
        Button("quit", "Exit", (891, 808, 1096, 873)),
    )


def hit_test(x: int, y: int):
    return next((button.action for button in controls() if button.contains(x, y)), None)


def point_in_preview(lm, viewport, mirror: bool):
    ox, oy, width, height = viewport
    return (int(round(ox + ((1.0 - lm.x) if mirror else lm.x) * width)),
            int(round(oy + lm.y * height)))


def _is_plain(path):
    """Skip bold/italic/narrow variants so the UI uses a regular weight."""
    stem = path.stem.lower()
    return not any(word in stem for word in
                   ("bold", "italic", "oblique", "condensed", "light", "mono"))


def _font_candidates():
    # Metro Nova is a commercial font. Use an existing system installation only.
    roots = [Path.home() / "Library/Fonts", Path("/Library/Fonts"),  # macOS
             Path("/System/Library/Fonts"),
             Path("/usr/share/fonts/truetype/dejavu"),  # Debian / Ubuntu
             Path("/usr/share/fonts/dejavu-sans-fonts"),  # Fedora
             Path("/usr/share/fonts/google-noto")]  # Fedora
    metro = []
    fallbacks = []
    for root in roots:
        if not root.exists():
            continue
        try:
            fonts = [p for p in root.iterdir() if p.is_file() and
                     p.suffix.lower() in (".otf", ".ttf", ".ttc")]
        except (PermissionError, OSError):
            continue
        metro.extend(p for p in fonts if "metro" in p.stem.lower() and "nova" in p.stem.lower())
        fallbacks.extend(p for p in fonts if _is_plain(p) and any(
            name in p.stem.lower() for name in
            ("avenir next", "avenirnext", "helveticaneue", "helvetica neue", "dejavusans",
             "notosans-regular")))
    return sorted(metro, key=lambda p: "regular" not in p.stem.lower()) + fallbacks


@lru_cache(maxsize=1)
def installed_font_path():
    override = os.environ.get("AUTOMOTION_FONT_PATH")
    if override and Path(override).is_file():
        return str(Path(override))
    for path in _font_candidates():
        try:
            ImageFont.truetype(str(path), size=16)
            return str(path)
        except (OSError, ValueError):
            continue
    # Typical Pillow bundled fallback, no extra third-party font assets shipped.
    return "DejaVuSans.ttf"


@lru_cache(maxsize=36)
def _font(px: int):
    try:
        return ImageFont.truetype(installed_font_path(), max(10, px))
    except (OSError, ValueError):
        return ImageFont.load_default(size=max(10, px))


def _size_to_px(size):
    return int(round(size * 35))


def _text(canvas, value, x, y, size=.68, color=TEXT):
    """Draw text with a real font. y is the baseline, matching old UI tests."""
    font = _font(_size_to_px(size))
    ImageDraw.Draw(canvas).text((int(x), int(y)), str(value), font=font,
                                fill=tuple(color), anchor="ls",
                                stroke_width=0)


def _fit_size(value, max_width, target=.72, minimum=.40):
    size = target
    while size > minimum:
        if _font(_size_to_px(size)).getlength(str(value)) <= max_width:
            return size
        size -= .03
    return minimum


def _center_text(canvas, value, rect, size=.67, color=TEXT):
    x1, y1, x2, y2 = rect
    fsize = _fit_size(value, x2 - x1 - 20, size)
    f = _font(_size_to_px(fsize))
    tw = f.getlength(str(value))
    baseline = (y1 + y2) // 2 + _size_to_px(fsize) * .34
    _text(canvas, value, x1 + (x2-x1-tw)//2, baseline, fsize, color)


def _round(canvas, rect, fill, radius=19, outline=None, width=1):
    ImageDraw.Draw(canvas).rounded_rectangle(rect, radius=radius, fill=fill,
                                             outline=outline, width=width)


def wrapping(text, max_chars=40, limit=3):
    lines, current = [], ""
    for word in str(text).split():
        if current and len(current)+len(word)+1 > max_chars:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        lines.append(current)
    return lines[:limit]


def status_text(feedback: Feedback):
    if feedback.status == "GOOD":
        return "Good form"
    if feedback.status == "BAD":
        return "Check form"
    if feedback.issue == "TRACK":
        return "Move into view"
    if not feedback.calibrated:
        return "Calibrating"
    if feedback.issue in ("START", "IDLE"):
        return "Ready to start"
    return "Waiting"


def _degrees(value):
    return "-" if value is None else f"{value:.0f}\u00b0"


def _percent(value):
    return "-" if value is None else f"{value * 100:.0f}%"


def detail_rows(feedback: Feedback):
    """(label, value, color) for every measurement in the details grid.

    Listed column by column: the left column first, then the right one.
    """
    flagged_color = ROSE if feedback.bad_reps else TEXT
    return (
        ("Completed reps", str(feedback.reps), MINT),
        ("Flagged reps", str(feedback.bad_reps), flagged_color),
        ("Stage", feedback.stage.capitalize(), TEXT),
        ("Confidence", _percent(feedback.confidence), TEXT),
        ("Elbow angle", _degrees(feedback.elbow_deg), TEXT),
        ("Torso shift", _degrees(feedback.torso_change_deg), TEXT),
        ("Upper-arm shift", _degrees(feedback.upper_arm_change_deg), TEXT),
    )


def _draw_details(canvas, feedback, rect):
    """Two-column label/value grid, four rows per column."""
    x1, y1, x2, y2 = rect
    _round(canvas, rect, SURFACE_RAISED, 15)
    column_width = (x2 - x1) // 2
    for index, (label, value, color) in enumerate(detail_rows(feedback)):
        column, row = divmod(index, 4)
        left = x1 + 16 + column * column_width
        right = x1 + (column + 1) * column_width - 16
        baseline = y1 + 28 + row * 25
        _text(canvas, label, left, baseline, .50, MUTED)
        width = _font(_size_to_px(.56)).getlength(value)
        _text(canvas, value, right - width, baseline, .56, color)


def _draw_progress(canvas, progress, x1, y, x2):
    """'Rep progress' label with a horizontal bar underneath."""
    progress = max(0.0, min(1.0, progress or 0.0))
    _text(canvas, "REP PROGRESS", x1, y, .50, SOFT)
    label = f"{progress * 100:.0f}%"
    _text(canvas, label, x2 - _font(_size_to_px(.50)).getlength(label), y, .50, MUTED)
    bar = (x1, y + 10, x2, y + 24)
    _round(canvas, bar, SURFACE_RAISED, 7)
    if progress > 0:
        _round(canvas, (x1, bar[1], x1 + max(14, round((x2 - x1) * progress)), bar[3]),
               MINT, 7)


def _status_colors(feedback):
    return {
        "GOOD": (MINT, (34, 58, 51)),
        "BAD": (ROSE, (65, 43, 51)),
        "UNKNOWN": (AMBER, (67, 54, 37)),
    }.get(feedback.status, (AMBER, (67, 54, 37)))


def _draw_button(canvas, button, selected=False, mirrored=True, connected=False):
    active = MINT if selected else SURFACE_RAISED
    fg = BG if selected else TEXT
    if button.action == "calibrate":
        active, fg = MINT, (20, 38, 32)
    if button.action == "arduino" and connected:
        active, fg = (61, 90, 79), MINT
    _round(canvas, button.rect, active, radius=17, outline=BORDER if not selected else None)
    text = button.text
    if button.action == "mirror":
        text = "Mirror on" if mirrored else "Mirror off"
    elif button.action == "arduino" and connected:
        text = "Arduino connected"
    _center_text(canvas, text, button.rect, .63, fg)


_LAST_PREVIEW = None  # one cached frame: 60 Hz UI need not rescale 30 FPS video twice


def _preview_image(frame, mirrored, width, height):
    global _LAST_PREVIEW
    if (_LAST_PREVIEW is not None and _LAST_PREVIEW[0] is frame and
            _LAST_PREVIEW[1] == mirrored and _LAST_PREVIEW[2] == (width, height)):
        return _LAST_PREVIEW[3]
    h, w = frame.shape[:2]
    preview = cv2.flip(frame, 1) if mirrored else frame
    scaled = cv2.resize(preview, (width, height),
                        interpolation=cv2.INTER_AREA if (w > width or h > height)
                        else cv2.INTER_LINEAR)
    result = Image.fromarray(cv2.cvtColor(scaled, cv2.COLOR_BGR2RGB))
    # Retain a strong reference to the original frame to avoid recycled object IDs.
    _LAST_PREVIEW = (frame, mirrored, (width, height), result)
    return result


def _draw_pose(canvas, landmarks, side, viewport, mirrored):
    if landmarks is None or len(landmarks) < 33:
        return
    joints = JOINTS[side]
    points = {}
    for label, index in joints.items():
        landmark = landmarks[index]
        visible, present = _quality(landmark)
        if (.005 <= landmark.x <= .995 and .005 <= landmark.y <= .995 and
                visible >= .40 and present >= .35):
            points[label] = point_in_preview(landmark, viewport, mirrored)
    draw = ImageDraw.Draw(canvas)
    for first, second in (("hip", "shoulder"), ("shoulder", "elbow"), ("elbow", "wrist")):
        if first in points and second in points:
            draw.line((points[first], points[second]), fill=(22, 35, 39), width=10)
            draw.line((points[first], points[second]), fill=MINT, width=5)
    for p in points.values():
        x, y = p
        draw.ellipse((x-9, y-9, x+9, y+9), fill=MINT, outline=(21, 39, 40), width=3)


def draw_screen(frame, landmarks, side: str, exercise: str, feedback: Feedback,
                arduino_connected: bool, mirrored: bool = True):
    """BGR NumPy in/out, for OpenCV's macOS HighGUI main thread."""
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(canvas)

    _round(canvas, (25, 26, 66, 67), MINT, radius=13)
    draw.ellipse((40, 34, 59, 53), fill=LAVENDER)
    _text(canvas, "AutoMotion", 85, 63, 1.16, TEXT)

    # Tiny device-status chip; technical data stays out of the main UI.
    _round(canvas, (1365, 28, 1572, 75), SURFACE, 18, outline=BORDER)
    dot = MINT if arduino_connected else SOFT
    draw.ellipse((1383, 47, 1398, 62), fill=dot)
    _text(canvas, "Arduino linked" if arduino_connected else "Camera only",
          1409, 60, .56, MUTED)

    _text(canvas, "EXERCISE", 28, 99, .47, SOFT)
    _text(canvas, "TRACKED ARM", 1114, 99, .47, SOFT)
    for b in controls():
        if b.action == "calibrate":
            continue
        _draw_button(canvas, b, selected=(b.action == f"mode:{exercise}" or
                         b.action == f"side:{side}"), mirrored=mirrored,
                         connected=arduino_connected)

    # Live video and pose overlay. Original anatomical side is unaffected by mirroring.
    _round(canvas, VIDEO_RECT, SURFACE, 23, outline=BORDER)
    vx1, vy1, vx2, vy2 = VIDEO_RECT
    ix1, iy1, ix2, iy2 = vx1 + 13, vy1 + 13, vx2 - 13, vy2 - 13
    _round(canvas, (ix1, iy1, ix2, iy2), PANEL_DARK, 16)
    h, w = frame.shape[:2]
    max_w, max_h = ix2-ix1, iy2-iy1
    zoom = min(max_w/max(1,w), max_h/max(1,h))
    pw, ph = max(1, round(w*zoom)), max(1, round(h*zoom))
    ox, oy = ix1+(max_w-pw)//2, iy1+(max_h-ph)//2
    canvas.paste(_preview_image(frame, mirrored, pw, ph), (ox, oy))
    _draw_pose(canvas, landmarks, side, (ox, oy, pw, ph), mirrored)
    _round(canvas, (vx1+28, vy1+24, vx1+195, vy1+65), PANEL_DARK, 14)
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((vx1+44, vy1+39, vx1+56, vy1+51), fill=MINT)
    _text(canvas, "LIVE CAMERA", vx1+71, vy1+52, .51, TEXT)
    # A quiet label instead of debug metrics/FPS counters.
    _round(canvas, (vx1+28, vy2-65, vx2-28, vy2-27), PANEL_DARK, 13)
    _text(canvas, f"Keep your {side} shoulder, elbow, wrist and hip in view",
          vx1+43, vy2-40, .54, MUTED)

    # Status panel: form status, next step, rep progress, details, Calibrate.
    _round(canvas, STATUS_RECT, SURFACE, 23, outline=BORDER)
    sx1, sy1, sx2, sy2 = STATUS_RECT
    _text(canvas, EXERCISE_NAMES[exercise], sx1+27, sy1+49,
          _fit_size(EXERCISE_NAMES[exercise], sx2-sx1-58, .89), TEXT)
    _text(canvas, "Your form", sx1+27, sy1+90, .56, MUTED)

    tint, fg = _status_colors(feedback)
    _round(canvas, (sx1+24, sy1+104, sx2-24, sy1+204), tint, 22)
    _text(canvas, status_text(feedback), sx1+44, sy1+156,
          _fit_size(status_text(feedback), sx2-sx1-88, 1.08), fg)
    _text(canvas, feedback.status, sx1+44, sy1+187, .52, fg)

    _text(canvas, "NEXT STEP", sx1+27, sy1+238, .50, SOFT)
    instructions = feedback.message or "Choose an exercise and calibrate."
    for line_index, line in enumerate(wrapping(instructions, 38, 3)):
        _text(canvas, line, sx1+27, sy1+268+line_index*26,
              _fit_size(line, sx2-sx1-54, .64), TEXT)

    _draw_progress(canvas, feedback.progress, sx1+27, sy1+346, sx2-27)
    _draw_details(canvas, feedback, DETAILS_RECT)
    _draw_button(canvas, next(b for b in controls() if b.action=="calibrate"))

    _text(canvas, "Camera guidance only - Not a medical or safety assessment",
          30, 893, .47, SOFT)
    # OpenCV expects BGR uint8.
    return cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR)
