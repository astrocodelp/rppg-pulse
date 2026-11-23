# rppg-pulse — camera-based pulse estimation, honestly evaluated

**Wellness demo — not a medical device.** CPU-only remote photoplethysmography
(rPPG): estimate pulse from tiny colour changes in a face video. Built for the
[AI for Medicine hackathon](https://ai-for-medicine.devpost.com/) with a
pre-registered evaluation protocol, a subject-disjoint held-out split, error
bars in BPM, and a limitations section that is not decoration.

**We did not hit our pre-registered accuracy target on the held-out split.**
The frozen protocol asked: MAE ≤ 5 BPM vs a simultaneous pulse-oximeter
reference on held-out subjects. On the 21 held-out UBFC REALISTIC subjects we
got **MAE 10.96 BPM (95% CI 4.68–19.65)**. Dev-split MAE was 4.50 BPM. We
report both, unchanged, and analyse why below. Nothing in the evaluation was
modified after seeing test results.

---

## What's in here

| Path | What it is |
|---|---|
| `rppg/` | CPU-only pipeline: MediaPipe face ROI → spatial-mean RGB → POS projection → band-pass 0.7–3.0 Hz → spectral-peak HR |
| `app/demo.py` | Gradio demo: live webcam pulse + video upload, persistent "not a medical device" disclaimer |
| `assets/sample_face_72bpm.mp4` | Fully synthetic face with a known 72 BPM pulse — try the demo without a webcam and without any real person |
| `protocol/` | Healthy's frozen analysis plan (`evaluation.md`), benchmark plan, split rules, verified references, amendment log |
| `split_manifest.json` | Subject-disjoint 21 dev / 21 test split, seed 20261204, fixed before processing |
| `params_frozen.json` | All pipeline parameters frozen **before** the test run (dev-only tuning rule included) |
| `scripts/fetch_dataset.py` | Downloads UBFC REALISTIC and caches per-frame ROI traces (dataset files are never committed) |
| `scripts/tune_dev.py` | Dev-only quality-gate selection; writes `params_frozen.json` |
| `scripts/evaluate.py` | Frozen held-out evaluation: MAE/RMSE, Bland–Altman, coverage, failure rate, cluster bootstrap |
| `scripts/posthoc_sensitivity.py` | Post-hoc, clearly labelled sensitivity analysis of ground-truth artefacts |
| `results/` | Per-window CSVs, metrics JSON, Markdown reports, figures (seed alongside every figure) |
| `tests/test_metrics.py` | Unit tests of every metric on synthetic known-answer data |
| `demo_video/rppg_pulse_demo.mp4` | ≥60 s screen recording of the app working end to end |
| `verify/` | Playwright browser-verification results + screenshots (desktop and 320 px phone) |

## Run the demo

Python 3.11+ (developed on 3.14), a webcam or just the bundled synthetic video. No GPU.

```bash
git clone https://github.com/astrocodelp/rppg-pulse.git
cd rppg-pulse
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 app/demo.py        # open http://localhost:7860
```

* **Live webcam tab:** allow camera access, keep your face centred and still;
  a rolling 15 s pulse estimate appears, or a visible "no estimate" with the reason.
* **Upload tab:** drop any 5–60 s face video (mp4/webm/avi), or click the
  bundled synthetic example (known truth: 72 BPM). Same frozen pipeline.
* Nothing is uploaded or stored: frames are processed in memory in your own
  Python process. Do not use it to make any health decision.

## Reproduce the evaluation

```bash
python3 scripts/fetch_dataset.py pipeline   # downloads UBFC (~3 GB) + caches ROI traces
python3 scripts/tune_dev.py                 # dev-only tuning -> params_frozen.json
python3 scripts/evaluate.py dev             # dev report
python3 scripts/evaluate.py test            # frozen held-out report (the headline numbers)
python3 scripts/posthoc_sensitivity.py      # labelled post-hoc sensitivity only
python3 -m pytest tests/ -q                 # metric unit tests
```

Dataset: **UBFC-rPPG Dataset 2 (REALISTIC)** — 42 subjects playing a
time-sensitive maths game, Logitech C920 at 30 fps 640×480, CMS50E fingertip
pulse oximeter ground truth (PPG waveform + device HR). Official page:
<https://sites.google.com/view/ybenezeth/ubfcrppg>. No credentialing needed.
**Dataset videos and ground-truth files are not committed to this repo** —
only the loader, subject-ID manifest, and numeric results. The official page
says "shared for research purpose" but publishes **no standard license text**;
we flag that gap and do not redistribute the data.

## Evaluation

**Metric and measurement method.** Mean absolute error (MAE) and RMSE in BPM
between the pipeline's 15-second-window pulse estimate and the mean CMS50E
device HR over the same window. Non-overlapping windows; Pearson r with
Fisher-z CI; subject-level Bland–Altman bias and limits of agreement (Bland &
Altman 1986); coverage (fraction of windows answered — an abstaining pipeline
must not look accurate by answering only easy windows); failure rate
(|error| > 10 BPM). Uncertainty: cluster bootstrap resampling **subjects**,
10,000 replicates, percentile 95% CI, **seed 20261204** saved alongside every
figure. Baselines: a constant guess (dev mean HR) and the naive green-channel
method, evaluated identically. Split: 21 dev / 21 test subjects, seed 20261204,
fixed before any processing. All parameters frozen in `params_frozen.json`
before the test run (dev-only selection rule documented in `scripts/tune_dev.py`
and `protocol/amendment_log.md`).

### Results (frozen protocol, nothing changed after seeing them)

| Split | Method | MAE (BPM) [95% CI] | RMSE (BPM) [95% CI] | r [95% CI] | Coverage | Failure >10 BPM |
|---|---|---|---|---|---|---|
| **Test (held-out, 21 subj, 82 win)** | **POS pipeline** | **10.96 [4.68, 19.65]** | **26.28 [10.26, 40.22]** | 0.288 [0.071, 0.478] | 96.3% | 16.5% |
| Test | Green channel | 12.82 [4.56, 23.81] | 26.98 [7.84, 42.32] | 0.383 [0.089, 0.615] | 51.2% | 23.8% |
| Test | Constant guess (96.8 BPM) | 17.02 [12.45, 22.15] | 22.46 [15.28, 30.12] | — | 100% | 67.1% |
| Dev (21 subj, 80 win) | POS pipeline | 4.50 [2.54, 7.16] | 8.39 [3.87, 11.99] | 0.858 [0.785, 0.908] | 96.2% | 9.1% |
| Dev | Green channel | 4.30 [2.34, 7.28] | 7.57 [3.26, 12.10] | 0.902 [0.803, 0.953] | 37.5% | 6.7% |
| Dev | Constant guess | 12.67 [9.50, 16.29] | 15.39 [11.66, 19.15] | — | 100% | 56.2% |

* **Bland–Altman (test, subject-level):** bias **+8.29 BPM**, limits of
  agreement **[−28.11, +44.69] BPM** (21 subjects). Dev: bias +1.57,
  LoA [−14.81, +17.94] BPM.
* **Worst-case MAE** (abstentions scored as 10 BPM failures): test 10.93 BPM, dev 4.71 BPM.
* **vs constant baseline (paired, per subject):** test −6.18 BPM [−11.44, −0.69];
  dev −8.26 BPM [−12.26, −4.35]. The pipeline beats a constant guess, but the
  test CI is wide and its lower bound is close to zero.
* **Pre-registered target MAE ≤ 5 BPM: met on dev, NOT met on held-out test.**
* Motion stratum (test): MAE 5.55 BPM without the motion flag vs **18.91 BPM**
  with it — motion is our dominant failure mode, exactly as pre-registered.
* Figures with axes in BPM and the seed on every plot: `results/figures/`;
  the underlying per-window data table is `results/windows_test.csv` / `windows_dev.csv`.

### Why test is so much worse than dev — honest failure analysis

1. **Ground-truth dropouts.** The CMS50E emitted physiologically impossible
   readings mid-game for subject20 (window means 19.7 and 4.6 BPM). Our frozen
   reference-blind rule only excluded flat non-positive device HR, so these
   scored as ~114–130 BPM "errors". A **post-hoc, clearly labelled** sensitivity
   analysis (`scripts/posthoc_sensitivity.py`, rule: device HR < 30 BPM =
   likely dropout, applied identically to dev and test) removes 2 test windows
   and gives test MAE **8.08 BPM [4.36, 12.65]**. That is still above target;
   we publish both numbers and the rule, and changed nothing frozen.
2. **Motion + HR transients.** The maths game makes subjects move and their
   heart rate drift within a 15 s window; the spectral peak can lock onto a
   motion harmonic near 128–134 BPM. Largest genuine errors: subject11/18/24
   windows during rapid HR change (e.g. ref 54.5 → est 129.2 BPM).
3. **Small-sample luck of the split.** 21 test subjects is a small sample;
   three bad subjects dominate the cluster bootstrap CI. That is precisely why
   we report the interval instead of hiding behind a point estimate.

### What our numbers are not

They are agreement with a consumer pulse oximeter under **our** frozen
preprocessing, not an "official UBFC accuracy". Published POS MAEs on UBFC
range 2.4–7.6 BPM under other groups' preprocessing (see
`protocol/references.md`); comparing across papers without matching protocols
is meaningless. Our pipeline is deliberately simple (spatial-mean RGB, no
skin segmentation, no learned components) and CPU-only.

