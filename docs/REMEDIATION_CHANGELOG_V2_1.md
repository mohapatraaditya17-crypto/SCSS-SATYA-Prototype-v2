# SATYA v2.1 Remediation Changelog

**Branch:** `remediation/forensic-safety-v2-1`  
**Base:** `main`  
**Purpose:** Correct unsafe screening semantics and make evaluation status transparent.

## Implemented in this branch

1. **Applicability enforcement:** The image characterization applicability matrix is now checked before JPEG/DQT, ELA, consistency, noise residual, FFT, copy-move, AI-statistical heuristic, typography, SRM/wavelet, splicing and lighting analyzers run. Inapplicable methods produce explicit `NOT_APPLICABLE` test records.
2. **Camera metadata:** EXIF Make/Model is treated as a mutable metadata observation. It does not establish optical capture, force a photograph class, or support an authenticity conclusion.
3. **Decision taxonomy:** Automated assessment now reports screening indicators (manipulation, AI-statistical, no indicators, inconclusive, insufficient evidence, and provenance status) rather than emitting `LIKELY_AUTHENTIC`.
4. **Missing outputs:** Missing detector score and confidence remain null. The pipeline no longer assigns default scores/confidences or a default 50% aggregate confidence.
5. **Calibration:** The prior reliability-weight rescaling is disabled. No calibrated probability is emitted without a fitted and independently evaluated calibration artifact.
6. **Evidence families and errors:** Hard-coded family reliability weights are disabled. Detector errors remain explicit and cannot be treated as negative evidence; negative family state is labelled as no indicator observed rather than support for authenticity.
7. **AI method scope:** The AI detector is described as an uncalibrated statistical heuristic. AI-related metadata is a separate mutable indication and no longer forces a high synthetic score. The heuristic cannot independently verify AI origin.
8. **ML registry:** Unsupported performance metrics and the empty-file SHA-256 placeholder are removed from model metadata. The coefficient-based classifier is explicitly marked experimental and unvalidated.
9. **Coverage:** Decision output includes applicable, successfully executed, and errored detector counts plus coverage. The pipeline propagates coverage separately from calibrated confidence.
10. **Evaluation:** The confusion matrix separates TP/TN/FP/FN from inconclusive, ERROR, and NOT_APPLICABLE states. It reports breakdowns by manipulation type, media class, source type, and compression history.
11. **Dataset lineage:** Manifest entries support parent IDs, source groups, device groups, media class, label provenance, adjudication reference, and compression history. Split ratios are validated, and source-group grouping is used for splitting.
12. **Detector registry:** `DETECTOR_REGISTRY_V2_1.md` documents all 15 screening methods, input/applicability constraints, likely false-positive/false-negative risks, and validation requirements.
13. **Regression tests:** Tests cover EXIF non-authority, screening decision taxonomy, missing confidence, error coverage, and evidence-family error isolation.

## Explicitly not claimed

- No detector is scientifically validated by this branch.
- No calibrated probability or empirical family reliability weight is claimed.
- No independent controlled v2 validation corpus has been created or populated here.
- Historical 1,005-row operational runs are not treated as independent accuracy evaluation.
- The branch is not a forensic certification or production-readiness declaration.

## Validation still required

- Run the backend unit and integration suites in the project's supported environment.
- Add end-to-end tests that mock all analyzer entry points and prove inapplicable analyzers are not invoked.
- Re-run historical specimens as an operational baseline only, clearly separated from labelled validation.
- Build a controlled, adjudicated parent/derivative dataset with source-group split isolation.
- Evaluate all detectors and the overall screening matrix by media class, source/device, manipulation subtype, and compression.
- Fit calibration only after a separate calibration split and report Brier score, ECE, reliability curves, calibration slope/intercept and confidence intervals.
- Perform security testing of upload limits, API authorization, evidence vault, immutable audit trail and retention controls.

**Test execution note:** GitHub source edits were made through the connected repository integration. No local Python runtime or confirmed GitHub Actions test run was available during this change session; tests must be run in CI before merge.
