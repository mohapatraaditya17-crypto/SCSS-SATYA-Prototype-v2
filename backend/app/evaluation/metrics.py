import math
from typing import Dict, Any, Optional
from pydantic import BaseModel


class BinaryMetrics(BaseModel):
    tp: int = 0
    tn: int = 0
    fp: int = 0
    fn: int = 0
    inconclusive: int = 0
    error: int = 0
    not_applicable: int = 0
    total: int = 0

    @property
    def decisive_total(self) -> int:
        return self.tp + self.tn + self.fp + self.fn

    @property
    def sensitivity(self) -> Optional[float]:
        denom = self.tp + self.fn
        return round(self.tp / denom, 4) if denom > 0 else None

    @property
    def recall(self) -> Optional[float]:
        return self.sensitivity

    @property
    def specificity(self) -> Optional[float]:
        denom = self.tn + self.fp
        return round(self.tn / denom, 4) if denom > 0 else None

    @property
    def precision(self) -> Optional[float]:
        denom = self.tp + self.fp
        return round(self.tp / denom, 4) if denom > 0 else None

    @property
    def f1(self) -> Optional[float]:
        p = self.precision
        r = self.recall
        if p is not None and r is not None and (p + r) > 0:
            return round(2.0 * p * r / (p + r), 4)
        return None

    @property
    def balanced_accuracy(self) -> Optional[float]:
        sens = self.sensitivity
        spec = self.specificity
        if sens is not None and spec is not None:
            return round((sens + spec) / 2.0, 4)
        return None

    @property
    def mcc(self) -> Optional[float]:
        numerator = (self.tp * self.tn) - (self.fp * self.fn)
        denominator = math.sqrt(
            (self.tp + self.fp) * (self.tp + self.fn) * (self.tn + self.fp) * (self.tn + self.fn)
        )
        if denominator > 0:
            return round(numerator / denominator, 4)
        return None

    @property
    def inconclusive_rate(self) -> float:
        return round(self.inconclusive / max(1, self.total), 4)

    @property
    def coverage(self) -> Optional[float]:
        applicable = self.total - self.not_applicable
        if applicable <= 0:
            return None
        return round((applicable - self.error) / applicable, 4)

    @property
    def fpr(self) -> Optional[float]:
        denom = self.fp + self.tn
        return round(self.fp / denom, 4) if denom > 0 else None

    @property
    def fnr(self) -> Optional[float]:
        denom = self.fn + self.tp
        return round(self.fn / denom, 4) if denom > 0 else None

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "TP": self.tp,
            "TN": self.tn,
            "FP": self.fp,
            "FN": self.fn,
            "Inconclusive": self.inconclusive,
            "Errors": self.error,
            "Not_Applicable": self.not_applicable,
            "Coverage": self.coverage,
            "Total": self.total,
            "Sensitivity": self.sensitivity,
            "Specificity": self.specificity,
            "Precision": self.precision,
            "F1": self.f1,
            "Balanced_Accuracy": self.balanced_accuracy,
            "MCC": self.mcc,
            "Inconclusive_Rate": self.inconclusive_rate,
            "FPR": self.fpr,
            "FNR": self.fnr,
        }

