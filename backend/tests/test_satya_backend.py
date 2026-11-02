import io
import os
import hashlib
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.core.config import settings
from app.database.session import SessionLocal, engine, Base
from app.database.models import Examination, ActivityEvent

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    from app.database.session import run_migrations
    run_migrations()
    yield


def generate_test_jpeg(width=300, height=200, color=(100, 150, 200)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def generate_test_png(width=200, height=200) -> bytes:
    img = Image.new("RGB", (width, height), color=(50, 80, 120))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# 1. Health & Version Endpoints
def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "pipeline_version" in data


def test_version_endpoint():
    response = client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == settings.VERSION
    assert "methods" in data
    assert "disclaimer" in data


# 2. SHA-256 Correctness against Independent Expected Digest
def test_sha256_hashing_correctness():
    raw_bytes = generate_test_jpeg()
    expected_hash = hashlib.sha256(raw_bytes).hexdigest()

    response = client.post(
        "/api/examinations",
        files={"file": ("test_hash.jpg", raw_bytes, "image/jpeg")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["file_integrity"]["digest"] == expected_hash
    assert data["file_integrity"]["algorithm"] == "SHA-256"


# 3. Valid Uploads (JPEG & PNG)
def test_valid_jpeg_upload():
    raw_bytes = generate_test_jpeg()
    response = client.post(
        "/api/examinations",
        files={"file": ("camera_photo.jpg", raw_bytes, "image/jpeg")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "completed"
    assert data["detected_media_type"] == "image/jpeg"
    assert data["image_width"] == 300
    assert data["image_height"] == 200
    assert len(data["tests"]) >= 12

    # Verify ELA ran for JPEG
    ela_test = next(t for t in data["tests"] if t["method"] == "error_level_analysis")
    assert ela_test["status"] == "completed"
    assert "ela_heatmap" in data["artifacts"]

    # Verify Noise, FFT, CopyMove, AI Generative, and Typography tests ran
    assert any(t["method"] == "noise_residual_analysis" for t in data["tests"])
    assert any(t["method"] == "fourier_spectral_analysis" for t in data["tests"])
    assert any(t["method"] == "copy_move_forgery_detection" for t in data["tests"])
    assert any(t["method"] == "ai_generative_classifier" for t in data["tests"])
    # Typography is correctly not applicable to a natural photograph; verify its gated result exists.\n    assert any(t["status"] == "not_applicable" and "Typography" in t["method"] for t in data["tests"])
    assert "noise_residual_map" in data["artifacts"]
    assert "fft_spectrum" in data["artifacts"]
    assert "copymove_map" in data["artifacts"]
    assert "ai_synthetic_map" in data["artifacts"]
    # typography_map is generated when glyphs are detected (blank test image has 0 glyphs)


def test_valid_png_upload():
    raw_bytes = generate_test_png()
    response = client.post(
        "/api/examinations",
        files={"file": ("diagram.png", raw_bytes, "image/png")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["detected_media_type"] == "image/png"

    # ELA must be honestly identified as unavailable for PNG
    ela_test = next(t for t in data["tests"] if t["method"] == "error_level_analysis")
    assert ela_test["status"] == "not_applicable"
    assert ela_test["indicator"] == "test_unavailable"


# 4. Error Handling: Unsupported Format
def test_unsupported_file_type():
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
    response = client.post(
        "/api/examinations",
        files={"file": ("payload.exe", fake_exe, "application/octet-stream")}
    )
    assert response.status_code == 400
    assert "Unsupported or invalid file format" in response.json()["detail"]


# 5. Error Handling: Corrupted Bytes
def test_corrupted_image_file():
    corrupted_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00corrupted_garbage_stream"
    response = client.post(
        "/api/examinations",
        files={"file": ("corrupt.jpg", corrupted_bytes, "image/jpeg")}
    )
    assert response.status_code == 400
    assert "Corrupted or invalid image stream" in response.json()["detail"]


# 6. Error Handling: Oversized File
def test_oversized_file_rejection(monkeypatch):
    # Set limit to 100 KB temporarily for testing
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 50 * 1024)
    oversized_bytes = b"\xFF\xD8\xFF" + b"\x00" * (60 * 1024)
    response = client.post(
        "/api/examinations",
        files={"file": ("huge.jpg", oversized_bytes, "image/jpeg")}
    )
    assert response.status_code == 400
    assert "exceeds maximum permitted limit" in response.json()["detail"]


# 7. Examination History and Retrieval
def test_examination_history_and_retrieval():
    raw_bytes = generate_test_jpeg(width=240, height=180)
    create_res = client.post(
        "/api/examinations",
        files={"file": ("sample_history.jpg", raw_bytes, "image/jpeg")}
    )
    assert create_res.status_code == 201
    created = create_res.json()
    exam_id = created["examination_id"]

    # Retrieve single record
    get_res = client.get(f"/api/examinations/{exam_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["examination_id"] == exam_id
    assert retrieved["file_integrity"]["digest"] == created["file_integrity"]["digest"]

    # List records
    list_res = client.get("/api/examinations?limit=10")
    assert list_res.status_code == 200
    records = list_res.json()
    assert any(r["examination_id"] == exam_id for r in records)


# 8. Cryptographic Integrity Check (Matching & Tampered)
def test_integrity_check():
    raw_bytes = generate_test_jpeg()
    create_res = client.post(
        "/api/examinations",
        files={"file": ("integrity_test.jpg", raw_bytes, "image/jpeg")}
    )
    exam_id = create_res.json()["examination_id"]

    # Check 1: Matching
    integ_res = client.get(f"/api/examinations/{exam_id}/integrity")
    assert integ_res.status_code == 200
    assert integ_res.json()["match"] is True
    assert integ_res.json()["status"] == "VERIFIED"

    # Check 2: Alter vault file to simulate tampering
    db = SessionLocal()
    exam = db.query(Examination).filter(Examination.examination_id == exam_id).first()
    vault_file = settings.VAULT_DIR / exam.stored_filename

    # Tamper with stored bitstream
    with open(vault_file, "ab") as f:
        f.write(b"TAMPER_PAYLOAD")

    integ_res2 = client.get(f"/api/examinations/{exam_id}/integrity")
    assert integ_res2.status_code == 200
    assert integ_res2.json()["match"] is False
    assert integ_res2.json()["status"] == "INTEGRITY_MISMATCH"
    db.close()


# 9. Human Forensic Review Workflow
def test_human_review_submission():
    raw_bytes = generate_test_jpeg()
    create_res = client.post(
        "/api/examinations",
        files={"file": ("review_case.jpg", raw_bytes, "image/jpeg")}
    )
    exam_id = create_res.json()["examination_id"]

    # Attempt review without attestation (must fail)
    bad_review = {
        "reviewer_name": "Dr. A. Dixit",
        "reviewer_designation": "Chief Forensic Examiner",
        "decision": "reviewed_no_indicators",
        "notes": "Preliminary manual checks complete. Lighting and shadows consistent.",
        "attestation": False,
    }
    fail_res = client.post(f"/api/examinations/{exam_id}/review", json=bad_review)
    assert fail_res.status_code == 400

    # Successful review with attestation
    good_review = {
        "reviewer_name": "Dr. A. Dixit",
        "reviewer_designation": "Chief Forensic Examiner",
        "reviewer_organization": "Sure Clue Scientific Solutions",
        "decision": "reviewed_no_indicators",
        "notes": "Preliminary manual checks complete. Lighting and shadows consistent across specimen.",
        "attestation": True,
    }
    ok_res = client.post(f"/api/examinations/{exam_id}/review", json=good_review)
    assert ok_res.status_code == 200
    updated = ok_res.json()
    assert updated["human_review_status"] == "reviewed_no_indicators"
    assert updated["human_review"]["reviewer_name"] == "Dr. A. Dixit"
    assert updated["human_review"]["attestation"] is True


# 10. Reports: JSON & PDF
def test_json_and_pdf_report_generation():
    raw_bytes = generate_test_jpeg()
    create_res = client.post(
        "/api/examinations",
        files={"file": ("report_case.jpg", raw_bytes, "image/jpeg")}
    )
    exam_id = create_res.json()["examination_id"]

    # JSON Report
    json_res = client.get(f"/api/examinations/{exam_id}/report")
    assert json_res.status_code == 200
    report_data = json_res.json()
    assert report_data["examination"]["examination_id"] == exam_id
    assert "disclaimer" in report_data
    assert len(report_data["examination"]["screening_tests"]) >= 12

    # PDF Report
    pdf_res = client.get(f"/api/examinations/{exam_id}/report.pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000  # Non-empty valid PDF bytes
    assert pdf_res.content.startswith(b"%PDF-")  # Valid PDF header


# 11. Security: Path Traversal Protection
def test_path_traversal_protection():
    # Attempt to request file with path traversal in examination ID
    res = client.get("/api/examinations/..%2F..%2Fetc%2Fpasswd")
    assert res.status_code in [404, 422]


# 12. Dashboard Statistics Endpoint
def test_dashboard_stats_endpoint():
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_examinations" in data
    assert "pending_review_count" in data
    assert "preliminary_notice" in data
    assert data["total_examinations"] >= 1


# 13. Visualization & Evidence Image Endpoints
def test_visualization_and_image_endpoints():
    raw_bytes = generate_test_jpeg()
    create_res = client.post(
        "/api/examinations",
        files={"file": ("vis_test.jpg", raw_bytes, "image/jpeg")}
    )
    exam_id = create_res.json()["examination_id"]

    # Image preview endpoint
    img_res = client.get(f"/api/examinations/{exam_id}/image")
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/jpeg"
    assert len(img_res.content) == len(raw_bytes)

    # ELA heatmap visualization endpoint
    ela_res = client.get(f"/api/examinations/{exam_id}/visualizations/ela_heatmap")
    assert ela_res.status_code == 200
    assert ela_res.headers["content-type"] == "image/png"


# 14. Frontend SPA Mount
def test_frontend_spa_serving():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert b"<!doctype html>" in res.content.lower() or b"<html>" in res.content.lower()

# 15. Nullable confidence and v2 taxonomy API contract
def test_api_exposes_nullable_confidence_and_current_decision_taxonomy():
    raw_bytes = generate_test_jpeg()
    created = client.post(
        "/api/examinations",
        files={"file": ("contract_case.jpg", raw_bytes, "image/jpeg")},
    )
    assert created.status_code == 201
    data = created.json()

    assert data["decision_assessment"] in {
        "MANIPULATION_INDICATORS_DETECTED",
        "AI_GENERATION_INDICATORS_DETECTED",
        "PROVENANCE_VERIFIED",
        "PROVENANCE_CONFLICT",
        "NO_MANIPULATION_INDICATORS_DETECTED",
        "INCONCLUSIVE",
        "INSUFFICIENT_EVIDENCE",
        "UNSUPPORTED_FORMAT",
        "ERROR",
    }
    # No calibrator is registered: the API must preserve null, not fabricate 50.
    assert data["decision_confidence"] is None

    detail = client.get(f"/api/examinations/{data['examination_id']}")
    assert detail.status_code == 200
    assert detail.json()["decision_confidence"] is None

    history = client.get("/api/examinations?limit=10")
    assert history.status_code == 200
    matching = next(item for item in history.json() if item["examination_id"] == data["examination_id"])
    assert matching["decision_confidence"] is None
