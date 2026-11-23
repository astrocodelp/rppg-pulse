"""Download UBFC-rPPG Dataset 2 (REALISTIC) from the public HF mirror and
build compact RGB-trace caches for evaluation.

Dataset files are NEVER committed (no standard license text on the official
page; research use only — see protocol/ubfc_benchmark_plan.md).

Resumable per subject:
  python3 scripts/fetch_dataset.py pipeline   # download -> traces -> delete raw

Traces cache per subject (data/traces/subjectN.npz):
  rgb (T,3) spatial-mean ROI trace (NaN rows where face not detected),
  detected (T,) bool, centers (T,2), luma (T,), face_h (T,),
  frame_count, nominal_fps, width, height, video_sha256_first16MB,
  gt_ppg, gt_hr, gt_t (ground truth rows verbatim).
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "UBFC"
TRACES = ROOT / "data" / "traces"
REPO_ID = "thachha901/UBFC"


def subjects():
    """The REALISTIC universe: IDs 1..49 minus 7 IDs absent from this mirror
    {2,6,7,19,21,28,29}. 42 subjects, matching the official count,
    verified against the mirror listing.
    """
    simple = {2, 6, 7, 19, 21, 28, 29}  # absent from mirror; 49-7=42 folders
    return [f"subject{i}" for i in range(1, 50) if i not in simple]


def pipeline():
    """Per-subject download -> traces -> delete raw video, so raw videos never
    pile up (75 GB total > free disk). Resumable at subject granularity."""
    from huggingface_hub import hf_hub_download
    sys.path.insert(0, str(ROOT))
    from rppg.roi import FaceROI, face_bbox_from_frames
    DATA.mkdir(parents=True, exist_ok=True)
    TRACES.mkdir(parents=True, exist_ok=True)
    roi = FaceROI()
    for s in subjects():
        out = TRACES / f"{s}.npz"
        if out.exists():
            print("skip (cached)", s, flush=True)
            continue
        gtf = DATA / s / "ground_truth.txt"
        vid = DATA / s / "vid.avi"
        t0 = time.time()
        if not (gtf.exists() and gtf.stat().st_size > 100):
            hf_hub_download(REPO_ID, f"UBFC/{s}/ground_truth.txt",
                            repo_type="dataset", local_dir=str(DATA.parent))
        if not vid.exists():
            hf_hub_download(REPO_ID, f"UBFC/{s}/vid.avi", repo_type="dataset",
                            local_dir=str(DATA.parent))
        tdl = time.time() - t0
        from rppg import video as vidio
        try:
            info = vidio.probe(vid)
        except Exception:
            print(f"{s}: corrupt/partial vid.avi, re-downloading", flush=True)
            vid.unlink(missing_ok=True)
            hf_hub_download(REPO_ID, f"UBFC/{s}/vid.avi", repo_type="dataset",
                            local_dir=str(DATA.parent))
            info = vidio.probe(vid)
        fps = info.fps
        h, w = info.height, info.width
        sha = hashlib.sha256()
        with open(vid, "rb") as fh:
            sha.update(fh.read(16 * 1024 * 1024))
        # pass 1: stream frames, keep ~9 probes for the face bbox
        probe_every = max(1, info.n_frames // 9) if info.n_frames else 200
        probes = []
        for i, fr in vidio.read_frames(vid):
            if i % probe_every == 0:
                probes.append(fr)
            if len(probes) >= 9:
                break
        bbox = face_bbox_from_frames(np.stack(probes), roi) if probes else None
        del probes
        nmax = info.n_frames if info.n_frames else int(info.duration_s * fps) + 10
        rgb_trace = np.full((nmax, 3), np.nan)
        detected = np.zeros(nmax, dtype=bool)
        centers = np.full((nmax, 2), np.nan)
        luma = np.full(nmax, np.nan)
        face_h = np.zeros(nmax)
        x, y, bw, bh = bbox if bbox else (0, 0, w, h)
        # pass 2: stream again, cropped by ffmpeg, landmark per frame
        for i, crop in vidio.read_frames(vid, crop=(x, y, bw, bh)):
            if i >= len(rgb_trace):
                break
            r = roi.process(crop)
            detected[i] = r.detected
            face_h[i] = r.face_h
            if r.detected:
                rgb_trace[i] = r.rgb_mean
                centers[i] = r.center + np.array([x, y])
                luma[i] = r.luma
            T = i + 1
        rgb_trace, detected = rgb_trace[:T], detected[:T]
        centers, luma, face_h = centers[:T], luma[:T], face_h[:T]
        gt = np.loadtxt(gtf)
        np.savez_compressed(
            out, rgb=rgb_trace, detected=detected, centers=centers,
            luma=luma, face_h=face_h, nominal_fps=fps, frame_count=T,
            width=w, height=h, video_sha256_first16mb=sha.hexdigest(),
            gt_ppg=gt[0], gt_hr=gt[1], gt_t=gt[2], bbox=np.array([x, y, bw, bh]),
        )
        vid.unlink()  # free disk; trace cache is the committed-work artifact
        print(f"{s}: T={T} fps={fps:.3f} det={detected.mean():.3f} "
              f"dl={tdl:.0f}s total={time.time()-t0:.0f}s", flush=True)
    roi.close()
    print("PIPELINE COMPLETE", flush=True)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "pipeline"
    {"pipeline": pipeline}[stage]()
