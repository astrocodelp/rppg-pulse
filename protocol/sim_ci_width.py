"""Sample-size illustration for evaluation.md §4.2 (run BEFORE data collection).

Monte Carlo check of the cluster-bootstrap 95% CI width for subject-level
window MAE, under an assumed error model. Model-dependent illustration only.

Environment: NumPy 2.5.5, SciPy 1.18.1. Seed fixed: 20261204.
Run: python3 sim_ci_width.py
Checked output (2026-11-22):
  n_subjects=10, windows/subj=20: median 95% CI width = 1.34 BPM
  n_subjects=15, windows/subj=20: median 95% CI width = 1.16 BPM
  n_subjects=20, windows/subj=20: median 95% CI width = 1.02 BPM
  t(0.975, df=9) = 2.262157162798205
"""
import numpy as np
import scipy
from scipy import stats

print("numpy", np.__version__, "scipy", scipy.__version__)
rng = np.random.default_rng(20261204)
true_mae = 2.5   # assumed true MAE, BPM
within_sd = 1.5  # assumed within-subject error SD, BPM
nwin = 20        # windows per subject (24 in protocol; 20 used conservatively)

for nsub in [10, 15, 20]:
    widths = []
    for _ in range(2000):
        subj_err = np.abs(rng.normal(0, true_mae, nsub))[:, None] \
            + rng.normal(0, within_sd, (nsub, nwin))
        boot = [np.abs(subj_err[rng.integers(0, nsub, nsub)]).mean()
                for _ in range(500)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
        widths.append(hi - lo)
    print(f"n_subjects={nsub}, windows/subj={nwin}: "
          f"median 95% CI width = {np.median(widths):.2f} BPM")

print("t(0.975, df=9) =", stats.t.ppf(0.975, 9))
