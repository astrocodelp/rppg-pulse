"""Video decoding that never depends on OpenCV's demuxers.

UBFC REALISTIC vids are uncompressed BGR24 AVI; some OpenCV builds crash on
them, so we decode with the ffmpeg binary bundled by imageio-ffmpeg (pinned),
which handles AVI/webm/mp4 alike. Frames are streamed as raw RGB24, optionally
spatially cropped by ffmpeg itself (fast path used by the evaluation: crop to
the face bounding box so only ~1 MB/window crosses the pipe).
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float          # nominal rate reported by the container
    n_frames: int       # container frame count (may be 0 if unknown)
    duration_s: float   # container duration


def probe(path: str | Path) -> VideoInfo:
    """Read width/height/fps/duration with ffprobe-style parsing of ffmpeg -i."""
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    p = subprocess.run([exe, "-hide_banner", "-i", str(path)],
                       capture_output=True, text=True)
    txt = p.stderr
    import re
    m = re.search(r"Video:.*?, (\d+)x(\d+)", txt)
    if not m:
        raise ValueError(f"no video stream found in {path}")
    w, h = int(m.group(1)), int(m.group(2))
    mfps = re.search(r"([\d.]+) fps", txt)
    fps = float(mfps.group(1)) if mfps else 0.0
    mdur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", txt)
    dur = (int(mdur.group(1)) * 3600 + int(mdur.group(2)) * 60 + float(mdur.group(3))) if mdur else 0.0
    return VideoInfo(w, h, fps, int(round(dur * fps)) if fps else 0, dur)


def read_frames(path: str | Path, crop: tuple[int, int, int, int] | None = None,
                start_s: float = 0.0, end_s: float | None = None,
                max_frames: int | None = None):
    """Yield (frame_index, rgb_uint8 HxWx3). crop = (x, y, w, h) in source pixels.

    Frame index counts decoded frames from start_s (ffmpeg -ss before -i is
    keyframe-accurate for AVI rawvideo: every frame is a keyframe).
    """
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    info = probe(path)
    cmd = [exe, "-hide_banner", "-loglevel", "error"]
    if start_s > 0:
        cmd += ["-ss", f"{start_s:.6f}"]
    cmd += ["-i", str(path)]
    if end_s is not None:
        cmd += ["-t", f"{end_s - start_s:.6f}"]
    vf = []
    if crop:
        x, y, w, h = crop
        x = max(0, x - x % 2); y = max(0, y - y % 2)
        w = min(w, info.width - x); h = min(h, info.height - y)
        vf.append(f"crop={w}:{h}:{x}:{y}")
    out_w, out_h = (w, h) if crop else (info.width, info.height)
    if vf:
        cmd += ["-vf", ",".join(vf)]
    if max_frames:
        cmd += ["-frames:v", str(max_frames)]
    cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         bufsize=out_w * out_h * 3)
    nbytes = out_w * out_h * 3
    i = 0
    try:
        while True:
            buf = p.stdout.read(nbytes)
            if len(buf) < nbytes:
                break
            yield i, np.frombuffer(buf, dtype=np.uint8).reshape(out_h, out_w, 3)
            i += 1
    finally:
        p.stdout.close()
        p.wait()


def read_all(path: str | Path, crop=None, start_s=0.0, end_s=None, max_frames=None):
    frames = [f for _, f in read_frames(path, crop, start_s, end_s, max_frames)]
    if not frames:
        return np.zeros((0, 1, 1, 3), dtype=np.uint8)
    return np.stack(frames)
