from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image

from app.analysis import pipeline as pipeline_module
from app.analysis.pipeline import ForensicPipeline
from app.analysis.characterizer import ImageCharacterizer
from app.schemas.examination import ScreeningTestResult


def _test(method: str) -> ScreeningTestResult:
    return ScreeningTestResult(
        method=method,
        version="mock-1",
        status="completed",
        indicator="inconclusive",
        indicator_label="Mocked inconclusive",
        explanation="Deterministic analyzer stub for applicability-routing verification.",
        limitations=[],
    )


def _characterization(inapplicable: str | None = None) -> dict:
    applicable = [d for d in ImageCharacterizer.ALL_DETECTORS if d != inapplicable]
    missing = {inapplicable: "mocked not-applicable gate"} if inapplicable else {}
    return {
        "format": "JPEG",
        "mime_type": "image/jpeg",
        "dimensions": {"width": 320, "height": 240},
        "megapixels": 0.08,
        "aspect_ratio": 1.333,
        "has_camera_exif": False,
        "camera_metadata_present": False,
        "camera_metadata_verified": False,
        "cryptographic_provenance_verified": False,
        "provenance_level": 0,
        "image_class": "PHOTOGRAPH",
        "applicable_detectors": applicable,
        "inapplicable_detectors": missing,
        "characterization_version": "mock-1",
    }


def _install_analyzer_stubs(monkeypatch, disabled: str | None):
    # Result labels use the detector identifiers where possible to avoid test
    # dependence on display-label normalization in the production pipeline.
    responses = {
        "DocumentForensicsAnalyzer": (_test("document_forensics"), {}),
        "JPEGQuantizationAnalyzer": (_test("jpeg_quantization_analysis"), {}),
        "ELAAnalyzer": (_test("error_level_analysis"), {}),
        "ConsistencyAnalyzer": (_test("image_consistency_checks"), {}, {}),
        "NoiseAnalyzer": (_test("noise_residual_analysis"), {}, {}, None),
        "FFTAnalyzer": (_test("fourier_spectral_analysis"), {}, {}),
        "CopyMoveAnalyzer": (_test("copy_move_forgery_detection"), {}, {}, None),
        "AISyntheticAnalyzer": (_test("ai_generative_classifier"), {}, {}, None),
        "TypographyAnalyzer": (_test("document_typography_and_alignment"), {}, {}, None),
        "SRMWaveletAnalyzer": (_test("srm_wavelet_analysis"), None, {}),
        "SplicingDetector": (_test("image_splicing_detector"), {}, {}, None),
        "LightingConsistencyAnalyzer": (_test("lighting_consistency_analysis"), None, {}),
    }
    detector_to_analyzer = {
        "document_forensics": "DocumentForensicsAnalyzer",
        "jpeg_quantization_analysis": "JPEGQuantizationAnalyzer",
        "error_level_analysis": "ELAAnalyzer",
        "image_consistency_checks": "ConsistencyAnalyzer",
        "noise_residual_analysis": "NoiseAnalyzer",
        "fourier_spectral_analysis": "FFTAnalyzer",
        "copy_move_forgery_detection": "CopyMoveAnalyzer",
        "ai_generative_classifier": "AISyntheticAnalyzer",
        "document_typography_and_alignment": "TypographyAnalyzer",
        "srm_wavelet_analysis": "SRMWaveletAnalyzer",
        "image_splicing_detector": "SplicingDetector",
        "lighting_consistency_analysis": "LightingConsistencyAnalyzer",
    }
    calls = {}
    calls = {}
    for analyzer_name, response in responses.items():
        analyzer = getattr(pipeline_module, analyzer_name)
        detector_id = next((key for key, name in detector_to_analyzer.items() if name == analyzer_name), None)
        if detector_id == disabled:
            fn = Mock(side_effect=AssertionError(f"{detector_id} analyzer invoked despite NOT_APPLICABLE gate"))
        else:
            fn = Mock(return_value=response)
        monkeypatch.setattr(analyzer, "analyze", fn)
        calls[analyzer_name] = fn

    # Core and non-gated methods are deterministic, well-formed test outputs.
    monkeypatch.setattr(
        pipeline_module.MetadataAnalyzer,
        "analyze",
        Mock(return_value={"test_result": _test("metadata_examination"), "extracted_metadata": {}}),
    )
    monkeypatch.setattr(
        pipeline_module.HashAnalyzer,
        "analyze",
        Mock(return_value=(_test("cryptographic_and_perceptual_hashing"), None,
                           {"cryptographic": {}, "perceptual": {}})),
    )
    monkeypatch.setattr(
        pipeline_module.C2PAAnalyzer,
        "analyze",
        Mock(return_value=(_test("c2pa_provenance"), {})),
    )
    monkeypatch.setattr(
        pipeline_module.MetadataAnalyzer,
        "analyze",
        Mock(return_value={"test_result": _test("metadata_examination"), "extracted_metadata": {}}),
    )
    monkeypatch.setattr(
        pipeline_module.HashAnalyzer,
        "analyze",
        Mock(return_value=(_test("cryptographic_and_perceptual_hashing"), None,
                           {"cryptographic": {}, "perceptual": {}})),
    )
    monkeypatch.setattr(
        pipeline_module.C2PAAnalyzer,
        "analyze",
        Mock(return_value=(_test("c2pa_provenance"), {})),
    )
    monkeypatch.setattr(
        pipeline_module.EvidenceFusionEngine,
        "fuse_evidence",
        Mock(return_value={
            "assessment": {
                "technical_assessment": "INCONCLUSIVE",
                "confidence": None,
                "evidence_strength": "NONE",
                "coverage": {"coverage_score": None},
            }
        }),
    )
    return calls


