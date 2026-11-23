# Evaluation Protocol — Webcam Heart Rate (rPPG)

**Project:** Remote heart-rate estimation from a webcam using photoplethysmography (rPPG)
**Event:** AI for Medicine: A Global Student Hackathon (submission deadline 4 Dec 2026)
**Status:** This plan was written and frozen **before** any participant data was collected and before any parameter tuning. Changes after data collection starts must be logged in §9 (amendment log) with a reason.
**Scope:** Research prototype and hackathon demonstration. **Not a medical device. No diagnostic, monitoring, or treatment use.**

---

## 1. Testable question

> On held-out participants recorded with an ordinary RGB webcam in ordinary indoor lighting, can our rPPG pipeline estimate average heart rate (BPM) with mean absolute error ≤ 5 BPM against a simultaneous pulse-oximeter reference, and does it do so without large errors on darker skin tones?

What counts as an answer: the held-out MAE with a 95% confidence interval, reported for all participants and stratified by skin-tone group and motion condition, plus the failure/abstention rate. We report the result whatever it is — including "no better than a constant predictor".

**Pipeline under test (fixed before evaluation, implemented by Coder health):** face ROI detection → spatial averaging of RGB traces → POS (plane-orthogonal-to-skin) projection (Wang et al. 2017) → band-pass 0.7–3.0 Hz (42–180 BPM) → spectral peak HR per window. Any change to this pipeline after tuning is frozen counts as a new method and needs a new held-out run.

---

## 2. Evaluation design

### 2.1 Data splits

| Split | Subjects | Use |
|---|---|---|
| Development | ≥ 6 volunteers | Build pipeline; tune window length, filter bands, ROI choice, signal-quality thresholds |
| Held-out test | **≥ 10 subjects, recruited after tuning is frozen** | Single evaluation run. Never used for tuning, debugging thresholds, or method selection |

Rules:
- No subject appears in both splits. Split assignment recorded by anonymous subject ID before the test session.
- All tunable parameters and the quality/abstention thresholds are written into `params_frozen.json` (hash committed to the repo) **before** the first held-out recording.
- The held-out set is processed exactly once with the frozen pipeline. If a bug is found and fixed, we re-run and disclose the re-run in §9 — we do not iterate until the number looks good.

### 2.2 Recording protocol (one session ≈ 12 min per subject)

- Consumer RGB webcam, ≥ 30 fps nominal (actual per-frame timestamps logged; dropped frames logged).
- Subject seated ~0.5–1 m from camera, face fully visible, no heavy makeup over cheeks/forehead.
- Reference: consumer fingertip pulse oximeter displaying pulse rate (e.g. any standard fingertip SpO₂/pulse device). The displayed pulse rate is transcribed at fixed 30 s marks by a second person, and/or the oximeter's serial/Bluetooth pulse stream is logged if available. Reference values are time-stamped in the same clock as the video.
- Conditions (each 2 min, order fixed):
  1. **Rest** — still, ambient indoor light (target ≥ 100 lux at face; a phone lux-meter app reading is logged).
  2. **Talking** — subject reads a text aloud (jaw/cheek motion).
  3. **Small head motion** — subject slowly turns head ±20° following a metronome.
- Illuminance at the face is logged at the start of each condition; sessions below the logged floor are kept but flagged `low_light`.

### 2.3 Windowing and pairing

- HR is estimated on **non-overlapping 15 s windows** (2 windows per 30 s reference interval → 8 windows per condition, 24 per subject).
- Reference HR for a window = mean of the oximeter readings whose timestamps fall in the window (at 30 s transcription cadence: nearest reading, held constant; if a serial pulse stream exists, average over the window).
- A window is **excluded from scoring** only by pre-registered, reference-blind rules: face not detected ≥ 20% of frames; effective frame rate < 15 fps; signal-quality index below the frozen threshold (the pipeline then outputs "no estimate", which counts toward the coverage metric, not toward MAE).
- **Coverage** = fraction of windows with an estimate, reported next to every accuracy metric. An abstaining pipeline must not look accurate by only answering easy windows.

