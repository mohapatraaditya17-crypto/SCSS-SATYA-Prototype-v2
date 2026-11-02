from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DetectorStatus(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"


class EvidenceStrength(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


class EvidenceFamilyType(str, Enum):
    INTEGRITY = "INTEGRITY"
    PROVENANCE = "PROVENANCE"
    COMPRESSION = "COMPRESSION"
    RESIDUAL = "RESIDUAL"
    MANIPULATION = "MANIPULATION"
    AI_ML = "AI_ML"
    PHYSICAL_CONSISTENCY = "PHYSICAL_CONSISTENCY"
    DOCUMENT_CONTAINER = "DOCUMENT_CONTAINER"


class TechnicalAssessment(str, Enum):
    # Screening outcomes; these are not final forensic opinions.
    MANIPULATION_INDICATORS_DETECTED = "MANIPULATION_INDICATORS_DETECTED"
    AI_GENERATION_INDICATORS_DETECTED = "AI_GENERATION_INDICATORS_DETECTED"
    PROVENANCE_VERIFIED = "PROVENANCE_VERIFIED"
    PROVENANCE_CONFLICT = "PROVENANCE_CONFLICT"
    NO_MANIPULATION_INDICATORS_DETECTED = "NO_MANIPULATION_INDICATORS_DETECTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LIKELY_AUTHENTIC = "LIKELY_AUTHENTIC"  # deprecated; no longer emitted
    LIKELY_TAMPERED = "LIKELY_TAMPERED"    # deprecated; no longer emitted
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    ERROR = "ERROR"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class FileIntegrityInfo(BaseModel):
    algorithm: str = "SHA-256"
    digest: str
    sha1: Optional[str] = None
    md5: Optional[str] = None
    verified: Optional[bool] = None


class EvidenceRegion(BaseModel):
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.85
    detector: str = ""
    label: str = ""


class DecisiveObservation(BaseModel):
    detector: str
    finding: str
    confidence: float
    region: Optional[EvidenceRegion] = None


class DetectorResult(BaseModel):
    detector_name: str
    detector_version: str
    status: str = DetectorStatus.INCONCLUSIVE.value  # POSITIVE, NEGATIVE, INCONCLUSIVE, NOT_APPLICABLE, ERROR
    # Missing detector outputs remain unknown; never synthesize values.
    score: Optional[float] = None
    confidence: Optional[float] = None
    raw_score: Optional[float] = None
    calibrated_probability: Optional[float] = None
    evidence_strength: str = EvidenceStrength.NONE.value  # NONE, LOW, MODERATE, STRONG, VERY_STRONG
    applicable: bool = True
    technical_reason: str = ""
    affected_regions: List[EvidenceRegion] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    error_code: Optional[str] = None
    observations: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class EvidenceFamilySummary(BaseModel):
    family: str
    status: str  # SUPPORTING_TAMPERING, SUPPORTING_AUTHENTIC, INCONCLUSIVE, NOT_APPLICABLE, CONTRADICTORY
    aggregate_score: float = 0.0
    weight: float = 1.0
    member_detectors: List[str] = Field(default_factory=list)
    findings_summary: str = ""


class DecisionEngineOutput(BaseModel):
    final_assessment: str = TechnicalAssessment.INCONCLUSIVE.value
    # Reserved for empirically calibrated outputs; null while no calibrator is registered.
    decision_confidence: Optional[float] = None
    evidence_strength: str = EvidenceStrength.NONE.value
    human_review_required: bool = True
    decisive_observations: List[DecisiveObservation] = Field(default_factory=list)
    supporting_observations: List[str] = Field(default_factory=list)
    contradictory_observations: List[str] = Field(default_factory=list)
    inconclusive_tests: List[str] = Field(default_factory=list)
    not_applicable_tests: List[str] = Field(default_factory=list)
    error_tests: List[str] = Field(default_factory=list)
    applicable_detector_count: int = 0
    successful_detector_count: int = 0
    detector_error_count: int = 0
    coverage_score: Optional[float] = None
    decision_rationale: str = ""
    evidence_families: Dict[str, EvidenceFamilySummary] = Field(default_factory=dict)
    rules_version: str = "2026.2-v2"
    threshold_profile: str = "production-v2"


class ScreeningTestResult(BaseModel):
    method: str
    version: str
    status: str  # completed, not_applicable, failed
    indicator: str  # indicator_detected, no_indicator_detected, inconclusive, test_unavailable, test_failed
    indicator_label: str  # Human readable label
    observations: List[str] = Field(default_factory=list)
    explanation: str
    limitations: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    # SATYA v2 extensions (optional for backwards compatibility)
    score: Optional[float] = None
    confidence: Optional[float] = None
    evidence_strength: Optional[str] = None
    normalized_status: Optional[str] = None
    affected_regions: List[EvidenceRegion] = Field(default_factory=list)


class ActivityEventResponse(BaseModel):
    id: int
    event_type: str
    timestamp: datetime
    details: Dict[str, Any] = Field(default_factory=dict)


class HumanReviewSubmission(BaseModel):
    reviewer_name: str = Field(..., min_length=2, max_length=128)
    reviewer_designation: str = Field(..., min_length=2, max_length=128)
    reviewer_organization: Optional[str] = Field(default="SCSS Forensic Laboratory", max_length=128)
    decision: str = Field(..., description="Decision: pending, requires_further_examination, reviewed_no_indicators, reviewed_manipulation_suspected, reviewed_inconclusive")
    notes: str = Field(..., min_length=5, description="Forensic examiner case notes")
    attestation: bool = Field(..., description="Explicit examiner attestation confirmation")


class HumanReviewResponse(BaseModel):
    status: str
    reviewer_name: Optional[str] = None
    reviewer_designation: Optional[str] = None
    reviewer_organization: Optional[str] = None
    notes: Optional[str] = None
    timestamp: Optional[datetime] = None
    attestation: bool = False


class ExaminationOverview(BaseModel):
    examination_id: str
    original_filename: str
    file_size_bytes: int
    detected_media_type: str
    sha256_digest: str
    upload_timestamp: datetime
    capture_timestamp: Optional[datetime] = None
    application_version: str
    analysis_pipeline_version: str
    image_width: int
    image_height: int
    color_mode: str
    status: str
    overall_assessment: str
    decision_assessment: Optional[str] = None
    evidence_strength: Optional[str] = None
    human_review_status: str


class ExaminationDetailResponse(BaseModel):
    examination_id: str
    status: str
    original_filename: str
    file_size_bytes: int
    detected_media_type: str
    image_width: int
    image_height: int
    color_mode: str
    upload_timestamp: datetime
    capture_timestamp: Optional[datetime] = None
    application_version: str
    analysis_pipeline_version: str

    file_integrity: FileIntegrityInfo
    tests: List[ScreeningTestResult]
    overall_assessment: str
    decision_assessment: Optional[str] = None
    evidence_strength: Optional[str] = None
    coverage_score: Optional[float] = None
    decision_output: Optional[DecisionEngineOutput] = None
    detector_results: List[DetectorResult] = Field(default_factory=list)
    image_characterization: Dict[str, Any] = Field(default_factory=dict)

    human_review_status: str
    human_review: HumanReviewResponse
    extracted_metadata: Dict[str, Any] = Field(default_factory=dict)
    known_limitations: List[str] = Field(default_factory=list)
    suggested_manual_checks: List[str] = Field(default_factory=list)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    activity_events: List[ActivityEventResponse] = Field(default_factory=list)
    report_generated_at: Optional[datetime] = None
    disclaimer: str


class IntegrityCheckResponse(BaseModel):
    examination_id: str
    stored_digest: str
    recomputed_digest: str
    match: bool
    algorithm: str = "SHA-256"
    checked_at: datetime
    status: Optional[str] = None
    message: Optional[str] = None


class DashboardStatsResponse(BaseModel):
    total_examinations: int = 0
    recent_examinations_count: int = 0
    pending_review_count: int = 0
    reviewed_count: int = 0
    requires_further_review_count: int = 0
    reports_generated_count: int = 0
    preliminary_notice: str
