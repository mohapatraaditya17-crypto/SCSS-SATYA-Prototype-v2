from pathlib import Path
from PIL import Image
from app.analysis.characterizer import ImageCharacterizer


def test_characterizer_builds_applicability_matrix(tmp_path):
    image_path = tmp_path / "photo.jpg"
    Image.new("RGB", (1024, 768), color=(100, 120, 140)).save(image_path, format="JPEG")
    data = image_path.read_bytes()
    result = ImageCharacterizer.characterize(
        image_path=image_path,
        file_bytes=data,
        mime_type="image/jpeg",
        image_width=1024,
        image_height=768,
        extracted_metadata={},
    )
    assert "noise_residual_analysis" in result["applicable_detectors"]
    assert "jpeg_quantization_analysis" in result["applicable_detectors"]


def test_camera_exif_is_metadata_not_authenticity_proof(tmp_path):
    image_path = tmp_path / "synthetic.jpg"
    Image.new("RGB", (640, 480), color=(20, 20, 20)).save(image_path, format="JPEG")
    result = ImageCharacterizer.characterize(
        image_path=image_path,
        file_bytes=image_path.read_bytes(),
        mime_type="image/jpeg",
        image_width=640,
        image_height=480,
        extracted_metadata={"Make": "Canon", "Model": "EOS R5"},
    )
    assert result["camera_metadata_present"] is True
    assert result["camera_metadata_verified"] is False
    assert result["cryptographic_provenance_verified"] is False
    assert result["provenance_level"] == 1
    assert result["image_class"] != "PHOTOGRAPH"
