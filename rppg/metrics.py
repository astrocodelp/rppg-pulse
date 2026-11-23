"""Metrics exactly per protocol/evaluation.md §3 (Healthy, frozen 2026-11-22).

MAE, RMSE (BPM); Pearson r with Fisher-z 95% CI; Bland-Altman with
subject-level bias and subject-level SD for limits of agreement;
coverage; failure rate (|error| > 10 BPM); constant and green baselines;
cluster bootstrap over subjects (10,000 replicates, percentile 95% CI,
seed 20261204). Unit-tested in tests/test_metrics.py before real data.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

SEED = 20261204
FAILURE_BPM = 10.0
BOOT_REPS = 10000


def scored_pairs(est, ref):
    """Keep only windows with both an estimate and a reference (coverage rule)."""
    est = np.asarray(est, dtype=float)
    ref = np.asarray(ref, dtype=float)
    ok = np.isfinite(est) & np.isfinite(ref)
    return est[ok], ref[ok], ok


def mae(est, ref):
    e, r, _ = scored_pairs(est, ref)
    return float(np.mean(np.abs(e - r))) if len(e) else float("nan")


def rmse(est, ref):
    e, r, _ = scored_pairs(est, ref)
    return float(np.sqrt(np.mean((e - r) ** 2))) if len(e) else float("nan")


def pearson_r_ci(est, ref, alpha=0.05):
    """Pearson r + Fisher-z CI (window-level, descriptive; cluster bootstrap
    is the primary uncertainty statement)."""
    e, r, _ = scored_pairs(est, ref)
    n = len(e)
    if n < 4 or np.std(e) == 0 or np.std(r) == 0:
        return float("nan"), (float("nan"), float("nan"))
    rho = float(stats.pearsonr(e, r).statistic)
    z = np.arctanh(np.clip(rho, -0.999999, 0.999999))
    se = 1.0 / np.sqrt(n - 3)
    zc = stats.norm.ppf(1 - alpha / 2)
    lo, hi = np.tanh([z - zc * se, z + zc * se])
    return rho, (float(lo), float(hi))


def bland_altman(est, ref, subjects):
    """Subject-level bias and LoA per protocol: mean error per subject first,
    then bias = mean of subject means, LoA = bias +/- 1.96 * SD(subject means).
    Window-level bias/SD returned alongside for the window-level plot."""
    e, r, ok = scored_pairs(est, ref)
    subj = np.asarray(subjects)[ok]
    d = e - r
    per = {}
    for s in np.unique(subj):
        per[str(s)] = float(d[subj == s].mean())
    means = np.array(list(per.values()))
    bias = float(means.mean())
    sd = float(means.std(ddof=1)) if len(means) > 1 else float("nan")
    return {
        "bias_bpm": bias,
        "loa_low_bpm": bias - 1.96 * sd,
        "loa_high_bpm": bias + 1.96 * sd,
        "subject_sd_bpm": sd,
        "n_subjects": len(means),
        "window_bias_bpm": float(d.mean()),
        "window_sd_bpm": float(d.std(ddof=1)) if len(d) > 1 else float("nan"),
        "per_subject_bias_bpm": per,
    }


def coverage(est, ref):
    """Fraction of reference-bearing windows that produced an estimate."""
    est = np.asarray(est, dtype=float)
    ref = np.asarray(ref, dtype=float)
    have_ref = np.isfinite(ref)
    if not have_ref.any():
        return float("nan")
    return float(np.isfinite(est[have_ref]).mean())


def failure_rate(est, ref):
    e, r, _ = scored_pairs(est, ref)
    return float(np.mean(np.abs(e - r) > FAILURE_BPM)) if len(e) else float("nan")


def cluster_bootstrap(est, ref, subjects, stat_fn=mae, reps=BOOT_REPS, seed=SEED):
    """Percentile 95% CI resampling SUBJECTS with replacement (windows within
    a resampled subject stay together). Returns (point, lo, hi)."""
    est = np.asarray(est, dtype=float)
    ref = np.asarray(ref, dtype=float)
    subjects = np.asarray(subjects)
    point = stat_fn(est, ref)
    uniq = np.unique(subjects)
    groups = [np.where(subjects == s)[0] for s in uniq]
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    for b in range(reps):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[k] for k in pick])
        vals[b] = stat_fn(est[idx], ref[idx])
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return float(point), float(lo), float(hi)


def paired_baseline_diff(est, ref, const_value, subjects, reps=BOOT_REPS, seed=SEED):
    """Per-subject paired MAE difference (pipeline - constant baseline),
    cluster-bootstrap CI. Negative = pipeline better."""
    est = np.asarray(est, dtype=float)
    ref = np.asarray(ref, dtype=float)
    subjects = np.asarray(subjects)
    # compute on scored windows only
    e, r, ok = scored_pairs(est, ref)
    s = subjects[ok]
    err_pipe = np.abs(e - r)
    err_const = np.abs(const_value - r)

    def stat_fn(idx):
        return float(err_pipe[idx].mean() - err_const[idx].mean())

    point = stat_fn(np.arange(len(e)))
    uniq = np.unique(s)
    groups = [np.where(s == u)[0] for u in uniq]
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    for b in range(reps):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[k] for k in pick])
        vals[b] = stat_fn(idx)
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return point, float(lo), float(hi)


def worst_case_mae(est, ref, impute_bpm=FAILURE_BPM):
    """Sensitivity per §4.4: quality-excluded (abstained but referenced)
    windows scored as failures with imputed error 10 BPM."""
    est = np.asarray(est, dtype=float)
    ref = np.asarray(ref, dtype=float)
    have_ref = np.isfinite(ref)
    err = np.abs(est[have_ref] - ref[have_ref])
    err = np.where(np.isfinite(err), err, impute_bpm)
    return float(err.mean()) if len(err) else float("nan")
