import os
from pathlib import Path
from typing import List, Set, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, extra="allow")

    PROJECT_NAME: str = "SCSS SATYA prototype v2"
    PROJECT_FULL_NAME: str = "SCSS SATYA prototype v2 — Forensic Image Analysis & Evidence Fusion Platform"
    TAGLINE: str = "Forensic-led digital image authenticity screening & multi-evidence fusion platform"
    VERSION: str = "2.1.0-unvalidated"
    PIPELINE_VERSION: str = "2026.3-v2.1-unvalidated"
    RULES_VERSION: str = "2026.3-v2.1-unvalidated"
    THRESHOLD_PROFILE: str = "production-v2"
    ORGANIZATION: str = "Sure Clue Scientific Solutions (SCSS)"
    CORE_PRINCIPLE: str = "The tool screens. The expert decides."

    MANDATORY_DISCLAIMER: str = (
        "SCSS SATYA produces preliminary, automated image-screening findings and decision-support "
        "evidence for investigative evaluation. Its results are not a definitive legal determination "
        "of authenticity, manipulation, source, or judicial admissibility. The absence of detected "
        "indicators does not establish that an image is unaltered. All findings must be interpreted "
        "by a qualified forensic examiner alongside available contextual evidence."
    )

    # Base Paths
    BACKEND_DIR: Path = Path(__file__).resolve().parent.parent.parent
    ROOT_DIR: Path = BACKEND_DIR.parent
    STORAGE_DIR: Path = ROOT_DIR / "storage"
    VAULT_DIR: Path = STORAGE_DIR / "vault"
    ARTIFACTS_DIR: Path = STORAGE_DIR / "artifacts"
    REPORTS_DIR: Path = STORAGE_DIR / "reports"
    MODELS_DIR: Path = STORAGE_DIR / "models"
    DATASETS_DIR: Path = STORAGE_DIR / "datasets"

    # Database
    DATABASE_URL: str = f"sqlite:///{STORAGE_DIR / 'satya_forensics.db'}"

    # File Upload Limits & Security Hardening
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    MAX_IMAGE_PIXELS: int = 50_000_000  # 50 Megapixels max (decompression bomb defense)
    MAX_IMAGE_DIMENSION: int = 12_000   # Max width or height in pixels
    MAX_PROCESSING_TIME_SECONDS: int = 60
    MAX_CONCURRENT_ANALYSES: int = 5
    ALLOWED_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    ALLOWED_MIME_TYPES: Set[str] = {"image/jpeg", "image/png", "image/webp", "image/tiff"}

    # Method Names and Versions
    METHOD_VERSIONS: Dict[str, str] = {
        "metadata_examination": "2.1.0-unvalidated",
        "cryptographic_and_perceptual_hashing": "2.1.0-unvalidated",
        "c2pa_provenance": "2.1.0-unvalidated",
        "document_forensics": "2.1.0-unvalidated",
        "jpeg_quantization_analysis": "2.1.0-unvalidated",
        "error_level_analysis": "2.1.0-unvalidated",
        "image_consistency_checks": "2.1.0-unvalidated",
        "noise_residual_analysis": "2.1.0-unvalidated",
        "fourier_spectral_analysis": "2.1.0-unvalidated",
        "copy_move_forgery_detection": "2.1.0-unvalidated",
        "ai_generative_classifier": "2.1.0-unvalidated",
        "document_typography_and_alignment": "2.1.0-unvalidated",
        "srm_wavelet_analysis": "2.1.0-unvalidated",
        "image_splicing_detector": "2.1.0-unvalidated",
        "lighting_consistency_analysis": "2.1.0-unvalidated",
    }

    # CORS Allowed Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]


settings = Settings()

# Ensure storage directories exist
settings.VAULT_DIR.mkdir(parents=True, exist_ok=True)
settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
settings.DATASETS_DIR.mkdir(parents=True, exist_ok=True)