### 2.4 Inclusion / exclusion criteria (participants)

Include:
- Age ≥ 18, able to give informed consent in their own language.
- Willing to sit for one ~12 min session with a fingertip oximeter.
- Any skin tone — we actively recruit across the Fitzpatrick range, aiming for ≥ 2 participants in types V–VI (self-reported category plus a photograph-free ordinal scale; see §6).

Exclude:
- Known cardiac arrhythmia or peripheral circulation disorder that makes fingertip pulse oximetry unreliable (e.g. Raynaud's, cold hands with no readable signal).
- Nail polish / artificial nails on the oximeter finger that prevent a reading (may switch fingers; otherwise exclude).
- Inability to keep the face in frame for the protocol (record but mark session invalid a priori).
- Anyone under 18 (no guardian-consent process exists for this hackathon).

No health data beyond pulse rate is collected. No diagnosis is made or implied from any reading.

### 2.5 Consent and data handling

- **Written informed consent before recording**, covering: purpose (student hackathon research/demo), what is recorded (face video + pulse-rate numbers), that participation is voluntary and withdrawable at any time without reason, who sees the data (the two-person hackathon team), where it is stored, and how long it is kept.
- Consent form includes a **separate, optional checkbox** for using a short clip in the public demo video. No clip goes public without that box ticked.
- Faces are biometric-adjacent personal data. Handling:
  - Raw videos stored only on encrypted local disk of the collecting team member; never uploaded to the public repo, cloud drives, or chat tools.
  - Subject IDs are random codes (e.g. `S07`); the ID↔identity list stays offline with the consent forms.
  - What may enter the repo: derived numeric traces, per-window HR pairs, aggregate results, and — only with the demo checkbox — a consented clip. Everything else is de-identified numbers.
  - For any figure showing a face: only consented clips; otherwise blurred/cropped faces or synthetic illustration.
  - **Retention:** raw video deleted within 30 days after the hackathon results (12 Dec 2026), unless the participant opts in to longer retention in writing. Derived de-identified numbers may be kept for the report.
  - Withdrawal: participant can request deletion at any time; we delete raw video and their rows from all result files and recompute aggregates.
- This is volunteer research for a student hackathon, not a clinical study; it is not submitted to an ethics board, and we say so plainly in the submission rather than implying approval we do not have.

---

## 3. Metrics (exact definitions, implementable as-is)

Let window pairs be $(\hat{h}_i, h_i)$, estimated vs reference HR in BPM, $i = 1..N$, from $K$ subjects.

| Metric | Definition | Notes |
|---|---|---|
| **Primary: MAE** | $\frac{1}{N}\sum_i \lvert \hat{h}_i - h_i \rvert$ (BPM) | Computed over all included windows, all conditions pooled; also per condition |
| RMSE | $\sqrt{\frac{1}{N}\sum_i (\hat{h}_i - h_i)^2}$ (BPM) | Secondary |
| Pearson r | correlation of $\hat{h}_i$ with $h_i$ | Secondary; also report with 95% CI (Fisher z) |
| Bland–Altman | bias $\bar{d} = \frac{1}{N}\sum_i(\hat{h}_i - h_i)$; limits of agreement $\bar{d} \pm 1.96\, s_d$ | Secondary; plot differences vs means; because windows cluster within subjects, compute subject-level bias first and use the subject-level SD for LoA, and show the window-level plot alongside |
| Coverage | fraction of windows with an estimate | Always reported beside accuracy |
| Failure rate | fraction of windows with $\lvert \hat{h}_i - h_i \rvert > 10$ BPM | Named failure threshold, chosen a priori |

Additional required baselines (computed on the same held-out windows):
1. **Constant predictor:** always output the development-set mean HR. If our MAE is not clearly below this baseline's, the honest conclusion is "no demonstrated skill".
2. **Trivial green-channel baseline:** mean of green ROI trace → same band-pass → spectral peak. Shows what the POS step buys.

Confidence intervals: **cluster bootstrap over subjects** (resample subjects with replacement, 10,000 replicates, percentile 95% CI; fixed seed 20261204). Windows within a subject are correlated; a naive window-level CI would be too narrow. For per-subject summaries with $K = 10$, t-intervals use df = 9 ($t_{0.975,9} = 2.262$; checked with SciPy).

---

## 4. Statistical analysis plan (frozen before data collection)

1. **Primary estimand:** population-average window MAE on held-out subjects under the §2 protocol, all three conditions pooled. Report point estimate + cluster-bootstrap 95% CI, with $N$ windows, $K$ subjects, and coverage.
2. **Sample size rationale:** this is a hackathon, not a powered trial — we state the precision we get, not a hypothesis-test power claim. A Monte Carlo check (NumPy 2.5.5 / SciPy 1.18.1, seed 20261204, script `sim_ci_width.py`, run before collection) assuming true MAE ≈ 2.5 BPM, within-subject error SD ≈ 1.5 BPM and 20 windows/subject gives median 95% CI widths of ≈ **1.3 BPM at 10 subjects, 1.2 BPM at 15, 1.0 BPM at 20** (checked by computation, model-dependent). Ten subjects is the minimum that makes the CI narrower than the 5 BPM decision threshold; we recruit more if volunteers allow.
3. **Stratified reports (descriptive, not powered tests):** MAE by condition (rest / talking / motion) and by skin-tone group (Fitzpatrick I–III vs IV–VI, groups fixed a priori because per-type cells would be tiny). Each stratum reported with its own bootstrap CI and n; with ~2–4 subjects in the dark-skin group these CIs will be wide and we will say so rather than claim parity.
4. **Outliers / exclusions:** no data point is removed for being inconvenient. The only exclusions are the reference-blind quality rules of §2.3, fixed before collection. Every excluded window is counted and its reason logged (`exclusions.csv`). Sensitivity analysis: recompute MAE with quality-excluded windows scored as failures (imputed error = 10 BPM) — reported as a worst-case bound beside the main number.
5. **Missing reference readings:** a window with no oximeter reading in range is unscored and counted in `exclusions.csv`; if > 15% of windows lose their reference, the session is flagged and reported separately.
6. **No p-values against zero skill by default.** The comparison that matters is MAE vs the constant baseline: report the paired difference (per subject) with a bootstrap CI. If the CI includes 0, we write "not distinguishable from a constant predictor on this sample".
7. **Multiplicity:** one primary metric, one primary comparison. Everything else is labelled secondary/descriptive; no fishing across window lengths or filter bands on the held-out set.
8. **Reporting format:** every number in BPM with its unit; every figure axis labelled with quantity and unit, uncertainty shown (CI bars or bootstrap bands), colour-blind-safe palette, data table published next to each plot.

---

## 5. Reference framing (literature)

All references below were looked up and their titles, authors, venues and identifiers checked against the records named. Claims are labelled: **[verified record]** = checked against the cited record; **[recalled, not checked]** = from memory, flagged.

1. **Wang, W., den Brinker, A. C., Stuijk, S., & de Haan, G. (2017). "Algorithmic Principles of Remote PPG." IEEE Transactions on Biomedical Engineering, 64(7), 1479–1491.** DOI: [10.1109/TBME.2016.2609282](https://doi.org/10.1109/TBME.2016.2609282). (Online 2016, journal issue July 2017 — both dates appear in records.) The paper models skin-reflection optics and physiology, explains prior rPPG methods within that model, and derives **POS**, a pulse extraction using a projection plane orthogonal to the skin tone — the algorithm our pipeline uses. [verified record: IEEE Xplore document 7565547, https://ieeexplore.ieee.org/document/7565547; OpenAlex W2520509592; TU/e research portal citation.]

2. **PURE dataset — Stricker, R., Müller, S., & Groß, H.-M. (2014). "Non-contact video-based pulse rate measurement on a mobile service robot." IEEE RO-MAN 2014.** DOI: [10.1109/ROMAN.2014.6926392](https://doi.org/10.1109/ROMAN.2014.6926392). [verified record: OpenAlex W2016778993.] Composition: **10 subjects (8 male, 2 female), 60 one-minute face videos in six motion setups** (steady, talking, slow/fast translation, small/medium rotation), fingertip pulse-oximeter reference. [verified via secondary sources quoting the paper: https://chatppg.com/research/datasets/pure and PMC12011667; composition not re-checked against the paper PDF itself.] **We do not use PURE**: access requires a request to TU Ilmenau and its 640×480 controlled recordings do not match our webcam demo conditions. It remains the standard external benchmark for a follow-up.

3. **VIPL-HR — Niu, X., Han, H., Shan, S., & Chen, X. (2019). "VIPL-HR: A Multi-modal Database for Pulse Estimation from Less-Constrained Face Video." CVM 2019, LNCS.** DOI: [10.1007/978-3-030-20873-8_36](https://doi.org/10.1007/978-3-030-20873-8_36); arXiv: [1810.04927](https://arxiv.org/abs/1810.04927). **2,378 visible-light and 752 near-infrared videos of 107 subjects**, with head movement and illumination variation. [verified record: arXiv abstract 1810.04927; OpenAlex W2896102525.] **We do not use VIPL-HR**: it requires a signed release agreement and is heavier than a hackathon cycle; also its reference is a contact PPG, and cross-dataset generalization of trained models is known to be poor (Vance et al., arXiv:2305.15199 [verified abstract]). We collect our own small consented dataset (§2) instead, and say so.

4. **Expected accuracy range from the literature.**
   - In **uncontrolled real-world webcam conditions** (10-minute recordings, 26 participants, ECG reference, natural/uncontrolled light), classical methods scored: GREEN **MAE 7.57 ± 0.66 BPM**, ICA 7.61 ± 0.42, CHROM 10.05 ± 0.46, POS 7.59 ± 0.46; RMSE 12–17 BPM; Pearson r 0.24–0.50. — Rodrigues & Garcia (2025), "Evaluating remote photoplethysmography: A 10-minute video dataset in uncontrolled lighting," *Data in Brief*, DOI: [10.1016/j.dib.2025.111888](https://doi.org/10.1016/j.dib.2025.111888), PMC12311941, Table 1. [verified record: full-text passage via research index.]
   - Across demographic groups in India and Sierra Leone with an FDA-cleared contact reference, rPPG mean difference vs ground truth ≈ **1 BPM (~2%)** but pulse-rate variability of ≈ **11 BPM (~15%)** — i.e. small average bias does not mean small per-window error. — Dasari, Arul Prakash, Jeni & Tucker (2021), *npj Digital Medicine*, DOI: [10.1038/s41746-021-00462-z](https://doi.org/10.1038/s41746-021-00462-z), PMID 34083724. [verified record: abstract.]
   - Gudi, Bittner & van Gemert (2020), "Real-Time Webcam Heart-Rate and Variability Estimation with Clean Ground Truth for Evaluation," *Applied Sciences* 10(23):8630, DOI: [10.3390/app10238630](https://doi.org/10.3390/app10238630), arXiv:2012.15846 — shows benchmark ground-truth artefacts inflate/deflate reported errors, and HR estimation error grows sharply as the time window shrinks. [verified record: arXiv abstract + MDPI page https://www.mdpi.com/2076-3417/10/23/8630; their exact MAE table values not extracted — not quoted here.]
   - **Our honest expectation:** with a 15 s window, consumer webcam, seated cooperative subjects and mostly ambient light, a classical POS pipeline should land around **2–5 BPM MAE at rest** and degrade to **5–10+ BPM with motion or low light**; published sub-2 BPM numbers typically come from controlled lighting, longer windows, or cleaned benchmarks. [conjectured from the verified records above; this is our prediction, not a measured result.] Our 5 BPM target (§1) is a decision threshold we chose, not a literature guarantee.

---

## 6. Who benefits, and who could be harmed (required honesty section)

**Who could benefit.** People who cannot or prefer not to wear a contact sensor for *non-clinical* wellness curiosity: quick resting-pulse checks during home exercise, telehealth conversations where a rough pulse trend adds context, contactless demos in education. Longer term (not this project): screening-adjacent triage research where cameras already exist. The direct beneficiary of *this* entry is the research community: an honest, reproducible evaluation of what a weekend-built rPPG pipeline can and cannot do.

**Who could be harmed, and how — named failure modes:**

1. **Skin-tone bias.** rPPG reads tiny colour changes in reflected light; melanin absorbs the signal, so darker skin (Fitzpatrick V–VI) yields lower signal-to-noise. Published rPPG benchmarks under-represent dark skin (Dasari et al. 2021, DOI 10.1038/s41746-021-00462-z [verified abstract]; Ba et al., arXiv:2106.06007 [verified record]). If our tool silently returns confident-looking numbers on dark skin while being wrong, users in that group get worse information dressed as equal quality. Mitigation: recruit across skin tones (§2.4), stratified MAE reporting (§4.3), quality-based abstention instead of a fabricated number. With our sample size we can *detect* a large disparity, not certify fairness.
2. **Motion artefacts.** Talking, head turns and exercise move the ROI and modulate brightness at frequencies near the pulse band; the estimator can lock onto motion harmonics and report a plausible but wrong BPM. Mitigation: motion condition in the protocol, quality gating, "no estimate" output.
3. **Low light and camera processing.** Below usable illuminance the colour signal drowns in sensor noise; auto-exposure, auto-white-balance and video compression (especially on phones) actively erase the pulse signal. Mitigation: lux logging, low-light flag, abstention.
4. **False reassurance / false alarm.** A wrong low reading could reassure someone with tachycardia; a wrong high reading could frighten a healthy person. **This is not a medical device**: it is not validated for diagnosis, monitoring or triage, it must never gate a care decision, and the UI says so on every screen with a number. Anyone with symptoms should use a validated device and a clinician, not a webcam.
5. **Privacy harm.** Face video is identifying and biometric-adjacent; a leaked recording is a durable harm. Mitigation: consent, local encrypted storage, no raw video in the repo, deletion schedule (§2.5).
6. **Reference-device error.** A consumer oximeter is itself imperfect (motion, cold fingers, poor perfusion); some of our "error" is reference error, and our MAE is an upper bound on true error only if the reference is unbiased — which we cannot verify. We name the device used and treat agreement, not truth, as what we measure.
7. **Arrhythmia and non-sinus rhythms.** Spectral-peak HR estimation assumes a reasonably periodic pulse; atrial fibrillation or frequent ectopy breaks that assumption. Such participants are excluded (§2.4) and the limitation is stated in the UI.

**AI disclosure (hackathon rules):** the codebase is written with LLM coding assistants (StellarFirm assistants incl. Claude-based coder); literature search and this protocol were drafted with an AI research assistant and every citation was checked against the cited public record. No LLM is in the measurement path — the HR estimate is classical signal processing, fully deterministic given the frozen parameters.

---

## 7. Limitations

What this project **cannot** do:
- It is **not a medical device** and has no regulatory clearance; no clinical claim is made. Agreement with a consumer oximeter on ~10–20 healthy seated volunteers is not clinical validation.
- It measures **average pulse rate over a window**, not beat-to-beat intervals; no HRV, no arrhythmia detection, no SpO₂, no blood pressure.
- It cannot be trusted during exercise, in moving vehicles, in dim rooms, with heavy occlusion (masks, hands), or at long distance / low face resolution.
- Skin-tone fairness is **explored, not established**: with ~2–4 dark-skin participants the stratified CIs are wide; absence of an observed gap is not evidence of parity.
- Volunteers are young, healthy, mostly known to the team — selection bias toward easy subjects; results do not generalize to elderly, ill, or paediatric populations.
- One camera model and one lighting environment per session; cross-camera generalization untested. Compression and auto-exposure differences between webcams and phones can change results materially.
- The reference itself has error and a slow display cadence; fast HR changes within a 15 s window are blurred in the reference.

What would **break** it: HR outside 42–180 BPM (filter band), frame rate below ~15 fps, strong periodic lighting flicker (50/60 Hz aliasing into the pulse band after auto-exposure), two faces in frame, heavy makeup over the ROI, irregular pulse rhythms.

What **another month** would fix or improve:
1. External validation on PURE and VIPL-HR under their access agreements (removes "our own easy data" criticism).
2. A larger, deliberately diverse cohort (≥ 40 subjects, balanced Fitzpatrick I–VI) powered for a fairness comparison instead of a descriptive one.
3. An ECG or research-grade PPG reference with beat-level timestamps, enabling HRV experiments and honest short-window evaluation.
4. Motion-robust ROI tracking and a learned quality model calibrated to abstain (with coverage–accuracy curves).
5. Cross-camera and compression robustness tests (webcam vs phone, resolution ladder).
6. A preregistration-style public timestamp of this protocol before collection (repo commit hash), and release of de-identified per-window data.

---

## 8. Implementation contract for the pipeline (Coder health)

Files the evaluation expects, one row per window, written by the pipeline:

`windows.csv` columns:
`subject_id, split (dev|test), condition (rest|talk|motion), window_start_s, window_end_s, hr_est_bpm (empty if abstained), hr_ref_bpm (empty if missing), quality_score, face_detect_frac, eff_fps, lux, excluded (0|1), exclusion_reason`

- `params_frozen.json`: window length 15 s, band-pass 0.7–3.0 Hz, POS projection, ROI definition, quality threshold, seed 20261204 — committed **before** the first test recording.
- `metrics.py`: implements §3 exactly (MAE, RMSE, Pearson r with Fisher-z CI, subject-level Bland–Altman, coverage, failure rate, constant & green baselines, cluster bootstrap 10,000 reps over subjects, seed 20261204). Unit-test on synthetic pairs with known answers before touching real data.
- `report.md` + figures generated from `windows.csv` only; every figure axis labelled in BPM with uncertainty shown; data tables beside plots.
- Nothing in the measurement path may call a network service or an LLM.

## 9. Amendment log

| Date | Change | Reason |
|---|---|---|
| 2026-11-22 | Initial protocol frozen (this file) | Written before any data collection |

*(Any later change to metrics, thresholds, exclusions or splits must be added here before it takes effect.)*

---

### Verification notes (what was checked, how)

- Citations 1–4 and the bias/generalization references: titles, authors, venues, DOIs/arXiv ids checked against IEEE Xplore (doc 7565547), OpenAlex (W2520509592, W2016778993, W2896102525), arXiv (1810.04927, 2012.15846, 2305.15199, 2106.06007), PubMed/PMC (PMID 34083724; PMC12311941) on 2026-11-22. PURE composition verified via two independent secondary sources, not the paper PDF. Gudi et al.'s numeric MAE table was not extracted and is therefore not quoted.
- Sample-size CI-width simulation and t multipliers: computed on the assistant's computer, NumPy 2.5.5 / SciPy 1.18.1, seed 20261204 (script `sim_ci_width.py` alongside this file). Results are model-dependent illustrations, labelled as such.
- Expected-accuracy statement in §5.4 is a **conjecture** built from the verified records, not a measurement of our pipeline. No participant data existed when this plan was written.
