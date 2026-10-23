"""
Method E: Annotation Provenance Analysis.
Evaluates evidence grades, ECO codes, PubMed citations, and Swiss-Prot review status.
Generates an evidence reliability profile and an interpretable provenance penalty score.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("contradiction_atlas.provenance")


class ProvenanceAnalyzer:
    """
    Assesses annotation provenance, evidence grades, and documentation strength.
    """

    def analyze_provenance(
        self,
        reviewed: bool,
        annotations: List[Dict[str, Any]],
        protein_existence: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates provenance reliability and penalty scores based on explicit evidence tiers.
        """
        if not annotations:
            # Missing annotations
            return {
                "overall_category": "UNANNOTATED",
                "experimental_count": 0,
                "phylogenetic_count": 0,
                "computational_count": 0,
                "author_statement_count": 0,
                "has_pubmed_reference": False,
                "has_experimental_support": False,
                "provenance_reliability": 0.15,
                "provenance_penalty": 0.85,
                "summary": "No functional annotations or catalytic evidence records found for this entry.",
                "limitations": "Absence of annotation does not establish lack of activity; record may be uncurated.",
            }

        experimental_count = 0
        phylogenetic_count = 0
        computational_count = 0
        author_statement_count = 0
        has_pubmed = False

        for ann in annotations:
            cat = ann.get("evidence_category", "UNSPECIFIED")
            if cat == "EXPERIMENTAL":
                experimental_count += 1
            elif cat == "PHYLOGENETIC_CURATED":
                phylogenetic_count += 1
            elif cat == "COMPUTATIONAL_UNREVIEWED":
                computational_count += 1
            elif cat == "AUTHOR_STATEMENT":
                author_statement_count += 1

            ref = str(ann.get("supporting_reference") or "")
            if "pubmed" in ref.lower():
                has_pubmed = True

        total_anns = len(annotations)
        has_experimental = experimental_count > 0

        # Tier classification
        if has_experimental:
            overall_category = "EXPERIMENTAL"
            base_reliability = 0.95 if reviewed else 0.80
        elif phylogenetic_count > 0:
            overall_category = "PHYLOGENETIC_CURATED"
            base_reliability = 0.70 if reviewed else 0.55
        elif author_statement_count > 0:
            overall_category = "AUTHOR_STATEMENT"
            base_reliability = 0.50 if reviewed else 0.40
        elif computational_count > 0:
            overall_category = "COMPUTATIONAL_UNREVIEWED"
            base_reliability = 0.35 if reviewed else 0.20
        else:
            overall_category = "UNSPECIFIED"
            base_reliability = 0.25 if reviewed else 0.10

        # Bonus for verifiable PubMed reference
        if has_pubmed:
            base_reliability = min(1.0, base_reliability + 0.05)

        provenance_reliability = round(float(base_reliability), 4)
        # Provenance penalty reflects uncertainty / computational fragility
        provenance_penalty = round(float(1.0 - provenance_reliability), 4)

        # Scientific narrative summary
        summary_parts = []
        if reviewed:
            summary_parts.append("Reviewed entry (Swiss-Prot).")
        else:
            summary_parts.append("Unreviewed entry (TrEMBL / computational).")

        if has_experimental:
            summary_parts.append(f"Supported by direct experimental evidence ({experimental_count} record(s))" + (", with PubMed citations." if has_pubmed else "."))
        elif phylogenetic_count > 0:
            summary_parts.append(f"Curated via sequence similarity/homology ({phylogenetic_count} record(s)). Direct assays pending.")
        elif computational_count > 0:
            summary_parts.append(f"Inferred purely by automated rules/computational pipelines ({computational_count} record(s)).")
        else:
            summary_parts.append("Annotation lacks explicit verifiable evidence codes.")

        limitations = (
            "Experimental evidence in UniProt confirms biological activity in specific assays but does not preclude dual/atypical specificity."
            if has_experimental else
            "Computational/homology-inferred annotations carry higher vulnerability to systematic propagation of historical misannotations."
        )

        return {
            "overall_category": overall_category,
            "experimental_count": experimental_count,
            "phylogenetic_count": phylogenetic_count,
            "computational_count": computational_count,
            "author_statement_count": author_statement_count,
            "has_pubmed_reference": has_pubmed,
            "has_experimental_support": has_experimental,
            "provenance_reliability": provenance_reliability,
            "provenance_penalty": provenance_penalty,
            "summary": " ".join(summary_parts),
            "limitations": limitations,
        }
