"""
Reporting and Export Service.
Generates CSV/JSON exports, comprehensive summary statistics,
and scientific markdown documentation for analysis runs and contradictions.
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from database.connection import get_db_session
from database.models import Protein, ReviewFlag, SequenceFeature, FunctionAnnotation, AnalysisRun

logger = logging.getLogger("contradiction_atlas.reporting")


class ReportingService:
    """
    Coordinates metrics compilation, CSV table exports, and summary narratives.
    """

    @staticmethod
    def get_database_summary() -> Dict[str, Any]:
        """
        Gathers live metrics directly from the database for the overview dashboard.
        """
        with get_db_session() as session:
            total_proteins = session.query(Protein).count()
            reviewed_count = session.query(Protein).filter(Protein.reviewed == True).count()
            unreviewed_count = session.query(Protein).filter(Protein.reviewed == False).count()

            proteins_with_annotations = session.query(FunctionAnnotation.protein_id).distinct().count()

            # Review flags by priority
            high_count = session.query(ReviewFlag).filter(ReviewFlag.review_priority == "HIGH").count()
            mod_count = session.query(ReviewFlag).filter(ReviewFlag.review_priority == "MODERATE").count()
            low_count = session.query(ReviewFlag).filter(ReviewFlag.review_priority == "LOW").count()
            total_flags = high_count + mod_count + low_count

            # Evidence category distribution
            evidence_dist = {}
            for cat, count in session.query(FunctionAnnotation.evidence_category, func.count(FunctionAnnotation.id)).group_by(FunctionAnnotation.evidence_category).all():
                evidence_dist[cat or "UNSPECIFIED"] = count

            # Common flag reasons
            top_flags = session.query(ReviewFlag.flag_reason, func.count(ReviewFlag.id)).group_by(ReviewFlag.flag_reason).order_by(desc(func.count(ReviewFlag.id))).limit(5).all()

            # Latest completed run
            latest_run = session.query(AnalysisRun).filter(AnalysisRun.run_status == "COMPLETED").order_by(desc(AnalysisRun.completion_time)).first()

            return {
                "total_proteins": total_proteins,
                "reviewed_count": reviewed_count,
                "unreviewed_count": unreviewed_count,
                "proteins_with_annotations": proteins_with_annotations,
                "analyzed_records": total_flags,
                "priority_breakdown": {
                    "HIGH": high_count,
                    "MODERATE": mod_count,
                    "LOW": low_count,
                },
                "evidence_distribution": evidence_dist,
                "top_flag_reasons": [{"reason": r, "count": c} for r, c in top_flags],
                "latest_run": {
                    "run_identifier": latest_run.run_identifier,
                    "dataset_version": latest_run.dataset_version,
                    "completed_at": latest_run.completion_time.isoformat() if latest_run.completion_time else None,
                } if latest_run else None,
            }

    @staticmethod
    def export_proteins_to_csv(proteins: List[Protein]) -> str:
        """
        Exports protein records with flags and annotations into standard CSV string.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Accession",
            "Gene Name",
            "Protein Name",
            "Sequence Length",
            "Reviewed Status",
            "Review Priority",
            "Contradiction Score",
            "Flag Reason",
            "Source URL",
        ])

        for p in proteins:
            flag = p.review_flags[0] if p.review_flags else None
            writer.writerow([
                p.accession,
                p.gene_name or "",
                p.protein_name,
                p.sequence_length,
                "Reviewed" if p.reviewed else "Unreviewed",
                flag.review_priority if flag else "NOT_ANALYZED",
                f"{flag.contradiction_score:.4f}" if flag else "",
                flag.flag_reason if flag else "",
                p.source_url,
            ])

        return output.getvalue()


from sqlalchemy import func, desc
