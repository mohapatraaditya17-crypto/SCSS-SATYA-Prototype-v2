from typing import Any, Dict, List

from app.schemas.examination import (
    DecisiveObservation,
    DecisionEngineOutput,
    DetectorResult,
    DetectorStatus,
    EvidenceFamilySummary,
    EvidenceStrength,
    TechnicalAssessment,
)


class ForensicDecisionEngine:
    """
    Conservative screening decision engine.

    This engine emits technical screening categories, not authenticity verdicts.
    Confidence remains null until a detector-specific calibrator is validated
    against an independent, representative, adjudicated dataset.
    """

    RULES_VERSION = "2026.2-v2.1-unvalidated"
    DEFAULT_PROFILE = "unvalidated-screening"

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
        positive_detectors: List[str] = []
        positive_families = [
            name
            for name, family in evidence_families.items()
            if family.status == "SUPPORTING_TAMPERING"
        ]

        for result in detector_results:
            name = result.detector_name
            if result.status == DetectorStatus.NOT_APPLICABLE.value:
                not_applicable.append(name)
            elif result.status == DetectorStatus.ERROR.value:
                errors.append(name)
            elif result.status == DetectorStatus.INCONCLUSIVE.value:
                inconclusive.append(name)
            elif result.status == DetectorStatus.POSITIVE.value:
                positive_detectors.append(name)
                # Raw scores may prioritize review, but are not probability or confidence.
                reason = result.technical_reason or f"{name} reported a screening anomaly."
                supporting.append(f"{name}: {reason}")

                if name in {
                    "copy_move_forgery_detection",
                    "image_splicing_detector",
                    "ai_generative_classifier",
                    "document_typography_and_alignment",
                }:
                    decisive.append(
                        DecisiveObservation(
                            detector=name,
                            finding=(
                                "Screening indicator requires examiner verification: "
                                f"{reason}"
                            ),
                            confidence=None,
                            region=result.affected_regions[0]
                            if result.affected_regions
                            else None,
                        )
                    )

        coverage = image_characterization.get("coverage", {})
        applicable_count = sum(
            1 for result in detector_results if result.applicable
        )
        executed_count = sum(
            1
            for result in detector_results
            if result.status
            not in {
                DetectorStatus.NOT_APPLICABLE.value,
                DetectorStatus.ERROR.value,
            }
        )

        has_provenance_conflict = any(
            family.status in {"CONTRADICTORY", "ERROR"}
            for family in evidence_families.values()
        )
        explicit_provenance_verified = bool(
            image_characterization.get("cryptographic_provenance_verified")
        )

        if errors and not executed_count:
            assessment = TechnicalAssessment.INSUFFICIENT_EVIDENCE.value
            strength = EvidenceStrength.NONE.value
            rationale = (
                "No applicable detector completed successfully. "
                "Analysis errors prevented a usable screening interpretation."
            )
        elif has_provenance_conflict:
            assessment = TechnicalAssessment.PROVENANCE_CONFLICT.value
            strength = EvidenceStrength.LOW.value
            rationale = (
                "Conflicting or erroneous provenance-family observations require "
                "manual verification of the manifest, signature chain, and source."
            )
        elif explicit_provenance_verified:
            assessment = TechnicalAssessment.PROVENANCE_VERIFIED.value
            strength = EvidenceStrength.MODERATE.value
            rationale = (
                "A provenance verification flag is present. This is limited to the "
                "verified provenance assertion and does not establish that all image "
                "content is unaltered."
            )
        elif "ai_generative_classifier" in positive_detectors:
            assessment = TechnicalAssessment.AI_GENERATION_INDICATORS_DETECTED.value
            strength = EvidenceStrength.LOW.value
            rationale = (
                "Statistical AI-generation screening indicators were observed. "
                "This heuristic is not a probability and requires independent "
                "verification using provenance, source context, and examiner review."
            )
        elif positive_detectors:
            assessment = TechnicalAssessment.MANIPULATION_INDICATORS_DETECTED.value
            strength = (
                EvidenceStrength.STRONG.value
                if len(positive_families) >= 2
                else EvidenceStrength.LOW.value
            )
            rationale = (
                "One or more detectors reported potential manipulation-related "
                "indicators. The findings are screening leads only; correlated "
                "methods are not independent witnesses and require examiner review."
            )
        elif applicable_count == 0 or (errors and not executed_count):
            assessment = TechnicalAssessment.INSUFFICIENT_EVIDENCE.value
            strength = EvidenceStrength.NONE.value
            rationale = (
                "There is insufficient applicable detector output to support a "
                "screening interpretation."
            )
        elif inconclusive and not positive_detectors:
            assessment = TechnicalAssessment.INCONCLUSIVE.value
            strength = EvidenceStrength.NONE.value
            rationale = (
                "Applicable screening methods did not yield a decisive indicator. "
                "Absence of detected indicators does not establish authenticity."
            )
        else:
            assessment = TechnicalAssessment.NO_MANIPULATION_INDICATORS_DETECTED.value
            strength = EvidenceStrength.NONE.value
            rationale = (
                "No manipulation indicators were detected by the applicable methods. "
                "This does not establish authenticity or prove the source is unaltered."
            )

        if errors:
            rationale += " One or more detector errors occurred and reduce coverage."
        if not_applicable:
            rationale += (
                f" {len(not_applicable)} detector(s) were not applicable to this specimen."
            )

        return DecisionEngineOutput(
            final_assessment=assessment,
            decision_confidence=None,
            evidence_strength=strength,
            human_review_required=True,
            decisive_observations=decisive,
            supporting_observations=supporting,
            contradictory_observations=contradictory,
            inconclusive_tests=inconclusive,
            not_applicable_tests=not_applicable,
            decision_rationale=rationale,
            evidence_families=evidence_families,
            rules_version=cls.RULES_VERSION,
            threshold_profile=threshold_profile,
        )
