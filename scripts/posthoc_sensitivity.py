"""POST-HOC descriptive sensitivity analysis (NOT the primary metric).

Written after the frozen test run; changes nothing in params_frozen.json,
the primary report or the CSVs. Motivation: the frozen reference-blind rule
excludes only flat non-positive device HR, but the CMS50E also emits
physiologically implausible low positive values during fingertip dropouts
(e.g. 4.6 BPM mid-game). Gudi et al. 2020 (10.3390/app10238630) documents
exactly this class of benchmark ground-truth artefact.

Rule (applied identically to dev and test, reference-only): a window whose
mean device HR < 30 BPM is flagged as a likely device artefact. We report
primary metrics with and without those windows; both are published.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import rppg.metrics as M  # noqa: E402

SEED = 20261204


def arr(s):
    return pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)


OUT = {}
for split in ("dev", "test"):
    df = pd.read_csv(ROOT / f"results/windows_{split}.csv")
    artefact = df["hr_ref_bpm"] < 30.0
    keep = df[~artefact]
    est = arr(keep["hr_est_bpm"])
    ref = arr(keep["hr_ref_bpm"])
    subj = keep["subject_id"].to_numpy()
    mae_pt, mae_lo, mae_hi = M.cluster_bootstrap(est, ref, subj, M.mae, seed=SEED)
    rmse_pt, rmse_lo, rmse_hi = M.cluster_bootstrap(est, ref, subj, M.rmse, seed=SEED)
    primary = json.loads((ROOT / f"results/metrics_{split}.json").read_text())
    OUT[split] = {
        "rule": "mean device HR < 30 BPM flagged as likely CMS50E dropout artefact (reference-only, post-hoc)",
        "n_artefact_windows": int(artefact.sum()),
        "artefact_subjects": sorted(df.loc[artefact, "subject_id"].unique().tolist()),
        "primary_pos_mae_bpm": primary["pos"]["mae_bpm"],
        "sensitivity_pos_mae_bpm": mae_pt,
        "sensitivity_pos_mae_ci95": [mae_lo, mae_hi],
        "sensitivity_pos_rmse_bpm": rmse_pt,
        "sensitivity_pos_rmse_ci95": [rmse_lo, rmse_hi],
        "sensitivity_pos_coverage": M.coverage(est, ref),
        "sensitivity_pos_failure_gt10": M.failure_rate(est, ref),
        "sensitivity_bland_altman": M.bland_altman(est, ref, subj),
    }
    print(split, json.dumps({k: v for k, v in OUT[split].items()
                             if k != "sensitivity_bland_altman"}, indent=1))
txt = json.dumps(OUT, indent=1) + "\n"
(ROOT / "results/posthoc_artefact_sensitivity.json").write_text(txt)
print("written results/posthoc_artefact_sensitivity.json")
