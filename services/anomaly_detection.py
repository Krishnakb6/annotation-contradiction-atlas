"""
Method C: Embedding-based Anomaly Detection.
Compares ESM-2 sequence embeddings against high-confidence reference functional groups
using centroid distance, k-NN neighborhood density, class-conditioned manifold distance,
and empirically calibrated anomaly scaling.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("contradiction_atlas.anomaly")


def cosine_distance(u: np.ndarray, v: np.ndarray) -> float:
    """
    Computes cosine distance (1.0 - cosine_similarity).
    """
    u_norm = np.linalg.norm(u)
    v_norm = np.linalg.norm(v)
    if u_norm == 0 or v_norm == 0:
        return 1.0
    cos_sim = float(np.dot(u, v) / (u_norm * v_norm))
    return max(0.0, min(2.0, 1.0 - cos_sim))


class EmbeddingAnomalyDetector:
    """
    Detects unusual sequence representations relative to characterized kinase reference panels.
    Supports centroid distance, k-NN distance, class-conditioned manifold checks,
    and diagnostic score distribution profiling.
    """

    def __init__(
        self,
        k_neighbors: int = 5,
        anomaly_threshold: float = 0.20,
        calibration_scale: float = 0.35,
    ):
        self.k_neighbors = k_neighbors
        self.anomaly_threshold = anomaly_threshold
        self.calibration_scale = calibration_scale

    def calibrate_threshold_from_controls(
        self,
        control_embeddings: List[np.ndarray],
        reference_entries: List[Dict[str, Any]],
        percentile: float = 95.0,
    ) -> float:
        """
        Calibrates the anomaly threshold on independent control instances to bound
        the empirical false-positive rate (e.g. 95th percentile of congruent controls).
        """
        if not control_embeddings:
            return self.anomaly_threshold

        scores = []
        for emb in control_embeddings:
            eval_res = self.evaluate_embedding(emb, reference_entries)
            scores.append(eval_res["anomaly_score"])

        calibrated = float(np.percentile(scores, percentile))
        # Ensure a reasonable minimum threshold to prevent over-flagging
        self.anomaly_threshold = max(0.12, round(calibrated, 4))
        logger.info(
            f"Calibrated ESM-2 anomaly threshold to {self.anomaly_threshold} (percentile {percentile} on {len(control_embeddings)} controls)"
        )
        return self.anomaly_threshold

    def evaluate_embedding(
        self,
        query_embedding: np.ndarray,
        reference_entries: List[Dict[str, Any]],
        assigned_functional_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Computes centroid distance, k-NN neighborhood distance, closest reference matches,
        class-conditioned manifold distance, and calibrated anomaly score.
        """
        if not reference_entries:
            return {
                "anomaly_score": 0.5,
                "is_outlier": False,
                "centroid_distance": 0.5,
                "knn_distance": 0.5,
                "raw_combined_distance": 0.5,
                "closest_references": [],
                "threshold": self.anomaly_threshold,
                "class_concordant": True,
                "class_discordance_penalty": 0.0,
                "method": "insufficient_references",
                "explanation": "No reference kinase embeddings provided for comparison.",
            }

        ref_embs = []
        valid_refs = []
        for ref in reference_entries:
            emb = ref.get("embedding")
            if emb is not None and len(emb) == len(query_embedding):
                ref_embs.append(emb)
                valid_refs.append(ref)

        if not ref_embs:
            return {
                "anomaly_score": 0.5,
                "is_outlier": False,
                "centroid_distance": 0.5,
                "knn_distance": 0.5,
                "raw_combined_distance": 0.5,
                "closest_references": [],
                "threshold": self.anomaly_threshold,
                "class_concordant": True,
                "class_discordance_penalty": 0.0,
                "method": "dimension_mismatch",
                "explanation": "Reference embeddings have incompatible dimensions or are empty.",
            }

        ref_matrix = np.vstack(ref_embs)

        # 1. Centroid calculation
        centroid = np.mean(ref_matrix, axis=0)
        c_dist = cosine_distance(query_embedding, centroid)

        # 2. Pairwise distances to each reference
        distances = []
        for i, ref in enumerate(valid_refs):
            dist = cosine_distance(query_embedding, ref_matrix[i])
            distances.append((dist, ref))

        distances.sort(key=lambda x: x[0])

        # Top-k neighbors
        k = min(self.k_neighbors, len(distances))
        top_k = distances[:k]
        knn_dist = float(np.mean([d[0] for d in top_k]))

        # Format closest references
        closest_refs = []
        for d, ref in top_k:
            closest_refs.append({
                "accession": ref.get("accession"),
                "gene_name": ref.get("gene_name"),
                "protein_name": ref.get("protein_name"),
                "functional_label": ref.get("functional_label"),
                "distance": round(float(d), 4),
                "similarity": round(float(1.0 - d), 4),
            })

        # 3. Class-Conditioned Manifold Discordance (if assigned functional label is available)
        class_concordant = True
        discordance_penalty = 0.0
        if assigned_functional_label:
            q_label = assigned_functional_label.lower()
            is_q_tyr = "tyrosine" in q_label and "serine" not in q_label
            is_q_ser = "serine" in q_label or "threonine" in q_label

            matched_own_class_dists = []
            other_class_dists = []

            for d, ref in distances:
                r_label = (ref.get("functional_label") or "").lower()
                is_r_tyr = "tyrosine" in r_label and "serine" not in r_label
                is_r_ser = "serine" in r_label or "threonine" in r_label

                if (is_q_tyr and is_r_tyr) or (is_q_ser and is_r_ser):
                    matched_own_class_dists.append(d)
                elif (is_q_tyr and is_r_ser) or (is_q_ser and is_r_tyr):
                    other_class_dists.append(d)

            if matched_own_class_dists and other_class_dists:
                own_min = min(matched_own_class_dists)
                other_min = min(other_class_dists)
                # If nearest reference in other class is markedly closer than nearest in own class
                if other_min < own_min - 0.02:
                    class_concordant = False
                    discordance_penalty = min(0.30, float(own_min - other_min) * 3.0)

        # 4. Calibrate anomaly score to [0.0, 1.0]
        combined_dist = (0.4 * c_dist) + (0.6 * knn_dist)
        # Scaled by calibration_scale (default 0.35, where typical non-kinases are > 0.70)
        base_calibrated_score = max(0.0, min(1.0, combined_dist / self.calibration_scale))
        final_anomaly_score = max(0.0, min(1.0, base_calibrated_score + discordance_penalty))

        is_outlier = final_anomaly_score >= self.anomaly_threshold

        # Narrative explanation
        top_ref = closest_refs[0] if closest_refs else None
        ref_desc = (
            f"{top_ref['gene_name'] or top_ref['accession']} (cosine dist: {top_ref['distance']:.3f})"
            if top_ref
            else "none"
        )

        if not class_concordant:
            explanation = (
                f"Embedding manifold discordance: Sequence is closer to alternative functional kinase cluster "
                f"than to references matching assigned label '{assigned_functional_label}'. "
                f"Nearest reference is {ref_desc}."
            )
        elif is_outlier:
            explanation = (
                f"Embedding is significantly distant from reference kinases (k-NN dist: {knn_dist:.3f}, centroid dist: {c_dist:.3f}). "
                f"Nearest reference is {ref_desc}. Sequence occupies an atypical region in protein language model manifold."
            )
        else:
            explanation = (
                f"Embedding aligns well with canonical reference kinases (k-NN dist: {knn_dist:.3f}). "
                f"Nearest reference is {ref_desc}."
            )

        return {
            "anomaly_score": round(float(final_anomaly_score), 4),
            "base_anomaly_score": round(float(base_calibrated_score), 4),
            "is_outlier": is_outlier,
            "centroid_distance": round(float(c_dist), 4),
            "knn_distance": round(float(knn_dist), 4),
            "raw_combined_distance": round(float(combined_dist), 4),
            "class_concordant": class_concordant,
            "class_discordance_penalty": round(float(discordance_penalty), 4),
            "closest_references": closest_refs,
            "threshold": self.anomaly_threshold,
            "method": "esm2_knn_centroid",
            "explanation": explanation,
        }

    def compute_diagnostics(
        self,
        evaluated_cases: List[Dict[str, Any]],
        reference_entries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generates detailed score distribution diagnostics across benchmark subsets:
        - Score percentiles (min, 25%, 50%, 75%, 95%, max) for each category.
        - Nearest reference distances.
        - Positive prediction counts at varying threshold cutoffs.
        """
        category_scores: Dict[str, List[float]] = {}
        category_raw_dists: Dict[str, List[float]] = {}

        for item in evaluated_cases:
            cat = item.get("ground_truth_category", "UNKNOWN")
            score = item.get("embedding_anomaly_score", 0.0)
            raw_d = item.get("embedding_raw_distance", score)

            if cat not in category_scores:
                category_scores[cat] = []
                category_raw_dists[cat] = []

            category_scores[cat].append(score)
            category_raw_dists[cat].append(raw_d)

        distribution_summary = {}
        for cat, scores in category_scores.items():
            arr = np.array(scores)
            distribution_summary[cat] = {
                "count": len(arr),
                "mean": round(float(np.mean(arr)), 4),
                "std": round(float(np.std(arr)), 4),
                "min": round(float(np.min(arr)), 4),
                "p25": round(float(np.percentile(arr, 25)), 4),
                "median": round(float(np.median(arr)), 4),
                "p75": round(float(np.percentile(arr, 75)), 4),
                "p95": round(float(np.percentile(arr, 95)), 4),
                "max": round(float(np.max(arr)), 4),
            }

        # Sensitivity sweep across threshold cutoffs
        cutoffs = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60]
        threshold_sweep = []
        all_scores = [item.get("embedding_anomaly_score", 0.0) for item in evaluated_cases]
        for c in cutoffs:
            pos_preds = sum(1 for s in all_scores if s >= c)
            threshold_sweep.append({
                "threshold_cutoff": c,
                "positive_predictions": pos_preds,
                "positive_rate": round(pos_preds / len(all_scores), 4) if all_scores else 0.0,
            })

        return {
            "evaluated_sample_count": len(evaluated_cases),
            "reference_panel_size": len(reference_entries),
            "current_anomaly_threshold": self.anomaly_threshold,
            "category_distributions": distribution_summary,
            "threshold_sensitivity_sweep": threshold_sweep,
        }
