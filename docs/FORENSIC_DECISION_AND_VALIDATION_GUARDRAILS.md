# Forensic Decision and Validation Guardrails

**Status:** Engineering and validation requirements  
**Scope:** SCSS SATYA forensic image authenticity screening pipeline  
**Audience:** Developers, forensic examiners, validation owners

> The tool screens. The expert decides. Automated findings are screening observations, not conclusive forensic opinions.

## 1. Purpose and decision principles

This document records safeguards required to keep automated screening outputs scientifically cautious, reproducible, and explainable.

1. A detector finding is not, by itself, a forensic conclusion.
2. Absence of a detected indicator is not proof of authenticity or absence of manipulation.
3. Detector applicability, execution status, evidence strength, and uncertainty must remain explicit.
4. A failed or inapplicable detector must never be silently represented as a negative finding.
5. Any probability or confidence claim must be supported by empirical validation on representative, independent data.

## 2. Characterization and detector applicability

The image characterization stage should produce a per-detector applicability decision before detector execution. A centralized detector registry should define, for each detector:

- detector identifier and version;
- supported media classes and technical preconditions;
- applicability predicate and rationale;
- execution entry point;
- expected result schema;
- known limitations.

The pipeline must apply this gate consistently to every detector, not only document forensics. For each detector, record one of:

- `SUCCESS`: applicable and executed successfully;
- `NOT_APPLICABLE`: a documented precondition was not met;
- `ERROR`: applicable, but execution failed;
- `SKIPPED`: intentionally not executed, with a reason.

A `NOT_APPLICABLE` detector must not execute. A detector error is a coverage failure, not negative evidence. Do not include either state as a negative finding in evidence fusion.

Characterization should explain its classification and limitations. Media-class labels are routing hints, not ground truth.

## 3. Metadata and provenance safeguards

EXIF, IPTC, XMP, software strings, and other embedded metadata are mutable observations. Their presence does not establish that a file came directly from a physical camera, nor that it is unaltered.

Do not treat EXIF presence as authoritative proof of camera origin. Keep separate fields for:

- `camera_metadata_present`;
- `camera_metadata_consistent`;
- `camera_metadata_complete`;
- `camera_metadata_plausible`;
- `camera_metadata_verified`;
- `cryptographic_provenance_verified`.

Only use the word *verified* when a defined verification procedure has actually succeeded. A metadata string naming an image-generation tool is an indication that may warrant examination, not conclusive proof of generation. A missing metadata string is not evidence that an image is camera-captured.

Cryptographic provenance validation (including any supported C2PA validation) must distinguish a valid signature, an invalid signature, an absent manifest, an untrusted signer, and a validation failure. Do not conflate absence of provenance data with a provenance conflict.

## 4. AI-synthetic indicators

Statistical image features such as cross-channel residual correlation, spatial autocorrelation, spectral decay, high-frequency lattice peaks, patch variance, and patch kurtosis can be useful research indicators. Unless a trained model and validation evidence are present, describe this component as a **statistical synthetic-indicator heuristic**, not a validated AI classifier.

Do not promote a metadata match (for example, a software or model name in EXIF/XMP) directly to a near-certain synthetic score. Report it as a metadata indication, separately from statistical evidence and independently verified provenance.

Suggested finding levels:

- **Metadata indication:** a relevant metadata field or software string was observed.
- **Statistical indication:** heuristic features crossed a documented screening threshold.
- **Corroborated indication:** independent evidence sources support the same hypothesis.
- **Inconclusive:** results are ambiguous, contradictory, or insufficient.

Any thresholds and weights must be versioned and evaluated on held-out data. Do not claim model accuracy without an identified model artifact, reproducible training/evaluation procedure, and independent test results.

## 5. Scores, confidence, and calibration

Missing values must remain missing. Do not replace a missing detector score with a fabricated positive or negative constant, and do not supply a default confidence value merely to satisfy a schema.

Use nullable fields and explicit states such as `UNKNOWN` or `NOT_REPORTED`. Preserve the detector's raw score and its documented score direction/range.

A fixed reliability weight is not empirical probability calibration. Terms such as *calibrated probability* should be reserved for a model calibrated on a representative held-out calibration set with documented methodology and evaluation. Suitable evaluation may include reliability diagrams, Brier score, expected calibration error (ECE), and calibration slope/intercept. Record calibration dataset version, method, and calibration artifact version.

If calibration has not been demonstrated, expose a raw screening score or ordinal evidence strength; do not present it as a probability of manipulation or authenticity.

## 6. Evidence-family fusion and dependence

Evidence from multiple detectors is not automatically independent. Several detectors may respond to the same underlying compression, resizing, resampling, noise, or image-content effects.

The final decision engine should:

1. preserve individual detector findings and raw observations;
2. group related observations into evidence families;
3. distinguish independent corroboration from correlated signals;
4. account for detector applicability and execution coverage;
5. avoid counting multiple correlated detectors as independent votes;
6. retain contradictory and inconclusive evidence in the report.

If family weights are used, document their source, rationale, version, and empirical validation. Do not imply that arbitrary constants are statistically calibrated. Do not invent correlation coefficients; estimate or otherwise justify dependence handling using appropriate validation data.

A weighted evidence design may be explored, but it must not be represented as validated until its weighting and aggregation rules have been tested on independent, representative specimens.

## 7. Decision taxonomy and reporting

Do not infer authenticity from the combination of camera metadata and a lack of positive manipulation findings. No-positive-evidence is not proof of authenticity.

Keep observations, findings, and conclusions separate. A conservative screening taxonomy may include:

