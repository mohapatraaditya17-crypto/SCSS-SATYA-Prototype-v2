from pathlib import Path
from typing import Dict, Any, List, Optional
from app.schemas.examination import (
    ScreeningTestResult,
    DetectorResult,
    DetectorStatus,
    EvidenceStrength,
    EvidenceRegion,
    DecisionEngineOutput,
)
from app.analysis.fusion.evidence_family import EvidenceFamilyManager
from app.analysis.fusion.calibration import ForensicCalibrator
from app.analysis.fusion.decision_engine import ForensicDecisionEngine
from app.analysis.fusion.composite_heatmap import CompositeHeatmapGenerator


class EvidenceFusionEngine:
    """
    Evidence Correlation, Calibrated Confidence Scoring & Four-Pillar Forensic Engine (SATYA v2).
    Conforms to NIST OpenMFC, ISO/IEC 27037, and C2PA Specification 2.x standards.
    
    Synthesizes normalized detector results, manages evidence family correlation,
    executes the deterministic decision engine, and generates composite heatmaps.
    """
    ENGINE_VERSION = "2026.2-v2"

    @classmethod
    def fuse_evidence(
        cls,
        case_id: str,
        original_filename: str,
        media_type: str,
        file_size_bytes: int,
        hashes: Dict[str, Any],
        extracted_metadata: Dict[str, Any],
        c2pa_analytics: Dict[str, Any],
        jpeg_analytics: Dict[str, Any],
        document_analytics: Dict[str, Any],
        all_artifacts: Dict[str, Any],
        all_tests: List[ScreeningTestResult],
        detector_results: Optional[List[DetectorResult]] = None,
        image_characterization: Optional[Dict[str, Any]] = None,
        image_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Synthesizes raw and normalized forensic signals into calibrated assessments,
        evaluates evidence families, answers the 4 forensic questions, extracts localized
        suspicious regions, and constructs the canonical evidence schema.
        """
        image_char = image_characterization or {}

        # 1. Ensure normalized DetectorResult list exists
        if detector_results is None:
            detector_results = []
            for t in all_tests:
                # Map old ScreeningTestResult to standardized DetectorResult
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

                detector_results.append(
                    DetectorResult(
                        detector_name=t.method,
                        detector_version=t.version,
                        status=status_str,
                        score=score,
                        confidence=conf,
                        evidence_strength=t.evidence_strength or ForensicCalibrator.get_evidence_strength(score, conf),
                        applicable=t.status != "not_applicable",
                        technical_reason=t.explanation,
                        affected_regions=t.affected_regions or [],
                        execution_time_ms=t.execution_time_ms,
                        observations=t.observations,
                        limitations=t.limitations,
                    )
                )

        # 2. Group into Evidence Families with correlation discounting
        evidence_families = EvidenceFamilyManager.group_detector_results(detector_results)

        # 3. Execute Decision Engine
        decision_output: DecisionEngineOutput = ForensicDecisionEngine.evaluate(
            detector_results=detector_results,
            evidence_families=evidence_families,
            image_characterization=image_char,
        )

        # 4. Generate Composite Evidence Heatmap if image path provided
        if image_path and image_path.exists():
            composite_map = CompositeHeatmapGenerator.generate(
                image_path=image_path,
                examination_id=case_id,
                detector_results=detector_results,
                all_artifacts=all_artifacts,
            )
            if composite_map:
                all_artifacts["composite_evidence_map"] = composite_map

        # 5. Extract suspicious localized regions from detector results
        suspicious_regions: List[Dict[str, Any]] = []
        for det_res in detector_results:
            for reg in det_res.affected_regions:
                suspicious_regions.append({
                    "x": reg.x,
                    "y": reg.y,
                    "width": reg.width,
                    "height": reg.height,
                    "score": round(reg.confidence, 3),
                    "detector": det_res.detector_name,
                    "label": reg.label or f"Anomalous region ({det_res.detector_name})",
                })

        # 6. Provenance & Metadata Metrics
        c2pa_present = c2pa_analytics.get("c2pa_present", False)
        signature_valid = c2pa_analytics.get("signature_valid")
        ai_declared = c2pa_analytics.get("ai_declared", False)
        is_screen_capture = image_char.get("image_class") == "SCREENSHOT"
        camera_metadata_present = image_char.get("camera_metadata_present", image_char.get("has_camera_exif", False))
        metadata_software = extracted_metadata.get("Software") or jpeg_analytics.get("software_fingerprint") or "Unknown"

        # 7. Answer the Four Independent Forensic Questions (ISO/IEC 27037)
        # Q1: Origin
        if is_screen_capture:
            q1_origin = "Direct Digital Screen Rendering (Display Interface Buffer)"
            origin_code = "SCREEN_CAPTURE"
        elif camera_metadata_present:
            make = image_char.get("camera_make") or extracted_metadata.get("Make", "Unknown")
            model = image_char.get("camera_model") or extracted_metadata.get("Model", "")
            q1_origin = f"Camera metadata present ({make} {model}); capture origin is unverified".strip()
            origin_code = "CAMERA_METADATA_PRESENT_UNVERIFIED"
        elif document_analytics.get("document_type") in ["pdf", "office_openxml"]:
            q1_origin = f"Digital Document Structure ({document_analytics.get('document_type').upper()})"
            origin_code = "DOCUMENT_CONTAINER"
        elif ai_declared or any(d.detector == "ai_generative_classifier" for d in decision_output.decisive_observations):
            q1_origin = "Statistical or declared synthetic-generation indicators; origin is not independently verified"
            origin_code = "AI_LATENT_SYNTHESIS"
        else:
            q1_origin = "Unknown Digital Source (Metadata Stripped or Web Exported)"
            origin_code = "UNKNOWN"

        # Q2: Integrity
        copymove_decisive = any("copy_move" in d.detector for d in decision_output.decisive_observations)
        splice_decisive = any("splicing" in d.detector for d in decision_output.decisive_observations)

        if copymove_decisive:
            q2_integrity = "Copy-move screening indicator: coherent cloned / duplicated content suspected; examiner verification required"
            integrity_code = "LOCALLY_ALTERED_CLONED"
        elif splice_decisive:
            q2_integrity = "Splicing screening indicator: multi-source composite boundary discontinuity suspected; examiner verification required"
            integrity_code = "LOCALLY_SPLICED"
        elif decision_output.final_assessment == "MANIPULATION_INDICATORS_DETECTED":
            q2_integrity = "Manipulation indicators reported by multiple screening methods; examiner verification required"
            integrity_code = "LOCALLY_ALTERED"
        elif c2pa_present and signature_valid and not ai_declared:
            q2_integrity = "C2PA signature validation succeeded for the supplied manifest; claim scope requires examiner review"
            integrity_code = "C2PA_SIGNATURE_VALID"
        elif decision_output.final_assessment == "NO_MANIPULATION_INDICATORS_DETECTED":
            q2_integrity = "No manipulation indicators reported by completed applicable screening methods; authenticity is not established"
            integrity_code = "NO_INDICATORS_REPORTED"
        else:
            q2_integrity = "Inconclusive: Bitstream Preserved without Decisive Alteration Markers"
            integrity_code = "INCONCLUSIVE"

        # Q3: Generation
        if ai_declared:
            q3_generation = "Generative AI: Explicitly Declared in C2PA Provenance Manifest"
            generation_code = "AI_DECLARED"
        elif decision_output.final_assessment == "AI_GENERATION_INDICATORS_DETECTED":
            q3_generation = "Statistical synthetic-generation indicators observed; origin is unverified"
            generation_code = "AI_GENERATION_INDICATORS_ONLY"
        elif is_screen_capture:
            q3_generation = "Human Interaction: Direct Operating System Interface Render"
            generation_code = "SCREEN_RENDER"
        elif camera_metadata_present:
            q3_generation = "Camera metadata is present; generation origin is undetermined"
            generation_code = "CAMERA_METADATA_UNVERIFIED"
        else:
            q3_generation = "Standard Digital Media (No Generative Diffusion Markers Detected)"
            generation_code = "CONVENTIONAL_DIGITAL"

        # Q4: Transformation
        transformations: List[str] = []
        if is_screen_capture:
            transformations.append("Direct Screen Rasterization")
        if jpeg_analytics.get("double_compression_suspected"):
            transformations.append(f"JPEG Recompression (Est. Q={jpeg_analytics.get('estimated_quality')}%)")
        if copymove_decisive:
            transformations.append("Copy-Move Cloning (Duplicated spatial keypoints)")
        if splice_decisive:
            transformations.append("Image Splicing / Compositing (Boundary discontinuity)")
        if "photoshop" in str(metadata_software).lower():
            transformations.append("Exported or Edited via Adobe Photoshop")
        if not transformations:
            transformations.append("No post-capture spatial transformation detected")
        q4_transformation = "; ".join(transformations)

        # 8. Build Explainability Evidentiary Hierarchy
        ranked_evidence: List[Dict[str, str]] = []
        for dec in decision_output.decisive_observations:
            ranked_evidence.append({
                "level": "DECISIVE",
                "item": f"[{dec.detector}] {dec.finding} (Confidence: {round(dec.confidence * 100)}%)",
            })
        for sup in decision_output.supporting_observations[:5]:
            ranked_evidence.append({
                "level": "SUPPORTING",
                "item": sup,
            })
        for contra in decision_output.contradictory_observations:
            ranked_evidence.append({
                "level": "CONTRADICTORY",
                "item": contra,
            })

        # 9. Format NIST OpenMFC / Canonical Evidence Schema
        canonical_evidence_json = {
            "case_id": case_id,
            "pipeline_version": cls.ENGINE_VERSION,
            "rules_version": decision_output.rules_version,
            "threshold_profile": decision_output.threshold_profile,
            "file": {
                "name": original_filename,
                "mime": media_type,
                "size": file_size_bytes,
                "sha256": hashes.get("sha256"),
                "sha512": hashes.get("sha512"),
                "blake3": hashes.get("blake3"),
                "perceptual_hashes": {
                    "phash": hashes.get("phash"),
                    "dhash": hashes.get("dhash"),
                    "ahash": hashes.get("ahash"),
                    "whash": hashes.get("whash"),
                    "colorhash": hashes.get("colorhash"),
                }
            },
            "image_characterization": image_char,
            "provenance": {
                "c2pa_present": c2pa_present,
                "signature_valid": signature_valid,
                "ai_declared": ai_declared,
                "claim_generator": c2pa_analytics.get("claim_generator"),
                "actions": c2pa_analytics.get("actions", []),
            },
            "metadata": {
                "camera": f"{extracted_metadata.get('Make', '')} {extracted_metadata.get('Model', '')}".strip() or "None",
                "software": metadata_software,
                "has_camera_exif": camera_metadata_present,
                "camera_metadata_present": camera_metadata_present,
                "camera_metadata_verified": bool(image_char.get("camera_metadata_verified", False)),
                "cryptographic_provenance_verified": bool(image_char.get("cryptographic_provenance_verified", False)),
            },
            "localization": {
                "heatmap": all_artifacts.get("composite_evidence_map") or all_artifacts.get("copymove_map") or all_artifacts.get("noise_residual_map") or all_artifacts.get("ela_heatmap"),
                "composite_heatmap": all_artifacts.get("composite_evidence_map"),
                "regions": suspicious_regions,
            },
            "assessment": {
                "technical_assessment": decision_output.final_assessment,
                "classification": decision_output.final_assessment,  # backward compatibility
                "confidence": decision_output.decision_confidence,
                "evidence_strength": decision_output.evidence_strength,
                "human_review_required": True,
                "decision_rationale": decision_output.decision_rationale,
                "coverage": {
                    "applicable_detectors": decision_output.applicable_detector_count,
                    "successful_detectors": decision_output.successful_detector_count,
                    "errors": decision_output.detector_error_count,
                    "coverage_score": decision_output.coverage_score,
                },
                "four_pillars": {
                    "q1_origin": {"question": "Q1 - Where did this content originate?", "finding": q1_origin, "code": origin_code},
                    "q2_integrity": {"question": "Q2 - Has the file/content been altered?", "finding": q2_integrity, "code": integrity_code},
                    "q3_generation": {"question": "Q3 - Was AI used to generate it?", "finding": q3_generation, "code": generation_code},
                    "q4_transformation": {"question": "Q4 - What operations were performed?", "finding": q4_transformation, "operations": transformations},
                },
                "explainability": {
                    "decisive_observations": [d.model_dump() for d in decision_output.decisive_observations],
                    "supporting_observations": decision_output.supporting_observations,
                    "contradictory_observations": decision_output.contradictory_observations,
                    "inconclusive_tests": decision_output.inconclusive_tests,
                    "not_applicable_tests": decision_output.not_applicable_tests,
                    "ranked_evidence": ranked_evidence,
                },
                "evidence_families": {k: v.model_dump() for k, v in evidence_families.items()},
            },
            "detector_results": [r.model_dump() for r in detector_results],
        }

        return canonical_evidence_json
