from typing import List, Dict, Any
from app.schemas.examination import (
    DetectorResult, DetectorStatus, EvidenceStrength, TechnicalAssessment,
    DecisiveObservation, DecisionEngineOutput, EvidenceFamilySummary,
)


class ForensicDecisionEngine:
    """Conservative screening engine; it does not issue final forensic opinions."""
    RULES_VERSION = "2026.3-v2.1"
    DEFAULT_PROFILE = "conservative-screening-no-calibration"

    @classmethod
    def evaluate(
        cls,
        detector_results: List[DetectorResult],
        evidence_families: Dict[str, EvidenceFamilySummary],
        image_characterization: Dict[str, Any],
        threshold_profile: str = DEFAULT_PROFILE,
    ) -> DecisionEngineOutput:
        decisive: List[DecisiveObservation] = []
        supporting: List[str] = []
        contradictory: List[str] = []
        inconclusive: List[str] = []
        not_applicable: List[str] = []
        errors: List[str] = []

        for result in detector_results:
            name = result.detector_name
            if result.status == DetectorStatus.NOT_APPLICABLE.value or not result.applicable:
                not_applicable.append(name)
                continue
            if result.status == DetectorStatus.ERROR.value:
                errors.append(name)
                continue
            if result.status == DetectorStatus.INCONCLUSIVE.value:
                inconclusive.append(name)
                continue
            if result.status != DetectorStatus.POSITIVE.value:
                continue

            reason = result.technical_reason or f"{name} reported a positive screening indicator."
            # A missing confidence value cannot satisfy a decisive threshold.
            if name == "copy_move_forgery_detection" and result.score is not None and result.score >= 0.70 and result.confidence is not None and result.confidence >= 0.75:
                decisive.append(DecisiveObservation(
                    detector=name,
                    finding="Copy-move screening indicator: coherent duplicated-region evidence reported; examiner verification required.",
                    confidence=result.confidence,
                    region=result.affected_regions[0] if result.affected_regions else None,
                ))
            elif name == "image_splicing_detector" and result.score is not None and result.score >= 0.60 and result.confidence is not None and result.confidence >= 0.70:
                decisive.append(DecisiveObservation(
                    detector=name,
                    finding="Splicing screening indicator: regional boundary/statistical mismatch reported; examiner verification required.",
                    confidence=result.confidence,
                    region=result.affected_regions[0] if result.affected_regions else None,
                ))
            elif name == "document_typography_and_alignment" and result.score is not None and result.score >= 0.70 and result.confidence is not None and result.confidence >= 0.70:
                decisive.append(DecisiveObservation(
                    detector=name,
                    finding="Document typography/alignment anomaly reported; examiner verification required.",
                    confidence=result.confidence,
                    region=result.affected_regions[0] if result.affected_regions else None,
                ))
            elif name == "ai_generative_classifier":
                supporting.append(f"{name}: statistical synthetic-indicator heuristic, not a validated ML classifier. {reason}")
            else:
                supporting.append(f"{name}: {reason}")

        tamper_families = [
            key for key, summary in evidence_families.items()
            if summary.status == "SUPPORTING_TAMPERING"
        ]
        applicable = [
            r for r in detector_results
            if r.applicable and r.status != DetectorStatus.NOT_APPLICABLE.value
        ]
        successful = [
            r for r in applicable
            if r.status in {
                DetectorStatus.POSITIVE.value,
                DetectorStatus.NEGATIVE.value,
                DetectorStatus.INCONCLUSIVE.value,
            }
        ]
        coverage = len(successful) / len(applicable) if applicable else None
        error_majority = bool(applicable) and len(errors) >= max(2, (len(applicable) + 1) // 2)
        contradictory_families = any(v.status == "CONTRADICTORY" for v in evidence_families.values())

        if error_majority:
            assessment = TechnicalAssessment.INSUFFICIENT_EVIDENCE.value
            strength = EvidenceStrength.NONE.value
            rationale = "A substantial portion of applicable detectors failed. Errors are coverage failures and were not treated as negative evidence."
        elif contradictory_families:
            assessment = TechnicalAssessment.INCONCLUSIVE.value
            strength = EvidenceStrength.LOW.value
            rationale = "Evidence-family results are contradictory; automated screening cannot resolve the conflict."
        elif decisive:
            assessment = TechnicalAssessment.MANIPULATION_INDICATORS_DETECTED.value
            strength = EvidenceStrength.STRONG.value
            rationale = "One or more configured spatial/document detectors crossed conservative screening thresholds. Independent examiner verification is required."
        elif len(tamper_families) >= 2:
            assessment = TechnicalAssessment.MANIPULATION_INDICATORS_DETECTED.value
            strength = EvidenceStrength.MODERATE.value
            rationale = f"Positive screening indicators were reported across {len(tamper_families)} evidence families. Family counts are not calibrated probabilities or proof of independence."
        elif any("ai_generative_classifier" in item for item in supporting):
            assessment = TechnicalAssessment.AI_GENERATION_INDICATORS_DETECTED.value
            strength = EvidenceStrength.LOW.value
            rationale = "Statistical features warrant examination for synthetic generation; the heuristic is not a validated AI classifier."
        elif image_characterization.get("cryptographic_provenance_verified"):
            assessment = TechnicalAssessment.PROVENANCE_VERIFIED.value
            strength = EvidenceStrength.MODERATE.value
            rationale = "Cryptographic provenance validation succeeded for the supplied manifest. This does not prove depicted events are true or exclude edits outside the signed claim history."
        elif errors:
            assessment = TechnicalAssessment.INSUFFICIENT_EVIDENCE.value
            strength = EvidenceStrength.NONE.value
            rationale = "One or more applicable detectors failed. Review execution errors and examination coverage."
        elif supporting or inconclusive:
            assessment = TechnicalAssessment.INCONCLUSIVE.value
            strength = EvidenceStrength.LOW.value if supporting else EvidenceStrength.NONE.value
            rationale = "No decisive screening result. Review supporting observations, inconclusive tests, and limitations."
        else:
            assessment = TechnicalAssessment.NO_MANIPULATION_INDICATORS_DETECTED.value
            strength = EvidenceStrength.NONE.value
            rationale = "No manipulation indicators were reported by completed applicable screening methods. Absence of detected indicators is not evidence of authenticity."

        return DecisionEngineOutput(
            final_assessment=assessment,
            decision_confidence=0.0,  # No calibrated decision probability is available.
            evidence_strength=strength,
            human_review_required=True,
            decisive_observations=decisive,
            supporting_observations=supporting,
            contradictory_observations=contradictory,
            inconclusive_tests=inconclusive,
            not_applicable_tests=not_applicable,
            error_tests=errors,
            applicable_detector_count=len(applicable),
            successful_detector_count=len(successful),
            detector_error_count=len(errors),
            coverage_score=round(coverage, 4) if coverage is not None else None,
            decision_rationale=rationale,
            evidence_families=evidence_families,
            rules_version=cls.RULES_VERSION,
            threshold_profile=threshold_profile,
        )
