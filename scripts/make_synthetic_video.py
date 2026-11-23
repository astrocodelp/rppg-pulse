"""Synthetic face video generator for demo testing and the demo video.

NOT used in any evaluation: purely a consenting-volunteer-free, fully
synthetic test signal (a cartoon face whose skin colour is modulated by a
known sinusoidal 'pulse'). Ground truth = the injected BPM exactly.

  python3 scripts/make_synthetic_video.py out.mp4 --bpm 72 --seconds 32

The face is a drawn ellipse with cheeks/forehead regions; MediaPipe detects
it (verified in tests). Skin modulation amplitude ~1% of channel value,
comparable to real rPPG amplitudes, plus mild sensor noise.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import numpy as np


def draw_face(h: int, w: int, pulse_phase: float, rng: np.random.Generator,
              amp: float = 0.012) -> np.ndarray:
    """RGB uint8 frame: neutral background + cartoon face with pulsing skin."""
    img = np.zeros((h, w, 3), dtype=np.float64)
    img[:, :] = (60, 66, 78)  # dim neutral background
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2, h / 2
    rx, ry = w * 0.22, h * 0.33
    face = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0
    base = np.array([196.0, 154.0, 132.0])  # mid skin tone
    # pulse: blood volume modulates green/blue more than red
    mod = amp * np.sin(pulse_phase) * np.array([0.35, 1.0, 0.6])
    img[face] = base * (1.0 + mod)
    # shading so MediaPipe sees structure: darker at edges
    edge = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    shade = np.clip(1.15 - 0.35 * edge, 0.6, 1.1)
    img[face] *= shade[face, None]
    # eyes (dark almond ellipses)
    for ex in (-0.09, 0.09):
        eye = ((xx - (cx + ex * w)) / (w * 0.045)) ** 2 + \
              ((yy - (cy - h * 0.07)) / (h * 0.028)) ** 2 <= 1.0
        img[eye] = (245, 245, 245)
        pupil = ((xx - (cx + ex * w)) / (w * 0.02)) ** 2 + \
                ((yy - (cy - h * 0.07)) / (h * 0.02)) ** 2 <= 1.0
        img[pupil] = (50, 38, 30)
    # brows
    for ex in (-0.09, 0.09):
        brow = (np.abs(xx - (cx + ex * w)) < w * 0.055) & \
               (np.abs(yy - (cy - h * 0.13)) < h * 0.012)
        img[brow] = (70, 50, 40)
    # nose shadow
    nose = (np.abs(xx - cx) < w * 0.012) & (yy > cy - h * 0.02) & (yy < cy + h * 0.09)
    img[nose] *= 0.82
    # mouth
    mouth = ((xx - cx) / (w * 0.07)) ** 2 + \
            ((yy - (cy + h * 0.17)) / (h * 0.022)) ** 2 <= 1.0
    img[mouth] = (150, 84, 80)
    img += rng.normal(0, 1.1, img.shape)  # sensor noise
    return np.clip(img, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--bpm", type=float, default=72.0)
    ap.add_argument("--seconds", type=float, default=32.0)
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--size", type=int, nargs=2, default=[480, 640])  # h w
    args = ap.parse_args()
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    h, w = args.size
    rng = np.random.default_rng(7)
    n = int(args.seconds * args.fps)
    cmd = [exe, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{w}x{h}", "-r", str(args.fps), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", args.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        phase = 2 * np.pi * (args.bpm / 60.0) * (i / args.fps)
        fr = draw_face(h, w, phase, rng)
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    p.wait()
    print(f"wrote {args.out}: {n} frames, injected pulse {args.bpm} BPM")


if __name__ == "__main__":
    main()