## Limitations

- **This is a wellness demonstration, not a medical device.** It has not been cleared or approved by any regulator, has not been validated in a clinical study, and must not be used to diagnose, screen, monitor or manage any medical condition, or to decide anything about a person's care. It is not an oximeter: it measures neither blood oxygen nor blood pressure, and it cannot detect arrhythmias.
- **It measures agreement with a fingertip pulse oximeter, not true heart rate.** Both our reference (a consumer pulse oximeter) and our camera estimate are noisy; agreement between two imperfect methods does not establish clinical accuracy (Bland & Altman, Lancet 1986).
- **The benchmark (UBFC-rPPG REALISTIC, 42 subjects) is limited:** healthy adults in one lab, one webcam model, no published skin-tone labels, and a ground truth that is itself a smoothed on-device oximeter estimate. Benchmark ground-truth artefacts are a documented problem in this literature (Gudi et al., Applied Sciences 2020) — and we hit exactly that (see failure analysis above).
- **Known failure modes, pre-registered before we measured anything:** head and jaw motion (the benchmark's maths game induces it), low or flickering light, heavy video compression, webcam frame rates below ~15 fps, and rapid heart-rate changes that straddle a 15-second window. The app abstains ("no estimate") when its quality gate fails; the abstention rate is reported alongside every accuracy number.
- **Skin-tone bias is a documented risk we could not test.** The rPPG literature reports systematic differences in camera-PPG error across skin tone and gender (Nowara et al., CVPRW 2020; Dasari et al., npj Digital Medicine 2021). UBFC publishes no skin-tone labels, so **we make no fairness claim**.
- **Held-out accuracy did not meet our own pre-registered bar.** Test MAE 10.96 BPM [4.68, 19.65] vs the ≤5 BPM target. Treat the live demo as a toy that can be wrong by tens of BPM.
- **No performance claim is made for:** children, people with cardiovascular disease or arrhythmias, people wearing heavy makeup over the ROI, very low ambient light, or anyone not represented in our evaluation.

## Who benefits, and who could be harmed

**Who benefits.**
- Curious healthy adults who want a contactless, toy-grade pulse check and a transparent look at how camera-based physiology works.
- Students and researchers: the full protocol, frozen parameters, subject-disjoint split (seed 20261204), scripts and per-window results are public, so every number in this README can be recomputed.
- The rPPG research community, through honest reporting: error bars in BPM, abstention rates, baselines, and failure strata instead of a single cherry-picked accuracy.

**Who could be harmed, and how we mitigate it.**
- **Someone who mistakes this for a medical reading.** A false-reassuring or false-alarming number could delay care or cause anxiety. Mitigation: the app displays "wellness demo — not a medical device" persistently, never renders diagnostic language, and abstains rather than guesses when signal quality is poor. Nothing in the app gives health advice.
- **People with darker skin tones.** Camera PPG relies on light absorbed by blood; less reflected signal can mean larger errors or more abstentions, and the literature documents this bias. Mitigation: we state the risk plainly, make no fairness claim, and abstain visibly rather than output a confident wrong number.
- **Privacy of anyone on camera.** Face video is biometric-adjacent personal data. Mitigation: all processing is local on your device; no frames are uploaded or stored by the demo; benchmark videos (UBFC research volunteers) are never re-uploaded or committed to the repository; only code, subject-ID manifests and numeric results are public. The bundled sample video is a fully synthetic face — no real person.
- **Over-trust in AI health demos generally.** Mitigation: the Evaluation section shows the baselines, the confidence intervals, and the cases where we fail — so a stranger can see exactly what the method is and is not worth.

## What we would do with another month

1. **Motion-robust ROI:** skin-tissue segmentation (Bobbia et al. 2019) instead of polygon means, plus landmark-stabilised ROI tracking to stop motion harmonics entering the pulse band.
2. **A learned component:** train POS-plus-ICA or a small temporal model on dev subjects only, freeze, and re-run the same held-out protocol — the split and metrics stay untouched, so the comparison is honest.
3. **Clean ground truth:** an ECG chest-strap reference and beat-to-beat alignment (Gudi et al. 2020), eliminating the oximeter-dropout artefacts that inflated our test error.
4. **Fairness evaluation with consented volunteers across the Fitzpatrick range**, pre-registered strata and enough subjects per stratum to say something real — the single most important gap in this entry.
5. **HR-transient handling:** shorter overlapping windows with explicit uncertainty, or time-frequency tracking instead of one spectral peak per 15 s.
6. **A phone-camera study:** real webcams and phones drop frames and compress heavily; our browser path needs its own protocol and numbers.

## Attribution

**Dataset.** UBFC-rPPG (Bobbia, Macwan, Benezeth, Mansouri & Dubois, *Pattern
Recognition Letters* 124, 2019, DOI 10.1016/j.patrec.2017.10.017), Dataset 2
REALISTIC, official page <https://sites.google.com/view/ybenezeth/ubfcrppg>.
Downloaded for this evaluation via a Hugging Face community mirror
(`PulseRate/UBFC-rPPG`); files verified against the official folder layout
(`subject<N>/vid.avi` + `ground_truth.txt`). The dataset is shared "for
research purpose"; **no standard license text is published** — we do not
redistribute it, and demo use should be confirmed with the dataset authors.

**Algorithms.** POS: Wang, den Brinker, Stuijk & de Haan, *IEEE TBME* 64(7),
2017, DOI 10.1109/TBME.2016.2609282. CHROM (comparator): de Haan & Jeanne,
*IEEE TBME* 60(10), 2013, DOI 10.1109/TBME.2013.2266196. Green-channel
baseline: standard practice, cited via Verkruysse et al. as referenced in Wang
2017. Bland–Altman agreement method: *Lancet* 1986,
DOI 10.1016/S0140-6736(86)90837-8. Full verified reference list with
record-by-record verification notes: `protocol/references.md`.

**Models & libraries.** MediaPipe Face Landmarker (Google, Apache-2.0),
model `face_landmarker.task` pinned in `models/` with SHA-256; NumPy, SciPy,
OpenCV, Gradio, matplotlib, pandas, imageio-ffmpeg — exact versions in
`requirements.txt`. No pre-trained HR model is used: estimation is classical
signal processing. Layout conventions cross-checked against rPPG-Toolbox
(ubicomplab, NeurIPS 2023) documentation; no toolbox code copied.

**AI-tools disclosure.** Built with assistance from AI tools: StellarFirm assistants drafted the analysis plan, evaluation protocol and reference verification (Healthy, Scientist), and implemented the pipeline, demo, evaluation scripts and this README (Coder health, Coder). All measurements were produced by the pinned scripts in this repository; no result was generated by an LLM.

## Verification (what we actually checked)

* `python3 -m pytest tests/ -q` — metric unit tests on synthetic known-answer data, all pass.
* Playwright/Chromium browser verification (`scripts/verify_browser.py`):
  13/13 checks pass — title, disclaimer visible, tabs reachable by keyboard
  with a visible 3 px focus ring, disclaimer contrast 10.3:1 (≥4.5:1), upload
  flow end to end (synthetic 72 BPM video → app reads 72 BPM), no JS errors,
  and **320 px phone-sized layout with no horizontal overflow**. Screenshots
  in `verify/`.
* Demo video: `demo_video/rppg_pulse_demo.mp4` (≥60 s, screen recording of the
  app working end to end, no installation needed to watch).

## License

Code: MIT (see `LICENSE`). Dataset: not included, see Attribution. The
MediaPipe model is Apache-2.0 (Google).
