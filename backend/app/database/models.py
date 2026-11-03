from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database.session import Base


def utc_now():
    return datetime.now(timezone.utc)


class Examination(Base):
    __tablename__ = "examinations"

    examination_id = Column(String(64), primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    detected_media_type = Column(String(64), nullable=False)

    sha256_digest = Column(String(64), nullable=False, index=True)
    sha1_digest = Column(String(40), nullable=True)
    md5_digest = Column(String(32), nullable=True)

    upload_timestamp = Column(DateTime, default=utc_now, nullable=False)
    capture_timestamp = Column(DateTime, nullable=True)

    application_version = Column(String(32), nullable=False)
    analysis_pipeline_version = Column(String(32), nullable=False)

    image_width = Column(Integer, nullable=False)
    image_height = Column(Integer, nullable=False)
    color_mode = Column(String(32), nullable=False)

    status = Column(String(32), default="completed", nullable=False)  # completed, failed
    overall_assessment = Column(String(64), default="requires_human_review", nullable=False)

    # SATYA v2 Decision Engine Fields
    decision_assessment = Column(String(64), default="INCONCLUSIVE", nullable=True)  # LIKELY_AUTHENTIC, LIKELY_TAMPERED, INCONCLUSIVE
    evidence_strength = Column(String(32), default="NONE", nullable=True)  # NONE, LOW, MODERATE, STRONG, VERY_STRONG
    decision_confidence = Column(Integer, default=None, nullable=True)  # 0 to 100; null until calibrated
    decision_data = Column(JSON, default=dict, nullable=True)
    detector_results = Column(JSON, default=list, nullable=True)
    image_characterization = Column(JSON, default=dict, nullable=True)
    model_versions = Column(JSON, default=dict, nullable=True)
    detector_versions = Column(JSON, default=dict, nullable=True)

    # Human Review Fields
    human_review_status = Column(String(64), default="pending", nullable=False)
    reviewer_name = Column(String(128), nullable=True)
    reviewer_designation = Column(String(128), nullable=True)
    reviewer_organization = Column(String(128), nullable=True)
    review_notes = Column(Text, nullable=True)
    review_timestamp = Column(DateTime, nullable=True)
    review_attestation = Column(Boolean, default=False, nullable=False)

    # Structured Data
    extracted_metadata = Column(JSON, default=dict, nullable=False)
    test_results = Column(JSON, default=list, nullable=False)
    known_limitations = Column(JSON, default=list, nullable=False)
    suggested_manual_checks = Column(JSON, default=list, nullable=False)
    artifacts = Column(JSON, default=dict, nullable=False)

    report_generated_at = Column(DateTime, nullable=True)

    # Relationships
    activity_events = relationship(
        "ActivityEvent",
        back_populates="examination",
        cascade="all, delete-orphan",
        order_by="ActivityEvent.timestamp.asc()",
    )


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    examination_id = Column(String(64), ForeignKey("examinations.examination_id", ondelete="CASCADE"), index=True, nullable=False)
    event_type = Column(String(64), nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False)
    details = Column(JSON, default=dict, nullable=False)

    examination = relationship("Examination", back_populates="activity_events")


class ModelVersionRecord(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(64), nullable=False, index=True)
    model_version = Column(String(32), nullable=False)
    model_hash = Column(String(64), nullable=False)
    training_dataset_version = Column(String(64), nullable=False)
    threshold_profile = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    details = Column(JSON, default=dict, nullable=False)


class DatasetVersionRecord(Base):
    __tablename__ = "dataset_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_version = Column(String(64), nullable=False, unique=True, index=True)
    specimens_count = Column(Integer, nullable=False)
    authentic_count = Column(Integer, nullable=False)
    tampered_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    manifest_hash = Column(String(64), nullable=False)
    details = Column(JSON, default=dict, nullable=False)
