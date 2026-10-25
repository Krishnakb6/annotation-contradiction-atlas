"""
Comprehensive System Verification and End-to-End Diagnostic Suite.
Tests database integrity, biological feature analysis, ESM-2 embeddings,
contradiction scoring, benchmark evaluation, and Streamlit user interface components.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.connection import get_db_session
from database.models import (
    Protein,
    FunctionAnnotation,
    SequenceFeature,
    ReviewFlag,
    ModelResult,
    EmbeddingRecord,
    AnalysisRun,
    BenchmarkCase,
)
from services.kinase_features import KinaseFeatureAnalyzer
from services.sequence_similarity import SequenceSimilarityBaseline
from services.embeddings import ESMEmbeddingService
from services.anomaly_detection import EmbeddingAnomalyDetector
from services.provenance_analysis import ProvenanceAnalyzer
from services.contradiction_scoring import ContradictionScorer
from ui.styles import render_priority_badge, CUSTOM_CSS
from ui.protein_detail import highlight_sequence


def test_section(name: str):
    print("\n" + "=" * 60)
    print(f"VERIFYING: {name}")
    print("=" * 60)


def run_all_diagnostics():
    passed = 0
    failed = 0

    # 1. DATABASE INTEGRITY
    test_section("1. Relational Database Layer")
    try:
        with get_db_session() as session:
            n_prot = session.query(Protein).count()
            n_ann = session.query(FunctionAnnotation).count()
            n_feat = session.query(SequenceFeature).count()
            n_flags = session.query(ReviewFlag).count()
            n_emb = session.query(EmbeddingRecord).count()
            n_runs = session.query(AnalysisRun).count()

            print(f"  [OK] Proteins count:            {n_prot}")
            print(f"  [OK] Functional annotations:    {n_ann}")
            print(f"  [OK] Sequence features stored:  {n_feat}")
            print(f"  [OK] Review flags recorded:     {n_flags}")
            print(f"  [OK] Embedding records:         {n_emb}")
            print(f"  [OK] Analysis runs logged:      {n_runs}")

            assert n_prot >= 500, f"Expected at least 500 proteins, found {n_prot}"
            assert n_ann >= 1000, f"Expected annotations >= 1000, found {n_ann}"
            assert n_flags >= 100, f"Expected review flags >= 100, found {n_flags}"
            print("  --> Database integrity check PASSED")
            passed += 1
    except Exception as e:
        print(f"  [FAIL] Database check failed: {e}")
        failed += 1

    # 2. BIOLOGICAL FEATURES & MOTIFS
    test_section("2. Kinase Biological Feature Checks (VAIK, HRD, DFG)")
    try:
        analyzer = KinaseFeatureAnalyzer()
        # Test on canonical EGFR kinase sequence segment
        seq_egfr = (
            "KIPVAIKVLRENTSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAE"
        )
        res_canon = analyzer.analyze_sequence(seq_egfr)
        print(f"  [OK] Canonical EGFR: {res_canon['canonical_count']}/3 motifs canonical, order valid: {res_canon['order_valid']}")
        assert res_canon['canonical_count'] == 3
        assert res_canon['order_valid'] is True
        assert res_canon['anomaly_score'] <= 0.05

        # Test on pseudokinase VRK3-like sequence (variant HRD: HGN)
        seq_vrk3 = "MKT" + "VAIK" + ("A" * 70) + "HGN" + ("A" * 20) + "DFG" + "KLM"
        res_vrk3 = analyzer.analyze_sequence(seq_vrk3)
        print(f"  [OK] Pseudokinase VRK3 signature: {res_vrk3['variant_count']} variant motif(s) detected ({res_vrk3['summary']})")
        assert res_vrk3['variant_count'] == 1

        print("  --> Biological feature checks PASSED")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] Biological feature checks failed: {e}")
        failed += 1

    # 3. SEQUENCE SIMILARITY BASELINE
    test_section("3. Sequence Similarity Baseline")
    try:
        baseline = SequenceSimilarityBaseline()
        s1 = "VAIKTLKPGTMSPEAFLQEAQVMKKLRHEKLVQLYAVVSEEPIYIV"
        s2 = "VAIKTLKPGTMSPEAFLQEAQVMKKLRHEKLVQLYAVVSEEPIYIV"
        res_sim = baseline.compute_identity_and_coverage(s1, s2)
        print(f"  [OK] Identity for identical sequences: {res_sim['identity']*100:.1f}%, Coverage: {res_sim['coverage']*100:.1f}%")
        assert res_sim['identity'] >= 0.95
        assert res_sim['coverage'] == 1.0

        ref_panel = [{"accession": "REF01", "gene_name": "EGFR", "sequence": s1, "functional_label": "Tyrosine kinase"}]
        comp = baseline.compare_against_reference_panel(s1, "Tyrosine kinase", ref_panel)
        print(f"  [OK] Nearest reference: {comp['best_reference_gene']}, Concordant: {comp['label_concordant']}")
        assert comp['label_concordant'] is True
        print("  --> Sequence similarity check PASSED")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] Sequence similarity check failed: {e}")
        failed += 1

    # 4. ESM-2 EMBEDDINGS & DISK CACHING
    test_section("4. ESM-2 Protein Language Model & Embeddings")
    try:
        emb_svc = ESMEmbeddingService()
        test_seq = "VAIKTLKPGTMSPEAFLQEAQVMKKLRHEKLVQLYAVVSEEPIYIV"
        emb, meta = emb_svc.compute_embedding(test_seq, accession="TEST_DIAG_01", use_cache=True)
        print(f"  [OK] Embedding computed: Shape={emb.shape}, Dim={meta.get('embedding_dim')}, Model={meta.get('model')}")
        assert len(emb) == 320

        # Test cache reload
        emb_cached, meta_cached = emb_svc.compute_embedding(test_seq, accession="TEST_DIAG_01", use_cache=True)
        print(f"  [OK] Cached reload verified: Cached flag={meta_cached.get('cached')}")
        assert meta_cached.get('cached') is True
        print("  --> ESM-2 embedding & caching check PASSED")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] ESM-2 embedding check failed: {e}")
        failed += 1

    # 5. EVIDENCE-AWARE CONTRADICTION SCORING
    test_section("5. Contradiction Scoring & Safeguards")
    try:
        scorer = ContradictionScorer()
        # Normal profile
        normal = scorer.compute_review_priority(
            {"anomaly_score": 0.1, "is_outlier": False},
            {"anomaly_score": 0.1, "label_concordant": True, "best_identity": 0.9},
            {"anomaly_score": 0.0, "canonical_count": 3, "variant_count": 0, "absent_count": 0},
            {"provenance_penalty": 0.1, "overall_category": "EXPERIMENTAL"}
        )
        print(f"  [OK] Canonical profile priority: {normal['review_priority']} (Score: {normal['contradiction_score']:.2f})")
        assert normal['review_priority'] == "LOW"

        # Broken profile
        broken = scorer.compute_review_priority(
            {"anomaly_score": 0.8, "is_outlier": True},
            {"anomaly_score": 0.7, "label_concordant": False, "best_identity": 0.2},
            {"anomaly_score": 0.9, "canonical_count": 0, "variant_count": 0, "absent_count": 3},
            {"provenance_penalty": 0.9, "overall_category": "COMPUTATIONAL_UNREVIEWED"}
        )
        print(f"  [OK] Broken motif profile priority: {broken['review_priority']} (Score: {broken['contradiction_score']:.2f})")
        assert broken['review_priority'] == "HIGH"
        print("  --> Contradiction scoring check PASSED")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] Contradiction scoring check failed: {e}")
        failed += 1

    # 6. STREAMLIT USER INTERFACE & VISUAL COMPONENTS
    test_section("6. Streamlit User Interface Components & Visual Styling")
    try:
        # Import all UI modules
        import ui.dashboard as d
        import ui.protein_explorer as pe
        import ui.protein_detail as pd
        import ui.contradiction_explorer as ce
        import ui.evaluation as ev
        import ui.data_management as dm
        import ui.methods as m

        assert hasattr(d, "render_dashboard")
        assert hasattr(pe, "render_protein_explorer")
        assert hasattr(pd, "render_protein_detail")
        assert hasattr(ce, "render_contradiction_explorer")
        assert hasattr(ev, "render_evaluation")
        assert hasattr(dm, "render_data_management")
        assert hasattr(m, "render_methods")
        print("  [OK] All 7 Streamlit UI view modules successfully imported and verified")

        # Verify badge rendering
        badge = render_priority_badge("HIGH")
        assert "badge-priority-high" in badge
        print("  [OK] Review priority badges verified")

        # Verify high-contrast sequence styling
        assert ".sequence-box" in CUSTOM_CSS
        assert "#0F172A" in CUSTOM_CSS and "#F8FAFC" in CUSTOM_CSS
        print("  [OK] High-contrast sequence CSS verified (Dark slate #0F172A + Crisp text #F8FAFC)")

        # Verify motif highlight rendering
        dummy_feat = SequenceFeature(feature_name="DFG", detected_status="canonical", start_position=1, end_position=3)
        hl = highlight_sequence("DFGLMN", [dummy_feat])
        assert "#059669" in hl and "#FFFFFF" in hl
        print("  [OK] Sequence motif highlight rendering verified (Emerald canonical triad)")

        # Verify .streamlit/config.toml
        cfg_path = Path(".streamlit/config.toml")
        assert cfg_path.exists(), ".streamlit/config.toml should exist"
        print("  [OK] Streamlit config lock file verified (.streamlit/config.toml)")

        print("  --> Streamlit User Interface check PASSED")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] Streamlit User Interface check failed: {e}")
        failed += 1

    # 7. BENCHMARK ARTIFACTS (VERSION 2)
    test_section("7. Benchmark Artifacts & Multi-Task Evaluation Report (v2)")
    try:
        report_v2_file = Path("artifacts/evaluation_report_v2.json")
        summary_v2_file = Path("artifacts/evaluation_summary_v2.csv")
        diagnostics_v2_file = Path("artifacts/benchmark_diagnostics_v2.json")
        audit_file = Path("artifacts/benchmark_audit.md")

        assert report_v2_file.exists(), "evaluation_report_v2.json missing!"
        assert summary_v2_file.exists(), "evaluation_summary_v2.csv missing!"
        assert diagnostics_v2_file.exists(), "benchmark_diagnostics_v2.json missing!"
        assert audit_file.exists(), "benchmark_audit.md missing!"

        with open(report_v2_file, "r", encoding="utf-8") as f:
            rep = json.load(f)

        assert "task_evaluations" in rep
        assert "overall_independent_test_evaluation" in rep
        ds = rep.get("dataset_summary", {})
        print(f"  [OK] Benchmark Report v2: {ds.get('total_benchmark_cases')} total cases ({ds.get('independent_test_cases_count')} test, {ds.get('calibration_cases_count')} calibration, {ds.get('natural_exceptions_count')} natural)")
        
        test_ens = rep["overall_independent_test_evaluation"]["methods_comparison"]["evidence_aware_ensemble"]
        print(f"  [OK] Independent Test Ensemble: Precision={test_ens['precision_display']}, Recall={test_ens['recall_display']}, F1={test_ens['f1_score_display']}")

        # Verify task separation
        task1 = rep["task_evaluations"]["task1_label_contradiction_detection"]
        task2 = rep["task_evaluations"]["task2_sequence_perturbation_detection"]
        task3 = rep["task_evaluations"]["task3_natural_biological_exceptions"]
        print(f"  [OK] Task 1 (Label Contradictions): {task1['sample_size']} cases evaluated")
        print(f"  [OK] Task 2 (Sequence Perturbations): {task2['sample_size']} cases evaluated")
        print(f"  [OK] Task 3 (Natural Pseudokinases): {len(task3['evaluated_cases'])} cases analyzed as biological exceptions")

        print("  --> Benchmark artifacts v2 check PASSED")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] Benchmark artifact check failed: {e}")
        failed += 1

    # SUMMARY
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Subsystems Passed: {passed} / {passed + failed}")
    print(f"Subsystems Failed: {failed} / {passed + failed}")
    if failed == 0:
        print("\nALL SYSTEMS OPERATIONAL: EVERYTHING IS WORKING AS EXPECTED.")
    else:
        print(f"\nWARNING: {failed} subsystem(s) encountered issues.")
    print("=" * 60 + "\n")
    return failed == 0


if __name__ == "__main__":
    success = run_all_diagnostics()
    sys.exit(0 if success else 1)
