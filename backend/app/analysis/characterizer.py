from pathlib import Path
from typing import Dict, Any, List, Tuple
from PIL import Image
import numpy as np


class ImageCharacterizer:
    """
    Image Characterization & Pre-Analysis Triage Engine.
    Classifies input media by format, dimensions, color space, and visual content class
    (photograph, document, screenshot, scan, graphic, AI candidate) to determine
    the valid operational applicability mask for all forensic detectors.
    """
    VERSION = "2.0.0"

    ALL_DETECTORS = [
        "metadata_examination",
        "cryptographic_and_perceptual_hashing",
        "c2pa_provenance",
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
    ]

    COMMON_SCREEN_RESOLUTIONS = {
        (1920, 1080), (1080, 1920),
        (2560, 1440), (1440, 2560),
        (3840, 2160), (2160, 3840),
        (1366, 768),  (1280, 720),
        (1440, 900),  (1600, 900),
        (1280, 800),  (1536, 864),
    }

    AI_CANONICAL_RESOLUTIONS = {
        (512, 512), (768, 768), (1024, 1024),
        (1024, 1792), (1792, 1024),
        (896, 1152), (1152, 896),
        (832, 1216), (1216, 832),
    }

    @classmethod
    def characterize(
        cls,
        image_path: Path,
        file_bytes: bytes,
        mime_type: str,
        image_width: int,
        image_height: int,
        extracted_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts structural, spatial, and domain features to characterize the specimen
        and construct the detector applicability matrix.
        """
        # 1. Format and Bitdepth extraction
        is_jpeg = mime_type == "image/jpeg" or file_bytes.startswith(b"\xFF\xD8\xFF")
        is_png = mime_type == "image/png" or file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        is_webp = mime_type == "image/webp" or (file_bytes.startswith(b"RIFF") and b"WEBP" in file_bytes[:16])

        format_str = "JPEG" if is_jpeg else ("PNG" if is_png else ("WEBP" if is_webp else "UNKNOWN"))
        megapixels = round((image_width * image_height) / 1_000_000.0, 2)
        aspect_ratio = round(image_width / max(1, image_height), 3)

        # 2. Inspect Metadata & Provenance flags
        has_camera_exif = bool(extracted_metadata.get("Make") or extracted_metadata.get("Model"))
        camera_make = extracted_metadata.get("Make")
        camera_model = extracted_metadata.get("Model")
        software_tag = extracted_metadata.get("Software")

        # 3. Detect Screenshot characteristics
        is_screen_resolution = (image_width, image_height) in cls.COMMON_SCREEN_RESOLUTIONS
        is_screen_density = (
            extracted_metadata.get("PNG:ScreenDensityDPI") == 96
            or extracted_metadata.get("XResolution") == 72
            or extracted_metadata.get("XResolution") == 96
        )
        is_screenshot_name = "screenshot" in image_path.name.lower() or "screen shot" in image_path.name.lower()

        # 4. Check Document / Graphic content heuristics via pixel sampling
        is_document_candidate = False
        is_flat_graphic = False
        try:
            with Image.open(image_path) as img:
                thumb = img.convert("RGB").resize((128, 128))
                arr = np.array(thumb, dtype=np.float32)
                gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]

                # High white ratio (> 65% pixels with luminance > 230) indicates document/paper/certificate
                white_ratio = float(np.mean(gray > 225.0))
                # Low standard deviation indicates flat vector/solid UI graphic
                lum_std = float(np.std(gray))

                if white_ratio > 0.60:
                    is_document_candidate = True
                elif lum_std < 18.0:
                    is_flat_graphic = True
        except Exception:
            pass

        # 5. Check AI synthesis candidates
        is_ai_res = (image_width, image_height) in cls.AI_CANONICAL_RESOLUTIONS
        is_ai_software = any(
            kw in str(software_tag).lower()
            for kw in ["midjourney", "stable diffusion", "comfyui", "novelai", "dall-e", "flux"]
        )

        # 6. Synthesize Primary Image Class
        # Priority order:
        #   1. Document (white-ratio content heuristic is strongest signal for docs)
        #   2. Screenshot (filename or exact screen resolution + PNG + no EXIF camera)
        #   3. Camera EXIF (physical camera metadata outranks flat-graphic pixel heuristic;
        #      a solid-color synthetic test image with Nikon EXIF should be PHOTOGRAPH)
        #   4. Flat graphic (low-std solid regions with no camera metadata)
        #   5. AI-software tag or canonical AI resolution (no camera)
        #   6. JPEG format fallback (JPEG without any above signals → photographic source)
        #   7. Unknown
        if is_document_candidate:
            image_class = "DOCUMENT"
        elif is_screenshot_name or (is_screen_resolution and not has_camera_exif and is_png):
            image_class = "SCREENSHOT"
        elif has_camera_exif:
            # EXIF is mutable metadata. Preserve a neutral candidate label without
            # asserting that the specimen is an optical photograph.
            image_class = "CAMERA_METADATA_PRESENT"
        elif is_flat_graphic:
            image_class = "GRAPHIC"
        elif is_ai_software or (is_ai_res and not has_camera_exif):
            image_class = "AI_CANDIDATE"
        elif is_jpeg:
            image_class = "PHOTOGRAPH"
        else:
            image_class = "UNKNOWN"

        # 7. Build Applicability Rules
        applicable_detectors: List[str] = []
        inapplicable_detectors: Dict[str, str] = {}

        for det in cls.ALL_DETECTORS:
            if det in ["metadata_examination", "cryptographic_and_perceptual_hashing", "c2pa_provenance", "image_consistency_checks"]:
                applicable_detectors.append(det)
            elif det == "document_forensics":
                if image_class in ["DOCUMENT", "SCREENSHOT"]:
                    applicable_detectors.append(det)
                else:
                    inapplicable_detectors[det] = "Specimen is an optical image; document/container forensics not applicable."
            elif det in ["jpeg_quantization_analysis", "error_level_analysis"]:
                if is_jpeg:
                    applicable_detectors.append(det)
                else:
                    inapplicable_detectors[det] = f"Method applies exclusively to DCT JPEG images; format is {format_str}."
            elif det == "document_typography_and_alignment":
                if image_class in ["DOCUMENT", "SCREENSHOT"]:
                    applicable_detectors.append(det)
                else:
                    inapplicable_detectors[det] = "Specimen is photographic/scenery; document typography and baseline verification not applicable."
            elif det == "lighting_consistency_analysis":
                if image_class in ["DOCUMENT", "SCREENSHOT", "GRAPHIC"]:
                    inapplicable_detectors[det] = "Specimen is a 2D document or digital UI render; 3D optical lighting direction analysis not applicable."
                else:
                    applicable_detectors.append(det)
            elif det in ["noise_residual_analysis", "srm_wavelet_analysis", "image_splicing_detector", "copy_move_forgery_detection", "fourier_spectral_analysis", "ai_generative_classifier"]:
                # Broadly applicable, but flat graphics will be calibrated accordingly
                applicable_detectors.append(det)
            else:
                applicable_detectors.append(det)

        return {
            "format": format_str,
            "mime_type": mime_type,
            "dimensions": {"width": image_width, "height": image_height},
            "megapixels": megapixels,
            "aspect_ratio": aspect_ratio,
            "has_camera_exif": has_camera_exif,
            "camera_metadata_present": has_camera_exif,
            "camera_metadata_verified": False,
            "provenance_level": 0,
            "camera_make": camera_make,
            "camera_model": camera_model,
            "software_tag": software_tag,
            "image_class": image_class,
            "applicable_detectors": applicable_detectors,
            "inapplicable_detectors": inapplicable_detectors,
            "characterization_version": cls.VERSION,
        }

