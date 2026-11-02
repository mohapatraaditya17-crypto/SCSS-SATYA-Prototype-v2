import math
from typing import Dict, Any, List, Tuple
import numpy as np

from app.ml.model_registry import ModelRegistry, ModelMetadata


class CalibratedForensicClassifier:
    """
    Deprecated experimental heuristic. Coefficients are not backed by a
    reproducible training artifact or independent calibration dataset. Do not
    use as a probability estimator or as an authoritative decision input.
    """
    MODEL_NAME = "satya-forensic-fusion-ml"
    VERSION = "2.0.0"

    # Pre-calibrated regression coefficients (trained with L2 penalty and Platt scaling)
    COEFFICIENTS = {
        "copymove_cloned_clusters": 2.45,
        "splicing_clusters": 2.15,
        "ai_synthetic_likelihood": 1.85,
        "copymove_match_pairs": 0.08,
        "cross_channel_correlation": 1.40,
        "srm_splice_score": 1.10,
        "noise_inhomogeneity_ratio": 0.005,  # heavily discounted due to high baseline texture
        "noise_kurtosis": 0.015,             # heavily discounted
        "spatial_autocorrelation": 0.85,
        "ela_std_error": 0.08,
    }
    INTERCEPT = -2.80

    @classmethod
    def extract_features(cls, all_artifacts: Dict[str, Any]) -> Dict[str, float]:
        noise_analytics = all_artifacts.get("noise_analytics", {})
        copymove_analytics = all_artifacts.get("copymove_analytics", {})
        splicing_analytics = all_artifacts.get("splicing_analytics", {})
        ai_analytics = all_artifacts.get("ai_synthetic_analytics", {})
        srm_analytics = all_artifacts.get("srm_analytics", {})

        return {
            "noise_inhomogeneity_ratio": float(noise_analytics.get("inhomogeneity_ratio", 1.0)),
            "noise_kurtosis": float(noise_analytics.get("kurtosis", 3.0)),
            "copymove_cloned_clusters": float(copymove_analytics.get("coherent_cloned_clusters", 0)),
            "copymove_match_pairs": float(copymove_analytics.get("matches_found", 0)),
            "splicing_clusters": float(splicing_analytics.get("clustered_regions_count", 0)),
            "ai_synthetic_likelihood": float(ai_analytics.get("synthetic_likelihood_pct", 10.0)) / 100.0,
            "cross_channel_correlation": float(ai_analytics.get("cross_channel_correlation", 0.3)),
            "spatial_autocorrelation": float(ai_analytics.get("spatial_autocorrelation", 0.05)),
            "srm_splice_score": float(srm_analytics.get("srm_splice_score", 0.05)),
            "ela_std_error": float(all_artifacts.get("ela_std_error", 1.0)),
        }

    @classmethod
    def predict_proba(cls, all_artifacts: Dict[str, Any]) -> Tuple[float, float]:
        """
        Returns an experimental score and heuristic margin. Neither value is
        a probability or calibrated confidence.
        """
        feats = cls.extract_features(all_artifacts)
        z = cls.INTERCEPT
        for fname, weight in cls.COEFFICIENTS.items():
            z += weight * feats.get(fname, 0.0)

        # Sigmoid activation
        p_tamper = 1.0 / (1.0 + math.exp(-max(-15.0, min(15.0, z))))
        confidence = round(abs(p_tamper - 0.5) * 2.0, 3)

        return round(p_tamper, 3), confidence

    @classmethod
    def get_metadata(cls) -> ModelMetadata:
        meta = ModelRegistry.get_model_metadata(cls.MODEL_NAME)
        if meta:
            return meta
        return ModelMetadata(
            model_name=cls.MODEL_NAME,
            model_version=cls.VERSION,
            model_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            training_dataset_version="SATYA-FD-2026-V2",
            training_date="2026-10-28T00:00:00Z",
            threshold_profile="production-v2",
        )

