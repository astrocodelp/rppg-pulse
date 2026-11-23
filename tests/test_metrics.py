"""Unit tests: metrics (§3 exact definitions) and HR estimator, on synthetic
data with known answers — required by the protocol before touching real data."""
import numpy as np
import pytest

from rppg import metrics as M
from rppg.hr import bandpass, spectral_hr, estimate_window
from rppg.signal import pos_signal, green_signal


def test_mae_rmse_known():
    est = np.array([70.0, 80.0, 90.0])
    ref = np.array([72.0, 78.0, 96.0])
    assert M.mae(est, ref) == pytest.approx((2 + 2 + 6) / 3)
    assert M.rmse(est, ref) == pytest.approx(np.sqrt((4 + 4 + 36) / 3))


def test_scored_pairs_skip_nan():
    est = np.array([70.0, np.nan, 90.0])
    ref = np.array([72.0, 78.0, np.nan])
    e, r, ok = M.scored_pairs(est, ref)
    assert list(e) == [70.0] and list(r) == [72.0]
    assert ok.tolist() == [True, False, False]


def test_coverage_and_failure():
    est = np.array([70.0, np.nan, 90.0, 55.0])
    ref = np.array([72.0, 78.0, 91.0, 70.0])
    assert M.coverage(est, ref) == pytest.approx(0.75)
    # scored: |−2|, |−1|, |−15| -> 1/3 failures (>10 BPM)
    assert M.failure_rate(est, ref) == pytest.approx(1 / 3)


def test_bland_altman_subject_level():
    # subject A errors +2,+4 (mean 3); subject B errors -1,-3 (mean -2)
    est = np.array([72.0, 74.0, 69.0, 67.0])
    ref = np.array([70.0, 70.0, 70.0, 70.0])
    subj = np.array(["A", "A", "B", "B"])
    ba = M.bland_altman(est, ref, subj)
    assert ba["bias_bpm"] == pytest.approx(0.5)
    sd = np.std([3.0, -2.0], ddof=1)
    assert ba["loa_low_bpm"] == pytest.approx(0.5 - 1.96 * sd)
    assert ba["loa_high_bpm"] == pytest.approx(0.5 + 1.96 * sd)
    assert ba["window_bias_bpm"] == pytest.approx(0.5)


def test_pearson_perfect():
    x = np.arange(10, dtype=float)
    r, (lo, hi) = M.pearson_r_ci(x, 2 * x + 1)
    assert r == pytest.approx(1.0, abs=1e-5)
    assert lo > 0.9 and hi <= 1.0 + 1e-9  # clipped Fisher-z near r=1


def test_cluster_bootstrap_deterministic_and_covers():
    rng = np.random.default_rng(7)
    subj = np.repeat([f"S{i}" for i in range(10)], 20)
    ref = rng.uniform(60, 100, len(subj))
    est = ref + rng.normal(0, 2, len(subj))
    p1, lo1, hi1 = M.cluster_bootstrap(est, ref, subj, reps=500)
    p2, lo2, hi2 = M.cluster_bootstrap(est, ref, subj, reps=500)
    assert (p1, lo1, hi1) == (p2, lo2, hi2)  # fixed seed
    assert lo1 < p1 < hi1
    assert p1 == pytest.approx(M.mae(est, ref))


def test_paired_baseline_diff_sign():
    subj = np.repeat(["A", "B"], 10)
    ref = np.full(20, 80.0)
    est = ref + 1.0  # pipeline MAE 1
    pt, lo, hi = M.paired_baseline_diff(est, ref, 60.0, subj, reps=500)
    assert pt == pytest.approx(1.0 - 20.0)
    assert hi < 0  # clearly better than constant


def test_worst_case_mae():
    est = np.array([70.0, np.nan, 90.0])
    ref = np.array([72.0, 78.0, 91.0])
    # errors 2, imputed 10, 1 -> mean 13/3
    assert M.worst_case_mae(est, ref) == pytest.approx(13 / 3)


def test_spectral_hr_recovers_known_frequency():
    fs = 30.0
    t = np.arange(int(15 * fs)) / fs
    for bpm in (48.0, 72.0, 105.0, 150.0):
        x = np.sin(2 * np.pi * (bpm / 60) * t) + 0.3 * np.sin(2 * np.pi * 0.1 * t)
        hr, q = spectral_hr(bandpass(x, fs), fs)
        assert abs(hr - bpm) < 1.0, f"{bpm}: got {hr}"
        assert q > 0.5


def test_bandpass_removes_out_of_band():
    fs = 30.0
    t = np.arange(int(15 * fs)) / fs
    x = np.sin(2 * np.pi * 0.1 * t) + np.sin(2 * np.pi * 1.2 * t) + np.sin(2 * np.pi * 8 * t)
    y = bandpass(x, fs)
    hr, q = spectral_hr(y, fs)
    assert abs(hr - 72.0) < 1.0
    assert q > 0.8


def test_quality_gate_abstains():
    fs = 30.0
    rng = np.random.default_rng(1)
    noise = rng.normal(0, 1, int(15 * fs))
    est = estimate_window(noise, fs, face_frac=1.0, quality_threshold=0.5)
    assert est.hr_bpm is None and est.reason == "low_quality"
    est = estimate_window(np.zeros(450), fs, face_frac=0.5, quality_threshold=0.5)
    assert est.hr_bpm is None and est.reason == "face_not_detected"
    est = estimate_window(np.zeros(450), 10.0, face_frac=1.0, quality_threshold=0.5)
    assert est.hr_bpm is None and est.reason == "low_fps"


def test_pos_removes_common_mode():
    # pure intensity change (all channels scale together) -> POS ~ 0
    t = np.arange(450)
    scale = 1 + 0.05 * np.sin(2 * np.pi * 0.2 * t / 30)
    rgb = np.outer(scale, np.array([120.0, 90.0, 70.0]))
    h = pos_signal(rgb)
    assert np.max(np.abs(h)) < 1e-9
    # pulse-like modulation strongest in green -> POS non-zero
    pulse = 1 + 0.01 * np.sin(2 * np.pi * 1.2 * t / 30)
    rgb2 = rgb * np.column_stack([0.3 * (pulse - 1) + 1, pulse, 0.6 * (pulse - 1) + 1])
    h2 = pos_signal(rgb2)
    hr, q = spectral_hr(bandpass(h2, 30.0), 30.0)
    assert abs(hr - 72.0) < 1.0


def test_green_baseline():
    t = np.arange(450)
    pulse = 1 + 0.01 * np.sin(2 * np.pi * 1.5 * t / 30)
    rgb = np.column_stack([np.full(450, 120.0), 90 * pulse, np.full(450, 70.0)])
    g = green_signal(rgb)
    hr, q = spectral_hr(bandpass(g, 30.0), 30.0)
    assert abs(hr - 90.0) < 1.0
