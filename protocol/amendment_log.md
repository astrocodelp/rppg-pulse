- 2026-12-04 (pre-test): quality_threshold frozen at 0.45 by dev-only rule
  fixed in scripts/tune_dev.py before dev results were seen (min dev
  worst-case MAE, abstentions imputed 10 BPM; ties -> lowest threshold).
  Motion/light stratum thresholds = dev 75th/25th percentiles
  (reference-blind). params_frozen.json sha256
  ec4163d325894ac94316438df9666dcdc9a496ef1792ad4a7bcb91b509335046.
  Frozen BEFORE any test-split evaluation was run. No other deviations.
- 2026-12-04 (POST-HOC, after frozen test run; no effect on primary numbers):
  descriptive sensitivity analysis scripts/posthoc_sensitivity.py flags
  windows with mean device HR < 30 BPM as likely CMS50E dropout artefacts
  (Gudi 2020). 2 test windows (subject20) affected; test MAE 10.96 -> 8.08
  BPM under this rule. Primary frozen numbers remain the headline. Nothing
  in params_frozen.json, the split or the primary metrics was changed.
