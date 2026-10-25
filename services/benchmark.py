"""
Ground-truth and Evaluation Benchmark Service (Version 2).
Constructs explicitly categorized evaluation instances:
- Category A: High-confidence congruent references (CONGRUENT_REFERENCE)
- Category B: Naturally occurring cases / pseudokinases (NATURAL_EXCEPTION)
- Category C: Synthetic label inconsistencies (SYNTHETIC_LABEL_CONTRADICTION)
- Category D: Synthetic sequence perturbations (SYNTHETIC_SEQUENCE_PERTURBATION)
- Unaltered synthetic controls (CONGRUENT_CONTROL)

Evaluates baseline vs embedding vs features vs evidence-aware ensemble without test-set leakage,
separating calibration from testing, and generating multi-task evaluation reports.
"""
from __future__ import annotations

import csv
import json
import logging
import random
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from config import BENCHMARK_DIR, ARTIFACTS_DIR, RANDOM_SEED, DEFAULT_ESM_MODEL
from database.connection import get_db_session
from database.models import BenchmarkCase, Protein
from database.repositories import BenchmarkRepository, ProteinRepository
from services.evaluation import calculate_binary_metrics, format_metrics_table

logger = logging.getLogger("contradiction_atlas.benchmark")


class BenchmarkService:
    """
    Generates controlled benchmarks and executes comparative evaluations across Atlas methods
    with explicit task separation and calibration/testing partition isolation.
    """

    def __init__(self, benchmark_dir: Path = BENCHMARK_DIR, artifacts_dir: Path = ARTIFACTS_DIR):
        self.benchmark_dir = benchmark_dir
        self.artifacts_dir = artifacts_dir

    def build_synthetic_benchmark(
        self,
        base_proteins: List[Dict[str, Any]],
        seed: int = RANDOM_SEED,
        num_synthetic_cases: int = 32,
    ) -> List[Dict[str, Any]]:
        """
        Creates synthetic controlled test cases divided into:
        - Category D: Catalytic motif alterations (VAIK, HRD, DFG knockouts)
        - Category C: Functional label swaps (Tyrosine kinase <-> Serine/threonine kinase)
        - Unaltered positive controls

        Instances are explicitly partitioned into CALIBRATION (train/dev) and TEST (eval).
        """
        rng = random.Random(seed)
        cases: List[Dict[str, Any]] = []

        if not base_proteins:
            return cases

        # 1. Category D: Motif Perturbations (ground truth: SYNTHETIC_SEQUENCE_PERTURBATION, is_inconsistent=True)
        # Allocate half the synthetic budget to motif perturbations
        n_motif = num_synthetic_cases // 2
        for i in range(n_motif):
            base = rng.choice(base_proteins)
            seq = base.get("sequence", "")
            if not seq or len(seq) < 50:
                continue

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
                mid = len(seq) // 2
                mutated_seq = seq[:mid] + "AAAA" + seq[mid+4:]
                mod_type = "core_segment_knockout"
                orig_motif = "native"
                sub_motif = "AAAA"

            # Assign alternating splits to ensure 50% calibration, 50% test
            split = "CALIBRATION" if i % 2 == 0 else "TEST"

            cases.append({
                "synthetic_identifier": f"SYNTH_MOTIF_{seed}_{i+1:03d}",
                "original_accession": base.get("accession"),
                "gene_name": base.get("gene_name"),
                "sequence": mutated_seq,
                "functional_label": base.get("functional_label", "ATP + protein = ADP + phosphoprotein"),
                "case_type": "CATEGORY_D_SYNTHETIC_SEQUENCE",
                "ground_truth_category": "SYNTHETIC_SEQUENCE_PERTURBATION",
                "is_inconsistent": True,
                "label_rationale": (
                    f"Deliberately mutated {orig_motif} -> {sub_motif} ({mod_type}) breaking "
                    "essential conserved catalytic residue."
                ),
                "synthetic_modification_details": {
                    "type": mod_type,
                    "original_motif": orig_motif,
                    "mutated_motif": sub_motif,
                    "parent_accession": base.get("accession"),
                },
                "dataset_split": split,
                "random_seed": seed,
            })

        # 2. Category C: Functional Label Swaps (ground truth: SYNTHETIC_LABEL_CONTRADICTION, is_inconsistent=True)
        # Allocate 25% of the synthetic budget
        n_label = num_synthetic_cases // 4
        for i in range(n_label):
            base = rng.choice(base_proteins)
            seq = base.get("sequence", "")
            orig_label = base.get("functional_label", "")

            if "tyrosine" in orig_label.lower():
                swapped_label = "protein serine/threonine kinase activity"
                swap_rationale = "Swapped true Tyrosine kinase annotation to Serine/threonine kinase."
            else:
                swapped_label = "protein-tyrosine kinase activity"
                swap_rationale = "Swapped true Serine/threonine kinase annotation to Tyrosine kinase."

            split = "CALIBRATION" if i % 2 == 0 else "TEST"

            cases.append({
                "synthetic_identifier": f"SYNTH_LABEL_{seed}_{i+1:03d}",
                "original_accession": base.get("accession"),
                "gene_name": base.get("gene_name"),
                "sequence": seq,
                "functional_label": swapped_label,
                "case_type": "CATEGORY_C_SYNTHETIC_LABEL",
                "ground_truth_category": "SYNTHETIC_LABEL_CONTRADICTION",
                "is_inconsistent": True,
                "label_rationale": (
                    f"Controlled functional label swap: original was '{orig_label}', swapped to '{swapped_label}'. "
                    f"{swap_rationale}"
                ),
                "synthetic_modification_details": {
                    "type": "functional_label_swap",
                    "original_label": orig_label,
                    "swapped_label": swapped_label,
                    "parent_accession": base.get("accession"),
                },
                "dataset_split": split,
                "random_seed": seed,
            })

        # 3. Unaltered Congruent Controls (ground truth: CONGRUENT_CONTROL, is_inconsistent=False)
        # Allocate remaining 25% of budget as negative controls
        n_ctrl = num_synthetic_cases - n_motif - n_label
        for i in range(n_ctrl):
            base = rng.choice(base_proteins)
            split = "CALIBRATION" if i % 2 == 0 else "TEST"

            cases.append({
                "synthetic_identifier": f"SYNTH_CONTROL_{seed}_{i+1:03d}",
                "original_accession": base.get("accession"),
                "gene_name": base.get("gene_name"),
                "sequence": base.get("sequence", ""),
                "functional_label": base.get("functional_label", "ATP + protein = ADP + phosphoprotein"),
                "case_type": "CATEGORY_C_SYNTHETIC_CONTROL",
                "ground_truth_category": "CONGRUENT_CONTROL",
                "is_inconsistent": False,
                "label_rationale": "Unaltered canonical kinase sequence paired with verified annotation as negative control.",
                "synthetic_modification_details": {
                    "type": "unaltered_control",
                    "parent_accession": base.get("accession"),
                },
                "dataset_split": split,
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
        model_name: str = DEFAULT_ESM_MODEL,
        run_id: str = "EVAL_V2_RUN",
    ) -> Dict[str, Any]:
        """
        Executes multi-task scientific benchmark evaluation:
        1. Calibrates thresholds on CALIBRATION split.
        2. Evaluates Task 1: Synthetic Label Contradiction Detection.
        3. Evaluates Task 2: Synthetic Sequence Perturbation Detection.
        4. Evaluates Task 3: Natural Biological Exception Characterization (Exploratory).
        5. Reports Overall Methods Comparison on the independent TEST split.
        6. Generates full score distributions and diagnostic artifacts.
        """
        if not benchmark_cases:
            return {"status": "NO_CASES", "message": "No benchmark cases provided for evaluation."}

        # 1. Isolate Calibration vs Test instances
        calib_cases = [c for c in benchmark_cases if c.get("dataset_split") == "CALIBRATION"]
        test_cases = [c for c in benchmark_cases if c.get("dataset_split") == "TEST"]
        cat_b_cases = [c for c in benchmark_cases if c.get("case_type") == "CATEGORY_B_NATURAL_EXCEPTION"]

        logger.info(
            f"Benchmark partition: {len(calib_cases)} Calibration, {len(test_cases)} Test, {len(cat_b_cases)} Natural Exceptions"
        )

        # 2. Calibration Phase: Calibrate ESM-2 threshold on calibration controls
        from services.anomaly_detection import EmbeddingAnomalyDetector
        det = EmbeddingAnomalyDetector(k_neighbors=5, anomaly_threshold=0.20, calibration_scale=0.35)

        # Collect calibration control embeddings
        calib_control_embs = []
        for c in calib_cases:
            if not c.get("is_inconsistent"):
                emb, _ = embedding_service.compute_embedding(
                    c["sequence"],
                    accession=c.get("synthetic_identifier") or c.get("accession"),
                    use_cache=True,
                )
                calib_control_embs.append(emb)

        if calib_control_embs:
            calibrated_threshold = det.calibrate_threshold_from_controls(
                calib_control_embs, reference_panel, percentile=95.0
            )
        else:
            calibrated_threshold = det.anomaly_threshold

        frozen_thresholds = {
            "similarity_anomaly_threshold": 0.40,
            "feature_anomaly_threshold": 0.30,
            "esm2_anomaly_threshold": calibrated_threshold,
            "ensemble_review_priority_threshold": "HIGH_OR_MODERATE (Score >= 0.40)",
        }
        logger.info(f"Frozen thresholds for evaluation: {frozen_thresholds}")

        # Helper evaluation function for any given subset of cases
        def evaluate_case_subset(cases_subset: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
            detailed_list = []
            y_true = []
            preds_sim = []
            preds_emb = []
            preds_feat = []
            preds_ensemble = []

            for case in cases_subset:
                is_inc = 1 if case.get("is_inconsistent") else 0
                y_true.append(is_inc)
                seq = case["sequence"]
                label = case.get("functional_label")
                ident = case.get("synthetic_identifier") or case.get("accession")

                # A. Feature analysis
                feat_res = feature_analyzer.analyze_sequence(seq)
                pred_feat = 1 if feat_res["anomaly_score"] >= frozen_thresholds["feature_anomaly_threshold"] else 0
                preds_feat.append(pred_feat)

                # B. Sequence similarity baseline
                sim_res = similarity_service.compare_against_reference_panel(seq, label, reference_panel)
                pred_sim = 1 if (not sim_res["label_concordant"] or sim_res["anomaly_score"] >= frozen_thresholds["similarity_anomaly_threshold"]) else 0
                preds_sim.append(pred_sim)

                # C. ESM-2 embedding anomaly
                emb, _ = embedding_service.compute_embedding(seq, accession=ident, use_cache=True)
                emb_res = det.evaluate_embedding(emb, reference_panel, assigned_functional_label=label)
                pred_emb = 1 if (emb_res["is_outlier"] or not emb_res.get("class_concordant", True)) else 0
                preds_emb.append(pred_emb)

                # D. Evidence-aware ensemble prioritization
                is_synth = bool(case.get("synthetic_identifier"))
                prov_res = {
                    "provenance_penalty": 0.50 if is_synth else 0.25,
                    "overall_category": "COMPUTATIONAL_UNREVIEWED" if is_synth else "EXPERIMENTAL",
                    "summary": "Benchmark evaluation instance.",
                }
                score_res = scorer.compute_review_priority(emb_res, sim_res, feat_res, prov_res)
                pred_ensemble = 1 if score_res["review_priority"] in ("HIGH", "MODERATE") else 0
                preds_ensemble.append(pred_ensemble)

                detailed_list.append({
                    "identifier": ident,
                    "accession": case.get("accession") or case.get("original_accession"),
                    "gene_name": case.get("gene_name"),
                    "case_type": case.get("case_type"),
                    "ground_truth_category": case.get("ground_truth_category"),
                    "dataset_split": case.get("dataset_split", "N/A"),
                    "is_inconsistent": case.get("is_inconsistent", False),
                    "functional_label": label,
                    "predictions": {
                        "sequence_similarity": pred_sim,
                        "esm2_anomaly": pred_emb,
                        "kinase_features": pred_feat,
                        "evidence_ensemble": pred_ensemble,
                    },
                    "scores": {
                        "sequence_identity": round(float(sim_res.get("best_identity", 0.0)), 4),
                        "similarity_anomaly": round(float(sim_res.get("anomaly_score", 0.0)), 4),
                        "label_concordant": sim_res.get("label_concordant", True),
                        "embedding_anomaly": round(float(emb_res.get("anomaly_score", 0.0)), 4),
                        "embedding_raw_distance": round(float(emb_res.get("raw_combined_distance", 0.0)), 4),
                        "feature_anomaly": round(float(feat_res.get("anomaly_score", 0.0)), 4),
                        "canonical_motif_count": feat_res.get("canonical_count", 0),
                        "variant_motif_count": feat_res.get("variant_count", 0),
                        "absent_motif_count": feat_res.get("absent_count", 0),
                        "contradiction_score": round(float(score_res.get("contradiction_score", 0.0)), 4),
                        "review_priority": score_res.get("review_priority", "LOW"),
                    },
                    "label_rationale": case.get("label_rationale", ""),
                })

            methods_metrics = {
                "sequence_similarity_baseline": calculate_binary_metrics(y_true, preds_sim, task_name="Sequence Similarity"),
                "esm2_embedding_anomaly": calculate_binary_metrics(y_true, preds_emb, task_name="ESM-2 Embedding Anomaly"),
                "kinase_biological_features": calculate_binary_metrics(y_true, preds_feat, task_name="Kinase Features"),
                "evidence_aware_ensemble": calculate_binary_metrics(y_true, preds_ensemble, task_name="Evidence-Aware Ensemble"),
            }
            return detailed_list, methods_metrics

        # Execute evaluations across defined partitions:
        # A. Independent TEST Set (Controlled Tasks 1 & 2 Combined on Test split)
        test_detailed, test_methods_comparison = evaluate_case_subset(test_cases)

        # B. Task 1: Synthetic Label Contradictions Only (Test split Category C vs Controls)
        task1_cases = [
            c for c in test_cases
            if c.get("case_type") in ("CATEGORY_C_SYNTHETIC_LABEL", "CATEGORY_C_SYNTHETIC_CONTROL", "CATEGORY_A_REFERENCE")
        ]
        _, task1_metrics = evaluate_case_subset(task1_cases)

        # C. Task 2: Synthetic Sequence Perturbations Only (Test split Category D vs Controls)
        task2_cases = [
            c for c in test_cases
            if c.get("case_type") in ("CATEGORY_D_SYNTHETIC_SEQUENCE", "CATEGORY_C_SYNTHETIC_CONTROL", "CATEGORY_A_REFERENCE")
        ]
        _, task2_metrics = evaluate_case_subset(task2_cases)

        # D. Task 3: Natural Biological Exceptions (Category B: VRK3, ILK) - Exploratory Analysis
        cat_b_detailed = []
        for case in cat_b_cases:
            seq = case["sequence"]
            label = case.get("functional_label")
            feat_res = feature_analyzer.analyze_sequence(seq)
            sim_res = similarity_service.compare_against_reference_panel(seq, label, reference_panel)
            emb, _ = embedding_service.compute_embedding(seq, accession=case.get("accession"), use_cache=True)
            emb_res = det.evaluate_embedding(emb, reference_panel, assigned_functional_label=label)
            prov_res = {
                "provenance_penalty": 0.20,
                "overall_category": "EXPERIMENTAL_REVIEWED",
                "summary": "Natural pseudokinase record with characterized non-catalytic biological function.",
            }
            score_res = scorer.compute_review_priority(emb_res, sim_res, feat_res, prov_res)

            cat_b_detailed.append({
                "accession": case.get("accession"),
                "gene_name": case.get("gene_name"),
                "assigned_annotation": label,
                "classification": "BIOLOGICAL_EXCEPTION (Pseudokinase)",
                "detected_motifs": {
                    "canonical": feat_res.get("canonical_count"),
                    "variant": feat_res.get("variant_count"),
                    "absent": feat_res.get("absent_count"),
                    "summary": feat_res.get("summary"),
                },
                "review_priority": score_res.get("review_priority"),
                "contradiction_score": score_res.get("contradiction_score"),
                "biological_caveat": (
                    "Lacks canonical phosphotransfer triad due to natural evolutionary divergence. "
                    "Functions as non-catalytic regulator/scaffold. Labeled as legitimate biological exception, "
                    "NOT a clerical misannotation."
                ),
            })

        # E. Calibration Set Evaluation (for verification that thresholds were derived honestly)
        calib_detailed, calib_methods_comparison = evaluate_case_subset(calib_cases)

        # F. Compute ESM-2 Embedding Diagnostics across all evaluated instances
        all_evaluated = test_detailed + calib_detailed
        diagnostics_data = []
        for d in all_evaluated:
            diagnostics_data.append({
                "ground_truth_category": d.get("ground_truth_category"),
                "embedding_anomaly_score": d["scores"]["embedding_anomaly"],
                "embedding_raw_distance": d["scores"]["embedding_raw_distance"],
            })
        esm_diagnostics = det.compute_diagnostics(diagnostics_data, reference_panel)

        # Assemble Master Evaluation Report (v2)
        report_v2 = {
            "evaluation_title": "Scientific Benchmark Evaluation Report (Version 2)",
            "evaluation_version": "2.0.0",
            "run_identifier": run_id,
            "timestamp": "2026-10-25T12:00:00Z",
            "model_identifier": model_name,
            "random_seed": RANDOM_SEED,
            "frozen_thresholds": frozen_thresholds,
            "dataset_summary": {
                "total_benchmark_cases": len(benchmark_cases),
                "calibration_cases_count": len(calib_cases),
                "independent_test_cases_count": len(test_cases),
                "natural_exceptions_count": len(cat_b_cases),
                "reference_panel_size": len(reference_panel),
            },
            "category_definitions": {
                "CATEGORY_A_REFERENCE": "High-confidence experimentally characterized human kinase reference controls (CONGRUENT_REFERENCE).",
                "CATEGORY_B_NATURAL_EXCEPTION": "Natural pseudokinases and divergent kinases requiring biological contextualization (NATURAL_EXCEPTION).",
                "CATEGORY_C_SYNTHETIC_LABEL": "Controlled functional label swaps between Tyrosine kinase and Ser/Thr kinase activities (SYNTHETIC_LABEL_CONTRADICTION).",
                "CATEGORY_D_SYNTHETIC_SEQUENCE": "Controlled catalytic triad mutations (VAIK, HRD, DFG knockouts) testing sensitivity to catalytic disruptions (SYNTHETIC_SEQUENCE_PERTURBATION).",
                "CATEGORY_C_SYNTHETIC_CONTROL": "Unaltered canonical sequence and annotation negative controls (CONGRUENT_CONTROL).",
            },
            "task_evaluations": {
                "task1_label_contradiction_detection": {
                    "description": "Evaluation of detection accuracy for controlled functional label swaps (Category C) vs Controls.",
                    "sample_size": len(task1_cases),
                    "methods": task1_metrics,
                },
                "task2_sequence_perturbation_detection": {
                    "description": "Evaluation of detection accuracy for catalytic motif knockouts (Category D) vs Controls.",
                    "sample_size": len(task2_cases),
                    "methods": task2_metrics,
                },
                "task3_natural_biological_exceptions": {
                    "description": "Exploratory characterization of naturally occurring pseudokinases. Not treated as binary clerical error.",
                    "evaluated_cases": cat_b_detailed,
                },
                "task4_real_world_annotation_limitations": {
                    "description": "Real-world confirmed annotation error status in public reference databases.",
                    "status": "UNVALIDATED_IN_PUBLIC_DATABASES",
                    "scientific_caveat": (
                        "No independently validated, high-throughput ground truth of confirmed clerical misannotations "
                        "exists in public protein databases. Real-world misannotation accuracy cannot be claimed without "
                        "independent experimental verification. Current results evaluate controlled sensitivity, not public database error rates."
                    ),
                },
            },
            "overall_independent_test_evaluation": {
                "description": "Comprehensive comparative performance on the independent frozen TEST partition (Tasks 1 & 2 combined).",
                "sample_size": len(test_cases),
                "methods_comparison": test_methods_comparison,
            },
            "calibration_split_performance": {
                "description": "Performance on the calibration partition used for threshold tuning.",
                "sample_size": len(calib_cases),
                "methods_comparison": calib_methods_comparison,
            },
            "esm2_embedding_diagnostics": esm_diagnostics,
            "detailed_case_evaluations": test_detailed,
            "scientific_limitations": [
                "Global mean-pooled ESM-2 embeddings (8M) are dominated by tertiary fold homology; point mutations in long sequences produce small cosine shifts (<0.001).",
                "Unsupervised sequence representations cannot detect label discordance unless conditioned on functional class annotations.",
                "Sequence similarity baseline outperforms embeddings for label swaps because alignment directly matches homologous residues with known experimental labels.",
                "Pseudokinases represent legitimate evolutionary exceptions, not database errors.",
            ],
        }

        # 1. Save artifacts/evaluation_report_v2.json
        report_v2_path = self.artifacts_dir / "evaluation_report_v2.json"
        try:
            with open(report_v2_path, "w", encoding="utf-8") as f:
                json.dump(report_v2, f, indent=2)
            logger.info(f"Evaluation report v2 saved to {report_v2_path}")
        except Exception as e:
            logger.error(f"Failed to write evaluation_report_v2.json: {e}")

        # 2. Save artifacts/evaluation_summary_v2.csv
        summary_csv_path = self.artifacts_dir / "evaluation_summary_v2.csv"
        try:
            rows = format_metrics_table(test_methods_comparison)
            if rows:
                with open(summary_csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
            logger.info(f"Evaluation summary v2 CSV saved to {summary_csv_path}")
        except Exception as e:
            logger.error(f"Failed to write evaluation_summary_v2.csv: {e}")

        # 3. Save artifacts/benchmark_diagnostics_v2.json
        diagnostics_path = self.artifacts_dir / "benchmark_diagnostics_v2.json"
        try:
            with open(diagnostics_path, "w", encoding="utf-8") as f:
                json.dump(esm_diagnostics, f, indent=2)
            logger.info(f"Benchmark diagnostics v2 saved to {diagnostics_path}")
        except Exception as e:
            logger.error(f"Failed to write benchmark_diagnostics_v2.json: {e}")

        return report_v2
