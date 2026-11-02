import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings


def evaluate_historical_dataset(csv_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Summarize prior executions as an operational baseline only.

    This CSV does not contain independently adjudicated labels or calibrated
    predictions. Folder names in specimen paths are descriptive strata, not
    ground truth. Consequently this function deliberately emits no confusion
    matrix, accuracy, precision, recall, or calibration statistics.
    """
    if csv_path is None:
        csv_path = settings.ROOT_DIR / "results.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Historical results file not found at {csv_path}")

    total = 0
    http_statuses: Counter[str] = Counter()
    overall_statuses: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    runtimes: list[float] = []
    path_strata: Counter[str] = Counter()
    detector_statuses: dict[str, Counter[str]] = defaultdict(Counter)

    with open(csv_path, mode="r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"path", "http_status", "overall_assessment", "indicators", "seconds", "error"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Historical CSV missing required columns: {sorted(missing)}")

        for row_number, row in enumerate(reader, start=2):
            total += 1
            http_statuses[str(row.get("http_status", "") or "MISSING")] += 1
            overall_statuses[str(row.get("overall_assessment", "") or "MISSING")] += 1

            path_lower = str(row.get("path", "")).replace("\\", "/").lower()
            # Descriptive path stratum only. Never promote this to a ground-truth label.
            if "/authentic/" in path_lower or "/control/" in path_lower:
                path_strata["path_named_authentic_or_control"] += 1
            elif "/tampered/" in path_lower or "/trial/" in path_lower:
                path_strata["path_named_tampered_or_trial"] += 1
            else:
                path_strata["other_or_unknown"] += 1

            try:
                runtime = float(row.get("seconds", "") or "nan")
                if runtime >= 0:
                    runtimes.append(runtime)
            except (TypeError, ValueError):
                error_counts["invalid_runtime_value"] += 1

            if row.get("error"):
                error_counts["row_error_present"] += 1

            for item in str(row.get("indicators", "") or "").split(";"):
                if "=" not in item:
                    continue
                detector, state = item.strip().split("=", 1)
                detector_statuses[detector.strip()][state.strip().upper()] += 1

    summary: Dict[str, Any] = {
        "report_type": "historical_operational_baseline",
        "dataset_rows": total,
        "label_status": "NOT_INDEPENDENTLY_ADJUDICATED",
        "path_strata_are_ground_truth": False,
        "accuracy_metrics_available": False,
        "calibration_metrics_available": False,
        "http_status_counts": dict(http_statuses),
        "overall_assessment_counts": dict(overall_statuses),
        "descriptive_path_strata": dict(path_strata),
        "detector_status_counts": {
            detector: dict(counts) for detector, counts in sorted(detector_statuses.items())
        },
        "row_error_counts": dict(error_counts),
        "runtime_seconds": {
            "count": len(runtimes),
            "total": round(sum(runtimes), 4),
            "mean": round(sum(runtimes) / len(runtimes), 4) if runtimes else None,
            "min": round(min(runtimes), 4) if runtimes else None,
            "max": round(max(runtimes), 4) if runtimes else None,
        },
        "limitations": [
            "The historical CSV is an execution log, not an independently labelled validation manifest.",
            "Directory names in specimen paths are descriptive strata and were not used as ground truth.",
            "The run's overall assessment was not a calibrated binary prediction.",
            "Accuracy, confusion matrices, and calibration claims require specimen-level adjudicated labels and a locked evaluation protocol.",
        ],
    }

    reports_dir = settings.STORAGE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_out = reports_dir / "historical_operational_baseline.json"
    md_out = reports_dir / "historical_operational_baseline.md"
    json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    markdown = [
        "# Historical operational baseline",
        "",
        f"- Rows: **{total}**",
        "- Independently adjudicated labels: **No**",
        "- Accuracy/calibration claims: **Not available from this file**",
        "",
        "This is an execution/coverage summary only. Folder labels were not treated as ground truth.",
        "",
        "## HTTP status counts",
    ]
    markdown.extend(f"- {key}: {value}" for key, value in sorted(http_statuses.items()))
    markdown.extend(["", "## Overall assessment counts"])
    markdown.extend(f"- {key}: {value}" for key, value in sorted(overall_statuses.items()))
    markdown.extend(["", "## Detector status counts"])
    for detector, counts in sorted(detector_statuses.items()):
        markdown.append(f"- {detector}: " + ", ".join(f"{state}={count}" for state, count in sorted(counts.items())))
    markdown.extend(["", "## Limitations", *[f"- {item}" for item in summary["limitations"]]])
    md_out.write_text("\\n".join(markdown) + "\\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    results = evaluate_historical_dataset()
    print(json.dumps(results, indent=2))
