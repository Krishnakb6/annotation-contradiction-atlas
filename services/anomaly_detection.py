"""
Method C: Embedding-based Anomaly Detection.
Compares ESM-2 sequence embeddings against high-confidence reference functional groups
using centroid distance, k-NN neighborhood density, and calibrated anomaly scaling.
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
    """

    def __init__(self, k_neighbors: int = 5, anomaly_threshold: float = 0.55):
        self.k_neighbors = k_neighbors
        self.anomaly_threshold = anomaly_threshold

    def evaluate_embedding(
        self,
        query_embedding: np.ndarray,
        reference_entries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Computes centroid distance, k-NN neighborhood distance, closest reference matches,
        and calibrated anomaly score.
        """
        if not reference_entries:
            return {
                "anomaly_score": 0.5,
                "is_outlier": False,
                "centroid_distance": 0.5,
                "knn_distance": 0.5,
                "closest_references": [],
                "threshold": self.anomaly_threshold,
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
                "closest_references": [],
                "threshold": self.anomaly_threshold,
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
                "distance": round(float(d), 4),
                "similarity": round(float(1.0 - d), 4),
            })

        # Calibrate anomaly score to [0.0, 1.0]
        # In ESM-2 cosine space, close kinases have dist ~0.05-0.25; divergent ~0.4-0.8+
        combined_dist = (0.4 * c_dist) + (0.6 * knn_dist)
        # Sigmoid-like or min-max calibration
        calibrated_score = max(0.0, min(1.0, combined_dist / 0.80))
        is_outlier = calibrated_score >= self.anomaly_threshold

        # Narrative explanation
        top_ref = closest_refs[0] if closest_refs else None
        ref_desc = f"{top_ref['gene_name'] or top_ref['accession']} (cosine dist: {top_ref['distance']:.3f})" if top_ref else "none"

        if is_outlier:
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
            "anomaly_score": round(float(calibrated_score), 4),
            "is_outlier": is_outlier,
            "centroid_distance": round(float(c_dist), 4),
            "knn_distance": round(float(knn_dist), 4),
            "closest_references": closest_refs,
            "threshold": self.anomaly_threshold,
            "method": "esm2_knn_centroid",
            "explanation": explanation,
        }
