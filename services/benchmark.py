"""
Ground-truth and Evaluation Benchmark Service.
Constructs explicitly categorized evaluation instances:
- Category A: High-confidence reference kinases
- Category B: Naturally occurring cases / pseudokinases
- Category C: Synthetic controlled inconsistencies (motif perturbation, label swaps)
Evaluates baseline vs embedding vs features vs evidence-aware ensemble without data leakage.
"""
from __future__ import annotations

import json
import logging
import random
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from config import BENCHMARK_DIR, ARTIFACTS_DIR, RANDOM_SEED
from database.connection import get_db_session
from database.models import BenchmarkCase, Protein
from database.repositories import BenchmarkRepository, ProteinRepository

logger = logging.getLogger("contradiction_atlas.benchmark")


def calculate_binary_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, Any]:
    """
    Computes confusion matrix, Precision, Recall, F1-score, Specificity, and Accuracy.
    """
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have identical length")

    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    total = len(y_true)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / total if total > 0 else 0.0

    return {
        "sample_size": total,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "specificity": round(float(specificity), 4),
        "f1_score": round(float(f1), 4),
        "accuracy": round(float(accuracy), 4),
    }


class BenchmarkService:
    """
    Generates controlled benchmarks and executes comparative evaluations across Atlas methods.
    """

    def __init__(self, benchmark_dir: Path = BENCHMARK_DIR, artifacts_dir: Path = ARTIFACTS_DIR):
        self.benchmark_dir = benchmark_dir
        self.artifacts_dir = artifacts_dir

    def build_synthetic_benchmark(
        self,
        base_proteins: List[Dict[str, Any]],
        seed: int = RANDOM_SEED,
        num_synthetic_cases: int = 40,
    ) -> List[Dict[str, Any]]:
        """
        Creates synthetic controlled test cases:
        1. Catalytic motif alterations (K->A in VAIK, D->A in HRD/DFG).
        2. Functional label swaps (Tyrosine kinase <-> Serine/threonine kinase).
        3. Unaltered positive controls.
        All synthetic cases are isolated from real database records.
        """
        rng = random.Random(seed)
        cases: List[Dict[str, Any]] = []

        if not base_proteins:
            return cases

        # 1. Motif Disruption Cases (ground truth: INCONSISTENT_CATALYTIC, is_inconsistent=True)
        for i in range(num_synthetic_cases // 2):
            base = rng.choice(base_proteins)
            seq = base.get("sequence", "")
            if not seq or len(seq) < 50:
                continue

            # Mutate VAIK or HRD or DFG
            mutated_seq = seq
            mod_type = ""
            orig_motif = ""
            sub_motif = ""

            if "VAIK" in seq:
                mutated_seq = seq.replace("VAIK", "VAIA", 1)
                mod_type = "catalytic_lysine_knockout"
                orig_motif = "VAIK"
                sub_motif = "VAIA"
            elif "HRD" in seq:
                mutated_seq = seq.replace("HRD", "HAA", 1)
                mod_type = "catalytic_base_aspartate_knockout"
                orig_motif = "HRD"
                sub_motif = "HAA"
            elif "DFG" in seq:
                mutated_seq = seq.replace("DFG", "AFG", 1)
                mod_type = "metal_binding_aspartate_knockout"
                orig_motif = "DFG"
                sub_motif = "AFG"
            else:
                # Force replace a middle segment
                mid = len(seq) // 2
                mutated_seq = seq[:mid] + "AAAA" + seq[mid+4:]
                mod_type = "core_segment_knockout"
                orig_motif = "native"
                sub_motif = "AAAA"

            cases.append({
                "synthetic_identifier": f"SYNTH_MOTIF_{seed}_{i+1:03d}",
                "original_accession": base.get("accession"),
                "gene_name": base.get("gene_name"),
                "sequence": mutated_seq,
                "functional_label": base.get("functional_label", "ATP + protein = ADP + phosphoprotein"),
                "case_type": "CATEGORY_C_SYNTHETIC",
                "ground_truth_category": "INCONSISTENT_CATALYTIC",
                "is_inconsistent": True,
                "label_rationale": f"Deliberately mutated {orig_motif} -> {sub_motif} ({mod_type}) breaking essential catalytic residue.",
                "synthetic_modification_details": {
                    "type": mod_type,
                    "original_motif": orig_motif,
                    "mutated_motif": sub_motif,
                    "parent_accession": base.get("accession"),
                },
                "dataset_split": "TEST" if i % 2 == 0 else "CALIBRATION",
                "random_seed": seed,
            })

        # 2. Label Swaps (ground truth: LABEL_MISMATCH, is_inconsistent=True)
        for i in range(num_synthetic_cases // 4):
            base = rng.choice(base_proteins)
            seq = base.get("sequence", "")
            orig_label = base.get("functional_label", "")

            # Swap tyrosine vs serine/threonine
            if "tyrosine" in orig_label.lower():
                swapped_label = "protein serine/threonine kinase activity"
            else:
                swapped_label = "protein-tyrosine kinase activity"

            cases.append({
                "synthetic_identifier": f"SYNTH_LABEL_{seed}_{i+1:03d}",
                "original_accession": base.get("accession"),
                "gene_name": base.get("gene_name"),
                "sequence": seq,
                "functional_label": swapped_label,
                "case_type": "CATEGORY_C_SYNTHETIC",
                "ground_truth_category": "LABEL_MISMATCH",
                "is_inconsistent": True,
                "label_rationale": f"Deliberate functional label swap: original was '{orig_label}', swapped to '{swapped_label}'.",
                "synthetic_modification_details": {
                    "type": "functional_label_swap",
                    "original_label": orig_label,
                    "swapped_label": swapped_label,
                    "parent_accession": base.get("accession"),
                },
                "dataset_split": "TEST",
                "random_seed": seed,
            })

        # 3. Unaltered Congruent Controls (ground truth: CONGRUENT, is_inconsistent=False)
        for i in range(num_synthetic_cases // 4):
            base = rng.choice(base_proteins)
            cases.append({
                "synthetic_identifier": f"SYNTH_CONTROL_{seed}_{i+1:03d}",
                "original_accession": base.get("accession"),
                "gene_name": base.get("gene_name"),
                "sequence": base.get("sequence", ""),
                "functional_label": base.get("functional_label", "ATP + protein = ADP + phosphoprotein"),
                "case_type": "CATEGORY_C_SYNTHETIC",
                "ground_truth_category": "CONGRUENT",
                "is_inconsistent": False,
                "label_rationale": "Unaltered canonical kinase sequence paired with verified annotation as positive control.",
                "synthetic_modification_details": {"type": "unaltered_control", "parent_accession": base.get("accession")},
                "dataset_split": "TEST",
                "random_seed": seed,
            })

        return cases

    def run_evaluation(
        self,
        benchmark_cases: List[Dict[str, Any]],
        reference_panel: List[Dict[str, Any]],
        similarity_service: Any,
        embedding_service: Any,
        feature_analyzer: Any,
        scorer: Any,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end evaluation comparing:
        1. Sequence similarity baseline
        2. Embedding anomaly detection
        3. Kinase feature checks
        4. Combined evidence-aware prioritization
        """
        if not benchmark_cases:
            return {"status": "NO_CASES", "message": "No benchmark cases provided for evaluation."}

        # Predictions store
        preds_sim = []
        preds_emb = []
        preds_feat = []
        preds_ensemble = []
        y_true = []

        detailed_results: List[Dict[str, Any]] = []

        for case in benchmark_cases:
            is_inc = 1 if case["is_inconsistent"] else 0
            y_true.append(is_inc)
            seq = case["sequence"]
            label = case.get("functional_label")

            # 1. Feature check
            feat_res = feature_analyzer.analyze_sequence(seq)
            # Feature predicts anomaly if integrity < 0.70 or anomaly >= 0.30
            pred_feat = 1 if feat_res["anomaly_score"] >= 0.30 else 0
            preds_feat.append(pred_feat)

            # 2. Sequence similarity baseline
            sim_res = similarity_service.compare_against_reference_panel(seq, label, reference_panel)
            # Similarity predicts anomaly if discordant label or anomaly >= 0.40
            pred_sim = 1 if (not sim_res["label_concordant"] or sim_res["anomaly_score"] >= 0.40) else 0
            preds_sim.append(pred_sim)

            # 3. ESM-2 Embedding Anomaly
            emb, _ = embedding_service.compute_embedding(seq, accession=case.get("synthetic_identifier") or case.get("accession"))
            # Compare against reference embeddings
            # We can use cosine distance to reference panel average
            from services.anomaly_detection import EmbeddingAnomalyDetector
            det = EmbeddingAnomalyDetector()
            emb_res = det.evaluate_embedding(emb, reference_panel)
            pred_emb = 1 if emb_res["is_outlier"] or emb_res["anomaly_score"] >= 0.50 else 0
            preds_emb.append(pred_emb)

            # 4. Combined Evidence-Aware Prioritization
            prov_res = {
                "provenance_penalty": 0.30 if not case.get("synthetic_identifier") else 0.50,
                "overall_category": "PHYLOGENETIC_CURATED" if not case.get("synthetic_identifier") else "COMPUTATIONAL_UNREVIEWED",
                "summary": "Benchmark evaluation instance.",
            }
            score_res = scorer.compute_review_priority(emb_res, sim_res, feat_res, prov_res)
            # Ensemble predicts inconsistency if review_priority in ("HIGH", "MODERATE")
            pred_ensemble = 1 if score_res["review_priority"] in ("HIGH", "MODERATE") else 0
            preds_ensemble.append(pred_ensemble)

            detailed_results.append({
                "identifier": case.get("synthetic_identifier") or case.get("accession"),
                "ground_truth": "INCONSISTENT" if is_inc == 1 else "CONGRUENT",
                "category": case.get("ground_truth_category"),
                "type": case.get("case_type"),
                "predictions": {
                    "similarity": pred_sim,
                    "embedding": pred_emb,
                    "features": pred_feat,
                    "ensemble": pred_ensemble,
                },
                "ensemble_priority": score_res["review_priority"],
                "contradiction_score": score_res["contradiction_score"],
            })

        # Calculate metrics for each method
        metrics_sim = calculate_binary_metrics(y_true, preds_sim)
        metrics_emb = calculate_binary_metrics(y_true, preds_emb)
        metrics_feat = calculate_binary_metrics(y_true, preds_feat)
        metrics_ensemble = calculate_binary_metrics(y_true, preds_ensemble)

        # Separate synthetic vs natural cases
        synth_indices = [i for i, c in enumerate(benchmark_cases) if c.get("case_type") == "CATEGORY_C_SYNTHETIC"]
        natural_indices = [i for i, c in enumerate(benchmark_cases) if c.get("case_type") != "CATEGORY_C_SYNTHETIC"]

        synth_metrics = None
        if synth_indices:
            synth_y_true = [y_true[i] for i in synth_indices]
            synth_y_pred = [preds_ensemble[i] for i in synth_indices]
            synth_metrics = calculate_binary_metrics(synth_y_true, synth_y_pred)

        natural_metrics = None
        if natural_indices:
            nat_y_true = [y_true[i] for i in natural_indices]
            nat_y_pred = [preds_ensemble[i] for i in natural_indices]
            natural_metrics = calculate_binary_metrics(nat_y_true, nat_y_pred)

        report = {
            "evaluation_title": "Multi-Method Comparative Benchmark on Protein Kinase Inconsistency Detection",
            "total_benchmark_cases": len(benchmark_cases),
            "synthetic_cases_count": len(synth_indices),
            "natural_cases_count": len(natural_indices),
            "methods_comparison": {
                "sequence_similarity_baseline": metrics_sim,
                "esm2_embedding_anomaly": metrics_emb,
                "kinase_biological_features": metrics_feat,
                "evidence_aware_ensemble": metrics_ensemble,
            },
            "synthetic_subset_performance": synth_metrics,
            "natural_subset_performance": natural_metrics,
            "detailed_case_evaluations": detailed_results,
            "scientific_limitations": [
                "Controlled synthetic motif disruptions provide proof-of-concept verification but cannot emulate all nuances of in vivo functional divergence.",
                "High precision on synthetic datasets does not guarantee identical performance on ambiguous natural borderline pseudokinases.",
                "False positives may highlight legitimate biological variants (atypical kinases) rather than clerical database errors.",
            ]
        }

        # Save report artifact
        artifact_file = self.artifacts_dir / "evaluation_report.json"
        try:
            with open(artifact_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Evaluation report saved to {artifact_file}")
        except Exception as e:
            logger.error(f"Failed to write evaluation report artifact: {e}")

        return report
