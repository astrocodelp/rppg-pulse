"""MediaPipe FaceLandmarker ROI extraction (CPU, no network at inference).

Model file: models/face_landmarker.task — the official MediaPipe FaceLandmarker
float16 bundle (v1), vendored in the repo; sha256 in models/README.md.
Inference is fully local. Landmark indices are the canonical FaceMesh topology.

ROI definition (frozen in params_frozen.json):
  forehead polygon: landmarks 10, 338, 297, 332, 284 (top edge, raised 12% of
    face height) and 251, 389, 356, 70, 63, 105, 66, 107 (brow line);
  left cheek polygon: 117, 118, 101, 36, 205, 206, 207, 213, 192, 147;
  right cheek polygon: 346, 347, 348, 266, 425, 426, 427, 436, 416, 376.
Pixels inside any polygon (filled mask) contribute to the spatial RGB mean.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "face_landmarker.task"

FOREHEAD_TOP = [10, 338, 297, 332, 284]
BROW = [251, 389, 356, 70, 63, 105, 66, 107]
LEFT_CHEEK = [117, 118, 101, 36, 205, 206, 207, 213, 192, 147]
RIGHT_CHEEK = [346, 347, 348, 266, 425, 426, 427, 436, 416, 376]
FOREHEAD_RAISE = 0.12  # fraction of face height the forehead polygon is raised


@dataclass
class FaceResult:
    detected: bool
    rgb_mean: np.ndarray | None   # (3,) float64 spatial mean inside ROI
    center: np.ndarray | None     # (2,) face center in pixels (motion tracking)
    face_h: float                 # face height in pixels
    n_roi_px: int
    luma: float                   # mean luma inside ROI, 0-255


class FaceROI:
    """Stateless per-frame detection (VIDEO mode uses tracking; IMAGE mode here
    is deliberate: per-frame independence keeps evaluation deterministic)."""

    def __init__(self, model_path: str | Path = MODEL_PATH):
        os.environ.setdefault("GLOG_minloglevel", "2")
        opts = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path),
                                     delegate=BaseOptions.Delegate.CPU),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.5,
        )
        self._lm = vision.FaceLandmarker.create_from_options(opts)

    def close(self):
        self._lm.close()

    def process(self, rgb: np.ndarray) -> FaceResult:
        h, w = rgb.shape[:2]
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        res = self._lm.detect(img)
        if not res.face_landmarks:
            return FaceResult(False, None, None, 0.0, 0, float("nan"))
        pts = np.array([[p.x * w, p.y * h] for p in res.face_landmarks[0]])
        ymin, ymax = pts[:, 1].min(), pts[:, 1].max()
        face_h = ymax - ymin
        top = pts[FOREHEAD_TOP].copy()
        top[:, 1] -= FOREHEAD_RAISE * face_h
        poly_fore = np.vstack([top, pts[BROW][::-1]])
        mask = np.zeros((h, w), dtype=np.uint8)
        for poly in (poly_fore, pts[LEFT_CHEEK], pts[RIGHT_CHEEK]):
            cv2.fillPoly(mask, [np.round(poly).astype(np.int32)], 255)
        sel = mask > 0
        n = int(sel.sum())
        if n < 30:
            return FaceResult(False, None, None, face_h, n, float("nan"))
        px = rgb[sel]
        mean = px.mean(axis=0).astype(np.float64)
        luma = float(mean @ np.array([0.299, 0.587, 0.114]))
        center = pts.mean(axis=0)
        return FaceResult(True, mean, center, face_h, n, luma)


def face_bbox_from_frames(frames: np.ndarray, roi: FaceROI, n_probe: int = 9,
                          margin: float = 0.35) -> tuple[int, int, int, int] | None:
    """Union face bbox over n_probe evenly spaced frames, with margin.

    Used only to speed up evaluation decoding (crop before landmarking);
    landmarks are then re-found inside the crop, so ROI pixels are identical.
    Returns (x, y, w, h) in source pixels or None if no face found.
    """
    n = len(frames)
    if n == 0:
        return None
    idxs = np.unique(np.linspace(0, n - 1, min(n_probe, n)).astype(int))
    h, w = frames.shape[1:3]
    x0, y0, x1, y1 = w, h, 0, 0
    found = False
    for i in idxs:
        img = mp.Image(image_format=mp.ImageFormat.SRGB,
                       data=np.ascontiguousarray(frames[i]))
        res = roi._lm.detect(img)
        if not res.face_landmarks:
            continue
        pts = np.array([[p.x * w, p.y * h] for p in res.face_landmarks[0]])
        found = True
        x0 = min(x0, pts[:, 0].min()); x1 = max(x1, pts[:, 0].max())
        y0 = min(y0, pts[:, 1].min()); y1 = max(y1, pts[:, 1].max())
    if not found:
        return None
    fw, fh = x1 - x0, y1 - y0
    x0 = int(max(0, x0 - margin * fw)); y0 = int(max(0, y0 - (margin + FOREHEAD_RAISE) * fh))
    x1 = int(min(w, x1 + margin * fw)); y1 = int(min(h, y1 + margin * fh))
    return (x0, y0, x1 - x0, y1 - y0)
