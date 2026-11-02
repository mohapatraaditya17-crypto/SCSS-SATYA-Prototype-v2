from pathlib import Path
from unittest.mock import Mock

from PIL import Image

from app.analysis import pipeline as pipeline_module
from app.analysis.pipeline import ForensicPipeline
from app.analysis.characterizer import ImageCharacterizer


def test_every_characterizer_detector_has_one_routing_state(tmp_path):
    image_path = tmp_path / "route.jpg"
    Image.new("RGB", (320, 240), color=(90, 110, 130)).save(image_path, "JPEG")
    data = image_path.read_bytes()
    characterization = ImageCharacterizer.characterize(
        image_path=image_path,
        file_bytes=data,
        mime_type="image/jpeg",
        image_width=320,
        image_height=240,
        extracted_metadata={},
    )
    applicable = set(characterization["applicable_detectors"])
    inapplicable = set(characterization["inapplicable_detectors"])
    declared = set(ImageCharacterizer.ALL_DETECTORS)
    assert applicable.isdisjoint(inapplicable)
    assert applicable | inapplicable == declared


def test_document_only_gates_skip_image_detectors_and_record_not_applicable(monkeypatch, tmp_path):
    image_path = tmp_path / "ordinary.jpg"
    Image.new("RGB", (320, 240), color=(90, 110, 130)).save(image_path, "JPEG")
    data = image_path.read_bytes()

    # Force a deterministic document characterization: only core detectors execute.
    core = {
        "metadata_examination", "cryptographic_and_perceptual_hashing",
        "c2pa_provenance", "image_consistency_checks",
    }
    inapplicable = set(ImageCharacterizer.ALL_DETECTORS) - core
    routing = {
        "applicable_detectors": sorted(core),
        "inapplicable_detectors": {key: "mocked gate: not applicable" for key in inapplicable},
        "image_class": "DOCUMENT",
        "cryptographic_provenance_verified": False,
    }
    monkeypatch.setattr(pipeline_module.ImageCharacterizer, "characterize", Mock(return_value=routing))

    def forbidden(*args, **kwargs):
        raise AssertionError("Inapplicable analyzer was invoked")

    for analyzer_name in (
        "DocumentForensicsAnalyzer", "JPEGQuantizationAnalyzer", "ELAAnalyzer",
        "ConsistencyAnalyzer", "NoiseAnalyzer", "FFTAnalyzer", "CopyMoveAnalyzer",
        "AISyntheticAnalyzer", "TypographyAnalyzer", "SRMWaveletAnalyzer",
        "SplicingDetector", "LightingConsistencyAnalyzer",
    ):
        analyzer = getattr(pipeline_module, analyzer_name)
        monkeypatch.setattr(analyzer, "analyze", forbidden)

    # Core analyzers return minimal valid values; all optional rich outputs are empty.
    monkeypatch.setattr(
        pipeline_module.MetadataAnalyzer, "analyze",
        Mock(return_value={
            "test_result": Mock(model_dump=lambda: {}),
            "extracted_metadata": {},
        }),
    )
    monkeypatch.setattr(
        pipeline_module.HashAnalyzer, "analyze",
        Mock(return_value=(Mock(), None, {"cryptographic": {}, "perceptual": {}})),
    )
    monkeypatch.setattr(
        pipeline_module.C2PAAnalyzer, "analyze",
        Mock(return_value=(Mock(), {})),
    )
    monkeypatch.setattr(
        pipeline_module.ConsistencyAnalyzer, "analyze",
        Mock(side_effect=AssertionError("Consistency gate deliberately included; expected invocation")),
    )
    # Mark consistency as applicable and supply a minimal result tuple.
    monkeypatch.setattr(
        pipeline_module.ConsistencyAnalyzer, "analyze",
        Mock(return_value=(Mock(), {}, {})),
    )
    monkeypatch.setattr(
        pipeline_module.EvidenceFusionEngine, "fuse_evidence",
        Mock(return_value={"assessment": {"technical_assessment": "INSUFFICIENT_EVIDENCE",
                                        "confidence": None, "evidence_strength": "NONE",
                                        "coverage": {"coverage_score": None}}}),
    )

    output = ForensicPipeline.execute(
        image_path=image_path,
        file_bytes=data,
        examination_id="GATE-TEST",
        media_type="image/jpeg",
        image_width=320,
        image_height=240,
        sha256_digest="0" * 64,
        file_size_bytes=len(data),
    )
    statuses = {test.method: test.status for test in output["tests"]}
    assert sum(status == "not_applicable" for status in statuses.values()) == len(inapplicable)