@pytest.fixture
def jpeg_specimen(tmp_path):
    path = tmp_path / "specimen.jpg"
    Image.new("RGB", (320, 240), (80, 90, 100)).save(path, "JPEG")
    return path, path.read_bytes()


def test_characterizer_routes_each_detector_to_exactly_one_bucket(jpeg_specimen):
    path, data = jpeg_specimen
    result = ImageCharacterizer.characterize(path, data, "image/jpeg", 320, 240, {})
    applicable = set(result["applicable_detectors"])
    inapplicable = set(result["inapplicable_detectors"])
    declared = set(ImageCharacterizer.ALL_DETECTORS)
    assert applicable.isdisjoint(inapplicable)
    assert applicable | inapplicable == declared


@pytest.mark.parametrize(
    "detector_id",
    [
        "document_forensics",
        "jpeg_quantization_analysis",
        "error_level_analysis",
        "image_consistency_checks",
        "noise_residual_analysis",
        "fourier_spectral_analysis",
        "copy_move_forgery_detection",
        "ai_generative_classifier",
        "document_typography_and_alignment",
        "srm_wavelet_analysis",
        "image_splicing_detector",
        "lighting_consistency_analysis",
    ],
)
def test_inapplicable_gate_skips_target_analyzer(monkeypatch, jpeg_specimen, detector_id):
    path, data = jpeg_specimen
    monkeypatch.setattr(
        pipeline_module.ImageCharacterizer,
        "characterize",
        Mock(return_value=_characterization(detector_id)),
    )
    calls = _install_analyzer_stubs(monkeypatch, detector_id)

    output = ForensicPipeline.execute(
        image_path=path,
        file_bytes=data,
        examination_id=f"GATE-{detector_id}",
        media_type="image/jpeg",
        image_width=320,
        image_height=240,
        sha256_digest="0" * 64,
        file_size_bytes=len(data),
    )

    target = {
        "document_forensics": "DocumentForensicsAnalyzer",
        "jpeg_quantization_analysis": "JPEGQuantizationAnalyzer",
        "error_level_analysis": "ELAAnalyzer",
        "image_consistency_checks": "ConsistencyAnalyzer",
        "noise_residual_analysis": "NoiseAnalyzer",
        "fourier_spectral_analysis": "FFTAnalyzer",
        "copy_move_forgery_detection": "CopyMoveAnalyzer",
        "ai_generative_classifier": "AISyntheticAnalyzer",
        "document_typography_and_alignment": "TypographyAnalyzer",
        "srm_wavelet_analysis": "SRMWaveletAnalyzer",
        "image_splicing_detector": "SplicingDetector",
        "lighting_consistency_analysis": "LightingConsistencyAnalyzer",
    }[detector_id]
    assert calls[target].call_count == 0

    gated = [d for d in output["detector_results"] if d.status == "NOT_APPLICABLE"]
    assert gated, f"{detector_id} should surface as NOT_APPLICABLE"
    assert output["decision_confidence"] is None


def test_metadata_is_preflight_and_executes_once_before_routing(monkeypatch, jpeg_specimen):
    path, data = jpeg_specimen
    characterize = Mock(return_value=_characterization())
    monkeypatch.setattr(pipeline_module.ImageCharacterizer, "characterize", characterize)
    calls = _install_analyzer_stubs(monkeypatch, None)
    metadata = pipeline_module.MetadataAnalyzer.analyze
    ForensicPipeline.execute(
        image_path=path,
        file_bytes=data,
        examination_id="GATE-METADATA-PREFLIGHT",
        media_type="image/jpeg",
        image_width=320,
        image_height=240,
        sha256_digest="0" * 64,
        file_size_bytes=len(data),
    )
    assert metadata.call_count == 1
    assert characterize.call_count == 1
