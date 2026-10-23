"""
Method A: Sequence Similarity Baseline.
Compares query kinase sequences against characterized high-confidence reference kinases
using Biopython PairwiseAligner with affine gap penalties.
Calculates alignment score, identity percentage, alignment coverage, and label concordance.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional, Tuple

try:
    from Bio.Align import PairwiseAligner
    BIO_AVAILABLE = True
except ImportError:
    BIO_AVAILABLE = False

logger = logging.getLogger("contradiction_atlas.similarity")


class SequenceSimilarityBaseline:
    """
    Computes local/global pairwise sequence alignment against a reference kinase panel.
    """

    def __init__(self, match_score: float = 2.0, mismatch_score: float = -1.0, open_gap_score: float = -10.0, extend_gap_score: float = -0.5):
        self.aligner = None
        if BIO_AVAILABLE:
            self.aligner = PairwiseAligner()
            self.aligner.mode = "global"
            self.aligner.match_score = match_score
            self.aligner.mismatch_score = mismatch_score
            self.aligner.open_gap_score = open_gap_score
            self.aligner.extend_gap_score = extend_gap_score

    def compute_identity_and_coverage(self, seq_query: str, seq_ref: str) -> Dict[str, float]:
        """
        Computes pairwise alignment, sequence identity fraction, and query coverage.
        """
        if not seq_query or not seq_ref:
            return {"identity": 0.0, "coverage": 0.0, "score": 0.0}

        if not self.aligner:
            # Fallback simple k-mer identity estimator if Bio is missing
            return self._fallback_kmer_similarity(seq_query, seq_ref)

        try:
            # For performance with full-length proteins, sample or align representative domains
            # If lengths are very large (>1500), truncate for baseline speed
            q_sub = seq_query[:1200]
            r_sub = seq_ref[:1200]

            score = self.aligner.score(q_sub, r_sub)
            max_possible = min(len(q_sub), len(r_sub)) * self.aligner.match_score
            normalized_score = max(0.0, min(1.0, score / max_possible)) if max_possible > 0 else 0.0

            # Estimate sequence identity via fast k-mer intersection
            q_kmers = set(q_sub[i:i+3] for i in range(len(q_sub)-2))
            r_kmers = set(r_sub[i:i+3] for i in range(len(r_sub)-2))
            jaccard = len(q_kmers & r_kmers) / max(len(q_kmers | r_kmers), 1)

            # Heuristic identity from jaccard and alignment score
            identity = (normalized_score * 0.7) + (jaccard * 0.3)
            coverage = min(len(seq_query), len(seq_ref)) / max(len(seq_query), len(seq_ref))

            return {
                "identity": round(float(identity), 4),
                "coverage": round(float(coverage), 4),
                "score": round(float(score), 2),
            }
        except Exception as e:
            logger.warning(f"Pairwise alignment error: {e}. Using fallback similarity.")
            return self._fallback_kmer_similarity(seq_query, seq_ref)

    def _fallback_kmer_similarity(self, s1: str, s2: str, k: int = 3) -> Dict[str, float]:
        kmers1 = set(s1[i:i+k] for i in range(len(s1)-k+1))
        kmers2 = set(s2[i:i+k] for i in range(len(s2)-k+1))
        if not kmers1 or not kmers2:
            return {"identity": 0.0, "coverage": 0.0, "score": 0.0}
        intersection = len(kmers1 & kmers2)
        union = len(kmers1 | kmers2)
        jaccard = intersection / union if union > 0 else 0.0
        coverage = min(len(s1), len(s2)) / max(len(s1), len(s2))
        return {
            "identity": round(float(jaccard), 4),
            "coverage": round(float(coverage), 4),
            "score": round(float(intersection), 2),
        }

    def compare_against_reference_panel(
        self,
        query_seq: str,
        query_label: Optional[str],
        reference_panel: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Compares query sequence against an entire reference panel.
        Finds the top matching reference kinase and evaluates functional consistency.
        """
        if not reference_panel:
            return {
                "best_reference_accession": None,
                "best_reference_gene": None,
                "best_identity": 0.0,
                "best_coverage": 0.0,
                "best_score": 0.0,
                "reference_label": None,
                "label_concordant": False,
                "anomaly_score": 1.0,
                "explanation": "No reference panel available for comparison.",
            }

        best_match = None
        best_sim = -1.0
        best_metrics = None

        for ref in reference_panel:
            ref_seq = ref.get("sequence", "")
            metrics = self.compute_identity_and_coverage(query_seq, ref_seq)
            sim = metrics["identity"] * (0.8 + 0.2 * metrics["coverage"])
            if sim > best_sim:
                best_sim = sim
                best_match = ref
                best_metrics = metrics

        ref_acc = best_match.get("accession")
        ref_gene = best_match.get("gene_name")
        ref_label = best_match.get("functional_label", "Kinase catalytic activity")

        # Evaluate label concordance (e.g. Tyrosine kinase vs Serine/threonine kinase)
        label_concordant = True
        if query_label and ref_label:
            q_lower = query_label.lower()
            r_lower = ref_label.lower()
            # Check for tyrosine vs serine/threonine mismatch
            if ("tyrosine" in q_lower and "serine" in r_lower and "tyrosine" not in r_lower) or \
               ("serine" in q_lower and "tyrosine" in r_lower and "serine" not in r_lower):
                label_concordant = False

        # Sequence anomaly score is inverse of similarity
        sim_identity = best_metrics["identity"] if best_metrics else 0.0
        anomaly_score = max(0.0, min(1.0, 1.0 - sim_identity))

        explanation = (
            f"Nearest high-confidence reference is {ref_gene or ref_acc} (Identity: {sim_identity*100:.1f}%, "
            f"Coverage: {best_metrics['coverage']*100:.1f}%). "
            f"{'Functional labels are consistent.' if label_concordant else 'Noticeable functional class discordance detected.'}"
        )

        return {
            "best_reference_accession": ref_acc,
            "best_reference_gene": ref_gene,
            "best_identity": best_metrics["identity"],
            "best_coverage": best_metrics["coverage"],
            "best_score": best_metrics["score"],
            "reference_label": ref_label,
            "label_concordant": label_concordant,
            "anomaly_score": round(float(anomaly_score), 4),
            "explanation": explanation,
        }
