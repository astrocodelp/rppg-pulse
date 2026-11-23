"""POS projection (Wang et al. 2017) and the green-channel baseline.

POS: temporal normalisation of the RGB traces by their window mean, projection
onto the plane orthogonal to the skin tone (1,1,1):
    S1 = G - B
    S2 = -R + G - B ... implemented exactly as in Wang 2017:
    S = [[0,1,-1],[-2,1,1]] @ Cn ;  h = S[0] + (std(S[0])/std(S[1])) * S[1]
The result is mean-centred. No detrending beyond what POS prescribes.
"""
from __future__ import annotations

import numpy as np


def pos_signal(rgb: np.ndarray) -> np.ndarray:
    """rgb: (T, 3) spatial-mean traces in R,G,B order -> POS pulse signal (T,)."""
    rgb = np.asarray(rgb, dtype=np.float64)
    mean = rgb.mean(axis=0)
    if np.any(mean <= 0):
        raise ValueError("non-positive channel mean; window unusable")
    cn = rgb / mean  # temporal normalisation
    s1 = cn[:, 1] - cn[:, 2]
    s2 = -2.0 * cn[:, 0] + cn[:, 1] + cn[:, 2]
    sd1, sd2 = s1.std(), s2.std()
    alpha = sd1 / sd2 if sd2 > 1e-12 else 0.0
    h = s1 + alpha * s2
    return h - h.mean()


def green_signal(rgb: np.ndarray) -> np.ndarray:
    """Baseline: mean-normalised, mean-centred green channel (Verkruysse 2008)."""
    rgb = np.asarray(rgb, dtype=np.float64)
    g = rgb[:, 1]
    m = g.mean()
    if m <= 0:
        raise ValueError("non-positive green mean")
    g = g / m
    return g - g.mean()


def chrom_signal(rgb: np.ndarray, fs: float) -> np.ndarray:
    """CHROM (de Haan & Jeanne 2013), secondary comparator, DEV ONLY.

    Temporal normalisation, chrominance projections X = 3R - 2G,
    Y = 1.5R + G - 1.5B, band-passed, then S = X - (std(X)/std(Y)) Y.
    """
    from scipy.signal import butter, sosfiltfilt
    rgb = np.asarray(rgb, dtype=np.float64)
    mean = rgb.mean(axis=0)
    if np.any(mean <= 0):
        raise ValueError("non-positive channel mean")
    cn = rgb / mean
    x = 3.0 * cn[:, 0] - 2.0 * cn[:, 1]
    y = 1.5 * cn[:, 0] + cn[:, 1] - 1.5 * cn[:, 2]
    sos = butter(3, [0.7, 3.0], btype="bandpass", fs=fs, output="sos")
    x = sosfiltfilt(sos, x)
    y = sosfiltfilt(sos, y)
    sy = y.std()
    alpha = x.std() / sy if sy > 1e-12 else 0.0
    s = x - alpha * y
    return s - s.mean()
