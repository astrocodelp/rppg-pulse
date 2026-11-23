# UBFC-rPPG Benchmark Plan — webcam heart rate (rPPG), AI for Medicine hackathon

**Status: frozen before any UBFC data was processed by this team.** This document is the benchmark half of the protocol; the live-webcam volunteer half is `evaluation.md` (same metrics, same seed). Amendment log at the bottom. All claims labelled **[verified record]**, **[checked by computation]**, **[conjectured]** or **[missing: …]**.

---

## 1. Testable question

> On the public UBFC-rPPG benchmark (Dataset 2, "REALISTIC": 42 subjects playing a time-sensitive maths game), can a classical POS rPPG pipeline estimate 15-second-window mean heart rate with **MAE ≤ 5 BPM** against the simultaneous pulse-oximeter ground truth, on a **subject-disjoint held-out split fixed before processing**?

Primary estimand, metrics, confidence intervals and baselines are exactly those in `evaluation.md` §3–4 (MAE and RMSE in BPM, Pearson r with Fisher-z CI, subject-level Bland–Altman bias and limits of agreement, coverage/abstention rate, cluster bootstrap over subjects, 10,000 replicates, **seed 20261204**, constant and green-channel baselines). Nothing new is defined here except the dataset, the split, and the ground-truth pairing.

## 2. Dataset (chosen; verified facts)

**UBFC-rPPG** (Univ. Bourgogne Franche-Comté remote PPG dataset). Official page: <https://sites.google.com/view/ybenezeth/ubfcrppg> [verified record: page fetched 2026-11-22].

Facts from the official page (quoted/paraphrased):
- Recorded with a **Logitech C920 HD Pro webcam, 30 fps, 640×480, uncompressed 8-bit RGB**, custom C++ acquisition app.
- Ground truth: **CMS50E transmissive fingertip pulse oximeter**, providing the **PPG waveform and PPG heart rates**.
- Subject sits ~1 m from the camera, face visible, indoors with varying sunlight and indoor illumination.
- **Dataset 1 (SIMPLE): 8 videos** (~16,500 frames), subjects asked to sit still, some videos with significant movement at the start. **Dataset 2 (REALISTIC): 42 videos shared (of 46 recorded)**, subject plays a time-sensitive mathematical game that raises heart rate while emulating normal human–computer interaction.
- Download (no credentialing, no form): official **Google Drive folder** <https://drive.google.com/drive/folders/1o0XU4gTIo46YfwaWjIgbtCncc-oF44Xk?usp=drive_link> or **OneDrive** <https://univbourgogne-my.sharepoint.com/:f:/g/personal/yannick_benezeth_u-bourgogne_fr/IgDQvHIcDjiMSrzknzArGE25AVSjt4fjw11QgLpsJX2QPec?e=ySQtZt>. A DaTa@BFC link is announced ("soon") on the page. Matlab and Python ground-truth readers are provided by the authors.

**Reference paper:** Bobbia, S., Macwan, R., Benezeth, Y., Mansouri, A., Dubois, J. (2019). "Unsupervised skin tissue segmentation for remote photoplethysmography." *Pattern Recognition Letters* 124, 82–90. DOI: **10.1016/j.patrec.2017.10.017** [verified record: ScienceDirect article page S0167865517303860 and ACM DL entry for this DOI; the ACM record shows first authors Serge Bobbia, Richard Macwan, Yannick Benezeth; volume/pages from the ScienceDirect listing].

**License:** the official page states Dataset 2 videos are "shared **for research purpose**". **No standard open license (CC-BY/CC0 etc.) is stated on the page we fetched — [missing: explicit license text]**. Consequences we adopt:
1. Use is **research/demo only**, with attribution to the Bobbia et al. paper and the dataset page.
2. **Do not commit dataset videos or ground-truth files to the public repo**; the repo ships only the loader, the split manifest (subject IDs), and results CSVs.
3. Before submission, email Y. Benezeth (yannick.benezeth@u-bourgogne.fr, address on the official page) to confirm hackathon-demo use is within "research purpose" — a polite confirmation, not an access request. Until confirmed, the submission says "used under the dataset's stated research-purpose terms; explicit license not published".
4. The dataset contains identifiable faces of consenting research volunteers recorded by UBFC; we treat the videos as personal data: local storage, no re-upload, no face images in the README or video demo (use plots and a synthetic/own-consented face only).

