from app.analysis.fusion.decision_engine import ForensicDecisionEngine
from app.analysis.fusion.evidence_family import EvidenceFamilyManager
from app.schemas.examination import (
    DetectorResult,
    DetectorStatus,
    EvidenceFamilySummary,
    EvidenceStrength,
    TechnicalAssessment,
)


def _detector(name, status, **kwargs):
    return DetectorResult(
        detector_name=name,
        detector_version="test",
        status=status,
        **kwargs,
    )


def test_positive_copy_move_is_a_screening_indicator_not_a_verdict():
    detector = _detector(
        "copy_move_forgery_detection",
        DetectorStatus.POSITIVE.value,
        score=0.88,
        confidence=0.90,
    )
    families = EvidenceFamilyManager.group_detector_results([detector])
    decision = ForensicDecisionEngine.evaluate([detector], families, {})

    assert decision.final_assessment == TechnicalAssessment.MANIPULATION_INDICATORS_DETECTED.value
    assert decision.decision_confidence is None
    assert decision.human_review_required is True
    assert len(decision.decisive_observations) == 1
    assert "examiner verification" in decision.decisive_observations[0].finding.lower()


def test_camera_exif_and_negative_detectors_do_not_establish_authenticity():
    detectors = [
        _detector("noise_residual_analysis", DetectorStatus.NEGATIVE.value),
        _detector("copy_move_forgery_detection", DetectorStatus.NEGATIVE.value),
        _detector("image_splicing_detector", DetectorStatus.NEGATIVE.value),
        _detector("ai_generative_classifier", DetectorStatus.NEGATIVE.value),
    ]
    families = EvidenceFamilyManager.group_detector_results(detectors)
    decision = ForensicDecisionEngine.evaluate(
        detectors,
        families,
        {"has_camera_exif": True, "camera_make": "Canon", "camera_model": "EOS R5"},
    )

    assert decision.final_assessment == TechnicalAssessment.NO_MANIPULATION_INDICATORS_DETECTED.value
    assert decision.decision_confidence is None
    assert decision.human_review_required is True
    assert "does not establish authenticity" in decision.decision_rationale.lower() or "does not establish authenticity" in decision.decision_rationale.lower()


def test_single_weak_residual_indicator_does_not_become_likely_tampered():
    detector = _detector(
        "noise_residual_analysis",
        DetectorStatus.POSITIVE.value,
        score=0.55,
        confidence=0.60,
    )
    families = EvidenceFamilyManager.group_detector_results([detector])
    decision = ForensicDecisionEngine.evaluate([detector], families, {})

    assert decision.final_assessment == TechnicalAssessment.MANIPULATION_INDICATORS_DETECTED.value
    assert decision.decision_confidence is None
    assert decision.human_review_required is True
    assert decision.evidence_strength == EvidenceStrength.LOW.value


def test_ai_heuristic_indicator_is_not_a_probability():
    detector = _detector(
        "ai_generative_classifier",
        DetectorStatus.POSITIVE.value,
        score=0.80,
        confidence=None,
    )
    families = EvidenceFamilyManager.group_detector_results([detector])
    decision = ForensicDecisionEngine.evaluate([detector], families, {})

    assert decision.final_assessment == TechnicalAssessment.AI_GENERATION_INDICATORS_DETECTED.value
    assert decision.decision_confidence is None
    assert decision.human_review_required is True


def test_detector_error_and_no_applicable_outputs_are_reported():
    detector = _detector(
        "copy_move_forgery_detection",
        DetectorStatus.ERROR.value,
        score=None,
        confidence=None,
        error_code="ANALYZER_FAILED",
    )
    families = EvidenceFamilyManager.group_detector_results([detector])
    decision = ForensicDecisionEngine.evaluate([detector], families, {})

    assert decision.final_assessment == TechnicalAssessment.INSUFFICIENT_EVIDENCE.value
    assert decision.decision_confidence is None
    assert decision.human_review_required is True
    assert "error" in decision.decision_rationale.lower()


def test_provenance_conflict_is_not_a_clean_or_tampered_verdict():
    family = EvidenceFamilySummary(
        family="PROVENANCE",
        status="CONTRADICTORY",
        aggregate_score=0.0,
        weight=0.0,
    )
    decision = ForensicDecisionEngine.evaluate([], {"PROVENANCE": family}, {})

    assert decision.final_assessment == TechnicalAssessment.PROVENANCE_CONFLICT.value
    assert decision.decision_confidence is None
    assert decision.human_review_required is True
