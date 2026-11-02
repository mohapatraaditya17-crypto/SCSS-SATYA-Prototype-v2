import json

from app.evaluation.evaluate_historical_run import evaluate_historical_dataset


def test_historical_csv_is_reported_as_operational_only(tmp_path):
    csv_path = tmp_path / "old.csv"
    csv_path.write_text(
        "path,http_status,examination_id,overall_assessment,indicators,seconds,error\n"
        "test_images/authentic/a.jpg,201,x,requires_human_review,ela=NO_INDICATOR_DETECTED,1.2,\n"
        "test_images/tampered/b.jpg,201,y,requires_human_review,ela=INCONCLUSIVE,2.4,\n",
        encoding="utf-8",
    )
    result = evaluate_historical_dataset(csv_path)
    assert result["dataset_rows"] == 2
    assert result["label_status"] == "NOT_INDEPENDENTLY_ADJUDICATED"
    assert result["accuracy_metrics_available"] is False
    assert result["calibration_metrics_available"] is False
    assert result["path_strata_are_ground_truth"] is False
    assert "overall_system_confusion_matrix" not in result
    assert result["runtime_seconds"]["mean"] == 1.8
