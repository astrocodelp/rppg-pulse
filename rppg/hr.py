"""Band-pass + spectral-peak HR estimation per non-overlapping window.

Frozen design (protocol/evaluation.md §2.3, ubfc_benchmark_plan.md §4):
  band-pass 0.7-3.0 Hz (42-180 BPM), FFT spectral peak on the window signal,
  quality gate: face detected >= 80% of frames, effective fps >= 15,
  spectral quality index >= frozen threshold, else abstain ("no estimate").

Quality index: fraction of in-band spectral power inside the Hann main lobe
(+/- 2/T Hz around the dominant peak, T = window duration) relative to total
in-band power — a periodicity score. Halfwidth tied to window resolution so a
clean sinusoid scores ~1 regardless of window length (dev-stage choice,
recorded in params_frozen.json).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, sosfiltfilt

BAND_HZ = (0.7, 3.0)
MIN_FACE_FRAC = 0.80
MIN_FPS = 15.0


@dataclass
class HREstimate:
    hr_bpm: float | None       # None = abstained
    quality: float             # spectral periodicity index 0..1
    reason: str                # "" if estimated, else abstention reason


def bandpass(x: np.ndarray, fs: float, band=BAND_HZ) -> np.ndarray:
    sos = butter(3, [band[0], band[1]], btype="bandpass", fs=fs, output="sos")
    # sosfiltfilt needs len > padlen; 15 s @ 30 fps = 450 samples is plenty.
    return sosfiltfilt(sos, x)


def spectral_hr(x: np.ndarray, fs: float, band=BAND_HZ,
                peak_halfwidth_hz: float | None = None) -> tuple[float, float]:
    """Return (hr_bpm, quality). Zero-padded periodogram (Hann window) of the
    filtered signal; peak = max-power frequency in band; quality = power within
    the Hann main lobe of the peak divided by total in-band power."""
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    if peak_halfwidth_hz is None:
        peak_halfwidth_hz = 2.0 / (len(x) / fs)
    nfft = int(2 ** np.ceil(np.log2(len(x))) * 4)  # >= 4x zero pad
    win = np.hanning(len(x))
    spec = np.abs(np.fft.rfft(x * win, n=nfft)) ** 2
    freqs = np.fft.rfftfreq(nfft, d=1.0 / fs)
    inband = (freqs >= band[0]) & (freqs <= band[1])
    p = spec[inband]
    f = freqs[inband]
    if p.sum() <= 0:
        return float("nan"), 0.0
    k = int(np.argmax(p))
    f0 = f[k]
    near = np.abs(f - f0) <= peak_halfwidth_hz
    quality = float(p[near].sum() / p.sum())
    return float(f0 * 60.0), quality


def estimate_window(sig: np.ndarray, fs: float, face_frac: float,
                    quality_threshold: float, band=BAND_HZ) -> HREstimate:
    """Apply the frozen quality gate, then band-pass + spectral peak."""
    if face_frac < MIN_FACE_FRAC:
        return HREstimate(None, 0.0, "face_not_detected")
    if fs < MIN_FPS:
        return HREstimate(None, 0.0, "low_fps")
    if len(sig) < int(fs * 5):
        return HREstimate(None, 0.0, "too_short")
    try:
        filtered = bandpass(sig, fs, band)
    except ValueError:
        return HREstimate(None, 0.0, "too_short")
    hr, q = spectral_hr(filtered, fs, band)
    if not np.isfinite(hr):
        return HREstimate(None, 0.0, "flat_signal")
    if q < quality_threshold:
        return HREstimate(None, q, "low_quality")
    return HREstimate(hr, q, "")
