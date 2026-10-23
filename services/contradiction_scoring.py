"""
Evidence-Aware Contradiction Scoring and Review Prioritization Engine.
Synthesizes signals from ESM-2 embeddings, sequence similarity baselines,
catalytic motif integrity, and annotation provenance into an interpretable priority tier.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional, Tuple

from config import WEIGHTS, PRIORITY_THRESHOLDS

logger = logging.getLogger("contradiction_atlas.scoring")


class ContradictionScorer:
    """
    Computes explainable review priorities and natural-language evidence summaries.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None,
    ):
        self.weights = weights or WEIGHTS
        self.thresholds = thresholds or PRIORITY_THRESHOLDS

    def compute_review_priority(
        self,
        embedding_result: Dict[str, Any],
        similarity_result: Dict[str, Any],
        feature_result: Dict[str, Any],
        provenance_result: Dict[str, Any],
        protein_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculates multi-evidence contradiction score, priority tier, and structured narrative.
        """
        # Extract individual component scores (all normalized in [0.0, 1.0])
        emb_score = float(embedding_result.get("anomaly_score", 0.5))
        sim_score = float(similarity_result.get("anomaly_score", 0.5))
        feat_score = float(feature_result.get("anomaly_score", 0.5))
        prov_score = float(provenance_result.get("provenance_penalty", 0.5))

        # Check for label discordance in sequence similarity
        if not similarity_result.get("label_concordant", True):
            sim_score = min(1.0, sim_score + 0.20)

        # Scientific Safeguard 1: Low annotation confidence alone cannot produce a HIGH score
        # If both sequence features and embeddings indicate a canonical, consistent kinase,
        # cap contradiction score at MODERATE (max 0.55).
        is_canonical_sequence = (feat_score <= 0.15) and (emb_score <= 0.40)

        # Scientific Safeguard 2: Unusual embedding alone cannot prove misannotation
        is_isolated_embedding_anomaly = (emb_score >= 0.70) and (feat_score <= 0.15) and (sim_score <= 0.35)

        # Weighted combination
        raw_score = (
            self.weights["embedding_anomaly"] * emb_score
            + self.weights["sequence_similarity"] * sim_score
            + self.weights["kinase_feature"] * feat_score
            + self.weights["provenance_penalty"] * prov_score
        )

        if is_canonical_sequence and raw_score >= self.thresholds["HIGH"]:
            # Prevent pure provenance uncertainty from triggering HIGH priority
            raw_score = 0.55

        contradiction_score = round(float(raw_score), 4)

        # Determine priority category
        if contradiction_score >= self.thresholds["HIGH"]:
            review_priority = "HIGH"
        elif contradiction_score >= self.thresholds["MODERATE"]:
            review_priority = "MODERATE"
        else:
            review_priority = "LOW"

        # Categorize nature of the finding
        is_pseudokinase = (
            feature_result.get("variant_count", 0) > 0
            or "pseudokinase" in (protein_info.get("protein_name", "").lower() if protein_info else "")
            or "inactive" in (protein_info.get("protein_name", "").lower() if protein_info else "")
        )

        if is_pseudokinase:
            finding_category = "Biological exception / Pseudokinase candidate"
        elif contradiction_score >= self.thresholds["HIGH"]:
            finding_category = "Potential functional annotation inconsistency"
        elif prov_score >= 0.65 and feat_score <= 0.20:
            finding_category = "Annotation with limited supporting evidence"
        elif is_isolated_embedding_anomaly:
            finding_category = "Unusual but potentially legitimate protein (divergent variant)"
        else:
            finding_category = "Congruent annotation / Low review priority"

        # Generate structured explanations and signal lists
        flag_reason, contradictory_signals, evidence_summary, limitations = self._generate_narrative(
            review_priority=review_priority,
            finding_category=finding_category,
            contradiction_score=contradiction_score,
            emb_res=embedding_result,
            sim_res=similarity_result,
            feat_res=feature_result,
            prov_res=provenance_result,
            is_pseudokinase=is_pseudokinase,
        )

        return {
            "review_priority": review_priority,
            "contradiction_score": contradiction_score,
            "finding_category": finding_category,
            "flag_reason": flag_reason,
            "supporting_evidence_summary": evidence_summary,
            "contradictory_signals": contradictory_signals,
            "limitations": limitations,
            "component_scores": {
                "embedding_anomaly": emb_score,
                "sequence_similarity": sim_score,
                "kinase_feature": feat_score,
                "provenance_penalty": prov_score,
            },
        }

    def _generate_narrative(
        self,
        review_priority: str,
        finding_category: str,
        contradiction_score: float,
        emb_res: Dict[str, Any],
        sim_res: Dict[str, Any],
        feat_res: Dict[str, Any],
        prov_res: Dict[str, Any],
        is_pseudokinase: bool,
    ) -> Tuple[str, str, str, str]:
        reasons: List[str] = []
        signals: List[str] = []

        # Feature signals
        absent_count = feat_res.get("absent_count", 0)
        variant_count = feat_res.get("variant_count", 0)
        if absent_count > 0:
            reasons.append(f"A core kinase motif is absent ({feat_res.get('summary', '')})")
            signals.append(f"Missing catalytic motif(s) [Anomaly: {feat_res.get('anomaly_score', 0):.2f}]")
        elif variant_count > 0:
            reasons.append(f"Atypical motif variant detected: {feat_res.get('summary', '')}")
            signals.append(f"Variant motif sequence [Anomaly: {feat_res.get('anomaly_score', 0):.2f}]")

        # Embedding signals
        if emb_res.get("is_outlier", False):
            reasons.append(f"Protein language model embedding is significantly distant from canonical kinase manifold (score: {emb_res.get('anomaly_score', 0):.2f})")
            signals.append(f"ESM-2 embedding outlier [dist: {emb_res.get('knn_distance', 0):.2f}]")

        # Sequence similarity signals
        if not sim_res.get("label_concordant", True):
            reasons.append(f"Sequence similarity baseline identifies discordant reference functional class ({sim_res.get('reference_label', '')})")
            signals.append(f"Reference label disagreement [Query vs Ref: {sim_res.get('best_reference_accession', '')}]")
        elif sim_res.get("best_identity", 1.0) < 0.35:
            reasons.append(f"Low sequence identity to top reference kinase ({sim_res.get('best_identity', 0)*100:.1f}%)")
            signals.append(f"Low reference sequence homology [Identity: {sim_res.get('best_identity', 0)*100:.1f}%]")

        # Provenance signals
        if prov_res.get("overall_category") in ("COMPUTATIONAL_UNREVIEWED", "UNANNOTATED"):
            reasons.append("Functional label is derived primarily from automated unreviewed computational inference without experimental assay support")
            signals.append("Purely computational / unreviewed provenance")

        if not reasons:
            reasons.append("Evidence across sequence features, embeddings, and provenance is mutually congruent with assigned function.")
            signals.append("No active contradictory signals detected.")

        flag_reason = f"Classified as '{finding_category}' (Priority: {review_priority}, Composite Score: {contradiction_score:.2f}). " + " ".join(reasons)

        evidence_summary = (
            f"Provenance tier: {prov_res.get('overall_category', 'UNSPECIFIED')} ({prov_res.get('summary', '')}). "
            f"Motif status: {feat_res.get('canonical_count', 0)}/3 canonical, {variant_count} variant, {absent_count} absent. "
            f"Nearest reference kinase: {sim_res.get('best_reference_gene') or sim_res.get('best_reference_accession') or 'None'} "
            f"(Identity: {sim_res.get('best_identity', 0)*100:.1f}%)."
        )

        limitations = (
            "Flagging represents an evidence-supported review priority, not definitive proof of an annotation error. "
            "Divergent sequences may represent legitimate evolutionary specializations, non-catalytic scaffolding roles, "
            "or allosteric regulatory adaptations. Physical biochemical assays remain required to conclusively verify catalytic status."
        )

        return flag_reason, "; ".join(signals), evidence_summary, limitations
