# README sections — use verbatim

> These two sections are written for the hackathon README. Copy them as-is.
> They match the frozen protocols (`evaluation.md`, `ubfc_benchmark_plan.md`).

---

## Limitations

- **This is a wellness demonstration, not a medical device.** It has not been cleared or approved by any regulator, has not been validated in a clinical study, and must not be used to diagnose, screen, monitor or manage any medical condition, or to decide anything about a person's care. It is not an oximeter: it measures neither blood oxygen nor blood pressure, and it cannot detect arrhythmias.
- **It measures agreement with a fingertip pulse oximeter, not true heart rate.** Both our reference (a consumer pulse oximeter) and our camera estimate are noisy; agreement between two imperfect methods does not establish clinical accuracy (Bland & Altman, Lancet 1986).
- **Small, controlled evaluation.** Our live-webcam protocol is pre-registered for 10–20 consenting adult volunteers, seated, in ordinary indoor light, at rest. That sample size gives a 95% confidence interval roughly ±2.5–3.7 BPM wide around the mean absolute error (Monte Carlo, `sim_ci_width.py`); a result of "4 BPM MAE" honestly means "somewhere between about 2 and 8". We report the interval, not just the point estimate.
- **The benchmark (UBFC-rPPG REALISTIC, 42 subjects) is also limited:** healthy adults in one lab, one webcam model, no published skin-tone labels, and a ground truth that is itself a smoothed on-device oximeter estimate. Benchmark ground-truth artefacts are a documented problem in this literature (Gudi et al., Applied Sciences 2020).
- **Known failure modes, pre-registered before we measured anything:** head and jaw motion (the benchmark's maths game induces it), low or flickering light, heavy video compression, webcam frame rates below ~15 fps, and rapid heart-rate changes that straddle a 15-second window. The app abstains ("no estimate") when its quality gate fails; the abstention rate is reported alongside every accuracy number, because a low error on the windows we kept can hide a high failure rate.
- **Skin-tone bias is a documented risk we could not fully test.** The rPPG literature reports systematic differences in camera-PPG error across skin tone and gender (Nowara, McDuff & Veeraraghavan, CVPR Workshops 2020; Dasari et al., npj Digital Medicine 2021). UBFC publishes no skin-tone labels, so we make no fairness claim on the benchmark; the volunteer study records self-described skin tone for descriptive, exploratory strata only, too small to certify fairness.
- **Reported accuracies in this literature are protocol-dependent.** Published MAEs for the same classical algorithms range from roughly 2.4 to 7.6 BPM depending on preprocessing and windowing (see `references.md`). Our numbers are from our frozen protocol on our held-out split; they are not the collaboration-style "official" accuracy of any dataset and should not be compared across papers without matching protocols.
- **No performance claim is made for:** children, people with cardiovascular disease or arrhythmias, people wearing heavy makeup over the ROI, very low ambient light, or anyone not represented in our evaluation.

## Who benefits, and who could be harmed

**Who benefits.**
- Curious healthy adults who want a contactless, toy-grade pulse check and a transparent look at how camera-based physiology works.
- Students and researchers: the full protocol, frozen parameters, subject-disjoint split (seed 20261204), scripts and per-window results are public, so every number in this README can be recomputed.
- The rPPG research community, through honest reporting: error bars in BPM, abstention rates, baselines, and failure strata instead of a single cherry-picked accuracy.

**Who could be harmed, and how we mitigate it.**
- **Someone who mistakes this for a medical reading.** A false-reassuring or false-alarming number could delay care or cause anxiety. Mitigation: the app displays "wellness demo — not a medical device" persistently, never renders diagnostic language, and abstains rather than guesses when signal quality is poor. Nothing in the app gives health advice.
- **People with darker skin tones.** Camera PPG relies on light absorbed by blood; less reflected signal can mean larger errors or more abstentions, and the literature documents this bias. Mitigation: we state the risk plainly, report self-described skin-tone strata in the volunteer study (exploratory, not a fairness certification), make no fairness claim, and abstain visibly rather than output a confident wrong number.
- **Privacy of anyone on camera.** Face video is biometric-adjacent personal data. Mitigation: all processing is local in the browser/on the device; no frames are uploaded or stored by the demo; volunteer recordings are made only with written consent, kept locally, de-identified by participant code in every released file, and deleted after analysis unless the volunteer consents to retention. Benchmark videos (UBFC research volunteers) are never re-uploaded or committed to the repository; only code, subject-ID manifests and numeric results are public.
- **Volunteers in our study.** Participation is optional, stoppable at any moment without giving a reason, involves only sitting in front of a webcam and a fingertip oximeter, and excludes anyone under 18. The consent form states exactly what is recorded, what is published (numbers only, participant codes), and the deletion date.
- **Over-trust in AI health demos generally.** Mitigation: the Evaluation section shows the baselines (a constant guess and a naive green-channel method), the confidence intervals, and the cases where we fail — so a stranger can see exactly what the method is and is not worth.

---

*Disclosure line for the README (hackathon rules): "Built with assistance from AI tools: StellarFirm assistants drafted the analysis plan, evaluation protocol and code review (Scientist), and implemented the app and pipeline (Coder). All measurements were produced by the pinned scripts in this repository; no result was generated by an LLM."*
