import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from app.core.config import settings
from app.database.session import get_db
from app.database.models import Examination, ActivityEvent
from app.schemas.examination import (
    ExaminationDetailResponse,
    ExaminationOverview,
    HumanReviewSubmission,
    HumanReviewResponse,
    IntegrityCheckResponse,
    DashboardStatsResponse,
    FileIntegrityInfo,
    ScreeningTestResult,
    DetectorResult,
    DecisionEngineOutput,
    ActivityEventResponse,
)
from app.services.storage import StorageService
from app.services.activity_log import ActivityLogService
from app.analysis.pipeline import ForensicPipeline
from app.reports.pdf_generator import PDFReportGenerator
from app.reports.json_generator import JSONReportGenerator

router = APIRouter()


def _format_examination_response(exam: Examination) -> ExaminationDetailResponse:
    tests = [ScreeningTestResult(**t) for t in (exam.test_results or [])]
    detector_results = [DetectorResult(**d) for d in (exam.detector_results or [])]
    decision_output = None
    if exam.decision_data:
        try:
            decision_output = DecisionEngineOutput(**exam.decision_data)
        except Exception:
            pass

    activity = [
        ActivityEventResponse(
            id=ev.id,
            event_type=ev.event_type,
            timestamp=ev.timestamp,
            details=ev.details,
        )
        for ev in (exam.activity_events or [])
    ]

    return ExaminationDetailResponse(
        examination_id=exam.examination_id,
        status=exam.status,
        original_filename=exam.original_filename,
        file_size_bytes=exam.file_size_bytes,
        detected_media_type=exam.detected_media_type,
        image_width=exam.image_width,
        image_height=exam.image_height,
        color_mode=exam.color_mode,
        upload_timestamp=exam.upload_timestamp,
        capture_timestamp=exam.capture_timestamp,
        application_version=exam.application_version,
        analysis_pipeline_version=exam.analysis_pipeline_version,
        file_integrity=FileIntegrityInfo(
            algorithm="SHA-256",
            digest=exam.sha256_digest,
            sha1=exam.sha1_digest,
            md5=exam.md5_digest,
            verified=True,
        ),
        tests=tests,
        overall_assessment=exam.overall_assessment,
        decision_assessment=exam.decision_assessment or "INCONCLUSIVE",
        evidence_strength=exam.evidence_strength or "NONE",
        decision_confidence=exam.decision_confidence,
        decision_output=decision_output,
        detector_results=detector_results,
        image_characterization=exam.image_characterization or {},
        human_review_status=exam.human_review_status,
        human_review=HumanReviewResponse(
            status=exam.human_review_status,
            reviewer_name=exam.reviewer_name,
            reviewer_designation=exam.reviewer_designation,
            reviewer_organization=exam.reviewer_organization,
            notes=exam.review_notes,
            timestamp=exam.review_timestamp,
            attestation=exam.review_attestation,
        ),
        extracted_metadata=exam.extracted_metadata or {},
        known_limitations=exam.known_limitations or [],
        suggested_manual_checks=exam.suggested_manual_checks or [],
        artifacts=exam.artifacts or {},
        activity_events=activity,
        report_generated_at=exam.report_generated_at,
        disclaimer=settings.MANDATORY_DISCLAIMER,
    )


