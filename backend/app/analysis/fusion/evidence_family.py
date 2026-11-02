from typing import Dict, List, Any
from app.schemas.examination import (
    DetectorResult,
    DetectorStatus,
    EvidenceStrength,
    EvidenceFamilyType,
    EvidenceFamilySummary,
)


class EvidenceFamilyManager:
    """
    Evidence Family Grouping & Correlation Control Engine.
    Prevents artificial inflation of tampering confidence by grouping correlated
    forensic detectors (e.g. noise residual + SRM + wavelet residual + spectral decay)
    into unified evidence families with inter-method correlation discounting.
    """
    VERSION = "2.0.0"

    # Detector-to-Family Mapping
    DETECTOR_FAMILY_MAP = {
        "cryptographic_and_perceptual_hashing": EvidenceFamilyType.INTEGRITY.value,
        "sha256_integrity": EvidenceFamilyType.INTEGRITY.value,
        "c2pa_provenance": EvidenceFamilyType.PROVENANCE.value,
        "metadata_examination": EvidenceFamilyType.PROVENANCE.value,
        "error_level_analysis": EvidenceFamilyType.COMPRESSION.value,
        "jpeg_quantization_analysis": EvidenceFamilyType.COMPRESSION.value,
        "noise_residual_analysis": EvidenceFamilyType.RESIDUAL.value,
        "srm_wavelet_analysis": EvidenceFamilyType.RESIDUAL.value,
        "fourier_spectral_analysis": EvidenceFamilyType.RESIDUAL.value,
        "copy_move_forgery_detection": EvidenceFamilyType.MANIPULATION.value,
        "image_splicing_detector": EvidenceFamilyType.MANIPULATION.value,
        "ai_generative_classifier": EvidenceFamilyType.AI_ML.value,
        "lighting_consistency_analysis": EvidenceFamilyType.PHYSICAL_CONSISTENCY.value,
        "document_typography_and_alignment": EvidenceFamilyType.DOCUMENT_CONTAINER.value,
        "document_forensics": EvidenceFamilyType.DOCUMENT_CONTAINER.value,
        "image_consistency_checks": EvidenceFamilyType.INTEGRITY.value,
    }

    # Reliability weights are intentionally disabled until estimated and
    # validated on an independent representative dataset.
    FAMILY_WEIGHTS = {}

    @classmethod
    def group_detector_results(
        cls, detector_results: List[DetectorResult]
    ) -> Dict[str, EvidenceFamilySummary]:
        """
        Groups raw detector results into structured evidence families, applies correlation
        discounting, and evaluates intra-family consensus.
        """
        family_buckets: Dict[str, List[DetectorResult]] = {}
        for res in detector_results:
            fam = cls.DETECTOR_FAMILY_MAP.get(res.detector_name, EvidenceFamilyType.RESIDUAL.value)
            if fam not in family_buckets:
                family_buckets[fam] = []
            family_buckets[fam].append(res)

        family_summaries: Dict[str, EvidenceFamilySummary] = {}

        for fam_name, members in family_buckets.items():
            pos_members = [m for m in members if m.status == DetectorStatus.POSITIVE.value]
            neg_members = [m for m in members if m.status == DetectorStatus.NEGATIVE.value]
            inconcl_members = [m for m in members if m.status == DetectorStatus.INCONCLUSIVE.value]
            not_appl_members = [m for m in members if m.status == DetectorStatus.NOT_APPLICABLE.value]
            error_members = [m for m in members if m.status == DetectorStatus.ERROR.value]

            # Correlation Discounting for Residual Family:
            # If multiple residual detectors trigger, their aggregate score is computed
            # using bounded diminishing returns: S_agg = max(scores) + 0.3 * second_highest
            # to strictly prevent treating them as 3 independent witnesses!
            scores = sorted([m.score for m in pos_members if m.score is not None], reverse=True)
            if not scores:
                aggregate_score = 0.05
            elif len(scores) == 1:
                aggregate_score = scores[0]
            else:
                # Diminishing returns formula
                aggregate_score = min(1.0, scores[0] + 0.25 * scores[1] + (0.10 * scores[2] if len(scores) > 2 else 0.0))

            # Determine family status
            if len(pos_members) > 0 and aggregate_score >= 0.60:
                fam_status = "SUPPORTING_TAMPERING"
                summary_str = f"{len(pos_members)} detector(s) indicate anomaly (aggregate score {aggregate_score:.2f})."
            elif len(error_members) > 0 and not pos_members:
                fam_status = "ERROR"
                summary_str = f"{len(error_members)} detector(s) failed and {len(neg_members)} returned no-indicator observations; failure is not negative evidence."
            elif len(neg_members) > 0 and len(pos_members) == 0:
                fam_status = "NO_INDICATOR_OBSERVED"
                summary_str = f"{len(neg_members)} detector(s) returned negative screening observations; this does not establish authenticity."
            elif len(not_appl_members) == len(members):
                fam_status = "NOT_APPLICABLE"
                summary_str = "All member detectors determined not applicable for specimen class."
            elif len(pos_members) > 0 and len(neg_members) > 0:
                fam_status = "CONTRADICTORY"
                summary_str = f"Mixed observations: {len(pos_members)} positive vs {len(neg_members)} negative."
            else:
                fam_status = "INCONCLUSIVE"
                summary_str = f"{len(inconcl_members)} inconclusive and {len(error_members)} error result(s); errors are not negative evidence."

            family_summaries[fam_name] = EvidenceFamilySummary(
                family=fam_name,
                status=fam_status,
                aggregate_score=round(aggregate_score, 3),
                weight=1.0,
                member_detectors=[m.detector_name for m in members],
                findings_summary=summary_str,
            )

        return family_summaries

