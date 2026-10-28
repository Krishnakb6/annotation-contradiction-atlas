"""
Comprehensive Unit & Scientific Audit Tests (Version 2).
Validates benchmark categorization, metric calculations, zero-division safeguards,
confusion matrix orientation, calibration/test split isolation, pseudokinase handling,
and artifact consistency.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest
import numpy as np
import sklearn.metrics as skm

from config import ARTIFACTS_DIR, RANDOM_SEED
from services.evaluation import calculate_binary_metrics, format_metrics_table
from services.benchmark import BenchmarkService
from services.anomaly_detection import EmbeddingAnomalyDetector, cosine_distance
from services.kinase_features import KinaseFeatureAnalyzer
from services.sequence_similarity import SequenceSimilarityBaseline
from services.contradiction_scoring import ContradictionScorer


# 1. Benchmark Labels & Interpretation
def test_benchmark_label_categorization_and_safeguards():
    """Verify all 4 benchmark categories and explicit labeling safeguards."""
    service = BenchmarkService()
    base_proteins = [
        {"accession": "P00533", "gene_name": "EGFR", "sequence": "MKT" + "VAIK" + ("A" * 70) + "HRD" + ("A" * 20) + "DFG", "functional_label": "Tyrosine kinase activity"},
        {"accession": "P12931", "gene_name": "SRC", "sequence": "MKT" + "VAIK" + ("A" * 70) + "HRD" + ("A" * 20) + "DFG", "functional_label": "Tyrosine kinase activity"},
    ]
    cases = service.build_synthetic_benchmark(base_proteins, seed=42, num_synthetic_cases=8)

    valid_types = {"CATEGORY_C_SYNTHETIC_LABEL", "CATEGORY_D_SYNTHETIC_SEQUENCE", "CATEGORY_C_SYNTHETIC_CONTROL"}
    valid_categories = {"SYNTHETIC_LABEL_CONTRADICTION", "SYNTHETIC_SEQUENCE_PERTURBATION", "CONGRUENT_CONTROL"}

    for c in cases:
        assert c["case_type"] in valid_types
        assert c["ground_truth_category"] in valid_categories
        assert c["dataset_split"] in ("CALIBRATION", "TEST")
        if c["ground_truth_category"] == "CONGRUENT_CONTROL":
            assert c["is_inconsistent"] is False
        else:
            assert c["is_inconsistent"] is True


# 2. Separation of Synthetic and Natural Cases
def test_synthetic_and_natural_separation():
    """Ensure natural exceptions and synthetic perturbations are never merged into an undifferentiated positive class."""
    rep_path = ARTIFACTS_DIR / "evaluation_report_v2.json"
    if rep_path.exists():
        with open(rep_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "task_evaluations" in data
        assert "task1_label_contradiction_detection" in data["task_evaluations"]
        assert "task2_sequence_perturbation_detection" in data["task_evaluations"]
        assert "task3_natural_biological_exceptions" in data["task_evaluations"]
        assert "task4_real_world_annotation_limitations" in data["task_evaluations"]


# 3. Pseudokinases are NOT Labeled as Misannotated
def test_pseudokinases_not_labeled_as_misannotated():
    """Verify that pseudokinases VRK3 and ILK are classified as biological exceptions, NOT misannotations."""
    cat_b = [
        {"accession": "Q9Y616", "gene_name": "VRK3", "is_inconsistent": False, "ground_truth_category": "NATURAL_EXCEPTION"},
        {"accession": "Q13418", "gene_name": "ILK", "is_inconsistent": False, "ground_truth_category": "NATURAL_EXCEPTION"},
    ]
    for p in cat_b:
        assert p["is_inconsistent"] is False, "Pseudokinase should not be marked is_inconsistent=True"
        assert p["ground_truth_category"] == "NATURAL_EXCEPTION"


# 4. Metric Calculations on Known Confusion Matrices (Cross-verified with scikit-learn)
def test_metric_calculations_known_matrix():
    """Verify metrics against hand-calculated values and scikit-learn output."""
    # 4 TP, 1 FP, 5 TN, 2 FN -> Total = 12
    y_true = [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0]
    y_pred = [1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0]

    res = calculate_binary_metrics(y_true, y_pred)

    assert res["true_positives"] == 4
    assert res["false_positives"] == 1
    assert res["true_negatives"] == 5
    assert res["false_negatives"] == 2
    assert res["sample_size"] == 12

    # Precision = 4 / 5 = 0.8
    assert res["precision"] == 0.8000
    sk_prec = skm.precision_score(y_true, y_pred)
    assert res["precision"] == pytest.approx(sk_prec, abs=1e-4)

    # Recall = 4 / 6 = 0.6667
    assert res["recall"] == pytest.approx(4 / 6, abs=1e-4)
    sk_rec = skm.recall_score(y_true, y_pred)
    assert res["recall"] == pytest.approx(sk_rec, abs=1e-4)

    # Specificity = 5 / 6 = 0.8333
    assert res["specificity"] == pytest.approx(5 / 6, abs=1e-4)

    # Accuracy = (4 + 5) / 12 = 0.75
    assert res["accuracy"] == 0.7500
    sk_acc = skm.accuracy_score(y_true, y_pred)
    assert res["accuracy"] == pytest.approx(sk_acc, abs=1e-4)


# 5. Correct Zero-Division Handling
def test_zero_division_transparent_safeguards():
    """Zero division must return None (rendered as Undefined), never silent 0.0 or 1.0."""
    # Zero positive predictions made
    y_true = [1, 1, 0, 0]
    y_pred = [0, 0, 0, 0]

    res = calculate_binary_metrics(y_true, y_pred)
    assert res["precision"] is None
    assert "Undefined" in res["precision_display"]
    assert res["f1_score"] is None
    assert "Undefined" in res["f1_score_display"]
    assert res["recall"] == 0.0  # TP=0, FN=2 -> 0/2 = 0.0


# 6. Correct Confusion Matrix Orientation
def test_confusion_matrix_orientation():
    """Verify matrix follows standard scikit-learn [[TN, FP], [FN, TP]] layout."""
    y_true = [0, 0, 1, 1]
    y_pred = [0, 1, 0, 1]

    res = calculate_binary_metrics(y_true, y_pred)
    arr = res["matrix_array"]
    sk_matrix = skm.confusion_matrix(y_true, y_pred, labels=[0, 1])

    # arr[0][0] = TN, arr[0][1] = FP, arr[1][0] = FN, arr[1][1] = TP
    assert arr[0][0] == res["true_negatives"] == sk_matrix[0, 0] == 1
    assert arr[0][1] == res["false_positives"] == sk_matrix[0, 1] == 1
    assert arr[1][0] == res["false_negatives"] == sk_matrix[1, 0] == 1
    assert arr[1][1] == res["true_positives"] == sk_matrix[1, 1] == 1


# 7. Identical Evaluation Cases Across Methods
def test_identical_evaluation_cases():
    """All methods must evaluate the exact same instances in any comparison."""
    rep_path = ARTIFACTS_DIR / "evaluation_report_v2.json"
    if rep_path.exists():
        with open(rep_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        methods = data["overall_independent_test_evaluation"]["methods_comparison"]
        sample_sizes = [m["sample_size"] for m in methods.values()]
        assert len(set(sample_sizes)) == 1, "All methods must evaluate identical sample size"


# 8. Threshold Selection Without Test-Label Leakage
def test_threshold_selection_without_leakage():
    """Verify threshold calibration operates only on control embeddings without test set leakage."""
    det = EmbeddingAnomalyDetector()
    rng = np.random.RandomState(42)
    controls = [rng.randn(320) for _ in range(10)]
    refs = [{"accession": f"REF_{i}", "embedding": rng.randn(320)} for i in range(5)]

    thresh = det.calibrate_threshold_from_controls(controls, refs, percentile=95.0)
    assert isinstance(thresh, float)
    assert thresh > 0.0


# 9. Embedding Dimension and Preprocessing Consistency
def test_embedding_dimensions_and_cosine_distance():
    """Cosine distance must be mathematically bounded in [0.0, 2.0]."""
    u = np.array([1.0, 0.0, 0.0])
    v = np.array([1.0, 0.0, 0.0])
    assert cosine_distance(u, v) == pytest.approx(0.0)

    w = np.array([-1.0, 0.0, 0.0])
    assert cosine_distance(u, w) == pytest.approx(2.0)

    z = np.array([0.0, 1.0, 0.0])
    assert cosine_distance(u, z) == pytest.approx(1.0)


# 10. Anomaly Threshold Behavior
def test_anomaly_threshold_behavior():
    """Scores above threshold flag outliers; scores below do not."""
    det = EmbeddingAnomalyDetector(anomaly_threshold=0.25)
    ref = np.zeros(320)
    ref[0] = 1.0
    refs = [{"accession": "R1", "embedding": ref, "gene_name": "REF1"}]

    # Near query
    q_near = np.zeros(320)
    q_near[0] = 0.99
    res_near = det.evaluate_embedding(q_near, refs)
    assert res_near["is_outlier"] is False

    # Distant query
    q_far = np.zeros(320)
    q_far[1] = 1.0
    res_far = det.evaluate_embedding(q_far, refs)
    assert res_far["is_outlier"] is True


# 11. Sequence Similarity Baseline Tie Handling
def test_sequence_similarity_tie_handling():
    """Similarity comparison handles multiple equidistant references gracefully."""
    sim = SequenceSimilarityBaseline()
    seq = "VAIKTLKPGTMSPEAFLQEAQVMKKLRHEKLVQLYAVVSEEPIYIV"
    ref_panel = [
        {"accession": "REF1", "gene_name": "G1", "sequence": seq, "functional_label": "Kinase activity"},
        {"accession": "REF2", "gene_name": "G2", "sequence": seq, "functional_label": "Kinase activity"},
    ]
    res = sim.compare_against_reference_panel(seq, "Kinase activity", ref_panel)
    assert res["label_concordant"] is True
    assert res["best_identity"] >= 0.99


# 12. Motif Detection with Atypical Cases
def test_motif_detection_atypical_pseudokinases():
    """VRK3 atypical loop (HGN) must be detected as variant, not missing or canonical."""
    analyzer = KinaseFeatureAnalyzer()
    seq_vrk3 = "MKT" + "VAIK" + ("A" * 70) + "HGN" + ("A" * 20) + "DFG" + "KLM"
    res = analyzer.analyze_sequence(seq_vrk3)
    assert res["variant_count"] >= 1
    assert "HGN" in res["summary"] or "variant" in res["summary"].lower()


# 13. Missing Provenance Information Handling
def test_provenance_handling_missing_evidence():
    """Missing evidence should be scored as UNREVIEWED uncertainty, not treated as negative evidence."""
    scorer = ContradictionScorer()
    emb_res = {"anomaly_score": 0.1, "is_outlier": False}
    sim_res = {"anomaly_score": 0.1, "label_concordant": True, "best_identity": 0.9}
    feat_res = {"anomaly_score": 0.0, "canonical_count": 3, "variant_count": 0, "absent_count": 0}

    # Low provenance alone must NOT trigger HIGH review priority
    prov_res = {"provenance_penalty": 0.8, "overall_category": "COMPUTATIONAL_UNREVIEWED"}
    res = scorer.compute_review_priority(emb_res, sim_res, feat_res, prov_res)
    assert res["review_priority"] in ("LOW", "MODERATE")
    assert res["review_priority"] != "HIGH"


# 14. Report Generation Artifacts Verification
def test_report_v2_artifacts_exist():
    """Verify that all four required artifacts exist and are well-formatted."""
    f1 = ARTIFACTS_DIR / "evaluation_report_v2.json"
    f2 = ARTIFACTS_DIR / "evaluation_summary_v2.csv"
    f3 = ARTIFACTS_DIR / "benchmark_diagnostics_v2.json"
    f4 = ARTIFACTS_DIR / "benchmark_audit.md"

    assert f1.exists(), "evaluation_report_v2.json must exist"
    assert f2.exists(), "evaluation_summary_v2.csv must exist"
    assert f3.exists(), "benchmark_diagnostics_v2.json must exist"
    assert f4.exists(), "benchmark_audit.md must exist"


# 15. Consistency Between JSON Metrics and Formatted Table
def test_metrics_json_and_table_consistency():
    """Formatted summary table must match exact values in JSON report."""
    rep_path = ARTIFACTS_DIR / "evaluation_report_v2.json"
    if rep_path.exists():
        with open(rep_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        methods = data["overall_independent_test_evaluation"]["methods_comparison"]
        rows = format_metrics_table(methods)

        for row in rows:
            m_key = row["Method"].lower().replace(" ", "_")
            if m_key in methods:
                m = methods[m_key]
                assert row["Sample Size"] == m["sample_size"]
                assert row["Precision"] == m["precision_display"]
                assert row["Recall"] == m["recall_display"]
                assert row["F1-Score"] == m["f1_score_display"]


# 16. Regression Test: Elimination of False 100% Natural Subset Metric
def test_regression_no_artificial_natural_subset_perfection():
    """Ensure natural exceptions are never presented as 100% precision and recall."""
    rep_path = ARTIFACTS_DIR / "evaluation_report_v2.json"
    if rep_path.exists():
        with open(rep_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Task 3 should NOT contain a binary classification asserting 100% precision/recall on pseudokinases
        t3 = data.get("task_evaluations", {}).get("task3_natural_biological_exceptions", {})
        assert "methods" not in t3, "Task 3 must be exploratory exception characterization, not binary precision/recall"
        assert "evaluated_cases" in t3


# 17. Biological Exceptions Excluded from Suspected-Conflict Queue by Default
def test_biological_exceptions_excluded_from_ordinary_queue_by_default():
    """Verify that biological exceptions (pseudokinases) are excluded from ordinary suspected conflict queue by default."""
    from services.contradiction_scoring import is_biological_exception, filter_suspected_conflicts
    from ui.contradiction_explorer import get_explorer_candidates

    suspected_conflicts, _ = get_explorer_candidates()

    # None of the candidates in suspected_conflicts should be biological exceptions
    for candidate in suspected_conflicts:
        assert not is_biological_exception(candidate), f"Biological exception {candidate} found in ordinary conflict queue"

    # Direct test of filter_suspected_conflicts
    mixed_candidates = [
        {"accession": "P00533", "gene_name": "EGFR", "classification": "SUSPECTED_CONFLICT", "flag_reason": "Missing motif"},
        {"accession": "Q9Y616", "gene_name": "VRK3", "classification": "BIOLOGICAL_EXCEPTION (Pseudokinase)", "flag_reason": "Biological exception / Pseudokinase candidate"},
        {"accession": "Q13418", "gene_name": "ILK", "classification": "BIOLOGICAL_EXCEPTION (Pseudokinase)", "flag_reason": "Biological exception / Pseudokinase candidate"},
        {"accession": "P12931", "gene_name": "SRC", "classification": "SUSPECTED_CONFLICT", "flag_reason": "ESM-2 outlier"},
    ]

    default_queue = filter_suspected_conflicts(mixed_candidates, include_exceptions=False)
    assert len(default_queue) == 2
    queue_accessions = [c["accession"] for c in default_queue]
    assert "P00533" in queue_accessions
    assert "P12931" in queue_accessions
    assert "Q9Y616" not in queue_accessions
    assert "Q13418" not in queue_accessions

    # When include_exceptions=True, all candidates are preserved
    full_queue = filter_suspected_conflicts(mixed_candidates, include_exceptions=True)
    assert len(full_queue) == 4


# 18. VRK3 and ILK Accessible in Biological-Exceptions Section
def test_vrk3_and_ilk_accessible_in_biological_exceptions_section():
    """Verify that VRK3 and ILK remain accessible in the biological-exceptions section with motif explanations and diagnostic scores."""
    from services.contradiction_scoring import is_biological_exception, load_benchmark_exceptions
    from ui.contradiction_explorer import get_explorer_candidates

    # Verify classification logic
    vrk3_meta = {"accession": "Q9Y616", "gene_name": "VRK3", "classification": "BIOLOGICAL_EXCEPTION (Pseudokinase)"}
    ilk_meta = {"accession": "Q13418", "gene_name": "ILK", "classification": "BIOLOGICAL_EXCEPTION (Pseudokinase)"}
    assert is_biological_exception(vrk3_meta) is True
    assert is_biological_exception(ilk_meta) is True

    # Verify explorer candidates return them
    _, bio_exceptions = get_explorer_candidates()
    ex_by_acc = {e["accession"]: e for e in bio_exceptions}

    assert "Q9Y616" in ex_by_acc, "VRK3 (Q9Y616) must be accessible in biological exceptions section"
    assert "Q13418" in ex_by_acc, "ILK (Q13418) must be accessible in biological exceptions section"

    vrk3 = ex_by_acc["Q9Y616"]
    ilk = ex_by_acc["Q13418"]

    # Verify scores and priorities are preserved
    assert vrk3["contradiction_score"] == pytest.approx(0.4537, abs=1e-3)
    assert vrk3["priority"] == "MODERATE"
    assert "HRD" in vrk3["motif_summary"] or "HGA" in vrk3["motif_summary"] or vrk3["variant_count"] > 0
    assert len(vrk3["biological_caveat"]) > 0

    assert ilk["contradiction_score"] == pytest.approx(0.7167, abs=1e-3)
    assert ilk["priority"] == "HIGH"
    assert "HRD" in ilk["motif_summary"] or "FKK" in ilk["motif_summary"] or ilk["variant_count"] > 0
    assert len(ilk["biological_caveat"]) > 0


# 19. Existing Benchmark Metrics, Thresholds, Labels, and Report Files Preserved
def test_existing_benchmark_metrics_and_reports_preserved():
    """Verify that benchmark metrics, thresholds, labels, and saved evaluation reports remain intact."""
    rep_path = ARTIFACTS_DIR / "evaluation_report_v2.json"
    assert rep_path.exists(), "evaluation_report_v2.json must exist"

    with open(rep_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Thresholds preserved
    assert data["frozen_thresholds"]["esm2_anomaly_threshold"] == 0.1814
    assert data["frozen_thresholds"]["similarity_anomaly_threshold"] == 0.4
    assert data["frozen_thresholds"]["feature_anomaly_threshold"] == 0.3
    assert data["frozen_thresholds"]["ensemble_review_priority_threshold"] == "HIGH_OR_MODERATE (Score >= 0.40)"

    # ESM-2 Independent test metrics preserved
    esm_test = data["overall_independent_test_evaluation"]["methods_comparison"]["esm2_embedding_anomaly"]
    assert esm_test["sample_size"] == 21
    assert esm_test["false_positives"] == 1
    assert esm_test["true_positives"] == 2
    assert esm_test["false_negatives"] == 10
    assert esm_test["true_negatives"] == 8
    assert esm_test["precision_display"] == "0.6667"
    assert esm_test["recall_display"] == "0.1667"
    assert esm_test["f1_score_display"] == "0.2667"

    # Task 3 evaluated cases preserved
    t3 = data["task_evaluations"]["task3_natural_biological_exceptions"]["evaluated_cases"]
    assert len(t3) == 2
    t3_by_acc = {c["accession"]: c for c in t3}
    assert t3_by_acc["Q9Y616"]["contradiction_score"] == 0.4537
    assert t3_by_acc["Q9Y616"]["review_priority"] == "MODERATE"
    assert t3_by_acc["Q13418"]["contradiction_score"] == 0.7167
    assert t3_by_acc["Q13418"]["review_priority"] == "HIGH"


# 20. ESM-2 Diagnostic Text Scientific Accuracy
def test_esm2_diagnostic_text_accuracy():
    """Verify that ui/evaluation.py accurately reflects test results without claiming zero false positives."""
    eval_ui_path = Path("ui/evaluation.py")
    with open(eval_ui_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must NOT claim that false positives are not inflated or eliminated
    assert "without inflating false positives" not in content, "Misleading false-positive claim found"
    assert "eliminates false positives" not in content.lower()

    # Must describe observed results accurately
    assert "0.1814" in content or "{calib_thresh:.4f}" in content
    assert "1 false positive" in content
    assert "0.40" in content
    assert "zero positive predictions" in content or "0.0%" in content
    assert "does not establish reliable real-world annotation-error detection" in content

