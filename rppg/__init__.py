"""rppg-pulse: CPU-only remote photoplethysmography (rPPG) heart-rate estimation.

Wellness demo / research prototype. NOT a medical device.
Pipeline frozen in protocol/evaluation.md (Healthy, Scientist):
  MediaPipe face ROI -> spatial-mean RGB traces -> POS projection (Wang 2017)
  -> band-pass 0.7-3.0 Hz -> spectral-peak HR per non-overlapping 15 s window.
"""
SEED = 20261204
