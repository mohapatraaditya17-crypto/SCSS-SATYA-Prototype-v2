import csv
import json
import hashlib
from pathlib import Path
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class GroundTruthLabel(str, Enum):
    AUTHENTIC = "AUTHENTIC"
    TAMPERED = "TAMPERED"


class ManipulationType(str, Enum):
    AUTHENTIC = "AUTHENTIC"
    COPY_MOVE = "COPY_MOVE"
    SPLICING = "SPLICING"
    OBJECT_REMOVAL = "OBJECT_REMOVAL"
    INPAINTING = "INPAINTING"
    RETOUCHING = "RETOUCHING"
    TEXT_MODIFICATION = "TEXT_MODIFICATION"
    FACE_MANIPULATION = "FACE_MANIPULATION"
    AI_GENERATED = "AI_GENERATED"
    AI_INPAINTING = "AI_INPAINTING"
    AI_OUTPAINTING = "AI_OUTPAINTING"
    GENERATIVE_FILL = "GENERATIVE_FILL"
    IMAGE_COMPOSITING = "IMAGE_COMPOSITING"
    RESIZING = "RESIZING"
    RECOMPRESSION = "RECOMPRESSION"
    SCREENSHOT = "SCREENSHOT"
    PRINT_SCAN = "PRINT_SCAN"
    MULTI_OPERATION = "MULTI_OPERATION"
    OTHER = "OTHER"


class ManipulationSeverity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SourceDeviceType(str, Enum):
    SMARTPHONE = "SMARTPHONE"
    DSLR = "DSLR"
    MIRRORLESS = "MIRRORLESS"
    SCAN = "SCAN"
    SCREENSHOT = "SCREENSHOT"
    DOCUMENT = "DOCUMENT"
    SYNTHETIC = "SYNTHETIC"
    UNKNOWN = "UNKNOWN"


class SpecimenRecord(BaseModel):
    specimen_id: str
    source_id: str
    parent_id: Optional[str] = None
    source_group: Optional[str] = None
    device_group: Optional[str] = None
    media_class: Optional[str] = None
    ground_truth: str  # AUTHENTIC, TAMPERED
    manipulation_type: str = ManipulationType.AUTHENTIC.value
    manipulation_subtype: Optional[str] = None
    severity: str = ManipulationSeverity.NONE.value
    source_type: str = SourceDeviceType.UNKNOWN.value
    camera_device: Optional[str] = None
    image_format: str = "JPEG"
    resolution: str = "1920x1080"
    compression_quality: Optional[int] = None
    generation_method: str = "REAL_WORLD"  # CONTROLLED_SYNTHETIC, CONTROLLED_MANUAL, AI_GENERATED, AI_MODIFIED, REAL_WORLD_MANIPULATED, AUTHENTIC
    editing_tool: Optional[str] = None
    operations: List[str] = Field(default_factory=list)
    dataset_split: str = "test"  # train, val, test
    file_path: Optional[str] = None
    sha256: Optional[str] = None
    label_source: Optional[str] = None
    adjudication_reference: Optional[str] = None
    compression_history: List[str] = Field(default_factory=list)


class DatasetManifest(BaseModel):
    manifest_id: str = "SATYA-FD-2026-V2"
    version: str = "2.0.0"
    description: str = "Defensible Forensic Evaluation Dataset Manifest with Source-Level Splitting"
    specimens: List[SpecimenRecord] = Field(default_factory=list)

    @classmethod
    def split_by_source(
        cls,
        specimens: List[SpecimenRecord],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        salt: str = "satya_v2_seed_42",
    ) -> List[SpecimenRecord]:
        """
        Partitions specimens strictly by source_id.
        Guarantees that all derivative manipulations originating from source X
        fall into the exact same partition as source X, preventing data leakage.
        """
        if any(value < 0 for value in (train_ratio, val_ratio, test_ratio)):
            raise ValueError("Split ratios must be non-negative.")
        if abs((train_ratio + val_ratio + test_ratio) - 1.0) > 1e-9:
            raise ValueError("train_ratio + val_ratio + test_ratio must equal 1.0.")
        updated_records: List[SpecimenRecord] = []
        for rec in specimens:
            # Keep all parent/derivative specimens together by explicit source group.
            group = rec.source_group or rec.source_id
            h = hashlib.sha256(f"{group}_{salt}".encode()).hexdigest()
            val = int(h[:8], 16) / 0xFFFFFFFF

            if val < train_ratio:
                rec.dataset_split = "train"
            elif val < train_ratio + val_ratio:
                rec.dataset_split = "val"
            else:
                rec.dataset_split = "test"
            updated_records.append(rec)

        return updated_records

    def save_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2)

    @classmethod
    def load_json(cls, path: Path) -> "DatasetManifest":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

