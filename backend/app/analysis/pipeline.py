import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.schemas.examination import (
    ScreeningTestResult,
    DetectorResult,
    DetectorStatus,
    EvidenceStrength,
    EvidenceRegion,
    DecisionEngineOutput,
)
from app.analysis.characterizer import ImageCharacterizer
from app.analysis.metadata_analyzer import MetadataAnalyzer
from app.analysis.integrity_analyzer import IntegrityAnalyzer
from app.analysis.hash_analyzer import HashAnalyzer
from app.analysis.c2pa_analyzer import C2PAAnalyzer
from app.analysis.document_forensics_analyzer import DocumentForensicsAnalyzer
from app.analysis.jpeg_quantization_analyzer import JPEGQuantizationAnalyzer
from app.analysis.ela_analyzer import ELAAnalyzer
from app.analysis.consistency_analyzer import ConsistencyAnalyzer
from app.analysis.noise_analyzer import NoiseAnalyzer
from app.analysis.fft_analyzer import FFTAnalyzer
from app.analysis.copymove_analyzer import CopyMoveAnalyzer
from app.analysis.ai_synthetic_analyzer import AISyntheticAnalyzer
from app.analysis.typography_analyzer import TypographyAnalyzer
from app.analysis.srm_wavelet_analyzer import SRMWaveletAnalyzer
from app.analysis.splicing_detector import SplicingDetector
from app.analysis.lighting_consistency_analyzer import LightingConsistencyAnalyzer
from app.analysis.evidence_fusion import EvidenceFusionEngine


