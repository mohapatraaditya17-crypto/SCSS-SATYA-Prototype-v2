from typing import Optional


class ForensicCalibrator:
    """
    Calibration is intentionally unavailable.

    Raw detector scores are not probabilities. A calibrated value may only be
    introduced after independent, adjudicated v2 validation and documented
    reliability/calibration analysis.
    """

    VERSION = "3.0.0-unvalidated"
    IS_CALIBRATED = False

    @classmethod
    def calibrate_score(cls, detector_name: str, raw_score: Optional[float]) -> None:
        return None

    @classmethod
    def get_evidence_strength(
        cls, score: Optional[float], confidence: Optional[float]
    ) -> str:
        return "NONE"