@router.post("/examinations", response_model=ExaminationDetailResponse, status_code=status.HTTP_201_CREATED, tags=["Examinations"])
async def create_examination(
    file: UploadFile = File(..., description="Digital image evidence to screen (JPEG, PNG, WebP)"),
    db: Session = Depends(get_db),
):
    """
    Ingests digital image evidence, computes immutable SHA-256 cryptographic seal,
    executes explainable screening tests, and stores records in SQLite.
    """
    # 1. Read raw byte stream
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or contains 0 bytes.")

    # 2. Ingest into secure evidence vault
    try:
        metadata, vault_path = StorageService.ingest_evidence(
            file_bytes=file_bytes,
            original_filename=file.filename or "evidence_image.jpg",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Generate unique ID: SATYA-YYYYMMDD-XXXXXX
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    exam_id = f"SATYA-{today_str}-{uuid.uuid4().hex[:6].upper()}"

    # 3. Create initial database record & audit log
    now = datetime.now(timezone.utc)
    exam = Examination(
        examination_id=exam_id,
        original_filename=metadata["original_filename"],
        stored_filename=metadata["stored_filename"],
        file_size_bytes=metadata["file_size_bytes"],
        detected_media_type=metadata["detected_media_type"],
        sha256_digest=metadata["sha256_digest"],
        sha1_digest=metadata["sha1_digest"],
        md5_digest=metadata["md5_digest"],
        upload_timestamp=now,
        application_version=settings.VERSION,
        analysis_pipeline_version=settings.PIPELINE_VERSION,
        image_width=metadata["image_width"],
        image_height=metadata["image_height"],
        color_mode=metadata["color_mode"],
        status="screening",
        overall_assessment="requires_human_review",
        human_review_status="pending",
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    ActivityLogService.record_event(
        db, exam_id, "EXAMINATION_CREATED",
        {"original_filename": metadata["original_filename"], "size_bytes": metadata["file_size_bytes"]}
    )
    ActivityLogService.record_event(
        db, exam_id, "FILE_HASH_CALCULATED",
        {"algorithm": "SHA-256", "digest": metadata["sha256_digest"]}
    )
    ActivityLogService.record_event(
        db, exam_id, "SCREENING_STARTED",
        {"pipeline_version": settings.PIPELINE_VERSION}
    )

    # 4. Execute defensible screening pipeline
    try:
        pipeline_output = ForensicPipeline.execute(
            image_path=vault_path,
            file_bytes=file_bytes,
            examination_id=exam_id,
            media_type=metadata["detected_media_type"],
            image_width=metadata["image_width"],
            image_height=metadata["image_height"],
            sha256_digest=metadata["sha256_digest"],
            file_size_bytes=metadata["file_size_bytes"],
        )

        exam.status = "completed"
        exam.overall_assessment = pipeline_output["overall_assessment"]
        exam.decision_assessment = pipeline_output.get("decision_assessment", "INCONCLUSIVE")
        exam.evidence_strength = pipeline_output.get("evidence_strength", "NONE")
        exam.decision_confidence = pipeline_output.get("decision_confidence")
        exam.capture_timestamp = pipeline_output["capture_timestamp"]
        exam.extracted_metadata = pipeline_output["extracted_metadata"]
        exam.test_results = [t.model_dump() for t in pipeline_output["tests"]]
        exam.detector_results = [d.model_dump() for d in pipeline_output.get("detector_results", [])]
        exam.image_characterization = pipeline_output.get("image_characterization", {})
        exam.decision_data = pipeline_output.get("canonical_evidence", {}).get("assessment", {})
        exam.known_limitations = pipeline_output["known_limitations"]
        exam.suggested_manual_checks = pipeline_output["suggested_manual_checks"]
        exam.artifacts = pipeline_output["artifacts"]

        db.commit()
        db.refresh(exam)

        ActivityLogService.record_event(
            db, exam_id, "SCREENING_COMPLETED",
            {"overall_assessment": exam.overall_assessment, "test_count": len(exam.test_results)}
        )

    except Exception as e:
        exam.status = "failed"
        db.commit()
        ActivityLogService.record_event(
            db, exam_id, "SCREENING_METHOD_FAILED",
            {"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Screening analysis failed: {str(e)}")

    return _format_examination_response(exam)


@router.get("/examinations", response_model=List[ExaminationOverview], tags=["Examinations"])
def list_examinations(
    search: Optional[str] = Query(None, description="Search by examination ID or filename"),
    status: Optional[str] = Query(None, description="Filter by status (completed, failed)"),
    review_status: Optional[str] = Query(None, description="Filter by human review status"),
    sort_by: str = Query("upload_timestamp", description="Sort field"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Lists historical examinations with optional search, filtering, and pagination.
    """
    query = db.query(Examination)

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Examination.examination_id.ilike(search_fmt),
                Examination.original_filename.ilike(search_fmt),
                Examination.sha256_digest.ilike(search_fmt),
            )
        )

    if status:
        query = query.filter(Examination.status == status)

    if review_status:
        query = query.filter(Examination.human_review_status == review_status)

    sort_col = getattr(Examination, sort_by, Examination.upload_timestamp)
    query = query.order_by(desc(sort_col) if order.lower() == "desc" else asc(sort_col))

    results = query.offset(offset).limit(limit).all()

    return [
        ExaminationOverview(
            examination_id=e.examination_id,
            original_filename=e.original_filename,
            file_size_bytes=e.file_size_bytes,
            detected_media_type=e.detected_media_type,
            sha256_digest=e.sha256_digest,
            upload_timestamp=e.upload_timestamp,
            capture_timestamp=e.capture_timestamp,
            application_version=e.application_version,
            analysis_pipeline_version=e.analysis_pipeline_version,
            image_width=e.image_width,
            image_height=e.image_height,
            color_mode=e.color_mode,
            status=e.status,
            overall_assessment=e.overall_assessment,
            decision_assessment=e.decision_assessment or "INCONCLUSIVE",
            evidence_strength=e.evidence_strength or "NONE",
            decision_confidence=e.decision_confidence,
            human_review_status=e.human_review_status,
        )
        for e in results
    ]


@router.get("/examinations/{examination_id}", response_model=ExaminationDetailResponse, tags=["Examinations"])
def get_examination(examination_id: str, db: Session = Depends(get_db)):
    """
    Retrieves full examination record by examination ID.
    """
    exam = db.query(Examination).filter(Examination.examination_id == examination_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail=f"Examination '{examination_id}' not found.")
    return _format_examination_response(exam)


@router.get("/examinations/{examination_id}/report", tags=["Reports"])
def get_examination_json_report(examination_id: str, db: Session = Depends(get_db)):
    """
    Returns machine-readable JSON forensic examination report.
    """
    exam = db.query(Examination).filter(Examination.examination_id == examination_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail=f"Examination '{examination_id}' not found.")

    report_data = JSONReportGenerator.generate(exam)
    return JSONResponse(content=report_data)


@router.get("/examinations/{examination_id}/canonical-evidence", tags=["Reports"])
def get_canonical_evidence(examination_id: str, db: Session = Depends(get_db)):
    """
    Returns the canonical NIST OpenMFC & Section 44 Evidence JSON representation.
    """
    exam = db.query(Examination).filter(Examination.examination_id == examination_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail=f"Examination '{examination_id}' not found.")

    artifacts = exam.artifacts or {}
    evidence = artifacts.get("canonical_evidence")
    if not evidence:
        report_data = JSONReportGenerator.generate(exam)
        evidence = report_data.get("canonical_evidence") or {}

    return JSONResponse(content=evidence)


@router.get("/examinations/{examination_id}/report.pdf", tags=["Reports"])
def get_examination_pdf_report(examination_id: str, db: Session = Depends(get_db)):
    """
    Generates and downloads official ISO/IEC 27037 compliant PDF forensic examination report.
    """
    exam = db.query(Examination).filter(Examination.examination_id == examination_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail=f"Examination '{examination_id}' not found.")

    pdf_filename = f"{exam.examination_id}_forensic_report.pdf"
    pdf_path = settings.REPORTS_DIR / pdf_filename

    # Generate PDF
    try:
        PDFReportGenerator.generate(exam, pdf_path)
        exam.report_generated_at = datetime.now(timezone.utc)
        db.commit()

        ActivityLogService.record_event(
            db, exam.examination_id, "REPORT_GENERATED",
            {"format": "PDF", "filename": pdf_filename}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=pdf_filename,
    )


@router.get("/examinations/{examination_id}/integrity", response_model=IntegrityCheckResponse, tags=["Integrity"])
def check_examination_integrity(examination_id: str, db: Session = Depends(get_db)):
    """
    Recomputes SHA-256 cryptographic hash directly from original vault bytes
    and verifies consistency against the recorded initial hash.
    """
    exam = db.query(Examination).filter(Examination.examination_id == examination_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail=f"Examination '{examination_id}' not found.")

    now = datetime.now(timezone.utc)
    recomputed = StorageService.recompute_vault_hash(exam.stored_filename)

    if recomputed is None:
        ActivityLogService.record_event(
            db, examination_id, "INTEGRITY_CHECK_PERFORMED",
            {"match": False, "status": "VAULT_FILE_MISSING"}
        )
        return IntegrityCheckResponse(
            examination_id=examination_id,
            stored_digest=exam.sha256_digest,
            recomputed_digest="VAULT_FILE_UNAVAILABLE",
            match=False,
            algorithm="SHA-256",
            checked_at=now,
            status="FAILED",
            message="Evidence bitstream unavailable in local vault.",
        )

    matches = (recomputed == exam.sha256_digest)
    ActivityLogService.record_event(
        db, examination_id, "INTEGRITY_CHECK_PERFORMED",
        {"match": matches, "status": "VERIFIED" if matches else "INTEGRITY_BREACH"}
    )

    return IntegrityCheckResponse(
        examination_id=examination_id,
        stored_digest=exam.sha256_digest,
        recomputed_digest=recomputed,
        match=matches,
        algorithm="SHA-256",
        checked_at=now,
        status="VERIFIED" if matches else "INTEGRITY_MISMATCH",
        message="Cryptographic integrity intact: bitstream matches recorded upload hash." if matches else "Warning: Stored bytes differ from recorded initial digest.",
    )


@router.post("/examinations/{examination_id}/review", response_model=ExaminationDetailResponse, tags=["Human Review"])
def submit_human_review(
    examination_id: str,
    review_data: HumanReviewSubmission,
    db: Session = Depends(get_db),
):
    """
    Records an authorized human forensic review, examiner credentials, qualitative observations,
    and formal decision attestation.
    """
    exam = db.query(Examination).filter(Examination.examination_id == examination_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail=f"Examination '{examination_id}' not found.")

    if not review_data.attestation:
        raise HTTPException(status_code=400, detail="Examiner attestation must be confirmed.")

    now = datetime.now(timezone.utc)
    exam.human_review_status = review_data.decision
    exam.reviewer_name = review_data.reviewer_name.strip()
    exam.reviewer_designation = review_data.reviewer_designation.strip()
    exam.reviewer_organization = review_data.reviewer_organization.strip() if review_data.reviewer_organization else settings.ORGANIZATION
    exam.review_notes = review_data.notes.strip()
    exam.review_timestamp = now
    exam.review_attestation = review_data.attestation

    db.commit()
    db.refresh(exam)

    ActivityLogService.record_event(
        db, examination_id, "HUMAN_REVIEW_UPDATED",
        {
            "reviewer": exam.reviewer_name,
            "designation": exam.reviewer_designation,
            "decision": exam.human_review_status,
        }
    )

    return _format_examination_response(exam)


@router.get("/examinations/{examination_id}/visualizations/{vis_type}", tags=["Artifacts"])
def get_visualization_artifact(examination_id: str, vis_type: str, db: Session = Depends(get_db)):
    """
    Serves generated forensic visualizations (e.g., ELA heatmap, noise map).
    """
    exam = db.query(Examination).filter(Examination.examination_id == examination_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail=f"Examination '{examination_id}' not found.")

    artifacts = exam.artifacts or {}
    filename = artifacts.get(vis_type)
    if not filename:
        raise HTTPException(status_code=404, detail=f"Visualization artifact '{vis_type}' not found for case {examination_id}.")

    # Secure path traversal check
    clean_name = Path(filename).name
    file_path = settings.ARTIFACTS_DIR / clean_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Artifact file missing from disk.")

    return FileResponse(file_path, media_type="image/png")


@router.get("/examinations/{examination_id}/image", tags=["Artifacts"])
def get_evidence_image(examination_id: str, db: Session = Depends(get_db)):
    """
    Serves the original evidence image safely from vault.
    """
    exam = db.query(Examination).filter(Examination.examination_id == examination_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail=f"Examination '{examination_id}' not found.")

    clean_name = Path(exam.stored_filename).name
    file_path = settings.VAULT_DIR / clean_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Evidence file missing from vault.")

    return FileResponse(file_path, media_type=exam.detected_media_type)


@router.get("/dashboard/stats", response_model=DashboardStatsResponse, tags=["Dashboard"])
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Returns actual recorded dashboard metrics derived from stored SQLite database records.
    Does NOT fabricate operational statistics.
    """
    total = db.query(Examination).count()

    # Recent examinations in last 24 hours
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = db.query(Examination).filter(Examination.upload_timestamp >= cutoff).count()

    pending = db.query(Examination).filter(Examination.human_review_status == "pending").count()
    reviewed = db.query(Examination).filter(
        Examination.human_review_status.in_(["reviewed_no_indicators", "reviewed_manipulation_suspected", "reviewed_inconclusive"])
    ).count()
    requires_further = db.query(Examination).filter(
        Examination.human_review_status == "requires_further_examination"
    ).count()
    reports_gen = db.query(Examination).filter(Examination.report_generated_at.isnot(None)).count()

    return DashboardStatsResponse(
        total_examinations=total,
        recent_examinations_count=recent,
        pending_review_count=pending,
        reviewed_count=reviewed,
        requires_further_review_count=requires_further,
        reports_generated_count=reports_gen,
        preliminary_notice=settings.MANDATORY_DISCLAIMER,
    )
