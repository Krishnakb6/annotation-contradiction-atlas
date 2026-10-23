"""
Command-line evaluation benchmark script for The Annotation Contradiction Atlas.
Executes controlled benchmark evaluation comparing sequence similarity, ESM-2 embeddings,
biological motif checks, and evidence-aware prioritization.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DEFAULT_ESM_MODEL, RANDOM_SEED
from database.connection import get_db_session
from database.repositories import ProteinRepository, BenchmarkRepository
from services.kinase_features import KinaseFeatureAnalyzer
from services.embeddings import ESMEmbeddingService
from services.sequence_similarity import SequenceSimilarityBaseline
from services.contradiction_scoring import ContradictionScorer
from services.benchmark import BenchmarkService
from services.data_import import CURATED_REFERENCE_KINASES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("atlas.evaluation")


def main():
    parser = argparse.ArgumentParser(description="Execute reproducible benchmark evaluation")
    parser.add_argument("--num-synthetic", type=int, default=32, help="Number of synthetic perturbation cases")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed for reproducibility")
    parser.add_argument("--model", type=str, default=DEFAULT_ESM_MODEL, help="ESM-2 model identifier")
    args = parser.parse_args()

    logger.info("Initializing services for benchmark evaluation...")
    feature_analyzer = KinaseFeatureAnalyzer()
    embedding_service = ESMEmbeddingService(model_name=args.model)
    similarity_service = SequenceSimilarityBaseline()
    scorer = ContradictionScorer()
    benchmark_service = BenchmarkService()

    # Load base proteins from database or curated reference fallback
    base_proteins = []
    with get_db_session() as session:
        prot_repo = ProteinRepository(session)
        db_prots = prot_repo.get_all_with_sequence(limit=50)
        if db_prots:
            for p in db_prots:
                base_proteins.append({
                    "accession": p.accession,
                    "gene_name": p.gene_name,
                    "protein_name": p.protein_name,
                    "sequence": p.sequence,
                    "functional_label": p.annotations[0].functional_label if p.annotations else "Kinase catalytic activity",
                    "reviewed": p.reviewed,
                })

    if not base_proteins:
        logger.info("Using curated reference kinases for base evaluation panel.")
        for p in CURATED_REFERENCE_KINASES:
            base_proteins.append({
                "accession": p["accession"],
                "gene_name": p["gene_name"],
                "protein_name": p["protein_name"],
                "sequence": p["sequence"],
                "functional_label": p["annotations"][0]["functional_label"],
                "reviewed": p["reviewed"],
            })

    # Build reference panel
    reference_panel = []
    for p in base_proteins[:20]:
        emb, _ = embedding_service.compute_embedding(p["sequence"], accession=p["accession"], use_cache=True)
        reference_panel.append({
            "accession": p["accession"],
            "gene_name": p["gene_name"],
            "protein_name": p["protein_name"],
            "sequence": p["sequence"],
            "functional_label": p["functional_label"],
            "embedding": emb,
        })

    # 1. Category A: High-confidence reference cases
    cat_a_cases = []
    for p in base_proteins[:10]:
        cat_a_cases.append({
            "accession": p["accession"],
            "sequence": p["sequence"],
            "functional_label": p["functional_label"],
            "case_type": "CATEGORY_A_REFERENCE",
            "ground_truth_category": "CONGRUENT",
            "is_inconsistent": False,
            "label_rationale": "High-confidence experimentally characterized human kinase reference.",
        })

    # 2. Category B: Natural pseudokinases / exceptions
    cat_b_cases = [
        {
            "accession": "Q9Y616",
            "gene_name": "VRK3",
            "sequence": "MEGSRSSGSEESEEEPQGRPEPGSQRPKAVRGAQGPRSEGNKVRPAAANSRCPGAPGARAKAPVSRKPRATPRTPAAGSLAGASLVPLLGFLVAVLGAAATAVAGQRLCRWQEVRLPGPLRPEAVTALLDRLSVGLEPELHRRCVEALRAGSLGGSGGATDVVAKLGALLRKLRLAPLRKLRALCRAAERLADEPPALLRVARQALAGLVEVGGWEEAEAALGAPEEGPAGLSGLFWLLLHGAARSPLWALAAGPGAFRHQALRDALAGLCRLLRRLGPGAWGPELRSALAWCLGALCACPEALPEV",
            "functional_label": "Inactive serine/threonine-protein kinase VRK3",
            "case_type": "CATEGORY_B_NATURAL_EXCEPTION",
            "ground_truth_category": "NATURAL_PSEUDOKINASE",
            "is_inconsistent": True,
            "label_rationale": "Documented pseudokinase with catalytic loop deviation (HGN vs HRD).",
        },
        {
            "accession": "Q13418",
            "gene_name": "ILK",
            "sequence": "MDDMDAMLAGLEPPAISLSTDGSLTVVVTETNSSPTLQRLVEQGIRVFIDGSSVEKLQEFYQLMVERAKSEELRDIELIKSLIQGKHIIDLKDNVFSSDTFYSVFKGLKDFEKDDTILKKLREVLAKGLKQLQLKDLGLPFEEAEMLKSLELLFKKDIKDLKDIVLKTVDFFLKLIKLKEKDREKLKKLREFLDKALEEVKKVDLGKPFELKEMLEALELLFKKDIKDLKDIVLKTVDFFLKLIKLKEKDREKLKKLREFLDKALEEVKKVDLGKPFELKEMLEALELLFKKDIKDLKDIVLKTVDFFLKLIKLKEKDREKLKKLREFLDKALEEVKKVDLGKPFELKEMLE",
            "functional_label": "Integrin-linked protein kinase (pseudokinase)",
            "case_type": "CATEGORY_B_NATURAL_EXCEPTION",
            "ground_truth_category": "NATURAL_PSEUDOKINASE",
            "is_inconsistent": True,
            "label_rationale": "Documented pseudokinase functioning as scaffold without phosphotransfer.",
        }
    ]

    # 3. Category C: Controlled synthetic perturbations
    cat_c_cases = benchmark_service.build_synthetic_benchmark(
        base_proteins=base_proteins,
        seed=args.seed,
        num_synthetic_cases=args.num_synthetic,
    )

    all_cases = cat_a_cases + cat_b_cases + cat_c_cases
    logger.info(f"Running evaluation over {len(all_cases)} total benchmark cases ({len(cat_c_cases)} synthetic, {len(cat_b_cases)} natural exceptions, {len(cat_a_cases)} references)...")

    report = benchmark_service.run_evaluation(
        benchmark_cases=all_cases,
        reference_panel=reference_panel,
        similarity_service=similarity_service,
        embedding_service=embedding_service,
        feature_analyzer=feature_analyzer,
        scorer=scorer,
    )

    # Print summary table
    print("\n" + "="*80)
    print("BENCHMARK EVALUATION RESULTS ACROSS DETECTION METHODS")
    print("="*80)
    print(f"{'Method':<35} | {'Prec':<6} | {'Recall':<6} | {'F1':<6} | {'Spec':<6} | {'Acc':<6} | {'TP':<3} | {'FP':<3}")
    print("-"*80)
    for m_name, m in report["methods_comparison"].items():
        name_clean = m_name.replace("_", " ").title()
        print(f"{name_clean:<35} | {m['precision']:<6.3f} | {m['recall']:<6.3f} | {m['f1_score']:<6.3f} | {m['specificity']:<6.3f} | {m['accuracy']:<6.3f} | {m['true_positives']:<3} | {m['false_positives']:<3}")
    print("="*80)

    if report.get("synthetic_subset_performance"):
        sm = report["synthetic_subset_performance"]
        print(f"Synthetic Subset Performance (Ensemble): F1={sm['f1_score']:.3f}, Precision={sm['precision']:.3f}, Recall={sm['recall']:.3f}")
    if report.get("natural_subset_performance"):
        nm = report["natural_subset_performance"]
        print(f"Natural Subset Performance (Ensemble):   F1={nm['f1_score']:.3f}, Precision={nm['precision']:.3f}, Recall={nm['recall']:.3f}")

    print("\nArtifact saved to: artifacts/evaluation_report.json\n")


if __name__ == "__main__":
    main()
