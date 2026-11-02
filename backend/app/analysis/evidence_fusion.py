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
    Evidence Correlation, Conservative Screening Decision & Four-Pillar Forensic Engine (SATYA v2.1).
    Conforms to NIST OpenMFC, ISO/IEC 27037, and C2PA Specification 2.x standards.
    
    Synthesizes normalized detector results, manages evidence family correlation,
    executes the deterministic screening decision engine, and generates composite heatmaps.
    """
    ENGINE_VERSION = "2026.2-v2.1-unvalidated"

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
        Synthesizes raw and normalized forensic signals into uncalibrated screening assessments,
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

                # Missing values remain unknown; a status must not invent a score or confidence.
                score = t.score
                conf = t.confidence

                detector_results.append(
                    DetectorResult(
                        detector_name=t.method,
                        detector_version=t.version,
                        status=status_str,
                        score=score,
                        confidence=conf,
                        evidence_strength=ForensicCalibrator.get_evidence_strength(score, conf),
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
        has_camera_exif = image_char.get("has_camera_exif", False)
        metadata_software = extracted_metadata.get("Software") or jpeg_analytics.get("software_fingerprint") or "Unknown"

        # 7. Answer the Four Independent Forensic Questions (ISO/IEC 27037)
        # Q1: Origin
        if is_screen_capture:
            q1_origin = "Direct Digital Screen Rendering (Display Interface Buffer)"
            origin_code = "SCREEN_CAPTURE"
        elif has_camera_exif:
            make = image_char.get("camera_make") or extracted_metadata.get("Make", "Camera")
            model = image_char.get("camera_model") or extracted_metadata.get("Model", "")
            q1_origin = f"Camera make/model metadata is present ({make} {model}); optical capture is not verified.".strip()
            origin_code = "CAMERA_METADATA_PRESENT"
        elif document_analytics.get("document_type") in ["pdf", "office_openxml"]:
            q1_origin = f"Digital Document Structure ({document_analytics.get('document_type').upper()})"
            origin_code = "DOCUMENT_CONTAINER"
        elif ai_declared or any(d.detector == "ai_generative_classifier" for d in decision_output.decisive_observations):
            q1_origin = "Algorithmic Latent Diffusion / Neural Decoder Synthesis"
            origin_code = "AI_LATENT_SYNTHESIS"
        else:
            q1_origin = "Unknown Digital Source (Metadata Stripped or Web Exported)"
            origin_code = "UNKNOWN"

        # Q2: Integrity
        copymove_decisive = any("copy_move" in d.detector for d in decision_output.decisive_observations)
        splice_decisive = any("splicing" in d.detector for d in decision_output.decisive_observations)

        if copymove_decisive:
            q2_integrity = "Potential copy-move indicator: duplicated regions require examiner verification."
            integrity_code = "COPY_MOVE_INDICATOR_DETECTED"
        elif splice_decisive:
            q2_integrity = "Potential splicing indicator: composite boundary anomaly requires examiner verification."
            integrity_code = "SPLICING_INDICATOR_DETECTED"
        elif decision_output.final_assessment == "MANIPULATION_INDICATORS_DETECTED":
            q2_integrity = "Potential manipulation indicators detected; examiner verification required."
            integrity_code = "MANIPULATION_INDICATORS_DETECTED"
        elif c2pa_present and signature_valid and not ai_declared:
            q2_integrity = "A provenance signature validated for its stated claims; this does not prove all image content is unaltered."
            integrity_code = "PROVENANCE_SIGNATURE_VALIDATED"
        elif decision_output.final_assessment == "NO_MANIPULATION_INDICATORS_DETECTED":
            q2_integrity = "No manipulation indicators detected by applicable methods; this is not proof of an unaltered file."
            integrity_code = "NO_INDICATORS_DETECTED"
        else:
            q2_integrity = "Inconclusive: Bitstream Preserved without Decisive Alteration Markers"
            integrity_code = "INCONCLUSIVE"

        # Q3: Generation
        if ai_declared:
            q3_generation = "A C2PA manifest declares an AI-related action; verify claim scope, signer, and trust chain."
            generation_code = "AI_DECLARED"
        elif decision_output.final_assessment == "AI_GENERATION_INDICATORS_DETECTED":
            q3_generation = "AI-generation indicators detected by heuristic screening; no probability or generation attribution is established."
            generation_code = "AI_GENERATION_INDICATORS_DETECTED"
        elif is_screen_capture:
            q3_generation = "Human Interaction: Direct Operating System Interface Render"
            generation_code = "SCREEN_RENDER"
        elif has_camera_exif:
            q3_generation = "Indeterminate: Camera metadata is present but does not establish physical capture or generation method."
            generation_code = "INDETERMINATE_CAMERA_METADATA"
        else:
            q3_generation = "Generation method is indeterminate from the available screening evidence."
            generation_code = "CONVENTIONAL_DIGITAL"

        # Q4: Transformation
        transformations: List[str] = []
        if is_screen_capture:
            transformations.append("Screenshot-like characteristics observed")
        if jpeg_analytics.get("double_compression_suspected"):
            transformations.append(f"JPEG recompression indicator (estimated quality parameter {jpeg_analytics.get('estimated_quality')})")
        if copymove_decisive:
            transformations.append("Copy-move indicator observed; examiner confirmation required")
        if splice_decisive:
            transformations.append("Splicing indicator observed; examiner confirmation required")
        if "photoshop" in str(metadata_software).lower():
            transformations.append("Software metadata references Adobe Photoshop; metadata is mutable and not independently verified")
        if not transformations:
            transformations.append("No transformation indicator was emitted by the applicable screening methods; completeness is limited by detector coverage.")
        q4_transformation = "; ".join(transformations)

        # 8. Build Explainability Evidentiary Hierarchy
        ranked_evidence: List[Dict[str, str]] = []
        for dec in decision_output.decisive_observations:
            ranked_evidence.append({
                "level": "DECISIVE",
                "item": f"[{dec.detector}] {dec.finding}",
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
                "has_camera_exif": has_camera_exif,
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
