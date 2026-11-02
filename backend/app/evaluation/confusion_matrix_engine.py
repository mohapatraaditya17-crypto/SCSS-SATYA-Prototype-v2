from typing import Dict, Any
from collections import defaultdict
from app.evaluation.metrics import BinaryMetrics


class ConfusionMatrixEngine:
    """Multi-dimensional evaluation; ERROR and NOT_APPLICABLE remain separate states."""
    VERSION = "2.1.0"

    def __init__(self):
        self.system_matrix = {
            "AUTHENTIC": {"AUTHENTIC": 0, "TAMPERED": 0, "REVIEW": 0},
            "TAMPERED": {"AUTHENTIC": 0, "TAMPERED": 0, "REVIEW": 0},
        }
        self.detector_metrics = defaultdict(BinaryMetrics)
        self.detector_status_counts = defaultdict(lambda: {
            "positive": 0, "negative": 0, "inconclusive": 0,
            "error": 0, "not_applicable": 0, "total": 0,
        })
        self.manipulation_breakdown = defaultdict(lambda: defaultdict(lambda: {
            "positive": 0, "negative": 0, "inconclusive": 0,
            "error": 0, "not_applicable": 0, "total": 0,
        }))
        self.image_class_breakdown = defaultdict(lambda: {
            "AUTHENTIC": 0, "TAMPERED": 0, "REVIEW": 0, "total": 0,
        })
        self.source_breakdown = defaultdict(lambda: {
            "AUTHENTIC": 0, "TAMPERED": 0, "REVIEW": 0, "total": 0,
        })
        self.compression_breakdown = defaultdict(lambda: {
            "AUTHENTIC": 0, "TAMPERED": 0, "REVIEW": 0, "total": 0,
        })
        self.coverage = {"applicable": 0, "successful": 0, "error": 0, "not_applicable": 0}

    def record_sample(
        self,
        ground_truth: str,
        system_decision: str,
        detector_observations: Dict[str, str],
        manipulation_type: str = "UNKNOWN",
        image_class: str = "UNKNOWN",
        source_type: str = "UNKNOWN",
        compression_history: str = "UNKNOWN",
    ) -> None:
        gt = ground_truth.upper()
        if gt not in self.system_matrix:
            raise ValueError("ground_truth must be AUTHENTIC or TAMPERED")
        decision = system_decision.upper()
        if "TAMPER" in decision or "MANIPULATION_INDICATORS_DETECTED" in decision:
            prediction = "TAMPERED"
        elif decision in {"LIKELY_AUTHENTIC", "AUTHENTIC"}:
            # Historical import compatibility only. Current v2.1 does not emit this.
            prediction = "AUTHENTIC"
        else:
            prediction = "REVIEW"
        self.system_matrix[gt][prediction] += 1

        for buckets, key in (
            (self.image_class_breakdown, image_class),
            (self.source_breakdown, source_type),
            (self.compression_breakdown, compression_history),
        ):
            buckets[key][prediction] += 1
            buckets[key]["total"] += 1

        for detector, state in detector_observations.items():
            observation = str(state).upper().strip()
            counts = self.detector_status_counts[detector]
            counts["total"] += 1
            metric = self.detector_metrics[detector]
            metric.total += 1
            stratum = self.manipulation_breakdown[manipulation_type][detector]
            stratum["total"] += 1

            if observation in {"POSITIVE", "INDICATOR_DETECTED"}:
                counts["positive"] += 1
                stratum["positive"] += 1
                if gt == "TAMPERED":
                    metric.tp += 1
                else:
                    metric.fp += 1
                self.coverage["applicable"] += 1
                self.coverage["successful"] += 1
            elif observation in {"NEGATIVE", "NO_INDICATOR_DETECTED"}:
                counts["negative"] += 1
                stratum["negative"] += 1
                if gt == "AUTHENTIC":
                    metric.tn += 1
                else:
                    metric.fn += 1
                self.coverage["applicable"] += 1
                self.coverage["successful"] += 1
            elif observation == "NOT_APPLICABLE":
                counts["not_applicable"] += 1
                stratum["not_applicable"] += 1
                self.coverage["not_applicable"] += 1
            elif observation == "ERROR":
                counts["error"] += 1
                stratum["error"] += 1
                self.coverage["applicable"] += 1
                self.coverage["error"] += 1
            else:
                counts["inconclusive"] += 1
                stratum["inconclusive"] += 1
                metric.inconclusive += 1
                self.coverage["applicable"] += 1
                self.coverage["successful"] += 1

    def compute_summary(self) -> Dict[str, Any]:
        detector_metrics = {
            name: metrics.summary_dict()
            for name, metrics in self.detector_metrics.items()
        }
        manipulation = {}
        for kind, detectors in self.manipulation_breakdown.items():
            manipulation[kind] = {}
            for name, counts in detectors.items():
                applicable = counts["total"] - counts["not_applicable"]
                manipulation[kind][name] = {
                    **counts,
                    "positive_rate_pct": round(100 * counts["positive"] / max(1, applicable), 1),
                    "inconclusive_rate_pct": round(100 * counts["inconclusive"] / max(1, applicable), 1),
                }
        denominator = self.coverage["applicable"]
        return {
            "overall_system_confusion_matrix": dict(self.system_matrix),
            "detector_level_confusion_matrices": detector_metrics,
            "detector_status_counts": dict(self.detector_status_counts),
            "manipulation_type_matrix": manipulation,
            "image_class_matrix": dict(self.image_class_breakdown),
            "source_type_matrix": dict(self.source_breakdown),
            "compression_matrix": dict(self.compression_breakdown),
            "coverage": {
                **self.coverage,
                "coverage_score": round(self.coverage["successful"] / denominator, 4) if denominator else None,
            },
        }

    def format_markdown_report(self) -> str:
        summary = self.compute_summary()
        lines = [
            "## SCSS SATYA v2.1 — Forensic Evaluation and Decision Matrix",
            "",
            "Historical operational runs are not independent validation and must not be used as accuracy claims without adjudicated ground truth.",
            "",
            "### Overall system matrix",
            "| Ground truth | Authentic | Tampered indicators | Review |",
            "|---|---:|---:|---:|",
        ]
        for label, counts in sorted(summary["overall_system_confusion_matrix"].items()):
            lines.append(f"| {label} | {counts['AUTHENTIC']} | {counts['TAMPERED']} | {counts['REVIEW']} |")
        lines.extend([
            "",
            "### Detector status and metrics",
            "| Detector | TP | TN | FP | FN | Inconclusive | Errors | Not applicable |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for name, metrics in sorted(summary["detector_level_confusion_matrices"].items()):
            states = summary["detector_status_counts"][name]
            lines.append(
                f"| {name} | {metrics['TP']} | {metrics['TN']} | {metrics['FP']} | {metrics['FN']} | "
                f"{metrics['Inconclusive']} | {states['error']} | {states['not_applicable']} |"
            )
        return "\n".join(lines)
