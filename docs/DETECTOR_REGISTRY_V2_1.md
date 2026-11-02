# SATYA v2.1 Detector Registry and Method Contracts

**Status:** Screening method inventory, not an independent validation claim  
**Version:** 2.1.0  
**Principle:** The tool screens; the examiner decides.

All 15 methods are registered below. A detector's positive/negative state means only that its implemented screening logic emitted that state. It is not a calibrated probability, proof of authenticity, or proof of manipulation. The analyzer-specific thresholds remain implementation thresholds and must be assessed on held-out specimens before they are described as validated.

| Detector ID | Evidence family | Input / method | Applicability contract | Key limitations / FP risks | FN risks / required validation |
|---|---|---|---|---|---|
| metadata_examination | PROVENANCE (metadata only) | Embedded EXIF/IPTC/XMP/container metadata | Parse supported formats; report unsupported/parse error separately | Tags are mutable, copied, stripped, forged; software tag is not proof | Metadata stripping causes misses; test rewritten tags, malformed metadata, transcodes |
| cryptographic_and_perceptual_hashing | INTEGRITY | SHA-256/other cryptographic hashes and perceptual hashes | Cryptographic hashes apply to exact bytes; perceptual comparison requires reference specimen | Hash value identifies bytes, not truth; pHash similarity is not manipulation evidence | Similar but recompressed/edited files; test reference/no-reference distinction and collision behavior |
| c2pa_provenance | PROVENANCE | C2PA manifest/signature validation | Only when a manifest/claim is present and parser supports its format | Valid signature binds a claim/asset; signer trust and claim scope remain separate; absence is not conflict | Missing external manifests, unsupported algorithms, revoked/untrusted signers; test trust-list and chain outcomes |
| document_forensics | DOCUMENT_CONTAINER | PDF/Office container and structural parsing | Only active supported document/container inputs; raster image files are N/A | Repacked documents and legitimate incremental saves may look unusual | Embedded images, scans, malformed/polyglot containers; validate container-type boundaries |
| jpeg_quantization_analysis | COMPRESSION | JPEG DQT tables and double-compression cues | JPEG bitstream with readable DQT tables | Recompression, scaling, quality changes, encoder differences | PNG/WebP or re-encoded JPEG; validate each encoder, quality and resize stratum |
| error_level_analysis | COMPRESSION | JPEG recompression residual visualization | JPEG input; results are visual/heuristic | Texture, edges, quality changes and local content cause bright areas | High-quality recompression, blur, uniform edits; require controlled localized edit tests |
| image_consistency_checks | INTEGRITY / STRUCTURAL | Channel, quadrant and image-statistic comparisons | Supported raster images with sufficient dimensions | Natural content/lighting/color profiles can create nonuniformity | Uniform or low-resolution images may hide differences; test class-specific baselines |
| noise_residual_analysis | RESIDUAL | Multi-scale residual/noise blocks and spatial clustering | Raster with adequate size/texture; otherwise N/A/inconclusive | Denoising, sharpening, sensor variability and texture can mimic anomalies | Recompression/resizing can erase traces; test camera/device, ISO, denoise and export strata |
| fourier_spectral_analysis | RESIDUAL | 2-D FFT and spectral/lattice features | Raster with sufficient dimensions | Resampling, periodic texture, display capture and sharpening can create peaks | Blur/recompression can suppress peaks; validate resolution/content stratification |
| copy_move_forgery_detection | MANIPULATION | Local feature matching / spatial cluster detection | Adequate image dimensions and repeatable visual features | Repeated real-world patterns can resemble cloning | Smooth/low-texture regions, scale/rotation/blur can evade matching; synthetic paired transformations |
| ai_generative_classifier | AI_ML (heuristic) | Cross-channel residual, autocorrelation, spectral decay, lattice and patch statistics | Broad screening only; class and format should be logged | Not a trained/validated AI classifier; content, style, compression and resizing confound it; AI metadata is mutable | Modern generators/post-processing can evade it; evaluate per generator/version and keep it as heuristic until independently validated |
| document_typography_and_alignment | DOCUMENT_CONTAINER | OCR/text baseline, font/edge/alignment statistics | Documents/screenshots with sufficient text; otherwise N/A | Legitimate font rendering, antialiasing, scan skew and OCR error | Small text, low DPI, blur, multilingual scripts; validate per script/font/render pipeline |
| srm_wavelet_analysis | RESIDUAL | SRM filter-bank and wavelet residual statistics | Raster with sufficient spatial support | Same residual confounders as noise/FFT; correlated evidence | Low-res, denoised, recompressed; validate separately and do not count as independent witness |
| image_splicing_detector | MANIPULATION | Regional block/residual boundary inconsistency | Adequate resolution and region support | Natural boundaries, shadows, texture and compression discontinuities | Feathering, seamless blending, global transforms; paired splice ground truth with localization masks |
| lighting_consistency_analysis | PHYSICAL_CONSISTENCY | Illumination direction/geometry consistency | 3D scene/photographic content where lighting cues exist | Multiple light sources, reflective materials, HDR and scene complexity | Flat lighting, low dynamic range, rendered scenes; examiner review and controlled scene geometry |

## Runtime contract

Each result must keep execution status separate from finding:

- `POSITIVE`, `NEGATIVE`, `INCONCLUSIVE`: applicable detector ran.
- `NOT_APPLICABLE`: applicability contract was not met; analyzer must not run.
- `ERROR`: applicable detector failed; it is a coverage failure, never a negative.
- Missing score/confidence stays null.
- `calibrated_probability` stays null until a reproducible calibration artifact and independent evaluation are present.

## Evidence-family semantics

- INTEGRITY: exact-bitstream identity or perceptual similarity; not a truth/authenticity classifier.
- PROVENANCE: claims and signer/signature observations; not proof of depicted events.
- COMPRESSION: encoding and recompression traces; not proof of editing intent.
- RESIDUAL: noise/spectral/statistical anomalies; correlated methods must not be counted as separate independent witnesses.
- MANIPULATION: spatial cloning/splicing indicators; examiner validates localization and alternative explanations.
- AI_ML: currently a statistical heuristic, not a validated trained classifier.
- PHYSICAL_CONSISTENCY: scene-lighting/geometry indicators, with substantial applicability limits.
- DOCUMENT_CONTAINER: document structure and typography, not photographic authenticity.

## Required validation for every detector

Record detector version, input class, source group, device group, compression history, ground-truth label source, applicable status, execution status, raw score, nullability, threshold version, runtime, and localization (where relevant). Report TP/TN/FP/FN plus inconclusive/error/N/A counts, stratified by media class, manipulation subtype, source/device group and compression.
