"""
Unit tests for evaluation metrics, confusion matrix computation, and synthetic benchmark isolation.
"""
import pytest
from services.benchmark import calculate_binary_metrics, BenchmarkService


def test_calculate_binary_metrics_toy_example():
    # 3 TP, 1 FP, 4 TN, 2 FN -> total 10
    # True:  1, 1, 1, 1, 1, 0, 0, 0, 0, 0
    # Pred:  1, 1, 1, 0, 0, 1, 0, 0, 0, 0
    y_true = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
    y_pred = [1, 1, 1, 0, 0, 1, 0, 0, 0, 0]

    metrics = calculate_binary_metrics(y_true, y_pred)
    assert metrics["sample_size"] == 10
    assert metrics["true_positives"] == 3
    assert metrics["false_positives"] == 1
    assert metrics["true_negatives"] == 4
    assert metrics["false_negatives"] == 2

    # Precision = 3 / (3 + 1) = 0.75
    assert metrics["precision"] == 0.75
    # Recall = 3 / (3 + 2) = 0.60
    assert metrics["recall"] == 0.60
    # Specificity = 4 / (4 + 1) = 0.80
    assert metrics["specificity"] == 0.80
    # F1 = 2 * (0.75 * 0.6) / (0.75 + 0.6) = 0.9 / 1.35 = 0.6667
    assert metrics["f1_score"] == pytest.approx(0.6667, abs=1e-3)
    # Accuracy = (3 + 4) / 10 = 0.70
    assert metrics["accuracy"] == 0.70


def test_metric_calculation_zero_division():
    # All negatives predicted negative
    y_true = [0, 0, 0]
    y_pred = [0, 0, 0]
    metrics = calculate_binary_metrics(y_true, y_pred)
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["specificity"] == 1.0
    assert metrics["accuracy"] == 1.0


def test_synthetic_benchmark_generation():
    service = BenchmarkService()
    base_proteins = [
        {
            "accession": "P00533",
            "gene_name": "EGFR",
            "sequence": "MKT" + "VAIK" + ("A" * 70) + "HRD" + ("A" * 20) + "DFG" + "KLM",
            "functional_label": "Tyrosine kinase activity",
        }
    ]

    cases = service.build_synthetic_benchmark(base_proteins, seed=42, num_synthetic_cases=8)
    assert len(cases) > 0

    # Ensure all have synthetic identifiers and valid category
    for c in cases:
        assert c["synthetic_identifier"].startswith("SYNTH_")
        assert c["case_type"] == "CATEGORY_C_SYNTHETIC"
        assert c["ground_truth_category"] in ("INCONSISTENT_CATALYTIC", "LABEL_MISMATCH", "CONGRUENT")
        assert isinstance(c["is_inconsistent"], bool)
        assert c["random_seed"] == 42
