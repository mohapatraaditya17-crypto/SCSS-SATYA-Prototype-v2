import io
from pathlib import Path
from PIL import Image
import pytest

from app.analysis.characterizer import ImageCharacterizer


def test_characterize_jpeg_photo(tmp_path):
    img = Image.new("RGB", (640, 480), color=(120, 140, 160))
    img_path = tmp_path / "test_photo.jpg"
    img.save(img_path, "JPEG", quality=90)
    file_bytes = img_path.read_bytes()

    metadata = {"Make": "Nikon", "Model": "D850"}
    char = ImageCharacterizer.characterize(
        image_path=img_path,
        file_bytes=file_bytes,
        mime_type="image/jpeg",
        image_width=640,
        image_height=480,
        extracted_metadata=metadata,
    )

    assert char["format"] == "JPEG"
    assert char["image_class"] == "CAMERA_METADATA_PRESENT"
    assert char["has_camera_exif"] is True
    assert "error_level_analysis" in char["applicable_detectors"]
    assert "jpeg_quantization_analysis" in char["applicable_detectors"]
    # Document typography should not be applicable to optical photos
    assert "document_typography_and_alignment" in char["inapplicable_detectors"]


def test_characterize_png_document(tmp_path):
    # Mostly white image simulating document
    img = Image.new("RGB", (800, 1000), color=(250, 250, 250))
    img_path = tmp_path / "invoice.png"
    img.save(img_path, "PNG")
    file_bytes = img_path.read_bytes()

    char = ImageCharacterizer.characterize(
        image_path=img_path,
        file_bytes=file_bytes,
        mime_type="image/png",
        image_width=800,
        image_height=1000,
        extracted_metadata={},
    )

    assert char["format"] == "PNG"
    assert char["image_class"] == "DOCUMENT"
    assert "document_typography_and_alignment" in char["applicable_detectors"]
    assert "error_level_analysis" in char["inapplicable_detectors"]
    assert "jpeg_quantization_analysis" in char["inapplicable_detectors"]

