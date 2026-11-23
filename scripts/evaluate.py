"""Frozen-protocol evaluation runner.

  python3 scripts/evaluate.py dev     # tuning on development subjects only
  python3 scripts/evaluate.py test    # held-out, run ONCE with frozen params

Writes results/windows_<split>.csv, results/metrics_<split>.json,
results/report_ubfc.md, results/figures/*.png. Seed 20261204 everywhere.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rppg import metrics as M
from rppg.windows import run_split

TRACES = ROOT / "data" / "traces"
RESULTS = ROOT / "results"


def load_split():
    m = json.loads((ROOT / "split_manifest.json").read_text())
    assert m["seed"] == 20261204
    return m


def summarise(rows, split_name, constant_hr, params):
    import pandas as pd
    df = pd.DataFrame(rows)
    est = pd.to_numeric(df["hr_est_bpm"], errors="coerce").to_numpy(float)
    grn = pd.to_numeric(df["hr_green_bpm"], errors="coerce").to_numpy(float)
    ref = pd.to_numeric(df["hr_ref_bpm"], errors="coerce").to_numpy(float)
    subj = df["subject_id"].to_numpy()
    const = np.full_like(ref, constant_hr)

    out = {"split": split_name, "n_windows": len(df),
           "n_subjects": int(df["subject_id"].nunique()),
           "constant_baseline_bpm": constant_hr}
    for name, e in (("pos", est), ("green", grn), ("constant", const)):
        p_mae, lo, hi = M.cluster_bootstrap(e, ref, subj, M.mae)
        p_rmse, rlo, rhi = M.cluster_bootstrap(e, ref, subj, M.rmse)
        r, (rlo2, rhi2) = M.pearson_r_ci(e, ref)
        out[name] = {
            "mae_bpm": p_mae, "mae_ci95": [lo, hi],
            "rmse_bpm": p_rmse, "rmse_ci95": [rlo, rhi],
            "pearson_r": r, "r_ci95_fisher": [rlo2, rhi2],
            "coverage": M.coverage(e, ref),
            "failure_rate_gt10bpm": M.failure_rate(e, ref),
            "worst_case_mae_bpm": M.worst_case_mae(e, ref),
            "bland_altman": M.bland_altman(e, ref, subj),
        }
    pt, lo, hi = M.paired_baseline_diff(est, ref, constant_hr, subj)
    out["paired_mae_diff_vs_constant"] = {"diff_bpm": pt, "ci95": [lo, hi]}
    # strata (descriptive)
    for flag in ("motion_flag", "low_light_flag"):
        for v in (0, 1):
            m = pd.to_numeric(df[flag], errors="coerce").to_numpy() == v
            if m.sum() > 0:
                out[f"stratum_{flag}_{v}"] = {
                    "n_windows": int(m.sum()),
                    "mae_bpm": M.mae(est[m], ref[m]),
                    "coverage": M.coverage(est[m], ref[m]),
                }
    # abstention reasons
    out["abstention_reasons"] = df.loc[df["excluded"] == 1, "exclusion_reason"].value_counts().to_dict()
    return out, df


def figures(df, summ, split_name):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    figdir = RESULTS / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    est = pd.to_numeric(df["hr_est_bpm"], errors="coerce").to_numpy(float)
    ref = pd.to_numeric(df["hr_ref_bpm"], errors="coerce").to_numpy(float)
    ok = np.isfinite(est) & np.isfinite(ref)
    e, r = est[ok], ref[ok]
    # colour-blind-safe (Okabe-Ito)
    blue, orange, grey = "#0072B2", "#E69F00", "#666666"
    ba = summ["pos"]["bland_altman"]

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter((e + r) / 2, e - r, s=14, alpha=0.6, color=blue, edgecolors="none")
    ax.axhline(ba["bias_bpm"], color=orange, lw=1.5,
               label=f"bias {ba['bias_bpm']:.2f} BPM")
    for k in ("loa_low_bpm", "loa_high_bpm"):
        ax.axhline(ba[k], color=grey, ls="--", lw=1,
                   label=f"{'−' if 'low' in k else '+'}1.96 SD: {ba[k]:.2f} BPM")
    ax.set_xlabel("Mean of estimate and oximeter HR (BPM)")
    ax.set_ylabel("Estimate − oximeter HR (BPM)")
    ax.set_title(f"Bland–Altman, subject-level LoA — UBFC {split_name} (n={ok.sum()} windows)")
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(figdir / f"bland_altman_{split_name}.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.4, 5))
    ax.scatter(r, e, s=14, alpha=0.6, color=blue, edgecolors="none")
    lim = [min(r.min(), e.min()) - 3, max(r.max(), e.max()) + 3]
    ax.plot(lim, lim, color=grey, ls="--", lw=1, label="identity")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("Oximeter HR (BPM)")
    ax.set_ylabel("rPPG estimate (BPM)")
    ax.set_title(f"Estimate vs reference — UBFC {split_name}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(figdir / f"scatter_{split_name}.png", dpi=150)
    plt.close(fig)

    # error vs |delta HR| between adjacent windows (HR transient failure case)
    df2 = df.copy()
    df2["ref"] = ref
    d = df2.groupby("subject_id")["ref"].diff().abs().to_numpy()
    err = np.abs(est - ref)
    m = ok & np.isfinite(d)
    fig, ax = plt.subplots(figsize=(6, 4.4))
    ax.scatter(d[m], err[m], s=14, alpha=0.6, color=blue, edgecolors="none")
    ax.set_xlabel("|ΔHR| to previous window (BPM, oximeter)")
    ax.set_ylabel("Absolute error (BPM)")
    ax.set_title(f"Error vs HR transient — UBFC {split_name}")
    fig.tight_layout()
    fig.savefig(figdir / f"transient_{split_name}.png", dpi=150)
    plt.close(fig)


def write_report(summ, df, split_name, params_path):
    lines = [f"# UBFC REALISTIC evaluation — {split_name} split", ""]
    lines.append(f"- Windows: {summ['n_windows']} across {summ['n_subjects']} subjects; seed 20261204; params: `{params_path}`")
    lines.append(f"- Constant baseline: {summ['constant_baseline_bpm']:.1f} BPM (development mean)")
    lines.append("")
    lines.append("| Method | MAE (BPM) [95% CI] | RMSE (BPM) [95% CI] | r [Fisher 95% CI] | Coverage | Failure >10 BPM |")
    lines.append("|---|---|---|---|---|---|")
    for name, label in (("pos", "POS (pipeline)"), ("green", "Green channel"), ("constant", "Constant guess")):
        s = summ[name]
        lines.append(
            f"| {label} | {s['mae_bpm']:.2f} [{s['mae_ci95'][0]:.2f}, {s['mae_ci95'][1]:.2f}] "
            f"| {s['rmse_bpm']:.2f} [{s['rmse_ci95'][0]:.2f}, {s['rmse_ci95'][1]:.2f}] "
            f"| {s['pearson_r']:.3f} [{s['r_ci95_fisher'][0]:.3f}, {s['r_ci95_fisher'][1]:.3f}] "
            f"| {s['coverage']*100:.1f}% | {s['failure_rate_gt10bpm']*100:.1f}% |")
    ba = summ["pos"]["bland_altman"]
    lines += ["",
              f"Bland–Altman (subject-level): bias {ba['bias_bpm']:.2f} BPM, "
              f"LoA [{ba['loa_low_bpm']:.2f}, {ba['loa_high_bpm']:.2f}] BPM "
              f"({ba['n_subjects']} subjects).",
              f"Worst-case MAE (abstentions imputed 10 BPM): {summ['pos']['worst_case_mae_bpm']:.2f} BPM.",
              f"Paired MAE difference vs constant: {summ['paired_mae_diff_vs_constant']['diff_bpm']:.2f} BPM "
              f"[{summ['paired_mae_diff_vs_constant']['ci95'][0]:.2f}, {summ['paired_mae_diff_vs_constant']['ci95'][1]:.2f}] (negative = pipeline better).",
              "", "Figures (data table = results/windows CSV):",
              f"- ![Bland–Altman](figures/bland_altman_{split_name}.png)",
              f"- ![Scatter](figures/scatter_{split_name}.png)",
              f"- ![Transient](figures/transient_{split_name}.png)", ""]
    for k, v in summ.items():
        if k.startswith("stratum_"):
            lines.append(f"- {k}: n={v['n_windows']}, MAE {v['mae_bpm']:.2f} BPM, coverage {v['coverage']*100:.1f}%")
    lines += ["", "Abstentions:", json.dumps(summ["abstention_reasons"], indent=1)]
    (RESULTS / f"report_ubfc_{split_name}.md").write_text("\n".join(lines) + "\n")


def main():
    which = sys.argv[1]
    assert which in ("dev", "test")
    params_path = ROOT / "params_frozen.json"
    params = json.loads(params_path.read_text())
    split = load_split()
    rows = run_split(TRACES, split[which], params)
    RESULTS.mkdir(exist_ok=True)
    import pandas as pd
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / f"windows_{which}.csv", index=False)
    # constant baseline = development mean reference HR (fixed once from dev)
    const_file = RESULTS / "constant_baseline.json"
    if which == "dev":
        ref = pd.to_numeric(df["hr_ref_bpm"], errors="coerce")
        const = float(ref.mean())
        const_file.write_text(json.dumps({"constant_bpm": const, "source": "dev mean reference HR"}))
    else:
        const = json.loads(const_file.read_text())["constant_bpm"]
    summ, df = summarise(rows, which, const, params)
    summ["params_sha256"] = hashlib.sha256(params_path.read_bytes()).hexdigest()
    summ["split_manifest_sha256"] = hashlib.sha256((ROOT / "split_manifest.json").read_bytes()).hexdigest()
    (RESULTS / f"metrics_{which}.json").write_text(json.dumps(summ, indent=1))
    figures(df, summ, which)
    write_report(summ, df, which, "params_frozen.json")
    print(json.dumps({k: summ[k] for k in ("n_windows", "n_subjects")}, indent=1))
    print("POS MAE", summ["pos"]["mae_bpm"], "CI", summ["pos"]["mae_ci95"])


if __name__ == "__main__":
    main()
