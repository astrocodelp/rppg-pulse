"""rppg-pulse demo — Gradio app (CPU only, no data leaves this machine).

Wellness demo, NOT a medical device. Two modes:
  * Live webcam: rolling 15 s pulse estimate from the webcam stream.
  * Upload a short video (<= 60 s): per-window HR estimates, same pipeline
    as the frozen evaluation (MediaPipe ROI -> POS -> 0.7-3.0 Hz -> peak).

Run:  python3 app/demo.py         (serves on 0.0.0.0:7860)
"""
from __future__ import annotations

import sys
import time
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import gradio as gr

from rppg.roi import FaceROI
from rppg.signal import pos_signal
from rppg.hr import estimate_window, bandpass, spectral_hr
from rppg.windows import interpolate_rgb
from rppg import video as vidio

ROI = FaceROI()
WINDOW_S = 15.0
MIN_FPS_LIVE = 8.0        # browser webcam streams are ~10-15 fps
import json
QUALITY_THRESHOLD = float(json.loads(
    (ROOT / "params_frozen.json").read_text())["quality_threshold"])  # frozen gate
MAX_UPLOAD_S = 60.0

DISCLAIMER = (
    "**Wellness demo — not a medical device.** This app estimates pulse from "
    "colour changes in a face video. It is a research prototype: it can be "
    "wrong by tens of BPM, and it abstains when the signal is poor. Never use "
    "it to diagnose, monitor or treat any condition. No video is stored or "
    "sent anywhere: processing happens in this Python process, in memory."
)

CSS = """
.disclaimer {border: 2px solid #8a6d00; background: #fff8e1; color: #4a3b00;
  padding: 0.75rem 1rem; border-radius: 8px; font-size: 1rem;}
.dark .disclaimer {background: #3a3000; color: #ffe9a8; border-color: #ffe9a8;}
.hr-big {font-size: 2.2rem; font-weight: 700; font-variant-numeric: tabular-nums;}
footer {visibility: hidden;}
a:focus-visible, button:focus-visible, input:focus-visible,
textarea:focus-visible, [tabindex]:focus-visible {
  outline: 3px solid #0057b8 !important; outline-offset: 2px;}
"""


def live_frame(frame, buf):
    """Stream handler: frame is RGB numpy or None; buf is a deque state."""
    if buf is None:
        buf = deque(maxlen=1200)
    if frame is None:
        return buf, _live_status(buf, None)
    now = time.monotonic()
    r = ROI.process(frame)
    buf.append((now, r.rgb_mean if r.detected else None))
    return buf, _live_status(buf, None)


def _live_status(buf, _):
    if not buf:
        return "<p class='hr-big'>—</p><p>Waiting for camera frames…</p>"
    now = buf[-1][0]
    recent = [(t, m) for t, m in buf if now - t <= WINDOW_S]
    span = now - recent[0][0]
    det = [m for _, m in recent if m is not None]
    face_frac = len(det) / len(recent)
    if span < WINDOW_S - 0.5:
        return (f"<p class='hr-big'>…</p><p>Collecting: {span:.0f} s of "
                f"{WINDOW_S:.0f} s. Keep your face still and well lit.</p>")
    fps = len(recent) / span
    if face_frac < 0.8:
        return ("<p class='hr-big'>No estimate</p><p>Face not visible enough "
                f"({face_frac*100:.0f}% of frames). Centre your face.</p>")
    if fps < MIN_FPS_LIVE:
        return ("<p class='hr-big'>No estimate</p>"
                f"<p>Camera too slow ({fps:.1f} fps).</p>")
    # resample irregular stream onto a uniform grid at measured fps
    ts = np.array([t for t, _ in recent])
    grid = np.linspace(ts[0], ts[-1], int(round(span * fps)) + 1)
    rgb = np.array([m if m is not None else [np.nan] * 3 for _, m in recent])
    try:
        rgb_i = interpolate_rgb(rgb)
        cols = np.column_stack([np.interp(grid, ts, rgb_i[:, c]) for c in range(3)])
        sig = pos_signal(cols)
        est = estimate_window(sig, fps, face_frac, QUALITY_THRESHOLD)
    except ValueError:
        est = None
    if est is None or est.hr_bpm is None:
        return ("<p class='hr-big'>No estimate</p><p>Signal too noisy — try "
                "steadier light and less movement.</p>")
    return (f"<p class='hr-big'>{est.hr_bpm:.0f} BPM</p>"
            f"<p>Rolling {WINDOW_S:.0f} s estimate · signal quality "
            f"{est.quality:.2f} · {fps:.0f} fps.<br>"
            "Wellness demo only — not a medical measurement.</p>")


