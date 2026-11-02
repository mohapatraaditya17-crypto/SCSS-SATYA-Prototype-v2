from app.schemas.examination import DetectorResult
from app.analysis.fusion.evidence_family import EvidenceFamilyManager


def test_detector_errors_are_not_negative_evidence():
    results = [
        DetectorResult(detector_name="noise_residual_analysis", detector_version="2.1.0", status="ERROR"),
        DetectorResult(detector_name="srm_wavelet_analysis", detector_version="2.1.0", status="ERROR"),
    ]
    families = EvidenceFamilyManager.group_detector_results(results)
    assert families["RESIDUAL"].status == "ERROR"
    assert "failure is not negative evidence" in families["RESIDUAL"].findings_summary


def test_family_weights_are_not_claimed_as_empirical():
    assert EvidenceFamilyManager.FAMILY_WEIGHTS == {}
