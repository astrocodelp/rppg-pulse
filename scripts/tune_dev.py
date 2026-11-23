"""Development-only tuning + freezing of params_frozen.json.

Selection rules fixed BEFORE looking at any dev results (this file committed
together with params_frozen.json):

* quality_threshold: candidates [0.20, 0.25, 0.30, 0.35, 0.40, 0.45].
  Pick the candidate minimising DEV worst-case MAE (abstentions imputed at
  10 BPM per the protocol's worst-case metric); ties -> lowest threshold
  (more coverage). This balances accuracy against abstention without ever
  touching test data or per-window references beyond the frozen metric.
* motion_px_p95_threshold: 75th percentile of dev window motion_px_p95
  (descriptive stratum only; reference-blind).
* low_light_luma_threshold: 25th percentile of dev window mean ROI luma
  (descriptive stratum only; reference-blind).

Everything else (window 15 s, band-pass 0.7-3.0 Hz, POS, ROI polygons, seed
20261204) is fixed by protocol/evaluation.md and not tunable here.

Run: python3 scripts/tune_dev.py   (requires all 21 dev traces present)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rppg.windows import run_split

CANDIDATES = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45]


def main():
    split = json.loads((ROOT / "split_manifest.json").read_text())
    dev = split["dev"]
    traces = ROOT / "data" / "traces"
    missing = [s for s in dev if not (traces / f"{s}.npz").exists()]
    if missing:
        raise SystemExit(f"dev traces missing: {missing}")
    base = {"quality_threshold": 0.0, "motion_px_p95_threshold": 1e9,
            "low_light_luma_threshold": 0.0}
    rows0 = run_split(traces, dev, base)
    motion = np.array([r["motion_px_p95"] for r in rows0], float)
    luma = np.array([r["luma_mean"] for r in rows0], float)
    motion_thr = float(np.nanpercentile(motion, 75))
    luma_thr = float(np.nanpercentile(luma, 25))

    table = []
    for thr in CANDIDATES:
        p = {"quality_threshold": thr,
             "motion_px_p95_threshold": motion_thr,
             "low_light_luma_threshold": luma_thr}
        rows = run_split(traces, dev, p)
        est = np.array([r["hr_est_bpm"] if r["hr_est_bpm"] != "" else np.nan
                        for r in rows], float)
        ref = np.array([r["hr_ref_bpm"] for r in rows], float)
        ok = np.isfinite(ref)
        e, rr = est[ok], ref[ok]
        answered = np.isfinite(e)
        err = np.where(answered, np.abs(e - rr), 10.0)
        mae_answered = float(np.abs(e[answered] - rr[answered]).mean()) if answered.any() else float("nan")
        wc = float(err.mean())
        table.append({"threshold": thr, "coverage": float(answered.mean()),
                      "mae_answered_bpm": mae_answered, "worst_case_mae_bpm": wc})
        print(json.dumps(table[-1]))
    best = min(table, key=lambda t: (t["worst_case_mae_bpm"], t["threshold"]))
    params = {
        "window_s": 15.0,
        "bandpass_hz": [0.7, 3.0],
        "method": "POS (Wang et al. 2017)",
        "roi": "MediaPipe FaceLandmarker forehead+cheeks polygons (rppg/roi.py)",
        "fps_nominal": 30.0,
        "min_face_detect_frac": 0.8,
        "min_eff_fps": 15.0,
        "quality_threshold": best["threshold"],
        "motion_px_p95_threshold": round(motion_thr, 3),
        "low_light_luma_threshold": round(luma_thr, 2),
        "seed": 20261204,
        "selection_rule": "min dev worst-case MAE (abstentions=10 BPM); ties -> lowest threshold",
        "dev_tuning_table": table,
        "frozen_before_test_run": True,
    }
    txt = json.dumps(params, indent=1) + "\n"
    (ROOT / "params_frozen.json").write_text(txt)
    print("frozen quality_threshold:", best["threshold"])
    print("params sha256:", hashlib.sha256(txt.encode()).hexdigest())


if __name__ == "__main__":
    main()
