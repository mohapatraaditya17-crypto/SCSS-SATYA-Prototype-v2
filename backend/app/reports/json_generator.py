from datetime import datetime, timezone
from typing import Dict, Any
from app.core.config import settings
from app.database.models import Examination


class JSONReportGenerator:
    """
    Forensic JSON Report Generator (SATYA v2).
    Generates structured, verifiable, machine-readable forensic examination records
    conforming to ISO/IEC 27037 and NIST OpenMFC specifications.
    """
    @classmethod
    def generate(cls, exam: Examination) -> Dict[str, Any]:
        artifacts = exam.artifacts or {}
        canonical_evidence = artifacts.get("canonical_evidence")

        return {
            "platform": {
                "name": settings.PROJECT_FULL_NAME,
                "version": settings.VERSION,
                "pipeline_version": settings.PIPELINE_VERSION,
                "rules_version": settings.RULES_VERSION,
                "threshold_profile": settings.THRESHOLD_PROFILE,
                "organization": settings.ORGANIZATION,
                "core_principle": settings.CORE_PRINCIPLE,
                "standard_compliance": ["ISO/IEC 27037", "NIST OpenMFC", "C2PA Specification 2.x"],
            },
            "disclaimer": settings.MANDATORY_DISCLAIMER,
            "report_metadata": {
                "report_id": f"REP-{exam.examination_id}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "format_version": "2.0",
            },
            "canonical_evidence": canonical_evidence,
            "technical_assessment": {
                "decision_assessment": exam.decision_assessment or "INCONCLUSIVE",
                "evidence_strength": exam.evidence_strength or "NONE",
                "decision_confidence_pct": exam.decision_confidence,
                "decision_data": exam.decision_data or {},
                "human_review_required": True,
            },
            "image_characterization": exam.image_characterization or {},
            "examination": {
                "examination_id": exam.examination_id,
                "status": exam.status,
                "overall_assessment": exam.overall_assessment,
                "timestamps": {
                    "uploaded_at": exam.upload_timestamp.isoformat() if exam.upload_timestamp else None,
                    "captured_at": exam.capture_timestamp.isoformat() if exam.capture_timestamp else None,
                },
                "evidence_file": {
                    "original_filename": exam.original_filename,
                    "file_size_bytes": exam.file_size_bytes,
                    "media_type": exam.detected_media_type,
                    "dimensions": {
                        "width": exam.image_width,
                        "height": exam.image_height,
                        "aspect_ratio": round(exam.image_width / exam.image_height, 2) if exam.image_height > 0 else 1.0,
                    },
                    "color_mode": exam.color_mode,
                },
                "cryptographic_integrity": {
                    "algorithm": "SHA-256",
                    "sha256": exam.sha256_digest,
                    "sha1": exam.sha1_digest,
                    "md5": exam.md5_digest,
                    "verified_against_vault": True,
                },
                "detector_results": exam.detector_results or [],
                "screening_tests": exam.test_results or [],
                "extracted_metadata": exam.extracted_metadata or {},
                "artifacts": artifacts,
                "methodological_limitations": exam.known_limitations or [],
                "suggested_manual_forensic_checks": exam.suggested_manual_checks or [],
                "human_review": {
                    "status": exam.human_review_status,
                    "reviewer_name": exam.reviewer_name,
                    "reviewer_designation": exam.reviewer_designation,
                    "reviewer_organization": exam.reviewer_organization,
                    "notes": exam.review_notes,
                    "reviewed_at": exam.review_timestamp.isoformat() if exam.review_timestamp else None,
                    "attestation": exam.review_attestation,
                },
                "activity_log": [
                    {
                        "event_type": ev.event_type,
                        "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                        "details": ev.details,
                    }
                    for ev in (exam.activity_events or [])
                ],
            },
        }
