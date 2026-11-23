# References — every entry checked against a record

Verification key: **[V]** title/authors/year/identifier confirmed in the named record during this task (2026-11-22). Numbers quoted from a source are attributed there; nothing here is a result we measured.

## Methods

1. **[V]** Wang, W., den Brinker, A. C., Stuijk, S., & de Haan, G. (2017). Algorithmic Principles of Remote PPG. *IEEE Transactions on Biomedical Engineering*, 64(7), 1479–1491. DOI: **10.1109/TBME.2016.2609282**. Records: IEEE Xplore document 7565547; OpenAlex W2520509592 (title, authors, venue, DOI checked; online 2016, issue July 2017). — The POS algorithm our pipeline uses.

2. **[V]** de Haan, G., & Jeanne, V. (2013). Robust pulse rate from chrominance-based rPPG. *IEEE Transactions on Biomedical Engineering*, 60(10), 2878–2886. DOI: **10.1109/TBME.2013.2266196**. Record: Europe PMC, PMID **23744659** (title, authors, journal 60(10):2878–86, DOI fetched). — The CHROM algorithm (secondary comparator).

3. **[V]** Bland, J. M., & Altman, D. G. (1986). Statistical methods for assessing agreement between two methods of clinical measurement. *The Lancet*, 327(8476), 307–310. DOI: **10.1016/S0140-6736(86)90837-8**. Record: Europe PMC, PMID **2868172** (title, authors, journal, volume/issue/pages, DOI fetched). — Bias and limits of agreement.

## Dataset

4. **[V]** Bobbia, S., Macwan, R., Benezeth, Y., Mansouri, A., & Dubois, J. (2019). Unsupervised skin tissue segmentation for remote photoplethysmography. *Pattern Recognition Letters*, 124, 82–90. DOI: **10.1016/j.patrec.2017.10.017**. Records: ScienceDirect article S0167865517303860 (title, journal, vol 124, pages, DOI) and ACM DL entry for this DOI (first authors Serge Bobbia, Richard Macwan, Yannick Benezeth). — The UBFC-rPPG dataset paper. Official dataset page: <https://sites.google.com/view/ybenezeth/ubfcrppg> (fetched: Logitech C920 webcam, 30 fps, 640×480 uncompressed RGB; CMS50E transmissive pulse oximeter ground truth, PPG waveform + PPG heart rates; Dataset 1 SIMPLE 8 videos; Dataset 2 REALISTIC 42 shared of 46 recorded, maths-game condition; Google Drive and OneDrive download links, no credentialing; "shared for research purpose" — **no standard license text stated [missing: explicit license]**).

## Bias, fairness and ground-truth quality (failure-case evidence)

5. **[V]** Nowara, E. M., McDuff, D., & Veeraraghavan, A. (2020). A Meta-Analysis of the Impact of Skin Tone and Gender on Non-Contact Photoplethysmography Measurements. *IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops (CVPRW) 2020*. Record: CVF Open Access PDF, <https://openaccess.thecvf.com/content_CVPRW_2020/papers/w19/Nowara_A_Meta-Analysis_of_the_Impact_of_Skin_Tone_and_Gender_CVPRW_2020_paper.pdf> (title, authors, venue fetched; DOI **[missing: CVF page shows no DOI]**). Verified numbers from the paper's tables: POS mean error female **−0.43 ± 0.15 BPM** vs male **1.51 ± 0.10 BPM**; female MAE **4.49**, male MAE **3.78 BPM**; female RMSE **10.44**, male RMSE **9.17 BPM**; GREEN errors grow with Fitzpatrick type (type VI ≈ −9.6 ± 1.7 BPM). — Documents systematic skin-tone/gender differences in camera PPG error.

6. **[V]** Dasari, A., Prakash, S. K. A., Jeni, L. A., & Tucker, C. S. (2021). Evaluation of biases in remote photoplethysmography methods. *npj Digital Medicine*, 4, 91. DOI: **10.1038/s41746-021-00462-z**, PMID **34083724**. Record: abstract fetched (India and Sierra Leone cohorts, FDA-cleared contact reference; mean difference ≈ 1 BPM but pulse-rate variability ≈ 11 BPM). — Small average bias does not mean small per-window error.

7. **[V]** Gudi, A., Bittner, M., & van Gemert, J. (2020). Real-Time Webcam Heart-Rate and Variability Estimation with Clean Ground Truth for Evaluation. *Applied Sciences*, 10(23), 8630. DOI: **10.3390/app10238630**, arXiv:**2012.15846**. Records: arXiv abstract + MDPI page <https://www.mdpi.com/2076-3417/10/23/8630> (title, authors, venue, identifiers fetched; their exact MAE table not extracted — not quoted). — Benchmark ground-truth artefacts distort reported errors; error grows as the window shrinks.

## Expected-accuracy anchors (other groups' numbers, graded in ubfc_benchmark_plan.md §6)

8. **[V]** Rodrigues & Garcia et al. (2025). Evaluating remote photoplethysmography: A 10-minute video dataset in uncontrolled lighting. *Data in Brief*. DOI: **10.1016/j.dib.2025.111888**, PMC**12311941**. Record: full-text Table 1 passage via research index (26 participants, ECG reference, uncontrolled light; GREEN MAE 7.57 ± 0.66, ICA 7.61 ± 0.42, CHROM 10.05 ± 0.46, POS 7.59 ± 0.46 BPM; RMSE 12–17 BPM; r 0.24–0.50). Author initials as listed on the PMC record; full author list in `evaluation.md` §5 citation line.

9. **[V-table]** PhysBench (archived) benchmark tables. <https://github.com/KegangWangCCNU/PhysBench_Archived> (README tables fetched): UBFC-trained → UBFC-tested classical **POS MAE 3.60 BPM, RMSE 10.1, r 0.634; CHROM MAE 4.56 BPM, RMSE 9.91, r 0.569**; cross-dataset (PURE-trained → UBFC-tested) **POS MAE 2.45 BPM, RMSE 8.56, r 0.900; CHROM 3.82 / 12.3 / 0.830**. The authors themselves note unsupervised methods are highly sensitive to pre/post-processing. **Not peer-reviewed; preprocessing differs from ours.** Used only to grade the plausible range, never as our result.

## Tools

10. **[V]** rPPG-Toolbox (Ubiquitous Computing Lab, NeurIPS 2023). <https://github.com/ubicomplab/rPPG-Toolbox> (README fetched: UBFC folder layout `data/UBFC-rPPG/subject<N>/vid.avi` + `ground_truth.txt`). License: **[missing: LICENSE file not opened this task — verify before reusing code]**.

11. MediaPipe Face Detection (Google). <https://developers.google.com/mediapipe> — tool documentation pointer; version pinned by Coder health in `requirements.txt`. [not a paper]

---

**Honesty notes.** (a) No reference here was cited from memory alone; each identifier was opened in a database or publisher record during this task. (b) Where a record lacked a field (Nowara DOI; UBFC license text; rPPG-Toolbox license) the gap is marked rather than filled. (c) Numbers in rows 5–9 belong to other groups under other protocols; our own results will appear only in `report.md` / `report_ubfc.md` after the frozen runs.
