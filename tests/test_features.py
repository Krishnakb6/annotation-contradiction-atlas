"""
Unit tests for kinase biological features, motif detection, pseudokinase signatures,
sequence similarity baseline, and provenance analysis.
"""
import pytest
from services.kinase_features import KinaseFeatureAnalyzer
from services.sequence_similarity import SequenceSimilarityBaseline
from services.provenance_analysis import ProvenanceAnalyzer


def test_canonical_kinase_motifs():
    analyzer = KinaseFeatureAnalyzer()
    # Typical kinase domain snippet containing VAIK, HRD, and DFG in order:
    # ... VAIK ... (approx 80 aa) ... HRD ... (approx 20 aa) ... DFG ...
    test_seq = (
        "MKT" + "VAIK" + ("A" * 70) + "HRD" + ("A" * 20) + "DFG" + "KLM"
    )
    result = analyzer.analyze_sequence(test_seq)
    assert result["canonical_count"] == 3
    assert result["variant_count"] == 0
    assert result["absent_count"] == 0
    assert result["order_valid"] is True
    assert result["integrity_score"] >= 0.95
    assert result["anomaly_score"] <= 0.05


def test_mutated_motifs_detection():
    analyzer = KinaseFeatureAnalyzer()
    # Engineered mutation: HRD mutated to AAA, VAIK mutated to VAIA (missing Lysine)
    broken_seq = (
        "MKT" + "VAIA" + ("A" * 70) + "AAA" + ("A" * 20) + "DFG" + "KLM"
    )
    result = analyzer.analyze_sequence(broken_seq)
    assert result["canonical_count"] == 1  # Only DFG
    assert result["absent_count"] >= 1
    assert result["integrity_score"] < 0.60
    assert result["anomaly_score"] > 0.40


def test_variant_pseudokinase_motifs():
    analyzer = KinaseFeatureAnalyzer()
    # VRK3-like signature: HRD is HGN (variant catalytic loop lacking catalytic aspartate)
    pseudokinase_seq = (
        "MKT" + "VAIK" + ("A" * 70) + "HGN" + ("A" * 20) + "DFG" + "KLM"
    )
    result = analyzer.analyze_sequence(pseudokinase_seq)
    assert result["canonical_count"] == 2
    assert result["variant_count"] == 1
    # Check that HRD status is 'variant'
    hrd_feature = [m for m in result["motifs"] if m["feature_name"] == "HRD"][0]
    assert hrd_feature["detected_status"] == "variant"
    assert hrd_feature["detected_sequence"] == "HGN"


def test_sequence_similarity_baseline():
    baseline = SequenceSimilarityBaseline()
    s1 = "VAIKTLKPGTMSPEAFLQEAQVMKKLRHEKLVQLYAVVSEEPIYIV"
    s2 = "VAIKTLKPGTMSPEAFLQEAQVMKKLRHEKLVQLYAVVSEEPIYIV"  # Identical
    s3 = "MGGAAAGGGAAAGGGAAAGGGAAAGGGAAAGGGAAAGGGAAAGGGA"  # Dissimilar

    res_id = baseline.compute_identity_and_coverage(s1, s2)
    assert res_id["identity"] >= 0.90
    assert res_id["coverage"] == 1.0

    res_diff = baseline.compute_identity_and_coverage(s1, s3)
    assert res_diff["identity"] < 0.30

    # Test panel comparison
    ref_panel = [
        {"accession": "P00533", "gene_name": "EGFR", "sequence": s1, "functional_label": "Tyrosine kinase activity"},
    ]
    comp = baseline.compare_against_reference_panel(s1, "Tyrosine kinase activity", ref_panel)
    assert comp["best_reference_accession"] == "P00533"
    assert comp["label_concordant"] is True
    assert comp["anomaly_score"] <= 0.15


def test_provenance_analysis_tiers():
    analyzer = ProvenanceAnalyzer()

    # Experimental reviewed
    exp_anns = [
        {
            "functional_label": "ATP + protein = ADP + phosphoprotein",
            "evidence_category": "EXPERIMENTAL",
            "supporting_reference": "PubMed:12345678",
        }
    ]
    res_exp = analyzer.analyze_provenance(reviewed=True, annotations=exp_anns)
    assert res_exp["overall_category"] == "EXPERIMENTAL"
    assert res_exp["has_experimental_support"] is True
    assert res_exp["has_pubmed_reference"] is True
    assert res_exp["provenance_reliability"] >= 0.90
    assert res_exp["provenance_penalty"] <= 0.10

    # Computational unreviewed
    comp_anns = [
        {
            "functional_label": "Inferred kinase activity",
            "evidence_category": "COMPUTATIONAL_UNREVIEWED",
            "supporting_reference": "UniRule:UR0001",
        }
    ]
    res_comp = analyzer.analyze_provenance(reviewed=False, annotations=comp_anns)
    assert res_comp["overall_category"] == "COMPUTATIONAL_UNREVIEWED"
    assert res_comp["has_experimental_support"] is False
    assert res_comp["provenance_penalty"] >= 0.70
