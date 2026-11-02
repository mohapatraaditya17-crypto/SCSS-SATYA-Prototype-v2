import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from PIL import Image
import numpy as np
import cv2

from app.core.config import settings
from app.schemas.examination import (
    ScreeningTestResult,
    DetectorResult,
    DetectorStatus,
    EvidenceStrength,
    EvidenceRegion,
)


class AISyntheticAnalyzer:
    METHOD_NAME = "ai_generative_classifier"
    VERSION = "3.0.0-unvalidated"

    @classmethod
    def analyze(
        cls,
        image_path: Path,
        examination_id: str,
        media_type: str,
    ) -> Tuple[ScreeningTestResult, Dict[str, str], Dict[str, Any], DetectorResult]:
        start_time = time.perf_counter()
        observations: List[str] = []
        artifacts: Dict[str, str] = {}
        analytics: Dict[str, Any] = {}
        affected_regions: List[EvidenceRegion] = []
        limitations: List[str] = [
            "AI generation screening evaluates statistical spectral decay, high-frequency residuals, frequency lattice patterns, and cross-channel co-occurrence.",
            "Modern diffusion architectures (Midjourney v6, Stable Diffusion XL, FLUX.1) evolve rapidly and post-processing (noise injection, heavy recompression) may attenuate signatures.",
            "The heuristic score is uncalibrated and is not a probability or confidence estimate; it requires independent validation and examiner review."
        ]

        try:
            with Image.open(image_path) as img:
                # Check for explicit generative metadata in container tags/info
                metadata_ai_found = False
                meta_source = ""
                for k, v in getattr(img, "info", {}).items():
                    val_str = str(v).lower()
                    if any(kw in val_str for kw in ["stable diffusion", "midjourney", "dall-e", "comfyui", "novelai", "flux.1", "civitai", "steps: ", "sampler: "]):
                        metadata_ai_found = True
                        meta_source = f"{k}: {str(v)[:60]}..."
                        break

                rgb = np.array(img.convert("RGB"))
                gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
                height, width = gray.shape

                # 1. Edge-Suppressed Cross-Channel Noise Residual Co-occurrence
                r_ch = rgb[:, :, 0].astype(np.float32)
                g_ch = rgb[:, :, 1].astype(np.float32)
                b_ch = rgb[:, :, 2].astype(np.float32)

                r_res = r_ch - cv2.medianBlur(rgb[:, :, 0], 3).astype(np.float32)
                g_res = g_ch - cv2.medianBlur(rgb[:, :, 1], 3).astype(np.float32)
                b_res = b_ch - cv2.medianBlur(rgb[:, :, 2], 3).astype(np.float32)

                sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
                sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
                grad_mag = np.sqrt(sobel_x ** 2 + sobel_y ** 2)

                flat_mask = (grad_mag < 15.0) & (gray > 10) & (gray < 245)
                if np.sum(flat_mask) > 1000:
                    r_eval = r_res[flat_mask]
                    g_eval = g_res[flat_mask]
                    b_eval = b_res[flat_mask]
                else:
                    r_eval = r_res.ravel()
                    g_eval = g_res.ravel()
                    b_eval = b_res.ravel()

                std_r = float(np.std(r_eval))
                std_g = float(np.std(g_eval))
                std_b = float(np.std(b_eval))

                corr_rg = float(np.corrcoef(r_eval, g_eval)[0, 1]) if std_r > 0 and std_g > 0 else 0.0
                corr_rb = float(np.corrcoef(r_eval, b_eval)[0, 1]) if std_r > 0 and std_b > 0 else 0.0
                corr_gb = float(np.corrcoef(g_eval, b_eval)[0, 1]) if std_g > 0 and std_b > 0 else 0.0
                cross_channel_corr = float((corr_rg + corr_rb + corr_gb) / 3.0)

                # 2. Residual Spatial Autocorrelation
                res_center = r_res[1:-1, 1:-1]
                res_shift_x = r_res[1:-1, 2:]
                res_shift_y = r_res[2:, 1:-1]
                std_c = np.std(res_center)
                if std_c > 1e-4:
                    autocorr_x = float(np.corrcoef(res_center.ravel(), res_shift_x.ravel())[0, 1])
                    autocorr_y = float(np.corrcoef(res_center.ravel(), res_shift_y.ravel())[0, 1])
                    spatial_autocorr = float(max(0.0, (autocorr_x + autocorr_y) / 2.0))
                else:
                    spatial_autocorr = 0.0

                # 3. Spectral Power Decay Slope
                f_transform = np.fft.fftshift(np.fft.fft2(gray))
                psd2d = np.abs(f_transform) ** 2
                cy, cx = height // 2, width // 2
                y_grid, x_grid = np.ogrid[:height, :width]
                dist_matrix = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2).astype(np.int32)
                max_r = min(cy, cx)

                radial_prof = np.zeros(max_r)
                for radius in range(1, max_r):
                    m = (dist_matrix == radius)
                    if np.any(m):
                        radial_prof[radius] = np.mean(psd2d[m])

                freq_range = np.arange(max(2, max_r // 8), max_r // 2)
                valid_vals = radial_prof[freq_range]
                valid_mask = valid_vals > 0

                if np.sum(valid_mask) > 10:
                    log_freq = np.log10(freq_range[valid_mask])
                    log_power = np.log10(valid_vals[valid_mask])
                    slope, _ = np.polyfit(log_freq, log_power, 1)
                    spectral_slope = float(-slope)
                else:
                    spectral_slope = 2.0

                # High-Frequency Lattice Peaks
                hf_mask = dist_matrix > (0.35 * max_r)
                hf_log_psd = np.log(psd2d + 1.0)
                hf_vals = hf_log_psd[hf_mask]
                if len(hf_vals) > 100:
                    hf_threshold = float(np.percentile(hf_vals, 99.5))
                    hf_peak_count = int(np.sum((hf_log_psd > hf_threshold) & hf_mask))
                    hf_peak_density = (hf_peak_count / max(1, len(hf_vals))) * 100.0
                else:
                    hf_peak_count = 0
                    hf_peak_density = 0.0

                # 4. Patch-Level Disparity Analysis
                full_laplacian = cv2.Laplacian(gray, cv2.CV_32F)
                patch_size = 32
                h_patches = max(1, height // patch_size)
                w_patches = max(1, width // patch_size)

                crop_lap = full_laplacian[:h_patches * patch_size, :w_patches * patch_size]
                reshaped = crop_lap.reshape(h_patches, patch_size, w_patches, patch_size)
                patch_scores = np.var(reshaped, axis=(1, 3)).astype(np.float32)

                p_min = float(np.min(patch_scores))
                p_max = float(np.max(patch_scores))
                norm_patch_scores = (patch_scores - p_min) / (p_max - p_min + 1e-4)

                p_mean = np.mean(patch_scores)
                p_std = np.std(patch_scores)
                patch_kurtosis = float(np.mean(((patch_scores - p_mean) / (p_std + 1e-4)) ** 4) - 3.0) if p_std > 1e-4 else 0.0

                # Find localized synthetic patch regions (if any patch > 0.85)
                high_synth_patches = np.where(norm_patch_scores > 0.82)
                for py, px in zip(high_synth_patches[0][:10], high_synth_patches[1][:10]):
                    affected_regions.append(
                        EvidenceRegion(
                            x=int(px * patch_size),
                            y=int(py * patch_size),
                            width=patch_size,
                            height=patch_size,
                            confidence=0.82,
                            detector=cls.METHOD_NAME,
                            label="Localized Synthetic Inpainting / Residual Anomaly",
                        )
                    )

                # 5. Synthesize an uncalibrated statistical heuristic score.
                # Container strings are mutable metadata and are not independently verified.
                if metadata_ai_found:
                    observations.append(f"Unverified AI-related metadata string observed: {meta_source}")
                    if cross_channel_corr > 0.95:
                        c_score = 0.60 + 0.35 * ((cross_channel_corr - 0.95) / 0.05)
                    elif cross_channel_corr > 0.88:
                        c_score = 0.40 + 0.20 * ((cross_channel_corr - 0.88) / 0.07)
                    elif cross_channel_corr > 0.70:
                        c_score = 0.15 + 0.25 * ((cross_channel_corr - 0.70) / 0.18)
                    else:
                        c_score = max(0.02, cross_channel_corr * 0.15)

                    slope_dev = abs(spectral_slope - 2.05)
                    s_score = min(0.35, max(0.0, (slope_dev - 0.35) * 0.5)) if slope_dev > 0.35 else 0.0
                    a_score = min(0.30, max(0.0, (spatial_autocorr - 0.25) * 0.8)) if spatial_autocorr > 0.25 else 0.0
                    p_score = 0.25 if hf_peak_count > 2500 and hf_peak_density > 0.4 else (0.10 if hf_peak_count > 1000 else 0.0)
                    k_score = min(0.15, max(0.0, (patch_kurtosis - 5.0) * 0.02)) if patch_kurtosis > 5.0 else 0.0

                    raw_score = 0.45 * c_score + 0.20 * s_score + 0.15 * a_score + 0.12 * p_score + 0.08 * k_score
                    synthetic_score = min(0.96, max(0.04, raw_score * 1.5))

                synthetic_pct = round(float(synthetic_score * 100.0), 1)

                analytics["raw_heuristic_score_percent"] = synthetic_pct
                analytics["raw_heuristic_score_percent"] = synthetic_pct
                analytics["spectral_decay_slope"] = round(float(spectral_slope), 2)
                analytics["cross_channel_correlation"] = round(float(cross_channel_corr), 3)
                analytics["spatial_autocorrelation"] = round(float(spatial_autocorr), 3)
                analytics["hf_lattice_peaks"] = int(hf_peak_count)
                analytics["patch_kurtosis"] = round(float(patch_kurtosis), 2)
                analytics["metadata_flagged"] = metadata_ai_found
                analytics["metadata_flag_source"] = meta_source if metadata_ai_found else None
                analytics["score_semantics"] = "UNCALIBRATED_HEURISTIC_NOT_PROBABILITY"

                # Generate Visual Artifact
                resized_map = cv2.resize(norm_patch_scores, (width, height), interpolation=cv2.INTER_CUBIC)
                norm_vis = cv2.normalize(resized_map, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                colored_vis = cv2.applyColorMap(norm_vis, cv2.COLORMAP_MAGMA)
                blended = cv2.addWeighted(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), 0.35, colored_vis, 0.65, 0)

                artifact_filename = f"{examination_id}_ai_synthetic.png"
                artifact_path = settings.ARTIFACTS_DIR / artifact_filename
                cv2.imwrite(str(artifact_path), blended)
                artifacts["ai_synthetic_map"] = artifact_filename

                observations.append(f"Raw uncalibrated statistical heuristic score: {synthetic_pct} (not a probability).")
                observations.append(f"Fourier radial spectral decay slope: alpha={spectral_slope:.2f}.")
                observations.append(f"Cross-channel noise residual correlation: {cross_channel_corr:.3f}.")
                observations.append(f"Spatial noise residual autocorrelation: {spatial_autocorr:.3f}.")

                # Exploratory threshold only; this score is not calibrated.
                if synthetic_score >= 0.75:
                    indicator = "indicator_detected"
                    indicator_label = f"AI-generation-related statistical indicators detected (raw heuristic score {synthetic_pct}; uncalibrated)"
                    norm_status = DetectorStatus.POSITIVE.value
                    confidence = None
                    strength = EvidenceStrength.LOW.value
                    explanation = (
                        f"Elevated statistical indicators were observed (raw uncalibrated heuristic score: {synthetic_pct}). "
                        f"Noise residual cross-channel correlation ({cross_channel_corr:.3f}), spatial autocorrelation ({spatial_autocorr:.3f}), "
                        f"and spectral roll-off (alpha={spectral_slope:.2f}) deviate significantly from physical optical sensor physics, "
                        "these observations are not specific enough to attribute the image to a generative model without independent corroboration."
                    )
                elif synthetic_score >= 0.45:
                    indicator = "inconclusive"
                    indicator_label = f"Inconclusive / Mixed Indicators ({synthetic_pct}%)"
                    norm_status = DetectorStatus.INCONCLUSIVE.value
                    confidence = None
                    strength = EvidenceStrength.NONE.value
                    explanation = (
                        f"Moderate raw statistical heuristic score ({synthetic_pct}; uncalibrated). "
                        "Image exhibits partial spectral flattening or atypical noise correlation, but insufficient to conclusively distinguish "
                        "between synthetic generation, digital rendering, and heavy recompression smoothing."
                    )
                else:
                    indicator = "no_indicator_detected"
                    indicator_label = f"No AI-generation heuristic indicators detected (raw score {synthetic_pct}; uncalibrated)"
                    norm_status = DetectorStatus.NEGATIVE.value
                    confidence = None
                    strength = EvidenceStrength.NONE.value
                    explanation = (
                        f"Low synthetic likelihood index ({synthetic_pct}%). "
                        f"Radial spectral decay (alpha={spectral_slope:.2f}) and noise residual correlations conform to standard "
                        "several measured features are within the heuristic range. This does not establish natural optical capture or exclude generation/editing."
                    )

        except Exception as e:
            exec_time = round((time.perf_counter() - start_time) * 1000, 2)
            res = ScreeningTestResult(
                method=cls.METHOD_NAME,
                version=cls.VERSION,
                status="failed",
                indicator="test_failed",
                indicator_label="Test failed",
                observations=[f"Error during AI generative analysis: {str(e)}"],
                explanation="AI generative classification encountered an unexpected processing error.",
                limitations=limitations,
                execution_time_ms=exec_time,
            )
            d_res = DetectorResult(
                detector_name=cls.METHOD_NAME,
                detector_version=cls.VERSION,
                status=DetectorStatus.ERROR.value,
                score=None,
                confidence=None,
                evidence_strength=EvidenceStrength.NONE.value,
                applicable=True,
                technical_reason=str(e),
                affected_regions=[],
                execution_time_ms=exec_time,
            )
            return res, artifacts, analytics, d_res

        exec_time = round((time.perf_counter() - start_time) * 1000, 2)
        test_result = ScreeningTestResult(
            method=cls.METHOD_NAME,
            version=cls.VERSION,
            status="completed",
            indicator=indicator,
            indicator_label=indicator_label,
            observations=observations,
            explanation=explanation,
            limitations=limitations,
            execution_time_ms=exec_time,
            score=round(synthetic_score, 3),
            confidence=None,
            evidence_strength=strength,
            normalized_status=norm_status,
            affected_regions=affected_regions,
        )
        detector_result = DetectorResult(
            detector_name=cls.METHOD_NAME,
            detector_version=cls.VERSION,
            status=norm_status,
            score=round(synthetic_score, 3),
            confidence=round(confidence, 3),
            evidence_strength=strength,
            applicable=True,
            technical_reason=explanation,
            affected_regions=affected_regions,
            execution_time_ms=exec_time,
            observations=observations,
            limitations=limitations,
        )
        return test_result, artifacts, analytics, detector_result
