"""Window-level estimation from cached ROI traces (or live video via rppg.roi).

Time base: UBFC REALISTIC nominal 30 fps from frame index per the dataset
page and the authors' reader; ground-truth line-3 timestamps aligned at t=0.
The container reports ~29.26 fps (avi rounding of the raw stream); the plan
freezes nominal 30 fps. Effective fps for the quality gate is measured from
decoded frame count / duration.

Missing RGB rows (face not detected on a frame) are linearly interpolated
inside the window before POS; windows failing the >=80% detection gate are
abstained anyway, so interpolation only touches <=20% of samples.

Ground truth per window: mean of device HR values (line 2) whose timestamps
(line 3) fall inside [t0, t1). Flat/missing device HR -> reference NaN
(reference-blind exclusion, counted).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from rppg.hr import estimate_window, bandpass, spectral_hr
from rppg.signal import pos_signal, green_signal, chrom_signal

NOMINAL_FPS = 30.0
WINDOW_S = 15.0


def interpolate_rgb(rgb: np.ndarray) -> np.ndarray:
    """Linear interpolation over NaN rows; edge rows held constant."""
    rgb = np.array(rgb, dtype=np.float64)
    T = len(rgb)
    good = np.isfinite(rgb).all(axis=1)
    if good.all():
        return rgb
    if not good.any():
        raise ValueError("no detected frames")
    idx = np.arange(T)
    for c in range(3):
        rgb[:, c] = np.interp(idx, idx[good], rgb[good, c])
    return rgb


def windows_from_trace(npz_path: str | Path, params: dict) -> list[dict]:
    z = np.load(npz_path)
    subject = Path(npz_path).stem
    rgb = z["rgb"]
    detected = z["detected"]
    luma = z["luma"]
    centers = z["centers"]
    T = int(z["frame_count"])
    fps = NOMINAL_FPS
    gt_hr, gt_t = z["gt_hr"], z["gt_t"]
    duration = T / fps
    n_win = int(duration // WINDOW_S)
    out = []
    qthr = params["quality_threshold"]
    for k in range(n_win):
        i0, i1 = int(k * WINDOW_S * fps), int((k + 1) * WINDOW_S * fps)
        t0, t1 = i0 / fps, i1 / fps
        seg = rgb[i0:i1]
        det = detected[i0:i1]
        face_frac = float(det.mean())
        eff_fps = float(len(seg) / WINDOW_S)
        # reference
        m = (gt_t >= t0) & (gt_t < t1)
        hr_ref = float(np.mean(gt_hr[m])) if m.any() else float("nan")
        if m.any() and np.std(gt_hr[m]) == 0 and gt_hr[m][0] <= 0:
            hr_ref = float("nan")
        # flags (descriptive strata, reference-blind)
        cen = centers[i0:i1]
        if np.isfinite(cen).all(axis=1).sum() > 2:
            d = np.diff(cen[np.isfinite(cen).all(axis=1)], axis=0)
            motion_px = float(np.percentile(np.linalg.norm(d, axis=1), 95))
        else:
            motion_px = float("nan")
        lm = luma[i0:i1]
        mean_luma = float(np.nanmean(lm)) if np.isfinite(lm).any() else float("nan")
        rec = {
            "subject_id": subject, "window_start_s": t0, "window_end_s": t1,
            "face_detect_frac": round(face_frac, 4), "eff_fps": eff_fps,
            "lux": "", "motion_px_p95": round(motion_px, 3),
            "luma_mean": round(mean_luma, 2),
            "motion_flag": int(motion_px > params["motion_px_p95_threshold"])
                if np.isfinite(motion_px) else "",
            "low_light_flag": int(mean_luma < params["low_light_luma_threshold"])
                if np.isfinite(mean_luma) else "",
            "hr_ref_bpm": hr_ref,
        }
        # estimates
        est_pos, est_green, est_chrom = None, None, None
        reason, quality = "", 0.0
        try:
            seg_i = interpolate_rgb(seg)
            sig = pos_signal(seg_i)
            e = estimate_window(sig, fps, face_frac, qthr)
            est_pos, quality, reason = e.hr_bpm, e.quality, e.reason
            if e.hr_bpm is not None:
                gsig = green_signal(seg_i)
                from rppg.hr import bandpass as bp
                gh, gq = spectral_hr(bp(gsig, fps), fps)
                est_green = gh if gq >= qthr else None
                csig = chrom_signal(seg_i, fps)
                ch, cq = spectral_hr(csig, fps)
                est_chrom = ch if cq >= qthr else None
        except ValueError:
            reason = reason or "no_detected_frames"
        rec.update({
            "hr_est_bpm": est_pos if est_pos is not None else "",
            "hr_green_bpm": est_green if est_green is not None else "",
            "hr_chrom_bpm": est_chrom if est_chrom is not None else "",
            "quality_score": round(quality, 4),
            "excluded": int(est_pos is None),
            "exclusion_reason": reason,
            "dataset": "UBFC", "condition": "game",
        })
        out.append(rec)
    return out


def run_split(traces_dir: str | Path, split: list[str], params: dict) -> list[dict]:
    rows = []
    for s in split:
        rows.extend(windows_from_trace(Path(traces_dir) / f"{s}.npz", params))
    return rows