**Why UBFC and not others** (each checked earlier, see `evaluation.md` §5): MIMIC-IV needs credentialing (excluded by the brief); VIPL-HR needs a signed agreement; PURE needs an email request; UBFC is a direct download with a contact-PPG ground truth and a game condition that exercises the exact failure modes we pre-register (motion, HR change).

### 2.1 Ground-truth definition and file format

- Folder layout (standard, as used by rPPG-Toolbox): `subject<N>/vid.avi` + `subject<N>/ground_truth.txt` [verified record: rPPG-Toolbox README dataset layout, github.com/ubicomplab/rPPG-Toolbox].
- `ground_truth.txt` (Dataset 2): **line 1 = PPG waveform samples, line 2 = device heart rates, line 3 = time stamps in seconds** [verified via a secondary source quoting the format: ieee-dataport.org record "Simulated_Multispectral_rPPG"; cross-check on first load against the authors' Python reader shipped in the download — if the layout differs, log an amendment and follow the authors' reader].
- **Ground-truth HR for a window** = mean of the line-2 device HR values whose line-3 timestamps fall inside the window. The device HR is itself a smoothed on-device estimate, not beat-to-beat truth: we measure **agreement with a pulse oximeter**, exactly as in the volunteer protocol, and say so.
- Frame time base: nominal 30 fps from frame index (the page states 30 fps acquisition); align video time 0 to ground-truth time 0 per the authors' reader; any offset correction must be logged as an amendment before held-out scoring.

## 3. Held-out split (fixed seed, subject-disjoint)

- Universe: **42 REALISTIC subjects**. Dataset 1 (SIMPLE, 8 videos) is **development-only** sanity material; its subjects are not scored.
- **Seed 20261204**, `numpy.random.default_rng(20261204)`: sort subject IDs lexicographically, permute, take first **21 → development**, remaining **21 → held-out test**. The manifest `split_manifest.json` is generated by `make_split.py` (in `docs/`) **before any frame is processed**, committed to the repo with its hash.
- Tuning (window length is fixed at 15 s by the protocol; ROI choice, quality threshold, filter edge details) happens **only on development subjects**. `params_frozen.json` committed before the held-out run; held-out processed once; any re-run disclosed in the amendment log.
- Per subject: whole video cut into non-overlapping 15 s windows (~4–5 per minute of video). All windows of a subject share the subject's split.

## 4. Pipeline under test (identical to volunteer protocol)

MediaPipe face detection → cheek/forehead ROI → spatial mean RGB traces → **POS** projection (Wang et al. 2017, DOI 10.1109/TBME.2016.2609282 [verified record]) → band-pass **0.7–3.0 Hz** (42–180 BPM) → spectral-peak HR per 15 s window, with the pre-registered quality gate (face detected ≥80% of frames; effective fps ≥15; quality index above frozen threshold, else "no estimate" → counted in coverage, not in MAE). Baselines on the same windows: constant (development mean HR) and green-channel spectral peak. CHROM (de Haan & Jeanne 2013, DOI 10.1109/TBME.2013.2266196 [verified record: Europe PMC PMID 23744659]) is a secondary comparator on development only.

## 5. Pre-registered failure cases (benchmark-relevant)