class ForensicPipeline:
    """
    Forensic Screening Pipeline (SATYA v2).
    Coordinates:
      1. Pre-Analysis Characterization & Applicability Determination
      2. 15 Defensive Multi-Method Screening Analyzers
      3. Result Normalization into Structured DetectorResult format
      4. Evidence Family Correlation & Correlation Discounting
      5. Calibrated Multi-Evidence Decision Engine
      6. Composite Forensic Heatmap Fusion
    """
    PIPELINE_VERSION = "2026.3-v2.1"

    STANDARD_SUGGESTED_MANUAL_CHECKS: List[str] = [
        "Inspect original hardware or source storage device directly where possible (camera SD card, mobile device bitstream acquisition).",
        "Perform optical shadow and lighting direction consistency analysis across objects and subjects.",
        "Compare suspected facial, boundary, or text edges at 400%+ magnification for pixel interpolation or feathering artifacts.",
        "Query reference reverse-image search databases (TinEye, Google Lens) to determine prior online publications or unedited source candidates.",
        "Verify camera hardware serial numbers against manufacturer registration or other known specimens from the same device.",
        "Examine discrete cosine transform (DCT) coefficient histograms with specialized tools (JPEGsnoop) if double-compression is suspected.",
        "Verify font metrics, kerning, and pixel alignment under high contrast for digital documents and interface screenshots.",
        "Assess localized high-frequency diffusion residuals to verify AI synthesis indications.",
        "Inspect C2PA manifest certificate chains against the Adobe / C2PA Trust List where available.",
    ]

    STANDARD_KNOWN_LIMITATIONS: List[str] = [
        "Preliminary screening tool: Automated indicators do not constitute legal proof or definitive forensic determination.",
        "Social media platforms, messaging apps, and content management systems routinely strip EXIF metadata and recompress imagery.",
        "High-quality recompression or intentional blur filtering can suppress or mask Error Level Analysis differences.",
        "Absence of detected manipulation indicators does not establish that an image is authentic or unaltered.",
        "Passive-blind screening methods evaluate statistical anomalies; sophisticated diffusion models (DALL-E 3, Midjourney v6, FLUX) evolve rapidly.",
        "Screenshots and flat UI graphics naturally lack optical sensor noise and camera EXIF records.",
        "C2PA provenance manifests require unbroken cryptographic chains; file format conversions drop external manifest bindings.",
    ]

    @staticmethod
    def _not_applicable_test(method: str, reason: str) -> ScreeningTestResult:
        return ScreeningTestResult(
            method=method,
            version="2.1.0",
            status="not_applicable",
            indicator="test_unavailable",
            indicator_label="Not applicable",
            observations=[reason],
            explanation=reason,
            limitations=["Applicability is a routing decision, not ground truth."],
            execution_time_ms=0.0,
        )


    @classmethod
    def execute(
        cls,
        image_path: Path,
        file_bytes: bytes,
        examination_id: str,
        media_type: str,
        image_width: int,
        image_height: int,
        sha256_digest: str,
        file_size_bytes: int,
    ) -> Dict[str, Any]:
        """
        Executes the comprehensive multi-layer digital media forensics pipeline.
        Produces full screening test results, visual artifacts, analytics, detector results,
        calibrated decision engine output, and canonical evidence JSON.
        """
        all_tests: List[ScreeningTestResult] = []
        all_detector_results: List[DetectorResult] = []
        all_artifacts: Dict[str, Any] = {}

        # 1. Test 1: Metadata & Deep Structural Chunk Forensics
        meta_res = MetadataAnalyzer.analyze(file_bytes, image_width, image_height, media_type)
        all_tests.append(meta_res["test_result"])
        extracted_metadata = meta_res["extracted_metadata"]

        # Parse capture timestamp
        capture_timestamp = None
        raw_date = (
            extracted_metadata.get("DateTimeOriginal") or
            extracted_metadata.get("DateTime") or
            extracted_metadata.get("PNG:LastModified")
        )
        if raw_date:
            try:
                date_str = str(raw_date).strip().replace("/", ":")
                dt = datetime.strptime(date_str[:19], "%Y:%m:%d %H:%M:%S")
                capture_timestamp = dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # 0. Phase 0: Image Characterization & Applicability Determination
        image_char = ImageCharacterizer.characterize(
            image_path=image_path,
            file_bytes=file_bytes,
            mime_type=media_type,
            image_width=image_width,
            image_height=image_height,
            extracted_metadata=extracted_metadata,
        )

        def detector_applicable(detector_id: str) -> bool:
            return detector_id in image_char.get("applicable_detectors", [])

        def record_inapplicable(detector_id: str, method: str) -> None:
            reason = image_char.get("inapplicable_detectors", {}).get(detector_id) or "Characterization rules marked this method not applicable."
            all_tests.append(cls._not_applicable_test(method, reason))

        # 2. Test 2: Dual Cryptographic & Perceptual Hashing (SHA-256, BLAKE3, pHash, dHash, etc.)
        hash_test, _, hash_analytics = HashAnalyzer.analyze(image_path, file_bytes, file_size_bytes)
        all_tests.append(hash_test)
        if hash_analytics:
            all_artifacts["hash_analytics"] = hash_analytics

        # 3. Test 3: C2PA & Content Credentials Cryptographic Provenance
        c2pa_test, c2pa_analytics = C2PAAnalyzer.analyze(file_bytes, media_type, extracted_metadata)
        all_tests.append(c2pa_test)
        all_artifacts["c2pa_analytics"] = c2pa_analytics

        # 4. Test 4: Document & Container Structural Forensics
        if "document_forensics" in image_char.get("inapplicable_detectors", {}):
            reason = image_char["inapplicable_detectors"]["document_forensics"]
            doc_test = ScreeningTestResult(
                method="Document & Container Structural Forensics (ISO/IEC 29500 & PDF 32000)",
                version="2.0.0",
                status="not_applicable",
                indicator="test_unavailable",
                indicator_label="Not Applicable (non-document media)",
                observations=[reason],
                explanation="Specimen is an image rather than an active PDF/Office document container.",
                limitations=cls.STANDARD_KNOWN_LIMITATIONS,
                execution_time_ms=0.5,
            )
            doc_analytics = {"applicable": False, "reason": reason}
        else:
            doc_test, doc_analytics = DocumentForensicsAnalyzer.analyze(file_bytes, image_path, media_type)
        all_tests.append(doc_test)
        all_artifacts["document_analytics"] = doc_analytics

        # 5. Test 5: JPEG Quantization (DQT) & Double-Compression Analysis
        if detector_applicable("jpeg_quantization_analysis"):
            jpeg_test, jpeg_analytics = JPEGQuantizationAnalyzer.analyze(file_bytes, media_type)
            all_tests.append(jpeg_test)
        else:
            jpeg_analytics = {"applicable": False, "reason": image_char.get("inapplicable_detectors", {}).get("jpeg_quantization_analysis")}
            record_inapplicable("jpeg_quantization_analysis", "JPEG Quantization Analysis")
        all_artifacts["jpeg_analytics"] = jpeg_analytics

        # 6. Test 6: Error Level Analysis (ELA - JPEG DCT Compression Grids)
        if detector_applicable("error_level_analysis"):
            ela_test, ela_artifacts = ELAAnalyzer.analyze(image_path, examination_id, media_type)
            all_tests.append(ela_test)
            all_artifacts.update(ela_artifacts)
        else:
            ela_artifacts = {}
            record_inapplicable("error_level_analysis", "Error Level Analysis")

        # 7. Test 7: Image Consistency & Channel Analytics
        if detector_applicable("image_consistency_checks"):
            consistency_test, consistency_artifacts, consistency_analytics = ConsistencyAnalyzer.analyze(
                image_path, examination_id, media_type, extracted_metadata
            )
            all_tests.append(consistency_test)
            all_artifacts.update(consistency_artifacts)
            if "channels" in consistency_analytics:
                all_artifacts["channel_analytics"] = consistency_analytics["channels"]
            if "quadrant_variance" in consistency_analytics:
                all_artifacts["quadrant_variance"] = consistency_analytics["quadrant_variance"]
        else:
            consistency_analytics = {"applicable": False}
            record_inapplicable("image_consistency_checks", "Image Consistency & Channel Analytics")

        # 8. Test 8: Multi-Scale Noise Inconsistency & Residual Analysis (SATYA v2)
        if detector_applicable("noise_residual_analysis"):
            noise_out = NoiseAnalyzer.analyze(image_path, examination_id, media_type)
            noise_test, noise_artifacts, noise_analytics = noise_out[:3]
            noise_det_res = noise_out[3] if len(noise_out) > 3 else None
            all_tests.append(noise_test)
            all_artifacts.update(noise_artifacts)
            if noise_analytics:
                all_artifacts["noise_analytics"] = noise_analytics
            if noise_det_res:
                all_detector_results.append(noise_det_res)
        else:
            noise_analytics = {"applicable": False}
            record_inapplicable("noise_residual_analysis", "Multi-Scale Noise Residual Analysis")

        # 9. Test 9: 2D Fourier Spectral Analysis (FFT Frequency & Lattice Artifacts)
        if detector_applicable("fourier_spectral_analysis"):
            fft_test, fft_artifacts, fft_analytics = FFTAnalyzer.analyze(
                image_path, examination_id, media_type
            )
            all_tests.append(fft_test)
            all_artifacts.update(fft_artifacts)
            if fft_analytics:
                all_artifacts["fft_analytics"] = fft_analytics
        else:
            fft_analytics = {"applicable": False}
            record_inapplicable("fourier_spectral_analysis", "Fourier Spectral Analysis")

        # 10. Test 10: Copy-Move / Clone Forgery Detection (SATYA v2)
        if detector_applicable("copy_move_forgery_detection"):
            copymove_out = CopyMoveAnalyzer.analyze(image_path, examination_id, media_type)
            copymove_test = copymove_out[0]
            copymove_artifacts = copymove_out[1]
            copymove_analytics = copymove_out[2]
            copymove_det_res = copymove_out[3] if len(copymove_out) > 3 else None
            all_tests.append(copymove_test)
            all_artifacts.update(copymove_artifacts)
            if copymove_analytics:
                all_artifacts["copymove_analytics"] = copymove_analytics
            if copymove_det_res:
                all_detector_results.append(copymove_det_res)
        else:
            copymove_analytics = {"applicable": False}
            record_inapplicable("copy_move_forgery_detection", "Copy-Move Forgery Detection")

        # 11. Test 11: AI Generative Classifier (SATYA v2)
        if detector_applicable("ai_generative_classifier"):
            ai_out = AISyntheticAnalyzer.analyze(image_path, examination_id, media_type)
            ai_test, ai_artifacts, ai_analytics = ai_out[:3]
            ai_det_res = ai_out[3] if len(ai_out) > 3 else None
            all_tests.append(ai_test)
            all_artifacts.update(ai_artifacts)
            if ai_analytics:
                all_artifacts["ai_synthetic_analytics"] = ai_analytics
            if ai_det_res:
                all_detector_results.append(ai_det_res)
        else:
            ai_analytics = {"applicable": False}
            record_inapplicable("ai_generative_classifier", "Statistical Synthetic-Indicator Heuristic")

        # 12. Test 12: Document Typography & Character Alignment Engine (SATYA v2)
        if detector_applicable("document_typography_and_alignment"):
            typo_out = TypographyAnalyzer.analyze(
                image_path, examination_id, media_type, image_characterization=image_char
            )
            typo_test = typo_out[0]
            typo_artifacts = typo_out[1]
            typo_analytics = typo_out[2]
            typo_det_res = typo_out[3] if len(typo_out) > 3 else None
            all_tests.append(typo_test)
            all_artifacts.update(typo_artifacts)
            if typo_analytics:
                all_artifacts["typography_analytics"] = typo_analytics
            if typo_det_res:
                all_detector_results.append(typo_det_res)
        else:
            record_inapplicable("document_typography_and_alignment", "Document Typography & Character Alignment")

        # 13. Test 13: SRM Spatial Rich Model & Wavelet Residual Analysis
        if detector_applicable("srm_wavelet_analysis"):
            srm_test, _, srm_analytics = SRMWaveletAnalyzer.analyze(
                image_path, examination_id, media_type
            )
            all_tests.append(srm_test)
            if srm_analytics:
                all_artifacts["srm_analytics"] = srm_analytics
        else:
            srm_analytics = {"applicable": False}
            record_inapplicable("srm_wavelet_analysis", "SRM Wavelet Residual Analysis")

        # 14. Test 14: Splicing & Composite Forgery Detection (SATYA v2)
        if detector_applicable("image_splicing_detector"):
            splice_out = SplicingDetector.analyze(image_path, examination_id, media_type)
            splice_test = splice_out[0]
            splice_artifacts = splice_out[1]
            splice_analytics = splice_out[2]
            splice_det_res = splice_out[3] if len(splice_out) > 3 else None
            all_tests.append(splice_test)
            all_artifacts.update(splice_artifacts)
            if splice_analytics:
                all_artifacts["splicing_analytics"] = splice_analytics
            if splice_det_res:
                all_detector_results.append(splice_det_res)
        else:
            splice_analytics = {"applicable": False}
            record_inapplicable("image_splicing_detector", "Image Splicing Detection")

        # 15. Test 15: Illumination Direction & Geometric Consistency
        if detector_applicable("lighting_consistency_analysis"):
            lighting_test, _, lighting_analytics = LightingConsistencyAnalyzer.analyze(
                image_path, examination_id, media_type
            )
            all_tests.append(lighting_test)
            if lighting_analytics:
                all_artifacts["lighting_analytics"] = lighting_analytics
        else:
            lighting_analytics = {"applicable": False, "reason": image_char.get("inapplicable_detectors", {}).get("lighting_consistency_analysis")}
            record_inapplicable("lighting_consistency_analysis", "Illumination Direction & Geometric Consistency")

        # Build complete DetectorResult list for all 15 tests
        already_added = {d.detector_name for d in all_detector_results}
        for t in all_tests:
            if t.method not in already_added:
                status_str = DetectorStatus.INCONCLUSIVE.value
                if t.status == "not_applicable":
                    status_str = DetectorStatus.NOT_APPLICABLE.value
                elif t.status == "failed":
                    status_str = DetectorStatus.ERROR.value
                elif t.indicator == "indicator_detected":
                    status_str = DetectorStatus.POSITIVE.value
                elif t.indicator == "no_indicator_detected":
                    status_str = DetectorStatus.NEGATIVE.value

                score = t.score
                conf = t.confidence
                all_detector_results.append(
                    DetectorResult(
                        detector_name=t.method,
                        detector_version=t.version,
                        status=status_str,
                        score=score,
                        confidence=conf,
                        raw_score=score,
                        calibrated_probability=None,
                        evidence_strength=t.evidence_strength or (EvidenceStrength.NONE.value if score is None else ("STRONG" if score > 0.70 else ("MODERATE" if score > 0.40 else "NONE"))),
                        applicable=t.status != "not_applicable",
                        technical_reason=t.explanation,
                        affected_regions=t.affected_regions or [],
                        execution_time_ms=t.execution_time_ms,
                        observations=t.observations,
                        limitations=t.limitations,
                    )
                )

        # 16. Multi-Layer Evidence Fusion & Correlation Engine
        hashes = {
            "sha256": sha256_digest,
            "sha512": hash_analytics.get("cryptographic", {}).get("sha512"),
            "blake3": hash_analytics.get("cryptographic", {}).get("blake3"),
            "phash": hash_analytics.get("perceptual", {}).get("phash"),
            "dhash": hash_analytics.get("perceptual", {}).get("dhash"),
            "ahash": hash_analytics.get("perceptual", {}).get("ahash"),
            "whash": hash_analytics.get("perceptual", {}).get("whash"),
            "colorhash": hash_analytics.get("perceptual", {}).get("colorhash"),
        }

        canonical_evidence = EvidenceFusionEngine.fuse_evidence(
            case_id=examination_id,
            original_filename=image_path.name,
            media_type=media_type,
            file_size_bytes=file_size_bytes,
            hashes=hashes,
            extracted_metadata=extracted_metadata,
            c2pa_analytics=c2pa_analytics,
            jpeg_analytics=jpeg_analytics,
            document_analytics=doc_analytics,
            all_artifacts=all_artifacts,
            all_tests=all_tests,
            detector_results=all_detector_results,
            image_characterization=image_char,
            image_path=image_path,
        )

        all_artifacts["canonical_evidence"] = canonical_evidence
        all_artifacts["assessment_summary"] = canonical_evidence["assessment"]

        # Technical Assessment from Calibrated Decision Engine
        assessment_obj = canonical_evidence["assessment"]
        decision_assessment = assessment_obj["technical_assessment"]
        decision_confidence = None if assessment_obj.get("confidence") is None else int(round(assessment_obj["confidence"] * 100))
        evidence_strength = assessment_obj.get("evidence_strength", "NONE")

        # Crucial Doctrine: Human Review is ALWAYS required
        overall_assessment = "requires_human_review"

        return {
            "tests": all_tests,
            "detector_results": all_detector_results,
            "artifacts": all_artifacts,
            "extracted_metadata": extracted_metadata,
            "capture_timestamp": capture_timestamp,
            "overall_assessment": overall_assessment,
            "decision_assessment": decision_assessment,
            "evidence_strength": evidence_strength,
            "decision_confidence": decision_confidence,
            "coverage_score": assessment_obj.get("coverage", {}).get("coverage_score"),
            "canonical_evidence": canonical_evidence,
            "image_characterization": image_char,
            "known_limitations": cls.STANDARD_KNOWN_LIMITATIONS,
            "suggested_manual_checks": cls.STANDARD_SUGGESTED_MANUAL_CHECKS,
        }
