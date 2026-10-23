"""
Full computational analysis pipeline for The Annotation Contradiction Atlas.
Executes sequence feature checks, ESM-2 embeddings, similarity baseline, provenance analysis,
and multi-evidence contradiction scoring across all protein records in the database.
"""
from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DEFAULT_ESM_MODEL, RANDOM_SEED, WEIGHTS, PRIORITY_THRESHOLDS
from database.connection import get_db_session, init_db
from database.models import Protein, FunctionAnnotation
from database.repositories import (
    ProteinRepository,
    SequenceFeatureRepository,
    EmbeddingRepository,
    ModelResultRepository,
    ReviewFlagRepository,
    AnalysisRunRepository,
)
from services.kinase_features import KinaseFeatureAnalyzer
from services.embeddings import ESMEmbeddingService
from services.sequence_similarity import SequenceSimilarityBaseline
from services.anomaly_detection import EmbeddingAnomalyDetector
from services.provenance_analysis import ProvenanceAnalyzer
from services.contradiction_scoring import ContradictionScorer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("atlas.analysis")


def run_full_pipeline(limit: int = None, model_name: str = DEFAULT_ESM_MODEL, seed: int = RANDOM_SEED) -> Dict[str, Any]:
    """
    Executes all analytical modules across stored proteins.
    """
    init_db()

    # Initialize service components
    feature_analyzer = KinaseFeatureAnalyzer()
    embedding_service = ESMEmbeddingService(model_name=model_name)
    similarity_service = SequenceSimilarityBaseline()
    anomaly_detector = EmbeddingAnomalyDetector()
    provenance_analyzer = ProvenanceAnalyzer()
    scorer = ContradictionScorer()

    run_id_str = f"RUN_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    with get_db_session() as session:
        prot_repo = ProteinRepository(session)
        feat_repo = SequenceFeatureRepository(session)
        emb_repo = EmbeddingRepository(session)
        result_repo = ModelResultRepository(session)
        flag_repo = ReviewFlagRepository(session)
        run_repo = AnalysisRunRepository(session)

        proteins = prot_repo.get_all_with_sequence(limit=limit)
        if not proteins:
            logger.warning("No protein records found in database. Ingest UniProt records first.")
            return {"status": "EMPTY_DATABASE", "message": "No proteins found."}

        logger.info(f"Loaded {len(proteins)} proteins for computational analysis.")

        # Create AnalysisRun
        analysis_run = run_repo.create_run(
            identifier=run_id_str,
            dataset_version="UniProtKB-2026_human_kinome",
            config_dict={"esm_model": model_name, "weights": WEIGHTS, "thresholds": PRIORITY_THRESHOLDS},
            seed=seed,
        )

        # Build high-confidence reference panel for similarity and embedding comparisons
        # Prefer reviewed proteins with direct experimental evidence
        reference_panel: List[Dict[str, Any]] = []
        for p in proteins:
            if p.reviewed and p.sequence and len(reference_panel) < 40:
                # Get functional label
                ann = session.query(FunctionAnnotation).filter(
                    FunctionAnnotation.protein_id == p.id,
                    FunctionAnnotation.evidence_category == "EXPERIMENTAL"
                ).first() or session.query(FunctionAnnotation).filter(FunctionAnnotation.protein_id == p.id).first()

                ref_label = ann.functional_label if ann else "Protein kinase activity"
                # Compute or retrieve embedding
                ref_emb, _ = embedding_service.compute_embedding(p.sequence, accession=p.accession, use_cache=True)
                reference_panel.append({
                    "accession": p.accession,
                    "gene_name": p.gene_name,
                    "protein_name": p.protein_name,
                    "sequence": p.sequence,
                    "functional_label": ref_label,
                    "embedding": ref_emb,
                })

        logger.info(f"Assembled reference panel containing {len(reference_panel)} characterized kinase references.")

        processed_count = 0
        priority_tallies = {"HIGH": 0, "MODERATE": 0, "LOW": 0}

        for p in proteins:
            # 1. Kinase feature checks
            feat_res = feature_analyzer.analyze_sequence(p.sequence)
            feat_repo.replace_features(p.id, feat_res["motifs"])

            # 2. ESM-2 Embeddings
            emb, emb_meta = embedding_service.compute_embedding(p.sequence, accession=p.accession, use_cache=True)
            emb_repo.upsert_record({
                "protein_id": p.id,
                "model_name": model_name,
                "model_version": "1.0",
                "embedding_dim": len(emb),
                "artifact_path": emb_meta.get("artifact_path", f"mem_{p.accession}.npy"),
                "preprocessing_details": emb_meta.get("pooling", "mean_pool"),
            })

            # 3. Embedding anomaly detection
            emb_anomaly = anomaly_detector.evaluate_embedding(emb, reference_panel)
            result_repo.save_result({
                "protein_id": p.id,
                "run_id": analysis_run.id,
                "method_name": "esm2_anomaly",
                "model_version": model_name,
                "anomaly_score": emb_anomaly["anomaly_score"],
                "threshold": emb_anomaly["threshold"],
                "is_outlier": emb_anomaly["is_outlier"],
                "result_explanation": emb_anomaly["explanation"],
            })

            # 4. Sequence similarity baseline
            p_anns = session.query(FunctionAnnotation).filter(FunctionAnnotation.protein_id == p.id).all()
            q_label = p_anns[0].functional_label if p_anns else None
            sim_res = similarity_service.compare_against_reference_panel(p.sequence, q_label, reference_panel)
            result_repo.save_result({
                "protein_id": p.id,
                "run_id": analysis_run.id,
                "method_name": "sequence_similarity",
                "model_version": "biopython_pairwise",
                "anomaly_score": sim_res["anomaly_score"],
                "similarity_score": sim_res["best_identity"],
                "reference_protein_accession": sim_res["best_reference_accession"],
                "is_outlier": not sim_res["label_concordant"],
                "result_explanation": sim_res["explanation"],
            })

            # 5. Provenance analysis
            anns_dicts = [
                {"functional_label": a.functional_label, "evidence_category": a.evidence_category, "supporting_reference": a.supporting_reference}
                for a in p_anns
            ]
            prov_res = provenance_analyzer.analyze_provenance(p.reviewed, anns_dicts, p.protein_existence)

            # 6. Synthesized Contradiction Scoring & Review Priority
            prot_meta = {"protein_name": p.protein_name, "gene_name": p.gene_name}
            score_res = scorer.compute_review_priority(emb_anomaly, sim_res, feat_res, prov_res, protein_info=prot_meta)

            flag_repo.upsert_flag({
                "protein_id": p.id,
                "run_id": analysis_run.id,
                "review_priority": score_res["review_priority"],
                "contradiction_score": score_res["contradiction_score"],
                "flag_reason": score_res["flag_reason"],
                "supporting_evidence_summary": score_res["supporting_evidence_summary"],
                "contradictory_signals": score_res["contradictory_signals"],
                "limitations": score_res["limitations"],
                "review_status": "PENDING",
            })

            priority_tallies[score_res["review_priority"]] += 1
            processed_count += 1
            if processed_count % 50 == 0:
                logger.info(f"Processed {processed_count}/{len(proteins)} proteins...")

        # Complete AnalysisRun
        summary = {
            "total_analyzed": processed_count,
            "priority_counts": priority_tallies,
            "reference_panel_size": len(reference_panel),
            "completed_at": datetime.utcnow().isoformat(),
        }
        run_repo.complete_run(analysis_run.id, summary, status="COMPLETED")

        logger.info(f"Analysis complete: {summary}")
        return summary


def main():
    parser = argparse.ArgumentParser(description="Run computational analysis pipeline on database proteins")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of proteins to analyze (for quick runs)")
    parser.add_argument("--model", type=str, default=DEFAULT_ESM_MODEL, help="ESM-2 model identifier")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed for reproducibility")
    args = parser.parse_args()

    summary = run_full_pipeline(limit=args.limit, model_name=args.model, seed=args.seed)
    print("\n" + "="*50)
    print("ANALYSIS EXECUTION SUMMARY")
    print("="*50)
    print(f"Total Analyzed:   {summary.get('total_analyzed', 0)}")
    print(f"Priority Tallies: {summary.get('priority_counts', {})}")
    print(f"Completed At:     {summary.get('completed_at')}")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()