1. **Motion** — the maths game produces head/jaw movement and posture shifts; motion harmonics can capture the spectral peak. We report MAE by window with a motion flag (frame-to-frame ROI displacement above the frozen threshold).
2. **Illumination variation** — the dataset spans varying sunlight/indoor light; low-light windows are flagged by mean ROI luma below the frozen threshold and reported separately.
3. **Skin tone** — UBFC does **not publish skin-tone labels** [missing: skin-tone annotations]. We do **not** guess labels from video. Honest statement: fairness **cannot be evaluated on UBFC**; it is addressed only descriptively in the volunteer study (`evaluation.md` §4.3), and the literature warns of bias (Nowara, McDuff & Veeraraghavan, CVPRW 2020 [verified record: CVF Open Access page/PDF]; Dasari et al. 2021, DOI 10.1038/s41746-021-00462-z [verified record]).
4. **HR transients** — the game raises HR; a 15 s window straddling a fast rise pairs a lagging oximeter average with a spectral peak — errors concentrate there; report error vs |ΔHR| between adjacent windows as a descriptive plot.
5. **Ground-truth artefacts** — Gudi et al. 2020 (DOI 10.3390/app10238630 [verified record]) show benchmark ground-truth artefacts distort reported errors; windows with missing/flat device HR are excluded by the reference-blind rule and counted.

## 6. Expected accuracy — graded, not promised

Evidence for what POS-class pipelines achieve **on UBFC** (all numbers from other groups, not ours):

| Source | Condition | Reported accuracy | Grade |
|---|---|---|---|
| PhysBench benchmark tables (github.com/KegangWangCCNU/PhysBench_Archived), UBFC-trained → UBFC-tested | standardized preprocessing, windows per their protocol | POS MAE ≈ **3.6 BPM**, RMSE ≈ 10.1, r ≈ 0.63; CHROM MAE ≈ **4.6**, RMSE ≈ 9.9 [verified record: table fetched; preprocessing differs from ours] | Moderate: public reproducible code, but not peer-reviewed table; split/window details differ |
| Same tables, cross-dataset (trained on PURE → tested UBFC) | no UBFC tuning | POS MAE **2.45**, RMSE 8.56, r 0.90; CHROM 3.82 / 12.3 [verified record] | Moderate; shows large sensitivity to preprocessing |
| Rodrigues & Garcia 2025, *Data in Brief*, DOI 10.1016/j.dib.2025.111888 [verified record, see evaluation.md §5] | uncontrolled light, 10-min videos, ECG ref | POS MAE **7.59 ± 0.46 BPM** | Moderate: peer-reviewed, small n (26), different setting |
| Dasari et al. 2021, *npj Digital Medicine*, DOI 10.1038/s41746-021-00462-z [verified record] | diverse real-world cohorts | mean diff ≈ 1 BPM but variability ≈ 11 BPM | Moderate–high for the bias/variability lesson |

**Our pre-registered expectation [conjectured]:** with our own 15 s windows and frozen POS pipeline, UBFC REALISTIC held-out MAE lands in the **3–8 BPM** range; the ≤5 BPM target may fail, and we will report that plainly if it does. We promise **no number** before the run. The spread across sources (2.4–7.6 BPM MAE for the same algorithm family) is itself the honest headline: **preprocessing and evaluation protocol dominate the reported accuracy of classical rPPG.**

## 7. Deliverables from the benchmark run (Coder health implements)

- `windows.csv` — same schema as `evaluation.md` §8, with `dataset=UBFC`, `condition=game`, `motion_flag`, `low_light_flag` columns added.
- `report_ubfc.md`: MAE/RMSE with cluster-bootstrap 95% CIs (BPM), coverage, Bland–Altman plot (subject-level LoA), baselines, per-flag strata, all axes labelled in BPM, colour-blind-safe palette, data table beside every figure.
- Everything reproducible from: dataset download (URLs above) + `make_split.py` + `params_frozen.json` + pinned `requirements.txt` + seed 20261204.

## 8. Amendment log

| Date | Change | Reason |
|---|---|---|
| 2026-11-22 | Benchmark plan frozen (this file); split not yet generated | Written before any UBFC processing |
