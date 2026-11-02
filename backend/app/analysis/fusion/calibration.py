"""Calibration safeguards for SATYA.

Raw detector scores are not probabilities. A probability calibrator must be
fitted on a representative held-out calibration set and versioned with its
dataset and calibration artifact. No such artifact is currently configured.
"""
from typing import Optional


class ForensicCalibrator:
    VERSION = "3.0.0-unvalidated"
    CALIBRATION_AVAILABLE = False

    @classmethod
    def calibrate_score(cls, detector_name: str, raw_score: Optional[float]) -> Optional[float]:
        """Return None until an empirical calibration artifact is available."""
        return None

    @classmethod
    def get_evidence_strength(cls, score: Optional[float], confidence: Optional[float] = None) -> str:
        """Map a present raw score to an ordinal band; never infer confidence."""
        if score is None:
            return "NONE"
        value = max(0.0, min(1.0, float(score)))
        if value >= 0.80:
            return "VERY_STRONG"
        if value >= 0.65:
            return "STRONG"
        if value >= 0.40:
            return "MODERATE"
        if value >= 0.20:
            return "LOW"
        return "NONE"