- `MANIPULATION_INDICATORS_DETECTED`;
- `AI_GENERATION_INDICATORS_DETECTED`;
- `PROVENANCE_VERIFIED`;
- `PROVENANCE_CONFLICT`;
- `NO_MANIPULATION_INDICATORS_DETECTED`;
- `INCONCLUSIVE`;
- `INSUFFICIENT_EVIDENCE`;
- `ANALYSIS_ERROR`.

These are screening states, not categorical legal opinions. A report should show the evidence supporting the state, contradictory observations, applicable limitations, detector coverage, and whether human review is required.

Suggested coverage metric:

`coverage = successfully_executed_applicable_detectors / applicable_detectors`

Report the numerator, denominator, and any detector errors/skips; do not hide low coverage behind a single percentage. If no detectors were applicable, report coverage as not defined rather than dividing by zero.

## 8. Detector result contract

Normalize detector outputs without discarding provenance or uncertainty. A result contract should include at least:

```json
{
  "detector_id": "example_detector",
  "version": "2.0.0",
  "applicable": true,
  "execution_status": "SUCCESS",
  "finding": "INCONCLUSIVE",
  "raw_score": null,
  "calibrated_probability": null,
  "confidence": null,
  "evidence_strength": "UNKNOWN",
  "family": "RESIDUAL",
  "regions": [],
  "observations": [],
  "limitations": [],
  "error_code": null,
  "runtime_ms": 0.0
}
```

Schema rules:

- `raw_score`, `calibrated_probability`, and `confidence` are nullable.
- `calibrated_probability` remains null unless calibration is empirically established.
- `execution_status` is independent from `finding`.
- An `ERROR` result cannot be converted into a negative finding.
- A `NOT_APPLICABLE` result records a reason and is excluded from the applicable-detector denominator.
- Include detector and pipeline versions in exported reports.

## 9. Dataset construction and leakage prevention

Historical processing logs are operational telemetry, not automatically a labelled accuracy dataset. A successful HTTP response or completed analysis does not establish whether a detector was correct.

Build a controlled evaluation corpus with documented source lineage, ground truth, and transformation history. Retain parent-child relationships: all derivatives of a source specimen must remain in the same train, calibration, validation, or test partition.

Recommended manifest fields:

- `specimen_id`;
- `parent_id`;
- `sha256`;
- `source_group`;
- `device_group`;
- `media_class`;
- `ground_truth`;
- `manipulation`;
- `generation_model`;
- `compression_history`;
- `split`;
- `label_source`;
- `reviewer_or_adjudication_reference`.

Use the project's intended corpus categories as separate strata, including authentic photographs, authentic documents, screenshots, scanned documents, authentic AI-generated images, copy-move, splicing, object removal/inpainting, retouching, and text modification. Document any imbalance or missing category rather than implying coverage.

Keep all related source and derivative files in one split to prevent near-duplicate leakage. Prefer independent source devices, source collections, and acquisition contexts across partitions where feasible.

## 10. Evaluation and confusion matrices

Evaluate both the overall decision and each detector. At minimum, report:

- confusion matrix with clearly defined positive class;
- precision, recall, specificity, F1, and balanced accuracy where appropriate;
- per-class sample counts and confidence intervals;
- inconclusive, not-applicable, and error rates;
- detector applicability and analysis coverage;
- performance by manipulation type and media class;
- performance by source/device group and compression history;
- false-positive and false-negative specimen review.

Use multidimensional confusion matrices or stratified evaluation tables for overall assessment, manipulation type, media type, source/device, and compression. Do not pool categories in a way that hides failure on a particular class.

Track error categories such as `FALSE_POSITIVE`, `FALSE_NEGATIVE`, `OVER_CONFIDENT`, `UNDER_CONFIDENT`, `WRONG_APPLICABILITY`, `WRONG_LOCALIZATION`, `PROVENANCE_ERROR`, `AI_FALSE_POSITIVE`, `AI_FALSE_NEGATIVE`, `COMPRESSION_CONFUSION`, and `METADATA_CONFUSION`.

## 11. Security and evidence handling

Before production use, verify and document:

- authentication and role-based authorization for analysis, evidence access, and export;
- upload size, file type, parser, and decompression limits enforced consistently at frontend and backend;
- streaming upload handling and safe temporary-file cleanup;
- encryption and access control for evidence storage and exported reports;
- immutable or tamper-evident audit events for evidence access and processing;
- transaction and recovery behaviour for interrupted analysis;
- dependency, container, and deployment security checks.

A local filesystem or SQLite database should not be represented as a production evidence vault without a documented security, availability, backup, access-control, and integrity design.

A tamper-evident audit chain may use a construction such as:

`H_n = SHA256(H_(n-1) || CanonicalJSON(Event_n))`

Protect checkpoints with appropriate signing/key management and ensure event canonicalization, key rotation, verification, and failure handling are specified. A hash chain alone does not prevent an attacker with write access from rewriting the entire chain unless checkpoints are protected.

## 12. Release gates

Before making forensic performance claims or promoting a release:

- [ ] Every detector has a documented applicability contract.
- [ ] Inapplicable and failed detectors are represented distinctly.
- [ ] Missing scores/confidence remain unknown.
- [ ] Metadata indicators are not treated as proof of origin or generation.
- [ ] Calibration terminology matches demonstrated validation.
- [ ] Evidence dependence and family aggregation are documented.
- [ ] No-positive-finding paths do not assert authenticity.
- [ ] Dataset lineage and split isolation are independently checked.
- [ ] Overall and stratified confusion matrices are produced.
- [ ] Security and evidence-handling controls are tested.
- [ ] Tests and evaluation results are reproducible from versioned artifacts.

## 13. Implementation note

This document specifies engineering and validation guardrails. It does not claim that these controls are already implemented, that historical metrics establish detector accuracy, or that the platform is certified for evidentiary use. Implementation status must be verified against code, tests, deployment configuration, and independent validation artifacts.