def analyse_video(path):
    if path is None:
        raise gr.Error("Upload a video first (or record one with the webcam tab).")
    info = vidio.probe(path)
    if info.duration_s > MAX_UPLOAD_S + 1:
        raise gr.Error(f"Video is {info.duration_s:.0f} s; please keep uploads "
                       f"under {MAX_UPLOAD_S:.0f} s so CPU analysis stays quick.")
    fps = info.fps if info.fps >= 15 else 30.0
    rows = []
    rgb_all, det_all = [], []
    for _, fr in vidio.read_frames(path):
        r = ROI.process(fr)
        rgb_all.append(r.rgb_mean if r.detected else [np.nan] * 3)
        det_all.append(r.detected)
    rgb_all = np.array(rgb_all, dtype=float)
    det_all = np.array(det_all)
    T = len(rgb_all)
    if T < fps * 5:
        raise gr.Error("Video too short: need at least 5 seconds with a visible face.")
    n_win = int((T / fps) // WINDOW_S)
    if n_win == 0:
        # one short-window estimate, labelled as shorter than protocol
        n_win = 1
    table = []
    hrs = []
    for k in range(n_win):
        i0 = int(k * WINDOW_S * fps)
        i1 = min(int((k + 1) * WINDOW_S * fps), T)
        seg = rgb_all[i0:i1]
        frac = float(det_all[i0:i1].mean())
        eff = (i1 - i0) / ((i1 - i0) / fps)
        try:
            sig = pos_signal(interpolate_rgb(seg))
            est = estimate_window(sig, fps, frac, QUALITY_THRESHOLD)
        except ValueError:
            est = None
        if est is not None and est.hr_bpm is not None:
            table.append([f"{i0/fps:.0f}–{i1/fps:.0f} s", f"{est.hr_bpm:.0f}",
                          f"{est.quality:.2f}"])
            hrs.append(est.hr_bpm)
        else:
            reason = est.reason if est else "no detected frames"
            table.append([f"{i0/fps:.0f}–{i1/fps:.0f} s", "no estimate", reason])
    if hrs:
        summary = (f"<p class='hr-big'>{np.median(hrs):.0f} BPM</p>"
                   f"<p>Median of {len(hrs)} window estimate(s) · "
                   f"{len(hrs)}/{n_win} windows answered.<br>"
                   "Wellness demo only — not a medical measurement.</p>")
    else:
        summary = ("<p class='hr-big'>No estimate</p><p>No window passed the "
                   "quality gate. Try steadier lighting, a closer face, less "
                   "movement.</p>")
    return summary, table


with gr.Blocks(title="rppg-pulse — webcam heart-rate wellness demo") as demo:
    gr.HTML("<div class='disclaimer' role='note'>" + DISCLAIMER + "</div>")
    gr.Markdown("# rppg-pulse\nCamera-based pulse estimation (rPPG). "
                "CPU-only · nothing uploaded · open source.")
    with gr.Tab("Live webcam"):
        gr.Markdown("Allow camera access, then keep your face centred and "
                    "still for 15 seconds. The estimate updates continuously.")
        with gr.Row():
            cam = gr.Image(sources=["webcam"], streaming=True, type="numpy",
                           label="Webcam stream", height=320)
            status = gr.HTML("<p class='hr-big'>—</p><p>Camera not started.</p>",
                             label="Pulse estimate")
        buf = gr.State(None)
        cam.stream(live_frame, inputs=[cam, buf], outputs=[buf, status],
                   concurrency_limit=1)
    with gr.Tab("Upload a video"):
        gr.Markdown("No webcam? Upload a short face video (5–60 s, mp4/webm/avi). "
                    "The same frozen pipeline estimates pulse per 15 s window.")
        with gr.Row():
            vid = gr.Video(sources=["upload"], label="Face video (max 60 s)")
            with gr.Column():
                out_summary = gr.HTML(label="Summary")
                btn = gr.Button("Estimate pulse", variant="primary")
        out_table = gr.Dataframe(headers=["Window", "HR (BPM)", "Quality / reason"],
                                 label="Per-window estimates", wrap=True)
        btn.click(analyse_video, inputs=vid, outputs=[out_summary, out_table])
        gr.Examples(examples=[[str(ROOT / "assets" / "sample_face_72bpm.mp4")]],
                    inputs=vid, label="Try it without a webcam: synthetic face "
                    "with a known 72 BPM pulse (no real person)")
    gr.Markdown(
        "Pipeline: MediaPipe face ROI → spatial-mean RGB → POS (Wang et al. 2017) "
        "→ band-pass 0.7–3.0 Hz → spectral peak. Evaluation protocol, results and "
        "limitations: see the repository README. Made for the AI for Medicine "
        "hackathon with StellarFirm assistants (Healthy: protocol & statistics; "
        "Coder health: implementation & demo).")

if __name__ == "__main__":
    demo.queue(max_size=8).launch(server_name="0.0.0.0", server_port=7860,
                                  ssr_mode=False, css=CSS, mcp_server=False)
