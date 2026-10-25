"""
Centralized Scientific Evaluation and Metric Calculation Module.
Standardizes metric calculations, confusion matrix formatting, zero-division handling,
and multi-task benchmark evaluation across all Annotation Contradiction Atlas detection methods.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np

logger = logging.getLogger("contradiction_atlas.evaluation")


def calculate_binary_metrics(
    y_true: List[int],
    y_pred: List[int],
    task_name: str = "binary_classification",
    positive_label_meaning: str = "Inconsistent / Review Candidate",
    negative_label_meaning: str = "Congruent / Control",
) -> Dict[str, Any]:
    """
    Computes rigorous binary classification metrics with explicit zero-division safeguards,
    standardized confusion matrix orientation, and complete sample accounting.

    Confusion Matrix Orientation (Standard scikit-learn layout):
      - Rows: Actual Ground Truth (Row 0 = Actual Negative [0], Row 1 = Actual Positive [1])
      - Columns: Predicted Class (Col 0 = Predicted Negative [0], Col 1 = Predicted Positive [1])

      Matrix Array:
        [[TN, FP],
         [FN, TP]]

    Zero-Division Safeguards:
      - Precision: Undefined if TP + FP == 0 (no positive predictions made).
      - Recall: Undefined if TP + FN == 0 (no actual positives present).
      - Specificity: Undefined if TN + FP == 0 (no actual negatives present).
      - F1-Score: Undefined if Precision is undefined, Recall is undefined, or Precision + Recall == 0.
      Undefined metrics return None (rendered as 'Undefined' in UI/reports), never fabricated as 0.0 or 1.0.
    """
    if len(y_true) != len(y_pred):
        raise ValueError(f"Length mismatch: len(y_true)={len(y_true)} vs len(y_pred)={len(y_pred)}")

    total = len(y_true)
    if total == 0:
        return {
            "task_name": task_name,
            "sample_size": 0,
            "actual_positives": 0,
            "actual_negatives": 0,
            "true_positives": 0,
            "false_positives": 0,
            "true_negatives": 0,
            "false_negatives": 0,
            "precision": None,
            "precision_display": "Undefined (no samples)",
            "recall": None,
            "recall_display": "Undefined (no samples)",
            "specificity": None,
            "specificity_display": "Undefined (no samples)",
            "f1_score": None,
            "f1_score_display": "Undefined (no samples)",
            "accuracy": None,
            "accuracy_display": "Undefined (no samples)",
            "confusion_matrix": {
                "actual_positive": {"predicted_positive": 0, "predicted_negative": 0},
                "actual_negative": {"predicted_positive": 0, "predicted_negative": 0},
            },
            "matrix_array": [[0, 0], [0, 0]],
            "positive_label_meaning": positive_label_meaning,
            "negative_label_meaning": negative_label_meaning,
        }

    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    n_pos = tp + fn
    n_neg = tn + fp
    pred_pos = tp + fp
    pred_neg = tn + fn

    # 1. Precision
    if pred_pos > 0:
        precision = tp / pred_pos
        precision_disp = f"{precision:.4f}"
    else:
        precision = None
        precision_disp = "Undefined (0 positive predictions)"

    # 2. Recall (Sensitivity)
    if n_pos > 0:
        recall = tp / n_pos
        recall_disp = f"{recall:.4f}"
    else:
        recall = None
        recall_disp = "Undefined (no actual positives)"

    # 3. Specificity
    if n_neg > 0:
        specificity = tn / n_neg
        specificity_disp = f"{specificity:.4f}"
    else:
        specificity = None
        specificity_disp = "Undefined (no actual negatives)"

    # 4. F1-score
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = (2 * precision * recall) / (precision + recall)
        f1_disp = f"{f1:.4f}"
    else:
        f1 = None
        if pred_pos == 0:
            f1_disp = "Undefined (P and R undefined)"
        else:
            f1_disp = "0.0000" if (precision == 0 or recall == 0) else "Undefined"

    # 5. Accuracy
    accuracy = (tp + tn) / total
    accuracy_disp = f"{accuracy:.4f}"

    return {
        "task_name": task_name,
        "sample_size": total,
        "actual_positives": n_pos,
        "actual_negatives": n_neg,
        "predicted_positives": pred_pos,
        "predicted_negatives": pred_neg,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "precision": round(precision, 4) if precision is not None else None,
        "precision_display": precision_disp,
        "recall": round(recall, 4) if recall is not None else None,
        "recall_display": recall_disp,
        "specificity": round(specificity, 4) if specificity is not None else None,
        "specificity_display": specificity_disp,
        "f1_score": round(f1, 4) if f1 is not None else None,
        "f1_score_display": f1_disp,
        "accuracy": round(accuracy, 4),
        "accuracy_display": accuracy_disp,
        "confusion_matrix": {
            "actual_positive": {"predicted_positive": tp, "predicted_negative": fn},
            "actual_negative": {"predicted_positive": fp, "predicted_negative": tn},
        },
        "matrix_array": [[tn, fp], [fn, tp]],
        "matrix_orientation": "Rows: Actual [0: Neg, 1: Pos], Columns: Predicted [0: Neg, 1: Pos]",
        "positive_label_meaning": positive_label_meaning,
        "negative_label_meaning": negative_label_meaning,
    }


def format_metrics_table(metrics_dict: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Converts a dictionary of method metrics into a tabular list for display and CSV export.
    """
    rows = []
    for method_key, m in metrics_dict.items():
        name_clean = method_key.replace("_", " ").title()
        rows.append({
            "Method": name_clean,
            "Sample Size": m.get("sample_size", 0),
            "Actual Pos": m.get("actual_positives", 0),
            "Actual Neg": m.get("actual_negatives", 0),
            "TP": m.get("true_positives", 0),
            "FP": m.get("false_positives", 0),
            "TN": m.get("true_negatives", 0),
            "FN": m.get("false_negatives", 0),
            "Precision": m.get("precision_display", "N/A"),
            "Recall": m.get("recall_display", "N/A"),
            "F1-Score": m.get("f1_score_display", "N/A"),
            "Specificity": m.get("specificity_display", "N/A"),
            "Accuracy": m.get("accuracy_display", "N/A"),
        })
    return rows
