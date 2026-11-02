"""Run the six committed Samples as a paired operational baseline.

The three control files are original phone images. The three trial files are
ChatGPT-modified derivatives. This paired convenience set is NOT an independent
validation dataset and must not be used to publish accuracy/calibration metrics.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[3]
SAMPLES = ROOT / "Samples"
BASE_URL = "http://127.0.0.1:8000"
PAIRS = [
    ("Media - Control sample 1.jpg", "Media - Trial sample 1.jpg"),
    ("Media - Control sample 2.jpg", "Media - Trial sample 2.jpg"),
    ("Media - Control sample 3.jpg", "Media - Trial sample 3.jpg"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def upload(client: httpx.Client, path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    response = client.post(
        "/api/examinations",
        files={"file": (path.name, payload, "image/jpeg")},
        timeout=180.0,
    )
    response.raise_for_status()
    result = response.json()
    return {
        "file": path.name,
        "sha256_local": sha256(path),
        "http_status": response.status_code,
        "examination_id": result.get("examination_id"),
        "application_version": result.get("application_version"),
        "pipeline_version": result.get("analysis_pipeline_version"),
        "decision_assessment": result.get("decision_assessment"),
        "decision_confidence": result.get("decision_confidence"),
        "evidence_strength": result.get("evidence_strength"),
        "coverage_score": result.get("coverage_score"),
        "human_review_status": result.get("human_review_status"),
        "tests": [
            {
                "method": item.get("method"),
                "status": item.get("status"),
                "indicator": item.get("indicator"),
                "score": item.get("score"),
                "confidence": item.get("confidence"),
            }
            for item in result.get("tests", [])
        ],
        "detectors": [
            {
                "name": item.get("detector_name"),
                "status": item.get("status"),
                "score": item.get("score"),
                "confidence": item.get("confidence"),
                "applicable": item.get("applicable"),
                "error_code": item.get("error_code"),
            }
            for item in result.get("detector_results", [])
        ],
    }


def main() -> int:
    missing = [str(SAMPLES / name) for pair in PAIRS for name in pair if not (SAMPLES / name).is_file()]
    if missing:
        print(json.dumps({"error": "Sample files missing", "missing": missing}, indent=2))
        return 2

    records = []
    with httpx.Client(base_url=BASE_URL) as client:
        health = client.get("/api/health")
        health.raise_for_status()
        for index, (control_name, trial_name) in enumerate(PAIRS, start=1):
            control = upload(client, SAMPLES / control_name)
            trial = upload(client, SAMPLES / trial_name)
            records.append({
                "pair": index,
                "relationship": "same pair index; original vs ChatGPT-modified",
                "control": control,
                "trial": trial,
                "sha256_equal": control["sha256_local"] == trial["sha256_local"],
                "assessment_changed": control["decision_assessment"] != trial["decision_assessment"],
                "confidence_values": [control["decision_confidence"], trial["decision_confidence"]],
            })

    report = {
        "report_type": "paired_sample_operational_baseline",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "api_base": BASE_URL,
        "health": health.json(),
        "pair_count": len(records),
        "specimen_count": len(records) * 2,
        "labels": {
            "control": "phone-captured originals as described by the user",
            "trial": "ChatGPT-modified images as described by the user",
            "independent_adjudication": False,
        },
        "accuracy_metrics_available": False,
        "calibration_metrics_available": False,
        "interpretation": (
            "Descriptive operational comparison only. Six specimens from three related "
            "pairs are not independent, are not a representative dataset, and cannot "
            "support general detector accuracy or probability calibration claims."
        ),
        "pairs": records,
    }
    output = ROOT / "storage" / "reports" / "paired_samples_operational_baseline.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report_path": str(output), "specimens": 6, "pairs": 3}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
