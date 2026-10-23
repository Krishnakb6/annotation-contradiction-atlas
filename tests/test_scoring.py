"""
Unit tests for evidence-aware contradiction scoring, priority thresholds, and safeguards.
"""
import pytest
from services.contradiction_scoring import ContradictionScorer


@pytest.fixture
def scorer():
    return ContradictionScorer()


def test_congruent_canonical_kinase(scorer):
    # Canonical EGFR-like profile
    emb_res = {"anomaly_score": 0.12, "is_outlier": False, "knn_distance": 0.15}
    sim_res = {"anomaly_score": 0.10, "label_concordant": True, "best_identity": 0.95}
    feat_res = {"anomaly_score": 0.0, "canonical_count": 3, "variant_count": 0, "absent_count": 0, "summary": "All motifs present."}
    prov_res = {"provenance_penalty": 0.05, "overall_category": "EXPERIMENTAL", "summary": "Direct experimental."}

    res = scorer.compute_review_priority(emb_res, sim_res, feat_res, prov_res)
    assert res["review_priority"] == "LOW"
    assert res["contradiction_score"] < 0.40
    assert "Congruent" in res["finding_category"]


def test_broken_catalytic_motifs_triggers_high_priority(scorer):
    # Broken motifs + computational provenance
    emb_res = {"anomaly_score": 0.65, "is_outlier": True, "knn_distance": 0.62}
    sim_res = {"anomaly_score": 0.60, "label_concordant": False, "best_identity": 0.30}
    feat_res = {"anomaly_score": 0.90, "canonical_count": 0, "variant_count": 0, "absent_count": 3, "summary": "Missing core motifs."}
    prov_res = {"provenance_penalty": 0.85, "overall_category": "COMPUTATIONAL_UNREVIEWED", "summary": "Unreviewed rule."}

    res = scorer.compute_review_priority(emb_res, sim_res, feat_res, prov_res)
    assert res["review_priority"] == "HIGH"
    assert res["contradiction_score"] >= 0.65
    assert "Potential functional annotation inconsistency" in res["finding_category"]
    assert "Missing catalytic motif" in res["contradictory_signals"]


def test_safeguard_low_provenance_alone_cannot_trigger_high(scorer):
    # Canonical sequence & embedding, but only computational annotation
    emb_res = {"anomaly_score": 0.15, "is_outlier": False}
    sim_res = {"anomaly_score": 0.15, "label_concordant": True, "best_identity": 0.85}
    feat_res = {"anomaly_score": 0.05, "canonical_count": 3, "variant_count": 0, "absent_count": 0}
    prov_res = {"provenance_penalty": 0.95, "overall_category": "COMPUTATIONAL_UNREVIEWED"}

    res = scorer.compute_review_priority(emb_res, sim_res, feat_res, prov_res)
    # Must NOT be HIGH
    assert res["review_priority"] != "HIGH"
    assert res["contradiction_score"] < 0.65


def test_pseudokinase_exception_classification(scorer):
    # VRK3-like pseudokinase
    emb_res = {"anomaly_score": 0.50, "is_outlier": False}
    sim_res = {"anomaly_score": 0.45, "label_concordant": True, "best_identity": 0.50}
    feat_res = {"anomaly_score": 0.40, "canonical_count": 2, "variant_count": 1, "absent_count": 0, "summary": "Variant HRD (HGN)."}
    prov_res = {"provenance_penalty": 0.20, "overall_category": "EXPERIMENTAL"}
    prot_info = {"protein_name": "Inactive serine/threonine-protein kinase VRK3"}

    res = scorer.compute_review_priority(emb_res, sim_res, feat_res, prov_res, protein_info=prot_info)
    assert "Pseudokinase" in res["finding_category"] or "Biological exception" in res["finding_category"]
