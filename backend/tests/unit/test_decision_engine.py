import pytest
from app.schemas.examination import (
    DetectorResult, DetectorStatus, EvidenceStrength, TechnicalAssessment, EvidenceRegion,
)
from app.analysis.fusion.evidence_family import EvidenceFamilyManager
from app.analysis.fusion.decision_engine import ForensicDecisionEngine


def test_strong_copy_move_is_a_screening_indicator_not_final_opinion():
    region = EvidenceRegion(x=50, y=50, width=80, height=80, confidence=0.92, detector="copy_move_forgery_detection")
    result = DetectorResult(
        detector_name="copy_move_forgery_detection",
        detector_version="2.1.0",
        status=DetectorStatus.POSITIVE.value,
        score=0.88,
        confidence=0.90,
        evidence_strength=EvidenceStrength.STRONG.value,
        affected_regions=[region],
    )
    families = EvidenceFamilyManager.group_detector_results([result])
    decision = ForensicDecisionEngine.evaluate([result], families, {"image_class": "PHOTOGRAPH"})
    assert decision.final_assessment == TechnicalAssessment.MANIPULATION_INDICATORS_DETECTED.value
    assert decision.human_review_required is True
    assert len(decision.decisive_observations) == 1


def test_camera_metadata_and_negative_detectors_never_establish_authenticity():
    detectors = [
        DetectorResult(detector_name="error_level_analysis", detector_version="2.1.0", status="NEGATIVE", score=0.05),
        DetectorResult(detector_name="noise_residual_analysis", detector_version="2.1.0", status="NEGATIVE", score=0.05),
        DetectorResult(detector_name="copy_move_forgery_detection", detector_version="2.1.0", status="NEGATIVE", score=0.02),
        DetectorResult(detector_name="image_splicing_detector", detector_version="2.1.0", status="NEGATIVE", score=0.04),
    ]
    families = EvidenceFamilyManager.group_detector_results(detectors)
    decision = ForensicDecisionEngine.evaluate(
        detectors, families, {"has_camera_exif": True, "camera_metadata_present": True, "image_class": "PHOTOGRAPH"}
    )
    assert decision.final_assessment == TechnicalAssessment.NO_MANIPULATION_INDICATORS_DETECTED.value
    assert "authentic" not in decision.decision_rationale.lower()


def test_single_weak_residual_signal_is_inconclusive():
    detectors = [
        DetectorResult(detector_name="noise_residual_analysis", detector_version="2.1.0", status="POSITIVE", score=0.55, confidence=0.60),
        DetectorResult(detector_name="copy_move_forgery_detection", detector_version="2.1.0", status="NEGATIVE", score=0.02),
    ]
    decision = ForensicDecisionEngine.evaluate(detectors, EvidenceFamilyManager.group_detector_results(detectors), {"image_class": "PHOTOGRAPH"})
    assert decision.final_assessment == TechnicalAssessment.INCONCLUSIVE.value


def test_error_is_coverage_failure_not_negative_evidence():
    detectors = [
        DetectorResult(detector_name="noise_residual_analysis", detector_version="2.1.0", status="ERROR", applicable=True),
        DetectorResult(detector_name="copy_move_forgery_detection", detector_version="2.1.0", status="NEGATIVE", score=0.02),
    ]
    decision = ForensicDecisionEngine.evaluate(detectors, EvidenceFamilyManager.group_detector_results(detectors), {})
    assert decision.error_tests == ["noise_residual_analysis"]
    assert decision.detector_error_count == 1
    assert decision.coverage_score == 0.5
    assert decision.final_assessment == TechnicalAssessment.INSUFFICIENT_EVIDENCE.value


def test_missing_confidence_does_not_become_decisive():
    result = DetectorResult(
        detector_name="copy_move_forgery_detection",
        detector_version="2.1.0",
        status="POSITIVE",
        score=0.99,
        confidence=None,
    )
    decision = ForensicDecisionEngine.evaluate([result], EvidenceFamilyManager.group_detector_results([result]), {})
    assert decision.decisive_observations == []
    assert decision.final_assessment == TechnicalAssessment.MANIPULATION_INDICATORS_DETECTED.value
